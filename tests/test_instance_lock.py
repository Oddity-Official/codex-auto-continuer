from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from codex_auto_continuer.instance_lock import SingleInstanceLock, is_running
from codex_auto_continuer import instance_lock
from codex_auto_continuer.errors import AlreadyRunningError


def test_lock_is_reusable(tmp_path: Path):
    path = tmp_path / "x.lock"
    with SingleInstanceLock(path):
        assert path.exists()
    with SingleInstanceLock(path):
        pass


def test_running_status_uses_os_lock_not_stale_pid(tmp_path):
    path = tmp_path / "x.lock"
    assert not is_running(path)
    with SingleInstanceLock(path):
        assert is_running(path)
    assert not is_running(path)


def test_status_probe_preserves_owner_metadata(tmp_path):
    path = tmp_path / "x.lock"
    path.write_bytes(b"987654")
    assert not is_running(path)
    assert path.read_bytes() == b"987654"


def test_lock_io_failure_is_not_reported_as_running(tmp_path, monkeypatch):
    path = tmp_path / "x.lock"
    path.touch()
    failure = OSError(5, "fixture I/O failure")
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(instance_lock, "_lock", fail)
    with pytest.raises(OSError) as observed:
        is_running(path)
    assert observed.value is failure
    owner = SingleInstanceLock(path)
    with pytest.raises(OSError) as observed:
        owner.acquire()
    assert observed.value is failure and owner._file is None


def test_status_probes_do_not_claim_each_other_as_owner(tmp_path):
    path = tmp_path / "x.lock"
    path.write_bytes(b"987654")
    with path.open("rb", buffering=0) as probe:
        instance_lock._lock(probe, exclusive=False)
        try:
            assert not is_running(path)
            assert path.read_bytes() == b"987654"
        finally:
            instance_lock._unlock(probe)


def test_start_waits_for_short_status_probe(tmp_path):
    path = tmp_path / "x.lock"
    path.touch()
    acquired = threading.Event()
    def observe():
        with path.open("rb", buffering=0) as probe:
            instance_lock._lock(probe, exclusive=False)
            acquired.set()
            try:
                time.sleep(0.03)
            finally:
                instance_lock._unlock(probe)
    observer = threading.Thread(target=observe)
    observer.start()
    try:
        assert acquired.wait(1)
        with SingleInstanceLock(path):
            assert is_running(path)
    finally:
        observer.join(timeout=1)
    assert not observer.is_alive()


def test_empty_pid_rewrite_window_still_reports_lock_contention(tmp_path):
    with SingleInstanceLock(tmp_path / "x.lock") as owner:
        # Reproduce the gap between truncating PID metadata and writing it.
        owner._file.seek(0)
        owner._file.truncate()
        assert is_running(owner.path)
        contender = SingleInstanceLock(owner.path)
        with pytest.raises(AlreadyRunningError):
            contender.acquire()
        assert contender._file is None


def test_second_process_cannot_acquire(tmp_path: Path):
    path = tmp_path / "x.lock"
    src = Path(__file__).resolve().parents[1] / "src"
    code = (
        "from pathlib import Path; from codex_auto_continuer.instance_lock import SingleInstanceLock; "
        f"l=SingleInstanceLock(Path({str(path)!r})); "
        "\ntry:\n l.acquire(); print('acquired')\nexcept Exception as e:\n print(type(e).__name__); raise SystemExit(7)"
    )
    with SingleInstanceLock(path):
        env = os.environ.copy(); env["PYTHONPATH"] = str(src)
        cp = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=5)
    assert cp.returncode == 7
    assert "AlreadyRunningError" in cp.stdout

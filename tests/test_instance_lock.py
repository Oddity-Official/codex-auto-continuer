from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from codex_auto_continuer.instance_lock import SingleInstanceLock, is_running


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

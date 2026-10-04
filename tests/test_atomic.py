import os
import threading
import time

import pytest

from codex_auto_continuer.atomic import replace_file


@pytest.mark.skipif(os.name != "nt", reason="Native Windows file sharing")
def test_brief_reader_lock_does_not_turn_atomic_replace_into_a_runtime_failure(tmp_path):
    target, temporary = tmp_path / "status.json", tmp_path / "new.tmp"
    target.write_bytes(b"old complete snapshot")
    temporary.write_bytes(b"new complete snapshot")
    reader = target.open("rb")
    # Establish the actual Windows sharing failure before exercising the repair.
    with pytest.raises(PermissionError):
        os.replace(temporary, target)
    release = threading.Thread(target=lambda: (time.sleep(0.08), reader.close()))
    release.start()
    try:
        replace_file(temporary, target)
        assert target.read_bytes() == b"new complete snapshot" and not temporary.exists()
    finally:
        reader.close()
        release.join(timeout=1)


@pytest.mark.skipif(os.name != "nt", reason="Native Windows file sharing")
def test_persistent_lock_fails_bounded_and_preserves_both_files(tmp_path):
    target, temporary = tmp_path / "state.json", tmp_path / "new.tmp"
    target.write_bytes(b"saved obligations")
    temporary.write_bytes(b"new intent")
    with target.open("rb"):
        started = time.monotonic()
        with pytest.raises(PermissionError):
            replace_file(temporary, target, timeout=0.05)
        assert time.monotonic() - started < 0.5
    assert target.read_bytes() == b"saved obligations" and temporary.read_bytes() == b"new intent"

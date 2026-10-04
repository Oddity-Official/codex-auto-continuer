import os
import subprocess
import sys
from pathlib import Path

import pytest

from codex_auto_continuer.update_install import process_path


@pytest.mark.skipif(os.name != "nt", reason="Native Windows process handles")
def test_process_identity_distinguishes_live_and_exited_children_with_retained_handles():
    with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"]) as process:
        try:
            assert process_path(process.pid) == Path(sys.executable).resolve()
        finally:
            process.terminate()
            process.wait(timeout=10)
        # Popen still owns its Windows handle here: OpenProcess succeeds even after exit.
        assert process_path(process.pid) is None

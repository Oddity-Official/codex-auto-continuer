"""Keep atomic writes reliable across brief Windows reader/antivirus sharing locks."""
from __future__ import annotations

import os
import time
from pathlib import Path


def replace_file(temporary: Path, target: Path, *, timeout=1.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.replace(temporary, target)
            return
        except PermissionError:
            if os.name != "nt" or time.monotonic() >= deadline:
                raise
            time.sleep(0.02)

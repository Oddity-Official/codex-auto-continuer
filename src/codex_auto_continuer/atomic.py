"""Keep atomic writes reliable across brief Windows reader/antivirus sharing locks."""
from __future__ import annotations

import json
import os
import tempfile
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


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + "-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        replace_file(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

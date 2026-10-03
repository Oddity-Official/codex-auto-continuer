from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

from .errors import AlreadyRunningError


class SingleInstanceLock:
    def __init__(self, path: Path):
        self.path = path
        self._file: BinaryIO | None = None

    def acquire(self) -> None:
        if self._file is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        f = os.fdopen(fd, "r+b", buffering=0)
        try:
            if f.seek(0, os.SEEK_END) == 0:
                f.write(b"0")
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise AlreadyRunningError(
                        f"Another Codex Auto Continuer instance already holds {self.path}."
                    ) from exc
            else:
                import fcntl
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise AlreadyRunningError(
                        f"Another Codex Auto Continuer instance already holds {self.path}."
                    ) from exc
            f.seek(0)
            f.truncate()
            f.write(str(os.getpid()).encode("ascii"))
            f.flush()
        except Exception:
            f.close()
            raise
        self._file = f

    def release(self) -> None:
        f = self._file
        if f is None:
            return
        try:
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()
            self._file = None

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def is_running(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with SingleInstanceLock(path):
            return False
    except AlreadyRunningError:
        return True

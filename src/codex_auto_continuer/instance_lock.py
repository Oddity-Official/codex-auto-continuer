from __future__ import annotations

import errno
import os
import time
from pathlib import Path
from typing import BinaryIO

from .errors import AlreadyRunningError

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _Overlapped(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                    ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD), ("hEvent", wintypes.HANDLE)]

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel.LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                 wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_Overlapped)]
    _kernel.UnlockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.DWORD, ctypes.POINTER(_Overlapped)]
    _kernel.LockFileEx.restype = _kernel.UnlockFileEx.restype = wintypes.BOOL


def _lock(stream: BinaryIO, *, exclusive: bool) -> None:
    if os.name == "nt":
        flags = 1 | (2 if exclusive else 0)  # Immediate, shared probes or exclusive ownership.
        if not _kernel.LockFileEx(msvcrt.get_osfhandle(stream.fileno()), flags, 0, 1, 0, ctypes.byref(_Overlapped())):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        import fcntl
        fcntl.flock(stream.fileno(), (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)


def _unlock(stream: BinaryIO) -> None:
    if os.name == "nt":
        if not _kernel.UnlockFileEx(msvcrt.get_osfhandle(stream.fileno()), 0, 1, 0, ctypes.byref(_Overlapped())):
            raise ctypes.WinError(ctypes.get_last_error())
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _contended(exc: OSError) -> bool:
    return getattr(exc, "winerror", None) == 33 if os.name == "nt" else exc.errno in {errno.EACCES, errno.EAGAIN}


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
            # Lock the byte range before writing, including when it is past EOF.
            # A current owner may be rewriting PID metadata in an empty file.
            deadline = time.monotonic() + 0.1
            while True:
                try:
                    _lock(f, exclusive=True)
                    break
                except OSError as exc:
                    if not _contended(exc):
                        raise
                    if time.monotonic() >= deadline:
                        raise AlreadyRunningError(f"Another Codex Auto Continuer instance already holds {self.path}.") from exc
                    # Read-only status probes must not make a legitimate start fail.
                    time.sleep(0.005)
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
            _unlock(f)
        finally:
            f.close()
            self._file = None

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def is_running(path: Path) -> bool:
    try:
        stream = path.open("rb", buffering=0)
    except FileNotFoundError:
        return False
    with stream:
        try:
            # Shared probes coexist and never write PID metadata or pretend to own monitoring.
            _lock(stream, exclusive=False)
        except OSError as exc:
            if _contended(exc):
                return True
            raise
        try:
            return False
        finally:
            _unlock(stream)

"""Windows-account encryption for private local data; never export plaintext."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

from .errors import ConfigurationError


def dpapi(payload: bytes, *, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise ConfigurationError("Private queue holding requires Windows account encryption.")
    if not isinstance(payload, bytes) or not payload or len(payload) > 64 * 1024 * 1024:
        raise ConfigurationError("Private local data must contain between 1 byte and 64 MiB.")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
    incoming, outgoing = Blob(len(payload), buffer), Blob()
    if not operation(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ConfigurationError("Windows could not decrypt/encrypt private local data for this account. "
            "Preserve the encrypted file; use its original Windows account and inspect file permissions.")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)

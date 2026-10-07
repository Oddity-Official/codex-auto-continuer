"""Guard the Windows file-sharing boundary in native daemon fixture teardown."""
import ctypes
import importlib.util
import os
from ctypes import wintypes
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Native Windows directory sharing")
def test_daemon_directory_requires_delete_sharing_before_cleanup(tmp_path):
    module_path = Path(__file__).resolve().parents[1] / "integration/native_support.py"
    spec = importlib.util.spec_from_file_location("native_cleanup_fixture", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateFileW(str(tmp_path), 0x80000000, 3, None, 3, 0x02000000, None)
    assert handle != ctypes.c_void_p(-1).value
    try:
        with pytest.raises(TimeoutError, match="denies delete sharing"):
            module.wait_directory_release(tmp_path, timeout=0)
        assert tmp_path.is_dir(), "The readiness check must never delete the directory"
    finally:
        kernel.CloseHandle(handle)
    module.wait_directory_release(tmp_path, timeout=0)
    assert tmp_path.is_dir()

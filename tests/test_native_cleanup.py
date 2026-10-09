"""Guard the Windows file-sharing boundary in native daemon fixture teardown."""
import ctypes
import importlib.util
import os
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path

import pytest


def native_support():
    module_path = Path(__file__).resolve().parents[1] / "integration/native_support.py"
    spec = importlib.util.spec_from_file_location("native_cleanup_fixture", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shutdown_failure_keeps_primary_error_and_does_not_remove_live_home(tmp_path):
    module = native_support()
    fixture = module.NativeFixture(tmp_path, "unused")
    fixture.home = tmp_path / ".data/nfixture"
    fixture.home.mkdir(parents=True)
    def fail_shutdown():
        raise TimeoutError("original shutdown failure")
    fixture.stack.callback(fail_shutdown)
    with pytest.raises(TimeoutError, match="original shutdown failure"):
        fixture.__exit__(None, None, None)
    assert fixture.home.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows directory sharing")
def test_daemon_directory_requires_delete_sharing_before_cleanup(tmp_path):
    module = native_support()
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


@pytest.mark.skipif(os.name != "nt", reason="Native Windows process identity")
def test_detached_cleanup_stops_only_executables_inside_private_home(tmp_path, monkeypatch):
    module = native_support()
    original = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
    owned = tmp_path / "cmd.exe"
    shutil.copy2(original, owned)
    processes = [subprocess.Popen([str(binary), "/d", "/q", "/k"], cwd=tmp_path,
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW) for binary in (owned, original)]
    try:
        assert all(process.poll() is None for process in processes)
        monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_options: pytest.fail("Cleanup must not launch PowerShell/CIM"))
        assert module.stop_private_processes(tmp_path) == 1
        assert processes[0].wait(timeout=5) == 0
        assert processes[1].poll() is None, "An external executable must not be stopped"
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdin.close()

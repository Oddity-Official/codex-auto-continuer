from __future__ import annotations

import subprocess
import os
import sys
from pathlib import Path

import pytest

import codex_auto_continuer.codex as codex
from codex_auto_continuer.errors import CodexCommandError, ProtocolError


def cp(code=0, out="", err=""):
    return subprocess.CompletedProcess(["codex"], code, out, err)


def test_version_probe_finishes_when_a_helper_inherits_its_output(tmp_path):
    # A completed probe is not a timeout just because another process kept its handles.
    release = tmp_path / "release"
    helper = (
        "import pathlib, sys, time\n"
        "end = time.monotonic() + 10\n"
        "while not pathlib.Path(sys.argv[1]).exists() and time.monotonic() < end: time.sleep(.05)"
    )
    probe = ("import subprocess, sys; "
             "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]], "
             "stdout=sys.stdout, stderr=sys.stderr); print('codex-cli 0.160.0')")
    try:
        result = codex._run(sys._base_executable, ["-c", probe, helper, str(release)], 2)
        assert result.returncode == 0 and result.stdout.strip() == "codex-cli 0.160.0"
    finally:
        release.touch()


@pytest.mark.skipif(os.name != "nt", reason="Windows timeout cleanup")
def test_unresponsive_taskkill_does_not_escape_monitor_reconnect(tmp_path, monkeypatch):
    import psutil
    pid_file = tmp_path / "probe.pid"
    def slow_taskkill(args, **kwargs):
        assert args[0] == "taskkill"
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])
    monkeypatch.setattr(subprocess, "run", slow_taskkill)
    probe = ("import os, pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); "
             "time.sleep(12)")
    try:
        with pytest.raises(CodexCommandError, match="exceeded"):
            codex._run(sys._base_executable, ["-c", probe, str(pid_file)], 1)
        assert not psutil.pid_exists(int(pid_file.read_text()))
    finally:
        if pid_file.exists() and psutil.pid_exists(pid := int(pid_file.read_text())):
            psutil.Process(pid).kill()


def test_version_parse(monkeypatch):
    monkeypatch.setattr(codex, "_run", lambda *_: cp(out="codex-cli 0.160.0\n"))
    assert codex.codex_version("codex", 1) == "0.160.0"


def test_old_version_rejected(monkeypatch):
    monkeypatch.setattr(codex, "_run", lambda *_: cp(out="codex-cli 0.159.9\n"))
    with pytest.raises(ProtocolError, match="too old"):
        codex.codex_version("codex", 1)


def test_daemon_json(monkeypatch):
    monkeypatch.setattr(codex, "_run", lambda *_: cp(out='{"status":"Running","socketPath":"C:/x.sock","cliVersion":"0.160.0"}'))
    info = codex.daemon_version("codex", 1)
    assert str(info.socket_path).replace("\\", "/") == "C:/x.sock"


def test_ensure_daemon_can_start(monkeypatch):
    calls = []
    def fake_run(_bin, args, _timeout):
        calls.append(args)
        if args[-1] == "version":
            return cp(1, err="not running")
        return cp(out='{"status":"Started","socketPath":"/tmp/x.sock"}')
    monkeypatch.setattr(codex, "_run", fake_run)
    assert codex.ensure_daemon("codex", 1, True).status == "Started"
    assert calls[-1][-1] == "start"


def test_ensure_daemon_no_autostart(monkeypatch):
    monkeypatch.setattr(codex, "_run", lambda *_: cp(1, err="nope"))
    with pytest.raises(CodexCommandError, match="auto_start_daemon"):
        codex.ensure_daemon("codex", 1, False)


@pytest.mark.skipif(os.name != "nt", reason="Windows native executable discovery")
def test_windows_desktop_binary_discovery_without_shell_path(tmp_path, monkeypatch):
    monkeypatch.setattr(codex.shutil, "which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    binary = tmp_path / "Programs/OpenAI/Codex/bin/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    assert codex.find_codex() == str(binary)


@pytest.mark.skipif(os.name != "nt", reason="Windows npm executable discovery")
def test_windows_npm_shim_resolves_native_binary_without_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "missing"))
    shim = tmp_path / "codex.cmd"
    monkeypatch.setattr(codex.shutil, "which", lambda name: str(shim) if name == "codex.cmd" else None)
    monkeypatch.setattr(codex.platform, "machine", lambda: "AMD64")
    binary = tmp_path / "node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    assert codex.find_codex() == str(binary)

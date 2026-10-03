from __future__ import annotations

import subprocess

import pytest

import codex_auto_continuer.codex as codex
from codex_auto_continuer.errors import CodexCommandError, ProtocolError


def cp(code=0, out="", err=""):
    return subprocess.CompletedProcess(["codex"], code, out, err)


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

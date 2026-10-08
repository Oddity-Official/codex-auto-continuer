from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from codex_auto_continuer import updates, update_install
from codex_auto_continuer.config import Config
from codex_auto_continuer.updates import UpdateError


def package(tmp_path, extra=None):
    files = {"CodexAutoContinuer.exe": b"new GUI", "CodexAutoContinuer-CLI.exe": b"new CLI",
             "_internal/runtime.dll": b"new runtime", "README.md": b"Guide", "LICENSE": b"MIT"}
    if extra:
        files.update(extra)
    manifest = {"version": "0.6.0", "platform": "windows-x86_64", "files": {
        name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()}}
    path = tmp_path / "codex-auto-continuer-0.6.0-windows-x86_64.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            entry = zipfile.ZipInfo()
            entry.filename = "CodexAutoContinuer/" + name
            archive.writestr(entry, data)
        archive.writestr("CodexAutoContinuer/RELEASE-MANIFEST.json", json.dumps(manifest))
    record = {"format": 1, "repository": "example/cac", "version": "0.6.0", "platform": "windows-x86_64",
              "asset": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "state_schema": 2}
    return path, record, manifest


def sign(record):
    private = Ed25519PrivateKey.generate()
    trust = {"repository": record["repository"], "public_key": private.public_key().public_bytes_raw().hex()}
    payload = json.dumps(record).encode()
    return payload, private.sign(payload), trust


def test_signature_authenticates_repository_platform_schema_and_exact_package(tmp_path):
    path, record, manifest = package(tmp_path)
    payload, signature, trust = sign(record)
    assert updates.signed_release(payload, signature, trust) == record
    assert updates.verify_zip(path, record) == manifest
    for wrong in (payload + b" ", payload.replace(b"example/cac", b"attacker/cac")):
        with pytest.raises(UpdateError, match="signature"):
            updates.signed_release(wrong, signature, trust)
    for field, value in (("repository", "attacker/cac"), ("state_schema", 3), ("platform", "linux"), ("bytes", True), ("version", "0.6.0-beta")):
        bad = record | {field: value}
        body, sig, other_trust = sign(bad)
        other_trust["repository"] = "example/cac"
        with pytest.raises(UpdateError):
            updates.signed_release(body, sig, other_trust)
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(UpdateError, match="size"):
        updates.verify_zip(path, record)


@pytest.mark.parametrize("name", ["../outside", "/absolute", "_internal/../../outside", "data/state.json", "Docs/audit.md",
    "_internal/C:evil", "_internal/a\\b", "_internal/NUL.txt", "_internal/foo.", "_internal/Foo/a", "_internal/CON", "LICENSE/a", "_internal/bad?name", "_internal/new\nline"])
def test_unsafe_release_paths_never_extract(tmp_path, name):
    extra = {name: b"bad"}
    if name == "_internal/Foo/a":
        extra["_internal/foo/b"] = b"collision"
    path, record, _ = package(tmp_path, extra)
    with pytest.raises(UpdateError, match="path|directories"):
        updates.verify_zip(path, record)
    assert not (tmp_path.parent / "outside").exists()


def test_release_rejects_symlink_and_duplicate_entries(tmp_path):
    for kind in ("symlink", "duplicate"):
        path, record, _ = package(tmp_path)
        with zipfile.ZipFile(path, "a") as archive:
            entry = zipfile.ZipInfo("CodexAutoContinuer/_internal/linked")
            entry.external_attr = (0o120777 << 16) if kind == "symlink" else 0
            archive.writestr(entry, b"target")
            if kind == "duplicate":
                with pytest.warns(UserWarning):
                    archive.writestr(entry, b"target")
        record.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        with pytest.raises(UpdateError, match="Unsafe"):
            updates.verify_zip(path, record)


def test_redirect_strips_authentication_and_rejects_foreign_hosts():
    request = urllib.request.Request("https://api.github.com/repos/example/cac/releases/assets/123",
                                     headers={"Authorization": "Bearer SECRET"})
    redirected = updates.GitHubRedirect().redirect_request(request, None, 302, "", {}, "https://release-assets.githubusercontent.com/package")
    assert not redirected.has_header("Authorization")
    for url in ("http://github.com/x", "https://evilgithubusercontent.com/x", "https://github.com@evil.example/x", "file:///x", "https://api.github.com:invalid/x"):
        with pytest.raises(UpdateError):
            updates.safe_url(url)


def test_metadata_rejects_duplicate_keys_and_non_finite_numbers():
    for payload in (b'{"version": "1", "version": "2"}', b'{"bytes": NaN}', b'[]'):
        with pytest.raises(UpdateError):
            updates.parse_json(payload)


def test_source_install_does_not_contact_network(tmp_path, monkeypatch):
    monkeypatch.delattr(updates.sys, "frozen", raising=False)
    monkeypatch.setattr(updates, "GitHub", lambda *_: pytest.fail("Source updater must not access GitHub"))
    assert updates.check_release(tmp_path / "settings.toml", Config(), stage=True)["status"] == "source_install"


def transaction(tmp_path):
    path, record, manifest = package(tmp_path)
    bundle = tmp_path / "bundle"
    with zipfile.ZipFile(path) as archive:
        archive.extractall(bundle)
    app = tmp_path / "App"
    app.mkdir()
    (app / "data").mkdir()
    (app / "data/state.json").write_bytes(b"uncertain, never retry")
    (app / "data/continue-prompt.md").write_bytes(b"My private prompt")
    (app / "custom-user-file.txt").write_bytes(b"Keep")
    (app / "CodexAutoContinuer.exe").write_bytes(b"old GUI")
    (app / "CodexAutoContinuer-CLI.exe").write_bytes(b"old CLI")
    (app / "_internal").mkdir()
    (app / "_internal/runtime.dll").write_bytes(b"old runtime")
    (app / "RELEASE-MANIFEST.json").write_text(json.dumps({"version": "0.5.0"}))
    job = tmp_path / "jobs" / ("a" * 32) / "job.json"
    job.parent.mkdir(parents=True)
    request = {"old_version": "0.5.0", "version": "0.6.0", "status": "staged"}
    updates.write_json(job, request)
    return update_install.Replacement(job, request, app, bundle / "CodexAutoContinuer"), manifest


@pytest.mark.parametrize("failure_at", [None, "CodexAutoContinuer-CLI.exe", "_internal"])
def test_replacement_and_partial_failure_preserve_runtime_and_user_files(tmp_path, monkeypatch, failure_at):
    replacement, manifest = transaction(tmp_path)
    app = replacement.app
    original = {p.relative_to(app).as_posix(): p.read_bytes() for p in app.rglob("*") if p.is_file()}
    old_copy = shutil.copy2
    old_tree = shutil.copytree
    def copy(source, target, *args, **kwargs):
        if Path(source).name == failure_at:
            raise OSError("Injected disk failure")
        return old_copy(source, target, *args, **kwargs)
    def tree(source, target, *args, **kwargs):
        if Path(source).name == failure_at:
            Path(target).mkdir()
            (Path(target) / "partial.dll").write_bytes(b"partial")
            raise OSError("Injected partial directory copy")
        return old_tree(source, target, *args, **kwargs)
    monkeypatch.setattr(shutil, "copy2", copy)
    monkeypatch.setattr(shutil, "copytree", tree)
    if failure_at:
        with pytest.raises(OSError):
            replacement.apply()
    else:
        replacement.apply()
        update_install.verify_bundle_code(app, manifest)
        assert (app / "CodexAutoContinuer.exe").read_bytes() == b"new GUI"
    replacement.restore()
    assert {p.relative_to(app).as_posix(): p.read_bytes() for p in app.rglob("*") if p.is_file()} == original
    assert replacement.request["status"] == "rolled_back"


def test_interrupted_backup_move_recovers_without_restoring_old_state(tmp_path, monkeypatch):
    replacement, _ = transaction(tmp_path)
    original_move = os.replace
    def fail_move(source, target):
        if Path(source).name == "_internal" and Path(target).parent == replacement.backup:
            raise OSError("Injected interrupted backup")
        return original_move(source, target)
    monkeypatch.setattr(os, "replace", fail_move)
    with pytest.raises(OSError):
        replacement.apply()
    (replacement.app / "data/state.json").write_bytes(b"newer obligation state")
    replacement.restore()
    assert (replacement.app / "data/state.json").read_bytes() == b"newer obligation state"
    assert (replacement.app / "CodexAutoContinuer.exe").read_bytes() == b"old GUI"


def test_quarantine_and_untested_notices_are_nonmodal_and_deduplicated(tmp_path, monkeypatch):
    from codex_auto_continuer import tray
    controller = tray.TrayController(tmp_path / "settings.toml")
    messages = []
    class Icon:
        def notify(self, body, title):
            messages.append(body)
    controller.icon = Icon()
    controller.notify_once("build:hash", "Untested stable build; continuing")
    controller.notify_once("build:hash", "Untested stable build; continuing")
    restarted = tray.TrayController(tmp_path / "settings.toml")
    restarted.icon = Icon()
    restarted.notify_once("build:hash", "Untested stable build; continuing")
    assert messages == ["Untested stable build; continuing"]
    assert "build:hash" not in (tmp_path / "notifications.json").read_text()


def test_compatible_build_updates_do_not_repeat_notice_for_the_same_contract(tmp_path, monkeypatch):
    from codex_auto_continuer import tray
    controller = tray.TrayController(tmp_path / "settings.toml")
    messages = []
    class Icon:
        def notify(self, body, title):
            messages.append(body)
    controller.icon = Icon()
    current = {"phase": "monitoring", "compatibility": {"status": "untested", "dispatch_allowed": True,
        "read_allowed": True, "contract_scope": "recovery", "policy": "balanced", "schema_sha256": "contract-a"}}
    monkeypatch.setattr(tray, "owns_monitor", lambda *_: True)
    monkeypatch.setattr(tray, "read_runtime", lambda *_: current)
    for build in ("first", "second", "third", "fourth"):
        current["compatibility"].update(cli_sha256=build, server_sha256=build)
        controller.refresh()
    assert len(messages) == 1 and "Balanced mode continues" in messages[0]
    current["compatibility"]["schema_sha256"] = "contract-b"
    controller.refresh()
    assert len(messages) == 2
    current["compatibility"].update(dispatch_allowed=False, policy="strict")
    controller.refresh()
    assert len(messages) == 3 and "Strict mode blocks" in messages[-1]


def test_release_download_does_not_block_monitor_controls(tmp_path, monkeypatch):
    import threading
    from codex_auto_continuer import tray
    controller = tray.TrayController(tmp_path / "settings.toml")
    started, release = threading.Event(), threading.Event()
    def download(*args):
        started.set()
        assert release.wait(2)
        return json.dumps({"status": "current"})
    monkeypatch.setattr(controller, "command", download)
    controller.check_updates(automatic=True)
    try:
        assert started.wait(1)
        controller.enqueue("stop", "stop")
        assert controller.actions.get_nowait() == ("stop", ("stop",))
    finally:
        controller.done.set()
        release.set()


def test_slow_response_has_a_total_deadline_not_just_a_socket_timeout(monkeypatch):
    class Response:
        url = "https://api.github.com/slow"
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read1(self, size):
            return b"x"
        def read(self, size):
            pytest.fail("read() can wait forever for a full block while a peer trickles bytes")
    class Opener:
        def open(self, *_args, **_kwargs):
            return Response()
    clock = iter(range(0, 100, 6))
    monkeypatch.setattr(updates.time, "monotonic", lambda: next(clock))
    client = updates.GitHub()
    client.opener = Opener()
    with pytest.raises(UpdateError, match="total deadline"):
        client.fetch(Response.url, 1000)


def test_health_failure_automatically_rolls_back_code_and_restarts_previous_build(tmp_path, monkeypatch):
    replacement, manifest = transaction(tmp_path)
    request, app, job = replacement.request, replacement.app, replacement.job
    config = app / "data/settings.toml"
    control = tmp_path / "control"
    monkeypatch.setattr(update_install, "control_dir", lambda: control)
    monkeypatch.setattr(update_install, "validate_job", lambda _: (request, app, config, replacement.bundle, manifest))
    monkeypatch.setattr(update_install, "preflight_processes", lambda *_: None)
    order = []
    monkeypatch.setattr(update_install, "stop_monitor", lambda *_: order.append("cycle_finished"))
    monkeypatch.setattr(update_install, "stop_tray", lambda *_: order.append("tray_stopped"))
    def health(app_root, settings, expected, *, start_monitor):
        assert start_monitor is False
        order.append(expected)
        if expected == "0.6.0":
            (app_root / "data/state.json").write_bytes(b"newer state, never restore an older copy")
            raise UpdateError("Injected startup failure")
    monkeypatch.setattr(update_install, "start_and_check", health)
    monkeypatch.setattr(update_install, "owns_monitor", lambda _: False)
    assert update_install.run_worker(job) == 1
    assert order == ["cycle_finished", "tray_stopped", "0.6.0", "0.5.0"]
    assert (app / "CodexAutoContinuer.exe").read_bytes() == b"old GUI"
    assert (app / "data/state.json").read_bytes() == b"newer state, never restore an older copy"
    assert updates.parse_json(job.read_bytes())["status"] == "rolled_back"


def test_disabling_auto_update_during_download_prevents_installation(tmp_path, monkeypatch):
    import threading
    from dataclasses import replace
    from codex_auto_continuer import tray
    controller = tray.TrayController(tmp_path / "settings.toml")
    started, release = threading.Event(), threading.Event()
    def download(*_):
        started.set()
        assert release.wait(2)
        return json.dumps({"status": "staged", "job": "fixture-job"})
    monkeypatch.setattr(controller, "command", download)
    controller.check_updates(automatic=True)
    assert started.wait(1)
    controller.cfg = replace(controller.cfg, auto_update=False)
    release.set()
    deadline = time.monotonic() + 2
    while controller._update_busy and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not controller._update_busy and controller.actions.empty()


def test_updating_wrong_tray_refuses_before_stopping_any_monitor(tmp_path, monkeypatch):
    monkeypatch.setattr(update_install, "process_path", lambda _: tmp_path / "OtherApp.exe")
    monkeypatch.setattr(update_install, "stop_monitor", lambda *_: pytest.fail("Preflight must refuse before stopping a process"))
    with pytest.raises(UpdateError, match="No monitoring process was stopped"):
        update_install.preflight_processes({"tray_pid": 42}, tmp_path / "App", tmp_path / "settings.toml")

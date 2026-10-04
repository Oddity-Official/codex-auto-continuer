"""Transport roundtrips and failure boundaries; no production-data access."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import zipfile

import pytest

SCRIPTS = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("project_workflow", SCRIPTS / "project-workflow.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def command(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, timeout=15, check=True)


def commit(root):
    command(root, "add", "--all")
    command(root, "-c", "user.name=Workflow Tests", "-c", "user.email=workflow@example.invalid",
            "commit", "--quiet", "-m", "fixture source")


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "project with spaces \u03b1"
    root.mkdir()
    for name in workflow.COMMON:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name.startswith("scripts/"):
            shutil.copyfile(SCRIPTS / Path(name).name, path)
        else:
            path.write_text("source", encoding="utf-8")
    (root / "scripts/manage-audits.py").write_bytes((SCRIPTS / "manage-audits.py").read_bytes())
    (root / ".gitignore").write_text(".data/*\n!.data/.gitkeep\nfixture-codex-handoff.zip\nCheckpoints/\n.project-workflow.lock\nDocs/Audits/.maintenance.json\nDocs/Audits/.audit.lock\n__pycache__/\n", encoding="utf-8")
    (root / "CHAT-MANIFEST.md").write_text("Checkpoint: local-bootstrap\n", encoding="utf-8")
    (root / "CODEX-MANIFEST.md").write_text("ChatGPT base checkpoint: local-bootstrap\n", encoding="utf-8")
    (root / workflow.CONFIG).write_text(json.dumps({
        "version": 1, "name": "fixture", "required_files": ["src/tool.py"],
        "exclude_directories": [], "exclude_files": [], "windows_python": "3.13",
    }), encoding="utf-8")
    (root / "src").mkdir()
    (root / "src/tool.py").write_bytes(b"old source\r\n")
    (root / ".data").mkdir()
    (root / ".data/.gitkeep").write_bytes(b"")
    command(root, "init", "--quiet")
    commit(root)
    runtime = root / ".data/private.sqlite3"
    runtime.write_bytes(b"local database and telemetry must stay local")
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    monkeypatch.setattr(workflow.tempfile, "tempdir", str(temporary))
    for key in ("TEMP", "TMP", "TMPDIR"):
        monkeypatch.setenv(key, str(temporary))
    return root


def checkpoint(project, tmp_path):
    donor = tmp_path / "donor"
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(project), str(donor)],
                   capture_output=True, timeout=15, check=True)
    (donor / "CHAT-MANIFEST.md").write_text("Checkpoint: v001\n", encoding="utf-8")
    (donor / "src/tool.py").write_bytes(b"new source\r\n")
    archive = workflow.build(donor, "checkpoint", "v001")
    # A checkpoint is deliberately outside the recipient checkout.
    return archive


def test_handoff_is_self_contained_and_preserves_bytes(project):
    audit = project / "Docs/Audits/2026-09-30"
    audit.mkdir()
    (audit / "AUDIT.md").write_text("observations")
    (audit / "fixture.txt").write_bytes(b"source\r\n")
    output = workflow.build(project)
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert not any(n.startswith((".data/", ".git/", "Checkpoints/")) for n in names)
        assert "Docs/Audits/.maintenance.json" in names
        assert "scripts/manage-audits.py" in names
        assert "scripts/project-workflow.py" in names
        assert archive.read("Docs/Audits/2026-09-30/fixture.txt") == b"source\r\n"
        manifest = json.loads(archive.read("_HANDOFF_MANIFEST.json"))
        assert manifest["kind"] == "handoff"
        assert manifest["checkpoint"] == "local-bootstrap"
        assert archive.testzip() is None


def test_source_export_excludes_portable_data_settings_and_env_variants(project):
    actual = json.loads((SCRIPTS.parent / workflow.CONFIG).read_text(encoding="utf-8"))
    config = workflow.settings(project)
    for key in ("exclude_directories", "exclude_files"):
        config[key] = actual[key]
    (project / workflow.CONFIG).write_text(json.dumps(config), encoding="utf-8")
    private_names = ["data/state.json", "data/telemetry.jsonl", "settings.toml",
                     "continue-prompt.md", "telemetry.jsonl.9.gz", "updates.jsonl.9.gz", "update-status.json",
                     "notifications.json", "tray-ready.json", ".cac-updates/job/recovery.json", ".env.local", "nested/.env.production"]
    for name in private_names:
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"private export canary")
    archive_path = workflow.build(project)
    with zipfile.ZipFile(archive_path) as archive:
        assert not set(private_names) & set(archive.namelist())
        assert all(b"private export canary" not in archive.read(name) for name in archive.namelist())
        assert archive.read("src/tool.py") == b"old source\r\n"


def test_git_ignores_runtime_and_env_files_but_keeps_public_sources(project):
    shutil.copyfile(SCRIPTS.parent / ".gitignore", project / ".gitignore")
    private_names = ["data/state.json", "App/data/settings.toml", ".data/runtime/telemetry.jsonl",
                     "settings.toml", "continue-prompt.md", "telemetry.jsonl.1.gz",
                     "updates.jsonl.1.gz", "update-status.json", "notifications.json", "tray-ready.json",
                     ".cac-updates/job/recovery.json", ".env.local", "nested/.env.production"]
    result = subprocess.run(["git", "-C", str(project), "check-ignore", "-z", "--stdin"],
                            input="\0".join(private_names + ["src/tool.py", "Docs/README.md"]).encode(),
                            capture_output=True, check=True, timeout=15)
    assert set(result.stdout.decode().rstrip("\0").split("\0")) == set(private_names)


def test_checkpoint_preview_and_import_preserve_runtime_and_backup(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    before = (project / "src/tool.py").read_bytes()
    assert workflow.import_checkpoint(project, archive, preview=True) is None
    assert (project / "src/tool.py").read_bytes() == before
    backup = workflow.import_checkpoint(project, archive)
    assert (backup / "src/tool.py").read_bytes() == before
    assert (project / "src/tool.py").read_bytes() == b"new source\r\n"
    assert (project / ".data/private.sqlite3").read_bytes() == b"local database and telemetry must stay local"
    assert (project / ".data/.gitkeep").exists()
    assert "verification is pending" in (project / "CODEX-MANIFEST.md").read_text().lower()
    assert (project / "Docs/Audits/.maintenance.json").is_file()


def test_checkpoint_identity_cannot_be_reused(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    before = archive.read_bytes()
    with pytest.raises(workflow.WorkflowError, match="already exists"):
        workflow.build(archive.parents[1], "checkpoint", "v001")
    assert archive.read_bytes() == before


def test_checkpoint_number_cannot_go_backwards_from_imported_base(project):
    (project / "CHAT-MANIFEST.md").write_text("Checkpoint: v001\n")
    (project / "CODEX-MANIFEST.md").write_text("ChatGPT base checkpoint: v002\n")
    with pytest.raises(workflow.WorkflowError, match="greater than"):
        workflow.build(project, "checkpoint", "v001")
    assert not (project / "Checkpoints").exists()


def test_handoff_is_not_an_importable_checkpoint(project):
    handoff = workflow.build(project)
    outside = project.parent / "received.zip"
    shutil.copyfile(handoff, outside)
    with pytest.raises(workflow.WorkflowError, match="excluded state"):
        workflow.import_checkpoint(project, outside)


def test_dirty_project_refuses_import(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    (project / "src/tool.py").write_bytes(b"uncommitted")
    with pytest.raises(workflow.WorkflowError, match="local changes"):
        workflow.import_checkpoint(project, archive)
    assert (project / "src/tool.py").read_bytes() == b"uncommitted"


def test_untracked_conflict_refuses_import(project, tmp_path):
    (project / ".gitignore").write_text((project / ".gitignore").read_text() + "local.txt\n")
    commit(project)
    donor = tmp_path / "donor"
    archive = checkpoint(project, tmp_path)
    (donor / "local.txt").write_bytes(b"checkpoint source")
    (donor / "CHAT-MANIFEST.md").write_text("Checkpoint: v002\n")
    archive = workflow.build(donor, "checkpoint", "v002")
    (project / "local.txt").write_bytes(b"local ignored data")
    with pytest.raises(workflow.WorkflowError, match="untracked/ignored"):
        workflow.import_checkpoint(project, archive)
    assert (project / "local.txt").read_bytes() == b"local ignored data"


def test_checksum_corruption_cannot_replace_source(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(corrupt, "w") as changed:
        for info in original.infolist():
            changed.writestr(info, b"tampered" if info.filename == "src/tool.py" else original.read(info))
    with pytest.raises(workflow.WorkflowError, match="checksum mismatch"):
        workflow.import_checkpoint(project, corrupt)
    assert (project / "src/tool.py").read_bytes() == b"old source\r\n"


def test_checkpoint_cannot_smuggle_files_excluded_by_its_own_profile(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    conflict = tmp_path / "profile-conflict.zip"
    with zipfile.ZipFile(archive) as original:
        payloads = {info.filename: original.read(info) for info in original.infolist()}
    config = json.loads(payloads[workflow.CONFIG])
    config["exclude_files"] = ["private.txt"]
    payloads[workflow.CONFIG] = json.dumps(config).encode()
    payloads["private.txt"] = b"must never be imported"
    manifest = json.loads(payloads["_CHECKPOINT_MANIFEST.json"])
    for name in (workflow.CONFIG, "private.txt"):
        manifest["files"][name] = {"size": len(payloads[name]), "sha256": hashlib.sha256(payloads[name]).hexdigest()}
    payloads["_CHECKPOINT_MANIFEST.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(conflict, "w") as changed:
        for name, data in payloads.items():
            changed.writestr(name, data)
    with pytest.raises(workflow.WorkflowError, match="own declared export exclusions"):
        workflow.import_checkpoint(project, conflict)
    assert not (project / "private.txt").exists()
    assert (project / "src/tool.py").read_bytes() == b"old source\r\n"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/drive", "a\\b", "CON.txt", "a//b", "a/../b", "bad. ", "COM\u00b9.txt"])
def test_unsafe_archive_names_are_rejected_before_extraction(project, tmp_path, name):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr(name, b"unsafe")
    with pytest.raises(workflow.WorkflowError):
        workflow.import_checkpoint(project, archive)
    assert (project / "src/tool.py").read_bytes() == b"old source\r\n"


def test_linked_and_case_conflicting_archive_entries_are_rejected(project, tmp_path):
    archive = tmp_path / "unsafe.zip"
    info = zipfile.ZipInfo("linked")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr(info, "outside")
    with pytest.raises(workflow.WorkflowError, match="linked/special"):
        workflow.import_checkpoint(project, archive)
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr("Foo", "file")
        file.writestr("foo/child", "conflict")
    with pytest.raises(workflow.WorkflowError, match="file/directory conflict"):
        workflow.import_checkpoint(project, archive)


@pytest.mark.parametrize("blocker", [".audit.lock", ".maintenance.json"])
def test_retention_failure_keeps_previous_handoff(project, blocker):
    output = workflow.build(project)
    before = output.read_bytes()
    (project / "Docs/Audits" / blocker).write_text("invalid or busy")
    with pytest.raises(Exception, match="locked|Invalid retention state"):
        workflow.build(project)
    assert output.read_bytes() == before


@pytest.mark.skipif(os.name != "nt", reason="Native PowerShell wrappers")
def test_native_wrapper_packages_project_with_space_path(project):
    result = subprocess.run(["pwsh", "-NoProfile", "-File", str(project / "scripts/pack-codex-handoff.ps1")],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    assert str(project) in result.stdout
    assert (project / "fixture-codex-handoff.zip").is_file()


@pytest.mark.skipif(os.name != "nt", reason="Native PowerShell wrappers")
def test_native_import_wrapper_preview_and_replace(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    arguments = ["pwsh", "-NoProfile", "-File", str(project / "scripts/import-checkpoint.ps1"),
                 "-ArchivePath", str(archive)]
    preview = subprocess.run([*arguments, "-Preview"], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert preview.returncode == 0, preview.stderr
    assert str(project) in preview.stdout
    assert (project / "src/tool.py").read_bytes() == b"old source\r\n"
    imported = subprocess.run(arguments, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert imported.returncode == 0, imported.stderr
    assert (project / "src/tool.py").read_bytes() == b"new source\r\n"


def test_monorepo_import_preserves_unrelated_dirty_sibling(project, tmp_path):
    archive = checkpoint(project, tmp_path)
    repo = tmp_path / "monorepo"
    recipient = repo / "tools/fixture"
    shutil.copytree(project, recipient, ignore=shutil.ignore_patterns(".git"))
    sibling = repo / "other.txt"
    sibling.write_bytes(b"tracked sibling")
    command(repo, "init", "--quiet")
    commit(repo)
    sibling.write_bytes(b"unrelated user change")
    workflow.import_checkpoint(recipient, archive)
    assert sibling.read_bytes() == b"unrelated user change"
    assert (recipient / "src/tool.py").read_bytes() == b"new source\r\n"
    assert (recipient / ".data/private.sqlite3").read_bytes() == b"local database and telemetry must stay local"


def test_import_removes_only_obsolete_owned_source(project, tmp_path):
    obsolete = project / "src/obsolete.py"
    obsolete.write_bytes(b"completed source")
    commit(project)
    checkpoint(project, tmp_path)
    donor = tmp_path / "donor"
    (donor / "src/obsolete.py").unlink()
    (donor / "CHAT-MANIFEST.md").write_text("Checkpoint: v002\n")
    archive = workflow.build(donor, "checkpoint", "v002")
    backup = workflow.import_checkpoint(project, archive)
    assert not obsolete.exists()
    assert (backup / "src/obsolete.py").read_bytes() == b"completed source"


def test_archive_size_budget_fails_before_extracting(project, tmp_path, monkeypatch):
    archive = tmp_path / "oversized.zip"
    with zipfile.ZipFile(archive, "w") as file:
        file.writestr("payload", b"exceeds tiny test budget")
    monkeypatch.setattr(workflow, "LIMIT", 1)
    with pytest.raises(workflow.WorkflowError, match="input-size safety limit"):
        workflow.import_checkpoint(project, archive)
    assert (project / "src/tool.py").read_bytes() == b"old source\r\n"

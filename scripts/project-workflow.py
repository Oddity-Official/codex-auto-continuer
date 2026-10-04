"""Build verified source transports and safely import canonical checkpoints."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ".project-workflow.json"
LOCK = ".project-workflow.lock"
LIMIT = 128 * 1024 * 1024
COMMON = ["AGENTS.md", "README.md", "CHAT-MANIFEST.md", "CODEX-MANIFEST.md", CONFIG,
          "Docs/README.md", "Docs/Audits/README.md", "scripts/project-workflow.py", "scripts/manage-audits.py",
          "scripts/pack-codex-handoff.ps1", "scripts/import-checkpoint.ps1", "scripts/run-project-command.ps1",
          "scripts/verify-windows.ps1"]
CACHE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
              ".ruff_cache", ".mypy_cache", ".idea", ".vs"}
LOCAL_DIRS = {"target", "build", "dist", ".data", "Checkpoints", "Handoffs"}
SKIP_FILES = {LOCK, ".audit.lock", ".DS_Store", "Thumbs.db", ".env",
              "_HANDOFF_MANIFEST.json", "_CHECKPOINT_MANIFEST.json"}
SKIP_SUFFIXES = {".tmp", ".bak", ".pyc", ".pyo", ".profraw", ".profdata"}
SLUG = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}\Z")


class WorkflowError(Exception):
    pass


def safe_name(name):
    parts = PurePosixPath(name).parts
    if not parts or PurePosixPath(name).as_posix() != name or "\\" in name:
        raise WorkflowError(f"Unsafe project/archive path: {name!r}.")
    for part in parts:
        if part in {".", ".."} or part.endswith((".", " ")) or re.search(r'[\x00-\x1f<>:"|?*]', part):
            raise WorkflowError(f"Unsafe project/archive path: {name!r}.")
        if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9\u00b9\u00b2\u00b3]|LPT[1-9\u00b9\u00b2\u00b3])(?:\..*)?", part):
            raise WorkflowError(f"Reserved Windows path: {name!r}.")
    if PurePosixPath(name).is_absolute():
        raise WorkflowError(f"Absolute project/archive path: {name!r}.")
    return name


def plain(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise WorkflowError(f"Refusing linked/reparse path: {path}.")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise WorkflowError(f"Unsupported filesystem entry: {path}.")


def target(root, name):
    safe_name(name)
    root = root.absolute()
    path = root.joinpath(*PurePosixPath(name).parts)
    if not path.is_relative_to(root) or path == root:
        raise WorkflowError(f"Target escapes project: {path}.")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            plain(item)
            if item != path and not item.is_dir():
                raise WorkflowError(f"File blocks an import/output parent directory: {item}.")
    return path


def settings(root):
    path = target(root, CONFIG)
    value = json.loads(path.read_text(encoding="utf-8"))
    if set(value) != {"version", "name", "required_files", "exclude_directories", "exclude_files", "windows_python"}:
        raise WorkflowError(f"Invalid workflow configuration keys: {path}.")
    if value["version"] != 1 or not SLUG.fullmatch(value["name"]):
        raise WorkflowError(f"Invalid workflow version or project name: {path}.")
    for key in ("required_files", "exclude_directories", "exclude_files"):
        if not isinstance(value[key], list) or any(not isinstance(p, str) for p in value[key]):
            raise WorkflowError(f"{key} must be a list of literal project-relative paths.")
        for name in value[key]:
            safe_name(name)
    if not re.fullmatch(r"3(?:\.\d+)?", value["windows_python"]):
        raise WorkflowError("windows_python must be 3 or a specific Python 3 minor, such as 3.13.")
    return value


def excluded(name, config):
    parts = PurePosixPath(name).parts
    lowered = [p.casefold() for p in parts]
    if any(p in {d.casefold() for d in CACHE_DIRS} or p.endswith(".egg-info") for p in lowered):
        return True
    if lowered[0] in {d.casefold() for d in LOCAL_DIRS}:
        return True
    if len(parts) > 1 and lowered[:2] in [["reference", "toolchains"], ["reference", "dependencies"]]:
        return True
    prefixes = config["exclude_directories"]
    if any(name.casefold() == p.casefold() or name.casefold().startswith(p.casefold() + "/") for p in prefixes):
        return True
    if name.casefold() in {p.casefold() for p in config["exclude_files"]}:
        return True
    if parts[-1].casefold() in {p.casefold() for p in SKIP_FILES}:
        return True
    if lowered[-1].startswith(".env."):
        return True
    if len(parts) == 1 and lowered[-1].startswith(("telemetry.jsonl", "tray.jsonl", "updates.jsonl")):
        return True
    if lowered[-1] == f"{config['name']}-codex-handoff.zip".casefold():
        return True
    return Path(parts[-1]).suffix.casefold() in SKIP_SUFFIXES


def collect(root, config):
    plain(root)
    files, folded = {}, set()
    pending = [root]
    while pending:
        for child in sorted(pending.pop().iterdir()):
            name = child.relative_to(root).as_posix()
            if excluded(name, config):
                continue
            safe_name(name)
            plain(child)
            if child.is_dir():
                pending.append(child)
            else:
                if name.casefold() in folded:
                    raise WorkflowError(f"Case-insensitive path collision: {name}.")
                folded.add(name.casefold())
                files[name] = child
    for name in COMMON + config["required_files"]:
        if name not in files:
            raise WorkflowError(f"Project anchor missing or excluded: {name}.")
    return dict(sorted(files.items()))


def git(root, *arguments, required=True):
    try:
        result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        if not required:
            return None
        raise WorkflowError(f"Cannot inspect Git safely: {error}.") from error
    if result.returncode:
        if not required:
            return None
        raise WorkflowError(f"Git inspection failed: {result.stderr.decode('utf-8', errors='replace')}")
    return result.stdout


def checkpoint_identity(text):
    matches = re.findall(r"^Checkpoint:\s*(\S+)\s*$", text, re.MULTILINE)
    if len(matches) != 1 or not SLUG.fullmatch(matches[0]):
        raise WorkflowError("CHAT-MANIFEST.md must contain exactly one Checkpoint: identifier.")
    return matches[0]


def verify_checkpoint_sequence(root, name, identity):
    number = re.fullmatch(r"v(\d+)(?:[._-].*)?", identity)
    if not number or int(number[1]) < 1:
        raise WorkflowError("Canonical checkpoint IDs must start with a positive v-number, such as v001 or v001-description.")
    bases = re.findall(r"^ChatGPT base checkpoint:\s*(\S+)", target(root, "CODEX-MANIFEST.md").read_text(encoding="utf-8"), re.MULTILINE)
    if len(bases) != 1:
        raise WorkflowError("CODEX-MANIFEST.md must identify exactly one imported ChatGPT base checkpoint.")
    prior = []
    if bases[0] != "local-bootstrap":
        base = re.fullmatch(r"v(\d+)(?:[._-].*)?", bases[0])
        if not base:
            raise WorkflowError("Cannot verify checkpoint sequence: Codex base must be local-bootstrap or a v-number ID.")
        prior.append(int(base[1]))
    directory = target(root, "Checkpoints")
    if directory.exists():
        prefix = f"{name}-checkpoint-"
        for child in directory.iterdir():
            if child.name.startswith(prefix) and child.suffix == ".zip":
                match = re.fullmatch(r"v(\d+)(?:[._-].*)?", child.stem[len(prefix):])
                if match:
                    prior.append(int(match[1]))
    if prior and int(number[1]) <= max(prior):
        raise WorkflowError("Checkpoint number must be greater than the imported base and every existing checkpoint number.")


def audit_module():
    spec = importlib.util.spec_from_file_location("audit_retention", Path(__file__).with_name("manage-audits.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def workflow_lock(root):
    path = target(root, LOCK)
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise WorkflowError(f"Workflow is locked at {path}. Confirm its PID has stopped before removing a stale lock.") from error
    try:
        with os.fdopen(handle, "w", encoding="ascii") as file:
            file.write(f"pid={os.getpid()}\n")
        yield
    finally:
        path.unlink()


def build(root, kind="handoff", checkpoint=None):
    config = settings(root)
    identity = checkpoint_identity(target(root, "CHAT-MANIFEST.md").read_text(encoding="utf-8"))
    if kind == "checkpoint":
        if checkpoint != identity or checkpoint == "local-bootstrap":
            raise WorkflowError("Set CHAT-MANIFEST.md to the new canonical checkpoint ID before building it.")
        destination = target(root, f"Checkpoints/{config['name']}-checkpoint-{identity}.zip")
        if destination.exists():
            raise WorkflowError(f"Checkpoint already exists; identities are never reused: {destination}.")
        verify_checkpoint_sequence(root, config["name"], identity)
    else:
        destination = target(root, f"{config['name']}-codex-handoff.zip")
    with workflow_lock(root):
        config = settings(root)
        collect(root, config)  # Fail before retention mutates an incomplete project.
        audit_module().maintain(root / "Docs/Audits")
        files = collect(root, config)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".transport-", suffix=".tmp", dir=destination.parent)
        os.close(descriptor)
        records = {}
        head = git(root, "rev-parse", "HEAD", required=False)
        status = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".", required=False)
        manifest = {"version": 1, "kind": kind, "project": config["name"], "checkpoint": identity,
                    "created_utc": datetime.now(timezone.utc).isoformat(),
                    "git_head": head.decode().strip() if head else None,
                    "git_dirty": bool(status) if status is not None else None, "files": records}
        manifest_name = "_HANDOFF_MANIFEST.json" if kind == "handoff" else "_CHECKPOINT_MANIFEST.json"
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                total = 0
                for name, path in files.items():
                    data = path.read_bytes()
                    total += len(data)
                    if total > LIMIT:
                        raise WorkflowError("Source transport exceeds 128 MiB. Remove redundant output or explicitly revise the transport policy.")
                    records[name] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    archive.writestr(name, data)
                archive.writestr(manifest_name, json.dumps(manifest, indent=2) + "\n")
            with zipfile.ZipFile(temporary) as archive:
                verify_archive(archive, config, kind)
            if set(collect(root, config)) != set(files):
                raise WorkflowError("Project file set changed during packaging. Stop edits and rerun.")
            for name, path in files.items():
                if hashlib.sha256(path.read_bytes()).hexdigest() != records[name]["sha256"]:
                    raise WorkflowError(f"Source changed during packaging: {name}. Stop edits and rerun.")
            if kind == "checkpoint":
                # Exclusive creation also protects against another process using the same ID.
                created = False
                try:
                    with destination.open("xb") as output, open(temporary, "rb") as source:
                        created = True
                        shutil.copyfileobj(source, output)
                except OSError:
                    if created:
                        destination.unlink()
                    raise
            else:
                os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
    print(f"Verified {len(records)} files. {kind.title()}: {destination}")
    print(f"SHA-256: {hashlib.sha256(destination.read_bytes()).hexdigest()}")
    return destination


def verify_archive(archive, config, kind="checkpoint"):
    files, seen, total = {}, set(), 0
    manifest_name = "_CHECKPOINT_MANIFEST.json" if kind == "checkpoint" else "_HANDOFF_MANIFEST.json"
    if len(archive.infolist()) > 10000:
        raise WorkflowError("Archive exceeds the 10,000-entry safety limit.")
    for info in archive.infolist():
        name = safe_name(info.filename[:-1] if info.is_dir() else info.filename)
        if name.casefold() in seen:
            raise WorkflowError(f"Duplicate case-insensitive archive path: {name}.")
        seen.add(name.casefold())
        mode = stat.S_IFMT(info.external_attr >> 16)
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or info.external_attr & 0x400:
            raise WorkflowError(f"Archive contains linked/special entry: {name}.")
        if info.is_dir():
            if excluded(name, config):
                raise WorkflowError(f"Archive contains excluded directory: {name}.")
            continue
        if name != manifest_name and excluded(name, config):
            raise WorkflowError(f"Archive contains excluded state: {name}.")
        total += info.file_size
        if total > LIMIT or len(seen) > 10000:
            raise WorkflowError("Archive exceeds 128 MiB or 10,000-entry safety limit.")
        files[name] = info
    folded_files = {name.casefold() for name in files}
    for name in files:
        if any(parent.as_posix().casefold() in folded_files for parent in PurePosixPath(name).parents if parent.as_posix() != "."):
            raise WorkflowError(f"Archive file/directory conflict: {name}.")
    if manifest_name not in files:
        raise WorkflowError(f"Missing {manifest_name}. Use a verified {kind} built by project-workflow.py.")
    manifest = json.loads(archive.read(manifest_name))
    if manifest.get("version") != 1 or manifest.get("kind") != kind or manifest.get("project") != config["name"]:
        raise WorkflowError("Transport manifest version, role or project does not match.")
    records = manifest.get("files")
    if not isinstance(records, dict) or set(records) != set(files) - {manifest_name}:
        raise WorkflowError("Transport manifest does not describe the exact file set.")
    for name, record in records.items():
        data = archive.read(name)
        if not isinstance(record, dict) or record.get("size") != len(data) or record.get("sha256") != hashlib.sha256(data).hexdigest():
            raise WorkflowError(f"Transport checksum mismatch: {name}.")
    for name in COMMON + config["required_files"] + ["Docs/Audits/.maintenance.json"]:
        if name not in records:
            raise WorkflowError(f"Checkpoint missing project anchor: {name}.")
    if manifest.get("checkpoint") != checkpoint_identity(archive.read("CHAT-MANIFEST.md").decode("utf-8")):
        raise WorkflowError("Checkpoint identity disagrees with CHAT-MANIFEST.md.")
    return manifest, files


def import_checkpoint(root, archive_path, preview=False):
    config = settings(root)
    archive_path = archive_path.absolute()
    plain(archive_path)
    if archive_path.stat().st_size > 2 * LIMIT:
        raise WorkflowError("Checkpoint ZIP exceeds the 256 MiB input-size safety limit.")
    if archive_path.is_relative_to(root.absolute()):
        raise WorkflowError("Import checkpoints from outside the checkout, not from a file that import may replace.")
    dirty = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
    if dirty:
        raise WorkflowError("Project has local changes. Commit or preserve them before importing; unrelated sibling changes are allowed.")
    tracked = {name.decode("utf-8") for name in git(root, "ls-files", "-z", "--", ".").split(b"\0") if name}
    if not tracked or any(name not in tracked for name in COMMON):
        raise WorkflowError("Commit the project workflow before importing a checkpoint.")
    with workflow_lock(root), zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory(prefix="project-checkpoint-stage-") as temporary:
        manifest, entries = verify_archive(archive, config)
        incoming = set(entries) - {"_CHECKPOINT_MANIFEST.json"}
        stage = Path(temporary)
        for name in incoming:
            destination = target(stage, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
        incoming_config = settings(stage)
        if incoming_config["name"] != config["name"]:
            raise WorkflowError("Checkpoint workflow configuration names another project.")
        if set(collect(stage, incoming_config)) != incoming:
            raise WorkflowError("Checkpoint file set conflicts with its own declared export exclusions.")
        module = audit_module()
        module.inventory(stage / "Docs/Audits")
        module.read_state(stage / "Docs/Audits", datetime.now(timezone.utc))
        state_name = "Docs/Audits/.maintenance.json"
        existing_state = target(root, state_name)
        module.inventory(root / "Docs/Audits")
        module.read_state(root / "Docs/Audits", datetime.now(timezone.utc))
        owned = {name for name in tracked if not excluded(name, config)} | ({state_name} if existing_state.exists() else set())
        for name in owned | incoming:
            path = target(root, name)
            if path.exists() and not path.is_file():
                raise WorkflowError(f"File/directory import conflict: {path}.")
            if name in incoming and path.exists() and name not in owned:
                raise WorkflowError(f"Refusing to overwrite untracked/ignored data: {path}.")
        removed = owned - incoming
        changed = {name for name in incoming if not target(root, name).exists() or
                   target(root, name).read_bytes() != target(stage, name).read_bytes()}
        print(f"Destination: {root}")
        print(f"Checkpoint {manifest['checkpoint']}: {len(incoming)} files; {len(changed)} new/changed, {len(removed)} removed.")
        if preview:
            print("Preview only; project files and retention state unchanged.")
            return None
        backup = Path(tempfile.mkdtemp(prefix=f"{config['name']}-checkpoint-backup-"))
        for name in owned:
            source = target(root, name)
            if source.is_file():
                destination = target(backup, name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
                if destination.read_bytes() != source.read_bytes():
                    raise WorkflowError(f"Backup verification failed: {name}. Checkout unchanged; backup at {backup}.")
        print(f"Verified recovery backup: {backup}")
        try:
            for name in sorted(changed):
                destination = target(root, name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target(stage, name), destination)
                if destination.read_bytes() != target(stage, name).read_bytes():
                    raise WorkflowError(f"Imported file verification failed: {name}.")
            for name in sorted(removed):
                target(root, name).unlink()
            target(root, "CODEX-MANIFEST.md").write_text(
                f"# Codex manifest\n\nChatGPT base checkpoint: {manifest['checkpoint']}\n"
                f"Updated: {datetime.now(timezone.utc).date()}\n\n## Local work\n\n"
                "- Imported the canonical checkpoint and verified every source checksum.\n\n"
                "## Verification\n\nNative verification is pending. Run the project gate before committing or handing off.\n",
                encoding="utf-8", newline="\n")
        except (OSError, WorkflowError) as error:
            raise WorkflowError(f"Import stopped during replacement: {error}. Restore affected paths from {backup}; do not delete that backup.") from error
        print("Import complete. Native verification is required before commit; local runtime/cache directories were not touched.")
        return backup


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("handoff", help="Refresh the stable verified Codex source ZIP.")
    checkpoint = sub.add_parser("checkpoint", help="Create a never-overwritten ChatGPT checkpoint.")
    checkpoint.add_argument("--id", required=True)
    importer = sub.add_parser("import-checkpoint", help="Import into a clean Git project; retain a recovery backup.")
    importer.add_argument("archive", type=Path)
    importer.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "import-checkpoint":
            import_checkpoint(ROOT, args.archive, args.preview)
        else:
            build(ROOT, "checkpoint" if args.command == "checkpoint" else "handoff", getattr(args, "id", None))
    except Exception as error:
        print(f"Project workflow failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

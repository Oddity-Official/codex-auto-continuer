"""Read-only privacy inventory; report locations and categories, never secret values."""
from __future__ import annotations

import hashlib
import io
import json
import marshal
import os
import re
import subprocess
import tempfile
import types
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
RULES = {
    "credential-shaped value": re.compile(rb"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|Bearer [A-Za-z0-9._-]{24,})"),
}
FORBIDDEN = {"App", ".data", ".venv", "node_modules", "__pycache__"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout


def scan(body, location):
    findings = []
    for kind, pattern in RULES.items():
        for hit in pattern.finditer(body):
            findings.append({"location": location, "kind": kind,
                             "fingerprint": hashlib.sha256(hit.group()).hexdigest()[:12]})
    markers = [Path.home().name, str(ROOT), ROOT.as_posix()]
    for marker in markers:
        for encoding in ("utf-8", "utf-16-le"):
            if marker.encode(encoding).lower() in body.lower():
                findings.append({"location": location, "kind": "local profile or project path", "encoding": encoding})
    return findings


def code_paths(code):
    if isinstance(code, types.CodeType):
        yield code.co_filename
        for value in code.co_consts:
            yield from code_paths(value)


def inspect_zip(archive, location, matches, filenames, counts, temporary):
    assert archive.testzip() is None
    for name in archive.namelist():
        body = archive.read(name)
        label = f"{location}: {name}"
        matches.extend(scan(body, label))
        if name.endswith(".pyc"):
            filenames.update(code_paths(marshal.loads(body[16:])))
            counts["bytecodeModules"] += 1
        elif name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(body)) as nested:
                inspect_zip(nested, label, matches, filenames, counts, temporary)
        elif name.endswith(".exe"):
            from PyInstaller.archive.readers import CArchiveReader

            executable = temporary / Path(name).name
            executable.write_bytes(body)
            reader = CArchiveReader(str(executable))
            counts["executables"] += 1
            for entry, metadata in reader.toc.items():
                content = reader.extract(entry)
                matches.extend(scan(content, f"{label}: {entry}"))
                if metadata[-1] in {"s", "m", "M"}:
                    filenames.update(code_paths(marshal.loads(content)))
                    counts["bytecodeModules"] += 1
                elif metadata[-1] == "z":
                    embedded = reader.open_embedded_archive(entry)
                    for module in embedded.toc:
                        content = embedded.extract(module, raw=True)
                        if content is None:
                            continue
                        matches.extend(scan(content, f"{label}: {entry}: {module}"))
                        if embedded.toc[module][0] in {0, 1}:
                            filenames.update(code_paths(marshal.loads(content)))
                            counts["bytecodeModules"] += 1


def main():
    commits = git("rev-list", "--all").decode().splitlines()
    blobs = {}
    forbidden = []
    for commit in commits:
        for row in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
            if not row:
                continue
            metadata, path = row.split(b"\t", 1)
            mode, kind, identity = metadata.split()
            name = path.decode("utf-8")
            if set(Path(name).parts) & FORBIDDEN or name.endswith((".jsonl", ".key", ".env")):
                forbidden.append({"commit": commit[:7], "path": name})
            if kind == b"blob":
                blobs.setdefault(identity.decode(), set()).add(name)
    findings = []
    for identity, names in blobs.items():
        findings.extend(scan(git("cat-file", "blob", identity), f"Git blob {identity[:8]}: {sorted(names)[0]}"))
    working_findings = []
    working_files = 0
    broken_links = []
    for name in git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0"):
        path = ROOT / name
        if name and path.is_file():
            working_files += 1
            working_findings.extend(scan(path.read_bytes(), f"working tree: {name}"))
            if path.suffix == ".md":
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                    link = link.split("#", 1)[0]
                    if link and "://" not in link and not link.startswith("mailto:"):
                        if not (path.parent / unquote(link)).exists():
                            broken_links.append({"document": name, "target": link})
    authors = git("log", "--all", "--format=%ae%n%ce").decode().splitlines()
    private_emails = sorted({email for email in authors if not email.endswith("@users.noreply.github.com")})
    artifacts = []
    paths = sorted((ROOT / "dist").glob("*0.3.0*"))
    handoff = ROOT / "codex-auto-continuer-codex-handoff.zip"
    if handoff.exists():
        paths.append(handoff)
    for path in paths:
        with tempfile.TemporaryDirectory(prefix="cac-publication-") as temporary, zipfile.ZipFile(path) as archive:
            matches = []
            filenames = set()
            counts = {"executables": 0, "bytecodeModules": 0}
            inspect_zip(archive, path.name, matches, filenames, counts, Path(temporary))
            personal_code_paths = [name for name in sorted(filenames)
                                   if str(ROOT).lower() in name.lower() or str(Path.home()).lower() in name.lower()]
            artifacts.append({"artifact": path.name, "entries": len(archive.namelist()),
                              **counts,
                              "findings": matches, "compiledPersonalPaths": personal_code_paths,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    print(json.dumps({"commits": len(commits), "uniqueBlobs": len(blobs), "historyFindings": findings,
                      "workingFiles": working_files, "workingFindings": working_findings,
                      "brokenMarkdownLinks": broken_links,
                      "runtimeFilesInHistory": forbidden, "privateAuthorEmailCount": len(private_emails),
                      "artifacts": artifacts}, indent=2))


if __name__ == "__main__":
    main()

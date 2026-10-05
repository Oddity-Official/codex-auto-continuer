"""Fetch a checksum-verified official Windows CLI package for isolated CI probes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tarfile
import time
import urllib.request
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024 * 1024


def extract_package(archive: Path, destination: Path):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        seen = set()
        total = 0
        if len(members) > 10000:
            raise ValueError("Official package exceeds the 10,000-entry probe limit.")
        for member in members:
            path = Path(member.name)
            if (PurePosixPath(member.name).is_absolute() or path.anchor or ".." in path.parts or ":" in member.name or "\\" in member.name or
                member.issym() or member.islnk() or not (member.isfile() or member.isdir())):
                raise ValueError("Official package contains an unsafe archive entry.")
            key = path.as_posix().casefold().rstrip("/")
            if key in seen:
                raise ValueError("Official package contains duplicate or case-colliding paths.")
            seen.add(key)
            total += member.size
        if total > MAX_BYTES:
            raise ValueError("Official package exceeds the 1 GiB extracted probe limit.")
        source.extractall(destination, members=members, filter="data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Exact stable version or latest")
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.version != "latest" and not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        raise SystemExit("Use an exact stable version or latest, not a URL or branch.")
    destination = args.destination.resolve()
    stage = (ROOT / ".data").resolve()
    if (not stage.is_relative_to(ROOT.resolve()) or not destination.is_relative_to(stage) or
        destination == stage or destination.exists()):
        raise SystemExit("Destination must be a new directory inside this checkout's .data staging area.")
    tag = "latest" if args.version == "latest" else "tags/rust-v" + args.version
    headers = {"User-Agent": "CAC-compatibility-probe", "Accept": "application/vnd.github+json"}
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com/repos/openai/codex/releases/" + tag, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        release = json.load(response)
    version = release["tag_name"].removeprefix("rust-v")
    if release["prerelease"] or release["draft"] or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("Official response is not a stable release.")
    if args.version != "latest" and version != args.version:
        raise SystemExit("Official release response does not match the requested version.")
    name = "codex-package-x86_64-pc-windows-msvc.tar.gz"
    assets = [asset for asset in release["assets"] if asset["name"] == name]
    if len(assets) != 1:
        raise SystemExit("Official release has no unique complete Windows CLI package.")
    asset = assets[0]
    expected = asset.get("digest", "")
    url = f"https://github.com/openai/codex/releases/download/rust-v{version}/{name}"
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected) or asset["browser_download_url"] != url or asset["size"] > MAX_BYTES:
        raise SystemExit("Official package has no usable checksum, unexpected URL or excessive size.")
    destination.mkdir(parents=True)
    archive = destination / name
    deadline = time.monotonic() + 180
    digest = hashlib.sha256()
    count = 0
    with urllib.request.urlopen(url, timeout=20) as incoming, archive.open("xb") as outgoing:
        while block := incoming.read(1024 * 1024):
            count += len(block)
            if count > asset["size"] or time.monotonic() > deadline:
                raise SystemExit("Official package download exceeded its size or 180-second deadline.")
            digest.update(block)
            outgoing.write(block)
    if count != asset["size"] or "sha256:" + digest.hexdigest() != expected:
        raise SystemExit("Official package checksum/size mismatch. Nothing was executed or installed.")
    package = destination / "package"
    extract_package(archive, package)
    candidates = list(package.rglob("bin/codex.exe"))
    if len(candidates) != 1:
        raise SystemExit("Official package did not contain exactly one expected native entrypoint.")
    report = {"version": version, "package_sha256": digest.hexdigest(),
        "binary": candidates[0].relative_to(destination).as_posix(),
        "binary_sha256": hashlib.sha256(candidates[0].read_bytes()).hexdigest()}
    (destination / "download.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

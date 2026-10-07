"""Inspect archive integrity, private-profile markers and source/package boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PROFILES = ("Oddity_PC", "ODDITY~1")
FORBIDDEN = {"App", ".data", "data", ".venv", "node_modules", ".git", "build", "dist", "__pycache__"}
TOKENS = (b"-----BEGIN PRIVATE KEY-----", b"-----BEGIN RSA PRIVATE KEY-----", b"-----BEGIN OPENSSH PRIVATE KEY-----")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source", action="store_true")
    args = parser.parse_args()
    needles = [value.encode(encoding) for value in PROFILES for encoding in ("utf-8", "utf-16-le")]
    with zipfile.ZipFile(args.archive) as archive:
        assert archive.testzip() is None, "CRC failure"
        names = archive.namelist()
        for name in names:
            parts = Path(name).parts
            if args.source:
                assert not FORBIDDEN.intersection(parts), "Forbidden source tree"
            else:
                assert "Docs" not in parts and "data" not in parts and ".data" not in parts, "Runtime/developer data"
            assert not any(part.startswith(".env") for part in parts), "Environment file"
            body = archive.read(name)
            assert not any(needle in body for needle in needles + list(TOKENS)), "Private marker detected"
        if not args.source and args.archive.suffix == ".zip":
            manifest = json.loads(archive.read("CodexAutoContinuer/RELEASE-MANIFEST.json"))
            assert len(names) == len(manifest["files"]) + 1
            for name, metadata in manifest["files"].items():
                body = archive.read("CodexAutoContinuer/" + name)
                assert len(body) == metadata["bytes"] and hashlib.sha256(body).hexdigest() == metadata["sha256"]
            assert any(name.endswith("status_window.pyc") for name in names), "Frozen status module absent"
            assert sum("/assets/" in name and name.endswith(".png") for name in names) == 20
    print(json.dumps({"entries": len(names), "bytes": args.archive.stat().st_size,
        "sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(), "crc": "passed",
        "configuredPrivateMarkers": "absent", "boundary": "source" if args.source else "release"}, indent=2))


if __name__ == "__main__":
    main()

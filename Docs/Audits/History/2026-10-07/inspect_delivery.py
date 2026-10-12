"""Inspect archive integrity, private-profile markers and source/package boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

FORBIDDEN = {"App", ".data", "data", ".venv", "node_modules", ".git", "build", "dist", "__pycache__",
    ".cac-updates", "Checkpoints", "Handoffs"}
TOKENS = tuple(b"-----BEGIN " + kind + b"-----" for kind in
    (b"PRIVATE KEY", b"RSA PRIVATE KEY", b"OPENSSH PRIVATE KEY"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--private-marker", action="append", default=[],
        help="Local-only private canary to reject; repeat for multiple values. Values are not printed.")
    args = parser.parse_args()
    needles = [value.encode(encoding) for value in args.private_marker for encoding in ("utf-8", "utf-16-le")]
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
        "configuredPrivateMarkers": "absent" if needles else "not configured",
        "boundary": "source" if args.source else "release"}, indent=2))


if __name__ == "__main__":
    main()

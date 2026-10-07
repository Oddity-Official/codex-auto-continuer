"""Read installed client code without extracting or modifying its archive."""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path


class Asar:
    def __init__(self, path):
        self.path = Path(path)
        with self.path.open("rb") as source:
            size, header_size, payload_size, text_size = struct.unpack("<4I", source.read(16))
            if size != 4 or not 0 < text_size <= payload_size <= header_size <= 16 * 1024 * 1024:
                raise ValueError("Unsupported ASAR header")
            self.header = json.loads(source.read(text_size))
        self.offset = 8 + header_size

    def files(self):
        def walk(entries, parent=""):
            for name, item in entries.items():
                relative = parent + name
                if "files" in item:
                    yield from walk(item["files"], relative + "/")
                elif "offset" in item and not item.get("unpacked"):
                    yield relative, item
        yield from walk(self.header["files"])

    def read(self, item):
        count = item["size"]
        if not 0 <= count <= 32 * 1024 * 1024:
            raise ValueError("Refusing an oversized client source file")
        with self.path.open("rb") as source:
            source.seek(self.offset + int(item["offset"]))
            body = source.read(count)
        if len(body) != count:
            raise ValueError("Truncated ASAR member")
        return body.decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--file", help="Packed member; omit to list main-process bundles")
    parser.add_argument("--pattern", action="append", help="Literal source symbol, with bounded context")
    parser.add_argument("--symbols", action="store_true", help="List Codex environment-like symbols")
    parser.add_argument("--find", help="Find a literal in app/conversation/queue bundles; list members/counts only")
    args = parser.parse_args()
    archive = Asar(args.path) if args.path.suffix == ".asar" else None
    if archive and args.find:
        result = []
        total = 0
        for name, item in archive.files():
            if not name.startswith("webview/assets/") or not name.endswith(".js"):
                continue
            if not Path(name).name.startswith(("app-", "local-conversation-", "queued-message-")):
                continue
            total += item["size"]
            if total > 128 * 1024 * 1024:
                raise ValueError("Webview inspection exceeded its size bound")
            count = archive.read(item).count(args.find)
            if count:
                result.append({"member": name, "matches": count})
        print(json.dumps(result, indent=2))
        return
    if archive and not args.file:
        print(json.dumps([{ "name": name, "bytes": item["size"]} for name, item in archive.files()
            if name.startswith(".vite/build/") or name == "package.json"], indent=2))
        return
    if archive:
        item = next(item for name, item in archive.files() if name == args.file)
        text = archive.read(item)
    else:
        text = args.path.read_text(encoding="utf-8")
    if args.symbols:
        print(json.dumps(sorted(set(re.findall(r"\b[A-Z_]*(?:CODEX|APP_SERVER)[A-Z_]*\b", text))), indent=2))
    elif args.pattern:
        result = {}
        for pattern in args.pattern:
            matches = list(re.finditer(re.escape(pattern), text))
            result[pattern] = {"count": len(matches), "matches": [{"offset": m.start(),
                "context": text[max(0, m.start() - 200): m.end() + 300]} for m in matches[:12]]}
        print(json.dumps(result, indent=2))
    else:
        print(text[:4000])


if __name__ == "__main__":
    main()

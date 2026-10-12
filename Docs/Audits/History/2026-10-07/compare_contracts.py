"""Report only consumed schema differences from a native Codex executable."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.codex import _run
from codex_auto_continuer.compatibility import RECORD, schema_contract


def differences(old, new, path=""):
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(old.keys() | new.keys()):
            yield from differences(old.get(key), new.get(key), path + "/" + key)
    elif isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        for index, (before, after) in enumerate(zip(old, new)):
            yield from differences(before, after, path + "/" + str(index))
    elif old != new:
        yield {"path": path, "before": old, "after": new}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="cac-contract-") as temporary:
        result = _run(str(args.executable.resolve(strict=True)),
                      ["app-server", "generate-json-schema", "--experimental", "--out", temporary], 20)
        if result.returncode:
            raise SystemExit("Native schema generation failed")
        current = schema_contract(Path(temporary))
    baseline = json.loads(RECORD.read_text(encoding="utf-8"))["contract"]
    print(json.dumps(list(differences(baseline, current)), indent=2))


if __name__ == "__main__":
    main()

"""Resolve the smallest set of distinct CLI/daemon version tuples."""
from __future__ import annotations

import argparse
import json
import re


def matrix(baseline: str, stable: str) -> dict:
    for value in (baseline, stable):
        if not re.fullmatch(r"\d+\.\d+\.\d+", value):
            raise ValueError("Compatibility matrix requires exact stable versions, not latest or prereleases.")
    rows, seen = [], set()
    for name, cli, daemon in [("certified-baseline", baseline, baseline),
                              ("current-stable", stable, stable),
                              ("mixed-daemon-update", baseline, stable)]:
        if (cli, daemon) not in seen:
            seen.add((cli, daemon))
            rows.append(dict(name=name, cli=cli, daemon=daemon))
    return {"include": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--stable", required=True)
    args = parser.parse_args()
    print(json.dumps(matrix(args.baseline, args.stable), separators=(",", ":")))


if __name__ == "__main__":
    main()

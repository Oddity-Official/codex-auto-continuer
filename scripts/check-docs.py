"""Check local Markdown file links without installing product dependencies."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = []
    checked = 0
    # Current guides can link into history. Historical reports are not build inputs.
    docs = root / "Docs"
    guides = (path for path in docs.rglob("*.md") if path.relative_to(docs).parts[0] not in {"Audits", "History"})
    for path in [*root.glob("*.md"), *guides]:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.S)
        for target in re.findall(r"\[[^\]\n]*\]\(([^\n)]+)\)", text):
            target = target.strip()
            if target.startswith("<"):
                target = target[1:target.index(">")]
            else:
                target = target.split(' "', 1)[0]
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            checked += 1
            if not (path.parent / unquote(parts.path)).exists():
                failures.append(f"{path.relative_to(root)}: missing link {target}")
    for failure in failures:
        print(failure)
    print(f"Checked {checked} local Markdown file links; {len(failures)} failures.")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())

import sys

from codex_auto_continuer.cli import main
from codex_auto_continuer.tray import message

try:
    result = main(sys.argv[1:] or ["tray"])
except Exception as exc:
    message(f"Cannot launch Codex Auto Continuer: {exc}", error=True)
    result = 2
raise SystemExit(result)

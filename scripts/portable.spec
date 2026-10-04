import os
from pathlib import Path

root = Path(SPECPATH).parent
icon = os.environ["CAC_BUILD_ICON"]
common = dict(pathex=[str(root / "src")], hiddenimports=["pystray._win32"],
              datas=[(str(root / "src/codex_auto_continuer/assets"), "codex_auto_continuer/assets"),
                     (str(root / "src/codex_auto_continuer/compatibility.json"), "codex_auto_continuer"),
                     (str(root / "src/codex_auto_continuer/updates.json"), "codex_auto_continuer")],
              excludes=["tkinter", "pytest", "numpy", "matplotlib", "torch", "resvg_py"], noarchive=True)
gui = Analysis([str(root / "scripts/gui-entry.py")], **common)
cli = Analysis([str(root / "scripts/cli-entry.py")], **common)
gui_pyz = PYZ(gui.pure)
cli_pyz = PYZ(cli.pure)
gui_exe = EXE(gui_pyz, gui.scripts, [], exclude_binaries=True, name="CodexAutoContinuer",
              debug=False, strip=False, upx=False, console=False, icon=icon)
cli_exe = EXE(cli_pyz, cli.scripts, [], exclude_binaries=True, name="CodexAutoContinuer-CLI",
              debug=False, strip=False, upx=False, console=True, icon=icon)
COLLECT(gui_exe, cli_exe, gui.binaries, gui.datas, cli.binaries, cli.datas,
        strip=False, upx=False, name="CodexAutoContinuer")

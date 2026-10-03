# Third-party components

The portable application includes Python, pystray, Pillow and six. PyInstaller supplies the executable bootloader. Original dependency license notices are included in the release's `Licenses` folder.

- [Python](https://docs.python.org/3/license.html): Python Software Foundation license
- [pystray](https://github.com/moses-palmer/pystray/blob/master/COPYING.LGPL): LGPL-3.0; matching Python source is included under `Licenses/pystray/source`, and its bundled modules can be replaced in `_internal/pystray`
- [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE): HPND and component notices
- [six](https://github.com/benjaminp/six/blob/master/LICENSE): MIT
- [PyInstaller](https://pyinstaller.org/en/stable/license.html): GPL with its distribution exception for bundled applications

The supervisor talks only to the local Codex installation. These components do not add a remote analytics service. Codex's own network access and telemetry settings belong to Codex.

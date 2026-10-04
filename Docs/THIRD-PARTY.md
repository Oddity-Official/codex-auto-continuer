# Third-party components

The portable application includes Python, pystray, Pillow, six, TOMLKit and Cryptography with its supporting libraries. PyInstaller supplies the executable bootloader. Original dependency license notices are included in the release's `Licenses` folder.

- [Python](https://docs.python.org/3/license.html): Python Software Foundation license
- [pystray](https://github.com/moses-palmer/pystray/blob/master/COPYING.LGPL): LGPL-3.0; matching Python source is included under `Licenses/pystray/source`, and its bundled modules can be replaced in `_internal/pystray`
- [Pillow](https://github.com/python-pillow/Pillow/blob/main/LICENSE): HPND and component notices
- [six](https://github.com/benjaminp/six/blob/master/LICENSE): MIT
- [TOMLKit](https://github.com/python-poetry/tomlkit/blob/master/LICENSE): MIT; preserves settings comments
- [Cryptography](https://github.com/pyca/cryptography/blob/main/LICENSE): Apache-2.0 or BSD; includes component notices for its bundled native libraries. Ed25519 verifies release metadata. CFFI and pycparser notices are also bundled.
- [PyInstaller](https://pyinstaller.org/en/stable/license.html): GPL with its distribution exception for bundled applications
- [Codex](https://github.com/openai/codex/blob/rust-v0.160.0/LICENSE): Apache-2.0; the packaged compatibility contract is a filtered, modified projection of generated 0.160.0 protocol schemas, not Codex executable code. Its upstream license is included in the wheel and portable notices.

Build-only resvg-py renders our SVG master; it is not bundled in the app. The matching source dependency licenses remain in the build environment. Our SVG and generated PNGs use the project's MIT license.

The supervisor talks only to local Codex. The updater requests GitHub release metadata and signed packages; it does not upload diagnostics. These components add no remote analytics service. Codex's own network and telemetry settings belong to Codex.

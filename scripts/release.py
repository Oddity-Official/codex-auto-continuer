"""Generate publisher keys and sign portable releases. Never print private material."""
from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.updates import TRUST, parse_json, verify_zip, write_json
from codex_auto_continuer.state import STATE_VERSION

KEY = ROOT / ".data/release-signing.dpapi"
REPOSITORY = "Oddity-Official/codex-auto-continuer"


def dpapi(payload: bytes, *, decrypt=False) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Local publishing keys use Windows account encryption; CI reads its GitHub secret instead.")
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    buffer = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
    incoming, outgoing = Blob(len(payload), buffer), Blob()
    if not operation(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise RuntimeError("Windows account encryption failed; no private key was printed or exported.")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        kernel.LocalFree(outgoing.data)


def signing_key():
    secret = os.environ.get("CAC_RELEASE_SIGNING_KEY")
    raw = base64.b64decode(secret, validate=True) if secret else dpapi(KEY.read_bytes(), decrypt=True)
    return Ed25519PrivateKey.from_private_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    key = sub.add_parser("key", help="Create an encrypted local key, public trust record and GitHub Actions signing secret.")
    key.add_argument("--install-secret", action="store_true")
    sign = sub.add_parser("sign", help="Sign a clean portable ZIP with the local key or Actions secret.")
    sign.add_argument("archive", type=Path)
    sign.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if args.command == "key":
        if KEY.exists() or TRUST.exists():
            raise SystemExit("Publisher key/trust already exists. Key rotation requires an explicit reviewed trust update.")
        private = Ed25519PrivateKey.generate()
        KEY.parent.mkdir(parents=True, exist_ok=True)
        KEY.write_bytes(dpapi(private.private_bytes_raw()))
        write_json(TRUST, {"format": 1, "repository": REPOSITORY, "public_key": private.public_key().public_bytes_raw().hex()})
        if args.install_secret:
            # stdin avoids exposing the key in command arguments, shell history or command diagnostics.
            result = subprocess.run(["gh", "secret", "set", "CAC_RELEASE_SIGNING_KEY", "--repo", REPOSITORY],
                input=base64.b64encode(private.private_bytes_raw()), capture_output=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise SystemExit("GitHub signing-secret installation failed. The encrypted local key remains intact.")
        print("Publisher key encrypted for this Windows account; public trust record generated.")
        return
    trust = parse_json(TRUST.read_bytes())
    private = signing_key()
    if private.public_key().public_bytes_raw().hex() != trust["public_key"]:
        raise SystemExit("Signing key does not match CAC's public trust record.")
    import zipfile
    with zipfile.ZipFile(args.archive) as archive:
        manifest = parse_json(archive.read("CodexAutoContinuer/RELEASE-MANIFEST.json"))
    record = {"format": 1, "repository": trust["repository"], "version": manifest["version"],
              "platform": "windows-x86_64", "asset": args.archive.name, "state_schema": STATE_VERSION,
              "bytes": args.archive.stat().st_size, "sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest()}
    verify_zip(args.archive, record)
    payload = (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "UPDATE.json").write_bytes(payload)
    (args.out / "UPDATE.sig").write_bytes(private.sign(payload))
    print(f"Signed CAC {record['version']} portable release; SHA-256 {record['sha256']}.")


if __name__ == "__main__":
    main()

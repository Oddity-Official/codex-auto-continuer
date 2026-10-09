"""Authenticated stable release discovery and bounded portable-package validation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import __version__
from .config import Config, control_dir
from .errors import AutoContinuerError
from .telemetry import emit, setup
from .atomic import replace_file

TRUST = Path(__file__).with_name("updates.json")
ROOT_ITEMS = {"CodexAutoContinuer.exe", "CodexAutoContinuer-CLI.exe", "_internal", "Licenses",
              "LICENSE", "README.md", "RELEASE-MANIFEST.json"}
MAX_ZIP = 256 * 1024 * 1024
MAX_EXTRACTED = 1024 * 1024 * 1024


class UpdateError(AutoContinuerError):
    pass


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + "-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        replace_file(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_json(payload: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result
    try:
        value = json.loads(payload, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid number.")))
        if not isinstance(value, dict):
            raise ValueError("Expected object.")
        return value
    except (ValueError, UnicodeError) as exc:
        raise UpdateError("Invalid release metadata. Monitoring continues; no update was installed.") from exc


def version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}", value):
        raise UpdateError("Updates require a stable three-part version.")
    return tuple(map(int, value.split(".")))


def signed_release(payload: bytes, signature: bytes, trust: dict) -> dict:
    if len(payload) > 16384 or len(signature) != 64:
        raise UpdateError("Invalid release signature or metadata size.")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(trust["public_key"])).verify(signature, payload)
    except (InvalidSignature, ValueError, KeyError) as exc:
        raise UpdateError("Release signature verification failed. No update was installed; check the trusted publisher.") from exc
    record = parse_json(payload)
    expected = {"format", "repository", "version", "platform", "asset", "sha256", "bytes", "state_schema"}
    if (set(record) != expected or type(record["format"]) is not int or record["format"] != 1
            or record["repository"] != trust["repository"] or record["platform"] != "windows-x86_64"
            or type(record["state_schema"]) is not int or record["state_schema"] != 2
            or type(record["bytes"]) is not int or not 0 < record["bytes"] <= MAX_ZIP
            or not isinstance(record["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", record["sha256"])):
        raise UpdateError("The signed release does not match this repository, platform or state format.")
    version(record["version"])
    if record["asset"] != f"codex-auto-continuer-{record['version']}-windows-x86_64.zip":
        raise UpdateError("Unexpected portable release asset name.")
    return record


def safe_url(url: str) -> None:
    try:
        parsed = urllib.parse.urlsplit(url)
        host, port = parsed.hostname or "", parsed.port
    except ValueError:
        raise UpdateError("Invalid release redirect URL.") from None
    if (parsed.scheme != "https" or parsed.username or parsed.password or port not in {None, 443}
            or not (host in {"api.github.com", "github.com"} or host.endswith(".githubusercontent.com"))):
        raise UpdateError("Release download redirected outside trusted HTTPS GitHub hosts.")


class GitHubRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        safe_url(newurl)
        redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
        if redirected is not None and urllib.parse.urlsplit(newurl).hostname != "api.github.com":
            redirected.remove_header("Authorization")
        return redirected


class GitHub:
    def __init__(self, use_cli_auth: bool = False):
        self._token = None
        self.opener = urllib.request.build_opener(GitHubRedirect())
        if use_cli_auth:
            executable = shutil.which("gh")
            if not executable:
                raise UpdateError("CAC updates: GitHub CLI (gh) was not found. Private releases need gh auth login. Install gh or disable update_use_github_cli_auth. Codex monitoring continues.")
            for timeout in (5, 10):
                try:
                    result = subprocess.run([executable, "auth", "token", "--hostname", "github.com"],
                        capture_output=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    break
                except subprocess.TimeoutExpired:
                    if timeout == 10:
                        raise UpdateError("CAC updates: GitHub CLI (gh) login timed out after two attempts (15 seconds total). Retry Check For Updates; if it persists, run gh auth status. Codex monitoring continues.") from None
                    emit("update.auth_retry", timeout_seconds=timeout)
                except OSError:
                    raise UpdateError("CAC updates: GitHub CLI (gh) could not be launched. Check its installation, then retry Check For Updates. Codex monitoring continues.") from None
            token = result.stdout.strip()
            if result.returncode or not token or len(token) > 4096 or any(x < 33 or x > 126 for x in token):
                raise UpdateError("CAC updates: no usable GitHub CLI (gh) login for private releases. Run gh auth login, then retry Check For Updates. Codex monitoring continues; no credentials are stored by CAC.")
            self._token = token.decode("ascii")

    def fetch(self, url: str, maximum: int, *, binary=False, target: Path | None = None) -> bytes:
        safe_url(url)
        headers = {"User-Agent": f"CAC/{__version__}", "Accept": "application/octet-stream" if binary else "application/vnd.github+json"}
        if self._token and urllib.parse.urlsplit(url).hostname == "api.github.com":
            headers["Authorization"] = "Bearer " + self._token
        request = urllib.request.Request(url, headers=headers)
        deadline = time.monotonic() + (180 if target else 20)
        output = bytearray()
        stream = None
        try:
            with self.opener.open(request, timeout=10) as response:
                safe_url(response.url)
                if target:
                    stream = target.open("xb")
                total = 0
                while True:
                    if time.monotonic() > deadline:
                        raise UpdateError("GitHub download exceeded its total deadline. Monitoring continues.")
                    block = response.read1(65536)
                    if not block:
                        break
                    total += len(block)
                    if total > maximum:
                        raise UpdateError("GitHub release exceeded its download size limit.")
                    if stream:
                        stream.write(block)
                    else:
                        output.extend(block)
            return bytes(output)
        except urllib.error.HTTPError as exc:
            raise UpdateError(f"GitHub release request returned HTTP {exc.code}. The repository may be private, have no stable release, or be rate-limited. Monitoring continues.") from None
        except (OSError, urllib.error.URLError) as exc:
            raise UpdateError("GitHub release download failed. Check connectivity; monitoring continues.") from None
        finally:
            if stream:
                stream.close()

    def asset(self, repository: str, asset: dict, maximum: int, target=None):
        identifier = asset.get("id")
        if type(identifier) is not int or identifier <= 0:
            raise UpdateError("Invalid GitHub asset identifier.")
        return self.fetch(f"https://api.github.com/repos/{repository}/releases/assets/{identifier}", maximum, binary=True, target=target)


def verify_zip(path: Path, record: dict) -> dict:
    if path.stat().st_size != record["bytes"]:
        raise UpdateError("Portable release size does not match its signed metadata.")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]:
            raise UpdateError("Portable release checksum does not match its signed metadata.")
    try:
        with zipfile.ZipFile(path) as archive:
            seen = set()
            names = set()
            total = 0
            prefixes = {}
            entries = archive.infolist()
            if not entries or len(entries) > 20000:
                raise UpdateError("Portable release has an invalid entry count.")
            for entry in entries:
                name = entry.orig_filename
                parts = PurePosixPath(name).parts
                mode = entry.external_attr >> 16
                if ("\\" in name or ":" in name or "\x00" in name or not parts
                        or name != "/".join(parts) or parts[0] != "CodexAutoContinuer" or len(parts) < 2
                        or any(part in {".", ".."} or part.endswith((" ", ".")) for part in parts)
                        or any(any(ord(char) < 32 or char in '<>"|?*' for char in part) for part in parts)
                        or parts[1] not in ROOT_ITEMS or name.casefold() in seen
                        or (parts[1] not in {"_internal", "Licenses"} and len(parts) != 2)
                        or any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", part.split(".")[0]) for part in parts)
                        or entry.is_dir() or stat.S_ISLNK(mode) or entry.flag_bits & 1):
                    raise UpdateError("Unsafe, duplicate or unexpected portable release path.")
                for index in range(1, len(parts) + 1):
                    prefix = "/".join(parts[:index])
                    if prefixes.setdefault(prefix.casefold(), prefix) != prefix:
                        raise UpdateError("Case-colliding portable release directories.")
                seen.add(name.casefold())
                names.add("/".join(parts[1:]))
                total += entry.file_size
                if total > MAX_EXTRACTED or entry.file_size > MAX_EXTRACTED:
                    raise UpdateError("Portable release exceeds its extracted size limit.")
            for name in names:
                if any(parent.as_posix() in names for parent in PurePosixPath(name).parents if parent.as_posix() != "."):
                    raise UpdateError("Portable release contains a file/directory path collision.")
            if archive.getinfo("CodexAutoContinuer/RELEASE-MANIFEST.json").file_size > 8 * 1024 * 1024:
                raise UpdateError("Portable release manifest is too large.")
            manifest_bytes = archive.read("CodexAutoContinuer/RELEASE-MANIFEST.json")
            manifest = parse_json(manifest_bytes)
            files = manifest.get("files")
            if (manifest.get("version") != record["version"] or manifest.get("platform") != record["platform"]
                    or not isinstance(files, dict) or set(files) != names - {"RELEASE-MANIFEST.json"}
                    or not {"CodexAutoContinuer.exe", "CodexAutoContinuer-CLI.exe"} <= set(files)):
                raise UpdateError("Portable release manifest identity or file set is invalid.")
            for name, expected in files.items():
                if not isinstance(expected, dict) or type(expected.get("bytes")) is not int:
                    raise UpdateError("Invalid portable file checksum record.")
                digest = hashlib.sha256()
                size = 0
                with archive.open("CodexAutoContinuer/" + name) as stream:
                    while block := stream.read(65536):
                        digest.update(block)
                        size += len(block)
                if size != expected["bytes"] or digest.hexdigest() != expected.get("sha256"):
                    raise UpdateError("Portable release file failed checksum validation.")
            return manifest
    except UpdateError:
        raise
    except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError) as exc:
        raise UpdateError("Portable release failed ZIP validation.") from exc


def verify_bundle(bundle: Path, manifest: dict) -> None:
    actual = set()
    for path in bundle.rglob("*"):
        if path.is_symlink() or path.is_junction():
            raise UpdateError("Staged portable bundle contains a link or reparse point.")
        if path.is_file():
            actual.add(path.relative_to(bundle).as_posix())
    if actual != set(manifest["files"]) | {"RELEASE-MANIFEST.json"}:
        raise UpdateError("Staged bundle file set changed after verification.")
    for name, entry in manifest["files"].items():
        path = bundle / name
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if path.stat().st_size != entry["bytes"] or digest != entry["sha256"]:
            raise UpdateError("Staged portable bundle changed after verification.")


def update_status(config_file: Path) -> dict:
    path = config_file.parent / "update-status.json"
    result = parse_json(path.read_bytes()) if path.exists() else {"status": "not_checked"}
    if result.get("status") == "staged" and isinstance(result.get("job"), str):
        job = Path(result["job"])
        if job.name == "job.json" and job.parent.parent.resolve() == (control_dir() / "updates").resolve():
            failure = job.parent / "failure.json"
            if failure.exists():
                result.update(parse_json(failure.read_bytes()))
    return result


def check_release(config_file: Path, cfg: Config, *, stage=False, app_root: Path | None = None, installed_version: str | None = None) -> dict:
    if not getattr(sys, "frozen", False) and app_root is None:
        return {"status": "source_install", "reason": "Source and pip installations are updated by their developer/package manager."}
    current = installed_version or __version__
    app_root = app_root or Path(sys.executable).resolve().parent
    setup(config_file.parent / "updates.jsonl", cfg)
    emit("update.check_started", currentVersion=current, authentication="github_cli" if cfg.update_use_github_cli_auth else "anonymous")
    trust = parse_json(TRUST.read_bytes())
    repository = trust["repository"]
    github = GitHub(cfg.update_use_github_cli_auth)
    release = parse_json(github.fetch(f"https://api.github.com/repos/{repository}/releases/latest", 1024 * 1024))
    tag = release.get("tag_name", "")
    latest = version(tag.removeprefix("v"))
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise UpdateError("GitHub did not return a published stable release.")
    if latest <= version(current):
        emit("update.current", version=current)
        return {"status": "current", "version": current, "checkedAt": time.time()}
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("GitHub release assets are missing.")
    by_name = {}
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str) or asset["name"] in by_name:
            raise UpdateError("GitHub release assets are invalid or duplicated.")
        by_name[asset["name"]] = asset
    if not {"UPDATE.json", "UPDATE.sig"} <= set(by_name):
        raise UpdateError("Stable release is missing its signed update metadata.")
    payload = github.asset(repository, by_name["UPDATE.json"], 16384)
    signature = github.asset(repository, by_name["UPDATE.sig"], 64)
    record = signed_release(payload, signature, trust)
    emit("update.signature_verified", version=record["version"], sha256=record["sha256"], bytes=record["bytes"])
    if version(record["version"]) != latest or record["asset"] not in by_name:
        raise UpdateError("Signed metadata does not match the latest release tag and asset.")
    result = {"status": "available", "version": record["version"], "checkedAt": time.time()}
    if stage:
        directory = control_dir() / "updates" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory / "job.json", {"status": "downloading"})
        (directory / "UPDATE.json").write_bytes(payload)
        (directory / "UPDATE.sig").write_bytes(signature)
        package = directory / "release.zip"
        github.asset(repository, by_name[record["asset"]], record["bytes"], package)
        manifest = verify_zip(package, record)
        with zipfile.ZipFile(package) as archive:
            archive.extractall(directory / "bundle")
        bundle = directory / "bundle/CodexAutoContinuer"
        verify_bundle(bundle, manifest)
        emit("update.package_verified", version=record["version"], files=len(manifest["files"]))
        result.update(status="staged", job=str(directory / "job.json"))
        write_json(directory / "job.json", {"status": "staged", "app": str(app_root.resolve()),
            "config": str(config_file.resolve()), "version": record["version"], "old_version": current})
    return result


def launch_update(job: Path, tray_pid: int | None = None) -> None:
    request = parse_json(job.read_bytes())
    request["tray_pid"] = tray_pid
    request["requester_pid"] = os.getpid()
    write_json(job, request)
    executable = job.parent / "bundle/CodexAutoContinuer/CodexAutoContinuer-CLI.exe"
    subprocess.Popen([str(executable), "_update-worker", str(job)], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

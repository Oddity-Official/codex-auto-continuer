from __future__ import annotations

import importlib.util
import io
import hashlib
import json
import sys
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "download-probe-codex.py"
spec = importlib.util.spec_from_file_location("download_probe_codex", SCRIPT)
download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


def archive(tmp_path, names, *, link=False):
    path = tmp_path / "package.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            entry = tarfile.TarInfo(name)
            if link:
                entry.type = tarfile.SYMTYPE
                entry.linkname = "outside"
                tar.addfile(entry)
            else:
                entry.size = 3
                tar.addfile(entry, io.BytesIO(b"abc"))
    return path


@pytest.mark.parametrize("name", ["../escape.exe", "/absolute.exe", "C:/drive.exe", "bin\\codex.exe"])
def test_package_rejects_unsafe_paths_before_extracting(tmp_path, name):
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="unsafe"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe", name]), target)
    assert not target.exists()


def test_package_rejects_links_and_case_collisions(tmp_path):
    with pytest.raises(ValueError, match="unsafe"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe"], link=True), tmp_path / "target")
    with pytest.raises(ValueError, match="colliding"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe", "BIN/./codex.exe"]), tmp_path / "target")
    assert not (tmp_path / "target").exists()


def test_package_enforces_extracted_limit_and_accepts_normal_package(tmp_path, monkeypatch):
    path = archive(tmp_path, ["bin/codex.exe"])
    monkeypatch.setattr(download, "MAX_BYTES", 2)
    with pytest.raises(ValueError, match="limit"):
        download.extract_package(path, tmp_path / "target")
    monkeypatch.setattr(download, "MAX_BYTES", 100)
    download.extract_package(path, tmp_path / "target")
    assert (tmp_path / "target/bin/codex.exe").read_bytes() == b"abc"


@pytest.mark.parametrize("authenticated", [True, False])
def test_download_auth_is_metadata_only_and_never_persisted(tmp_path, monkeypatch, capsys, authenticated):
    package = archive(tmp_path, ["bin/codex.exe"]).read_bytes()
    token = "SYNTHETIC_CI_TOKEN_NOT_FOR_DOWNLOADS"
    name = "codex-package-x86_64-pc-windows-msvc.tar.gz"
    url = f"https://github.com/openai/codex/releases/download/rust-v0.160.0/{name}"
    release = {"tag_name": "rust-v0.160.0", "prerelease": False, "draft": False,
        "assets": [{"name": name, "size": len(package), "browser_download_url": url,
            "digest": "sha256:" + hashlib.sha256(package).hexdigest()}]}
    requests = []
    def fetch(request, *, timeout):
        requests.append(request)
        assert timeout == 20
        if isinstance(request, download.urllib.request.Request):
            assert request.full_url == "https://api.github.com/repos/openai/codex/releases/tags/rust-v0.160.0"
            assert request.get_header("Authorization") == ("Bearer " + token if authenticated else None)
            return io.BytesIO(json.dumps(release).encode())
        assert request == url  # A fresh token-free download, not a reused API request.
        return io.BytesIO(package)
    monkeypatch.setattr(download.urllib.request, "urlopen", fetch)
    monkeypatch.setattr(download, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--version", "0.160.0", "--destination", str(tmp_path / ".data/probe")])
    if authenticated:
        monkeypatch.setenv("GH_TOKEN", token)
    else:
        monkeypatch.delenv("GH_TOKEN", raising=False)
    download.main()
    assert len(requests) == 2
    assert (tmp_path / ".data/probe/package/bin/codex.exe").read_bytes() == b"abc"
    assert token not in capsys.readouterr().out
    assert token not in (tmp_path / ".data/probe/download.json").read_text()

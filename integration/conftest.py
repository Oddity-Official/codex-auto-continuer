from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from native_support import NativeFixture
from codex_auto_continuer.codex import codex_version, find_codex


def pytest_addoption(parser):
    parser.addoption("--codex-executable", help="Native Codex executable; otherwise auto-detect.")
    parser.addoption("--vscode-executable", help="Installed Code.exe for the separate extension integration gate.")
    parser.addoption("--vscode-extension", help="Installed openai.chatgpt extension directory, used without modification.")


@pytest.fixture(scope="session")
def codex_binary(request):
    binary = find_codex(request.config.getoption("--codex-executable"))
    version = codex_version(binary, 10)
    print(f"\nNative continuation baseline: Codex {version}")
    return binary


@pytest.fixture
def native(codex_binary):
    with NativeFixture(ROOT, codex_binary) as fixture:
        yield fixture

"""Pruebas de la logica de actualizacion (comparacion de versiones)."""

from remote_desk.updater.github import _pick_installer
from remote_desk.updater.version import is_newer, parse_version


def test_parse_version():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("0.10.0-beta") == (0, 10, 0)
    assert parse_version("sin-version") is None


def test_is_newer():
    assert is_newer("v0.2.0", "0.1.0")
    assert is_newer("v0.1.1", "0.1.0")
    assert not is_newer("v0.1.0", "0.1.0")
    assert not is_newer("v0.1.0", "0.2.0")
    assert not is_newer("basura", "0.1.0")


def test_pick_installer_prefers_exe():
    assets = [
        {"name": "notas.txt", "browser_download_url": "x"},
        {"name": "RemoteDeskSetup.exe", "browser_download_url": "ok"},
    ]
    assert _pick_installer(assets) == "ok"
    assert _pick_installer([]) == ""

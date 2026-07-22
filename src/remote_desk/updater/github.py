"""Consulta de la ultima Release publicada en GitHub (API REST v3).

Usa solo la biblioteca estandar (urllib) para no anadir dependencias. La llamada
es sincrona; el servicio la ejecuta en un executor para no bloquear la GUI.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from remote_desk.common.logging import setup_logging

log = setup_logging("updater.github")

_API = "https://api.github.com/repos/{repo}/releases/latest"
_TIMEOUT = 8  # segundos


@dataclass(frozen=True)
class ReleaseInfo:
    version: str  # tag, p.ej. 'v0.2.0'
    notes: str
    installer_url: str  # URL del asset .exe del instalador


def _pick_installer(assets: list[dict]) -> str:
    """Elige el asset del instalador (.exe) entre los adjuntos de la Release."""
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith(".exe"):
            return asset.get("browser_download_url", "")
    return ""


def fetch_latest_release(repo: str) -> ReleaseInfo | None:
    """Devuelve la ultima Release o None si no hay/falla la consulta."""
    url = _API.format(repo=repo)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "remote-desk-updater",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        log.info("no se pudo consultar releases: %s", exc)
        return None

    tag = data.get("tag_name")
    if not tag:
        return None
    return ReleaseInfo(
        version=tag,
        notes=data.get("body", "") or "",
        installer_url=_pick_installer(data.get("assets", [])),
    )

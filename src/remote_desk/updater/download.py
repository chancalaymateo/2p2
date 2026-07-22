"""Descarga del instalador de una nueva version a una carpeta temporal."""

from __future__ import annotations

import os
import tempfile
import urllib.request

from remote_desk.common.logging import setup_logging

log = setup_logging("updater.download")


def download_installer(url: str) -> str:
    """Descarga el instalador y devuelve la ruta local del .exe.

    Lanza una excepcion si la descarga falla (el caller la maneja en la GUI).
    """
    filename = os.path.basename(url) or "RemoteDeskSetup.exe"
    dest = os.path.join(tempfile.gettempdir(), filename)

    request = urllib.request.Request(url, headers={"User-Agent": "remote-desk-updater"})
    with urllib.request.urlopen(request, timeout=60) as resp, open(dest, "wb") as fh:  # noqa: S310
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            fh.write(chunk)

    log.info("instalador descargado en %s", dest)
    return dest

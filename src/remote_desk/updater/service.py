"""Servicio de actualizacion integrado con Qt/asyncio.

Orquesta: consulta la ultima Release -> compara version -> emite senal si hay
una nueva -> (bajo confirmacion del usuario) descarga y lanza el instalador.

Las operaciones de red corren en un executor para no congelar la interfaz.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from PySide6.QtCore import QObject, Signal

from remote_desk import __version__
from remote_desk.common.logging import setup_logging

from .download import download_installer
from .github import ReleaseInfo, fetch_latest_release
from .version import is_newer

log = setup_logging("updater.service")


class UpdateService(QObject):
    # Emitida cuando hay una version mas nueva disponible.
    update_available = Signal(object)  # ReleaseInfo
    # Progreso/errores de la actualizacion.
    error = Signal(str)

    def __init__(self, repo: str) -> None:
        super().__init__()
        self._repo = repo

    async def check(self) -> None:
        """Revisa si hay una version nueva y emite `update_available` si aplica."""
        loop = asyncio.get_event_loop()
        release = await loop.run_in_executor(None, fetch_latest_release, self._repo)
        if release is None:
            return
        if is_newer(release.version, __version__):
            log.info("nueva version disponible: %s (actual %s)", release.version, __version__)
            self.update_available.emit(release)
        else:
            log.info("ya estas en la ultima version (%s)", __version__)

    async def download_and_launch(self, release: ReleaseInfo) -> None:
        """Descarga el nuevo .exe y lo aplica, luego cierra la app.

        Si corremos como ejecutable empaquetado, la copia nueva se lanza en modo
        `--apply-update`: espera a que esta instancia cierre, reemplaza el .exe
        instalado y lo relanza. En desarrollo solo abre el archivo descargado.
        """
        if not release.installer_url:
            self.error.emit("La version publicada no incluye un .exe descargable.")
            return
        try:
            loop = asyncio.get_event_loop()
            path = await loop.run_in_executor(None, download_installer, release.installer_url)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"No se pudo descargar la actualizacion: {exc}")
            return

        from remote_desk import installer

        if installer.is_frozen():
            # La copia nueva reemplaza a la instalada y se relanza sola.
            target = str(installer.installed_exe())
            subprocess.Popen([path, "--apply-update", target])  # noqa: S603
        elif sys.platform == "win32" and hasattr(os, "startfile"):
            os.startfile(path)  # noqa: S606
        else:  # pragma: no cover
            subprocess.Popen([path])  # noqa: S603

        from PySide6.QtWidgets import QApplication

        QApplication.quit()

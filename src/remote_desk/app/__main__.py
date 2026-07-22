"""Punto de entrada de la app unificada de escritorio.

Integra asyncio + Qt con qasync, muestra la pantalla de inicio y revisa
actualizaciones en segundo plano. Es el ejecutable principal (`RemoteDesk.exe`),
que ademas se auto-instala en el primer arranque.

Modos de linea de comandos (usados internamente):
    --apply-update <ruta>   reemplaza el .exe instalado (auto-actualizacion)
    --install               instala en silencio y abre la copia instalada
    --portable              omite la auto-instalacion y corre desde aqui

Uso normal:
    python -m remote_desk.app
    RemoteDesk.exe          (doble clic; se instala solo la primera vez)
"""

from __future__ import annotations

import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication, QMessageBox

from remote_desk import installer
from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging
from remote_desk.updater.github import ReleaseInfo
from remote_desk.updater.service import UpdateService

from .home_window import HomeWindow
from .theme import apply_theme

log = setup_logging("app")


def _prompt_update(window: HomeWindow, service: UpdateService, release: ReleaseInfo) -> None:
    """Pop-up que ofrece instalar la nueva version."""
    box = QMessageBox(window)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle("Actualizacion disponible")
    box.setText(f"Hay una version nueva disponible: {release.version}")
    notes = release.notes.strip()
    if notes:
        box.setInformativeText(notes[:600])
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.button(QMessageBox.StandardButton.Yes).setText("Instalar ahora")
    box.button(QMessageBox.StandardButton.No).setText("Mas tarde")
    if box.exec() == QMessageBox.StandardButton.Yes:
        asyncio.ensure_future(service.download_and_launch(release))


def _maybe_self_install(app: QApplication) -> bool:
    """Auto-instalacion en el primer arranque del .exe portable.

    Devuelve True si se instalo y relanzo (el caller debe salir). En desarrollo
    (no empaquetado) o si ya corre desde la carpeta de instalacion, no hace nada.
    """
    if not installer.is_frozen() or installer.running_from_install():
        return False

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle("Instalar 2p2")
    box.setText("¿Instalar 2p2 en este equipo?")
    box.setInformativeText(
        "Se copiara a tu carpeta de usuario y se crearan accesos directos en el "
        "menu inicio y el escritorio. No requiere permisos de administrador."
    )
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.button(QMessageBox.StandardButton.Yes).setText("Instalar")
    box.button(QMessageBox.StandardButton.No).setText("Solo abrir")
    if box.exec() != QMessageBox.StandardButton.Yes:
        return False

    try:
        target = installer.perform_install()
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(None, "Error", f"No se pudo instalar: {exc}")
        return False

    installer.launch(target)
    return True


def _run_cli_mode() -> bool:
    """Maneja los modos de linea de comandos. Devuelve True si ya se atendio."""
    argv = sys.argv
    if "--apply-update" in argv:
        idx = argv.index("--apply-update")
        target = argv[idx + 1] if idx + 1 < len(argv) else str(installer.installed_exe())
        installer.apply_update(target)
        return True
    if "--install" in argv:
        target = installer.perform_install()
        installer.launch(target)
        return True
    return False


def main() -> None:
    # Modos internos que no abren la GUI principal.
    if _run_cli_mode():
        return

    config = AppConfig.load()

    app = QApplication(sys.argv)
    app.setApplicationName("2p2")
    apply_theme(app)

    # Primer arranque del portable: ofrecer instalar y relanzar.
    if "--portable" not in sys.argv and _maybe_self_install(app):
        return

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = HomeWindow(config)
    window.show()

    # Revision de actualizaciones (no bloqueante) si esta habilitada.
    if config.update_check_enabled and "/" in config.github_repo:
        service = UpdateService(config.github_repo)
        service.update_available.connect(
            lambda release: _prompt_update(window, service, release)
        )
        service.error.connect(lambda msg: log.warning("updater: %s", msg))
        asyncio.ensure_future(service.check())

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()

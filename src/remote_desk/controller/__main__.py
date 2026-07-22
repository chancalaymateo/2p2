"""Punto de entrada del controlador (GUI).

Integra el event loop de asyncio con el de Qt mediante `qasync`, de modo que
aiortc (asyncio) y PySide6 (Qt) coexisten en un unico hilo.

Uso:
    python -m remote_desk.controller
    remote-desk-controller   (si el paquete esta instalado)
"""

from __future__ import annotations

import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

from remote_desk.common.config import AppConfig
from remote_desk.common.logging import setup_logging

from .ui.main_window import MainWindow

log = setup_logging("controller")


def main() -> None:
    config = AppConfig.load()

    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow(config)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()

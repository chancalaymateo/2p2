"""Ventana independiente del controlador (entry point `remote-desk-controller`).

Solo aloja el `ControllerPanel`. La app unificada reutiliza el mismo panel.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from remote_desk.common.config import AppConfig

from .controller_panel import ControllerPanel


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("2p2  ·  Controlador")
        self.resize(1100, 720)
        self.panel = ControllerPanel(config)
        self.setCentralWidget(self.panel)

    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        self.panel.shutdown()
        event.accept()

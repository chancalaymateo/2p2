"""Panel del controlador: formulario de conexion + vista remota.

Es un QWidget reutilizable: lo usa tanto la ventana independiente
(`remote-desk-controller`) como la app unificada (pantalla de inicio).
"""

from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from remote_desk.common.config import AppConfig
from remote_desk.controller.connection import ControllerConnection

from .video_widget import VideoWidget


class ControllerPanel(QWidget):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.connection: ControllerConnection | None = None
        self._build_ui()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())

        self.video = VideoWidget(self._send_control)
        root.addWidget(self.video, stretch=1)

        self.status = QLabel("Ingresa el ID y la clave del equipo remoto.")
        self.status.setStyleSheet(
            "background:#171c22; color:#8a929c; padding:5px 14px; font-size:12px;"
            "border-top:1px solid #242b33;"
        )
        root.addWidget(self.status)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:#171c22; border-bottom:1px solid #242b33;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.server_input = QLineEdit(self.config.signaling_url)
        self.server_input.setFixedWidth(230)
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID del equipo (ej. 123 456 789)")
        self.id_input.setFixedWidth(200)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Clave")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedWidth(140)

        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.setStyleSheet(
            "QPushButton{background:#2f6fed; border:1px solid #2f6fed; color:white;}"
            "QPushButton:hover{background:#3f7cf5; border-color:#3f7cf5;}"
        )
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.disconnect_btn = QPushButton("Desconectar")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)

        for w in (
            QLabel("Servidor:"),
            self.server_input,
            QLabel("ID:"),
            self.id_input,
            QLabel("Clave:"),
            self.pass_input,
            self.connect_btn,
            self.disconnect_btn,
        ):
            layout.addWidget(w)
        layout.addStretch(1)
        return bar

    # -------------------------------------------------------------- acciones
    def _on_connect_clicked(self) -> None:
        agent_id = self.id_input.text().strip()
        password = self.pass_input.text()
        if not agent_id or not password:
            QMessageBox.warning(self, "Faltan datos", "Ingresa el ID y la clave.")
            return

        self.connection = ControllerConnection(self.server_input.text().strip())
        self.connection.frame_ready.connect(self.video.update_image)
        self.connection.status.connect(self._set_status)
        self.connection.error.connect(self._on_error)
        self.connection.closed.connect(self._on_closed)

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        asyncio.ensure_future(self._connect(agent_id, password))

    async def _connect(self, agent_id: str, password: str) -> None:
        try:
            await self.connection.connect_to(agent_id, password)
            self.video.set_control_enabled(True)
        except Exception as exc:  # noqa: BLE001
            self._on_error(f"No se pudo conectar: {exc}")

    def _on_disconnect_clicked(self) -> None:
        if self.connection:
            asyncio.ensure_future(self.connection.close())
        self._on_closed()

    def _send_control(self, event: dict) -> None:
        if self.connection:
            self.connection.send_control(event)

    # --------------------------------------------------------------- estado
    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error de conexion", message)
        self._on_closed()

    def _on_closed(self) -> None:
        self.video.set_control_enabled(False)
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

    def shutdown(self) -> None:
        if self.connection:
            asyncio.ensure_future(self.connection.close())

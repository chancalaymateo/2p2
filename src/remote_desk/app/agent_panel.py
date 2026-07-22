"""Panel 'Permitir control': ejecuta el agente y muestra ID + clave en la GUI.

Envuelve `AgentClient` inyectandole callbacks graficos: las credenciales se
muestran en pantalla y el consentimiento se pide con un dialogo modal.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from remote_desk.agent.connection import AgentClient
from remote_desk.common.config import AppConfig

from .theme import ACCENT, ACCENT_HOVER, BORDER, SURFACE, TEXT, TEXT_MUTED


class AgentPanel(QWidget):
    # Se emite desde el hilo asyncio (mismo loop, pero usamos senal por claridad).
    _credentials = Signal(str, str)
    _status = Signal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self._client: AgentClient | None = None
        self._task: asyncio.Task | None = None

        self._credentials.connect(self._show_credentials)
        self._status.connect(self._set_status)
        self._build_ui()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Permitir que controlen este equipo")
        title.setStyleSheet(f"font-size:18px; font-weight:600; color:{TEXT};")
        root.addWidget(title)

        hint = QLabel(
            "Comparte tu ID y clave solo con quien confies. Cada sesion pedira tu "
            "confirmacion antes de ceder el control."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        root.addWidget(hint)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{SURFACE}; border:1px solid {BORDER}; border-radius:8px;}}"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(26, 22, 26, 22)
        card_l.setSpacing(6)

        mono = "'Consolas', 'Cascadia Mono', monospace"
        cred_style = f"font-family:{mono}; font-size:30px; font-weight:600; letter-spacing:3px; color:{TEXT};"
        label_style = f"color:{TEXT_MUTED}; font-size:11px; letter-spacing:2px;"

        id_cap = QLabel("ID DEL EQUIPO")
        id_cap.setStyleSheet(label_style)
        self.id_label = QLabel("—")
        self.id_label.setStyleSheet(cred_style)
        pass_cap = QLabel("CLAVE DE SESION")
        pass_cap.setStyleSheet(label_style)
        self.pass_label = QLabel("—")
        self.pass_label.setStyleSheet(cred_style)

        card_l.addWidget(id_cap)
        card_l.addWidget(self.id_label)
        card_l.addSpacing(12)
        card_l.addWidget(pass_cap)
        card_l.addWidget(self.pass_label)
        root.addWidget(card)

        row = QHBoxLayout()
        self.start_btn = QPushButton("Activar")
        self.start_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT}; border:1px solid {ACCENT}; color:white;}}"
            f"QPushButton:hover{{background:{ACCENT_HOVER}; border-color:{ACCENT_HOVER};}}"
        )
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addStretch(1)
        root.addLayout(row)

        self.status = QLabel("Inactivo.")
        self.status.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        root.addWidget(self.status)

    # -------------------------------------------------------------- acciones
    def _on_start(self) -> None:
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._set_status("Conectando al servidor...")
        self._client = AgentClient(
            self.config,
            on_credentials=lambda i, p: self._credentials.emit(i, p),
            consent_provider=self._ask_consent,
            on_status=lambda s: self._status.emit(s),
        )
        self._task = asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        try:
            await self._client.run()
        except Exception as exc:  # noqa: BLE001
            self._status.emit(f"Error: {exc}")
            self._on_stop()

    def _on_stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        self._client = None
        self.id_label.setText("—")
        self.pass_label.setText("—")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._set_status("Inactivo.")

    async def _ask_consent(self, controller_ip: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Solicitud de control remoto")
        box.setText(f"Un equipo desde {controller_ip} quiere controlar esta maquina.")
        box.setInformativeText("¿Autorizas la conexion?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        # exec() bloquea el loop de Qt momentaneamente; para un dialogo de
        # consentimiento puntual es aceptable y garantiza decision explicita.
        return box.exec() == QMessageBox.StandardButton.Yes

    # --------------------------------------------------------------- senales
    def _show_credentials(self, agent_id: str, password: str) -> None:
        self.id_label.setText(agent_id)
        self.pass_label.setText(password)

    def _set_status(self, text: str) -> None:
        self.status.setText(text)

    def shutdown(self) -> None:
        if self._task:
            self._task.cancel()

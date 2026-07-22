"""Panel 'Permitir control': muestra el ID/clave permanentes y activa el agente.

El ID y la clave provienen de la identidad persistente (no cambian entre
reinicios) y se pueden copiar o restablecer. 'Activar' conecta al servidor para
quedar disponible; cada conexion entrante pide consentimiento.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from remote_desk.agent.connection import AgentClient
from remote_desk.common import identity as identity_mod
from remote_desk.common.config import AppConfig

from .theme import ACCENT, ACCENT_HOVER, BORDER, SURFACE, SURFACE_2, TEXT, TEXT_MUTED

_MONO = "'Consolas', 'Cascadia Mono', monospace"


class AgentPanel(QWidget):
    _granted = Signal(str, str)
    _status = Signal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.identity = identity_mod.load_or_create()
        self._client: AgentClient | None = None
        self._task: asyncio.Task | None = None
        self._active = False

        self._granted.connect(self._show_credentials)
        self._status.connect(self._set_status)
        self._build_ui()
        self._show_credentials(self.identity.id, self.identity.password)

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 36, 44, 28)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Permitir que controlen este equipo")
        title.setStyleSheet(f"font-size:19px; font-weight:600; color:{TEXT};")
        root.addWidget(title)

        hint = QLabel(
            "Tu ID es permanente. Comparte ID y clave solo con quien confies: cada "
            "sesion pedira tu confirmacion antes de ceder el control."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        root.addWidget(hint)

        root.addWidget(self._cred_card())

        # Acciones
        row = QHBoxLayout()
        row.setSpacing(10)
        self.toggle_btn = QPushButton("Activar")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT}; border:1px solid {ACCENT}; color:white;"
            "padding:9px 22px; font-weight:600;}"
            f"QPushButton:hover{{background:{ACCENT_HOVER}; border-color:{ACCENT_HOVER};}}"
        )
        self.toggle_btn.clicked.connect(self._on_toggle)

        self.reset_btn = QPushButton("Restablecer ID y clave")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset)

        row.addWidget(self.toggle_btn)
        row.addWidget(self.reset_btn)
        row.addStretch(1)
        root.addLayout(row)

        # Estado con indicador
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        self.status = QLabel("Inactivo")
        self.status.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        status_row.addWidget(self.dot)
        status_row.addWidget(self.status)
        status_row.addStretch(1)
        root.addLayout(status_row)

    def _cred_card(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{SURFACE}; border:1px solid {BORDER}; border-radius:10px;}}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 22, 26, 22)
        lay.setSpacing(18)
        lay.addLayout(self._cred_row("ID DEL EQUIPO", "id"))

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER};")
        lay.addWidget(sep)

        lay.addLayout(self._cred_row("CLAVE DE SESION", "pass"))
        return card

    def _cred_row(self, caption: str, kind: str) -> QHBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(4)
        cap = QLabel(caption)
        cap.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; letter-spacing:2px;")
        value = QLabel("—")
        value.setStyleSheet(
            f"font-family:{_MONO}; font-size:30px; font-weight:600; letter-spacing:3px; color:{TEXT};"
        )
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(cap)
        col.addWidget(value)

        copy = QPushButton("Copiar")
        copy.setCursor(Qt.CursorShape.PointingHandCursor)
        copy.setFixedWidth(84)
        copy.setStyleSheet(
            f"QPushButton{{background:{SURFACE_2}; border:1px solid {BORDER}; color:{TEXT_MUTED};"
            "padding:6px 10px; font-size:12px;}"
            f"QPushButton:hover{{color:{TEXT}; border-color:{ACCENT};}}"
        )

        row = QHBoxLayout()
        row.addLayout(col, stretch=1)
        row.addWidget(copy, alignment=Qt.AlignmentFlag.AlignBottom)

        if kind == "id":
            self.id_label = value
            copy.clicked.connect(lambda: self._copy(self.identity.id, "ID copiado"))
        else:
            self.pass_label = value
            copy.clicked.connect(lambda: self._copy(self.identity.password, "Clave copiada"))
        return row

    # -------------------------------------------------------------- acciones
    def _on_toggle(self) -> None:
        if self._active:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        self._active = True
        self.toggle_btn.setText("Detener")
        self.reset_btn.setEnabled(False)
        self._set_status("Conectando al servidor...", ACCENT)
        self._client = AgentClient(
            self.config,
            identity=self.identity,
            on_credentials=lambda i, p: self._granted.emit(i, p),
            consent_provider=self._ask_consent,
            on_status=lambda s: self._status.emit(s),
        )
        self._task = asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        try:
            await self._client.run()
        except Exception as exc:  # noqa: BLE001
            self._status.emit(f"Error: {exc}")
            self._stop()

    def _stop(self) -> None:
        self._active = False
        if self._task:
            self._task.cancel()
            self._task = None
        self._client = None
        self.toggle_btn.setText("Activar")
        self.reset_btn.setEnabled(True)
        self._set_status("Inactivo")

    def _on_reset(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Restablecer identidad",
            "Se generara un ID y una clave nuevos. Las conexiones guardadas con el "
            "ID anterior dejaran de funcionar. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        identity_mod.reset(self.identity)
        self._show_credentials(self.identity.id, self.identity.password)
        self._set_status("Identidad restablecida")

    async def _ask_consent(self, controller_ip: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Solicitud de control remoto")
        box.setText(f"Un equipo desde {controller_ip} quiere controlar esta maquina.")
        box.setInformativeText("¿Autorizas la conexion?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes

    # --------------------------------------------------------------- helpers
    def _copy(self, text: str, msg: str) -> None:
        QApplication.clipboard().setText(text)
        self._set_status(msg, ACCENT)

    def _show_credentials(self, agent_id: str, password: str) -> None:
        self.id_label.setText(agent_id)
        self.pass_label.setText(password)

    def _set_status(self, text: str, color: str = "") -> None:
        self.status.setText(text)
        col = color or TEXT_MUTED
        self.status.setStyleSheet(f"color:{col}; font-size:12px;")
        # Punto verde cuando alguien controla; azul en transicion; gris inactivo.
        if "controlando" in text.lower():
            self.dot.setStyleSheet("color:#3fb950; font-size:12px;")
        elif self._active:
            self.dot.setStyleSheet(f"color:{ACCENT}; font-size:12px;")
        else:
            self.dot.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")

    def shutdown(self) -> None:
        if self._task:
            self._task.cancel()

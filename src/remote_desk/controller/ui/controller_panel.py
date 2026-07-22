"""Panel del controlador: favoritos + formulario de conexion + vista remota.

Widget reutilizable por la ventana independiente y la app unificada. Incluye una
barra lateral de conexiones favoritas (guardadas localmente) que se oculta al
conectarse para dar todo el espacio al video.
"""

from __future__ import annotations

import asyncio

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from remote_desk.common.config import AppConfig
from remote_desk.common.favorites import Favorite, FavoritesStore
from remote_desk.controller.connection import ControllerConnection

# Paleta local (coherente con app.theme, sin acoplar el paquete controller a app).
BG = "#101418"
SURFACE = "#171c22"
SURFACE_2 = "#1d232b"
BORDER = "#242b33"
TEXT = "#e8eaed"
TEXT_MUTED = "#8a929c"
ACCENT = "#2f6fed"
ACCENT_HOVER = "#3f7cf5"


class ControllerPanel(QWidget):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.connection: ControllerConnection | None = None
        self.favorites = FavoritesStore.load()
        self._build_ui()
        self._refresh_favorites()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = self._build_sidebar()
        body.addWidget(self.sidebar)

        from .video_widget import VideoWidget

        self.video = VideoWidget(self._send_control)
        body.addWidget(self.video, stretch=1)
        root.addLayout(body, stretch=1)

        self.status = QLabel("Ingresa el ID y la clave del equipo remoto.")
        self.status.setStyleSheet(
            f"background:{SURFACE}; color:{TEXT_MUTED}; padding:6px 14px; font-size:12px;"
            f"border-top:1px solid {BORDER};"
        )
        root.addWidget(self.status)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background:{SURFACE}; border-bottom:1px solid {BORDER};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID del equipo (123 456 789)")
        self.id_input.setFixedWidth(210)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Clave")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setFixedWidth(150)

        self.connect_btn = QPushButton("Conectar")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT}; border:1px solid {ACCENT}; color:white; font-weight:600;}}"
            f"QPushButton:hover{{background:{ACCENT_HOVER}; border-color:{ACCENT_HOVER};}}"
        )
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.save_btn = QPushButton("Guardar")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setToolTip("Guardar como favorito")
        self.save_btn.clicked.connect(self._on_save_favorite)

        self.disconnect_btn = QPushButton("Desconectar")
        self.disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)

        # Servidor (avanzado): visible pero discreto.
        self.server_input = QLineEdit(self.config.signaling_url)
        self.server_input.setFixedWidth(200)
        self.server_input.setToolTip("Servidor de senalizacion")

        layout.addWidget(QLabel("ID"))
        layout.addWidget(self.id_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.disconnect_btn)
        layout.addStretch(1)
        layout.addWidget(QLabel("Servidor"))
        layout.addWidget(self.server_input)
        return bar

    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(230)
        panel.setStyleSheet(f"background:{BG}; border-right:1px solid {BORDER};")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(14, 16, 14, 16)
        outer.setSpacing(10)

        head = QLabel("FAVORITOS")
        head.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; letter-spacing:2px;")
        outer.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self.fav_layout = QVBoxLayout(container)
        self.fav_layout.setContentsMargins(0, 0, 0, 0)
        self.fav_layout.setSpacing(8)
        self.fav_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        self.empty_label = QLabel("Aun no hay favoritos.\nUsa 'Guardar' tras escribir un ID.")
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        outer.addWidget(self.empty_label)
        return panel

    # -------------------------------------------------------------- favoritos
    def _refresh_favorites(self) -> None:
        while self.fav_layout.count():
            item = self.fav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.empty_label.setVisible(not self.favorites.items)
        for fav in self.favorites.items:
            self.fav_layout.addWidget(self._favorite_card(fav))

    def _favorite_card(self, fav: Favorite) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{SURFACE}; border:1px solid {BORDER}; border-radius:7px;}}"
            f"QFrame:hover{{border-color:{ACCENT};}}"
        )
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 8, 10)
        lay.setSpacing(6)

        open_btn = QPushButton()
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(
            "QPushButton{background:transparent; border:none; text-align:left; padding:0;}"
        )
        open_btn.setText(f"{fav.alias}\n{fav.agent_id}")
        # Estiliza el texto de dos lineas via rich text no es directo en QPushButton;
        # usamos tooltip y una fuente simple.
        open_btn.setToolTip(f"Conectar a {fav.agent_id}")
        open_btn.clicked.connect(lambda: self._use_favorite(fav))

        remove = QPushButton("×")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setFixedSize(24, 24)
        remove.setStyleSheet(
            f"QPushButton{{background:transparent; border:none; color:{TEXT_MUTED}; font-size:16px;}}"
            f"QPushButton:hover{{color:#c14a4a;}}"
        )
        remove.clicked.connect(lambda: self._remove_favorite(fav))

        lay.addWidget(open_btn, stretch=1)
        lay.addWidget(remove, alignment=Qt.AlignmentFlag.AlignTop)
        return card

    def _use_favorite(self, fav: Favorite) -> None:
        self.id_input.setText(fav.agent_id)
        self.pass_input.setText(fav.password)
        if fav.password:
            self._on_connect_clicked()

    def _remove_favorite(self, fav: Favorite) -> None:
        self.favorites.remove(fav.agent_id)
        self._refresh_favorites()

    def _on_save_favorite(self) -> None:
        agent_id = self.id_input.text().strip()
        if not agent_id:
            QMessageBox.warning(self, "Guardar favorito", "Escribe primero un ID.")
            return
        alias, ok = QInputDialog.getText(
            self, "Guardar favorito", "Nombre para esta conexion:", text=agent_id
        )
        if not ok:
            return
        self.favorites.add(
            Favorite(alias=alias.strip() or agent_id, agent_id=agent_id, password=self.pass_input.text())
        )
        self._refresh_favorites()

    # -------------------------------------------------------------- conexion
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
        self.sidebar.setVisible(False)  # el video ocupa toda la ventana
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
        self.sidebar.setVisible(True)

    def shutdown(self) -> None:
        if self.connection:
            asyncio.ensure_future(self.connection.close())

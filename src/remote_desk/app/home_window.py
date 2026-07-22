"""Ventana principal de la app unificada.

Pantalla de inicio con dos modos:
  * "Permitir control"  -> AgentPanel
  * "Conectar a equipo" -> ControllerPanel

Un QStackedWidget alterna entre inicio y cada modo; una barra superior permite
volver. Diseno sobrio, sin emojis (solo simbolos tipograficos).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from remote_desk import __version__
from remote_desk.common.config import AppConfig
from remote_desk.controller.ui.controller_panel import ControllerPanel

from .agent_panel import AgentPanel
from .theme import ACCENT, BG, BORDER, BORDER_HOVER, SURFACE, TEXT, TEXT_MUTED


class HomeWindow(QWidget):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.config = config
        self.setWindowTitle("2p2")
        self.resize(960, 660)
        self.setStyleSheet(f"background:{BG};")

        self.stack = QStackedWidget()
        self.agent_panel = AgentPanel(config)
        self.controller_panel = ControllerPanel(config)

        self._home_index = self.stack.addWidget(self._build_home())
        self._agent_index = self.stack.addWidget(self._wrap(self.agent_panel, "Permitir control"))
        self._controller_index = self.stack.addWidget(
            self._wrap(self.controller_panel, "Conectar a un equipo")
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.stack)

    # ------------------------------------------------------------ pantallas
    def _build_home(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(64, 56, 64, 32)
        outer.setSpacing(0)

        # Encabezado (alineado a la izquierda, sobrio).
        brand = QLabel("2p2")
        brand.setStyleSheet(
            f"color:{TEXT}; font-size:28px; font-weight:700; letter-spacing:2px;"
        )
        outer.addWidget(brand)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background:{ACCENT}; max-width:52px;")
        outer.addSpacing(10)
        outer.addWidget(rule)

        tagline = QLabel("Control remoto de escritorio  ·  cifrado de extremo a extremo")
        tagline.setStyleSheet(f"color:{TEXT_MUTED}; font-size:13px;")
        outer.addSpacing(14)
        outer.addWidget(tagline)

        outer.addSpacing(40)

        # Filas de seleccion de modo.
        outer.addWidget(
            self._mode_row(
                "01",
                "Permitir control",
                "Comparte tu ID y clave para que otro equipo controle este.",
                lambda: self.stack.setCurrentIndex(self._agent_index),
            )
        )
        outer.addSpacing(14)
        outer.addWidget(
            self._mode_row(
                "02",
                "Conectar a un equipo",
                "Introduce el ID y la clave de la maquina que quieres controlar.",
                lambda: self.stack.setCurrentIndex(self._controller_index),
            )
        )

        outer.addStretch(1)

        version = QLabel(f"version {__version__}")
        version.setStyleSheet(f"color:#5a626c; font-size:11px; letter-spacing:1px;")
        outer.addWidget(version)
        return page

    def _mode_row(self, index: str, title: str, desc: str, on_click) -> QWidget:  # noqa: ANN001
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(92)
        btn.clicked.connect(on_click)
        btn.setStyleSheet(
            "QPushButton{"
            f"background:{SURFACE}; border:1px solid {BORDER}; border-left:2px solid {BORDER};"
            "border-radius:6px; text-align:left;}"
            f"QPushButton:hover{{border:1px solid {BORDER_HOVER}; border-left:2px solid {ACCENT};}}"
        )

        lay = QHBoxLayout(btn)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(20)

        num = QLabel(index)
        num.setStyleSheet(f"color:{ACCENT}; font-size:15px; font-weight:600; letter-spacing:1px;")
        num.setFixedWidth(28)
        lay.addWidget(num)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet(f"color:{TEXT}; font-size:16px; font-weight:600;")
        d = QLabel(desc)
        d.setStyleSheet(f"color:{TEXT_MUTED}; font-size:12px;")
        text_box.addWidget(t)
        text_box.addWidget(d)
        lay.addLayout(text_box, stretch=1)

        chevron = QLabel("›")  # simbolo ">" tipografico, no emoji
        chevron.setStyleSheet(f"color:{TEXT_MUTED}; font-size:22px;")
        lay.addWidget(chevron)
        return btn

    def _wrap(self, panel: QWidget, title: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QWidget()
        bar.setStyleSheet(f"background:{BG}; border-bottom:1px solid {BORDER};")
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(16, 10, 16, 10)
        back = QPushButton("‹  Inicio")  # simbolo "<" tipografico
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet(
            f"QPushButton{{background:transparent; color:{TEXT_MUTED}; border:none; font-size:13px;}}"
            f"QPushButton:hover{{color:{TEXT};}}"
        )
        back.clicked.connect(lambda: self.stack.setCurrentIndex(self._home_index))
        heading = QLabel(title)
        heading.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        bar_l.addWidget(back)
        bar_l.addSpacing(14)
        bar_l.addWidget(heading)
        bar_l.addStretch(1)

        layout.addWidget(bar)
        layout.addWidget(panel, stretch=1)
        return page

    # --------------------------------------------------------------- cierre
    def closeEvent(self, event) -> None:  # noqa: ANN001, N802
        self.agent_panel.shutdown()
        self.controller_panel.shutdown()
        event.accept()

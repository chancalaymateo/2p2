"""Widget que muestra el video remoto y captura mouse/teclado del usuario.

Convierte los eventos de Qt en eventos del protocolo de control con coordenadas
NORMALIZADAS (0.0-1.0) respecto al area donde realmente se dibuja el video
(teniendo en cuenta el 'letterboxing' cuando el aspect ratio no coincide).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QWidget

from remote_desk.common.protocol import Control, MouseButton

_QT_BUTTON = {
    Qt.MouseButton.LeftButton: MouseButton.LEFT,
    Qt.MouseButton.RightButton: MouseButton.RIGHT,
    Qt.MouseButton.MiddleButton: MouseButton.MIDDLE,
}

# Teclas no imprimibles: Qt.Key -> nombre del protocolo (ver input_controller).
_QT_SPECIAL = {
    Qt.Key.Key_Return: "Enter",
    Qt.Key.Key_Enter: "Enter",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Up: "ArrowUp",
    Qt.Key.Key_Down: "ArrowDown",
    Qt.Key.Key_Left: "ArrowLeft",
    Qt.Key.Key_Right: "ArrowRight",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_PageUp: "PageUp",
    Qt.Key.Key_PageDown: "PageDown",
    Qt.Key.Key_Shift: "Shift",
    Qt.Key.Key_Control: "Control",
    Qt.Key.Key_Alt: "Alt",
    Qt.Key.Key_Meta: "Meta",
    Qt.Key.Key_CapsLock: "CapsLock",
}


class VideoWidget(QWidget):
    def __init__(self, send: Callable[[dict], None]) -> None:
        super().__init__()
        self._send = send
        self._pixmap: QPixmap | None = None
        self._enabled = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: #0b0e14;")

    # --------------------------------------------------------------- entrada
    def set_control_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def update_image(self, image: QImage) -> None:
        self._pixmap = QPixmap.fromImage(image)
        self.update()

    # --------------------------------------------------------------- dibujo
    def _target_rect(self) -> QRectF:
        """Rectangulo donde se dibuja el video (centrado, manteniendo aspecto)."""
        if not self._pixmap:
            return QRectF(0, 0, self.width(), self.height())
        pw, ph = self._pixmap.width(), self._pixmap.height()
        scale = min(self.width() / pw, self.height() / ph)
        w, h = pw * scale, ph * scale
        x = (self.width() - w) / 2
        y = (self.height() - h) / 2
        return QRectF(x, y, w, h)

    def paintEvent(self, event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._pixmap:
            painter.drawPixmap(self._target_rect(), self._pixmap, self._pixmap.rect())

    # --------------------------------------------------------- normalizacion
    def _normalize(self, pos: QPointF) -> tuple[float, float] | None:
        rect = self._target_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return None
        nx = (pos.x() - rect.x()) / rect.width()
        ny = (pos.y() - rect.y()) / rect.height()
        if not (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
            return None  # fuera del area de video: no enviamos
        return nx, ny

    # ------------------------------------------------------ eventos de mouse
    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._enabled:
            return
        norm = self._normalize(event.position())
        if norm:
            self._send({"type": Control.MOUSE_MOVE, "x": norm[0], "y": norm[1]})

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.setFocus()
        if not self._enabled:
            return
        norm = self._normalize(event.position())
        button = _QT_BUTTON.get(event.button())
        if norm and button:
            self._send(
                {"type": Control.MOUSE_DOWN, "x": norm[0], "y": norm[1], "button": button}
            )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not self._enabled:
            return
        norm = self._normalize(event.position())
        button = _QT_BUTTON.get(event.button())
        if norm and button:
            self._send(
                {"type": Control.MOUSE_UP, "x": norm[0], "y": norm[1], "button": button}
            )

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if not self._enabled:
            return
        delta = event.angleDelta()
        self._send(
            {
                "type": Control.MOUSE_SCROLL,
                "dx": 1 if delta.x() > 0 else -1 if delta.x() < 0 else 0,
                "dy": 1 if delta.y() > 0 else -1 if delta.y() < 0 else 0,
            }
        )

    # ---------------------------------------------------- eventos de teclado
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self._enabled and not event.isAutoRepeat():
            self._send({"type": Control.KEY_DOWN, "key": self._key_name(event)})

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self._enabled and not event.isAutoRepeat():
            self._send({"type": Control.KEY_UP, "key": self._key_name(event)})

    @staticmethod
    def _key_name(event: QKeyEvent) -> str:
        special = _QT_SPECIAL.get(Qt.Key(event.key()))
        if special:
            return special
        text = event.text()
        if text and text.isprintable() and text != " ":
            return text
        return ""

"""Inyeccion de eventos de mouse/teclado en la maquina del agente (via pynput).

Recibe eventos ya parseados del DataChannel de WebRTC. Las coordenadas llegan
normalizadas (0.0-1.0) para ser independientes de la resolucion; aqui se
escalan al tamano real de la pantalla capturada.
"""

from __future__ import annotations

from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key
from pynput.mouse import Button
from pynput.mouse import Controller as MouseController

from remote_desk.common.logging import setup_logging
from remote_desk.common.protocol import Control, MouseButton

log = setup_logging("agent.input")

_BUTTON_MAP = {
    MouseButton.LEFT: Button.left,
    MouseButton.RIGHT: Button.right,
    MouseButton.MIDDLE: Button.middle,
}

# Nombres especiales de tecla -> pynput Key. Las teclas normales ('a', '1', ...)
# se envian como caracter directo.
_SPECIAL_KEYS = {
    "Enter": Key.enter,
    "Backspace": Key.backspace,
    "Tab": Key.tab,
    "Escape": Key.esc,
    "Space": Key.space,
    "Delete": Key.delete,
    "ArrowUp": Key.up,
    "ArrowDown": Key.down,
    "ArrowLeft": Key.left,
    "ArrowRight": Key.right,
    "Home": Key.home,
    "End": Key.end,
    "PageUp": Key.page_up,
    "PageDown": Key.page_down,
    "Shift": Key.shift,
    "Control": Key.ctrl,
    "Alt": Key.alt,
    "Meta": Key.cmd,
    "CapsLock": Key.caps_lock,
}


class InputController:
    """Aplica eventos de control sobre el escritorio local."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self._w = screen_width
        self._h = screen_height

    def _to_pixels(self, nx: float, ny: float) -> tuple[int, int]:
        x = int(max(0.0, min(1.0, nx)) * self._w)
        y = int(max(0.0, min(1.0, ny)) * self._h)
        return x, y

    def handle(self, event: dict) -> None:
        """Procesa un unico evento de control. Nunca lanza hacia el caller."""
        try:
            self._handle(event)
        except Exception as exc:  # noqa: BLE001 - un evento malo no debe caer la sesion
            log.debug("evento de input ignorado (%s): %r", exc, event)

    def _handle(self, event: dict) -> None:
        etype = event.get("type")

        if etype == Control.MOUSE_MOVE:
            self._mouse.position = self._to_pixels(event["x"], event["y"])

        elif etype == Control.MOUSE_DOWN:
            self._mouse.position = self._to_pixels(event["x"], event["y"])
            self._mouse.press(_BUTTON_MAP.get(event.get("button"), Button.left))

        elif etype == Control.MOUSE_UP:
            self._mouse.position = self._to_pixels(event["x"], event["y"])
            self._mouse.release(_BUTTON_MAP.get(event.get("button"), Button.left))

        elif etype == Control.MOUSE_SCROLL:
            self._mouse.scroll(int(event.get("dx", 0)), int(event.get("dy", 0)))

        elif etype == Control.KEY_DOWN:
            self._keyboard.press(self._resolve_key(event.get("key", "")))

        elif etype == Control.KEY_UP:
            self._keyboard.release(self._resolve_key(event.get("key", "")))

    @staticmethod
    def _resolve_key(name: str):
        if name in _SPECIAL_KEYS:
            return _SPECIAL_KEYS[name]
        # Tecla imprimible normal: usamos el primer caracter.
        return name[:1] if name else ""

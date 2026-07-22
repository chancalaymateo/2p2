"""Tema visual central de la aplicacion.

Define la paleta y una hoja de estilos (QSS) global que se aplica a toda la app,
para un aspecto sobrio y consistente. Sin emojis: solo simbolos tipograficos.
"""

from __future__ import annotations

# Paleta (fuente unica de verdad del tema).
BG = "#101418"
SURFACE = "#171c22"
SURFACE_2 = "#1d232b"
BORDER = "#242b33"
BORDER_HOVER = "#3d4a57"
TEXT = "#e8eaed"
TEXT_MUTED = "#8a929c"
ACCENT = "#2f6fed"
ACCENT_HOVER = "#3f7cf5"
DANGER = "#c14a4a"

QSS = f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    color: {TEXT};
}}
QWidget {{
    background: {BG};
}}
QLabel {{
    background: transparent;
}}
QPushButton {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton:hover {{
    border-color: {BORDER_HOVER};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background: {SURFACE};
}}
QLineEdit {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QMessageBox {{
    background: {SURFACE};
}}
"""


def apply_theme(app) -> None:  # noqa: ANN001
    """Aplica la hoja de estilos global a la QApplication."""
    app.setStyleSheet(QSS)

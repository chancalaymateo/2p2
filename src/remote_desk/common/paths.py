"""Rutas de datos persistentes de la app (identidad, favoritos, etc.)."""

from __future__ import annotations

import os
from pathlib import Path

APP_FOLDER = "2p2"


def data_dir() -> Path:
    """Carpeta de datos por-usuario. Se crea si no existe."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_FOLDER
    d.mkdir(parents=True, exist_ok=True)
    return d

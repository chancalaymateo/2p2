"""Auto-instalacion del ejecutable (sin permisos de administrador).

Convierte el unico RemoteDesk.exe en un instalador portable: al ejecutarlo desde
cualquier carpeta (Descargas, USB, etc.) se copia a
`%LOCALAPPDATA%\\Programs\\RemoteDesk`, crea accesos directos y se relanza desde
ahi. Tambien implementa el reemplazo en caliente para las actualizaciones.

Todo esto solo tiene sentido cuando la app corre como .exe empaquetado
(`sys.frozen`); en desarrollo (`python -m`) estas funciones no hacen nada.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "RemoteDesk"
DISPLAY_NAME = "Remote-Desk"

# Evita que las llamadas a PowerShell abran ventanas de consola.
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


def is_frozen() -> bool:
    """True si corremos como ejecutable empaquetado (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def current_exe() -> Path:
    return Path(sys.executable).resolve()


def install_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "Programs" / APP_NAME


def installed_exe() -> Path:
    return install_dir() / f"{APP_NAME}.exe"


def is_installed() -> bool:
    return installed_exe().exists()


def running_from_install() -> bool:
    try:
        return current_exe() == installed_exe().resolve()
    except OSError:
        return False


# --------------------------------------------------------------------------- lnk
def _create_shortcut(link_path: Path, target: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath='{tgt}';"
        "$s.WorkingDirectory='{wd}';"
        "$s.Description='{desc}';"
        "$s.Save()"
    ).format(lnk=link_path, tgt=target, wd=target.parent, desc=DISPLAY_NAME)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            creationflags=_NO_WINDOW,
            check=False,
            timeout=15,
        )
    except Exception:  # noqa: BLE001 - un acceso directo fallido no es fatal
        pass


def create_shortcuts() -> None:
    target = installed_exe()
    appdata = os.environ.get("APPDATA")
    userprofile = os.environ.get("USERPROFILE") or str(Path.home())

    if appdata:
        start_menu = (
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / f"{DISPLAY_NAME}.lnk"
        )
        _create_shortcut(start_menu, target)

    desktop = Path(userprofile) / "Desktop" / f"{DISPLAY_NAME}.lnk"
    _create_shortcut(desktop, target)


# ----------------------------------------------------------------------- install
def perform_install() -> Path:
    """Copia este .exe a la carpeta de instalacion y crea accesos directos."""
    dest_dir = install_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = installed_exe()

    src = current_exe()
    if src != target:
        shutil.copy2(src, target)
    create_shortcuts()
    return target


def launch(path: Path) -> None:
    os.startfile(str(path))  # noqa: S606 - Windows


# ------------------------------------------------------------------ auto-update
def apply_update(target: str) -> None:
    """Reemplaza el .exe instalado con ESTE (descargado en temp) y lo relanza.

    Se invoca en la copia nueva mediante `RemoteDesk.exe --apply-update <target>`.
    Espera a que la instancia vieja libere el archivo, lo sustituye y arranca.
    """
    target_path = Path(target)
    src = current_exe()

    # Espera hasta ~10 s a que el ejecutable viejo se cierre y libere el lock.
    for _ in range(50):
        try:
            if target_path.exists():
                target_path.unlink()
            break
        except OSError:
            time.sleep(0.2)

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target_path)
    except OSError:
        # Si no se pudo reemplazar, al menos intentamos abrir lo que haya.
        pass

    launch(target_path)

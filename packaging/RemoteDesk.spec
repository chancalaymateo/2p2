# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller: empaqueta la app unificada en un unico RemoteDesk.exe.

Incluye Python + todas las dependencias nativas (aiortc/av/PySide6/...), de modo
que el usuario final no necesita instalar Python ni ejecutar pip.

Build:
    pyinstaller packaging/RemoteDesk.spec --noconfirm
"""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Paquetes con binarios nativos / recursos que conviene recolectar completos.
for pkg in ("av", "aiortc", "aioice", "pylibsrtp", "pyee", "mss", "pynput", "qasync"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h


block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Modo ONEFILE: todo (Python + librerias + binarios) queda dentro de un unico
# RemoteDesk.exe. El usuario final solo hace doble clic; no instala nada.
import os

_icon = "icon.ico" if os.path.exists(os.path.join(os.path.dirname(SPEC), "icon.ico")) else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RemoteDesk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # app GUI: sin ventana de consola
    disable_windowed_traceback=False,
    icon=_icon,
)

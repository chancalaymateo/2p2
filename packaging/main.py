"""Script de arranque para PyInstaller.

PyInstaller necesita un archivo de script como punto de entrada; este solo
delega en la app unificada. Mantiene el spec simple y estable.
"""

from remote_desk.app.__main__ import main

if __name__ == "__main__":
    main()

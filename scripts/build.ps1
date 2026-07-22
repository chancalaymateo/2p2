# =============================================================================
#  Build de Remote-Desk para Windows.
#  Genera:  dist\RemoteDesk\RemoteDesk.exe   (app autocontenida)
#           dist\RemoteDeskSetup.exe         (instalador, si Inno Setup esta)
#
#  Uso (desde la raiz del repo, con el venv activado):
#     .\scripts\build.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==> Instalando el paquete y dependencias de build..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -e ".[build]"

# Lee la version desde el paquete (fuente unica de verdad).
$Version = python -c "import remote_desk; print(remote_desk.__version__)"
Write-Host "==> Version: $Version" -ForegroundColor Cyan

Write-Host "==> Empaquetando con PyInstaller (onefile)..." -ForegroundColor Cyan
pyinstaller packaging/RemoteDesk.spec --noconfirm --clean

Write-Host "==> Ejecutable listo: dist\2p2.exe (un solo archivo)" -ForegroundColor Green

# --- Instalador con Inno Setup (opcional) ---
$Iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (-not $Iscc) {
    $default = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $default) { $Iscc = $default } else { $Iscc = $null }
}

if ($Iscc) {
    Write-Host "==> Generando instalador con Inno Setup..." -ForegroundColor Cyan
    & $Iscc "/DMyAppVersion=$Version" "packaging\installer.iss"
    Write-Host "==> Instalador listo en dist\RemoteDeskSetup.exe" -ForegroundColor Green
} else {
    Write-Host "Inno Setup (ISCC.exe) no encontrado; se omite el instalador." -ForegroundColor Yellow
    Write-Host "Instalalo desde https://jrsoftware.org/isdl.php y vuelve a ejecutar." -ForegroundColor Yellow
}

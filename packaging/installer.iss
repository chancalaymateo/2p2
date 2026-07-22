; ============================================================================
;  Inno Setup - Instalador de Remote-Desk (por-usuario, sin admin)
;  Compilar:  ISCC.exe /DMyAppVersion=0.1.0 packaging\installer.iss
;  Produce:   dist\RemoteDeskSetup.exe
; ============================================================================

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

#define MyAppName "Remote-Desk"
#define MyAppExeName "RemoteDesk.exe"
#define MyAppPublisher "Remote-Desk"

[Setup]
; AppId identifica la app entre versiones (no lo cambies una vez publicado).
AppId={{8F3A6B21-2C4D-4E9A-9B77-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; --- Instalacion por-usuario, SIN privilegios de administrador ---
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\RemoteDesk
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}

; Salida del instalador
OutputDir=..\dist
OutputBaseFilename=RemoteDeskSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Descomenta cuando agregues packaging\icon.ico:
; SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
; PyInstaller en modo onefile genera un unico dist\RemoteDesk.exe.
Source: "..\dist\RemoteDesk.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Ofrece abrir la app al terminar de instalar.
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

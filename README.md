# Remote-Desk

Sistema de **control remoto de escritorio** (estilo TeamViewer / RustDesk) escrito en
**Python puro**. Te conectas a un equipo con un **ID + clave** y controlas su
pantalla, mouse y teclado a distancia. El video y el control viajan **cifrados
extremo a extremo (P2P) con WebRTC**; el servidor central solo empareja.

> ⚠️ **Uso responsable.** Esta herramienta es para administración remota de equipos
> **propios o con autorización explícita** del dueño. El agente muestra un aviso y
> (por defecto) pide consentimiento antes de aceptar cada conexión.

---

## Arquitectura

```
   ┌────────────────────┐        señalización (WebSocket)       ┌────────────────────┐
   │    CONTROLADOR      │ ───────  ID + clave, SDP/ICE  ──────▶ │      SERVIDOR       │
   │  (GUI · PySide6)    │ ◀───────  empareja y retransmite ──── │  (websockets)       │
   └─────────┬──────────┘                                        └─────────┬──────────┘
             │                                                             │
             │              WebRTC P2P cifrado (DTLS-SRTP)                 │
             │   ◀── video de pantalla ───   ── input (data channel) ──▶  │
             └───────────────────────────  AGENTE  ──────────────────────┘
                                    (Windows · mss + pynput)
```

- **`server/`** — Señalización: registra agentes, empareja por ID+clave (con
  hash `scrypt` + rate-limiting) y retransmite el handshake WebRTC. **No ve** el
  contenido de la sesión.
- **`agent/`** — Corre en la máquina a controlar (Windows). Captura la pantalla
  (`mss`) como pista de video WebRTC e inyecta el input recibido (`pynput`).
- **`controller/`** — App de escritorio (PySide6) que muestra la pantalla remota
  y envía tu mouse/teclado.
- **`common/`** — Código compartido: configuración, protocolo, criptografía, WebRTC.

## Estructura del proyecto

```
remote-desk/
├── pyproject.toml            # metadatos, dependencias, scripts
├── .env.example              # plantilla de configuración
├── src/remote_desk/
│   ├── common/               # config, logging, crypto, protocolo, webrtc
│   ├── server/               # servidor de señalización
│   ├── agent/                # host: captura + inyección de input
│   ├── controller/           # panel del controlador (UI reutilizable)
│   │   └── ui/
│   ├── updater/              # auto-actualización (GitHub Releases + popup)
│   └── app/                  # app unificada (pantalla de inicio) ← ejecutable
├── packaging/                # PyInstaller spec + Inno Setup + entry
├── scripts/build.ps1         # build: .exe + instalador
├── .github/workflows/        # CI: publica el instalador al crear un tag
└── tests/                    # pruebas de lógica pura
```

---

## Instalación

Requiere **Python 3.10+**. En Windows, `aiortc` trae binarios precompilados
(no necesitas compilar FFmpeg).

```bash
python -m venv .venv
.venv\Scripts\activate           # PowerShell/CMD en Windows
pip install -e ".[dev]"          # instala el paquete + herramientas de dev
```

Copia la configuración y ajústala:

```bash
copy .env.example .env
```

## Uso (prueba local con 3 terminales)

**1. Servidor de señalización**
```bash
python -m remote_desk.server
```

**2. Agente** (en el equipo a controlar)
```bash
python -m remote_desk.agent
```
Imprime en consola el **ID** y la **CLAVE** de esta sesión.

**3. Controlador** (en tu equipo)
```bash
python -m remote_desk.controller
```
Escribe el ID y la clave, pulsa **Conectar**. El agente pedirá confirmación en su
consola; al aceptar verás su pantalla y podrás controlarla.

> Para probar entre dos máquinas distintas, apunta `SIGNALING_URL` en el `.env` de
> agente y controlador a la IP/host del servidor.

### App unificada (experiencia de usuario final)

En vez de los componentes sueltos, la app de escritorio junta agente y
controlador en una sola ventana con pantalla de inicio:

```bash
python -m remote_desk.app        # (o el ejecutable `remote-desk`)
```

- **Permitir control** → activa el agente y muestra tu **ID + clave**; cada
  conexión entrante pide tu confirmación con un diálogo.
- **Conectar a un equipo** → introduce ID + clave y controla la otra máquina.

*(El servidor de señalización sigue siendo un proceso aparte: `python -m remote_desk.server`.)*

---

## Distribución: un solo `.exe` auto-instalable

El usuario final **no instala Python ni dependencias**: todo va dentro del `.exe`.

```powershell
.\scripts\build.ps1
```

Genera **`dist\RemoteDesk.exe`** — un único archivo autocontenido (PyInstaller
onefile) que es **a la vez la app y su instalador**:

- Al ejecutarlo desde cualquier carpeta (Descargas, USB…), pregunta si instalarlo.
  Al aceptar, se copia a `%LOCALAPPDATA%\Programs\RemoteDesk`, crea accesos
  directos en menú inicio y escritorio, y se relanza desde ahí. **Sin permisos de
  administrador.**
- Modos de línea de comandos: `--install` (instala en silencio), `--portable`
  (corre sin instalar), `--apply-update <ruta>` (uso interno del auto-update).

Es exportable: copia ese `.exe` a cualquier máquina Windows y funciona.

## Auto-actualización (basada en `main`)

1. `GITHUB_REPO` ya apunta a tu repo (`chancalaymateo/2p2`).
2. **Cada push a `main`**, GitHub Actions (`.github/workflows/release.yml`)
   compila el `.exe`, calcula la versión `0.1.<nº de build>` y publica una
   **Release** con `RemoteDesk.exe` adjunto.
3. Al abrir la app instalada, esta consulta la última Release; si hay una versión
   mayor que la suya, muestra un **pop-up "Actualización disponible"**. Al aceptar,
   descarga el nuevo `.exe`, reemplaza el instalado en caliente y se reinicia.

> El número de versión se inyecta en el build (`_version.py`), así que no hay que
> editarlo a mano: cada build de `main` es una versión nueva.

---

## Seguridad

Implementado:
- **Cifrado P2P** de video e input (DTLS-SRTP, propio de WebRTC).
- **Clave por sesión** aleatoria (`secrets`), guardada solo como hash `scrypt`.
- **Rate-limiting / bloqueo** por intentos fallidos de clave.
- **Consentimiento explícito** en el agente antes de aceptar (configurable).
- Soporte **`wss://` (TLS)** para el canal de señalización.

Pendiente para producción (ver `docs`/issues):
- TLS obligatorio + verificación de certificados; TURN propio para NAT estricto.
- Cuentas de usuario, 2FA y lista de dispositivos de confianza.
- Firmar/actualizar el agente; ejecutar con privilegios mínimos.
- Auditoría de sesiones y opción de "solo ver" vs "control total".

## Pruebas

```bash
pytest
```

## Estado

PoC funcional: pantalla remota + control de mouse/teclado sobre WebRTC. La base de
carpetas y el protocolo están listos para crecer (multi-monitor, portapapeles,
transferencia de archivos, etc.).

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
│   └── controller/           # GUI del controlador
│       └── ui/
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

"""Protocolo de mensajes entre componentes.

Hay DOS canales de mensajes:

1. SEÑALIZACION (JSON sobre WebSocket, contra el servidor): sirve para
   registrar el agente, emparejar por ID+clave y retransmitir SDP/ICE.

2. CONTROL (JSON sobre el DataChannel de WebRTC, P2P): transporta los
   eventos de mouse/teclado del controlador hacia el agente.

Mantener estos nombres sincronizados es la unica fuente de verdad del
contrato entre servidor, agente y controlador.
"""

from __future__ import annotations

import json
from typing import Any

# ----------------------------------------------------------------------------
# Canal de SEÑALIZACION (WebSocket)
# ----------------------------------------------------------------------------


class Signal:
    # Agente -> Servidor
    REGISTER_AGENT = "register-agent"
    ACCEPT_CONNECTION = "accept-connection"
    REJECT_CONNECTION = "reject-connection"

    # Controlador -> Servidor
    CONNECT_REQUEST = "connect-request"

    # Servidor -> Agente
    AGENT_REGISTERED = "agent-registered"
    INCOMING_CONNECTION = "incoming-connection"

    # Servidor -> Controlador
    CONNECTION_ACCEPTED = "connection-accepted"
    CONNECTION_REJECTED = "connection-rejected"

    # Servidor -> ambos
    ERROR = "error"
    PEER_DISCONNECTED = "peer-disconnected"

    # Relay bidireccional de WebRTC (agente <-> controlador via servidor)
    WEBRTC_OFFER = "webrtc-offer"
    WEBRTC_ANSWER = "webrtc-answer"
    WEBRTC_ICE = "webrtc-ice"


# ----------------------------------------------------------------------------
# Canal de CONTROL (DataChannel WebRTC)
# ----------------------------------------------------------------------------


class Control:
    MOUSE_MOVE = "mouse-move"
    MOUSE_DOWN = "mouse-down"
    MOUSE_UP = "mouse-up"
    MOUSE_SCROLL = "mouse-scroll"
    KEY_DOWN = "key-down"
    KEY_UP = "key-up"


# Botones de mouse normalizados en el protocolo.
class MouseButton:
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


# ----------------------------------------------------------------------------
# Helpers de (de)serializacion
# ----------------------------------------------------------------------------


def make(msg_type: str, **payload: Any) -> str:
    """Construye un mensaje JSON con su campo `type`."""
    return json.dumps({"type": msg_type, **payload})


def parse(raw: str | bytes) -> dict[str, Any]:
    """Parsea un mensaje JSON entrante. Lanza ValueError si es invalido."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"mensaje no es JSON valido: {exc}") from exc
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError("mensaje sin campo 'type'")
    return data

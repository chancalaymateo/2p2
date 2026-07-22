"""Registro de agentes conectados y sesiones de emparejamiento activas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from websockets.server import WebSocketServerProtocol


@dataclass
class Agent:
    """Un agente (maquina controlable) actualmente conectado al servidor."""

    agent_id: str  # normalizado (solo digitos)
    display_id: str  # formateado '123 456 789'
    ws: WebSocketServerProtocol
    salt_hex: str
    hash_hex: str
    device_uuid: str = ""  # identifica el dispositivo (permite reclamar su ID)


@dataclass
class Session:
    """Emparejamiento activo entre un controlador y un agente."""

    token: str
    agent_id: str
    agent_ws: WebSocketServerProtocol
    controller_ws: WebSocketServerProtocol


@dataclass
class Registry:
    """Estado en memoria del servidor.

    Para un despliegue multi-instancia esto se reemplazaria por Redis u otro
    backend compartido; la interfaz se mantiene igual.
    """

    agents: dict[str, Agent] = field(default_factory=dict)
    sessions: dict[str, Session] = field(default_factory=dict)
    # ws -> token, para limpiar rapido al desconectar.
    _ws_sessions: dict[Any, str] = field(default_factory=dict)

    # --- Agentes ---
    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.agents.get(agent_id)

    def remove_agent_by_ws(self, ws: WebSocketServerProtocol) -> Agent | None:
        for agent_id, agent in list(self.agents.items()):
            if agent.ws is ws:
                del self.agents[agent_id]
                return agent
        return None

    # --- Sesiones ---
    def add_session(self, session: Session) -> None:
        self.sessions[session.token] = session
        self._ws_sessions[session.agent_ws] = session.token
        self._ws_sessions[session.controller_ws] = session.token

    def get_session(self, token: str) -> Session | None:
        return self.sessions.get(token)

    def remove_session(self, token: str) -> Session | None:
        session = self.sessions.pop(token, None)
        if session:
            self._ws_sessions.pop(session.agent_ws, None)
            self._ws_sessions.pop(session.controller_ws, None)
        return session

    def find_session_by_ws(self, ws: WebSocketServerProtocol) -> Session | None:
        token = self._ws_sessions.get(ws)
        return self.sessions.get(token) if token else None

"""Carga de configuracion desde variables de entorno / archivo .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Carga el archivo .env de la raiz del proyecto (si existe) una sola vez.
load_dotenv()


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class IceConfig:
    """Servidores STUN/TURN para atravesar NAT."""

    stun_urls: list[str] = field(default_factory=list)
    turn_urls: list[str] = field(default_factory=list)
    turn_username: str = ""
    turn_password: str = ""

    @classmethod
    def from_env(cls) -> "IceConfig":
        return cls(
            stun_urls=_split(os.getenv("STUN_URLS", "stun:stun.l.google.com:19302")),
            turn_urls=_split(os.getenv("TURN_URLS", "")),
            turn_username=os.getenv("TURN_USERNAME", ""),
            turn_password=os.getenv("TURN_PASSWORD", ""),
        )


@dataclass(frozen=True)
class AppConfig:
    """Configuracion global compartida."""

    signaling_host: str = "0.0.0.0"
    signaling_port: int = 8765
    signaling_url: str = "ws://127.0.0.1:8765"
    tls_cert_file: str = ""
    tls_key_file: str = ""
    agent_require_consent: bool = True
    max_auth_attempts: int = 5
    auth_lockout_seconds: int = 60
    ice: IceConfig = field(default_factory=IceConfig)

    @classmethod
    def load(cls) -> "AppConfig":
        return cls(
            signaling_host=os.getenv("SIGNALING_HOST", "0.0.0.0"),
            signaling_port=int(os.getenv("SIGNALING_PORT", "8765")),
            signaling_url=os.getenv("SIGNALING_URL", "ws://127.0.0.1:8765"),
            tls_cert_file=os.getenv("TLS_CERT_FILE", ""),
            tls_key_file=os.getenv("TLS_KEY_FILE", ""),
            agent_require_consent=os.getenv("AGENT_REQUIRE_CONSENT", "true").lower() == "true",
            max_auth_attempts=int(os.getenv("MAX_AUTH_ATTEMPTS", "5")),
            auth_lockout_seconds=int(os.getenv("AUTH_LOCKOUT_SECONDS", "60")),
            ice=IceConfig.from_env(),
        )

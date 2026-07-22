"""Identidad persistente y unica del equipo (estilo TeamViewer).

El ID se deriva de forma DETERMINISTA de un UUID de dispositivo + un 'nonce',
asi que es **permanente**: el mismo equipo obtiene siempre el mismo ID mientras
no se restablezca. Al restablecer se cambia el nonce -> nuevo ID.

Unicidad:
  * Localmente: derivado de un UUID de 122 bits, la probabilidad de que dos
    equipos generen el mismo ID de 9 digitos es minima.
  * Globalmente garantizada: el servidor verifica el ID al registrarse y, ante
    una colision entre equipos distintos conectados, asigna otro (ver servidor).

Se guarda en `%LOCALAPPDATA%\\2p2\\identity.json`. La clave se guarda en claro
localmente (como TeamViewer/AnyDesk) y solo su hash viaja/permanece en el servidor.
"""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import asdict, dataclass

from . import crypto
from .paths import data_dir

_IDENTITY_FILE = "identity.json"


def _luhn_check_digit(number: str) -> int:
    """Digito verificador de Luhn para una cadena de digitos."""
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def _derive_id(device_uuid: str, nonce: str) -> str:
    """Deriva un ID de 9 digitos (8 + verificador Luhn), agrupado '123 456 789'."""
    import hashlib

    digest = hashlib.sha256(f"{device_uuid}:{nonce}".encode()).digest()
    base = f"{int.from_bytes(digest[:8], 'big') % 10**8:08d}"
    digits = base + str(_luhn_check_digit(base))
    return f"{digits[0:3]} {digits[3:6]} {digits[6:9]}"


@dataclass
class Identity:
    device_uuid: str
    nonce: str
    id: str  # display '123 456 789'
    password: str

    def path(self):  # noqa: ANN201
        return data_dir() / _IDENTITY_FILE

    def save(self) -> None:
        self.path().write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def credentials_hash(self) -> tuple[str, str]:
        """(salt, hash) de la clave actual, para enviar al servidor."""
        return crypto.hash_password(self.password)


def _new(device_uuid: str | None = None) -> Identity:
    device = device_uuid or uuid.uuid4().hex
    nonce = secrets.token_hex(4)
    return Identity(
        device_uuid=device,
        nonce=nonce,
        id=_derive_id(device, nonce),
        password=crypto.generate_password(),
    )


def load_or_create() -> Identity:
    """Carga la identidad guardada o crea una nueva y la persiste."""
    file = data_dir() / _IDENTITY_FILE
    if file.exists():
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            return Identity(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass  # archivo corrupto: regeneramos
    ident = _new()
    ident.save()
    return ident


def reset(identity: Identity, *, new_password: bool = True) -> Identity:
    """Restablece el ID (nuevo nonce) y opcionalmente la clave. Persiste."""
    identity.nonce = secrets.token_hex(4)
    identity.id = _derive_id(identity.device_uuid, identity.nonce)
    if new_password:
        identity.password = crypto.generate_password()
    identity.save()
    return identity


def set_granted_id(identity: Identity, granted: str) -> Identity:
    """Si el servidor asigno otro ID (colision), lo persistimos."""
    if granted and granted != identity.id:
        identity.id = granted
        identity.save()
    return identity

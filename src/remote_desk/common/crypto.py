"""Utilidades criptograficas: generacion de IDs, claves y hashing seguro.

Todo se apoya en el modulo `secrets` (CSPRNG) y en `hashlib.scrypt` para el
hashing de claves. Las claves en texto plano NUNCA se persisten: el servidor
solo guarda (salt, hash) y compara en tiempo constante.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# Alfabeto sin caracteres ambiguos (0/O, 1/l/I) para las claves de sesion.
_UNAMBIGUOUS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"

# Parametros de scrypt (coste CPU/memoria). N debe ser potencia de 2.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def generate_agent_id() -> str:
    """Genera un ID de 9 digitos, agrupado estilo TeamViewer: '123 456 789'."""
    digits = "".join(secrets.choice("0123456789") for _ in range(9))
    return f"{digits[0:3]} {digits[3:6]} {digits[6:9]}"


def generate_password(length: int = 8) -> str:
    """Genera una clave de sesion aleatoria y legible."""
    return "".join(secrets.choice(_UNAMBIGUOUS) for _ in range(length))


def hash_password(password: str) -> tuple[str, str]:
    """Devuelve (salt_hex, hash_hex) para una clave dada."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    """Verifica una clave contra (salt, hash) en tiempo constante."""
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return hmac.compare_digest(digest.hex(), expected_hash_hex)


def generate_session_token() -> str:
    """Token opaco para identificar una sesion de emparejamiento."""
    return secrets.token_urlsafe(24)


def normalize_id(raw: str) -> str:
    """Normaliza un ID quitando espacios para poder compararlo/indexarlo."""
    return "".join(ch for ch in raw if ch.isdigit())

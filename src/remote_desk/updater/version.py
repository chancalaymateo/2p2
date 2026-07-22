"""Comparacion de versiones semanticas (subconjunto: MAJOR.MINOR.PATCH)."""

from __future__ import annotations

import re

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Extrae (major, minor, patch) de cadenas como 'v1.2.3' o '1.2.3-beta'."""
    match = _SEMVER.search(text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def is_newer(candidate: str, current: str) -> bool:
    """True si `candidate` es una version estrictamente mayor que `current`."""
    c = parse_version(candidate)
    cur = parse_version(current)
    if c is None or cur is None:
        return False
    return c > cur

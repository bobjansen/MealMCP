#!/usr/bin/env python3
"""Short ID utilities for recipe management.

Short IDs are generated from the numeric primary key as an uppercase
hexadecimal string prefixed with ``R`` and suffixed with a single checksum
character.  The checksum is a base36 character derived from the numeric id.

For example, database ID ``15`` becomes ``RFF`` and ``255`` becomes ``RFF3``.
"""

import re
from typing import Optional

PREFIX = "R"
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ID_RE = re.compile(r"^R[0-9A-F]+[0-9A-Z]$")


def _checksum(numeric_id: int) -> str:
    """Return the checksum character for the given numeric id."""
    return ALPHABET[numeric_id % 36]


def generate_short_id(numeric_id: int) -> str:
    """Generate a short ID from a numeric database ID using hex encoding."""
    if numeric_id <= 0:
        raise ValueError("Numeric ID must be positive")
    body = f"{numeric_id:X}"
    return f"{PREFIX}{body}{_checksum(numeric_id)}"


def parse_short_id(short_id: str) -> Optional[int]:
    """Parse a short ID back to the original numeric ID."""
    if not short_id or not isinstance(short_id, str):
        return None

    short_id = short_id.strip().upper()
    if not ID_RE.fullmatch(short_id):
        return None

    body = short_id[1:-1]
    checksum = short_id[-1]
    try:
        numeric_id = int(body, 16)
    except ValueError:
        return None

    if _checksum(numeric_id) != checksum:
        return None

    return numeric_id


def is_valid_short_id(short_id: str) -> bool:
    """Check if a short ID is valid."""
    return parse_short_id(short_id) is not None

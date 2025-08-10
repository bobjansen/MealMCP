#!/usr/bin/env python3
"""
Short ID utilities for recipe management.
Generates human-friendly short IDs with checksums to prevent confusion.

Format: R{number}{checksum}
Example: R123X, R456M, R789Q

- R prefix indicates it's a recipe ID
- Base 36 encoding for compact representation
- Single checksum character to catch typos
- Maximum ~46k unique IDs (R1A - RZZZ)
"""

import string
import hashlib
from typing import Optional
from error_utils import validate_required_params

# Constants
ALPHABET = string.digits + string.ascii_uppercase
PREFIX = "R"


def generate_short_id(numeric_id: int) -> str:
    """
    Generate a short ID from a numeric database ID.

    Args:
        numeric_id: The database ID (integer)

    Returns:
        str: Short ID in format R{base36}{checksum}

    Example:
        generate_short_id(123) -> "R3FX"
        generate_short_id(1000) -> "RRSM"

    Raises:
        ValueError: If numeric_id is not positive
    """
    if numeric_id <= 0:
        raise ValueError("Numeric ID must be positive")

    # Convert to base36 using Python's built-in functions
    base36 = _to_base36(numeric_id)

    # Generate checksum
    checksum = _calculate_checksum(base36)

    return f"{PREFIX}{base36}{checksum}"


def parse_short_id(short_id: str) -> Optional[int]:
    """
    Parse a short ID back to the original numeric ID.

    Args:
        short_id: Short ID string (e.g., "R3FX")

    Returns:
        Optional[int]: Original numeric ID if valid, None if invalid
    """
    if not short_id or not isinstance(short_id, str):
        return None

    short_id = short_id.upper().strip()

    # Check format
    if not short_id.startswith(PREFIX) or len(short_id) < 3:
        return None

    # Extract parts
    body = short_id[1:-1]  # Remove prefix and checksum
    provided_checksum = short_id[-1]

    # Validate checksum
    expected_checksum = _calculate_checksum(body)
    if provided_checksum != expected_checksum:
        return None

    try:
        # Convert back to decimal using built-in int()
        return int(body, 36)
    except ValueError:
        return None


def is_valid_short_id(short_id: str) -> bool:
    """Check if a short ID is valid."""
    return parse_short_id(short_id) is not None


def _to_base36(num: int) -> str:
    """Convert integer to base36 string using built-in functions."""
    if num == 0:
        return "0"

    # Use numpy.base_repr equivalent logic but simpler
    digits = []
    while num:
        num, remainder = divmod(num, 36)
        digits.append(ALPHABET[remainder])
    return "".join(reversed(digits))


def _calculate_checksum(data: str) -> str:
    """Calculate single-character checksum from data."""
    # Use MD5 hash and map to our alphabet
    hash_obj = hashlib.md5(data.encode("utf-8"))
    hex_digest = hash_obj.hexdigest()

    # Take first hex character and map to base36 alphabet
    hex_char = hex_digest[0].upper()

    # Map 0-9 directly, A-F to A-F (both are in our alphabet)
    return hex_char if hex_char in ALPHABET else "0"

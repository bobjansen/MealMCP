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


class ShortIDGenerator:
    """Generate and validate short recipe IDs with checksums."""

    # Base36 alphabet (0-9, A-Z) - case insensitive
    ALPHABET = string.digits + string.ascii_uppercase
    PREFIX = "R"

    @classmethod
    def generate(cls, numeric_id: int) -> str:
        """
        Generate a short ID from a numeric database ID.

        Args:
            numeric_id: The database ID (integer)

        Returns:
            str: Short ID in format R{base36}{checksum}

        Example:
            generate(123) -> "R3FX"
            generate(1000) -> "RRSM"
        """
        if numeric_id <= 0:
            raise ValueError("Numeric ID must be positive")

        # Convert to base36
        base36 = cls._to_base36(numeric_id)

        # Generate checksum
        checksum = cls._calculate_checksum(base36)

        return f"{cls.PREFIX}{base36}{checksum}"

    @classmethod
    def parse(cls, short_id: str) -> Optional[int]:
        """
        Parse a short ID back to the original numeric ID.

        Args:
            short_id: Short ID string (e.g., "R3FX")

        Returns:
            Optional[int]: Original numeric ID if valid, None if invalid
        """
        short_id = short_id.upper().strip()

        # Check format
        if not short_id.startswith(cls.PREFIX) or len(short_id) < 3:
            return None

        # Extract parts
        body = short_id[1:-1]  # Remove prefix and checksum
        provided_checksum = short_id[-1]

        # Validate checksum
        expected_checksum = cls._calculate_checksum(body)
        if provided_checksum != expected_checksum:
            return None

        try:
            # Convert back to decimal
            return cls._from_base36(body)
        except ValueError:
            return None

    @classmethod
    def is_valid(cls, short_id: str) -> bool:
        """Check if a short ID is valid."""
        return cls.parse(short_id) is not None

    @classmethod
    def _to_base36(cls, num: int) -> str:
        """Convert integer to base36 string."""
        if num == 0:
            return "0"

        digits = []
        while num:
            num, remainder = divmod(num, 36)
            digits.append(cls.ALPHABET[remainder])
        return "".join(reversed(digits))

    @classmethod
    def _from_base36(cls, base36_str: str) -> int:
        """Convert base36 string to integer."""
        base36_str = base36_str.upper()
        result = 0
        for char in base36_str:
            if char not in cls.ALPHABET:
                raise ValueError(f"Invalid character in base36: {char}")
            result = result * 36 + cls.ALPHABET.index(char)
        return result

    @classmethod
    def _calculate_checksum(cls, data: str) -> str:
        """Calculate single-character checksum."""
        # Use MD5 hash for simplicity and take first character
        hash_obj = hashlib.md5(data.encode("utf-8"))
        hex_digest = hash_obj.hexdigest().upper()

        # Map hex digit to our alphabet for consistency
        hex_char = hex_digest[0]
        if hex_char in "0123456789":
            return hex_char
        else:
            # Map A-F to letters
            hex_to_alpha = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F"}
            return hex_to_alpha[hex_char]

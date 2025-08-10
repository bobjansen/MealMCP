"""Tests for short ID utilities."""

import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from short_id_utils import generate_short_id, parse_short_id, is_valid_short_id


class TestShortIDUtils:
    """Test cases for the short ID utilities."""

    def test_generate_and_parse_valid_ids(self):
        """Test generating and parsing valid short IDs."""
        test_cases = [1, 10, 255, 256, 4096]

        for test_id in test_cases:
            short_id = generate_short_id(test_id)
            parsed_id = parse_short_id(short_id)
            is_valid = is_valid_short_id(short_id)

            assert parsed_id == test_id, f"Expected {test_id}, got {parsed_id}"
            assert is_valid is True, f"Short ID {short_id} should be valid"
            assert isinstance(short_id, str), "Generated ID should be a string"
            assert len(short_id) >= 2, "Short ID should have at least 2 characters"

    def test_edge_cases(self):
        """Test edge cases and invalid inputs."""
        edge_cases = [
            ("", None),  # empty string
            ("R", None),  # missing body and checksum
            ("RZ", None),  # missing checksum and invalid body
            ("RF", None),  # missing checksum for body 'F'
            ("R1G", None),  # wrong checksum for id 1
            ("invalid", None),  # not in short id format
        ]

        for case, expected in edge_cases:
            result = parse_short_id(case)
            is_valid = is_valid_short_id(case)

            assert (
                result == expected
            ), f"Expected '{case}' to parse to {expected}, got {result}"
            assert is_valid is False, f"Edge case '{case}' should not be valid"

    def test_round_trip_consistency(self):
        """Test that generate->parse is consistent for a range of values."""
        for test_id in range(1, 100):
            short_id = generate_short_id(test_id)
            parsed_id = parse_short_id(short_id)

            assert (
                parsed_id == test_id
            ), f"Round trip failed for {test_id}: {short_id} -> {parsed_id}"

    def test_generate_with_invalid_input(self):
        """Test generate method with invalid inputs."""
        invalid_inputs = [0, -1, -100]

        for invalid_id in invalid_inputs:
            with pytest.raises(ValueError):
                generate_short_id(invalid_id)

    def test_uniqueness_of_generated_ids(self):
        """Test that different input IDs generate different short IDs."""
        generated_ids = set()

        for test_id in range(1, 1000):
            short_id = generate_short_id(test_id)
            assert (
                short_id not in generated_ids
            ), f"Duplicate short ID {short_id} for input {test_id}"
            generated_ids.add(short_id)

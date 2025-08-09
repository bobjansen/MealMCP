"""Tests for short ID utilities."""

import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from short_id_utils import ShortIDGenerator


class TestShortIDGenerator:
    """Test cases for the ShortIDGenerator class."""

    def test_generate_and_parse_valid_ids(self):
        """Test generating and parsing valid short IDs."""
        test_cases = [1, 10, 123, 1000, 9999, 46655]  # 46655 = ZZZ in base36

        for test_id in test_cases:
            short_id = ShortIDGenerator.generate(test_id)
            parsed_id = ShortIDGenerator.parse(short_id)
            is_valid = ShortIDGenerator.is_valid(short_id)

            assert parsed_id == test_id, f"Expected {test_id}, got {parsed_id}"
            assert is_valid is True, f"Short ID {short_id} should be valid"
            assert isinstance(short_id, str), "Generated ID should be a string"
            assert len(short_id) >= 2, "Short ID should have at least 2 characters"

    def test_invalid_checksum_detection(self):
        """Test that invalid checksums are properly detected."""
        test_cases = [123, 1000, 9999]

        for test_id in test_cases:
            short_id = ShortIDGenerator.generate(test_id)

            if len(short_id) > 2:
                # Create invalid checksum by changing last character
                invalid_id = (
                    short_id[:-1] + "X" if short_id[-1] != "X" else short_id[:-1] + "Y"
                )

                invalid_parsed = ShortIDGenerator.parse(invalid_id)
                is_valid = ShortIDGenerator.is_valid(invalid_id)

                assert (
                    invalid_parsed is None
                ), f"Invalid ID {invalid_id} should parse to None"
                assert is_valid is False, f"Invalid ID {invalid_id} should not be valid"

    def test_edge_cases(self):
        """Test edge cases and invalid inputs."""
        edge_cases = [
            ("", None),
            ("R", None),
            ("RX", None),
            ("RXYZ", None),
            ("invalid", None),
            ("r123x", None),  # lowercase should be invalid
            ("R123X", None),  # assuming this is invalid based on the original test
        ]

        for case, expected in edge_cases:
            result = ShortIDGenerator.parse(case)
            is_valid = ShortIDGenerator.is_valid(case)

            assert (
                result == expected
            ), f"Expected '{case}' to parse to {expected}, got {result}"
            assert is_valid is False, f"Edge case '{case}' should not be valid"

    def test_round_trip_consistency(self):
        """Test that generate->parse is consistent for a range of values."""
        for test_id in range(1, 100):
            short_id = ShortIDGenerator.generate(test_id)
            parsed_id = ShortIDGenerator.parse(short_id)

            assert (
                parsed_id == test_id
            ), f"Round trip failed for {test_id}: {short_id} -> {parsed_id}"

    def test_generate_with_invalid_input(self):
        """Test generate method with invalid inputs."""
        invalid_inputs = [0, -1, -100]

        for invalid_id in invalid_inputs:
            with pytest.raises((ValueError, AssertionError)):
                ShortIDGenerator.generate(invalid_id)

    def test_uniqueness_of_generated_ids(self):
        """Test that different input IDs generate different short IDs."""
        generated_ids = set()

        for test_id in range(1, 1000):
            short_id = ShortIDGenerator.generate(test_id)
            assert (
                short_id not in generated_ids
            ), f"Duplicate short ID {short_id} for input {test_id}"
            generated_ids.add(short_id)

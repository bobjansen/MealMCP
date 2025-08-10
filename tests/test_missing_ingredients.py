"""
Tests for missing ingredients calculation with unit conversion handling.
Focuses on the core logic without Flask integration complexity.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pantry_manager_sqlite import SQLitePantryManager
from db_setup import setup_database


class TestMissingIngredientsCalculation(unittest.TestCase):
    """Test missing ingredients calculation with various unit conversion scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Initialize database with proper setup
        setup_database(self.db_path)
        self.pantry = SQLitePantryManager(self.db_path)

        # Set up test data
        self._setup_test_data()

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _setup_test_data(self):
        """Set up test ingredients, units, and pantry contents."""
        # Add custom unit for honey pot
        self.pantry.set_unit("Pot of honey", "ml", 350)  # 350ml pot

        # Add ingredients to pantry
        self.pantry.add_item("honey", 1, "Pot of honey")  # 350ml of honey
        self.pantry.add_item("flour", 500, "Gram")  # 500g flour
        self.pantry.add_item("butter", 200, "Gram")  # 200g butter
        self.pantry.add_item("milk", 1, "Liter")  # 1L milk
        self.pantry.add_item("eggs", 6, "Piece")  # 6 eggs

    def test_unit_conversion_honey_tablespoons_sufficient(self):
        """Test honey conversion from pot to tablespoons when we have enough."""
        # Recipe needs 2 tablespoons of honey (30ml)
        # We have 1 pot = 350ml, so we have enough
        needed = 2  # tablespoons
        available = self.pantry.get_total_item_quantity("honey", "Tablespoon")

        # 350ml / 15ml per tablespoon = 23.33 tablespoons available
        self.assertAlmostEqual(available, 350 / 15, places=2)
        self.assertGreater(available, needed)

        # Missing calculation
        missing = max(0, needed - available)
        self.assertEqual(missing, 0)

    def test_unit_conversion_honey_tablespoons_insufficient(self):
        """Test honey conversion when we need more than available."""
        # Recipe needs 25 tablespoons of honey (375ml)
        # We have 1 pot = 350ml, so we need 25ml more
        needed = 25  # tablespoons = 375ml
        available = self.pantry.get_total_item_quantity("honey", "Tablespoon")

        # Available: 350ml / 15ml per tablespoon = 23.33 tablespoons
        expected_available = 350 / 15
        self.assertAlmostEqual(available, expected_available, places=2)
        self.assertLess(available, needed)

        # Missing calculation
        missing = needed - available
        expected_missing = 25 - (350 / 15)  # About 1.67 tablespoons
        self.assertAlmostEqual(missing, expected_missing, places=2)

    def test_unit_conversion_flour_grams_to_kilograms(self):
        """Test flour conversion between grams and kilograms."""
        # Recipe needs 0.6kg of flour (600g)
        # We have 500g, so we're missing 100g
        needed_kg = 0.6
        available_kg = self.pantry.get_total_item_quantity("flour", "Kilogram")

        # Available: 500g / 1000g per kg = 0.5kg
        self.assertAlmostEqual(available_kg, 0.5, places=3)
        self.assertLess(available_kg, needed_kg)

        # Missing calculation in original units (grams)
        needed_g = 600
        available_g = self.pantry.get_total_item_quantity("flour", "Gram")
        missing_g = needed_g - available_g

        self.assertEqual(available_g, 500)
        self.assertEqual(missing_g, 100)

    def test_unit_conversion_milk_liters_to_cups(self):
        """Test milk conversion from liters to cups."""
        # Recipe needs 3 cups of milk (720ml)
        # We have 1L = 1000ml, so we have enough
        needed_cups = 3
        available_cups = self.pantry.get_total_item_quantity("milk", "Cup")

        # Available: 1000ml / 240ml per cup = 4.17 cups
        expected_available = 1000 / 240
        self.assertAlmostEqual(available_cups, expected_available, places=2)
        self.assertGreater(available_cups, needed_cups)

        # Missing calculation
        missing = max(0, needed_cups - available_cups)
        self.assertEqual(missing, 0)

    def test_incompatible_unit_bases(self):
        """Test ingredients with incompatible unit bases (weight vs volume)."""
        # Add a special ingredient measured in grams
        self.pantry.add_item("spice", 50, "Gram")  # 50g of spice

        # Try to get quantity in cups (volume unit)
        # This should return 0 since grams and cups have different base units
        available_cups = self.pantry.get_total_item_quantity("spice", "Cup")
        self.assertEqual(available_cups, 0.0)

        # Recipe asking for spice in cups should show all as missing
        needed_cups = 1
        missing = needed_cups - available_cups
        self.assertEqual(missing, 1.0)

    def test_missing_ingredient_not_in_pantry(self):
        """Test calculation for ingredient not in pantry at all."""
        # Vanilla is not in our pantry
        available = self.pantry.get_total_item_quantity("vanilla", "Teaspoon")
        self.assertEqual(available, 0.0)

        # Recipe needs 1 teaspoon of vanilla
        needed = 1
        missing = needed - available
        self.assertEqual(missing, 1.0)

    def test_complex_recipe_missing_ingredients_calculation(self):
        """Test complete missing ingredients calculation for a complex recipe."""
        # Recipe ingredients with mixed availability
        recipe_ingredients = [
            {
                "name": "honey",
                "quantity": 2,
                "unit": "Tablespoon",
            },  # Available (30ml needed, 350ml available)
            {
                "name": "flour",
                "quantity": 300,
                "unit": "Gram",
            },  # Available (300g needed, 500g available)
            {
                "name": "butter",
                "quantity": 250,
                "unit": "Gram",
            },  # Missing (250g needed, 200g available)
            {
                "name": "milk",
                "quantity": 1,
                "unit": "Cup",
            },  # Available (240ml needed, 1000ml available)
            {
                "name": "eggs",
                "quantity": 8,
                "unit": "Piece",
            },  # Missing (8 needed, 6 available)
            {
                "name": "vanilla",
                "quantity": 1,
                "unit": "Teaspoon",
            },  # Missing (not in pantry)
        ]

        missing_ingredients = []
        available_ingredients = []

        for ingredient in recipe_ingredients:
            needed_quantity = ingredient["quantity"]
            available_quantity = self.pantry.get_total_item_quantity(
                ingredient["name"], ingredient["unit"]
            )

            if available_quantity < needed_quantity:
                missing_ingredients.append(
                    {
                        "name": ingredient["name"],
                        "needed": needed_quantity,
                        "available": available_quantity,
                        "missing": needed_quantity - available_quantity,
                        "unit": ingredient["unit"],
                    }
                )
            else:
                available_ingredients.append(
                    {
                        "name": ingredient["name"],
                        "needed": needed_quantity,
                        "available": available_quantity,
                        "unit": ingredient["unit"],
                    }
                )

        # Should have 3 available ingredients
        self.assertEqual(len(available_ingredients), 3)
        available_names = [ing["name"] for ing in available_ingredients]
        self.assertIn("honey", available_names)
        self.assertIn("flour", available_names)
        self.assertIn("milk", available_names)

        # Should have 3 missing ingredients
        self.assertEqual(len(missing_ingredients), 3)
        missing_names = [ing["name"] for ing in missing_ingredients]
        self.assertIn("butter", missing_names)
        self.assertIn("eggs", missing_names)
        self.assertIn("vanilla", missing_names)

        # Check specific missing quantities
        butter_missing = next(
            ing for ing in missing_ingredients if ing["name"] == "butter"
        )
        self.assertEqual(butter_missing["missing"], 50)  # 250 - 200

        eggs_missing = next(ing for ing in missing_ingredients if ing["name"] == "eggs")
        self.assertEqual(eggs_missing["missing"], 2)  # 8 - 6

        vanilla_missing = next(
            ing for ing in missing_ingredients if ing["name"] == "vanilla"
        )
        self.assertEqual(vanilla_missing["missing"], 1)  # 1 - 0

    def test_precise_unit_conversion_calculations(self):
        """Test that unit conversions are mathematically precise."""
        # Test precise honey calculation
        # 1 pot = 350ml, 1 tablespoon = 15ml
        # So 1 pot = 350/15 = 23.333... tablespoons

        honey_tablespoons = self.pantry.get_total_item_quantity("honey", "Tablespoon")
        expected_tablespoons = 350 / 15
        self.assertAlmostEqual(honey_tablespoons, expected_tablespoons, places=6)

        # Test edge case: need exactly 23.33 tablespoons (should have just enough)
        needed = 350 / 15 - 0.01  # Just slightly less than available
        available = self.pantry.get_total_item_quantity("honey", "Tablespoon")
        self.assertGreater(available, needed)

        # Test edge case: need exactly 23.34 tablespoons (should be missing tiny amount)
        needed = 350 / 15 + 0.01  # Just slightly more than available
        missing = needed - available
        self.assertAlmostEqual(missing, 0.01, places=2)

    def test_zero_and_negative_quantities(self):
        """Test edge cases with zero and negative quantities."""
        # Recipe needs 0 quantity (should always be satisfied)
        available = self.pantry.get_total_item_quantity("honey", "Tablespoon")
        needed = 0
        missing = max(0, needed - available)
        self.assertEqual(missing, 0)

        # Negative needed quantity (invalid but should be handled gracefully)
        needed = -1
        missing = max(0, needed - available)
        self.assertEqual(missing, 0)


if __name__ == "__main__":
    unittest.main()

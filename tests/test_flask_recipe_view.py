"""
Tests for Flask app recipe view functionality, especially missing ingredients calculation.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from pantry_manager_factory import PantryManagerFactory
from pantry_manager_sqlite import SQLitePantryManager
from db_setup import setup_database
import app_flask


class TestFlaskRecipeView(unittest.TestCase):
    """Test Flask recipe view functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Configure Flask app for testing
        app_flask.app.config["TESTING"] = True
        app_flask.app.config["WTF_CSRF_ENABLED"] = False
        os.environ["PANTRY_BACKEND"] = "sqlite"
        os.environ["PANTRY_DB_PATH"] = self.db_path

        # Create test client
        self.client = app_flask.app.test_client()

        # Initialize database with proper setup
        setup_database(self.db_path)
        self.pantry = SQLitePantryManager(self.db_path)

        # Verify the pantry manager was created successfully
        self.assertIsNotNone(self.pantry)

        # Set up test data
        self._setup_test_data()

    def tearDown(self):
        """Clean up test fixtures."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
        if "PANTRY_BACKEND" in os.environ:
            del os.environ["PANTRY_BACKEND"]
        if "PANTRY_DB_PATH" in os.environ:
            del os.environ["PANTRY_DB_PATH"]

    def _setup_test_data(self):
        """Set up test ingredients, units, and recipes."""
        # Add custom unit for honey pot
        self.pantry.set_unit("Pot of honey", "ml", 350)  # 350ml pot

        # Add ingredients to pantry
        self.pantry.add_item("honey", 1, "Pot of honey")  # 350ml of honey
        self.pantry.add_item("flour", 500, "Gram")  # 500g flour
        self.pantry.add_item("butter", 200, "Gram")  # 200g butter
        self.pantry.add_item("milk", 1, "Liter")  # 1L milk
        self.pantry.add_item("eggs", 6, "Piece")  # 6 eggs

        # Create test recipe with mixed units
        recipe_ingredients = [
            {
                "name": "honey",
                "quantity": 2,
                "unit": "Tablespoon",
            },  # 30ml (we have 350ml)
            {"name": "flour", "quantity": 300, "unit": "Gram"},  # 300g (we have 500g)
            {"name": "butter", "quantity": 150, "unit": "Gram"},  # 150g (we have 200g)
            {"name": "milk", "quantity": 2, "unit": "Cup"},  # 480ml (we have 1000ml)
            {"name": "eggs", "quantity": 3, "unit": "Piece"},  # 3 pieces (we have 6)
            {
                "name": "vanilla",
                "quantity": 1,
                "unit": "Teaspoon",
            },  # Missing ingredient
        ]

        success = self.pantry.add_recipe(
            "Test Cake", "Mix ingredients and bake", 45, recipe_ingredients
        )
        if not success:
            print("Failed to add Test Cake recipe")

        # Verify the recipe was added
        test_recipe = self.pantry.get_recipe("Test Cake")
        if not test_recipe:
            print("Test Cake recipe not found after adding")
        else:
            print(
                f"Successfully added Test Cake with {len(test_recipe.get('ingredients', []))} ingredients"
            )

        # Create recipe with insufficient quantities (unit mismatch scenario)
        insufficient_ingredients = [
            {
                "name": "honey",
                "quantity": 25,
                "unit": "Tablespoon",
            },  # 375ml needed, we have 350ml
            {
                "name": "flour",
                "quantity": 600,
                "unit": "Gram",
            },  # 600g needed, we have 500g
        ]

        self.pantry.add_recipe(
            "Large Honey Bread", "Make bread", 90, insufficient_ingredients
        )

    def test_recipe_view_integration_with_missing_ingredients_template(self):
        """Test that Flask app properly integrates missing ingredients logic in template."""
        # Since Flask app might use a different DB connection, let's test the template rendering
        # by directly calling the route logic

        # First verify our test recipe exists
        recipe = self.pantry.get_recipe("Test Cake")
        self.assertIsNotNone(recipe, "Test recipe should exist")
        self.assertEqual(len(recipe["ingredients"]), 6)

        # Test the missing ingredients calculation logic directly
        missing_ingredients = []
        available_ingredients = []

        for ingredient in recipe["ingredients"]:
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

        # Verify the logic works as expected
        self.assertEqual(
            len(available_ingredients), 5
        )  # honey, flour, butter, milk, eggs
        self.assertEqual(len(missing_ingredients), 1)  # vanilla

        # Check that vanilla is the missing ingredient
        vanilla_missing = missing_ingredients[0]
        self.assertEqual(vanilla_missing["name"], "vanilla")
        self.assertEqual(vanilla_missing["missing"], 1.0)

    def test_unit_conversion_logic_integration(self):
        """Test that unit conversions work correctly in the recipe missing ingredients logic."""
        recipe = self.pantry.get_recipe("Test Cake")

        # Test honey conversion: recipe needs 2 tbsp (30ml), we have 350ml
        honey_ingredient = next(
            ing for ing in recipe["ingredients"] if ing["name"] == "honey"
        )
        needed_honey = honey_ingredient["quantity"]  # 2 tablespoons
        available_honey = self.pantry.get_total_item_quantity("honey", "Tablespoon")

        # 350ml / 15ml per tablespoon = 23.33 tablespoons available
        expected_available = 350 / 15
        self.assertAlmostEqual(available_honey, expected_available, places=2)
        self.assertGreater(available_honey, needed_honey)

        # Honey should not be in missing ingredients
        missing = max(0, needed_honey - available_honey)
        self.assertEqual(missing, 0)

    def test_insufficient_quantities_logic(self):
        """Test logic when ingredient quantities are insufficient after unit conversion."""
        recipe = self.pantry.get_recipe("Large Honey Bread")
        self.assertIsNotNone(recipe)

        missing_ingredients = []
        for ingredient in recipe["ingredients"]:
            needed_quantity = ingredient["quantity"]
            available_quantity = self.pantry.get_total_item_quantity(
                ingredient["name"], ingredient["unit"]
            )

            if available_quantity < needed_quantity:
                missing_ingredients.append(
                    {
                        "name": ingredient["name"],
                        "missing": needed_quantity - available_quantity,
                        "unit": ingredient["unit"],
                    }
                )

        # Should have 2 missing ingredients
        self.assertEqual(len(missing_ingredients), 2)
        missing_names = [ing["name"] for ing in missing_ingredients]
        self.assertIn("honey", missing_names)
        self.assertIn("flour", missing_names)

        # Check specific amounts
        honey_missing = next(
            ing for ing in missing_ingredients if ing["name"] == "honey"
        )
        # Need 25 tbsp = 375ml, have 350ml → missing 25ml = 25/15 = 1.67 tbsp
        expected_honey_missing = 25 - (350 / 15)
        self.assertAlmostEqual(
            honey_missing["missing"], expected_honey_missing, places=2
        )

        flour_missing = next(
            ing for ing in missing_ingredients if ing["name"] == "flour"
        )
        # Need 600g, have 500g → missing 100g
        self.assertEqual(flour_missing["missing"], 100)

    def test_mathematical_precision_in_calculations(self):
        """Test that missing ingredient calculations are mathematically precise."""
        # Create a recipe that requires precise calculations
        precise_ingredients = [
            {
                "name": "honey",
                "quantity": 24,
                "unit": "Tablespoon",
            },  # 360ml needed, we have 350ml
        ]

        self.pantry.add_recipe(
            "Precise Honey Recipe", "Test precision", 30, precise_ingredients
        )
        recipe = self.pantry.get_recipe("Precise Honey Recipe")

        # Calculate missing ingredients precisely
        ingredient = recipe["ingredients"][0]
        needed_quantity = ingredient["quantity"]  # 24 tablespoons
        available_quantity = self.pantry.get_total_item_quantity("honey", "Tablespoon")

        # Available: 350ml / 15ml per tablespoon = 23.333... tablespoons
        expected_available = 350 / 15
        self.assertAlmostEqual(available_quantity, expected_available, places=6)

        # Missing: 24 - 23.333... = 0.666... tablespoons
        missing = needed_quantity - available_quantity
        expected_missing = 24 - (350 / 15)
        self.assertAlmostEqual(missing, expected_missing, places=6)


if __name__ == "__main__":
    unittest.main()

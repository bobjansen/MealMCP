import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from pantry_manager import PantryManager
from db_setup import setup_database


class TestPantryManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for testing
        self.db_path = tempfile.mktemp()
        self.pantry = PantryManager(self.db_path)

        # Run the database setup
        setup_database(self.db_path)

    def tearDown(self):
        # Close any remaining connections and remove the temporary database
        try:
            self.pantry._get_connection().close()
        except:
            pass
        try:
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except:
            pass

    def test_add_ingredient(self):
        """Test adding a new ingredient"""
        success = self.pantry.add_ingredient("flour", "g")
        self.assertTrue(success)

        # Verify ingredient exists
        ingredient_id = self.pantry.get_ingredient_id("flour")
        self.assertIsNotNone(ingredient_id)

    def test_add_item_to_pantry(self):
        """Test adding items to the pantry"""
        # Add a new item
        success = self.pantry.add_item("sugar", 500, "g", "brown sugar")
        self.assertTrue(success)

        # Verify quantity
        quantity = self.pantry.get_item_quantity("sugar", "g")
        self.assertEqual(quantity, 500)

    def test_remove_item_from_pantry(self):
        """Test removing items from the pantry"""
        # First add an item
        self.pantry.add_item("rice", 1000, "g")

        # Remove some of it
        success = self.pantry.remove_item("rice", 300, "g")
        self.assertTrue(success)

        # Verify remaining quantity
        quantity = self.pantry.get_item_quantity("rice", "g")
        self.assertEqual(quantity, 700)

        # Try to remove more than available
        success = self.pantry.remove_item("rice", 800, "g")
        self.assertFalse(success)

    def test_pantry_contents(self):
        """Test getting pantry contents"""
        # Add multiple items
        self.pantry.add_item("flour", 1000, "g")
        self.pantry.add_item("sugar", 500, "g")
        self.pantry.add_item("milk", 2, "L")

        contents = self.pantry.get_pantry_contents()

        self.assertIn("flour", contents)
        self.assertIn("sugar", contents)
        self.assertIn("milk", contents)
        self.assertEqual(contents["flour"]["g"], 1000)
        self.assertEqual(contents["sugar"]["g"], 500)
        self.assertEqual(contents["milk"]["L"], 2)

    def test_transaction_history(self):
        """Test transaction history tracking"""
        # Add and remove some items
        self.pantry.add_item("eggs", 12, "units", "fresh eggs")
        self.pantry.remove_item("eggs", 2, "units", "used for baking")

        history = self.pantry.get_transaction_history("eggs")

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["transaction_type"], "removal")
        self.assertEqual(history[1]["transaction_type"], "addition")
        self.assertEqual(history[1]["quantity"], 12)

    def test_recipe_management(self):
        """Test recipe creation and retrieval"""
        # Create a recipe
        recipe = {
            "name": "Simple Cookies",
            "instructions": "Mix and bake at 350°F",
            "time_minutes": 30,
            "ingredients": [
                {"name": "flour", "quantity": 200, "unit": "g"},
                {"name": "sugar", "quantity": 100, "unit": "g"},
                {"name": "eggs", "quantity": 2, "unit": "units"},
            ],
        }

        success = self.pantry.add_recipe(**recipe)
        self.assertTrue(success)

        # Retrieve the recipe
        saved_recipe = self.pantry.get_recipe("Simple Cookies")
        self.assertIsNotNone(saved_recipe)
        self.assertEqual(saved_recipe["name"], recipe["name"])
        self.assertEqual(saved_recipe["instructions"], recipe["instructions"])
        self.assertEqual(saved_recipe["time_minutes"], recipe["time_minutes"])
        self.assertEqual(len(saved_recipe["ingredients"]), len(recipe["ingredients"]))

    def test_get_all_recipes(self):
        """Test retrieving all recipes"""
        # Add multiple recipes
        recipes = [
            {
                "name": "Pancakes",
                "instructions": "Mix and cook on griddle",
                "time_minutes": 20,
                "ingredients": [
                    {"name": "flour", "quantity": 300, "unit": "g"},
                    {"name": "milk", "quantity": 200, "unit": "ml"},
                ],
            },
            {
                "name": "Scrambled Eggs",
                "instructions": "Beat and cook eggs",
                "time_minutes": 10,
                "ingredients": [
                    {"name": "eggs", "quantity": 3, "unit": "units"},
                    {"name": "milk", "quantity": 30, "unit": "ml"},
                ],
            },
        ]

        for recipe in recipes:
            success = self.pantry.add_recipe(**recipe)
            self.assertTrue(success)

        # Retrieve all recipes
        saved_recipes = self.pantry.get_all_recipes()
        self.assertEqual(len(saved_recipes), len(recipes))
        recipe_names = {r["name"] for r in saved_recipes}
        self.assertEqual(recipe_names, {"Pancakes", "Scrambled Eggs"})

    def test_ingredient_unit_consistency(self):
        """Test that ingredients maintain unit consistency"""
        # Add item to pantry
        self.pantry.add_item("flour", 1000, "g")

        # Try to add same item with different unit
        self.pantry.add_item("flour", 1, "kg")

        # Get quantities
        quantity_g = self.pantry.get_item_quantity("flour", "g")
        quantity_kg = self.pantry.get_item_quantity("flour", "kg")

        # Each unit should be tracked separately
        self.assertEqual(quantity_g, 1000)
        self.assertEqual(quantity_kg, 1)

    def test_execute_recipe(self):
        """Test executing a recipe and removing ingredients from pantry"""
        # Add ingredients to pantry
        self.pantry.add_item("flour", 500, "g")
        self.pantry.add_item("sugar", 300, "g")
        self.pantry.add_item("eggs", 6, "units")

        # Create a recipe
        recipe = {
            "name": "Test Cookies",
            "instructions": "Mix and bake",
            "time_minutes": 30,
            "ingredients": [
                {"name": "flour", "quantity": 200, "unit": "g"},
                {"name": "sugar", "quantity": 100, "unit": "g"},
                {"name": "eggs", "quantity": 2, "unit": "units"},
            ],
        }
        self.pantry.add_recipe(**recipe)

        # Execute recipe
        success, message = self.pantry.execute_recipe("Test Cookies")
        self.assertTrue(success)

        # Check remaining quantities
        self.assertEqual(self.pantry.get_item_quantity("flour", "g"), 300)
        self.assertEqual(self.pantry.get_item_quantity("sugar", "g"), 200)
        self.assertEqual(self.pantry.get_item_quantity("eggs", "units"), 4)

        # Try to execute recipe with insufficient ingredients
        success, message = self.pantry.execute_recipe("Test Cookies")
        self.assertTrue(success)
        success, message = self.pantry.execute_recipe("Test Cookies")
        self.assertFalse(success)
        self.assertIn("Missing ingredients", message)


if __name__ == "__main__":
    unittest.main()

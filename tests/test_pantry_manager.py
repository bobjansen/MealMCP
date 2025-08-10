import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from pantry_manager_factory import create_pantry_manager
from db_setup import setup_database
from datetime import date, timedelta


class TestPantryManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for testing
        self.db_path = tempfile.mktemp()
        self.pantry = create_pantry_manager(connection_string=self.db_path)

        # Run the database setup
        setup_database(self.db_path)

    def test_preferences_crud(self):
        """Test creating, reading, updating, and deleting preferences."""
        # Test adding a preference
        success = self.pantry.add_preference(
            category="dietary",
            item="vegetarian",
            level="required",
            notes="No meat or fish",
        )
        self.assertTrue(success, "Should successfully add a preference")

        # Test getting preferences
        prefs = self.pantry.get_preferences()
        self.assertEqual(len(prefs), 1, "Should have one preference")
        pref = prefs[0]
        self.assertEqual(pref["category"], "dietary")
        self.assertEqual(pref["item"], "vegetarian")
        self.assertEqual(pref["level"], "required")
        self.assertEqual(pref["notes"], "No meat or fish")

        # Test adding another preference
        success = self.pantry.add_preference(
            category="allergy", item="peanuts", level="avoid", notes="Severe allergy"
        )
        self.assertTrue(success, "Should successfully add second preference")

        prefs = self.pantry.get_preferences()
        self.assertEqual(len(prefs), 2, "Should have two preferences")

        # Test updating a preference
        pref_id = prefs[0]["id"]
        success = self.pantry.update_preference(
            preference_id=pref_id, level="preferred", notes="Trying to be more flexible"
        )
        self.assertTrue(success, "Should successfully update preference")

        # Verify the update
        prefs = self.pantry.get_preferences()
        updated_pref = next(p for p in prefs if p["id"] == pref_id)
        self.assertEqual(updated_pref["level"], "preferred")
        self.assertEqual(updated_pref["notes"], "Trying to be more flexible")
        self.assertEqual(
            updated_pref["category"], "dietary", "Category should not change"
        )
        self.assertEqual(updated_pref["item"], "vegetarian", "Item should not change")

        # Test deleting a preference
        success = self.pantry.delete_preference(pref_id)
        self.assertTrue(success, "Should successfully delete preference")

        # Verify the deletion
        prefs = self.pantry.get_preferences()
        self.assertEqual(len(prefs), 1, "Should have one preference remaining")
        self.assertNotEqual(
            prefs[0]["id"], pref_id, "Deleted preference should not be present"
        )

    def test_preference_constraints(self):
        """Test preference constraints and edge cases."""
        # Test duplicate preference
        success1 = self.pantry.add_preference(
            category="dietary", item="vegetarian", level="required"
        )
        self.assertTrue(success1, "Should add first preference")

        success2 = self.pantry.add_preference(
            category="dietary", item="vegetarian", level="preferred"
        )
        self.assertFalse(success2, "Should not add duplicate category/item combination")

        # Test with empty values
        with self.assertRaises(ValueError):
            self.pantry.add_preference("", "item", "required")

        # Test deleting non-existent preference
        success = self.pantry.delete_preference(999)
        self.assertFalse(success, "Should fail to delete non-existent preference")

        # Test updating non-existent preference
        success = self.pantry.update_preference(999, "required", "test")
        self.assertFalse(success, "Should fail to update non-existent preference")

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

    def test_get_item_quantity(self):
        """Test getting item quantities with various scenarios"""
        # Test non-existent item
        quantity = self.pantry.get_item_quantity("nonexistent", "g")
        self.assertEqual(quantity, 0.0, "Non-existent item should return 0")

        # Test existing item with no transactions
        self.pantry.add_ingredient("salt", "g")  # Add ingredient without any quantity
        quantity = self.pantry.get_item_quantity("salt", "g")
        self.assertEqual(quantity, 0.0, "Item with no transactions should return 0")

        # Test item with multiple additions
        self.pantry.add_item("flour", 500, "g")
        self.pantry.add_item("flour", 300, "g")
        quantity = self.pantry.get_item_quantity("flour", "g")
        self.assertEqual(quantity, 800, "Multiple additions should sum correctly")

        # Test item with additions and removals
        self.pantry.remove_item("flour", 200, "g")
        quantity = self.pantry.get_item_quantity("flour", "g")
        self.assertEqual(
            quantity, 600, "Additions and removals should calculate correctly"
        )

        # Test item with different units
        self.pantry.add_item("flour", 2, "kg")
        quantity_g = self.pantry.get_item_quantity("flour", "g")
        quantity_kg = self.pantry.get_item_quantity("flour", "kg")
        self.assertEqual(
            quantity_g, 600, "Different units should be tracked separately"
        )
        self.assertEqual(quantity_kg, 2, "Different units should be tracked separately")

        # Test rounding/floating point precision
        self.pantry.add_item("sugar", 1.5, "kg")
        self.pantry.remove_item("sugar", 0.75, "kg")
        quantity = self.pantry.get_item_quantity("sugar", "kg")
        self.assertEqual(
            quantity, 0.75, "Floating point calculations should be precise"
        )

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

    def test_recipe_fuzzy_matching(self):
        """Test fuzzy matching functionality in get_recipe"""
        # Create a recipe with a specific name
        recipe = {
            "name": "Grilled Chicken Breast with Herbs",
            "instructions": "Season chicken with herbs and grill until cooked through",
            "time_minutes": 25,
            "ingredients": [
                {"name": "chicken breast", "quantity": 2, "unit": "pieces"},
                {"name": "olive oil", "quantity": 2, "unit": "tbsp"},
                {"name": "mixed herbs", "quantity": 1, "unit": "tsp"},
            ],
        }

        success, recipe_id = self.pantry.add_recipe(**recipe)
        self.assertTrue(success)
        self.assertIsNotNone(recipe_id)

        # Test exact match (should still work)
        exact_match = self.pantry.get_recipe("Grilled Chicken Breast with Herbs")
        self.assertIsNotNone(exact_match)
        self.assertEqual(exact_match["name"], recipe["name"])

        # Test partial match
        partial_match = self.pantry.get_recipe("Grilled Chicken")
        self.assertIsNotNone(partial_match)
        self.assertEqual(partial_match["name"], recipe["name"])

        # Test case insensitive match
        case_match = self.pantry.get_recipe("grilled chicken breast")
        self.assertIsNotNone(case_match)
        self.assertEqual(case_match["name"], recipe["name"])

        # Test substring match
        substring_match = self.pantry.get_recipe("Chicken")
        self.assertIsNotNone(substring_match)
        self.assertEqual(substring_match["name"], recipe["name"])

        # Test with herbs keyword
        herbs_match = self.pantry.get_recipe("Herbs")
        self.assertIsNotNone(herbs_match)
        self.assertEqual(herbs_match["name"], recipe["name"])

        # Test non-matching query
        no_match = self.pantry.get_recipe("Pizza Margherita")
        self.assertIsNone(no_match)

        # Test empty string
        empty_match = self.pantry.get_recipe("")
        self.assertIsNone(empty_match)

        # Add another recipe to test preference for shorter matches
        recipe2 = {
            "name": "Chicken Salad",
            "instructions": "Mix chicken with vegetables",
            "time_minutes": 15,
            "ingredients": [
                {"name": "cooked chicken", "quantity": 200, "unit": "g"},
                {"name": "lettuce", "quantity": 100, "unit": "g"},
            ],
        }

        success2, recipe_id2 = self.pantry.add_recipe(**recipe2)
        self.assertTrue(success2)

        # When searching for "Chicken", should return the shorter match first
        chicken_search = self.pantry.get_recipe("Chicken")
        self.assertIsNotNone(chicken_search)
        # Should prefer "Chicken Salad" (shorter) over "Grilled Chicken Breast with Herbs"
        self.assertEqual(chicken_search["name"], "Chicken Salad")

        # Test advanced word-based matching
        word_search = self.pantry.get_recipe("Grilled Herbs")
        self.assertIsNotNone(word_search)
        self.assertEqual(word_search["name"], "Grilled Chicken Breast with Herbs")

        # Test word order independence
        reversed_search = self.pantry.get_recipe("Herbs Chicken")
        self.assertIsNotNone(reversed_search)
        self.assertEqual(reversed_search["name"], "Grilled Chicken Breast with Herbs")

        # Test single character typo tolerance
        typo_search = self.pantry.get_recipe("Chickn")  # Missing 'e'
        self.assertIsNotNone(typo_search)
        self.assertEqual(
            typo_search["name"], "Chicken Salad"
        )  # Shorter match preferred

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

    def test_grocery_list(self):
        """Test calculating grocery list based on meal plan and pantry contents."""
        recipe = {
            "name": "Toast",
            "instructions": "Toast bread",
            "time_minutes": 5,
            "ingredients": [
                {"name": "bread", "quantity": 2, "unit": "slices"},
                {"name": "butter", "quantity": 1, "unit": "tbsp"},
            ],
        }
        self.pantry.add_recipe(**recipe)
        self.pantry.set_meal_plan(date.today().isoformat(), "Toast")

        # Only one slice of bread in pantry, enough butter
        self.pantry.add_item("bread", 1, "slices")
        self.pantry.add_item("butter", 2, "tbsp")

        grocery = self.pantry.get_grocery_list()
        self.assertEqual(len(grocery), 1)
        self.assertEqual(grocery[0]["name"], "bread")
        self.assertEqual(grocery[0]["unit"], "slices")
        self.assertEqual(grocery[0]["quantity"], 1)

    def test_recipe_rating(self):
        """Test recipe rating functionality."""
        # First add a recipe
        success = self.pantry.add_recipe(
            name="Test Recipe",
            instructions="Test instructions",
            time_minutes=30,
            ingredients=[
                {"name": "flour", "quantity": 2, "unit": "cups"},
                {"name": "eggs", "quantity": 3, "unit": "whole"},
            ],
        )
        self.assertTrue(success, "Should successfully add recipe")

        # Test rating the recipe
        success = self.pantry.rate_recipe("Test Recipe", 5)
        self.assertTrue(success, "Should successfully rate recipe")

        # Verify the rating was saved
        recipe = self.pantry.get_recipe("Test Recipe")
        self.assertIsNotNone(recipe, "Recipe should exist")
        self.assertEqual(recipe["rating"], 5, "Recipe should have rating of 5")

        # Test rating with different value
        success = self.pantry.rate_recipe("Test Recipe", 3)
        self.assertTrue(success, "Should successfully update rating")

        recipe = self.pantry.get_recipe("Test Recipe")
        self.assertEqual(recipe["rating"], 3, "Recipe should have updated rating of 3")

        # Test invalid rating values
        success = self.pantry.rate_recipe("Test Recipe", 0)
        self.assertFalse(success, "Should fail with rating 0")

        success = self.pantry.rate_recipe("Test Recipe", 6)
        self.assertFalse(success, "Should fail with rating 6")

        # Test rating non-existent recipe
        success = self.pantry.rate_recipe("Non-existent Recipe", 4)
        self.assertFalse(success, "Should fail to rate non-existent recipe")


if __name__ == "__main__":
    unittest.main()

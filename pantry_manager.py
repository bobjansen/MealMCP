import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class PantryManager:
    def __init__(self, db_path: str = "pantry.db"):
        self.db_path = db_path

    def _get_connection(self):
        """Get a database connection. Should be used in a context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.isolation_level = None  # Enable autocommit mode
        return conn

    def add_ingredient(self, name: str, default_unit: str) -> bool:
        """
        Add a new ingredient to the database.

        Args:
            name: Name of the ingredient
            default_unit: Default unit of measurement for this ingredient

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO Ingredients (name, default_unit)
                    VALUES (?, ?)
                    """,
                    (name, default_unit),
                )
                return True
        except Exception as e:
            print(f"Error adding ingredient: {e}")
            return False

    def add_preference(
        self, category: str, item: str, level: str, notes: str = None
    ) -> bool:
        """
        Add a new food preference to the database.

        Args:
            category: Type of preference (dietary, allergy, dislike, like)
            item: The specific preference item
            level: Importance level (required, preferred, avoid)
            notes: Optional notes about the preference

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If category, item, or level is empty
        """
        if not category or not item or not level:
            raise ValueError("Category, item, and level are required")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO Preferences (category, item, level, notes, created_date)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (category, item, level, notes),
                )
                return True
        except sqlite3.IntegrityError as e:
            print(f"Error adding preference: {e}")
            return False
        except Exception as e:
            print(f"Error adding preference: {e}")
            return False

    def update_preference(
        self, preference_id: int, level: str, notes: str = None
    ) -> bool:
        """
        Update an existing food preference.

        Args:
            preference_id: ID of the preference to update
            level: New importance level (required/preferred/avoid)
            notes: Optional new notes

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If level is empty
        """
        if not level:
            raise ValueError("Level is required")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE Preferences
                    SET level = ?, notes = ?
                    WHERE id = ?
                    """,
                    (level, notes, preference_id),
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating preference: {e}")
            return False

    def delete_preference(self, preference_id: int) -> bool:
        """Delete a food preference by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Preferences WHERE id = ?", (preference_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting preference: {e}")
            return False

    def get_preferences(self) -> List[Dict[str, Any]]:
        """Get all food preferences."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, category, item, level, notes, created_date
                    FROM Preferences
                    ORDER BY id
                    """
                )
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting preferences: {e}")
            return []

    def get_ingredient_id(self, name: str) -> Optional[int]:
        """Get the ID of an ingredient by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM Ingredients WHERE name = ?",
                    (name,),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting ingredient ID: {e}")
            return None

    def add_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Add a new item to the pantry or increase existing item quantity.

        Args:
            item_name: Name of the item to add
            quantity: Amount to add
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get or create the ingredient
                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    self.add_ingredient(item_name, unit)
                    ingredient_id = self.get_ingredient_id(item_name)

                cursor.execute(
                    """
                    INSERT INTO PantryTransactions
                    (transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "addition",
                        ingredient_id,
                        quantity,
                        unit,
                        datetime.now().isoformat(),
                        notes,
                    ),
                )
                return True
        except Exception as e:
            print(f"Error adding item: {e}")
            return False

    def remove_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Remove a quantity of an item from the pantry.

        Args:
            item_name: Name of the item to remove
            quantity: Amount to remove
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First check if we have enough of the item
            current_quantity = self.get_item_quantity(item_name, unit)
            if current_quantity < quantity:
                print(
                    f"Not enough {item_name} in pantry. Current quantity: {current_quantity} {unit}"
                )
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    print(f"Ingredient {item_name} not found in database")
                    return False

                cursor.execute(
                    """
                    INSERT INTO PantryTransactions
                    (transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "removal",
                        ingredient_id,
                        quantity,
                        unit,
                        datetime.now().isoformat(),
                        notes,
                    ),
                )
                return True
        except Exception as e:
            print(f"Error removing item: {e}")
            return False

    def get_item_quantity(self, item_name: str, unit: str) -> float:
        """
        Get the current quantity of an item in the pantry.

        Args:
            item_name: Name of the item to check
            unit: Unit of measurement

        Returns:
            float: Current quantity of the item (can be negative if more removals than additions)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    return 0.0

                cursor.execute(
                    """
                    SELECT
                        SUM(CASE
                            WHEN transaction_type = 'addition' THEN quantity
                            ELSE -quantity
                        END) as net_quantity
                    FROM PantryTransactions
                    WHERE ingredient_id = ? AND unit = ?
                    """,
                    (ingredient_id, unit),
                )
                result = cursor.fetchone()[0]
                return float(result) if result is not None else 0.0
        except Exception as e:
            print(f"Error getting item quantity: {e}")
            return 0.0

    def get_pantry_contents(self) -> Dict[str, Dict[str, float]]:
        """
        Get the current contents of the pantry.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary with item names as keys and their quantities by unit as values
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        i.name,
                        t.unit,
                        SUM(CASE
                            WHEN t.transaction_type = 'addition' THEN t.quantity
                            ELSE -t.quantity
                        END) as net_quantity
                    FROM PantryTransactions t
                    JOIN Ingredients i ON t.ingredient_id = i.id
                    GROUP BY i.name, t.unit
                    HAVING net_quantity > 0
                    """
                )
                results = cursor.fetchall()

                contents = {}
                for item_name, unit, quantity in results:
                    if item_name not in contents:
                        contents[item_name] = {}
                    contents[item_name][unit] = quantity

                return contents
        except Exception as e:
            print(f"Error getting pantry contents: {e}")
            return {}

    def add_recipe(
        self,
        name: str,
        instructions: str,
        time_minutes: int,
        ingredients: List[Dict[str, Any]],
    ) -> bool:
        """
        Add a new recipe to the database.

        Args:
            name: Name of the recipe
            instructions: Cooking instructions
            time_minutes: Time required to prepare the recipe
            ingredients: List of dictionaries containing:
                - name: ingredient name
                - quantity: amount needed
                - unit: unit of measurement

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Insert recipe
                cursor.execute(
                    """
                    INSERT INTO Recipes
                    (name, instructions, time_minutes, created_date, last_modified)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (name, instructions, time_minutes, now, now),
                )
                recipe_id = cursor.lastrowid

                # Add ingredients
                for ingredient in ingredients:
                    ingredient_id = self.get_ingredient_id(ingredient["name"])
                    if ingredient_id is None:
                        # Create new ingredient if it doesn't exist
                        self.add_ingredient(ingredient["name"], ingredient["unit"])
                        ingredient_id = self.get_ingredient_id(ingredient["name"])

                    cursor.execute(
                        """
                        INSERT INTO RecipeIngredients
                        (recipe_id, ingredient_id, quantity, unit)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            recipe_id,
                            ingredient_id,
                            ingredient["quantity"],
                            ingredient["unit"],
                        ),
                    )
                return True
        except Exception as e:
            print(f"Error adding recipe: {e}")
            return False

    def get_recipe(self, recipe_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a recipe and its ingredients by name.

        Args:
            recipe_name: Name of the recipe to retrieve

        Returns:
            Optional[Dict[str, Any]]: Recipe details including ingredients, or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        r.id,
                        r.instructions,
                        r.time_minutes,
                        r.created_date,
                        r.last_modified
                    FROM Recipes r
                    WHERE r.name = ?
                    """,
                    (recipe_name,),
                )
                recipe = cursor.fetchone()
                if not recipe:
                    return None

                recipe_id, instructions, time_minutes, created_date, last_modified = (
                    recipe
                )

                # Get ingredients
                cursor.execute(
                    """
                    SELECT
                        i.name,
                        ri.quantity,
                        ri.unit
                    FROM RecipeIngredients ri
                    JOIN Ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = ?
                    """,
                    (recipe_id,),
                )
                ingredients = [
                    {"name": name, "quantity": qty, "unit": unit}
                    for name, qty, unit in cursor.fetchall()
                ]

                return {
                    "name": recipe_name,
                    "instructions": instructions,
                    "time_minutes": time_minutes,
                    "created_date": created_date,
                    "last_modified": last_modified,
                    "ingredients": ingredients,
                }
        except Exception as e:
            print(f"Error getting recipe: {e}")
            return None

    def get_transaction_history(
        self, item_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the transaction history for all items or a specific item.

        Args:
            item_name: Optional name of item to filter transactions

        Returns:
            List[Dict[str, Any]]: List of transactions with their details
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if item_name:
                    ingredient_id = self.get_ingredient_id(item_name)
                    if ingredient_id is None:
                        return []
                    cursor.execute(
                        """
                        SELECT
                            t.*,
                            i.name as item_name
                        FROM PantryTransactions t
                        JOIN Ingredients i ON t.ingredient_id = i.id
                        WHERE t.ingredient_id = ?
                        ORDER BY t.transaction_date DESC, t.id desc
                        """,
                        (ingredient_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            t.*,
                            i.name as item_name
                        FROM PantryTransactions t
                        JOIN Ingredients i ON t.ingredient_id = i.id
                        ORDER BY t.transaction_date DESC, t.id desc
                        """
                    )

                columns = [description[0] for description in cursor.description]
                transactions = []

                for row in cursor.fetchall():
                    transactions.append(dict(zip(columns, row)))

                return transactions
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []

    def get_all_recipes(self) -> List[Dict[str, Any]]:
        """
        Get all recipes from the database.

        Returns:
            List[Dict[str, Any]]: List of all recipes with their details
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM Recipes ORDER BY name")
                recipes = []

                for (name,) in cursor.fetchall():
                    recipe = self.get_recipe(name)
                    if recipe:
                        recipes.append(recipe)

                return recipes
        except Exception as e:
            print(f"Error getting all recipes: {e}")
            return []

    def edit_recipe(
        self,
        name: str,
        instructions: str,
        time_minutes: int,
        ingredients: List[Dict[str, Any]],
    ) -> bool:
        """
        Edit an existing recipe in the database.

        Args:
            name: Name of the recipe to edit
            instructions: Updated cooking instructions
            time_minutes: Updated time required to prepare the recipe
            ingredients: Updated list of dictionaries containing:
                - name: ingredient name
                - quantity: amount needed
                - unit: unit of measurement

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if recipe exists
                cursor.execute("SELECT id FROM Recipes WHERE name = ?", (name,))
                result = cursor.fetchone()
                if not result:
                    print(f"Recipe '{name}' not found")
                    return False

                recipe_id = result[0]
                now = datetime.now().isoformat()

                # Update recipe
                cursor.execute(
                    """
                    UPDATE Recipes
                    SET instructions = ?, time_minutes = ?, last_modified = ?
                    WHERE id = ?
                    """,
                    (instructions, time_minutes, now, recipe_id),
                )

                # Delete existing ingredients
                cursor.execute(
                    "DELETE FROM RecipeIngredients WHERE recipe_id = ?", (recipe_id,)
                )

                # Add new ingredients
                for ingredient in ingredients:
                    ingredient_id = self.get_ingredient_id(ingredient["name"])
                    if ingredient_id is None:
                        # Create new ingredient if it doesn't exist
                        self.add_ingredient(ingredient["name"], ingredient["unit"])
                        ingredient_id = self.get_ingredient_id(ingredient["name"])

                    cursor.execute(
                        """
                        INSERT INTO RecipeIngredients
                        (recipe_id, ingredient_id, quantity, unit)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            recipe_id,
                            ingredient_id,
                            ingredient["quantity"],
                            ingredient["unit"],
                        ),
                    )
                return True
        except Exception as e:
            print(f"Error editing recipe: {e}")
            return False

    def execute_recipe(self, recipe_name: str) -> tuple[bool, str]:
        """
        Execute a recipe by removing its ingredients from the pantry.

        Args:
            recipe_name: Name of the recipe to execute

        Returns:
            tuple[bool, str]: (Success status, Message with details or error)
        """
        try:
            recipe = self.get_recipe(recipe_name)
            if not recipe:
                return False, f"Recipe '{recipe_name}' not found"

            # Check if we have enough of each ingredient
            missing_ingredients = []
            for ingredient in recipe["ingredients"]:
                needed_quantity = ingredient["quantity"]
                available_quantity = self.get_item_quantity(
                    ingredient["name"], ingredient["unit"]
                )

                if available_quantity < needed_quantity:
                    missing_ingredients.append(
                        f"{ingredient['name']}: need {needed_quantity} {ingredient['unit']}, "
                        f"have {available_quantity} {ingredient['unit']}"
                    )

            if missing_ingredients:
                return False, "Missing ingredients:\n" + "\n".join(missing_ingredients)

            # Remove ingredients from pantry
            success = True
            used_ingredients = []
            for ingredient in recipe["ingredients"]:
                quantity = ingredient["quantity"]
                if self.remove_item(
                    ingredient["name"],
                    quantity,
                    ingredient["unit"],
                    f"Used in recipe: {recipe_name}",
                ):
                    used_ingredients.append(
                        f"{quantity} {ingredient['unit']} of {ingredient['name']}"
                    )
                else:
                    success = False
                    break

            if success:
                return True, f"Successfully made {recipe_name} using:\n" + "\n".join(
                    used_ingredients
                )
            else:
                return False, "Error removing ingredients from pantry"

        except Exception as e:
            print(f"Error executing recipe: {e}")
            return False, f"Error executing recipe: {str(e)}"

    def set_meal_plan(self, meal_date: str, recipe_name: str) -> bool:
        """Assign a recipe to a specific date in the MealPlan table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM Recipes WHERE name = ?", (recipe_name,))
                result = cursor.fetchone()
                if not result:
                    return False

                cursor.execute(
                    "INSERT OR REPLACE INTO MealPlan (meal_date, recipe_id) VALUES (?, ?)",
                    (meal_date, result[0]),
                )
                return True
        except Exception as e:
            print(f"Error setting meal plan: {e}")
            return False

    def get_meal_plan(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve planned meals between two dates."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT meal_date, r.name
                    FROM MealPlan m
                    JOIN Recipes r ON m.recipe_id = r.id
                    WHERE meal_date BETWEEN ? AND ?
                    ORDER BY meal_date
                    """,
                    (start_date, end_date),
                )
                return [{"date": row[0], "recipe": row[1]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting meal plan: {e}")
            return []

    def generate_week_plan(self) -> List[Dict[str, Any]]:
        """Generate meal plan entries for the coming week using available recipes."""
        recipes = self.get_all_recipes()
        if not recipes:
            return []

        start = date.today()
        plan = []
        for idx, recipe in enumerate(recipes[:7]):
            meal_date = start + timedelta(days=idx)
            if self.set_meal_plan(meal_date.isoformat(), recipe["name"]):
                plan.append({"date": meal_date.isoformat(), "recipe": recipe["name"]})
        return plan

    def get_grocery_list(self) -> List[Dict[str, Any]]:
        """Calculate grocery items needed for the coming week's meal plan."""
        start = date.today()
        end = start + timedelta(days=6)
        plan = self.get_meal_plan(start.isoformat(), end.isoformat())

        required: Dict[tuple[str, str], float] = {}
        for entry in plan:
            recipe = self.get_recipe(entry["recipe"])
            if not recipe:
                continue
            for ing in recipe["ingredients"]:
                key = (ing["name"], ing["unit"])
                required[key] = required.get(key, 0) + ing["quantity"]

        grocery_list = []
        for (name, unit), qty in required.items():
            have = self.get_item_quantity(name, unit)
            if have < qty:
                grocery_list.append(
                    {"name": name, "quantity": qty - have, "unit": unit}
                )

        return grocery_list

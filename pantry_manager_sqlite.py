import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from pantry_manager_abc import PantryManager
from short_id_utils import ShortIDGenerator
from error_utils import safe_execute, validate_required_params


class SQLitePantryManager(PantryManager):
    """SQLite implementation of the PantryManager interface."""

    def __init__(self, connection_string: str = "pantry.db", **kwargs):
        """
        Initialize the SQLite pantry manager.

        Args:
            connection_string: Path to the SQLite database file
            **kwargs: Additional configuration options (ignored for SQLite)
        """
        self.db_path = connection_string

    def _get_connection(self):
        """Get a database connection. Should be used in a context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.isolation_level = None  # Enable autocommit mode
        return conn

    @safe_execute("add ingredient", default_return=False)
    def add_ingredient(self, name: str, default_unit: str) -> bool:
        """
        Add a new ingredient to the database.

        Args:
            name: Name of the ingredient
            default_unit: Default unit of measurement for this ingredient

        Returns:
            bool: True if successful, False otherwise
        """
        validate_required_params(name=name, default_unit=default_unit)

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

    @safe_execute("add preference", default_return=False)
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
        """
        validate_required_params(category=category, item=item, level=level)

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

    @safe_execute("update preference", default_return=False)
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
        """
        validate_required_params(level=level)
        if preference_id is None or preference_id <= 0:
            raise ValueError("Valid preference_id is required")

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

    @safe_execute("delete preference", default_return=False)
    def delete_preference(self, preference_id: int) -> bool:
        """Delete a food preference by ID."""
        if preference_id is None or preference_id <= 0:
            raise ValueError("Valid preference_id is required")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Preferences WHERE id = ?", (preference_id,))
            return cursor.rowcount > 0

    @safe_execute("get preferences", default_return=[])
    def get_preferences(self) -> List[Dict[str, Any]]:
        """Get all food preferences."""
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

    @safe_execute("get ingredient ID", default_return=None)
    def get_ingredient_id(self, name: str) -> Optional[int]:
        """Get the ID of an ingredient by name."""
        validate_required_params(name=name)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM Ingredients WHERE name = ?",
                (name,),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    @safe_execute("add pantry item", default_return=False)
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
        validate_required_params(item_name=item_name, unit=unit)
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

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
    ) -> tuple[bool, Optional[str]]:
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
            tuple[bool, Optional[str]]: (Success status, Recipe Short ID)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                # Strategy: Get the next recipe ID by querying the current max ID
                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM Recipes")
                next_id = cursor.fetchone()[0]

                # Generate short ID from the predicted next ID
                short_id = ShortIDGenerator.generate(next_id)

                cursor.execute(
                    """
                    INSERT INTO Recipes
                    (short_id, name, instructions, time_minutes, created_date, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (short_id, name, instructions, time_minutes, now, now),
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
                return True, short_id
        except Exception as e:
            print(f"Error adding recipe: {e}")
            return False, None

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
                        r.rating,
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

                (
                    recipe_id,
                    instructions,
                    time_minutes,
                    rating,
                    created_date,
                    last_modified,
                ) = recipe

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
                    "rating": rating,
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
            List[Dict[str, Any]]: List of all recipes with their details including short IDs
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT short_id, name FROM Recipes ORDER BY name")
                recipes = []

                for short_id, name in cursor.fetchall():
                    recipe = self.get_recipe_by_short_id(short_id)
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

    def rate_recipe(self, recipe_name: str, rating: int) -> bool:
        """
        Rate a recipe on a scale of 1-5.

        Args:
            recipe_name: Name of the recipe to rate
            rating: Rating from 1 (poor) to 5 (excellent)

        Returns:
            bool: True if successful, False otherwise
        """
        if not (1 <= rating <= 5):
            print("Rating must be between 1 and 5")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE Recipes
                    SET rating = ?, last_modified = ?
                    WHERE name = ?
                    """,
                    (rating, datetime.now().isoformat(), recipe_name),
                )
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error rating recipe: {e}")
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

    def get_recipe_by_short_id(self, short_id: str) -> Optional[Dict[str, Any]]:
        """Get a recipe and its ingredients by short ID."""
        # Validate short ID format
        numeric_id = ShortIDGenerator.parse(short_id)
        if numeric_id is None:
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Get recipe details
                cursor.execute(
                    "SELECT id, short_id, name, instructions, time_minutes, rating, created_date, last_modified FROM Recipes WHERE id = ?",
                    (numeric_id,),
                )
                recipe_row = cursor.fetchone()
                if not recipe_row:
                    return None

                (
                    recipe_id,
                    stored_short_id,
                    name,
                    instructions,
                    time_minutes,
                    rating,
                    created_date,
                    last_modified,
                ) = recipe_row
                recipe = {
                    "id": recipe_id,
                    "short_id": stored_short_id,
                    "name": name,
                    "instructions": instructions,
                    "time_minutes": time_minutes,
                    "rating": rating,
                    "created_date": created_date,
                    "last_modified": last_modified,
                    "ingredients": [],
                }

                # Get ingredients
                cursor.execute(
                    """
                    SELECT i.name, ri.quantity, ri.unit
                    FROM RecipeIngredients ri
                    JOIN Ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = ?
                    """,
                    (recipe_id,),
                )
                ingredients = cursor.fetchall()
                for ingredient_name, quantity, unit in ingredients:
                    recipe["ingredients"].append(
                        {"name": ingredient_name, "quantity": quantity, "unit": unit}
                    )

                return recipe
        except Exception as e:
            print(f"Error getting recipe by short ID: {e}")
            return None

    def get_recipe_short_id(self, recipe_name: str) -> Optional[str]:
        """Get the short ID of a recipe by name."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT short_id FROM Recipes WHERE name = ?",
                    (recipe_name,),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting recipe short ID: {e}")
            return None

    def edit_recipe_by_short_id(
        self,
        short_id: str,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        time_minutes: Optional[int] = None,
        ingredients: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[bool, str]:
        """Edit an existing recipe by short ID with detailed error messages."""
        # Validate short ID format
        numeric_id = ShortIDGenerator.parse(short_id)
        if numeric_id is None:
            return (
                False,
                f"Invalid short ID format: '{short_id}'. Expected format: R123A",
            )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if recipe exists
                cursor.execute(
                    "SELECT id, name FROM Recipes WHERE id = ?", (numeric_id,)
                )
                result = cursor.fetchone()
                if not result:
                    return False, f"Recipe with short ID '{short_id}' not found"

                recipe_id, current_name = result
                updated_fields = []
                update_params = []

                # Build update query dynamically based on provided fields
                if name is not None:
                    updated_fields.append("name = ?")
                    update_params.append(name)

                if instructions is not None:
                    updated_fields.append("instructions = ?")
                    update_params.append(instructions)

                if time_minutes is not None:
                    updated_fields.append("time_minutes = ?")
                    update_params.append(time_minutes)

                # Always update last_modified
                updated_fields.append("last_modified = ?")
                update_params.append(datetime.now().isoformat())
                update_params.append(recipe_id)  # For WHERE clause

                if updated_fields:
                    cursor.execute(
                        f"UPDATE Recipes SET {', '.join(updated_fields)} WHERE id = ?",
                        update_params,
                    )

                # Update ingredients if provided
                if ingredients is not None:
                    # Delete existing ingredients
                    cursor.execute(
                        "DELETE FROM RecipeIngredients WHERE recipe_id = ?",
                        (recipe_id,),
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

                # Build success message
                changes = []
                if name is not None and name != current_name:
                    changes.append(f"name from '{current_name}' to '{name}'")
                if instructions is not None:
                    changes.append("instructions")
                if time_minutes is not None:
                    changes.append(f"time to {time_minutes} minutes")
                if ingredients is not None:
                    changes.append(f"ingredients ({len(ingredients)} items)")

                if changes:
                    return True, f"Successfully updated {', '.join(changes)}"
                else:
                    return (
                        True,
                        "No changes were made (all provided values were identical to current values)",
                    )

        except Exception as e:
            print(f"Error editing recipe by short ID: {e}")
            return False, f"Error editing recipe: {str(e)}"

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

    def get_household_characteristics(self) -> Dict[str, Any]:
        """Get household characteristics including number of adults and children."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT adults, children, notes, updated_date
                    FROM HouseholdCharacteristics
                    WHERE id = 1
                    """
                )
                result = cursor.fetchone()
                if result:
                    adults, children, notes, updated_date = result
                    return {
                        "adults": adults,
                        "children": children,
                        "notes": notes or "",
                        "updated_date": updated_date,
                    }
                else:
                    # Return default values if no record exists
                    return {
                        "adults": 2,
                        "children": 0,
                        "notes": "",
                        "updated_date": datetime.now().isoformat(),
                    }
        except Exception as e:
            print(f"Error getting household characteristics: {e}")
            return {
                "adults": 2,
                "children": 0,
                "notes": "",
                "updated_date": datetime.now().isoformat(),
            }

    def set_household_characteristics(
        self, adults: int, children: int, notes: str = ""
    ) -> bool:
        """Set household characteristics."""
        if adults < 1:
            print("Number of adults must be at least 1")
            return False
        if children < 0:
            print("Number of children cannot be negative")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO HouseholdCharacteristics
                    (id, adults, children, notes, updated_date)
                    VALUES (1, ?, ?, ?, datetime('now'))
                    """,
                    (adults, children, notes),
                )
                return True
        except Exception as e:
            print(f"Error setting household characteristics: {e}")
            return False

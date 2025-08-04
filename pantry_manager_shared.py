"""
Shared database PantryManager implementation.
All users share one database with user_id scoping for data isolation.
"""

import sqlite3
import psycopg2
import psycopg2.extras
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pantry_manager_abc import PantryManager


class SharedPantryManager(PantryManager):
    """PantryManager implementation using a shared database with user scoping."""

    def __init__(
        self, connection_string: str, user_id: int, backend: str = "sqlite", **kwargs
    ):
        """
        Initialize the shared pantry manager.

        Args:
            connection_string: Database connection string
            user_id: ID of the user (for data scoping)
            backend: 'sqlite' or 'postgresql'
            **kwargs: Additional configuration options
        """
        self.connection_string = connection_string
        self.user_id = user_id
        self.backend = backend
        self.connection_params = kwargs

        if backend == "postgresql" and connection_string.startswith(
            ("postgresql://", "postgres://")
        ):
            parsed = urlparse(connection_string)
            self.connection_params.update(
                {
                    "host": parsed.hostname,
                    "port": parsed.port or 5432,
                    "database": parsed.path.lstrip("/"),
                    "user": parsed.username,
                    "password": parsed.password,
                }
            )

    def _get_connection(self):
        """Get a database connection. Should be used in a context manager."""
        if self.backend == "postgresql":
            return psycopg2.connect(**self.connection_params)
        else:
            conn = sqlite3.connect(self.connection_string)
            conn.isolation_level = None  # Enable autocommit mode
            return conn

    def _get_placeholder(self) -> str:
        """Get the parameter placeholder for the current database."""
        return "%s" if self.backend == "postgresql" else "?"

    def add_ingredient(self, name: str, default_unit: str) -> bool:
        """Add a new ingredient to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    INSERT INTO ingredients (user_id, name, default_unit)
                    VALUES ({ph}, {ph}, {ph})
                """,
                    (self.user_id, name, default_unit),
                )
                return True
        except Exception as e:
            print(f"Error adding ingredient: {e}")
            return False

    def add_preference(
        self, category: str, item: str, level: str, notes: str = None
    ) -> bool:
        """Add a new food preference to the database."""
        if not category or not item or not level:
            raise ValueError("Category, item, and level are required")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                if self.backend == "postgresql":
                    cursor.execute(
                        f"""
                        INSERT INTO preferences (user_id, category, item, level, notes, created_date)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, NOW())
                    """,
                        (self.user_id, category, item, level, notes),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO preferences (user_id, category, item, level, notes, created_date)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, datetime('now'))
                    """,
                        (self.user_id, category, item, level, notes),
                    )
                return True
        except Exception as e:
            print(f"Error adding preference: {e}")
            return False

    def update_preference(
        self, preference_id: int, level: str, notes: str = None
    ) -> bool:
        """Update an existing food preference."""
        if not level:
            raise ValueError("Level is required")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    UPDATE preferences
                    SET level = {ph}, notes = {ph}
                    WHERE id = {ph} AND user_id = {ph}
                """,
                    (level, notes, preference_id, self.user_id),
                )

                if self.backend == "postgresql":
                    return cursor.rowcount > 0
                else:
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating preference: {e}")
            return False

    def delete_preference(self, preference_id: int) -> bool:
        """Delete a food preference by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    DELETE FROM preferences 
                    WHERE id = {ph} AND user_id = {ph}
                """,
                    (preference_id, self.user_id),
                )

                if self.backend == "postgresql":
                    return cursor.rowcount > 0
                else:
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting preference: {e}")
            return False

    def get_preferences(self) -> List[Dict[str, Any]]:
        """Get all food preferences for the current user."""
        try:
            with self._get_connection() as conn:
                if self.backend == "postgresql":
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                else:
                    cursor = conn.cursor()

                ph = self._get_placeholder()
                cursor.execute(
                    f"""
                    SELECT id, category, item, level, notes, created_date
                    FROM preferences
                    WHERE user_id = {ph}
                    ORDER BY id
                """,
                    (self.user_id,),
                )

                if self.backend == "postgresql":
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting preferences: {e}")
            return []

    def get_ingredient_id(self, name: str) -> Optional[int]:
        """Get the ID of an ingredient by name for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT id FROM ingredients 
                    WHERE name = {ph} AND user_id = {ph}
                """,
                    (name, self.user_id),
                )

                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting ingredient ID: {e}")
            return None

    def add_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """Add a new item to the pantry or increase existing item quantity."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Get or create the ingredient
                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    self.add_ingredient(item_name, unit)
                    ingredient_id = self.get_ingredient_id(item_name)

                if self.backend == "postgresql":
                    cursor.execute(
                        f"""
                        INSERT INTO pantry_transactions
                        (user_id, transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (
                            self.user_id,
                            "addition",
                            ingredient_id,
                            quantity,
                            unit,
                            datetime.now(),
                            notes,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO pantry_transactions
                        (user_id, transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (
                            self.user_id,
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
        """Remove a quantity of an item from the pantry."""
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
                ph = self._get_placeholder()

                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    print(f"Ingredient {item_name} not found in database")
                    return False

                if self.backend == "postgresql":
                    cursor.execute(
                        f"""
                        INSERT INTO pantry_transactions
                        (user_id, transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (
                            self.user_id,
                            "removal",
                            ingredient_id,
                            quantity,
                            unit,
                            datetime.now(),
                            notes,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO pantry_transactions
                        (user_id, transaction_type, ingredient_id, quantity, unit, transaction_date, notes)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (
                            self.user_id,
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
        """Get the current quantity of an item in the pantry for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    return 0.0

                cursor.execute(
                    f"""
                    SELECT
                        SUM(CASE
                            WHEN transaction_type = 'addition' THEN quantity
                            ELSE -quantity
                        END) as net_quantity
                    FROM pantry_transactions
                    WHERE ingredient_id = {ph} AND unit = {ph} AND user_id = {ph}
                """,
                    (ingredient_id, unit, self.user_id),
                )

                result = cursor.fetchone()[0]
                return float(result) if result is not None else 0.0
        except Exception as e:
            print(f"Error getting item quantity: {e}")
            return 0.0

    def get_multiple_item_quantities(
        self, items: List[tuple[str, str]]
    ) -> Dict[tuple[str, str], float]:
        """Get quantities for multiple (item_name, unit) pairs in one optimized query."""
        if not items:
            return {}

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Get ingredient IDs for all items at once
                item_names = list(set(item[0] for item in items))
                if not item_names:
                    return {}

                placeholders = ", ".join([ph] * len(item_names))
                cursor.execute(
                    f"""
                    SELECT name, id FROM ingredients 
                    WHERE user_id = {ph} AND name IN ({placeholders})
                """,
                    (self.user_id, *item_names),
                )

                name_to_id = dict(cursor.fetchall())

                # Build conditions for each (ingredient_id, unit) pair
                conditions = []
                params = [self.user_id]
                valid_items = []

                for item_name, unit in items:
                    if item_name in name_to_id:
                        conditions.append(f"(ingredient_id = {ph} AND unit = {ph})")
                        params.extend([name_to_id[item_name], unit])
                        valid_items.append((item_name, unit))

                if not conditions:
                    return {}

                cursor.execute(
                    f"""
                    SELECT ingredient_id, unit,
                           SUM(CASE WHEN transaction_type = 'addition' THEN quantity ELSE -quantity END) as net_quantity
                    FROM pantry_transactions
                    WHERE user_id = {ph} AND ({' OR '.join(conditions)})
                    GROUP BY ingredient_id, unit
                """,
                    params,
                )

                # Map back to (item_name, unit) tuples
                id_to_name = {v: k for k, v in name_to_id.items()}
                result = {}

                # Initialize all requested items to 0
                for item in items:
                    result[item] = 0.0

                # Fill in actual quantities
                for ingredient_id, unit, quantity in cursor.fetchall():
                    item_name = id_to_name.get(ingredient_id)
                    if item_name:
                        result[(item_name, unit)] = float(quantity) if quantity else 0.0

                return result
        except Exception as e:
            print(f"Error getting multiple item quantities: {e}")
            return {}

    def get_pantry_contents(self) -> Dict[str, Dict[str, float]]:
        """Get the current contents of the pantry for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT
                        i.name,
                        t.unit,
                        SUM(CASE
                            WHEN t.transaction_type = 'addition' THEN t.quantity
                            ELSE -t.quantity
                        END) as net_quantity
                    FROM pantry_transactions t
                    JOIN ingredients i ON t.ingredient_id = i.id
                    WHERE t.user_id = {ph}
                    GROUP BY i.name, t.unit
                    HAVING SUM(CASE
                        WHEN t.transaction_type = 'addition' THEN t.quantity
                        ELSE -t.quantity
                    END) > 0
                """,
                    (self.user_id,),
                )

                results = cursor.fetchall()
                contents = {}
                for item_name, unit, quantity in results:
                    if item_name not in contents:
                        contents[item_name] = {}
                    contents[item_name][unit] = (
                        float(quantity) if quantity is not None else 0.0
                    )

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
        """Add a new recipe to the database for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                if self.backend == "postgresql":
                    now = datetime.now()
                    cursor.execute(
                        f"""
                        INSERT INTO recipes
                        (user_id, name, instructions, time_minutes, created_date, last_modified)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                        RETURNING id
                    """,
                        (self.user_id, name, instructions, time_minutes, now, now),
                    )
                    recipe_id = cursor.fetchone()[0]
                else:
                    now = datetime.now().isoformat()
                    cursor.execute(
                        f"""
                        INSERT INTO recipes
                        (user_id, name, instructions, time_minutes, created_date, last_modified)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (self.user_id, name, instructions, time_minutes, now, now),
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
                        f"""
                        INSERT INTO recipe_ingredients
                        (recipe_id, ingredient_id, quantity, unit)
                        VALUES ({ph}, {ph}, {ph}, {ph})
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
        """Get a recipe and its ingredients by name for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT
                        r.id, r.instructions, r.time_minutes, r.rating,
                        r.created_date, r.last_modified
                    FROM recipes r
                    WHERE r.name = {ph} AND r.user_id = {ph}
                """,
                    (recipe_name, self.user_id),
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
                    f"""
                    SELECT i.name, ri.quantity, ri.unit
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = {ph}
                """,
                    (recipe_id,),
                )

                ingredients = [
                    {
                        "name": name,
                        "quantity": float(qty) if qty is not None else 0.0,
                        "unit": unit,
                    }
                    for name, qty, unit in cursor.fetchall()
                ]

                return {
                    "name": recipe_name,
                    "instructions": instructions,
                    "time_minutes": time_minutes,
                    "rating": float(rating) if rating is not None else None,
                    "created_date": (
                        created_date.isoformat()
                        if isinstance(created_date, datetime)
                        else created_date
                    ),
                    "last_modified": (
                        last_modified.isoformat()
                        if isinstance(last_modified, datetime)
                        else last_modified
                    ),
                    "ingredients": ingredients,
                }
        except Exception as e:
            print(f"Error getting recipe: {e}")
            return None

    def get_all_recipes(self) -> List[Dict[str, Any]]:
        """Get all recipes from the database for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Single query with JOIN to get all recipe data and ingredients
                cursor.execute(
                    f"""
                    SELECT 
                        r.name, r.instructions, r.time_minutes, r.rating,
                        r.created_date, r.last_modified,
                        i.name as ingredient_name, ri.quantity, ri.unit
                    FROM recipes r
                    LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                    LEFT JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE r.user_id = {ph}
                    ORDER BY r.name, i.name
                """,
                    (self.user_id,),
                )

                # Group results by recipe
                recipes = {}
                for row in cursor.fetchall():
                    recipe_name = row[0]
                    if recipe_name not in recipes:
                        recipes[recipe_name] = {
                            "name": recipe_name,
                            "instructions": row[1],
                            "time_minutes": row[2],
                            "rating": float(row[3]) if row[3] is not None else None,
                            "created_date": (
                                row[4].isoformat()
                                if isinstance(row[4], datetime)
                                else row[4]
                            ),
                            "last_modified": (
                                row[5].isoformat()
                                if isinstance(row[5], datetime)
                                else row[5]
                            ),
                            "ingredients": [],
                        }

                    if row[6]:  # Has ingredients
                        recipes[recipe_name]["ingredients"].append(
                            {
                                "name": row[6],
                                "quantity": (
                                    float(row[7]) if row[7] is not None else 0.0
                                ),
                                "unit": row[8],
                            }
                        )

                return list(recipes.values())
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
        """Edit an existing recipe in the database for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Check if recipe exists for this user
                cursor.execute(
                    f"""
                    SELECT id FROM recipes 
                    WHERE name = {ph} AND user_id = {ph}
                """,
                    (name, self.user_id),
                )

                result = cursor.fetchone()
                if not result:
                    print(f"Recipe '{name}' not found for current user")
                    return False

                recipe_id = result[0]

                if self.backend == "postgresql":
                    now = datetime.now()
                else:
                    now = datetime.now().isoformat()

                # Update recipe
                cursor.execute(
                    f"""
                    UPDATE recipes
                    SET instructions = {ph}, time_minutes = {ph}, last_modified = {ph}
                    WHERE id = {ph}
                """,
                    (instructions, time_minutes, now, recipe_id),
                )

                # Delete existing ingredients
                cursor.execute(
                    f"""
                    DELETE FROM recipe_ingredients WHERE recipe_id = {ph}
                """,
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
                        f"""
                        INSERT INTO recipe_ingredients
                        (recipe_id, ingredient_id, quantity, unit)
                        VALUES ({ph}, {ph}, {ph}, {ph})
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
        """Rate a recipe on a scale of 1-5 for the current user."""
        if not (1 <= rating <= 5):
            print("Rating must be between 1 and 5")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                if self.backend == "postgresql":
                    now = datetime.now()
                else:
                    now = datetime.now().isoformat()

                cursor.execute(
                    f"""
                    UPDATE recipes
                    SET rating = {ph}, last_modified = {ph}
                    WHERE name = {ph} AND user_id = {ph}
                """,
                    (rating, now, recipe_name, self.user_id),
                )

                if self.backend == "postgresql":
                    return cursor.rowcount > 0
                else:
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error rating recipe: {e}")
            return False

    def execute_recipe(self, recipe_name: str) -> tuple[bool, str]:
        """Execute a recipe by removing its ingredients from the pantry for the current user."""
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
        """Assign a recipe to a specific date in the meal plan for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT id FROM recipes 
                    WHERE name = {ph} AND user_id = {ph}
                """,
                    (recipe_name, self.user_id),
                )

                result = cursor.fetchone()
                if not result:
                    return False

                recipe_id = result[0]

                if self.backend == "postgresql":
                    cursor.execute(
                        f"""
                        INSERT INTO meal_plan (user_id, meal_date, recipe_id)
                        VALUES ({ph}, {ph}, {ph})
                        ON CONFLICT (user_id, meal_date) 
                        DO UPDATE SET recipe_id = EXCLUDED.recipe_id
                    """,
                        (self.user_id, meal_date, recipe_id),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT OR REPLACE INTO meal_plan (user_id, meal_date, recipe_id)
                        VALUES ({ph}, {ph}, {ph})
                    """,
                        (self.user_id, meal_date, recipe_id),
                    )
                return True
        except Exception as e:
            print(f"Error setting meal plan: {e}")
            return False

    def get_meal_plan(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve planned meals between two dates for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT meal_date, r.name
                    FROM meal_plan m
                    JOIN recipes r ON m.recipe_id = r.id
                    WHERE m.user_id = {ph} AND meal_date BETWEEN {ph} AND {ph}
                    ORDER BY meal_date
                """,
                    (self.user_id, start_date, end_date),
                )

                return [{"date": row[0], "recipe": row[1]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting meal plan: {e}")
            return []

    def clear_recipe_for_date(self, meal_date: str) -> bool:
        """Clear/remove a recipe from a specific date in the meal plan for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"DELETE FROM meal_plan WHERE user_id = {ph} AND meal_date = {ph}",
                    (self.user_id, meal_date),
                )

                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error clearing meal plan for {meal_date}: {e}")
            return False

    def get_grocery_list(self) -> List[Dict[str, Any]]:
        """Calculate grocery items needed for the coming week's meal plan."""
        start = date.today()
        end = start + timedelta(days=6)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Single query to get all meal plan recipes and their ingredients
                cursor.execute(
                    f"""
                    SELECT r.name as recipe_name, i.name as ingredient_name,
                           ri.quantity, ri.unit
                    FROM meal_plan m
                    JOIN recipes r ON m.recipe_id = r.id
                    JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE m.user_id = {ph} AND meal_date BETWEEN {ph} AND {ph}
                """,
                    (self.user_id, start.isoformat(), end.isoformat()),
                )

                # Calculate required ingredients
                required: Dict[tuple[str, str], float] = {}
                for recipe_name, ingredient_name, quantity, unit in cursor.fetchall():
                    key = (ingredient_name, unit)
                    required[key] = required.get(key, 0) + float(quantity)

            if not required:
                return []

            # Get current pantry quantities in batch
            quantities = self.get_multiple_item_quantities(list(required.keys()))

            # Calculate grocery list
            grocery_list = []
            for (name, unit), needed in required.items():
                have = quantities.get((name, unit), 0.0)
                if have < needed:
                    grocery_list.append(
                        {"name": name, "quantity": float(needed - have), "unit": unit}
                    )

            return grocery_list
        except Exception as e:
            print(f"Error getting optimized grocery list: {e}")
            return []

    def get_transaction_history(
        self, item_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get the transaction history for all items or a specific item for the current user."""
        try:
            with self._get_connection() as conn:
                if self.backend == "postgresql":
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                else:
                    cursor = conn.cursor()

                ph = self._get_placeholder()

                if item_name:
                    ingredient_id = self.get_ingredient_id(item_name)
                    if ingredient_id is None:
                        return []
                    cursor.execute(
                        f"""
                        SELECT t.*, i.name as item_name
                        FROM pantry_transactions t
                        JOIN ingredients i ON t.ingredient_id = i.id
                        WHERE t.ingredient_id = {ph} AND t.user_id = {ph}
                        ORDER BY t.transaction_date DESC, t.id DESC
                    """,
                        (ingredient_id, self.user_id),
                    )
                else:
                    cursor.execute(
                        f"""
                        SELECT t.*, i.name as item_name
                        FROM pantry_transactions t
                        JOIN ingredients i ON t.ingredient_id = i.id
                        WHERE t.user_id = {ph}
                        ORDER BY t.transaction_date DESC, t.id DESC
                    """,
                        (self.user_id,),
                    )

                if self.backend == "postgresql":
                    transactions = []
                    for row in cursor.fetchall():
                        row_dict = dict(row)
                        # Convert datetime to ISO string for consistency
                        if row_dict.get("transaction_date") and isinstance(
                            row_dict["transaction_date"], datetime
                        ):
                            row_dict["transaction_date"] = row_dict[
                                "transaction_date"
                            ].isoformat()
                        transactions.append(row_dict)
                    return transactions
                else:
                    columns = [description[0] for description in cursor.description]
                    transactions = []
                    for row in cursor.fetchall():
                        transactions.append(dict(zip(columns, row)))
                    return transactions

        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []

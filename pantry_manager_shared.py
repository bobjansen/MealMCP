"""
Shared database PantryManager implementation.
All users share one database with user_id scoping for data isolation.
"""

import sqlite3
import psycopg2
import psycopg2.extras
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pantry_manager_abc import PantryManager
from short_id_utils import ShortIDGenerator
from constants import (
    PREFERENCE_CATEGORIES,
    MAX_INGREDIENT_NAME_LENGTH,
    MAX_RECIPE_NAME_LENGTH,
    MAX_INSTRUCTIONS_LENGTH,
    MAX_NOTES_LENGTH,
    MAX_QUANTITY_VALUE,
    MAX_TIME_MINUTES,
)
from error_utils import safe_execute, safe_float_conversion, validate_required_params


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

    # Input Validation Methods
    def _validate_string(
        self,
        value: Any,
        field_name: str,
        max_length: int = 255,
        min_length: int = 1,
        allow_empty: bool = False,
    ) -> str:
        """Validate and sanitize string input."""
        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string, got {type(value).__name__}"
            )

        value = value.strip()

        if not allow_empty and len(value) == 0:
            raise ValueError(f"{field_name} cannot be empty")

        if len(value) < min_length:
            raise ValueError(
                f"{field_name} must be at least {min_length} characters long"
            )

        if len(value) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters")

        return value

    def _validate_ingredient_name(self, name: Any) -> str:
        """Validate ingredient name."""
        name = self._validate_string(
            name, "Ingredient name", max_length=MAX_INGREDIENT_NAME_LENGTH
        )
        # Allow letters, numbers, spaces, hyphens, apostrophes, parentheses
        if not re.match(r"^[a-zA-Z0-9\s\-'()]+$", name):
            raise ValueError("Ingredient name contains invalid characters")
        return name

    def _validate_unit(self, unit: Any) -> str:
        """Validate unit name."""
        unit = self._validate_string(unit, "Unit", max_length=50)
        # Allow letters, spaces, periods, forward slashes for units like "cups", "lb", "fl oz", "tbsp"
        if not re.match(r"^[a-zA-Z\s\./]+$", unit):
            raise ValueError("Unit contains invalid characters")
        return unit

    def _validate_quantity(self, quantity: Any) -> float:
        """Validate quantity value."""
        # First try safe conversion without bounds to detect type errors
        converted = safe_float_conversion(quantity, default=None)

        if converted is None:
            raise ValueError("Quantity must be a number")

        # Then apply bounds checking manually to get specific error messages
        if converted < 0:
            raise ValueError("Quantity cannot be negative")

        if converted > MAX_QUANTITY_VALUE:
            raise ValueError(f"Quantity is too large (max: {MAX_QUANTITY_VALUE:,})")

        return converted

    def _validate_recipe_name(self, name: Any) -> str:
        """Validate recipe name."""
        name = self._validate_string(
            name, "Recipe name", max_length=MAX_RECIPE_NAME_LENGTH
        )
        # More permissive for recipe names - allow most printable characters except <>&
        if re.search(r"[<>&]", name):
            raise ValueError("Recipe name contains invalid characters")
        return name

    def _validate_instructions(self, instructions: Any) -> str:
        """Validate recipe instructions."""
        instructions = self._validate_string(
            instructions, "Instructions", max_length=MAX_INSTRUCTIONS_LENGTH
        )
        # Remove potentially dangerous content but allow most text
        if re.search(
            r"<script[^>]*>.*?</script>", instructions, re.IGNORECASE | re.DOTALL
        ):
            raise ValueError("Instructions contain potentially dangerous content")
        return instructions

    def _validate_time_minutes(self, time_minutes: Any) -> int:
        """Validate cooking time in minutes."""
        if isinstance(time_minutes, (int, float)):
            time_minutes = int(time_minutes)
        else:
            try:
                time_minutes = int(time_minutes)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Time must be a number, got {type(time_minutes).__name__}"
                )

        if time_minutes < 0:
            raise ValueError("Time cannot be negative")

        if time_minutes > MAX_TIME_MINUTES:
            raise ValueError(f"Time is too long (max: {MAX_TIME_MINUTES} minutes)")

        return time_minutes

    def _validate_date(self, date_value: Any) -> str:
        """Validate date string."""
        if isinstance(date_value, date):
            return date_value.isoformat()

        if not isinstance(date_value, str):
            raise ValueError(
                f"Date must be a string or date object, got {type(date_value).__name__}"
            )

        date_value = date_value.strip()

        # Validate ISO date format (YYYY-MM-DD)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_value):
            raise ValueError("Date must be in YYYY-MM-DD format")

        try:
            # Validate it's a real date
            datetime.strptime(date_value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date")

        return date_value

    def _validate_preference_category(self, category: Any) -> str:
        """Validate preference category."""
        category = self._validate_string(category, "Category", max_length=50)
        if category.lower() not in PREFERENCE_CATEGORIES:
            raise ValueError(
                f"Invalid category. Allowed: {', '.join(PREFERENCE_CATEGORIES)}"
            )
        return category.lower()

    def _validate_preference_level(self, level: Any) -> str:
        """Validate preference level."""
        level = self._validate_string(level, "Level", max_length=20)
        # Only allow specific levels
        allowed_levels = {"required", "preferred", "neutral", "avoid", "severe"}
        if level.lower() not in allowed_levels:
            raise ValueError(f"Invalid level. Allowed: {', '.join(allowed_levels)}")
        return level.lower()

    def _validate_notes(self, notes: Any) -> str:
        """Validate notes field."""
        if notes is None:
            return ""
        return self._validate_string(
            notes, "Notes", max_length=MAX_NOTES_LENGTH, allow_empty=True
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
        # Validate inputs
        name = self._validate_ingredient_name(name)
        default_unit = self._validate_unit(default_unit)

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
        # Validate inputs
        category = self._validate_preference_category(category)
        item = self._validate_ingredient_name(
            item
        )  # Same validation as ingredient names
        level = self._validate_preference_level(level)
        notes = self._validate_notes(notes)

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
        # Validate inputs
        item_name = self._validate_ingredient_name(item_name)
        quantity = self._validate_quantity(quantity)
        unit = self._validate_unit(unit)
        notes = self._validate_notes(notes)

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
        # Validate inputs
        item_name = self._validate_ingredient_name(item_name)
        quantity = self._validate_quantity(quantity)
        unit = self._validate_unit(unit)
        notes = self._validate_notes(notes)

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
    ) -> tuple[bool, Optional[str]]:
        """Add a new recipe to the database for the current user."""
        # Validate inputs
        name = self._validate_recipe_name(name)
        instructions = self._validate_instructions(instructions)
        time_minutes = self._validate_time_minutes(time_minutes)

        # Validate ingredients list
        if not isinstance(ingredients, list):
            raise ValueError("Ingredients must be a list")

        validated_ingredients = []
        for i, ingredient in enumerate(ingredients):
            if not isinstance(ingredient, dict):
                raise ValueError(f"Ingredient {i} must be a dictionary")

            ingredient_name = self._validate_ingredient_name(ingredient.get("name", ""))
            ingredient_quantity = self._validate_quantity(ingredient.get("quantity", 0))
            ingredient_unit = self._validate_unit(ingredient.get("unit", ""))

            validated_ingredients.append(
                {
                    "name": ingredient_name,
                    "quantity": ingredient_quantity,
                    "unit": ingredient_unit,
                }
            )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Generate user-scoped short ID based on user's recipe count
                cursor.execute(
                    f"SELECT COUNT(*) FROM recipes WHERE user_id = {ph}",
                    (self.user_id,),
                )
                user_recipe_count = cursor.fetchone()[0]
                next_user_recipe_id = user_recipe_count + 1
                short_id = ShortIDGenerator.generate(next_user_recipe_id)

                if self.backend == "postgresql":
                    now = datetime.now()
                    cursor.execute(
                        f"""
                        INSERT INTO recipes
                        (short_id, user_id, name, instructions, time_minutes, created_date, last_modified)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                        RETURNING id
                    """,
                        (
                            short_id,
                            self.user_id,
                            name,
                            instructions,
                            time_minutes,
                            now,
                            now,
                        ),
                    )
                    recipe_id = cursor.fetchone()[0]
                else:
                    now = datetime.now().isoformat()
                    cursor.execute(
                        f"""
                        INSERT INTO recipes
                        (short_id, user_id, name, instructions, time_minutes, created_date, last_modified)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                        (
                            short_id,
                            self.user_id,
                            name,
                            instructions,
                            time_minutes,
                            now,
                            now,
                        ),
                    )
                    recipe_id = cursor.lastrowid

                # Add ingredients (use validated ingredients)
                for ingredient in validated_ingredients:
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
                return True, short_id
        except Exception as e:
            print(f"Error adding recipe: {e}")
            return False, None

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

                # Single query with JOIN to get all recipe data and ingredients including short IDs
                cursor.execute(
                    f"""
                    SELECT 
                        r.short_id, r.name, r.instructions, r.time_minutes, r.rating,
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
                    recipe_short_id = str(row[0])
                    recipe_name = row[1]
                    if recipe_short_id not in recipes:
                        recipes[recipe_short_id] = {
                            "short_id": recipe_short_id,
                            "name": recipe_name,
                            "instructions": row[2],
                            "time_minutes": row[3],
                            "rating": float(row[4]) if row[4] is not None else None,
                            "created_date": (
                                row[5].isoformat()
                                if isinstance(row[5], datetime)
                                else row[5]
                            ),
                            "last_modified": (
                                row[6].isoformat()
                                if isinstance(row[6], datetime)
                                else row[6]
                            ),
                            "ingredients": [],
                        }

                    if row[7]:  # Has ingredients
                        recipes[recipe_short_id]["ingredients"].append(
                            {
                                "name": row[7],
                                "quantity": (
                                    float(row[8]) if row[8] is not None else 0.0
                                ),
                                "unit": row[9],
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
        # Validate inputs (same as add_recipe)
        name = self._validate_recipe_name(name)
        instructions = self._validate_instructions(instructions)
        time_minutes = self._validate_time_minutes(time_minutes)

        # Validate ingredients list
        if not isinstance(ingredients, list):
            raise ValueError("Ingredients must be a list")

        validated_ingredients = []
        for i, ingredient in enumerate(ingredients):
            if not isinstance(ingredient, dict):
                raise ValueError(f"Ingredient {i} must be a dictionary")

            ingredient_name = self._validate_ingredient_name(ingredient.get("name", ""))
            ingredient_quantity = self._validate_quantity(ingredient.get("quantity", 0))
            ingredient_unit = self._validate_unit(ingredient.get("unit", ""))

            validated_ingredients.append(
                {
                    "name": ingredient_name,
                    "quantity": ingredient_quantity,
                    "unit": ingredient_unit,
                }
            )

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
                for ingredient in validated_ingredients:
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
        # Validate inputs
        recipe_name = self._validate_recipe_name(recipe_name)

        if not isinstance(rating, (int, float)):
            raise ValueError("Rating must be a number")

        rating = int(rating)
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

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

    # Short ID-based Recipe Methods
    def get_recipe_by_short_id(self, short_id: str) -> Optional[Dict[str, Any]]:
        """Get a recipe and its ingredients by short ID for the current user."""
        # Validate short ID format
        if not ShortIDGenerator.is_valid(short_id):
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Get recipe details by short_id within user scope
                cursor.execute(
                    f"""
                    SELECT id, short_id, name, instructions, time_minutes, rating, created_date, last_modified 
                    FROM recipes 
                    WHERE short_id = {ph} AND user_id = {ph}
                    """,
                    (short_id, self.user_id),
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
                    "created_date": str(created_date),
                    "last_modified": str(last_modified),
                    "ingredients": [],
                }

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
                ingredients = cursor.fetchall()
                for ingredient_name, quantity, unit in ingredients:
                    recipe["ingredients"].append(
                        {
                            "name": ingredient_name,
                            "quantity": float(quantity),
                            "unit": unit,
                        }
                    )

                return recipe
        except Exception as e:
            print(f"Error getting recipe by short ID: {e}")
            return None

    def get_recipe_short_id(self, recipe_name: str) -> Optional[str]:
        """Get the short ID of a recipe by name for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()
                cursor.execute(
                    f"""
                    SELECT short_id FROM recipes 
                    WHERE name = {ph} AND user_id = {ph}
                    """,
                    (recipe_name, self.user_id),
                )
                result = cursor.fetchone()
                return str(result[0]) if result else None
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
        """Edit an existing recipe by short ID with detailed error messages for the current user."""
        # Validate short ID format
        if not ShortIDGenerator.is_valid(short_id):
            return (
                False,
                f"Invalid short ID format: '{short_id}'. Expected format: R123A",
            )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                # Check if recipe exists for this user by short_id
                cursor.execute(
                    f"SELECT id, name FROM recipes WHERE short_id = {ph} AND user_id = {ph}",
                    (short_id, self.user_id),
                )
                result = cursor.fetchone()
                if not result:
                    return (
                        False,
                        f"Recipe with short ID '{short_id}' not found for current user",
                    )

                recipe_id, current_name = result
                updated_fields = []
                update_params = []

                # Validate and build update query dynamically
                if name is not None:
                    name = self._validate_recipe_name(name)
                    updated_fields.append(f"name = {ph}")
                    update_params.append(name)

                if instructions is not None:
                    instructions = self._validate_instructions(instructions)
                    updated_fields.append(f"instructions = {ph}")
                    update_params.append(instructions)

                if time_minutes is not None:
                    time_minutes = self._validate_time_minutes(time_minutes)
                    updated_fields.append(f"time_minutes = {ph}")
                    update_params.append(time_minutes)

                # Always update last_modified
                updated_fields.append(f"last_modified = {ph}")
                if self.backend == "postgresql":
                    update_params.append(datetime.now())
                else:
                    update_params.append(datetime.now().isoformat())

                # Add WHERE conditions
                update_params.extend([short_id, self.user_id])

                if updated_fields:
                    cursor.execute(
                        f"UPDATE recipes SET {', '.join(updated_fields)} WHERE short_id = {ph} AND user_id = {ph}",
                        update_params,
                    )

                # Update ingredients if provided
                if ingredients is not None:
                    # Validate ingredients
                    validated_ingredients = []
                    for i, ingredient in enumerate(ingredients):
                        if not isinstance(ingredient, dict):
                            return False, f"Ingredient {i} must be a dictionary"

                        try:
                            ingredient_name = self._validate_ingredient_name(
                                ingredient.get("name", "")
                            )
                            ingredient_quantity = self._validate_quantity(
                                ingredient.get("quantity", 0)
                            )
                            ingredient_unit = self._validate_unit(
                                ingredient.get("unit", "")
                            )

                            validated_ingredients.append(
                                {
                                    "name": ingredient_name,
                                    "quantity": ingredient_quantity,
                                    "unit": ingredient_unit,
                                }
                            )
                        except ValueError as e:
                            return False, f"Invalid ingredient {i}: {str(e)}"

                    # Delete existing ingredients
                    cursor.execute(
                        f"DELETE FROM recipe_ingredients WHERE recipe_id = {ph}",
                        (recipe_id,),
                    )

                    # Add new ingredients
                    for ingredient in validated_ingredients:
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

        except ValueError as ve:
            return False, f"Validation error: {str(ve)}"
        except Exception as e:
            print(f"Error editing recipe by short ID: {e}")
            return False, f"Error editing recipe: {str(e)}"

    def set_meal_plan(self, meal_date: str, recipe_name: str) -> bool:
        """Assign a recipe to a specific date in the meal plan for the current user."""
        # Validate inputs
        meal_date = self._validate_date(meal_date)
        recipe_name = self._validate_recipe_name(recipe_name)

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
        # Validate inputs
        start_date = self._validate_date(start_date)
        end_date = self._validate_date(end_date)

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
        # Validate inputs
        meal_date = self._validate_date(meal_date)

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

    def get_household_characteristics(self) -> Dict[str, Any]:
        """Get household characteristics from user data for the current user."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    SELECT household_adults, household_children, preferred_language
                    FROM users
                    WHERE id = {ph}
                    """,
                    (self.user_id,),
                )
                result = cursor.fetchone()
                if result:
                    adults, children, language = result
                    return {
                        "adults": adults or 2,
                        "children": children or 0,
                        "notes": f"Language preference: {language or 'en'}",
                        "updated_date": datetime.now().isoformat(),
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
        """Set household characteristics for the current user."""
        # Validate inputs
        if not isinstance(adults, (int, float)):
            raise ValueError("Adults must be a number")

        adults = int(adults)
        if adults < 1 or adults > 50:  # Reasonable upper limit
            raise ValueError("Number of adults must be between 1 and 50")

        if not isinstance(children, (int, float)):
            raise ValueError("Children must be a number")

        children = int(children)
        if children < 0 or children > 50:  # Reasonable upper limit
            raise ValueError("Number of children must be between 0 and 50")

        notes = self._validate_notes(notes)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = self._get_placeholder()

                cursor.execute(
                    f"""
                    UPDATE users
                    SET household_adults = {ph}, household_children = {ph}
                    WHERE id = {ph}
                    """,
                    (adults, children, self.user_id),
                )

                if self.backend == "postgresql":
                    return cursor.rowcount > 0
                else:
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"Error setting household characteristics: {e}")
            return False

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from pantry_manager_abc import PantryManager
from short_id_utils import parse_short_id
from error_utils import safe_execute, validate_required_params
from constants import DEFAULT_UNITS


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
        try:
            self._initialize_units()
        except Exception:
            # Defer database errors until actual operations
            pass

    def _get_connection(self):
        """Get a database connection. Should be used in a context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.isolation_level = None  # Enable autocommit mode
        return conn

    def _initialize_units(self) -> None:
        """Populate units table with defaults if empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    base_unit TEXT NOT NULL,
                    size REAL NOT NULL
                )
                """
            )
            cursor.execute("SELECT COUNT(*) FROM Units")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO Units (name, base_unit, size) VALUES (?, ?, ?)",
                    [(u["name"], u["base_unit"], u["size"]) for u in DEFAULT_UNITS],
                )

    @safe_execute("list units", default_return=[])
    def list_units(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, base_unit, size FROM Units")
            return [
                {"name": name, "base_unit": base_unit, "size": size}
                for name, base_unit, size in cursor.fetchall()
            ]

    @safe_execute("set unit", default_return=False)
    def set_unit(self, name: str, base_unit: str, size: float) -> bool:
        validate_required_params(name=name, base_unit=base_unit, size=size)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Units (name, base_unit, size)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET base_unit=excluded.base_unit, size=excluded.size
                """,
                (name, base_unit, size),
            )
            return True

    @safe_execute("delete unit", default_return=False)
    def delete_unit(self, name: str) -> bool:
        """Delete a custom measurement unit."""
        validate_required_params(name=name)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if unit is used in transactions before deleting
            cursor.execute(
                "SELECT COUNT(*) FROM PantryTransactions WHERE unit = ?", (name,)
            )
            if cursor.fetchone()[0] > 0:
                return False  # Cannot delete unit that's being used

            # Delete the unit
            cursor.execute("DELETE FROM Units WHERE name = ?", (name,))
            return cursor.rowcount > 0

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

        # Normalize the unit name to match database entries
        normalized_unit = self._normalize_unit_name(unit)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get or create the ingredient
            ingredient_id = self.get_ingredient_id(item_name)
            if ingredient_id is None:
                self.add_ingredient(item_name, normalized_unit)
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
                    normalized_unit,
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
            # Normalize the unit name to match database entries
            normalized_unit = self._normalize_unit_name(unit)

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
                        normalized_unit,
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

    def get_total_item_quantity(self, item_name: str, unit: str) -> float:
        """Get total quantity of an item across all units converted to the specified unit."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                ingredient_id = self.get_ingredient_id(item_name)
                if ingredient_id is None:
                    return 0.0

                # First try exact match
                cursor.execute(
                    "SELECT base_unit, size FROM Units WHERE name = ?",
                    (unit,),
                )
                target = cursor.fetchone()

                # If no exact match, try common variations
                if not target:
                    # Create mapping for common abbreviations and case variations
                    unit_mappings = {
                        # Volume abbreviations
                        "tsp": "Teaspoon",
                        "tbsp": "Tablespoon",
                        "cup": "Cup",
                        "ml": "Milliliter",
                        "l": "Liter",
                        "fl oz": "Fluid ounce",
                        "pt": "Pint",
                        "qt": "Quart",
                        "gal": "Gallon",
                        # Weight abbreviations
                        "g": "Gram",
                        "kg": "Kilogram",
                        "oz": "Ounce",
                        "lb": "Pound",
                        "lbs": "Pound",
                        # Count abbreviations
                        "pc": "Piece",
                        "pcs": "Piece",
                        "piece": "Piece",
                        "pieces": "Piece",
                        # Case variations (lowercase to proper case)
                        "teaspoon": "Teaspoon",
                        "tablespoon": "Tablespoon",
                        "milliliter": "Milliliter",
                        "liter": "Liter",
                        "gram": "Gram",
                        "kilogram": "Kilogram",
                        "ounce": "Ounce",
                        "pound": "Pound",
                    }

                    # Try mapped unit name
                    mapped_unit = unit_mappings.get(unit.lower())
                    if mapped_unit:
                        cursor.execute(
                            "SELECT base_unit, size FROM Units WHERE name = ?",
                            (mapped_unit,),
                        )
                        target = cursor.fetchone()

                    # If still no match, try case-insensitive search
                    if not target:
                        cursor.execute(
                            "SELECT base_unit, size FROM Units WHERE LOWER(name) = LOWER(?)",
                            (unit,),
                        )
                        target = cursor.fetchone()

                # If still no match, fall back to old behavior
                if not target:
                    return self.get_item_quantity(item_name, unit)

                target_base, target_size = target

                cursor.execute(
                    """
                    SELECT t.unit, u.base_unit, u.size,
                           SUM(CASE WHEN t.transaction_type = 'addition' THEN t.quantity ELSE -t.quantity END)
                               AS net_quantity
                    FROM PantryTransactions t
                    JOIN Units u ON t.unit = u.name
                    WHERE t.ingredient_id = ?
                    GROUP BY t.unit, u.base_unit, u.size
                    """,
                    (ingredient_id,),
                )

                total_base = 0.0
                for unit_name, base_unit, size, qty in cursor.fetchall():
                    if base_unit == target_base and qty:
                        total_base += qty * size

                return total_base / target_size
        except Exception as e:
            print(f"Error getting total item quantity: {e}")
            return 0.0

    def _normalize_unit_name(self, unit: str) -> str:
        """Normalize unit name to match Units table entries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # First try exact match
                cursor.execute("SELECT name FROM Units WHERE name = ?", (unit,))
                if cursor.fetchone():
                    return unit

                # Try common abbreviation mappings
                unit_mappings = {
                    "tsp": "Teaspoon",
                    "tbsp": "Tablespoon",
                    "cup": "Cup",
                    "ml": "Milliliter",
                    "l": "Liter",
                    "fl oz": "Fluid ounce",
                    "pt": "Pint",
                    "qt": "Quart",
                    "gal": "Gallon",
                    "g": "Gram",
                    "kg": "Kilogram",
                    "oz": "Ounce",
                    "lb": "Pound",
                    "lbs": "Pound",
                    "pc": "Piece",
                    "pcs": "Piece",
                    "piece": "Piece",
                    "pieces": "Piece",
                    "teaspoon": "Teaspoon",
                    "tablespoon": "Tablespoon",
                    "milliliter": "Milliliter",
                    "liter": "Liter",
                    "gram": "Gram",
                    "kilogram": "Kilogram",
                    "ounce": "Ounce",
                    "pound": "Pound",
                }

                mapped_unit = unit_mappings.get(unit.lower())
                if mapped_unit:
                    cursor.execute(
                        "SELECT name FROM Units WHERE name = ?", (mapped_unit,)
                    )
                    if cursor.fetchone():
                        return mapped_unit

                # Try case-insensitive match
                cursor.execute(
                    "SELECT name FROM Units WHERE LOWER(name) = LOWER(?)", (unit,)
                )
                result = cursor.fetchone()
                if result:
                    return result[0]

                # If no match found, return original unit (might need to be added to Units)
                return unit

        except Exception as e:
            print(f"Error normalizing unit name: {e}")
            return unit

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

                cursor.execute(
                    """
                    INSERT INTO Recipes
                    (name, instructions, time_minutes, created_date, last_modified)
                    VALUES (?, ?, ?, ?, ?)
                    RETURNING id, short_id
                    """,
                    (name, instructions, time_minutes, now, now),
                )
                recipe_id, short_id = cursor.fetchone()

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
        Get a recipe and its ingredients by name with fuzzy matching.

        Args:
            recipe_name: Name of the recipe to retrieve

        Returns:
            Optional[Dict[str, Any]]: Recipe details including ingredients, or None if not found
        """
        if not recipe_name or not recipe_name.strip():
            return None

        search_term = recipe_name.strip()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Strategy 1: Exact match
                cursor.execute(
                    """
                    SELECT
                        r.id, r.name, r.instructions, r.time_minutes, r.rating,
                        r.created_date, r.last_modified, 1 as match_score
                    FROM Recipes r
                    WHERE r.name = ?
                    """,
                    (search_term,),
                )
                recipe = cursor.fetchone()

                # Strategy 2: Case-insensitive exact match
                if not recipe:
                    cursor.execute(
                        """
                        SELECT
                            r.id, r.name, r.instructions, r.time_minutes, r.rating,
                            r.created_date, r.last_modified, 2 as match_score
                        FROM Recipes r
                        WHERE LOWER(r.name) = LOWER(?)
                        """,
                        (search_term,),
                    )
                    recipe = cursor.fetchone()

                # Strategy 3: Word-based matching - all words in search term appear in recipe name
                if not recipe:
                    search_words = [
                        w.lower() for w in search_term.split() if len(w) > 2
                    ]
                    if search_words:
                        word_conditions = " AND ".join(
                            ["LOWER(r.name) LIKE ?" for _ in search_words]
                        )
                        word_params = [f"%{word}%" for word in search_words]

                        cursor.execute(
                            f"""
                            SELECT
                                r.id, r.name, r.instructions, r.time_minutes, r.rating,
                                r.created_date, r.last_modified, 3 as match_score
                            FROM Recipes r
                            WHERE {word_conditions}
                            ORDER BY LENGTH(r.name) ASC
                            LIMIT 1
                            """,
                            word_params,
                        )
                        recipe = cursor.fetchone()

                # Strategy 4: Any word in search term appears in recipe name
                if not recipe:
                    search_words = [
                        w.lower() for w in search_term.split() if len(w) > 2
                    ]
                    if search_words:
                        word_conditions = " OR ".join(
                            ["LOWER(r.name) LIKE ?" for _ in search_words]
                        )
                        word_params = [f"%{word}%" for word in search_words]

                        cursor.execute(
                            f"""
                            SELECT
                                r.id, r.name, r.instructions, r.time_minutes, r.rating,
                                r.created_date, r.last_modified, 4 as match_score
                            FROM Recipes r
                            WHERE {word_conditions}
                            ORDER BY LENGTH(r.name) ASC
                            LIMIT 1
                            """,
                            word_params,
                        )
                        recipe = cursor.fetchone()

                # Strategy 5: Substring match (fallback)
                if not recipe:
                    cursor.execute(
                        """
                        SELECT
                            r.id, r.name, r.instructions, r.time_minutes, r.rating,
                            r.created_date, r.last_modified, 5 as match_score
                        FROM Recipes r
                        WHERE LOWER(r.name) LIKE LOWER(?)
                        ORDER BY LENGTH(r.name) ASC
                        LIMIT 1
                        """,
                        (f"%{search_term}%",),
                    )
                    recipe = cursor.fetchone()

                # Strategy 6: Character-level fuzzy matching for typos
                if not recipe and len(search_term) >= 4:
                    # Generate various character-level variations
                    variations = []
                    term = search_term.lower()

                    # Missing character variations
                    for i in range(len(term)):
                        if len(term) > 3:  # Don't make words too short
                            variations.append(f"%{term[:i] + term[i+1:]}%")

                    # Extra character variations (search within the term)
                    if len(term) > 4:
                        variations.append(f"%{term[1:]}%")  # Remove first char
                        variations.append(f"%{term[:-1]}%")  # Remove last char
                        if len(term) > 5:
                            variations.append(
                                f"%{term[1:-1]}%"
                            )  # Remove first and last

                    # Character substitution (common patterns)
                    common_typos = {
                        "i": "e",
                        "e": "i",
                        "a": "e",
                        "e": "a",
                        "tion": "sion",
                        "sion": "tion",
                    }

                    for old, new in common_typos.items():
                        if old in term:
                            variations.append(f"%{term.replace(old, new)}%")

                    if variations:
                        # Create OR conditions for all variations
                        or_conditions = " OR ".join(
                            ["LOWER(r.name) LIKE ?" for _ in variations]
                        )

                        cursor.execute(
                            f"""
                            SELECT
                                r.id, r.name, r.instructions, r.time_minutes, r.rating,
                                r.created_date, r.last_modified, 6 as match_score
                            FROM Recipes r
                            WHERE {or_conditions}
                            ORDER BY LENGTH(r.name) ASC
                            LIMIT 1
                            """,
                            variations,
                        )
                        recipe = cursor.fetchone()

                if not recipe:
                    return None

                (
                    recipe_id,
                    actual_name,
                    instructions,
                    time_minutes,
                    rating,
                    created_date,
                    last_modified,
                    match_score,
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
                    "name": actual_name,
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
        Get lightweight list of all recipes from the database.

        Returns:
            List[Dict[str, Any]]: List of recipes with name, short_id, and rating only
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT short_id, name, rating 
                    FROM Recipes 
                    ORDER BY name
                    """
                )

                recipes = []
                for short_id, name, rating in cursor.fetchall():
                    recipes.append(
                        {"short_id": short_id, "name": name, "rating": rating}
                    )

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
                available_quantity = self.get_total_item_quantity(
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
        if parse_short_id(short_id) is None:
            return None

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Get recipe details
                cursor.execute(
                    "SELECT id, short_id, name, instructions, time_minutes, rating, created_date, last_modified FROM Recipes WHERE short_id = ?",
                    (short_id,),
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
        if parse_short_id(short_id) is None:
            return (
                False,
                f"Invalid short ID format: '{short_id}'. Expected format: R1F",
            )

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if recipe exists
                cursor.execute(
                    "SELECT id, name FROM Recipes WHERE short_id = ?", (short_id,)
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
                    SELECT adults, children, notes, updated_date, volume_unit, weight_unit, count_unit
                    FROM HouseholdCharacteristics
                    WHERE id = 1
                    """,
                )
                result = cursor.fetchone()
                if result:
                    adults, children, notes, updated_date, volume, weight, count = (
                        result
                    )
                    return {
                        "adults": adults,
                        "children": children,
                        "notes": notes or "",
                        "updated_date": updated_date,
                        "preferred_units": {
                            "volume": volume or "Milliliter",
                            "weight": weight or "Gram",
                            "count": count or "Piece",
                        },
                    }
                else:
                    # Return default values if no record exists
                    return {
                        "adults": 2,
                        "children": 0,
                        "notes": "",
                        "updated_date": datetime.now().isoformat(),
                        "preferred_units": {
                            "volume": "Milliliter",
                            "weight": "Gram",
                            "count": "Piece",
                        },
                    }
        except Exception as e:
            print(f"Error getting household characteristics: {e}")
            return {
                "adults": 2,
                "children": 0,
                "notes": "",
                "updated_date": datetime.now().isoformat(),
                "preferred_units": {
                    "volume": "Milliliter",
                    "weight": "Gram",
                    "count": "Piece",
                },
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
                    UPDATE HouseholdCharacteristics
                    SET adults = ?, children = ?, notes = ?, updated_date = datetime('now')
                    WHERE id = 1
                    """,
                    (adults, children, notes),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO HouseholdCharacteristics
                        (id, adults, children, notes, updated_date, volume_unit, weight_unit, count_unit)
                        VALUES (1, ?, ?, ?, datetime('now'), 'Milliliter', 'Gram', 'Piece')
                        """,
                        (adults, children, notes),
                    )
                return True
        except Exception as e:
            print(f"Error setting household characteristics: {e}")
            return False

    def get_preferred_units(self) -> Dict[str, str]:
        """Get preferred units for the household."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT volume_unit, weight_unit, count_unit
                    FROM HouseholdCharacteristics
                    WHERE id = 1
                    """,
                )
                result = cursor.fetchone()
                if result:
                    volume, weight, count = result
                    return {
                        "volume": volume or "Milliliter",
                        "weight": weight or "Gram",
                        "count": count or "Piece",
                    }
        except Exception as e:
            print(f"Error getting preferred units: {e}")
        return {"volume": "Milliliter", "weight": "Gram", "count": "Piece"}

    def set_preferred_units(
        self, volume_unit: str, weight_unit: str, count_unit: str
    ) -> bool:
        """Set preferred units for the household."""
        validate_required_params(
            volume_unit=volume_unit, weight_unit=weight_unit, count_unit=count_unit
        )
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE HouseholdCharacteristics
                    SET volume_unit = ?, weight_unit = ?, count_unit = ?, updated_date = datetime('now')
                    WHERE id = 1
                    """,
                    (volume_unit, weight_unit, count_unit),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO HouseholdCharacteristics
                        (id, adults, children, notes, updated_date, volume_unit, weight_unit, count_unit)
                        VALUES (1, 2, 0, '', datetime('now'), ?, ?, ?)
                        """,
                        (volume_unit, weight_unit, count_unit),
                    )
                return True
        except Exception as e:
            print(f"Error setting preferred units: {e}")
            return False

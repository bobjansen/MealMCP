import sqlite3


def setup_database(
    db_path="pantry.db",
):  # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Ingredients table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            default_unit TEXT NOT NULL
        )
    """
    )

    # Create PantryTransactions table with foreign key to Ingredients
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PantryTransactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,  -- 'addition' or 'removal'
            ingredient_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (ingredient_id) REFERENCES Ingredients(id)
        )
    """
    )

    # Create Recipes table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            instructions TEXT NOT NULL,
            time_minutes INTEGER NOT NULL,
            rating INTEGER DEFAULT NULL CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
            created_date TEXT NOT NULL,
            last_modified TEXT NOT NULL
        )
    """
    )

    # Create Preferences table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,  -- e.g., 'dietary', 'allergy', 'dislike', 'like'
            item TEXT NOT NULL,      -- e.g., 'vegetarian', 'peanuts', 'mushrooms'
            level TEXT NOT NULL,     -- e.g., 'required', 'preferred', 'avoid'
            notes TEXT,
            created_date TEXT NOT NULL,
            UNIQUE(category, item)
        )
    """
    )

    # Create RecipeIngredients junction table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS RecipeIngredients (
            recipe_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            PRIMARY KEY (recipe_id, ingredient_id),
            FOREIGN KEY (recipe_id) REFERENCES Recipes(id),
            FOREIGN KEY (ingredient_id) REFERENCES Ingredients(id)
        )
    """
    )

    # Create MealPlan table for linking dates to recipes
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS MealPlan (
            meal_date TEXT PRIMARY KEY,
            recipe_id INTEGER NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES Recipes(id)
        )
        """
    )

    # Commit changes and close the connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Setting up the database")
    setup_database()

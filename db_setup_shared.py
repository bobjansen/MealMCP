"""
Database setup for single-database multi-user approach.
All users share one database with user_id scoping.
"""

import sqlite3
import psycopg2
from typing import Union


def setup_shared_database(connection: Union[str, object]) -> bool:
    """
    Set up database schema for single-database multi-user mode.

    Args:
        connection: Either a connection string (for PostgreSQL) or connection object

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if isinstance(connection, str):
            if connection.startswith(("postgresql://", "postgres://")):
                return _setup_postgresql_shared(connection)
            else:
                return _setup_sqlite_shared(connection)
        else:
            # Assume it's a connection object
            return _setup_with_connection(connection)
    except Exception as e:
        print(f"Error setting up shared database: {e}")
        return False


def _setup_postgresql_shared(connection_string: str) -> bool:
    """Set up PostgreSQL schema for shared database."""
    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Users table (already exists from web_auth.py)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    preferred_language VARCHAR(10) DEFAULT 'en'
                )
            """
            )

            # Ingredients table (shared, but could be user-specific)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingredients (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    default_unit VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """
            )

            # Preferences table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    category VARCHAR(50) NOT NULL,
                    item VARCHAR(255) NOT NULL,
                    level VARCHAR(50) NOT NULL,
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, category, item)
                )
            """
            )

            # Pantry transactions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pantry_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('addition', 'removal')),
                    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                    quantity DECIMAL(10,3) NOT NULL,
                    unit VARCHAR(50) NOT NULL,
                    transaction_date TIMESTAMP NOT NULL,
                    notes TEXT
                )
            """
            )

            # Recipes table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    instructions TEXT NOT NULL,
                    time_minutes INTEGER NOT NULL,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """
            )

            # Recipe ingredients table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipe_ingredients (
                    id SERIAL PRIMARY KEY,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                    quantity DECIMAL(10,3) NOT NULL,
                    unit VARCHAR(50) NOT NULL
                )
            """
            )

            # Meal plan table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meal_plan (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    meal_date DATE NOT NULL,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    UNIQUE(user_id, meal_date)
                )
            """
            )

            # Create indexes for better performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingredients_user_id ON ingredients(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_user_id ON pantry_transactions(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_id ON meal_plan(user_id)"
            )

            # Performance optimization indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_ingredient_unit ON pantry_transactions(user_id, ingredient_id, unit)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_date ON meal_plan(user_id, meal_date)"
            )

    return True


def _setup_sqlite_shared(db_path: str) -> bool:
    """Set up SQLite schema for shared database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                preferred_language TEXT DEFAULT 'en'
            )
        """
        )

        # Ingredients table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                default_unit TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """
        )

        # Preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                level TEXT NOT NULL,
                notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category, item)
            )
        """
        )

        # Pantry transactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pantry_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('addition', 'removal')),
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                transaction_date TIMESTAMP NOT NULL,
                notes TEXT
            )
        """
        )

        # Recipes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                instructions TEXT NOT NULL,
                time_minutes INTEGER NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """
        )

        # Recipe ingredients table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL
            )
        """
        )

        # Meal plan table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_plan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                meal_date DATE NOT NULL,
                recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                UNIQUE(user_id, meal_date)
            )
        """
        )

        # Create indexes for better performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingredients_user_id ON ingredients(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_user_id ON pantry_transactions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_id ON meal_plan(user_id)"
        )

        # Performance optimization indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_ingredient_unit ON pantry_transactions(user_id, ingredient_id, unit)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_date ON meal_plan(user_id, meal_date)"
        )

    return True


def _setup_with_connection(conn) -> bool:
    """Set up database with an existing connection object."""
    try:
        # Detect database type and call appropriate setup
        cursor = conn.cursor()
        cursor.execute("SELECT 1")  # Test query

        # This is a simplified approach - in practice you'd check the connection type
        if hasattr(conn, "autocommit"):  # PostgreSQL psycopg2 connection
            return _setup_postgresql_with_conn(conn)
        else:  # SQLite connection
            return _setup_sqlite_with_conn(conn)
    except Exception as e:
        print(f"Error setting up database with connection: {e}")
        return False


def _setup_postgresql_with_conn(conn) -> bool:
    """Set up PostgreSQL with existing connection."""
    # Implementation similar to _setup_postgresql_shared but using existing connection
    pass


def _setup_sqlite_with_conn(conn) -> bool:
    """Set up SQLite with existing connection."""
    # Implementation similar to _setup_sqlite_shared but using existing connection
    pass


if __name__ == "__main__":
    # Test setup
    print("Setting up shared database schema...")
    success = setup_shared_database("test_shared.db")
    print(f"Setup {'successful' if success else 'failed'}")

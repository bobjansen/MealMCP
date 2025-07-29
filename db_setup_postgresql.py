import psycopg2
from typing import Optional


def setup_postgresql_database(connection_string: str, drop_existing: bool = False):
    """
    Set up PostgreSQL database schema for MealMCP.

    Args:
        connection_string: PostgreSQL connection string
        drop_existing: Whether to drop existing tables first
    """
    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:

            if drop_existing:
                # Drop tables in reverse dependency order
                cursor.execute("DROP TABLE IF EXISTS meal_plan CASCADE")
                cursor.execute("DROP TABLE IF EXISTS recipe_ingredients CASCADE")
                cursor.execute("DROP TABLE IF EXISTS pantry_transactions CASCADE")
                cursor.execute("DROP TABLE IF EXISTS recipes CASCADE")
                cursor.execute("DROP TABLE IF EXISTS preferences CASCADE")
                cursor.execute("DROP TABLE IF EXISTS ingredients CASCADE")

            # Create Ingredients table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ingredients (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    default_unit VARCHAR(50) NOT NULL
                )
            """
            )

            # Create Preferences table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    id SERIAL PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    item VARCHAR(255) NOT NULL,
                    level VARCHAR(50) NOT NULL,
                    notes TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, item)
                )
            """
            )

            # Create PantryTransactions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pantry_transactions (
                    id SERIAL PRIMARY KEY,
                    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('addition', 'removal')),
                    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
                    quantity DECIMAL(10,3) NOT NULL,
                    unit VARCHAR(50) NOT NULL,
                    transaction_date TIMESTAMP NOT NULL,
                    notes TEXT
                )
            """
            )

            # Create Recipes table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    instructions TEXT NOT NULL,
                    time_minutes INTEGER NOT NULL,
                    rating INTEGER DEFAULT NULL CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
                    created_date TIMESTAMP NOT NULL,
                    last_modified TIMESTAMP NOT NULL
                )
            """
            )

            # Create RecipeIngredients table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recipe_ingredients (
                    id SERIAL PRIMARY KEY,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
                    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
                    quantity DECIMAL(10,3) NOT NULL,
                    unit VARCHAR(50) NOT NULL
                )
            """
            )

            # Create MealPlan table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meal_plan (
                    meal_date DATE PRIMARY KEY,
                    recipe_id INTEGER NOT NULL REFERENCES recipes(id)
                )
            """
            )

            # Create indexes for better performance
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pantry_transactions_ingredient_unit 
                ON pantry_transactions(ingredient_id, unit)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pantry_transactions_date 
                ON pantry_transactions(transaction_date)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe 
                ON recipe_ingredients(recipe_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_meal_plan_date 
                ON meal_plan(meal_date)
            """
            )

            print("PostgreSQL database schema created successfully!")


def create_postgresql_database(
    host: str = "localhost",
    port: int = 5432,
    user: str = "postgres",
    password: str = None,
    database: str = "mealmcp",
) -> str:
    """
    Create a PostgreSQL database if it doesn't exist.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL user
        password: PostgreSQL password
        database: Database name to create

    Returns:
        str: Connection string for the created database
    """
    # Connect to postgres database to create our database
    admin_conn_str = f"postgresql://{user}"
    if password:
        admin_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    else:
        admin_conn_str = f"postgresql://{user}@{host}:{port}/postgres"

    try:
        with psycopg2.connect(admin_conn_str) as conn:
            conn.autocommit = True
            with conn.cursor() as cursor:
                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
                )

                if not cursor.fetchone():
                    cursor.execute(f'CREATE DATABASE "{database}"')
                    print(f"Created database: {database}")
                else:
                    print(f"Database {database} already exists")

    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        raise

    # Return connection string for the new database
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql://{user}@{host}:{port}/{database}"


if __name__ == "__main__":
    import os

    # Example usage
    connection_string = os.getenv(
        "PANTRY_DATABASE_URL", "postgresql://localhost/mealmcp"
    )

    print(f"Setting up PostgreSQL database: {connection_string}")
    setup_postgresql_database(connection_string)
    print("Setup complete!")

"""
Centralized database schema definitions for both single-user and multi-user modes.
This module provides common schema definitions to avoid duplication.
"""

# Table schemas as dictionaries to enable reuse
SINGLE_USER_SCHEMAS = {
    "units": """
        CREATE TABLE IF NOT EXISTS Units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            base_unit TEXT NOT NULL,
            size REAL NOT NULL
        )
    """,
    "ingredients": """
        CREATE TABLE IF NOT EXISTS Ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            default_unit TEXT NOT NULL
        )
    """,
    "pantry_transactions": """
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
    """,
    "recipes": """
        CREATE TABLE IF NOT EXISTS Recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id TEXT GENERATED ALWAYS AS (
                'R' || hex(id) || substr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', (id % 36) + 1, 1)
            ) STORED UNIQUE,
            name TEXT NOT NULL,
            instructions TEXT NOT NULL,
            time_minutes INTEGER NOT NULL,
            rating INTEGER DEFAULT NULL CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
            created_date TEXT NOT NULL,
            last_modified TEXT NOT NULL
        )
    """,
    "preferences": """
        CREATE TABLE IF NOT EXISTS Preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,  -- e.g., 'dietary', 'allergy', 'dislike', 'like'
            item TEXT NOT NULL,      -- e.g., 'vegetarian', 'peanuts', 'mushrooms'
            level TEXT NOT NULL,     -- e.g., 'required', 'preferred', 'avoid'
            notes TEXT,
            created_date TEXT NOT NULL,
            UNIQUE(category, item)
        )
    """,
    "recipe_ingredients": """
        CREATE TABLE IF NOT EXISTS RecipeIngredients (
            recipe_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            PRIMARY KEY (recipe_id, ingredient_id),
            FOREIGN KEY (recipe_id) REFERENCES Recipes(id),
            FOREIGN KEY (ingredient_id) REFERENCES Ingredients(id)
        )
    """,
    "meal_plan": """
        CREATE TABLE IF NOT EXISTS MealPlan (
            meal_date TEXT PRIMARY KEY,
            recipe_id INTEGER NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES Recipes(id)
        )
    """,
    "household_characteristics": """
        CREATE TABLE IF NOT EXISTS HouseholdCharacteristics (
            id INTEGER PRIMARY KEY,
            adults INTEGER DEFAULT 2,
            children INTEGER DEFAULT 0,
            notes TEXT,
            updated_date TEXT NOT NULL
        )
    """,
}

MULTI_USER_POSTGRESQL_SCHEMAS = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            preferred_language VARCHAR(10) DEFAULT 'en',
            household_id INTEGER REFERENCES users(id),
            household_adults INTEGER DEFAULT 2,
            household_children INTEGER DEFAULT 0
        )
    """,
    "household_invites": """
        CREATE TABLE IF NOT EXISTS household_invites (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            email VARCHAR(120) NOT NULL,
            secret VARCHAR(128) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "units": """
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            base_unit VARCHAR(20) NOT NULL,
            size REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """,
    "ingredients": """
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            default_unit VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """,
    "preferences": """
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
    """,
    "pantry_transactions": """
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
    """,
    "recipes": """
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            short_id TEXT GENERATED ALWAYS AS (
                'R' || upper(to_hex(id)) || substr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', (id % 36) + 1, 1)
            ) STORED,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            instructions TEXT NOT NULL,
            time_minutes INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, short_id)
        )
    """,
    "recipe_ingredients": """
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity DECIMAL(10,3) NOT NULL,
            unit VARCHAR(50) NOT NULL
        )
    """,
    "meal_plan": """
        CREATE TABLE IF NOT EXISTS meal_plan (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            meal_date DATE NOT NULL,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            UNIQUE(user_id, meal_date)
        )
    """,
}

MULTI_USER_SQLITE_SCHEMAS = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            preferred_language TEXT DEFAULT 'en',
            household_id INTEGER REFERENCES users(id),
            household_adults INTEGER DEFAULT 2,
            household_children INTEGER DEFAULT 0
        )
    """,
    "household_invites": """
        CREATE TABLE IF NOT EXISTS household_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            secret TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "units": """
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            base_unit TEXT NOT NULL,
            size REAL NOT NULL,
            UNIQUE(user_id, name)
        )
    """,
    "ingredients": """
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            default_unit TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name)
        )
    """,
    "preferences": """
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
    """,
    "pantry_transactions": """
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
    """,
    "recipes": """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id TEXT GENERATED ALWAYS AS (
                'R' || hex(id) || substr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', (id % 36) + 1, 1)
            ) STORED,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            instructions TEXT NOT NULL,
            time_minutes INTEGER NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, short_id)
        )
    """,
    "recipe_ingredients": """
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL
        )
    """,
    "meal_plan": """
        CREATE TABLE IF NOT EXISTS meal_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            meal_date DATE NOT NULL,
            recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
            UNIQUE(user_id, meal_date)
        )
    """,
}

# Performance indexes for each schema type
SINGLE_USER_INDEXES = []

MULTI_USER_POSTGRESQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_ingredients_user_id ON ingredients(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_user_id ON pantry_transactions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipes_user_id ON recipes(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_id ON meal_plan(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_pantry_transactions_ingredient_unit ON pantry_transactions(user_id, ingredient_id, unit)",
    "CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id)",
    "CREATE INDEX IF NOT EXISTS idx_meal_plan_user_date ON meal_plan(user_id, meal_date)",
    "CREATE INDEX IF NOT EXISTS idx_household_invites_secret ON household_invites(secret)",
    "CREATE INDEX IF NOT EXISTS idx_household_invites_owner_id ON household_invites(owner_id)",
]

MULTI_USER_SQLITE_INDEXES = (
    MULTI_USER_POSTGRESQL_INDEXES  # Same indexes work for SQLite
)

# Default data to insert
SINGLE_USER_DEFAULTS = [
    """
    INSERT OR IGNORE INTO HouseholdCharacteristics (id, adults, children, updated_date)
    VALUES (1, 2, 0, datetime('now'))
    """
]

MULTI_USER_DEFAULTS = []  # No defaults for multi-user mode

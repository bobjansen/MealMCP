#!/usr/bin/env python3
"""
Migration script to add short_id field to existing recipes and generate short IDs.
This should be run on databases that were created before short ID support was added.

Usage:
    python migrate_add_short_ids.py [database_path]
    python migrate_add_short_ids.py --postgresql [connection_string]
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from short_id_utils import generate_short_id

try:
    import psycopg2

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


def migrate_sqlite_short_ids(db_path: str) -> bool:
    """Add short_id field to SQLite database and generate short IDs for existing recipes."""
    print(f"Migrating SQLite database: {db_path}")

    if not Path(db_path).exists():
        print(f"ERROR: Database file {db_path} does not exist")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if short_id column already exists
        cursor.execute("PRAGMA table_info(Recipes)")
        columns = [row[1] for row in cursor.fetchall()]

        if "short_id" in columns:
            print("✓ short_id column already exists in Recipes table")
        else:
            print("Adding short_id column to Recipes table...")
            cursor.execute("ALTER TABLE Recipes ADD COLUMN short_id TEXT UNIQUE")

        # Get all recipes that don't have short IDs yet
        cursor.execute("SELECT id, name FROM Recipes WHERE short_id IS NULL")
        recipes_without_short_ids = cursor.fetchall()

        if recipes_without_short_ids:
            print(
                f"Generating short IDs for {len(recipes_without_short_ids)} existing recipes..."
            )
            for recipe_id, recipe_name in recipes_without_short_ids:
                short_id = generate_short_id(recipe_id)
                cursor.execute(
                    "UPDATE Recipes SET short_id = ? WHERE id = ?",
                    (short_id, recipe_id),
                )
                print(f"  Recipe '{recipe_name}' -> {short_id}")
        else:
            print("✓ All recipes already have short IDs")

        conn.commit()
        conn.close()

        print("✓ SQLite short ID migration completed successfully!")
        return True

    except Exception as e:
        print(f"ERROR migrating SQLite database: {e}")
        import traceback

        traceback.print_exc()
        return False


def migrate_postgresql_short_ids(connection_string: str) -> bool:
    """Add short_id field to PostgreSQL database and generate short IDs for existing recipes."""
    if not PSYCOPG2_AVAILABLE:
        print("ERROR: psycopg2 not available for PostgreSQL migration")
        return False

    print("Migrating PostgreSQL database...")

    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()

        # Check if short_id column already exists
        cursor.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'recipes' AND column_name = 'short_id'
        """
        )

        if cursor.fetchone():
            print("✓ short_id column already exists in recipes table")
        else:
            print("Adding short_id column to recipes table...")
            cursor.execute("ALTER TABLE recipes ADD COLUMN short_id VARCHAR(10) UNIQUE")

        # Get all recipes that don't have short IDs yet
        cursor.execute("SELECT id, name FROM recipes WHERE short_id IS NULL")
        recipes_without_short_ids = cursor.fetchall()

        if recipes_without_short_ids:
            print(
                f"Generating short IDs for {len(recipes_without_short_ids)} existing recipes..."
            )
            for recipe_id, recipe_name in recipes_without_short_ids:
                short_id = generate_short_id(recipe_id)
                cursor.execute(
                    "UPDATE recipes SET short_id = %s WHERE id = %s",
                    (short_id, recipe_id),
                )
                print(f"  Recipe '{recipe_name}' -> {short_id}")
        else:
            print("✓ All recipes already have short IDs")

        conn.commit()
        conn.close()

        print("✓ PostgreSQL short ID migration completed successfully!")
        return True

    except Exception as e:
        print(f"ERROR migrating PostgreSQL database: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(
        description="Add short_id support to existing recipe database"
    )
    parser.add_argument(
        "--postgresql", action="store_true", help="Migrate PostgreSQL database"
    )
    parser.add_argument(
        "connection",
        nargs="?",
        default="pantry.db",
        help="Database path for SQLite or connection string for PostgreSQL",
    )

    args = parser.parse_args()

    print("Recipe Database Short ID Migration Script")
    print("========================================")
    print()
    print("This script adds short_id field to existing recipes and generates")
    print("human-friendly short IDs like R123A for recipe identification.")
    print(
        "NOTE: This system no longer uses UUIDs - short IDs are the primary ID system."
    )
    print()

    if args.postgresql:
        if not PSYCOPG2_AVAILABLE:
            print("ERROR: psycopg2 package is required for PostgreSQL migration")
            print("Install it with: pip install psycopg2-binary")
            return False
        return migrate_postgresql_short_ids(args.connection)
    else:
        return migrate_sqlite_short_ids(args.connection)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

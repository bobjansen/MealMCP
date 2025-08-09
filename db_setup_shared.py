"""
Database setup for single-database multi-user approach.
All users share one database with user_id scoping.
"""

import sqlite3
import psycopg2
from typing import Union
from db_schema_definitions import (
    MULTI_USER_POSTGRESQL_SCHEMAS,
    MULTI_USER_SQLITE_SCHEMAS, 
    MULTI_USER_POSTGRESQL_INDEXES,
    MULTI_USER_SQLITE_INDEXES,
    MULTI_USER_DEFAULTS
)


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
            # Connection object support not implemented - use connection string
            raise ValueError("Connection objects not supported. Use connection string instead.")
    except Exception as e:
        print(f"Error setting up shared database: {e}")
        return False


def _setup_postgresql_shared(connection_string: str) -> bool:
    """Set up PostgreSQL schema for shared database using centralized schema definitions."""
    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Create all tables using centralized schema definitions
            for table_name, schema in MULTI_USER_POSTGRESQL_SCHEMAS.items():
                cursor.execute(schema)

            # Add household columns to existing users table if they don't exist
            try:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN household_adults INTEGER DEFAULT 2"
                )
            except psycopg2.errors.DuplicateColumn:
                pass
            except Exception:
                pass

            try:
                cursor.execute(
                    "ALTER TABLE users ADD COLUMN household_children INTEGER DEFAULT 0"
                )
            except psycopg2.errors.DuplicateColumn:
                pass
            except Exception:
                pass

            # Create indexes for better performance
            for index_sql in MULTI_USER_POSTGRESQL_INDEXES:
                cursor.execute(index_sql)

            # Insert default data
            for default_sql in MULTI_USER_DEFAULTS:
                cursor.execute(default_sql)

    return True


def _setup_sqlite_shared(db_path: str) -> bool:
    """Set up SQLite schema for shared database using centralized schema definitions."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Create all tables using centralized schema definitions
        for table_name, schema in MULTI_USER_SQLITE_SCHEMAS.items():
            cursor.execute(schema)

        # Add household columns to existing users table if they don't exist
        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN household_adults INTEGER DEFAULT 2"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN household_children INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes for better performance
        for index_sql in MULTI_USER_SQLITE_INDEXES:
            cursor.execute(index_sql)

        # Insert default data
        for default_sql in MULTI_USER_DEFAULTS:
            cursor.execute(default_sql)

    return True




if __name__ == "__main__":
    # Test setup
    print("Setting up shared database schema...")
    success = setup_shared_database("test_shared.db")
    print(f"Setup {'successful' if success else 'failed'}")

"""
Database setup for single-database multi-user approach.
All users share one database with user_id scoping.
"""

import os
import sqlite3
import psycopg2
from typing import Iterable, Union, Type
from db_schema_definitions import (
    MULTI_USER_POSTGRESQL_SCHEMAS,
    MULTI_USER_SQLITE_SCHEMAS,
    MULTI_USER_POSTGRESQL_INDEXES,
    MULTI_USER_SQLITE_INDEXES,
    MULTI_USER_DEFAULTS,
)
from error_utils import safe_execute


def _add_column_if_not_exists(
    cursor, table: str, column: str, column_def: str, dialect: str
) -> None:
    """Add a column to a table if it doesn't already exist."""
    if dialect == "postgres":
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        exists = cursor.fetchone() is not None
    elif dialect == "sqlite":
        cursor.execute(f"PRAGMA table_info({table})")
        exists = any(row[1] == column for row in cursor.fetchall())
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")

    if not exists:
        _execute_with_reporting(
            cursor, f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"
        )


def _execute_with_reporting(
    cursor, sql: str, ignore_exceptions: Iterable[Type[BaseException]] = ()
) -> None:
    """Execute a SQL statement and report failures with the offending query."""
    try:
        cursor.execute(sql)
    except tuple(ignore_exceptions):
        pass
    except Exception as e:
        print(f"Error executing query: {e}\nQuery:\n{sql}")
        raise


def setup_shared_database(connection: Union[str, object, None] = None) -> bool:
    """Set up database schema for single-database multi-user mode.

    Args:
        connection: Optional connection string. If not provided, the
            PANTRY_DATABASE_URL environment variable will be used. For PostgreSQL
            the value must start with ``postgresql://`` or ``postgres://``. Any
            other string is treated as a SQLite path.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if connection is None:
            connection = os.getenv("PANTRY_DATABASE_URL")
            if not connection:
                raise ValueError("PANTRY_DATABASE_URL environment variable not set")

        if isinstance(connection, str):
            if connection.startswith(("postgresql://", "postgres://")):
                return _setup_postgresql_shared(connection)
            else:
                return _setup_sqlite_shared(connection)
        else:
            # Connection object support not implemented - use connection string
            raise ValueError(
                "Connection objects not supported. Use connection string instead."
            )
    except Exception as e:
        print(f"Error setting up shared database: {e}")
        return False


@safe_execute("setup PostgreSQL shared database", default_return=False, log_errors=True)
def _setup_postgresql_shared(connection_string: str) -> bool:
    """Set up PostgreSQL schema for shared database using centralized schema definitions."""
    with psycopg2.connect(connection_string) as conn:
        with conn.cursor() as cursor:
            # Create all tables using centralized schema definitions
            for _, schema in MULTI_USER_POSTGRESQL_SCHEMAS.items():
                _execute_with_reporting(cursor, schema)

            # Add additional columns to existing users table if they don't exist
            columns_to_add = [
                ("household_id", "INTEGER REFERENCES users(id)"),
                ("household_adults", "INTEGER DEFAULT 2"),
                ("household_children", "INTEGER DEFAULT 0"),
                ("preferred_volume_unit", "VARCHAR(50) DEFAULT 'Milliliter'"),
                ("preferred_weight_unit", "VARCHAR(50) DEFAULT 'Gram'"),
                ("preferred_count_unit", "VARCHAR(50) DEFAULT 'Piece'"),
            ]
            for column, definition in columns_to_add:
                _add_column_if_not_exists(
                    cursor, "users", column, definition, dialect="postgres"
                )

            # Create indexes for better performance
            for index_sql in MULTI_USER_POSTGRESQL_INDEXES:
                _execute_with_reporting(cursor, index_sql)

            # Insert default data
            for default_sql in MULTI_USER_DEFAULTS:
                _execute_with_reporting(cursor, default_sql)

    return True


@safe_execute("setup SQLite shared database", default_return=False, log_errors=True)
def _setup_sqlite_shared(db_path: str) -> bool:
    """Set up SQLite schema for shared database using centralized schema definitions."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Create all tables using centralized schema definitions
        for _, schema in MULTI_USER_SQLITE_SCHEMAS.items():
            _execute_with_reporting(cursor, schema)

        # Add additional columns to existing users table if they don't exist
        columns_to_add = [
            ("household_id", "INTEGER REFERENCES users(id)"),
            ("household_adults", "INTEGER DEFAULT 2"),
            ("household_children", "INTEGER DEFAULT 0"),
            ("preferred_volume_unit", "TEXT DEFAULT 'Milliliter'"),
            ("preferred_weight_unit", "TEXT DEFAULT 'Gram'"),
            ("preferred_count_unit", "TEXT DEFAULT 'Piece'"),
        ]
        for column, definition in columns_to_add:
            _add_column_if_not_exists(
                cursor, "users", column, definition, dialect="sqlite"
            )

        # Create indexes for better performance
        for index_sql in MULTI_USER_SQLITE_INDEXES:
            _execute_with_reporting(cursor, index_sql)

        # Insert default data
        for default_sql in MULTI_USER_DEFAULTS:
            _execute_with_reporting(cursor, default_sql)

    return True


if __name__ == "__main__":
    # Test setup using environment variable
    print("Setting up shared database schema...")
    success = setup_shared_database()
    print(f"Setup {'successful' if success else 'failed'}")

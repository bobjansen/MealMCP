"""
Unified database setup that works with both SQLite and PostgreSQL.
"""

import os
from typing import Optional


def setup_database(backend: str = None, connection_string: str = None, **kwargs):
    """
    Set up database schema for the specified backend.

    Args:
        backend: Database backend ('sqlite', 'postgresql').
                If None, auto-detected from connection_string or environment
        connection_string: Database connection string
        **kwargs: Additional options (e.g., drop_existing=True)
    """
    # Auto-detect backend
    if backend is None:
        backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

    if connection_string and backend == "sqlite":
        if connection_string.startswith(("postgresql://", "postgres://")):
            backend = "postgresql"

    # Set default connection string
    if connection_string is None:
        if backend == "sqlite":
            connection_string = os.getenv("PANTRY_DB_PATH", "pantry.db")
        elif backend in ("postgresql", "postgres"):
            connection_string = os.getenv(
                "PANTRY_DATABASE_URL", "postgresql://localhost/mealmcp"
            )

    if backend == "sqlite":
        from db_setup import setup_database as setup_sqlite

        setup_sqlite(connection_string)
        print(f"SQLite database setup complete: {connection_string}")

    elif backend in ("postgresql", "postgres"):
        try:
            from db_setup_postgresql import setup_postgresql_database

            setup_postgresql_database(connection_string, **kwargs)
            print(f"PostgreSQL database setup complete: {connection_string}")
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
            )
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def create_database_if_needed(backend: str = None, connection_string: str = None):
    """
    Create database if it doesn't exist (PostgreSQL only - SQLite creates automatically).

    Args:
        backend: Database backend
        connection_string: Database connection string
    """
    if backend is None:
        backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

    if backend in ("postgresql", "postgres"):
        try:
            from db_setup_postgresql import create_postgresql_database
            from urllib.parse import urlparse

            if connection_string:
                parsed = urlparse(connection_string)
                return create_postgresql_database(
                    host=parsed.hostname or "localhost",
                    port=parsed.port or 5432,
                    user=parsed.username or "postgres",
                    password=parsed.password,
                    database=parsed.path.lstrip("/") if parsed.path else "mealmcp",
                )
            else:
                return create_postgresql_database()

        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
            )

    # SQLite doesn't need explicit database creation
    return connection_string


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        backend = sys.argv[1]
        connection_string = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        backend = None
        connection_string = None

    # Create database if needed (PostgreSQL)
    connection_string = create_database_if_needed(backend, connection_string)

    # Setup schema
    setup_database(backend, connection_string)

    print("Database setup complete!")

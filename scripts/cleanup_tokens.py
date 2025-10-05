#!/usr/bin/env python3
"""
OAuth Token Cleanup Utility
Removes expired tokens from the database to prevent bloat.
"""

import os
import time
import sqlite3
import psycopg2
from pathlib import Path


def cleanup_sqlite_tokens():
    """Clean up expired tokens from SQLite database."""
    db_path = Path("oauth.db")
    if not db_path.exists():
        print("No SQLite OAuth database found")
        return 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM oauth_tokens WHERE expires_at > 0 AND expires_at < ?",
            (int(time.time()),),
        )
        deleted = cursor.rowcount
        conn.commit()

    return deleted


def cleanup_postgresql_tokens():
    """Clean up expired tokens from PostgreSQL database."""
    postgres_url = os.getenv("PANTRY_DATABASE_URL")
    if not postgres_url:
        print("No PostgreSQL connection URL found")
        return 0

    try:
        with psycopg2.connect(postgres_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM oauth_tokens WHERE expires_at > 0 AND expires_at < %s",
                    (int(time.time()),),
                )
                deleted = cursor.rowcount
                conn.commit()
        return deleted
    except Exception as e:
        print(f"PostgreSQL cleanup failed: {e}")
        return 0


def main():
    """Clean up expired tokens from both databases."""
    print("Cleaning up expired OAuth tokens...")

    sqlite_deleted = cleanup_sqlite_tokens()
    postgresql_deleted = cleanup_postgresql_tokens()

    total_deleted = sqlite_deleted + postgresql_deleted

    print(f"Cleaned up {sqlite_deleted} expired tokens from SQLite")
    print(f"Cleaned up {postgresql_deleted} expired tokens from PostgreSQL")
    print(f"Total: {total_deleted} expired tokens removed")


if __name__ == "__main__":
    main()

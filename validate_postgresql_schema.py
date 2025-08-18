#!/usr/bin/env python3
"""
PostgreSQL Schema Validation Script

This script validates that the PostgreSQL schema created by the application
matches exactly what the application code expects. It creates a temporary
database, applies the schema, and then validates that all expected tables,
columns, constraints, and indexes are present and correct.

Usage:
    python validate_postgresql_schema.py [--connection-string <url>] [--create-test-db]

Environment Variables:
    POSTGRES_TEST_URL: PostgreSQL connection URL for testing
    PANTRY_DATABASE_URL: Fallback connection URL

If --create-test-db is specified, it will create a temporary test database
and clean it up afterwards.
"""

import os
import sys
import argparse
import psycopg2
from typing import Dict, List, Set, Tuple, Any, Optional
import tempfile
import subprocess
from urllib.parse import urlparse, urlunparse
import uuid

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_setup_shared import setup_shared_database
from db_schema_definitions import (
    MULTI_USER_POSTGRESQL_SCHEMAS,
    MULTI_USER_POSTGRESQL_INDEXES,
)
from web_auth_simple import WebUserManager
from pantry_manager_shared import SharedPantryManager


class PostgreSQLSchemaValidator:
    """Validates PostgreSQL schema against application expectations."""

    def __init__(self, connection_string: str):
        """Initialize the validator with a connection string."""
        self.connection_string = connection_string
        self.expected_tables = set(MULTI_USER_POSTGRESQL_SCHEMAS.keys())
        self.validation_errors = []
        self.validation_warnings = []

    def validate_schema(self) -> bool:
        """
        Validate the complete PostgreSQL schema.

        Returns:
            bool: True if schema is valid, False if there are errors
        """
        print("🔍 Starting PostgreSQL schema validation...")

        try:
            # Step 1: Set up the database schema
            print("📝 Setting up database schema...")
            success = setup_shared_database(self.connection_string)
            if not success:
                self.validation_errors.append("Failed to set up database schema")
                return False

            # Step 2: Connect and validate
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    # Validate tables exist
                    self._validate_tables_exist(cursor)

                    # Validate each table's schema
                    for table_name in self.expected_tables:
                        self._validate_table_schema(cursor, table_name)

                    # Validate indexes
                    self._validate_indexes(cursor)

                    # Validate foreign key constraints
                    self._validate_foreign_keys(cursor)

                    # Validate application functionality
                    self._validate_application_functionality(conn)

            # Report results
            self._report_results()

            return len(self.validation_errors) == 0

        except Exception as e:
            self.validation_errors.append(f"Validation failed with exception: {e}")
            self._report_results()
            return False

    def _validate_tables_exist(self, cursor) -> None:
        """Validate that all expected tables exist."""
        print("  ✓ Checking table existence...")

        cursor.execute(
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
        )

        existing_tables = {row[0] for row in cursor.fetchall()}
        missing_tables = self.expected_tables - existing_tables
        extra_tables = existing_tables - self.expected_tables

        for table in missing_tables:
            self.validation_errors.append(f"Missing expected table: {table}")

        for table in extra_tables:
            self.validation_warnings.append(f"Unexpected table found: {table}")

    def _validate_table_schema(self, cursor, table_name: str) -> None:
        """Validate the schema of a specific table."""
        print(f"  ✓ Validating table schema: {table_name}")

        # Get column information
        cursor.execute(
            """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position
        """,
            (table_name,),
        )

        columns = cursor.fetchall()

        if not columns:
            self.validation_errors.append(
                f"Table {table_name} has no columns or doesn't exist"
            )
            return

        # Validate expected columns based on schema definition
        expected_columns = self._extract_expected_columns(table_name)
        actual_columns = {col[0]: col for col in columns}

        for expected_col in expected_columns:
            if expected_col not in actual_columns:
                self.validation_errors.append(
                    f"Table {table_name} missing column: {expected_col}"
                )

    def _extract_expected_columns(self, table_name: str) -> Set[str]:
        """Extract expected column names from schema definition."""
        schema_sql = MULTI_USER_POSTGRESQL_SCHEMAS.get(table_name, "")

        # More sophisticated parser for column extraction
        lines = schema_sql.split("\n")
        columns = set()
        in_generated_column = False
        paren_depth = 0

        for line in lines:
            line = line.strip()

            # Skip CREATE TABLE line, constraints, and other non-column lines
            if (
                not line
                or line.startswith(
                    ("CREATE", "UNIQUE", "CHECK", "FOREIGN", ")", "PRIMARY")
                )
                or line.upper().startswith("CONSTRAINT")
            ):
                continue

            # Track parentheses to handle generated columns and complex expressions
            paren_depth += line.count("(") - line.count(")")

            # Handle GENERATED ALWAYS AS columns (they span multiple lines)
            if "GENERATED ALWAYS AS" in line.upper():
                in_generated_column = True
                # Extract column name before GENERATED ALWAYS AS
                parts = line.split()
                if parts:
                    col_name = parts[0].replace(",", "").lower()
                    if col_name and not col_name.startswith("'"):
                        columns.add(col_name)
                continue

            # Skip lines inside generated column definition
            if in_generated_column:
                if paren_depth <= 0 and (
                    line.endswith(",") or "STORED" in line.upper()
                ):
                    in_generated_column = False
                continue

            # Extract regular column names
            parts = line.split()
            if (
                parts
                and not parts[0].startswith("'")
                and not parts[0].upper() in ("INDEX", "KEY")
            ):
                col_name = parts[0].replace(",", "").lower()
                if col_name and col_name.isalpha() or "_" in col_name:
                    columns.add(col_name)

        return columns

    def _validate_indexes(self, cursor) -> None:
        """Validate that expected indexes exist."""
        print("  ✓ Checking indexes...")

        cursor.execute(
            """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """
        )

        existing_indexes = {row[2] for row in cursor.fetchall()}

        # Check for expected indexes from schema definitions
        expected_index_names = set()
        for index_sql in MULTI_USER_POSTGRESQL_INDEXES:
            # Extract index name from CREATE INDEX statement
            # Format: CREATE INDEX IF NOT EXISTS idx_name ON table(columns)
            if "CREATE INDEX" in index_sql.upper():
                parts = index_sql.split()
                if "EXISTS" in index_sql.upper():
                    # Format: CREATE INDEX IF NOT EXISTS idx_name
                    idx_pos = parts.index("EXISTS") + 1
                else:
                    # Format: CREATE INDEX idx_name
                    idx_pos = 2

                if idx_pos < len(parts):
                    index_name = parts[idx_pos]
                    expected_index_names.add(index_name)

        missing_indexes = expected_index_names - existing_indexes
        for index_name in missing_indexes:
            self.validation_warnings.append(f"Expected index not found: {index_name}")

    def _validate_foreign_keys(self, cursor) -> None:
        """Validate foreign key constraints."""
        print("  ✓ Checking foreign key constraints...")

        cursor.execute(
            """
            SELECT
                tc.table_name,
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_schema = 'public'
        """
        )

        foreign_keys = cursor.fetchall()

        # Validate key foreign key relationships
        expected_fks = [
            ("ingredients", "user_id", "users", "id"),
            ("preferences", "user_id", "users", "id"),
            ("pantry_transactions", "user_id", "users", "id"),
            ("pantry_transactions", "ingredient_id", "ingredients", "id"),
            ("recipes", "user_id", "users", "id"),
            ("recipe_ingredients", "recipe_id", "recipes", "id"),
            ("recipe_ingredients", "ingredient_id", "ingredients", "id"),
            ("meal_plan", "user_id", "users", "id"),
            ("meal_plan", "recipe_id", "recipes", "id"),
            ("household_invites", "owner_id", "users", "id"),
        ]

        actual_fks = {(fk[0], fk[3], fk[4], fk[5]) for fk in foreign_keys}

        for expected_fk in expected_fks:
            if expected_fk not in actual_fks:
                self.validation_warnings.append(
                    f"Expected foreign key not found: {expected_fk[0]}.{expected_fk[1]} -> {expected_fk[2]}.{expected_fk[3]}"
                )

    def _validate_application_functionality(self, conn) -> None:
        """Test that application classes can work with the schema."""
        print("  ✓ Testing application functionality...")

        try:
            # Test WebUserManager
            auth_manager = WebUserManager("postgresql", self.connection_string)

            # Test basic user operations (without actually creating users)
            test_username = f"test_user_{uuid.uuid4().hex[:8]}"
            exists = auth_manager.user_exists(test_username)
            if exists:
                self.validation_warnings.append(
                    f"Test user {test_username} unexpectedly exists"
                )

            # Test SharedPantryManager
            # Create a test user first
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, household_id) 
                    VALUES (%s, %s, %s, %s) RETURNING id
                """,
                    (test_username, f"{test_username}@test.com", "test_hash", None),
                )

                user_id = cursor.fetchone()[0]

                # Update household_id to self-reference
                cursor.execute(
                    "UPDATE users SET household_id = %s WHERE id = %s",
                    (user_id, user_id),
                )
                conn.commit()

                # Test SharedPantryManager with this user
                pantry_manager = SharedPantryManager(
                    self.connection_string, user_id, backend="postgresql"
                )

                # Test basic operations
                pantry_contents = pantry_manager.get_pantry_contents()
                recipes = pantry_manager.get_all_recipes()
                preferences = pantry_manager.get_preferences()

                # Clean up test user
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()

            print("    ✓ Application classes work correctly with schema")

        except Exception as e:
            self.validation_errors.append(f"Application functionality test failed: {e}")

    def _report_results(self) -> None:
        """Report validation results."""
        print("\n" + "=" * 60)
        print("📋 SCHEMA VALIDATION RESULTS")
        print("=" * 60)

        if self.validation_errors:
            print(f"\n❌ ERRORS ({len(self.validation_errors)}):")
            for error in self.validation_errors:
                print(f"   • {error}")

        if self.validation_warnings:
            print(f"\n⚠️  WARNINGS ({len(self.validation_warnings)}):")
            for warning in self.validation_warnings:
                print(f"   • {warning}")

        if not self.validation_errors and not self.validation_warnings:
            print("\n✅ VALIDATION PASSED")
            print("   Schema is valid and matches application expectations!")
        elif not self.validation_errors:
            print("\n✅ VALIDATION PASSED WITH WARNINGS")
            print("   Schema is functionally correct but has minor issues.")
        else:
            print("\n❌ VALIDATION FAILED")
            print("   Schema has errors that need to be addressed.")

        print("=" * 60)


def create_test_database(base_connection_string: str) -> Tuple[str, str]:
    """
    Create a temporary test database.

    Returns:
        Tuple of (test_db_connection_string, test_db_name)
    """
    # Parse the connection string
    parsed = urlparse(base_connection_string)

    # Generate a unique test database name
    test_db_name = f"test_schema_validation_{uuid.uuid4().hex[:8]}"

    # Create connection string to postgres database (to create the test db)
    admin_parsed = parsed._replace(path="/postgres")
    admin_connection = urlunparse(admin_parsed)

    # Create the test database
    print(f"🏗️  Creating test database: {test_db_name}")
    with psycopg2.connect(admin_connection) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{test_db_name}"')

    # Create connection string to the test database
    test_parsed = parsed._replace(path=f"/{test_db_name}")
    test_connection = urlunparse(test_parsed)

    return test_connection, test_db_name


def cleanup_test_database(base_connection_string: str, test_db_name: str) -> None:
    """Clean up the temporary test database."""
    parsed = urlparse(base_connection_string)
    admin_parsed = parsed._replace(path="/postgres")
    admin_connection = urlunparse(admin_parsed)

    print(f"🧹 Cleaning up test database: {test_db_name}")
    with psycopg2.connect(admin_connection) as conn:
        conn.autocommit = True
        with conn.cursor() as cursor:
            # Terminate existing connections to the test database
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
            """,
                (test_db_name,),
            )

            # Drop the test database
            cursor.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate PostgreSQL schema against application expectations"
    )
    parser.add_argument(
        "--connection-string",
        help="PostgreSQL connection string (default: from POSTGRES_TEST_URL or PANTRY_DATABASE_URL env vars)",
    )
    parser.add_argument(
        "--create-test-db",
        action="store_true",
        help="Create a temporary test database and clean it up afterwards",
    )

    args = parser.parse_args()

    # Get connection string
    connection_string = (
        args.connection_string
        or os.getenv("POSTGRES_TEST_URL")
        or os.getenv("PANTRY_DATABASE_URL")
    )

    if not connection_string:
        print("❌ Error: No PostgreSQL connection string provided.")
        print("   Use --connection-string, POSTGRES_TEST_URL, or PANTRY_DATABASE_URL")
        return 1

    if not connection_string.startswith(("postgresql://", "postgres://")):
        print("❌ Error: Connection string must be a PostgreSQL URL")
        return 1

    test_db_name = None
    test_connection_string = connection_string

    try:
        if args.create_test_db:
            test_connection_string, test_db_name = create_test_database(
                connection_string
            )

        # Run validation
        validator = PostgreSQLSchemaValidator(test_connection_string)
        success = validator.validate_schema()

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        return 1

    finally:
        if test_db_name:
            try:
                cleanup_test_database(connection_string, test_db_name)
            except Exception as e:
                print(
                    f"⚠️  Warning: Failed to clean up test database {test_db_name}: {e}"
                )


if __name__ == "__main__":
    sys.exit(main())

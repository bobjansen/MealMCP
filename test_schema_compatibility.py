#!/usr/bin/env python3
"""
Schema Compatibility Test Script

This script tests schema compatibility by:
1. Creating a temporary SQLite database using the shared schema
2. Creating a temporary PostgreSQL database using the shared schema  
3. Testing that application functionality works with both
4. Comparing the logical schemas between SQLite and PostgreSQL versions

This ensures that the schema definitions in db_schema_definitions.py are correct
and that the multi-user functionality works properly.

Usage:
    python test_schema_compatibility.py [--postgres-url <url>] [--skip-postgres]
"""

import os
import sys
import argparse
import tempfile
import sqlite3
import uuid
from typing import List, Dict, Any

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_setup_shared import setup_shared_database
from web_auth_simple import WebUserManager
from pantry_manager_shared import SharedPantryManager
from pantry_manager_sqlite import SQLitePantryManager
from db_setup import setup_database


class SchemaCompatibilityTester:
    """Tests compatibility between SQLite and PostgreSQL schemas."""

    def __init__(self, postgres_url: str = None):
        """Initialize the tester."""
        self.postgres_url = postgres_url
        self.test_results = []
        self.errors = []

    def run_tests(self) -> bool:
        """Run all compatibility tests."""
        print("🧪 Starting Schema Compatibility Tests...")

        # Test 1: SQLite single-user schema
        sqlite_success = self._test_sqlite_schema()

        # Test 2: SQLite multi-user schema
        sqlite_multi_success = self._test_sqlite_multiuser_schema()

        # Test 3: PostgreSQL multi-user schema (if available)
        postgres_success = True
        if self.postgres_url:
            postgres_success = self._test_postgresql_schema()
        else:
            print("⏭️  Skipping PostgreSQL tests (no connection URL provided)")

        # Test 4: Cross-schema compatibility
        compatibility_success = self._test_cross_schema_compatibility()

        # Report results
        self._report_results()

        return all(
            [
                sqlite_success,
                sqlite_multi_success,
                postgres_success,
                compatibility_success,
            ]
        )

    def _test_sqlite_schema(self) -> bool:
        """Test the single-user SQLite schema."""
        print("\n📝 Testing SQLite Single-User Schema...")

        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
                db_path = tmp_file.name

            # Set up single-user SQLite database
            setup_database(db_path)

            # Test with SQLitePantryManager
            pantry = SQLitePantryManager(db_path)

            # Test basic operations
            self._test_basic_pantry_operations(pantry, "SQLite Single-User")

            # Clean up
            os.unlink(db_path)

            print("  ✅ SQLite single-user schema test passed")
            return True

        except Exception as e:
            self.errors.append(f"SQLite single-user schema test failed: {e}")
            print(f"  ❌ SQLite single-user schema test failed: {e}")
            return False

    def _test_sqlite_multiuser_schema(self) -> bool:
        """Test the multi-user SQLite schema."""
        print("\n📝 Testing SQLite Multi-User Schema...")

        try:
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
                db_path = tmp_file.name

            # Set up multi-user SQLite database
            success = setup_shared_database(db_path)
            if not success:
                raise Exception("Failed to set up shared SQLite database")

            # Test WebUserManager
            auth_manager = WebUserManager("sqlite", db_path)

            # Create a test user
            test_user = f"test_user_{uuid.uuid4().hex[:8]}"
            test_email = f"{test_user}@test.com"

            # Note: SQLite mode returns False for user creation, which is expected behavior
            success, message = auth_manager.create_user(
                test_user, test_email, "test_password"
            )
            if success:  # This should be False for SQLite mode
                self.errors.append("SQLite mode unexpectedly allowed user creation")

            # Test with SharedPantryManager - create user manually for testing
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, household_id) 
                VALUES (?, ?, ?, ?)
            """,
                (test_user, test_email, "test_hash", None),
            )
            user_id = cursor.lastrowid
            cursor.execute(
                "UPDATE users SET household_id = ? WHERE id = ?", (user_id, user_id)
            )
            conn.commit()
            conn.close()

            # Test SharedPantryManager
            pantry = SharedPantryManager(db_path, user_id)
            self._test_basic_pantry_operations(pantry, "SQLite Multi-User")

            # Clean up
            os.unlink(db_path)

            print("  ✅ SQLite multi-user schema test passed")
            return True

        except Exception as e:
            self.errors.append(f"SQLite multi-user schema test failed: {e}")
            print(f"  ❌ SQLite multi-user schema test failed: {e}")
            return False

    def _test_postgresql_schema(self) -> bool:
        """Test the PostgreSQL multi-user schema."""
        print("\n📝 Testing PostgreSQL Multi-User Schema...")

        try:
            # Import here to avoid requiring psycopg2 if PostgreSQL tests are skipped
            import psycopg2
            from urllib.parse import urlparse, urlunparse

            # Create temporary test database
            parsed = urlparse(self.postgres_url)
            test_db_name = f"test_schema_compat_{uuid.uuid4().hex[:8]}"

            # Connect to postgres database to create test database
            admin_parsed = parsed._replace(path="/postgres")
            admin_connection = urlunparse(admin_parsed)

            with psycopg2.connect(admin_connection) as admin_conn:
                admin_conn.autocommit = True
                with admin_conn.cursor() as cursor:
                    cursor.execute(f'CREATE DATABASE "{test_db_name}"')

            # Create connection to test database
            test_parsed = parsed._replace(path=f"/{test_db_name}")
            test_connection = urlunparse(test_parsed)

            try:
                # Set up multi-user PostgreSQL database
                success = setup_shared_database(test_connection)
                if not success:
                    raise Exception("Failed to set up shared PostgreSQL database")

                # Test WebUserManager
                auth_manager = WebUserManager("postgresql", test_connection)

                # Create a test user
                test_user = f"test_user_{uuid.uuid4().hex[:8]}"
                test_email = f"{test_user}@test.com"

                success, message = auth_manager.create_user(
                    test_user, test_email, "test_password123"
                )
                if not success:
                    raise Exception(f"Failed to create test user: {message}")

                # Get user ID
                with psycopg2.connect(test_connection) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM users WHERE username = %s", (test_user,)
                        )
                        user_id = cursor.fetchone()[0]

                # Test SharedPantryManager
                pantry = SharedPantryManager(test_connection, user_id)
                self._test_basic_pantry_operations(pantry, "PostgreSQL Multi-User")

                print("  ✅ PostgreSQL multi-user schema test passed")
                return True

            finally:
                # Clean up test database
                with psycopg2.connect(admin_connection) as admin_conn:
                    admin_conn.autocommit = True
                    with admin_conn.cursor() as cursor:
                        # Terminate connections to test database
                        cursor.execute(
                            """
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = %s AND pid <> pg_backend_pid()
                        """,
                            (test_db_name,),
                        )
                        cursor.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')

        except Exception as e:
            self.errors.append(f"PostgreSQL schema test failed: {e}")
            print(f"  ❌ PostgreSQL schema test failed: {e}")
            return False

    def _test_basic_pantry_operations(self, pantry_manager, schema_type: str) -> None:
        """Test basic pantry operations on a pantry manager."""
        print(f"    🧪 Testing basic operations for {schema_type}...")

        # Test pantry contents (ingredients in pantry)
        pantry_contents = pantry_manager.get_pantry_contents()
        self.test_results.append(
            f"{schema_type}: get_pantry_contents() returned {len(pantry_contents)} items"
        )

        # Test recipe operations
        recipes = pantry_manager.get_all_recipes()
        self.test_results.append(
            f"{schema_type}: get_all_recipes() returned {len(recipes)} items"
        )

        # Test preference operations
        preferences = pantry_manager.get_preferences()
        self.test_results.append(
            f"{schema_type}: get_preferences() returned {len(preferences)} items"
        )

        # Test adding an ingredient
        success = pantry_manager.add_ingredient("Test Ingredient", "gram")
        if success:
            self.test_results.append(
                f"{schema_type}: Successfully added test ingredient"
            )
        else:
            self.errors.append(f"{schema_type}: Failed to add test ingredient")

        # Test adding a preference
        success = pantry_manager.add_preference(
            "dietary", "Test Item", "preferred", "Test notes"
        )
        if success:
            self.test_results.append(
                f"{schema_type}: Successfully added test preference"
            )
        else:
            self.errors.append(f"{schema_type}: Failed to add test preference")

        print(f"    ✅ Basic operations completed for {schema_type}")

    def _test_cross_schema_compatibility(self) -> bool:
        """Test that schema definitions are compatible across database types."""
        print("\n📝 Testing Cross-Schema Compatibility...")

        try:
            from db_schema_definitions import (
                MULTI_USER_POSTGRESQL_SCHEMAS,
                MULTI_USER_SQLITE_SCHEMAS,
            )

            # Check that both schema sets have the same tables
            pg_tables = set(MULTI_USER_POSTGRESQL_SCHEMAS.keys())
            sqlite_tables = set(MULTI_USER_SQLITE_SCHEMAS.keys())

            if pg_tables != sqlite_tables:
                missing_in_pg = sqlite_tables - pg_tables
                missing_in_sqlite = pg_tables - sqlite_tables

                if missing_in_pg:
                    self.errors.append(
                        f"Tables missing in PostgreSQL schema: {missing_in_pg}"
                    )
                if missing_in_sqlite:
                    self.errors.append(
                        f"Tables missing in SQLite schema: {missing_in_sqlite}"
                    )
                return False

            print(f"  ✅ Both schemas define the same {len(pg_tables)} tables")
            print(f"    Tables: {', '.join(sorted(pg_tables))}")

            # Basic validation that each table schema contains expected keywords
            for table_name in pg_tables:
                pg_schema = MULTI_USER_POSTGRESQL_SCHEMAS[table_name]
                sqlite_schema = MULTI_USER_SQLITE_SCHEMAS[table_name]

                # Both should be CREATE TABLE statements
                if "CREATE TABLE" not in pg_schema.upper():
                    self.errors.append(
                        f"PostgreSQL schema for {table_name} is not a CREATE TABLE statement"
                    )
                if "CREATE TABLE" not in sqlite_schema.upper():
                    self.errors.append(
                        f"SQLite schema for {table_name} is not a CREATE TABLE statement"
                    )

            print("  ✅ Cross-schema compatibility test passed")
            return True

        except Exception as e:
            self.errors.append(f"Cross-schema compatibility test failed: {e}")
            print(f"  ❌ Cross-schema compatibility test failed: {e}")
            return False

    def _report_results(self) -> None:
        """Report test results."""
        print("\n" + "=" * 60)
        print("📋 SCHEMA COMPATIBILITY TEST RESULTS")
        print("=" * 60)

        if self.test_results:
            print(f"\n✅ SUCCESSFUL OPERATIONS ({len(self.test_results)}):")
            for result in self.test_results:
                print(f"   • {result}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")

        if not self.errors:
            print("\n🎉 ALL TESTS PASSED!")
            print(
                "   Schema definitions are compatible and functional across database types."
            )
        else:
            print("\n❌ SOME TESTS FAILED")
            print("   Schema compatibility issues found that need to be addressed.")

        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test schema compatibility between SQLite and PostgreSQL"
    )
    parser.add_argument(
        "--postgres-url",
        help="PostgreSQL connection string for testing (default: from POSTGRES_TEST_URL env var)",
    )
    parser.add_argument(
        "--skip-postgres", action="store_true", help="Skip PostgreSQL tests"
    )

    args = parser.parse_args()

    postgres_url = None
    if not args.skip_postgres:
        postgres_url = args.postgres_url or os.getenv("POSTGRES_TEST_URL")
        if not postgres_url:
            print(
                "ℹ️  No PostgreSQL URL provided. Use --postgres-url or POSTGRES_TEST_URL env var."
            )
            print("   PostgreSQL tests will be skipped.")

    # Run tests
    tester = SchemaCompatibilityTester(postgres_url)
    success = tester.run_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

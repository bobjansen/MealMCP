#!/usr/bin/env python3
"""
Test script to verify that household characteristics are properly set up
when creating new users through the web authentication system.
"""

import os
import sys
import tempfile
import uuid

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_setup_shared import setup_shared_database
from web_auth_simple import WebUserManager


def test_household_setup_sqlite():
    """Test household setup with SQLite backend."""
    print("🧪 Testing household setup with SQLite backend...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Set up shared database
        success = setup_shared_database(db_path)
        if not success:
            raise Exception("Failed to set up shared SQLite database")

        # Test WebUserManager
        auth_manager = WebUserManager("sqlite", db_path)

        # Try to create a user (should fail in SQLite mode)
        test_user = f"test_user_{uuid.uuid4().hex[:8]}"
        test_email = f"{test_user}@test.com"

        success, message = auth_manager.create_user(
            test_user, test_email, "test_password123"
        )

        # Should return False for SQLite mode
        if success:
            print("  ❌ SQLite mode unexpectedly allowed user creation")
            return False
        else:
            print(f"  ✅ SQLite mode correctly rejected user creation: {message}")
            return True

    except Exception as e:
        print(f"  ❌ SQLite test failed: {e}")
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def test_household_setup_postgresql(postgres_url: str = None):
    """Test household setup with PostgreSQL backend."""
    print("🧪 Testing household setup with PostgreSQL backend...")

    # Get PostgreSQL connection string
    if not postgres_url:
        postgres_url = os.getenv("POSTGRES_TEST_URL") or os.getenv(
            "PANTRY_DATABASE_URL"
        )

    if not postgres_url:
        print("  ⏭️  Skipping PostgreSQL test (no connection URL provided)")
        return True

    try:
        import psycopg2
        from urllib.parse import urlparse, urlunparse

        # Create temporary test database
        parsed = urlparse(postgres_url)
        test_db_name = f"test_household_setup_{uuid.uuid4().hex[:8]}"

        # Connect to postgres database to create test database
        admin_parsed = parsed._replace(path="/postgres")
        admin_connection = urlunparse(admin_parsed)

        admin_conn = psycopg2.connect(admin_connection)
        admin_conn.autocommit = True
        try:
            with admin_conn.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE "{test_db_name}"')
        finally:
            admin_conn.close()

        # Create connection to test database
        test_parsed = parsed._replace(path=f"/{test_db_name}")
        test_connection = urlunparse(test_parsed)

        try:
            # Set up shared database
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

            print(f"  ✅ Successfully created user: {test_user}")

            # Verify household characteristics were set up
            with psycopg2.connect(test_connection) as conn:
                with conn.cursor() as cursor:
                    # Verify user was created and has household_id
                    cursor.execute(
                        "SELECT username, email, household_id FROM users WHERE username = %s",
                        (test_user,),
                    )

                    user_data = cursor.fetchone()
                    if not user_data:
                        raise Exception("User not found in database")

                    username, email, household_id = user_data
                    if household_id is None:
                        raise Exception("household_id should be set to user's own ID")

                    print(f"  ✅ User created with household ID: {household_id}")

                    # Verify household characteristics were created in separate table
                    cursor.execute(
                        """
                        SELECT household_id, adults, children, preferred_volume_unit, 
                               preferred_weight_unit, preferred_count_unit
                        FROM household_characteristics WHERE household_id = %s
                        """,
                        (household_id,),
                    )

                    hc_data = cursor.fetchone()
                    if not hc_data:
                        raise Exception(
                            "Household characteristics not found in database"
                        )

                    (
                        hc_household_id,
                        adults,
                        children,
                        vol_unit,
                        weight_unit,
                        count_unit,
                    ) = hc_data

                    # Verify household characteristics
                    if hc_household_id != household_id:
                        raise Exception(
                            f"Household characteristics household_id mismatch: expected {household_id}, got {hc_household_id}"
                        )
                    if adults != 2:
                        raise Exception(f"Expected adults=2, got {adults}")
                    if children != 0:
                        raise Exception(f"Expected children=0, got {children}")
                    if vol_unit != "Milliliter":
                        raise Exception(
                            f"Expected preferred_volume_unit='Milliliter', got '{vol_unit}'"
                        )
                    if weight_unit != "Gram":
                        raise Exception(
                            f"Expected preferred_weight_unit='Gram', got '{weight_unit}'"
                        )
                    if count_unit != "Piece":
                        raise Exception(
                            f"Expected preferred_count_unit='Piece', got '{count_unit}'"
                        )

                    print(
                        f"  ✅ Household characteristics properly set in separate table:"
                    )
                    print(f"    - Household ID: {hc_household_id}")
                    print(f"    - Adults: {adults}, Children: {children}")
                    print(f"    - Units: {vol_unit}, {weight_unit}, {count_unit}")

            return True

        finally:
            # Clean up test database
            admin_conn = psycopg2.connect(admin_connection)
            admin_conn.autocommit = True
            try:
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
            finally:
                admin_conn.close()

    except Exception as e:
        print(f"  ❌ PostgreSQL test failed: {e}")
        return False


def main():
    """Run all household setup tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test household characteristics setup during user creation"
    )
    parser.add_argument(
        "--postgres-url",
        help="PostgreSQL connection string for testing (default: from POSTGRES_TEST_URL or PANTRY_DATABASE_URL env vars)",
    )
    parser.add_argument(
        "--skip-postgres", action="store_true", help="Skip PostgreSQL tests"
    )

    args = parser.parse_args()

    print("🏠 Testing Household Characteristics Setup")
    print("=" * 50)

    # Test SQLite
    sqlite_success = test_household_setup_sqlite()

    # Test PostgreSQL
    postgres_success = True
    if not args.skip_postgres:
        postgres_success = test_household_setup_postgresql(args.postgres_url)
    else:
        print("🧪 Skipping PostgreSQL tests (--skip-postgres specified)")

    print("\n" + "=" * 50)
    print("📋 TEST RESULTS")
    print("=" * 50)

    if sqlite_success and postgres_success:
        print("✅ ALL TESTS PASSED!")
        print("   Household characteristics are properly set up during user creation.")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        if not sqlite_success:
            print("   - SQLite test failed")
        if not postgres_success:
            print("   - PostgreSQL test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

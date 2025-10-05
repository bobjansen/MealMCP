#!/usr/bin/env python3
"""
Migrate existing users' units to match their preferred language.

This script:
1. Finds users whose preferred_language doesn't match their unit set
2. Checks if any pantry transactions use those units
3. If safe, replaces English units with locale-appropriate units
4. Provides a dry-run mode to preview changes

Usage:
    python scripts/migrate_units_to_locale.py --dry-run  # Preview changes
    python scripts/migrate_units_to_locale.py            # Apply changes
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2 import sql
from constants import UNITS_BY_LOCALE, get_units_for_locale


def get_database_connection():
    """Get PostgreSQL database connection from environment."""
    db_url = os.getenv("PANTRY_DATABASE_URL")
    if not db_url:
        print("❌ Error: PANTRY_DATABASE_URL environment variable not set")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        sys.exit(1)


def get_unit_names_for_locale(locale):
    """Get set of unit names for a locale."""
    units = get_units_for_locale(locale)
    return {u["name"] for u in units}


def analyze_users(conn):
    """Find users who need unit migration."""
    cursor = conn.cursor()

    # Get all users with their units
    cursor.execute(
        """
        SELECT
            u.id,
            u.username,
            u.preferred_language,
            COUNT(un.id) as unit_count,
            ARRAY_AGG(un.name ORDER BY un.name) as unit_names
        FROM users u
        LEFT JOIN units un ON un.user_id = u.id
        WHERE u.preferred_language IS NOT NULL
        GROUP BY u.id, u.username, u.preferred_language
        ORDER BY u.id
    """
    )

    users_to_migrate = []

    # Locale-specific marker units (units unique to each locale)
    locale_markers = {
        "en": {"Teaspoon", "Cup", "Ounce", "Pound", "Piece"},  # English-specific
        "nl": {"Theelepel", "Eetlepel", "Stuk", "Blik", "Pak"},  # Dutch-specific
    }

    for user_id, username, preferred_lang, unit_count, unit_names in cursor.fetchall():
        if unit_count == 0:
            continue  # No units yet, will be initialized on next access

        current_units = set(unit_names) if unit_names else set()

        # Get marker units for user's preferred language
        expected_markers = locale_markers.get(preferred_lang, set())

        # Check if user has marker units from a DIFFERENT locale
        for other_locale, other_markers in locale_markers.items():
            if other_locale != preferred_lang:
                # If user has units from a different locale
                if current_units.intersection(other_markers):
                    users_to_migrate.append(
                        {
                            "user_id": user_id,
                            "username": username,
                            "preferred_language": preferred_lang,
                            "current_locale": other_locale,
                            "current_units": current_units,
                            "expected_units": get_unit_names_for_locale(preferred_lang),
                        }
                    )
                    break

    cursor.close()
    return users_to_migrate


def check_unit_usage(conn, user_id):
    """Check if user has any pantry transactions using their units."""
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM pantry_transactions
        WHERE user_id = %s
    """,
        (user_id,),
    )

    transaction_count = cursor.fetchone()[0]
    cursor.close()

    return transaction_count


def migrate_user_units(conn, user_info, dry_run=True):
    """Migrate a user's units to their preferred locale."""
    user_id = user_info["user_id"]
    username = user_info["username"]
    locale = user_info["preferred_language"]

    print(
        f"\n{'[DRY RUN] ' if dry_run else ''}Migrating user: {username} (ID: {user_id}) to {locale} units"
    )

    # Check for pantry usage
    transaction_count = check_unit_usage(conn, user_id)

    if transaction_count > 0:
        print(f"  ⚠️  User has {transaction_count} pantry transactions")
        print(f"  ℹ️  Migration may affect existing pantry data")
        print(f"  ℹ️  Consider manual review for this user")
        return False

    cursor = conn.cursor()

    # Get new units for locale
    new_units = get_units_for_locale(locale)

    print(f"  📋 Current units: {', '.join(sorted(user_info['current_units']))}")
    print(f"  ✨ New units: {', '.join(sorted([u['name'] for u in new_units]))}")

    if not dry_run:
        try:
            # Delete old units
            cursor.execute("DELETE FROM units WHERE user_id = %s", (user_id,))
            deleted_count = cursor.rowcount
            print(f"  🗑️  Deleted {deleted_count} old units")

            # Insert new units
            cursor.executemany(
                """
                INSERT INTO units (user_id, name, base_unit, size)
                VALUES (%s, %s, %s, %s)
                """,
                [(user_id, u["name"], u["base_unit"], u["size"]) for u in new_units],
            )
            print(f"  ✅ Inserted {len(new_units)} new {locale} units")

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"  ❌ Error migrating user: {e}")
            cursor.close()
            return False
    else:
        print(f"  🔍 Would delete {len(user_info['current_units'])} units")
        print(f"  🔍 Would insert {len(new_units)} new units")

    cursor.close()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate user units to match their preferred language"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )
    parser.add_argument("--user-id", type=int, help="Migrate only specific user ID")

    args = parser.parse_args()

    print("🔄 Unit Locale Migration Tool")
    print("=" * 50)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()

    # Connect to database
    conn = get_database_connection()

    try:
        # Find users to migrate
        print("📊 Analyzing users...")
        users_to_migrate = analyze_users(conn)

        if not users_to_migrate:
            print("✅ All users already have locale-appropriate units!")
            return

        # Filter by user_id if specified
        if args.user_id:
            users_to_migrate = [
                u for u in users_to_migrate if u["user_id"] == args.user_id
            ]
            if not users_to_migrate:
                print(f"❌ User ID {args.user_id} not found or doesn't need migration")
                return

        print(f"\n📋 Found {len(users_to_migrate)} user(s) to migrate:")
        for user in users_to_migrate:
            print(
                f"  - {user['username']} (ID: {user['user_id']}) {user.get('current_locale', '?')} → {user['preferred_language']}"
            )

        if not args.dry_run:
            print("\n⚠️  This will modify the database!")
            response = input("Continue? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("❌ Migration cancelled")
                return

        # Migrate each user
        print("\n🚀 Starting migration...")
        success_count = 0

        for user in users_to_migrate:
            if migrate_user_units(conn, user, dry_run=args.dry_run):
                success_count += 1

        print("\n" + "=" * 50)
        if args.dry_run:
            print(
                f"🔍 Dry run complete - {success_count}/{len(users_to_migrate)} users would be migrated"
            )
            print("Run without --dry-run to apply changes")
        else:
            print(
                f"✅ Migration complete - {success_count}/{len(users_to_migrate)} users migrated"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Migrate recipe_ingredients table to use unit_id foreign key instead of unit text field.

This script:
1. Adds a new unit_id column to recipe_ingredients
2. Maps existing unit text values to unit IDs
3. Handles case variations and normalizes unit names
4. Drops the old unit column
5. Makes unit_id NOT NULL

Usage:
    PANTRY_DATABASE_URL="postgresql://..." python scripts/migrate_recipe_units_to_fk.py --dry-run
    PANTRY_DATABASE_URL="postgresql://..." python scripts/migrate_recipe_units_to_fk.py
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2 import sql


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


def normalize_unit_name(unit_text, target_locale=None):
    """Normalize unit name for matching (handle case variations and locale conversions)."""
    # Common variations mapping (English names)
    variations = {
        "g": "Gram",
        "gram": "Gram",
        "ml": "Milliliter",
        "milliliter": "Milliliter",
        "stuk": "Stuk",
        "piece": "Piece",
        "teaspoon": "Teaspoon",
        "tablespoon": "Tablespoon",
        "cup": "Cup",
        "liter": "Liter",
        "kilogram": "Kilogram",
        "kg": "Kilogram",
    }

    # Cross-locale mapping (English → Dutch)
    en_to_nl = {
        "Piece": "Stuk",
        "Teaspoon": "Theelepel",
        "Tablespoon": "Eetlepel",
        "Cup": "Deciliter",  # Approximate conversion
        # Shared units (same in both locales)
        "Gram": "Gram",
        "Kilogram": "Kilogram",
        "Milliliter": "Milliliter",
        "Liter": "Liter",
    }

    # Try exact match first
    if unit_text in variations:
        normalized = variations[unit_text]
    elif unit_text.lower() in variations:
        normalized = variations[unit_text.lower()]
    else:
        normalized = unit_text.capitalize() if unit_text else unit_text

    # If target locale is Dutch, try to convert English units to Dutch
    if target_locale == "nl" and normalized in en_to_nl:
        return en_to_nl[normalized]

    return normalized


def analyze_current_units(conn):
    """Analyze current unit values in recipe_ingredients."""
    cursor = conn.cursor()

    # Check if column already migrated
    cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'recipe_ingredients'
        AND column_name IN ('unit', 'unit_id')
    """
    )

    columns = {row[0]: row[1] for row in cursor.fetchall()}

    if "unit_id" in columns and "unit" not in columns:
        print(
            "✅ Migration already complete - unit_id column exists, unit column removed"
        )
        cursor.close()
        return None, True

    if "unit" not in columns:
        print("❌ Error: recipe_ingredients table doesn't have unit column")
        cursor.close()
        return None, False

    # Get distinct units with counts
    cursor.execute(
        """
        SELECT
            ri.unit,
            COUNT(*) as usage_count,
            array_agg(DISTINCT u.id) as user_ids
        FROM recipe_ingredients ri
        JOIN recipes r ON r.id = ri.recipe_id
        LEFT JOIN users u ON u.id = r.user_id
        GROUP BY ri.unit
        ORDER BY usage_count DESC
    """
    )

    unit_analysis = []
    for unit_text, count, user_ids in cursor.fetchall():
        unit_analysis.append({"text": unit_text, "count": count, "user_ids": user_ids})

    cursor.close()
    return unit_analysis, False


def build_unit_mapping(conn, unit_analysis):
    """Build mapping from unit text to unit_id for each user."""
    cursor = conn.cursor()

    # Get all units for all users with their locale
    cursor.execute(
        """
        SELECT u.user_id, u.id, u.name, usr.preferred_language
        FROM units u
        JOIN users usr ON usr.id = u.user_id
        ORDER BY u.user_id, u.name
    """
    )

    # Build lookup: (user_id, unit_name) -> unit_id
    unit_lookup = {}
    user_locales = {}
    for user_id, unit_id, unit_name, locale in cursor.fetchall():
        unit_lookup[(user_id, unit_name)] = unit_id
        user_locales[user_id] = locale or "en"

    cursor.close()

    # Map each unit text + user combo to unit_id
    mapping_report = []
    unmapped = []

    for unit_info in unit_analysis:
        unit_text = unit_info["text"]

        for user_id in unit_info["user_ids"]:
            if user_id is None:
                continue

            user_locale = user_locales.get(user_id, "en")

            # Try exact match first
            key = (user_id, unit_text)
            if key in unit_lookup:
                mapping_report.append(
                    {
                        "user_id": user_id,
                        "text": unit_text,
                        "unit_id": unit_lookup[key],
                        "matched": "exact",
                    }
                )
                continue

            # Try normalized match (with locale conversion)
            normalized = normalize_unit_name(unit_text, target_locale=user_locale)
            key = (user_id, normalized)
            if key in unit_lookup:
                mapping_report.append(
                    {
                        "user_id": user_id,
                        "text": unit_text,
                        "unit_id": unit_lookup[key],
                        "matched": "normalized",
                        "normalized_to": normalized,
                    }
                )
                continue

            # No match found
            unmapped.append(
                {
                    "user_id": user_id,
                    "text": unit_text,
                    "normalized": normalized,
                    "available_units": [
                        name for (uid, name) in unit_lookup.keys() if uid == user_id
                    ],
                }
            )

    return mapping_report, unmapped, unit_lookup


def perform_migration(conn, dry_run=True):
    """Perform the actual migration."""
    cursor = conn.cursor()

    print("\n🔄 Recipe Units Foreign Key Migration")
    print("=" * 60)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    # Analyze current state
    print("📊 Analyzing current recipe_ingredients table...")
    unit_analysis, already_migrated = analyze_current_units(conn)

    if already_migrated:
        return True

    if unit_analysis is None:
        return False

    if not unit_analysis:
        print("✅ No recipe ingredients found - nothing to migrate")
        return True

    print(f"\n📋 Found {len(unit_analysis)} distinct unit values:")
    for unit_info in unit_analysis:
        print(f"  - '{unit_info['text']}' (used {unit_info['count']} times)")

    # Build mappings
    print("\n🔍 Building unit mappings...")
    mapping_report, unmapped, unit_lookup = build_unit_mapping(conn, unit_analysis)

    if unmapped:
        print(
            f"\n⚠️  WARNING: {len(unmapped)} unit/user combinations couldn't be mapped:"
        )
        for item in unmapped[:10]:  # Show first 10
            print(
                f"  - User {item['user_id']}: '{item['text']}' → '{item['normalized']}'"
            )
            print(f"    Available units: {', '.join(item['available_units'][:5])}")

        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")

        print("\n❌ Cannot proceed - please fix unmapped units first")
        print("   Suggestion: Add missing units to users' unit tables")
        return False

    print(f"✅ All units mapped successfully ({len(mapping_report)} mappings)")

    if dry_run:
        print("\n🔍 Migration steps that WOULD be performed:")
        print("  1. Add unit_id column (nullable)")
        print("  2. Update unit_id values based on unit text")
        print(
            f"  3. Update {sum(u['count'] for u in unit_analysis)} recipe_ingredient rows"
        )
        print("  4. Make unit_id NOT NULL")
        print("  5. Drop unit column")
        print("  6. Add foreign key constraint")
        return True

    print("\n🚀 Performing migration...")

    try:
        # Step 1: Add unit_id column
        print("  1️⃣  Adding unit_id column...")
        cursor.execute(
            """
            ALTER TABLE recipe_ingredients
            ADD COLUMN IF NOT EXISTS unit_id INTEGER
        """
        )

        # Step 2: Update unit_id values
        print("  2️⃣  Updating unit_id values...")

        # Get all recipe ingredients with their user_ids and locales
        cursor.execute(
            """
            SELECT ri.id, ri.unit, r.user_id, u.preferred_language
            FROM recipe_ingredients ri
            JOIN recipes r ON r.id = ri.recipe_id
            JOIN users u ON u.id = r.user_id
        """
        )

        rows_to_update = cursor.fetchall()
        updated_count = 0

        for ri_id, unit_text, user_id, user_locale in rows_to_update:
            # Try exact match first
            unit_id = unit_lookup.get((user_id, unit_text))

            # Try normalized match with locale conversion
            if not unit_id:
                normalized = normalize_unit_name(
                    unit_text, target_locale=user_locale or "en"
                )
                unit_id = unit_lookup.get((user_id, normalized))

            if unit_id:
                cursor.execute(
                    "UPDATE recipe_ingredients SET unit_id = %s WHERE id = %s",
                    (unit_id, ri_id),
                )
                updated_count += 1

        print(f"     Updated {updated_count} rows")

        # Step 3: Make unit_id NOT NULL
        print("  3️⃣  Making unit_id NOT NULL...")
        cursor.execute(
            """
            ALTER TABLE recipe_ingredients
            ALTER COLUMN unit_id SET NOT NULL
        """
        )

        # Step 4: Drop old unit column
        print("  4️⃣  Dropping old unit column...")
        cursor.execute(
            """
            ALTER TABLE recipe_ingredients
            DROP COLUMN IF EXISTS unit
        """
        )

        # Step 5: Add foreign key constraint
        print("  5️⃣  Adding foreign key constraint...")
        cursor.execute(
            """
            ALTER TABLE recipe_ingredients
            ADD CONSTRAINT fk_recipe_ingredients_unit
            FOREIGN KEY (unit_id) REFERENCES units(id)
        """
        )

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        return False
    finally:
        cursor.close()

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate recipe_ingredients to use unit_id foreign key"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying them"
    )

    args = parser.parse_args()

    conn = get_database_connection()

    try:
        success = perform_migration(conn, dry_run=args.dry_run)

        if args.dry_run and success:
            print("\n" + "=" * 60)
            print("🔍 Dry run complete - run without --dry-run to apply changes")

        sys.exit(0 if success else 1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()

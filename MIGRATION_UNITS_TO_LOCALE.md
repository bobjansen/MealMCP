# Unit Locale Migration Guide

## Overview

Starting with this update, units are locale-specific:
- **English users** get Imperial/US units (Teaspoon, Cup, Ounce, Pound, Piece)
- **Dutch users** get Metric units (Theelepel, Eetlepel, Gram, Kilogram, Stuk)

## For New Users

✅ **No action needed** - units will automatically be created in the correct language based on `preferred_language`

## For Existing Users

Existing users may have units from the wrong locale. The migration script helps fix this.

### Migration Script

Located at: `scripts/migrate_units_to_locale.py`

### Usage

**1. Preview changes (dry-run):**
```bash
PANTRY_DATABASE_URL="postgresql://user:pass@host:5432/meal_manager" \
uv run python scripts/migrate_units_to_locale.py --dry-run
```

**2. Migrate all eligible users:**
```bash
PANTRY_DATABASE_URL="postgresql://user:pass@host:5432/meal_manager" \
uv run python scripts/migrate_units_to_locale.py
```

**3. Migrate specific user only:**
```bash
PANTRY_DATABASE_URL="postgresql://user:pass@host:5432/meal_manager" \
uv run python scripts/migrate_units_to_locale.py --user-id 2
```

### Safety Features

The script includes several safety checks:

1. **Dry-run mode** - Preview changes before applying
2. **Pantry transaction check** - Warns if user has existing pantry data
3. **Confirmation prompt** - Asks for confirmation before making changes
4. **Transaction rollback** - Automatically rolls back on errors

### What Gets Migrated

The script:
- ✅ Detects users with units from wrong locale (e.g., Dutch user with English units)
- ✅ Deletes old units
- ✅ Inserts new locale-appropriate units
- ⚠️ **WARNING**: May affect existing pantry data if user has transactions

### Example Output

```
🔄 Unit Locale Migration Tool
==================================================
🔍 DRY RUN MODE - No changes will be made

📊 Analyzing users...

📋 Found 1 user(s) to migrate:
  - Bob (ID: 2) en → nl

🚀 Starting migration...

[DRY RUN] Migrating user: Bob (ID: 2) to nl units
  ⚠️  User has 80 pantry transactions
  ℹ️  Migration may affect existing pantry data
  ℹ️  Consider manual review for this user
  📋 Current units: Cup, Fluid ounce, Gallon, Gram, Kilogram, Liter, ...
  ✨ New units: Blik, Deciliter, Eetlepel, Gram, Kilogram, Liter, ...
  🔍 Would delete 14 units
  🔍 Would insert 11 new units

==================================================
🔍 Dry run complete - 0/1 users would be migrated
Run without --dry-run to apply changes
```

### Users with Pantry Data

If a user has existing pantry transactions, the script:
1. **Warns** about potential data impact
2. **Still allows migration** but recommends manual review
3. Existing pantry items may reference old unit names

**Recommendation for users with data:**
- Review their pantry items before migration
- Consider having them manually migrate their pantry or
- Keep their current units and let them add Dutch units if needed

### Manual Alternative

Users can also:
1. Go to Units Management page
2. Delete unwanted units manually
3. Add new units in their preferred language
4. This gives them full control over the process

## Technical Details

### Locale Detection

The script identifies mismatched locales by checking for "marker units":
- **English markers**: Teaspoon, Cup, Ounce, Pound, Piece
- **Dutch markers**: Theelepel, Eetlepel, Stuk, Blik, Pak

If a Dutch user has English marker units, they're flagged for migration.

### Unit Sets

**English (en):**
- Teaspoon, Tablespoon, Fluid ounce, Cup, Pint, Quart, Gallon
- Milliliter, Liter
- Ounce, Pound, Gram, Kilogram
- Piece

**Dutch (nl):**
- Theelepel (teaspoon), Eetlepel (tablespoon)
- Milliliter, Deciliter, Liter
- Gram, Kilogram
- Stuk (piece), Blik (can), Pak (package), Zakje (packet)

## Questions?

- Check existing units: Query `units` table filtered by `user_id`
- Check user language: Query `users` table for `preferred_language`
- See code: `constants.py` for unit definitions

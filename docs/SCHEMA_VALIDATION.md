# Database Schema Validation

This document describes the schema validation tools available to ensure that the PostgreSQL database schema matches exactly what the application expects.

## Overview

The MealMCP application supports both SQLite (single-user) and PostgreSQL (multi-user) backends. To ensure database compatibility and prevent schema migration issues, two validation scripts are provided:

1. **`validate_postgresql_schema.py`** - Validates PostgreSQL schema against application expectations
2. **`test_schema_compatibility.py`** - Tests compatibility between SQLite and PostgreSQL schemas

## Schema Validation Scripts

### PostgreSQL Schema Validator

**Purpose**: Validates that a PostgreSQL database schema created by the application matches exactly what the application code expects.

**Usage**:
```bash
# Basic validation (requires POSTGRES_TEST_URL env var)
uv run python validate_postgresql_schema.py

# With connection string
uv run python validate_postgresql_schema.py --connection-string "postgresql://user:pass@localhost/dbname"

# Create temporary test database and clean up afterwards
uv run python validate_postgresql_schema.py --connection-string "postgresql://user:pass@localhost/" --create-test-db
```

**What it validates**:
- All expected tables exist
- Table schemas match expected column definitions
- Foreign key constraints are properly defined
- Indexes are created as expected
- Application classes (`WebUserManager`, `SharedPantryManager`) work correctly with the schema

### Schema Compatibility Tester

**Purpose**: Tests that schema definitions are compatible between SQLite and PostgreSQL implementations.

**Usage**:
```bash
# Test SQLite schemas only
uv run python test_schema_compatibility.py --skip-postgres

# Test with PostgreSQL (requires POSTGRES_TEST_URL env var)
uv run python test_schema_compatibility.py

# Test with specific PostgreSQL URL
uv run python test_schema_compatibility.py --postgres-url "postgresql://user:pass@localhost/"
```

**What it tests**:
- Single-user SQLite schema functionality
- Multi-user SQLite schema functionality
- Multi-user PostgreSQL schema functionality (if URL provided)
- Cross-schema compatibility (same tables defined in both)
- Application functionality works with all schema types

## Environment Variables

- **`POSTGRES_TEST_URL`**: PostgreSQL connection URL for testing (e.g., `postgresql://user:pass@localhost/`)
- **`PANTRY_DATABASE_URL`**: Fallback connection URL for general database operations

## Schema Definitions

All schema definitions are centralized in `db_schema_definitions.py`:

- **`SINGLE_USER_SCHEMAS`**: SQLite table definitions for single-user mode
- **`MULTI_USER_POSTGRESQL_SCHEMAS`**: PostgreSQL table definitions for multi-user mode
- **`MULTI_USER_SQLITE_SCHEMAS`**: SQLite table definitions for multi-user mode
- **`MULTI_USER_POSTGRESQL_INDEXES`**: Index definitions for PostgreSQL
- **`MULTI_USER_SQLITE_INDEXES`**: Index definitions for SQLite

## Running in CI/CD

These validation scripts can be integrated into CI/CD pipelines to ensure schema integrity:

```bash
# In your CI script
export POSTGRES_TEST_URL="postgresql://postgres:password@localhost/"

# Run compatibility tests
uv run python test_schema_compatibility.py

# Run PostgreSQL validation with temporary database
uv run python validate_postgresql_schema.py --create-test-db
```

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure PostgreSQL is running and connection credentials are correct
2. **Permission Errors**: User must have CREATE DATABASE permissions for `--create-test-db` option
3. **Schema Mismatch**: Check that `db_schema_definitions.py` is up to date with application requirements

### Debugging Schema Issues

If validation fails:

1. Check the error messages for specific table/column/constraint issues
2. Compare the expected schema in `db_schema_definitions.py` with the actual database schema
3. Ensure all recent schema changes are reflected in the definitions
4. Run the compatibility tester to identify cross-platform issues

### Manual Schema Inspection

You can manually inspect the database schema using:

```sql
-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Describe a table
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND table_schema = 'public';

-- List foreign keys
SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
```

## Benefits

Using these validation scripts ensures:

1. **No Schema Drift**: Database schema matches application expectations exactly
2. **Migration Safety**: New deployments won't fail due to schema mismatches  
3. **Cross-Platform Compatibility**: SQLite and PostgreSQL implementations stay in sync
4. **Early Detection**: Schema issues are caught before production deployment
5. **Documentation**: Schema expectations are explicitly tested and documented

## Integration with Tests

The schema validation can be integrated with existing test suites:

```python
import subprocess
import sys

def test_postgresql_schema_validation():
    """Test that PostgreSQL schema validation passes."""
    result = subprocess.run([
        sys.executable, "validate_postgresql_schema.py", "--create-test-db"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Schema validation failed: {result.stderr}"

def test_schema_compatibility():
    """Test that schema compatibility tests pass."""
    result = subprocess.run([
        sys.executable, "test_schema_compatibility.py", "--skip-postgres"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Compatibility test failed: {result.stderr}"
```

This ensures that schema validation is part of your regular testing process and prevents schema-related regressions.
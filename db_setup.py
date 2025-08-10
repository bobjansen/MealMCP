import sqlite3
from db_schema_definitions import (
    SINGLE_USER_SCHEMAS,
    SINGLE_USER_INDEXES,
    SINGLE_USER_DEFAULTS,
)
from error_utils import safe_execute


@safe_execute("setup single-user database", default_return=False, log_errors=True)
def setup_database(db_path="pantry.db"):
    """
    Set up SQLite database for single-user mode using centralized schema definitions.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create all tables using centralized schema definitions
    for table_name, schema in SINGLE_USER_SCHEMAS.items():
        cursor.execute(schema)

    # Create indexes
    for index_sql in SINGLE_USER_INDEXES:
        cursor.execute(index_sql)

    # Insert default data
    for default_sql in SINGLE_USER_DEFAULTS:
        cursor.execute(default_sql)

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    print("Setting up the database")
    setup_database()

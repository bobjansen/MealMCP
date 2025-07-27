import sqlite3


def setup_database(
    db_path="pantry.db",
):  # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Create PantryTransactions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PantryTransactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,  -- 'addition' or 'removal'
            item_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            transaction_date TEXT NOT NULL,
            notes TEXT
        )
    """
    )

    # Commit changes and close the connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Setting up the database")
    setup_database()

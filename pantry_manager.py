import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class PantryManager:
    def __init__(self, db_path: str = "pantry.db"):
        self.db_path = db_path

    def _get_connection(self):
        """Get a database connection. Should be used in a context manager."""
        return sqlite3.connect(self.db_path)

    def add_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Add a new item to the pantry or increase existing item quantity.

        Args:
            item_name: Name of the item to add
            quantity: Amount to add
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO PantryTransactions
                    (transaction_type, item_name, quantity, unit, transaction_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "addition",
                        item_name,
                        quantity,
                        unit,
                        datetime.now().isoformat(),
                        notes,
                    ),
                )
                return True
        except Exception as e:
            print(f"Error adding item: {e}")
            return False

    def remove_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Remove a quantity of an item from the pantry.

        Args:
            item_name: Name of the item to remove
            quantity: Amount to remove
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # First check if we have enough of the item
            current_quantity = self.get_item_quantity(item_name, unit)
            if current_quantity < quantity:
                print(
                    f"Not enough {item_name} in pantry. Current quantity: {current_quantity} {unit}"
                )
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO PantryTransactions
                    (transaction_type, item_name, quantity, unit, transaction_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "removal",
                        item_name,
                        quantity,
                        unit,
                        datetime.now().isoformat(),
                        notes,
                    ),
                )
                return True
        except Exception as e:
            print(f"Error removing item: {e}")
            return False

    def get_item_quantity(self, item_name: str, unit: str) -> float:
        """
        Get the current quantity of an item in the pantry.

        Args:
            item_name: Name of the item to check
            unit: Unit of measurement

        Returns:
            float: Current quantity of the item (can be negative if more removals than additions)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        SUM(CASE
                            WHEN transaction_type = 'addition' THEN quantity
                            ELSE -quantity
                        END) as net_quantity
                    FROM PantryTransactions
                    WHERE item_name = ? AND unit = ?
                    """,
                    (item_name, unit),
                )
                result = cursor.fetchone()[0]
                return float(result) if result is not None else 0.0
        except Exception as e:
            print(f"Error getting item quantity: {e}")
            return 0.0

    def get_pantry_contents(self) -> Dict[str, Dict[str, float]]:
        """
        Get the current contents of the pantry.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary with item names as keys and their quantities by unit as values
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT
                        item_name,
                        unit,
                        SUM(CASE
                            WHEN transaction_type = 'addition' THEN quantity
                            ELSE -quantity
                        END) as net_quantity
                    FROM PantryTransactions
                    GROUP BY item_name, unit
                    HAVING net_quantity > 0
                    """
                )
                results = cursor.fetchall()

                contents = {}
                for item_name, unit, quantity in results:
                    if item_name not in contents:
                        contents[item_name] = {}
                    contents[item_name][unit] = quantity

                return contents
        except Exception as e:
            print(f"Error getting pantry contents: {e}")
            return {}

    def get_transaction_history(
        self, item_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the transaction history for all items or a specific item.

        Args:
            item_name: Optional name of item to filter transactions

        Returns:
            List[Dict[str, Any]]: List of transactions with their details
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if item_name:
                    cursor.execute(
                        """
                        SELECT * FROM PantryTransactions
                        WHERE item_name = ?
                        ORDER BY transaction_date DESC
                        """,
                        (item_name,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM PantryTransactions
                        ORDER BY transaction_date DESC
                        """
                    )

                columns = [description[0] for description in cursor.description]
                transactions = []

                for row in cursor.fetchall():
                    transactions.append(dict(zip(columns, row)))

                return transactions
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return []

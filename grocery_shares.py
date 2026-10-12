"""Persistent, read-only shopping-list snapshots addressed by unguessable URLs."""

import json
import re
import secrets

from db import get_database


class GroceryShares:
    def __init__(self, backend, connection_string):
        self.db = get_database(backend, connection_string)
        self.placeholder = "%s" if self.db.backend == "postgresql" else "?"
        with self.db.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS grocery_shares "
                    "(token TEXT PRIMARY KEY, snapshot TEXT NOT NULL)"
                )
            finally:
                cursor.close()

    def create(self, items, start_date, language):
        token = secrets.token_urlsafe(32)
        # Only include list fields, never account or pantry metadata.
        snapshot = {
            "items": [
                {
                    "name": item["name"],
                    "quantity": str(item["quantity"]),
                    "unit": item["unit"],
                }
                for item in items
            ],
            "start_date": start_date.isoformat(),
            "language": language,
        }
        with self.db.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"INSERT INTO grocery_shares (token, snapshot) VALUES ({self.placeholder}, {self.placeholder})",
                    (token, json.dumps(snapshot)),
                )
            finally:
                cursor.close()
        return token

    def get(self, token):
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        with self.db.connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"SELECT snapshot FROM grocery_shares WHERE token = {self.placeholder}",
                    (token,),
                )
                row = cursor.fetchone()
            finally:
                cursor.close()
        return json.loads(row[0]) if row else None

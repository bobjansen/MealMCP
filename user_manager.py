"""
Recipe-specific User Manager - wraps generic MCP Core.

Provides backwards compatibility while using the new generic user manager.
"""

from mcp_core.auth.user_manager import UserManager as GenericUserManager
from db_setup import setup_database
import os


class UserManager(GenericUserManager):
    """Recipe-specific user manager with pantry database setup."""

    def __init__(self, mode: str = "local"):
        # Initialize with recipe-specific database setup
        super().__init__(mode=mode, database_setup_func=setup_database)

    def get_user_db_path(self, user_id: str) -> str:
        """Get the database path for a specific user."""
        if self.mode == "local":
            # In local mode, use PANTRY_DB_PATH if set, otherwise default to "pantry.db"
            return os.getenv("PANTRY_DB_PATH", "pantry.db")

        # Create user-specific database file
        user_db_dir = self.data_dir / user_id
        user_db_dir.mkdir(exist_ok=True)
        return str(user_db_dir / "pantry.db")

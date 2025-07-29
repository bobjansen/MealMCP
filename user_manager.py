import os
import hashlib
import secrets
from typing import Dict, Optional
from pathlib import Path


class UserManager:
    """Manages user authentication and database isolation for multi-user mode."""

    def __init__(self, mode: str = "local"):
        self.mode = mode  # "local" or "remote"
        self.users: Dict[str, Dict[str, str]] = {}
        self.tokens: Dict[str, str] = {}  # token -> user_id
        self.data_dir = Path("user_data")

        if mode == "remote":
            self.data_dir.mkdir(exist_ok=True)
            self._load_users()

    def _load_users(self):
        """Load users from environment or create default admin user."""
        # In production, this would load from a secure database
        # For now, we'll use environment variables for simplicity
        admin_token = os.getenv("ADMIN_TOKEN")
        if not admin_token:
            admin_token = secrets.token_urlsafe(32)
            print(f"Generated admin token: {admin_token}")
            print("Set ADMIN_TOKEN environment variable to use this token")

        admin_user = "admin"
        self.users[admin_user] = {"token": admin_token}
        self.tokens[admin_token] = admin_user

        # Load additional users from environment
        additional_users = os.getenv("ADDITIONAL_USERS", "")
        if additional_users:
            for user_config in additional_users.split(","):
                if ":" in user_config:
                    username, token = user_config.strip().split(":", 1)
                    self.users[username] = {"token": token}
                    self.tokens[token] = username

    def authenticate(self, token: str) -> Optional[str]:
        """Authenticate a user by token and return user_id."""
        if self.mode == "local":
            return "local_user"

        return self.tokens.get(token)

    def get_user_db_path(self, user_id: str) -> str:
        """Get the database path for a specific user."""
        if self.mode == "local":
            return "pantry.db"

        # Create user-specific database file
        user_db_dir = self.data_dir / user_id
        user_db_dir.mkdir(exist_ok=True)
        return str(user_db_dir / "pantry.db")

    def create_user(self, username: str) -> str:
        """Create a new user and return their token."""
        if self.mode == "local":
            raise ValueError("Cannot create users in local mode")

        if username in self.users:
            raise ValueError(f"User {username} already exists")

        token = secrets.token_urlsafe(32)
        self.users[username] = {"token": token}
        self.tokens[token] = username

        # Initialize user's database
        from db_setup import setup_database

        db_path = self.get_user_db_path(username)
        setup_database(db_path)

        return token

    def list_users(self) -> list:
        """List all users (admin only)."""
        if self.mode == "local":
            return ["local_user"]

        return list(self.users.keys())

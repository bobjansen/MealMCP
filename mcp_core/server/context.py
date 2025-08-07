"""
Generic MCP Context management.

This module provides a generic context manager that can be configured with any
data manager factory and database setup function.
"""

from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
from ..auth.user_manager import UserManager
import os

# Context variable to store current user
current_user: ContextVar[Optional[str]] = ContextVar("current_user", default=None)


class MCPContext:
    """
    Generic MCP server context for user authentication and resource management.

    This class can be configured with any data manager factory and database setup
    function to work with different types of applications.
    """

    def __init__(
        self,
        data_manager_factory: Optional[Callable] = None,
        database_setup_func: Optional[Callable] = None,
    ):
        """
        Initialize MCP context.

        Args:
            data_manager_factory: Function to create data manager instances
            database_setup_func: Function to setup/initialize databases
        """
        self.mode = os.getenv("MCP_MODE", "local")  # "local" or "remote"
        self.user_manager = UserManager(self.mode, database_setup_func)
        self.data_managers: Dict[str, Any] = {}

        # Store the factory functions
        self.data_manager_factory = data_manager_factory
        self.database_setup_func = database_setup_func

        # Initialize local user in local mode
        if self.mode == "local" and self.data_manager_factory:
            local_user = "local_user"
            db_path = self.user_manager.get_user_db_path(local_user)
            self.data_managers[local_user] = self.data_manager_factory(
                connection_string=db_path
            )

            if self.database_setup_func:
                self.database_setup_func(db_path)

    def authenticate_and_get_data_manager(
        self, token: Optional[str] = None
    ) -> tuple[Optional[str], Optional[Any]]:
        """Authenticate user and return their data manager instance."""
        if self.mode == "local":
            user_id = "local_user"
            if user_id not in self.data_managers and self.data_manager_factory:
                db_path = self.user_manager.get_user_db_path(user_id)
                self.data_managers[user_id] = self.data_manager_factory(
                    connection_string=db_path
                )
            return user_id, self.data_managers.get(user_id)

        if not token:
            return None, None

        user_id = self.user_manager.authenticate(token)
        if not user_id:
            return None, None

        # Lazy load data manager for this user
        if user_id not in self.data_managers and self.data_manager_factory:
            db_path = self.user_manager.get_user_db_path(user_id)
            self.data_managers[user_id] = self.data_manager_factory(
                connection_string=db_path
            )

            if self.database_setup_func:
                self.database_setup_func(db_path)

        return user_id, self.data_managers.get(user_id)

    def set_current_user(self, user_id: str):
        """Set the current user in context."""
        current_user.set(user_id)

    def get_current_user(self) -> Optional[str]:
        """Get the current user from context."""
        return current_user.get()

    def create_user(self, username: str, admin_token: str) -> Dict[str, Any]:
        """Create a new user (admin only)."""
        # Verify admin token
        admin_user = self.user_manager.authenticate(admin_token)
        if admin_user != "admin":
            return {"status": "error", "message": "Admin access required"}

        try:
            token = self.user_manager.create_user(username)
            return {"status": "success", "token": token, "username": username}
        except ValueError as e:
            return {"status": "error", "message": str(e)}

    # Backwards compatibility method for recipe-specific usage
    def authenticate_and_get_pantry(
        self, token: Optional[str] = None
    ) -> tuple[Optional[str], Optional[Any]]:
        """Backwards compatibility alias for authenticate_and_get_data_manager."""
        return self.authenticate_and_get_data_manager(token)

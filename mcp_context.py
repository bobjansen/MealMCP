"""
Recipe-specific MCP Context - wraps generic MCP Core.

Provides backwards compatibility while using the new generic MCP core.
"""

from typing import Optional, Dict, Any
from mcp_core.server.context import MCPContext as GenericMCPContext
from pantry_manager_factory import create_pantry_manager
from pantry_manager_abc import PantryManager
from user_manager import UserManager
from db_setup import setup_database


class MCPContext(GenericMCPContext):
    """Recipe-specific MCP context with pantry management capabilities."""

    def __init__(self):
        # Initialize with recipe-specific components
        super().__init__(
            data_manager_factory=create_pantry_manager,
            database_setup_func=setup_database,
        )

        # Maintain backwards compatibility - alias data_managers to pantry_managers
        self.pantry_managers = self.data_managers

    def authenticate_and_get_pantry(
        self, token: Optional[str] = None
    ) -> tuple[Optional[str], Optional[PantryManager]]:
        """Authenticate user and return their PantryManager instance."""
        return self.authenticate_and_get_data_manager(token)

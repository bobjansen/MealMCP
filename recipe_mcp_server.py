"""
Recipe-specific MCP Server using the generic MCP Core.

This server wraps the generic UnifiedMCPServer with recipe-specific
tool routers and data managers.
"""

import os
from mcpnp import UnifiedMCPServer
from mcp_tool_router import MCPToolRouter
from pantry_manager_factory import create_pantry_manager
from pantry_manager_shared import SharedPantryManager
from db_setup import setup_database
from db_setup_shared import setup_shared_database
from datastore_postgresql import PostgreSQLOAuthDatastore


class RecipeDataManagerFactory:
    """Factory class that creates recipe data managers with proper user context."""

    def __init__(self):
        self.current_user_id = None

    def set_user_context(self, user_id: int):
        """Set the current user context for the factory."""
        self.current_user_id = user_id

    def create_data_manager(
        self, connection_string: str = None, user_id: int = None, **kwargs
    ):
        """
        Factory function for creating recipe data managers that supports both SQLite and PostgreSQL.

        Args:
            connection_string: Database connection string
            user_id: User ID for multi-user PostgreSQL scenarios (uses context if not provided)
            **kwargs: Additional configuration options

        Returns:
            PantryManager: Configured pantry manager instance
        """
        # Use provided user_id or fall back to context
        effective_user_id = user_id or self.current_user_id

        # Determine backend from environment or connection string
        backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

        # Auto-detect PostgreSQL from connection string
        if connection_string and connection_string.startswith(
            ("postgresql://", "postgres://")
        ):
            backend = "postgresql"

        # Use appropriate manager based on backend
        if backend in ("postgresql", "postgres"):
            if not connection_string:
                connection_string = os.getenv("PANTRY_DATABASE_URL")
            if not connection_string:
                raise ValueError(
                    "PostgreSQL connection string required for PostgreSQL backend"
                )
            if effective_user_id is None:
                # For PostgreSQL multi-user, try to extract user_id from connection_string path
                # The MCP framework may encode user info in the db_path

                if connection_string.startswith(("postgresql://", "postgres://")):
                    # Use a default user_id of 1 if we can't determine it
                    # This is a fallback - ideally the MCP framework should pass user_id
                    effective_user_id = 1
                else:
                    raise ValueError(
                        "user_id required for PostgreSQL multi-user scenarios"
                    )

            # Setup shared database if needed
            setup_shared_database(connection_string)
            return SharedPantryManager(
                connection_string, effective_user_id, backend="postgresql"
            )
        else:
            # Use factory for SQLite single-user scenarios
            return create_pantry_manager(backend, connection_string, **kwargs)


# Global factory instance
_recipe_factory = RecipeDataManagerFactory()


def create_recipe_data_manager(connection_string: str = None, **kwargs):
    """Wrapper function for the MCP framework that uses the global factory."""
    return _recipe_factory.create_data_manager(connection_string, **kwargs)


class RecipeMCPServer(UnifiedMCPServer):
    """Recipe-specific MCP server with pantry management capabilities."""

    def __init__(self):
        # Create recipe-specific tool router
        tool_router = MCPToolRouter()

        # Setup OAuth datastore if needed
        oauth_datastore = None
        transport = os.environ.get("MCP_TRANSPORT", "fastmcp")
        if transport == "oauth" or os.environ.get("MCP_MODE") == "oauth":
            db_url = os.environ.get("PANTRY_DATABASE_URL")
            if db_url:
                oauth_datastore = PostgreSQLOAuthDatastore(db_url)

        # Choose appropriate database setup function
        backend = os.environ.get("PANTRY_BACKEND", "sqlite").lower()
        db_url = os.environ.get("PANTRY_DATABASE_URL", "")
        if backend in ("postgresql", "postgres") or db_url.startswith(
            ("postgresql://", "postgres://")
        ):
            db_setup_func = setup_shared_database
        else:
            db_setup_func = setup_database

        # Configure with recipe-specific components
        super().__init__(
            tool_router=tool_router,
            data_manager_factory=create_recipe_data_manager,
            database_setup_func=db_setup_func,
            server_name="Recipe Manager",
            oauth_datastore=oauth_datastore,
        )

    def get_user_data_manager(self, user_id: str):
        """Override to handle PostgreSQL multi-user scenarios properly."""
        backend = os.environ.get("PANTRY_BACKEND", "sqlite").lower()
        db_url = os.environ.get("PANTRY_DATABASE_URL", "")

        # For PostgreSQL backend, use shared database with user scoping
        if backend in ("postgresql", "postgres") or db_url.startswith(
            ("postgresql://", "postgres://")
        ):
            # Check if we already have a data manager for this user
            if user_id not in self.context.data_managers:
                connection_string = os.environ.get("PANTRY_DATABASE_URL")
                if not connection_string:
                    raise ValueError(
                        "PANTRY_DATABASE_URL required for PostgreSQL backend"
                    )

                # Convert user_id to integer for SharedPantryManager
                try:
                    user_id_int = int(user_id)
                except (ValueError, TypeError):
                    # If user_id is not numeric, use a hash or assign a default
                    user_id_int = hash(user_id) % 1000000  # Simple hash to integer

                # Setup shared database if needed
                setup_shared_database(connection_string)

                # Create SharedPantryManager directly with user_id
                data_manager = SharedPantryManager(
                    connection_string, user_id_int, backend="postgresql"
                )
                self.context.data_managers[user_id] = data_manager

            return user_id, self.context.data_managers[user_id]
        else:
            # For SQLite, use the parent implementation
            return super().get_user_data_manager(user_id)

    # Backwards compatibility methods for recipe-specific API
    def get_user_pantry(self, user_id=None, token=None):
        """Backwards compatibility alias for get_user_data_manager."""
        return self.get_user_data_manager(user_id)


def main():
    """Main entry point for recipe MCP server."""
    server = RecipeMCPServer()
    server.run()


if __name__ == "__main__":
    main()

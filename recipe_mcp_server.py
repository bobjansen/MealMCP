"""
Recipe-specific MCP Server using the generic MCP Core.

This server wraps the generic UnifiedMCPServer with recipe-specific
tool routers and data managers.
"""

import os
from mcpnp import UnifiedMCPServer, MCPContext
from mcp_tool_router import MCPToolRouter
from pantry_manager_factory import create_pantry_manager
from db_setup import setup_database
from datastore_postgresql import PostgreSQLOAuthDatastore


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

        # Configure with recipe-specific components
        super().__init__(
            tool_router=tool_router,
            data_manager_factory=create_pantry_manager,
            database_setup_func=setup_database,
            server_name="Recipe Manager",
            oauth_datastore=oauth_datastore,
        )

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

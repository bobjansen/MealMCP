"""
Recipe MCP Server - Recipe-specific MCP server implementation.

This is the main entry point for the recipe MCP server, which uses the
generic MCP Core framework with recipe-specific components.

Supports:
- Multiple transport modes: FastMCP (stdio), HTTP REST, Server-Sent Events
- Authentication modes: None (local), Token (remote), OAuth 2.1 (multi-user)
- Backend modes: SQLite (single-user), PostgreSQL (multi-user)
- Recipe and pantry management tools

Environment Configuration:
- MCP_TRANSPORT: "fastmcp" (default), "http", "sse", "oauth"
- MCP_MODE: "local" (default), "multiuser"
- MCP_HOST: "localhost"
- MCP_PORT: 8000
- PANTRY_BACKEND: "sqlite", "postgresql"
- MCP_PUBLIC_URL: For OAuth mode
"""

# Import the recipe-specific server
from recipe_mcp_server import RecipeMCPServer

# Import OAuth components for backwards compatibility
from mcp_core.auth import OAuthServer, OAuthFlowHandler
from mcp_core.templates.oauth_templates import (
    generate_login_form,
    generate_register_form,
    generate_error_page,
)

# Alias for backwards compatibility
UnifiedMCPServer = RecipeMCPServer


def main():
    """Main entry point for the recipe MCP server."""
    server = RecipeMCPServer()
    server.run()


# Main entry point
if __name__ == "__main__":
    main()

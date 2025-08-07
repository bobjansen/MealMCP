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
- MCP_MODE: "local" (default), "remote", "multiuser"
- MCP_HOST: "localhost"
- MCP_PORT: 8000
- PANTRY_BACKEND: "sqlite", "postgresql"
- MCP_PUBLIC_URL: For OAuth mode
"""

# Import the recipe-specific server
from recipe_mcp_server import RecipeMCPServer

# Alias for backwards compatibility
UnifiedMCPServer = RecipeMCPServer


def main():
    """Main entry point for the recipe MCP server."""
    server = RecipeMCPServer()
    server.run()


# Main entry point
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Start script for MealMCP server with mode selection.

Environment Variables:
- MCP_MODE: "local", "remote", or "oauth" (default: "local")
- MCP_TRANSPORT: "stdio" or "http" (default: "stdio")
- ADMIN_TOKEN: Admin token for remote mode (auto-generated if not set)
- ADDITIONAL_USERS: Comma-separated list of "username:token" pairs
- MCP_HOST: Host to bind to in HTTP mode (default: "localhost")
- MCP_PORT: Port to bind to in HTTP mode (default: 8000)
- CORS_ORIGINS: Comma-separated list of allowed CORS origins (default: "*")
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    mode = os.getenv("MCP_MODE", "local").lower()
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    print(f"Starting MealMCP server in {mode} mode with {transport} transport...")

    # HTTP transport mode
    if transport == "http":
        print("HTTP transport: Server accessible over HTTP/SSE")
        host = os.getenv("MCP_HOST", "localhost")
        port = os.getenv("MCP_PORT", "8000")
        print(f"Server will be available at: http://{host}:{port}")

        if mode == "oauth":
            print("OAuth mode: Multi-user with OAuth 2.1 authentication")
            print(f"Authorization endpoint: http://{host}:{port}/authorize")
            print(f"Token endpoint: http://{host}:{port}/token")
            print(
                f"Discovery: http://{host}:{port}/.well-known/oauth-authorization-server"
            )
            print("User databases will be stored in: user_data/")

            # Use OAuth/SSE server
            from mcp_oauth_sse import app
            import uvicorn

            uvicorn.run(app, host=host, port=int(port))

        elif mode == "remote":
            # Check for admin token
            admin_token = os.getenv("ADMIN_TOKEN")
            if not admin_token:
                import secrets

                admin_token = secrets.token_urlsafe(32)
                print(f"Generated admin token: {admin_token}")
                print("Set ADMIN_TOKEN environment variable to use this token")
            else:
                print("Using admin token from environment")

            # Show additional users if configured
            additional_users = os.getenv("ADDITIONAL_USERS")
            if additional_users:
                users = [user.split(":")[0] for user in additional_users.split(",")]
                print(f"Additional users configured: {users}")

            print("User databases will be stored in: user_data/")

            # Use HTTP server
            from mcp_server_http import run_server

            run_server()

        else:
            print("Local mode: Single user, no authentication required")
            print("Database: pantry.db")

            # Use HTTP server
            from mcp_server_http import run_server

            run_server()

    # Stdio transport mode (default)
    elif transport == "stdio":
        print("Stdio transport: For Claude Desktop integration")

        if mode == "local":
            print("Local mode: Single user, no authentication required")
            print("Database: pantry.db")
            # Use the multiuser server even for local mode - it handles both
            from mcp_server_multiuser import mcp

            mcp.run()

        elif mode == "oauth":
            print("OAuth mode: OAuth 2.1 authentication (stdio not supported)")
            print("Use MCP_TRANSPORT=http for OAuth mode")
            sys.exit(1)

        elif mode == "remote":
            print("Remote mode: Multi-user with authentication")

            # Check for admin token
            admin_token = os.getenv("ADMIN_TOKEN")
            if not admin_token:
                import secrets

                admin_token = secrets.token_urlsafe(32)
                print(f"Generated admin token: {admin_token}")
                print("Set ADMIN_TOKEN environment variable to use this token")
            else:
                print("Using admin token from environment")

            # Show additional users if configured
            additional_users = os.getenv("ADDITIONAL_USERS")
            if additional_users:
                users = [user.split(":")[0] for user in additional_users.split(",")]
                print(f"Additional users configured: {users}")

            print("User databases will be stored in: user_data/")

            from mcp_server_multiuser import mcp

            mcp.run()

        else:
            print(f"Invalid mode: {mode}. Use 'local', 'remote', or 'oauth'")
            sys.exit(1)

    else:
        print(f"Invalid transport: {transport}. Use 'stdio' or 'http'")
        sys.exit(1)


if __name__ == "__main__":
    main()

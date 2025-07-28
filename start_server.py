#!/usr/bin/env python3
"""
Start script for MealMCP server with mode selection.

Environment Variables:
- MCP_MODE: "local" or "remote" (default: "local")
- ADMIN_TOKEN: Admin token for remote mode (auto-generated if not set)
- ADDITIONAL_USERS: Comma-separated list of "username:token" pairs
- MCP_HOST: Host to bind to in remote mode (default: "localhost")
- MCP_PORT: Port to bind to in remote mode (default: 8000)
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    mode = os.getenv("MCP_MODE", "local").lower()
    
    print(f"Starting MealMCP server in {mode} mode...")
    
    if mode == "local":
        print("Local mode: Single user, no authentication required")
        print("Database: pantry.db")
        # Use the multiuser server even for local mode - it handles both
        from mcp_server_multiuser import mcp
        mcp.run()
        
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
        
        # In a real deployment, you'd use a proper ASGI server
        # For now, we'll use the built-in FastMCP server
        mcp.run()
        
    else:
        print(f"Invalid mode: {mode}. Use 'local' or 'remote'")
        sys.exit(1)

if __name__ == "__main__":
    main()
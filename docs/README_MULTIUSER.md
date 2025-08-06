# Multi-User MCP Server Setup

The MealMCP server now supports both single-user local mode and multi-user remote mode.

## Modes

### Local Mode (Default)
- Single user
- No authentication required
- Uses `pantry.db` database file
- Compatible with existing Claude Desktop configuration

### Remote Mode
- Multiple users with authentication
- Token-based authentication
- Each user gets isolated database in `user_data/` directory
- Admin functions for user management

## Configuration

### Environment Variables

- `MCP_MODE`: Set to "local" or "remote" (default: "local")
- `ADMIN_TOKEN`: Admin authentication token for remote mode
- `ADDITIONAL_USERS`: Comma-separated list of "username:token" pairs
- `MCP_LANG`: Language setting (default: "en")

### Local Mode Usage

**Claude Desktop Configuration (claude_desktop_config.json):**
```json
{
  "mcpServers": {
    "mealmcp": {
      "command": "uv",
      "args": [
        "--directory",
        "path/to/mealmcp",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

**Direct execution:**
```bash
# Default local mode
uv run mcp_server.py

# Or explicitly set local mode
MCP_MODE=local uv run mcp_server.py

# Using the start script
uv run start_server.py
```

### Remote Mode Usage

**Start server in remote mode:**
```bash
# Basic remote mode (generates admin token)
MCP_MODE=remote uv run start_server.py

# With predefined admin token
MCP_MODE=remote ADMIN_TOKEN=your-admin-token-here uv run start_server.py

# With additional users
MCP_MODE=remote ADMIN_TOKEN=admin-token ADDITIONAL_USERS="alice:alice-token,bob:bob-token" uv run start_server.py
```

**Claude Desktop Configuration for remote mode:**
```json
{
  "mcpServers": {
    "mealmcp": {
      "command": "python",
      "args": [
        "/path/to/mealmcp/mcp_server.py"
      ],
      "env": {
        "MCP_MODE": "remote",
        "USER_TOKEN": "your-user-token-here"
      }
    }
  }
}
```

## Authentication

### In Local Mode
- No authentication required
- All MCP tools work without token parameter

### In Remote Mode
- All MCP tools require a `token` parameter
- Use your user token for authentication
- Admin functions require the admin token

## User Management

### Admin Functions

**Create a new user:**
```python
create_user("username", "admin-token")
# Returns: {"status": "success", "token": "new-user-token", "username": "username"}
```

**List all users:**
```python
list_users("admin-token")
# Returns: {"status": "success", "users": ["admin", "alice", "bob"]}
```

## Database Structure

### Local Mode
- Single database: `pantry.db`

### Remote Mode
```
user_data/
├── admin/
│   └── pantry.db
├── alice/
│   └── pantry.db
└── bob/
    └── pantry.db
```

## Security Considerations

1. **Token Security**: Store tokens securely, don't commit them to version control
2. **Admin Access**: The admin token has full access to create users and list all users
3. **User Isolation**: Each user's data is completely isolated in separate databases
4. **Network Security**: In production, use HTTPS and proper network security

## Migration from Single-User

Existing single-user installations will continue to work without changes. The multiuser server is backwards compatible and defaults to local mode.

To migrate existing data to a specific user in remote mode:
1. Start in remote mode
2. Create a user account
3. Copy your existing `pantry.db` to `user_data/{username}/pantry.db`

## Troubleshooting

**Authentication errors:**
- Verify your token is correct
- Check that MCP_MODE is set properly
- Ensure token parameter is included in all tool calls for remote mode

**Database issues:**
- Check file permissions on `user_data/` directory
- Verify database files exist and are readable
- Check disk space for database creation

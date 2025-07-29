# MCP Server Testing Guide

This guide shows you different ways to test your MealMCP server to ensure it's working correctly.

## 1. Direct Function Testing (Easiest)

The simplest way to test is to run the functions directly:

```bash
# Run all tests using the test runner
uv run python tests/run_tests.py all

# Or run specific test suites
uv run python tests/run_tests.py direct       # Direct function tests
uv run python tests/run_tests.py scenarios   # End-to-end workflow tests
uv run python tests/run_tests.py quick       # Quick automated tests
uv run python tests/run_tests.py interactive # Interactive menu testing
```

This will test both local and remote modes and show you exactly what's happening.

## 2. Claude Desktop Integration

### Local Mode (Single User)

1. **Add to Claude Desktop config** (`~/AppData/Roaming/Claude/claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

You can copy the example config from `tests/configs/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mealmcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/MealMCP",
        "run",
        "mcp_server.py"
      ]
    }
  }
}
```

2. **Restart Claude Desktop**

3. **Test in Claude Desktop** by asking:
   - "What food preferences do I have?"
   - "Add a new dietary preference for vegetarian as required"
   - "Show me all my recipes"
   - "What's in my pantry?"

### Remote Mode (Multi-User)

1. **Start the server in remote mode:**
```bash
MCP_MODE=remote ADMIN_TOKEN=your-secret-token uv run mcp_server.py
```

2. **Update Claude Desktop config:**

You can copy the example config from `tests/configs/claude_desktop_config_remote.json`:

```json
{
  "mcpServers": {
    "mealmcp-remote": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/MealMCP", 
        "run",
        "mcp_server.py"
      ],
      "env": {
        "MCP_MODE": "remote",
        "USER_TOKEN": "your-user-token-here"
      }
    }
  }
}
```

3. **Create users via Claude Desktop:**
   - "Create a new user called 'alice' using admin token 'your-secret-token'"
   - "List all users using admin token 'your-secret-token'"

## 3. Manual MCP Protocol Testing

You can test the MCP protocol directly using stdio:

```bash
# Start the server and send JSON-RPC commands
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | uv run python mcp_server.py
```

## 4. Interactive Testing

For hands-on testing, use the interactive test mode:

```bash
uv run python tests/run_tests.py interactive
```

This gives you a menu to test different functions.

## 5. Debugging Tips

### Check Server Logs
```bash
# Run with debugging output
DEBUG=1 uv run python mcp_server.py
```

### Test Database Access
```bash
# Check if database exists and has data
sqlite3 pantry.db ".tables"
sqlite3 pantry.db "SELECT * FROM Preferences LIMIT 5;"
```

### Verify Environment Variables
```bash
# For remote mode
echo $MCP_MODE
echo $ADMIN_TOKEN
```

### Test Network Connectivity (Remote Mode)
```bash
# If running as a network service
curl -X POST http://localhost:8000/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## 6. Common Issues and Solutions

### "Authentication required" errors
- **Local mode**: Make sure MCP_MODE is not set to "remote"
- **Remote mode**: Ensure you're passing the correct token parameter

### "Module not found" errors
- Run `uv sync` to install dependencies
- Make sure you're in the correct directory

### "Database locked" errors  
- Close any other connections to the database
- Restart the server

### Claude Desktop doesn't see the server
- Check the config file path and syntax
- Restart Claude Desktop after config changes
- Check Claude Desktop's MCP server logs

## 7. Performance Testing

For load testing with multiple users:

```bash
# Create multiple test users
for i in {1..10}; do
  python3 -c "
import sys
sys.path.insert(0, '.')
from mcp_server import create_user
result = create_user('user$i', 'your-admin-token')
print(f'Created user$i: {result}')
"
done
```

## 8. Example Test Scenarios

### Recipe Management Flow
1. List all recipes (should be empty initially)
2. Add a simple recipe
3. List recipes again (should show your recipe)
4. Get the specific recipe details
5. Edit the recipe
6. Execute the recipe (remove ingredients from pantry)

### Pantry Management Flow  
1. Check pantry contents (should be empty initially)
2. Add some ingredients
3. Check pantry contents again
4. Remove some ingredients
5. Check transaction history

### Meal Planning Flow
1. Add a few recipes
2. Set recipes for specific dates
3. Get the week's meal plan
4. Generate a grocery list

### Multi-User Flow (Remote Mode)
1. Create admin user
2. Create regular users
3. Test user isolation (each user should see only their own data)
4. Test admin functions (list users, create users)

## Next Steps

Once you've verified the server works:

1. **Deploy to production** using proper authentication
2. **Add SSL/TLS** for secure remote access  
3. **Set up monitoring** and logging
4. **Create backups** of user databases
5. **Scale horizontally** if needed

Happy testing! 🧪
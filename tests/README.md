# MealMCP Test Suite

This directory contains comprehensive tests for the MealMCP server in both local and remote modes.

## Test Structure

```
tests/
├── run_tests.py                    # Main test runner
├── configs/                        # Configuration files
│   ├── claude_desktop_config.json      # Local mode Claude Desktop config
│   └── claude_desktop_config_remote.json # Remote mode Claude Desktop config
├── mcp_tests/                      # MCP-specific tests
│   ├── test_direct_functions.py        # Direct function testing
│   ├── test_interactive.py             # Interactive menu testing
│   └── test_scenarios.py               # End-to-end workflow tests
└── test_pantry_manager.py          # Unit tests for PantryManager class
```

## Quick Start

```bash
# Run all automated tests
uv run python tests/run_tests.py all

# Show available test commands
uv run python tests/run_tests.py help
```

## Test Types

### 1. Direct Function Tests
Tests MCP server functions directly without going through the protocol layer.
```bash
uv run python tests/run_tests.py direct
```

### 2. End-to-End Scenario Tests
Tests complete workflows like recipe management, pantry operations, and meal planning.
```bash
uv run python tests/run_tests.py scenarios
```

### 3. Interactive Tests
Menu-driven testing for manual exploration and debugging.
```bash
uv run python tests/run_tests.py interactive
```

### 4. Quick Tests
Fast automated tests for basic functionality.
```bash
uv run python tests/run_tests.py quick
```

### 5. Unit Tests
Traditional pytest-based unit tests.
```bash
uv run python tests/run_tests.py pytest
```

## Individual Test Files

You can also run test files directly:

```bash
# Direct function testing
uv run python tests/mcp_tests/test_direct_functions.py

# Interactive testing with menu
uv run python tests/mcp_tests/test_interactive.py interactive

# End-to-end scenarios
uv run python tests/mcp_tests/test_scenarios.py
```

## Configuration Files

The `configs/` directory contains ready-to-use Claude Desktop configuration files:

- `claude_desktop_config.json` - Local mode (single user, no auth)
- `claude_desktop_config_remote.json` - Remote mode (multi-user with tokens)

Copy these to your Claude Desktop configuration directory and update the paths.

## Testing Both Modes

### Local Mode (Default)
All tests run in local mode by default. No authentication required.

### Remote Mode
Set environment variables to test remote mode:
```bash
MCP_MODE=remote ADMIN_TOKEN=test-token uv run python tests/run_tests.py all
```

Or use the dedicated remote mode test:
```bash
uv run python tests/mcp_tests/test_interactive.py remote
```

## Common Test Scenarios

### Recipe Management
1. Add a recipe
2. List all recipes
3. Get specific recipe details
4. Edit a recipe
5. Execute a recipe (remove ingredients from pantry)

### Pantry Management
1. Add items to pantry
2. Check pantry contents
3. Remove items from pantry
4. View transaction history

### Meal Planning
1. Set recipes for specific dates
2. Get weekly meal plan
3. Generate grocery list based on planned meals

### User Management (Remote Mode)
1. Create new users
2. Test user isolation
3. Admin functions

## Troubleshooting

### Common Issues

**Import Errors**: Make sure you're running from the project root directory.

**Authentication Errors**: 
- Local mode: Ensure MCP_MODE is not set to "remote"
- Remote mode: Provide valid tokens

**Database Issues**: Tests use temporary databases, but check file permissions if issues persist.

### Debug Mode
Add debug output to any test by modifying the print statements or adding logging.

## Adding New Tests

1. **Unit Tests**: Add to `test_pantry_manager.py`
2. **MCP Function Tests**: Add to `test_direct_functions.py`
3. **Workflow Tests**: Add to `test_scenarios.py`
4. **Interactive Tests**: Add options to `test_interactive.py`

Follow the existing patterns and ensure proper error handling.
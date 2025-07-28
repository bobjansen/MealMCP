# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
- **Web Interface**: `uv run app.py` - Starts the Dash web interface on http://localhost:8050
- **MCP Server (Local)**: `uv run mcp_server.py` - Starts the MCP server in single-user local mode
- **MCP Server (Remote)**: `MCP_MODE=remote uv run mcp_server.py` - Starts the MCP server in multi-user remote mode
- **MCP Server (Start Script)**: `uv run start_server.py` - Starts server with mode selection and configuration

### Testing
- **Run Tests**: `pytest` or `uv run pytest` - Runs the test suite located in the `tests/` directory
- **Single Test**: `pytest tests/test_pantry_manager.py` - Run a specific test file

### Environment Setup
- **Install Dependencies**: `uv sync` - Installs all project dependencies
- **Database Setup**: The database is automatically initialized when the PantryManager class is first instantiated

## Architecture Overview

### Core Components

**PantryManager (`pantry_manager.py`)**
- Central business logic class that handles all database operations
- Manages ingredients, recipes, pantry inventory, preferences, and meal planning
- Uses SQLite with `pantry.db` as the default database file
- All database interactions go through this class for consistency

**MCP Server (`mcp_server.py`)**
- FastMCP-based server providing tools for Claude Desktop integration
- Supports both single-user local mode and multi-user remote mode
- Exposes pantry management functions as MCP tools with optional authentication
- Key tools include: `list_units()`, `add_preference()`, `list_recipes()`, `add_recipe()`, `plan_meals()`
- Uses `MCPContext` for user management and `UserManager` for authentication
- In local mode: single `PantryManager` instance, no authentication
- In remote mode: per-user `PantryManager` instances with token-based authentication

**Dash Web App (`app.py`)**
- Multi-tab web interface built with Dash and Bootstrap components
- Tabs: Preferences, Pantry Management, Recipes, Meal Planner
- Uses callback-driven architecture with `@app.callback` decorators
- Shares the same `PantryManager` instance with the MCP server

### Database Schema
- **Ingredients**: Base ingredients with default units
- **PantryTransactions**: Track additions/removals from pantry with timestamps
- **Recipes**: Store recipe details with JSON ingredients field
- **Preferences**: Food preferences with categories (dietary, allergy, dislike, like)
- **MealPlans**: Planned meals with dates and recipe associations

### Key Files
- `constants.py`: Defines `UNITS` list for measurement units
- `db_setup.py`: Database schema creation and initialization
- `i18n.py`: Internationalization support (English/Dutch) with environment variable `MCP_LANG`
- `user_manager.py`: User authentication and database isolation for multi-user mode
- `mcp_context.py`: Context management for user sessions and PantryManager instances
- `start_server.py`: Server startup script with mode selection and configuration

## Development Guidelines

### Adding New Features
- All database operations should go through `PantryManager` methods
- Both web interface and MCP server should use the same business logic
- Add appropriate error handling and return boolean success indicators
- Include unit tests in the `tests/` directory

### Database Changes
- Modify `db_setup.py` for schema changes
- Update `PantryManager` methods accordingly
- Test with both interfaces (web and MCP)

### MCP Tool Development
- New MCP tools should be added to `mcp_server.py` using `@mcp.tool()` decorator
- All tools must include optional `token: Optional[str] = None` parameter for authentication
- Use `get_user_pantry(token)` helper to authenticate and get user's PantryManager instance
- Return `{"status": "error", "message": "Authentication required"}` if authentication fails
- Follow the existing pattern: authenticate, call `PantryManager` methods, return structured data
- Include proper type hints and docstrings

### Web Interface Development
- New web components go in `app.py`
- Use Bootstrap components from `dash_bootstrap_components`
- Follow the existing callback pattern with proper Input/Output/State decorators
- Support internationalization using `i18n.t()` function
- Web interface only supports local mode (single user)

### Multi-User Mode Configuration
- Set `MCP_MODE=remote` environment variable to enable multi-user mode
- Use `ADMIN_TOKEN` environment variable to set admin authentication token
- User databases are stored in `user_data/{username}/pantry.db`
- Tokens should be kept secure and not committed to version control
- See `README_MULTIUSER.md` for detailed setup instructions
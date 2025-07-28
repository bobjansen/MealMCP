# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
- **Web Interface**: `uv run app.py` - Starts the Dash web interface on http://localhost:8050
- **MCP Server**: `uv run mcp_server.py` - Starts the Model Context Protocol server for Claude Desktop integration

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
- Exposes pantry management functions as MCP tools
- Key tools include: `list_units()`, `add_preference()`, `list_recipes()`, `add_recipe()`, `plan_meals()`
- Instantiates a single `PantryManager` instance at startup

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
- Follow the existing pattern: accept parameters, call `PantryManager` methods, return structured data
- Include proper type hints and docstrings

### Web Interface Development
- New web components go in `app.py`
- Use Bootstrap components from `dash_bootstrap_components`
- Follow the existing callback pattern with proper Input/Output/State decorators
- Support internationalization using `i18n.t()` function
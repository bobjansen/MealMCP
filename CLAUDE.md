# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the Application
- **Flask Web Interface (Recommended)**: `uv run run_web.py` - Smart launcher with backend detection and validation
- **Flask Web Interface (Direct)**: `uv run app_flask.py` - Direct Flask app startup on http://localhost:5000
- **Unified MCP Server (Recommended)**: `uv run run_mcp.py [mode]` - Single server supporting all transport modes
  - `uv run run_mcp.py` - FastMCP local mode (default)
  - `uv run run_mcp.py http --port 8080` - HTTP REST API server
  - `uv run run_mcp.py oauth --multiuser` - OAuth 2.1 multi-user server
  - `uv run run_mcp.py sse` - Server-Sent Events server

### Testing
- **Run All Tests**: `pytest` or `uv run pytest` - Runs all tests (both recipe-specific and MCP core tests)
- **Run Recipe Tests Only**: `pytest tests/` - Runs recipe-specific tests in the `tests/` directory
- **Run MCP Core Tests Only**: `pytest mcp_core/tests/` - Runs generic MCP tests in the `mcp_core/tests/` directory
- **Single Test**: `pytest tests/test_pantry_manager.py` - Run a specific test file

#### Test Organization
- **`tests/`** - Recipe and pantry management specific tests (e.g., `test_pantry_manager.py`, `test_mcp_integration.py`)
- **`mcp_core/tests/`** - Generic MCP server tests (e.g., `test_mcp_transport_modes.py`, `test_mcp_server_startup.py`)

### Environment Setup
- **Install Dependencies**: `uv sync` - Installs all project dependencies
- **Database Setup**: Database is automatically initialized when PantryManager instances are created through the factory
- **PostgreSQL Setup**: Install with `pip install psycopg2-binary` and ensure PostgreSQL server is running
- **Flask Configuration**: Set `FLASK_SECRET_KEY` environment variable for production use

## Architecture Overview

### Core Components

**PantryManager Interface**
- Abstract interface defined in `pantry_manager_abc.py` that standardizes pantry management operations
- Two implementations: `SQLitePantryManager` (single-user) and `SharedPantryManager` (multi-user)
- Single-user: Created through `PantryManagerFactory` for local SQLite scenarios
- Multi-user: `SharedPantryManager` used directly for PostgreSQL with user_id scoping
- Manages ingredients, recipes, pantry inventory, preferences, and meal planning
- All database interactions go through concrete implementations for consistency

**MCP Server (`mcp_server.py`)**
- FastMCP-based server providing tools for Claude Desktop integration
- Supports both single-user local mode and multi-user remote mode
- Exposes pantry management functions as MCP tools with optional authentication
- Key tools include: `get_user_profile()`, `add_preference()`, `get_all_recipes()`, `add_recipe()`, `manage_pantry_item()`, `get_week_plan()`, `set_recipe_for_date()`
- Uses `MCPContext` for user management and `UserManager` for authentication
- In local mode: single `PantryManager` instance, no authentication
- In remote mode: per-user `PantryManager` instances with token-based authentication

**Flask Web App (`app_flask.py`)**
- Modern Flask-based web interface with Bootstrap styling
- Multi-user authentication support when using PostgreSQL backend
- Single-user mode when using SQLite backend (no authentication required)
- Routes: Preferences, Pantry Management, Recipes, Meal Planning, User Authentication
- Uses `SharedPantryManager` for user data isolation in PostgreSQL mode
- Includes authentication decorators and session management

**Legacy Dash Web App (`app.py`)**
- Original multi-tab interface built with Dash and Bootstrap components
- Single-user only, no authentication support
- Uses callback-driven architecture with `@app.callback` decorators

### Database Schema

**Shared Database Schema (PostgreSQL Multi-User)**:
- **Users**: User accounts with authentication (username, email, password_hash)
- **Ingredients**: Base ingredients with default units (scoped by user_id)
- **PantryTransactions**: Track additions/removals from pantry with timestamps (scoped by user_id)
- **Recipes**: Store recipe details with separate recipe_ingredients table (scoped by user_id)
- **RecipeIngredients**: Junction table linking recipes to ingredients with quantities
- **Preferences**: Food preferences with categories (scoped by user_id)
- **MealPlans**: Planned meals with dates and recipe associations (scoped by user_id)

**SQLite Schema (Single-User)**:
- Same structure as above but without user_id scoping or Users table

### Key Files
- `constants.py`: Defines `UNITS` list for measurement units
- `pantry_manager_abc.py`: Abstract base class defining the PantryManager interface
- `pantry_manager_sqlite.py`: SQLite implementation of PantryManager (single-user local mode)
- `pantry_manager_shared.py`: SharedPantryManager implementation for multi-user PostgreSQL with user_id scoping
- `pantry_manager_factory.py`: Factory class for creating single-user SQLite PantryManager instances
- `db_setup.py`: SQLite database schema creation for single-user mode
- `db_setup_shared.py`: PostgreSQL database schema with user_id scoping for multi-user mode
- `web_auth_simple.py`: Simple user authentication system for Flask web interface
- `app_flask.py`: Main Flask web application with multi-user support
- `run_web.py`: Smart web application launcher with backend detection and validation
- `i18n.py`: Internationalization support (English/Dutch) with environment variable `MCP_LANG`
- `user_manager.py`: User authentication and database isolation for multi-user MCP mode
- `mcp_context.py`: Context management for user sessions and PantryManager instances
- `start_server.py`: Server startup script with mode selection and configuration

## Development Guidelines

### Adding New Features
- All database operations should go through `PantryManager` methods
- Both web interface and MCP server should use the same business logic
- Add appropriate error handling and return boolean success indicators
- Include unit tests in the `tests/` directory

### Database Changes
- **For SQLite (single-user)**: Modify `db_setup.py` for schema changes
- **For PostgreSQL (multi-user)**: Modify `db_setup_shared.py` for schema changes
- Update corresponding PantryManager implementations (`SQLitePantryManager` and `SharedPantryManager`)
- Test with both database backends and both interfaces (web and MCP)

### Database Backend Configuration
- **Default**: Uses SQLite with automatic backend detection
- **Environment Variables**:
  - `PANTRY_BACKEND`: Set to 'sqlite' or 'postgresql' (default: 'sqlite')
  - `PANTRY_DB_PATH`: SQLite database file path (default: 'pantry.db')
  - `PANTRY_DATABASE_URL`: PostgreSQL connection string
  - `FLASK_SECRET_KEY`: Flask session secret key (auto-generated if not set)
- **Usage**: `create_pantry_manager(backend='postgresql', connection_string='postgresql://...')`
- **Factory Methods**: `PantryManagerFactory.from_environment()` or `PantryManagerFactory.from_config()`

### Web Interface Modes
- **SQLite Mode**: Single-user, no authentication required, uses `SQLitePantryManager`
- **PostgreSQL Mode**: Multi-user with authentication, uses `SharedPantryManager` with user_id scoping
- **Backend Detection**: Automatic based on `PANTRY_BACKEND` environment variable

### MCP Tool Development
- New MCP tools should be added in two places:
  1. **Tool Definition**: Add to `mcp_tools.py` with proper schema definition
  2. **Tool Implementation**: Add to `mcp_tool_router.py` with actual implementation
- Authentication is handled at the server level, not in individual tool parameters
- The server provides the appropriate authenticated `pantry_manager` instance to the tool router
- Tools don't need to handle authentication directly - they receive a pre-authenticated manager
- Follow the existing pattern: authenticate, call `PantryManager` methods, return structured data
- Include proper type hints and docstrings
- **Important**: Ensure tools are registered in BOTH `mcp_tools.py` (for exposure) AND `mcp_tool_router.py` (for implementation)

### Available MCP Tools
The following tools are currently available through the MCP interface (as defined in `mcp_tools.py`):

**Utilities:**
- `list_units()`: List all available units of measurement

**User Profile & Preferences:**
- `get_user_profile()`: Get comprehensive user profile including preferences, household size, and constraints
- `add_preference(category, item, level, notes?)`: Add food preference (like/dislike/allergy/dietary)
- `get_food_preferences()`: Get all food preferences

**Recipe Management:**
- `add_recipe(name, instructions, time_minutes, ingredients)`: Add a new recipe to the database
- `get_recipe(recipe_name)`: Get detailed information about a specific recipe
- `get_all_recipes()`: Get all recipes with basic information
- `edit_recipe(recipe_name, field, new_value)`: Edit an existing recipe
- `execute_recipe(recipe_name)`: Execute recipe by removing required ingredients from pantry

**Recipe Analysis:**
- `search_recipes(query?, max_prep_time?, min_rating?)`: Search recipes with filters
- `suggest_recipes_from_pantry()`: Suggest recipes based on available pantry items
- `check_recipe_feasibility(recipe_name)`: Check if a recipe can be made with current pantry items

**Pantry Management:**
- `get_pantry_contents()`: Get current pantry inventory
- `manage_pantry_item(action, item_name, quantity, unit)`: Add or remove items from pantry (unified)
- `add_pantry_item(item_name, quantity, unit, notes?)`: Add an item to the pantry (individual)
- `remove_pantry_item(item_name, quantity, unit)`: Remove an item from the pantry (individual)

**Meal Planning:**
- `get_week_plan()`: Get meal plan for the next 7 days
- `get_meal_plan(start_date, days?)`: Get meal plan for specified period
- `plan_meals(meal_assignments)`: Plan meals for specified dates
- `set_recipe_for_date(meal_date, recipe_name)`: Set a recipe for a specific date
- `clear_meal_plan(start_date, end_date)`: Clear meal plan for specified date range

**Grocery Management:**
- `get_grocery_list()`: Get grocery items needed for the coming week's meal plan
- `generate_grocery_list(start_date?, days?)`: Generate grocery list for upcoming meal plan

**Short ID-Based Recipe Editing:**
- `edit_recipe_by_id(recipe_id, name?, instructions?, time_minutes?, ingredients?)`: Edit recipes by short ID with partial updates and detailed error messages
- `get_recipe_id(recipe_name)`: Get a recipe's short ID by name for precise editing
- Short IDs are human-friendly (e.g., R123A, R456B) with checksums to prevent typos
- All recipe operations support both short IDs and UUIDs for maximum precision

**Note:** Authentication is handled automatically at the server level based on the configured mode (local, remote, or OAuth multiuser).

### Flask Web Interface Development
- New routes and components go in `app_flask.py`
- Use `@requires_auth` decorator for routes that need authentication in PostgreSQL mode
- Use `get_current_user_pantry()` to get user-scoped PantryManager instance
- All routes must handle both SQLite (no auth) and PostgreSQL (with auth) modes
- Templates receive global variables: `backend`, `requires_auth`, `current_user`
- Follow Flask patterns with `flash()` messages and `redirect()` responses
- Support internationalization using `i18n.t()` function

### Multi-User Mode Configuration

**Flask Web Interface Multi-User Setup**:
- Set `PANTRY_BACKEND=postgresql` to enable PostgreSQL backend
- Set `PANTRY_DATABASE_URL=postgresql://user:pass@host:port/database`
- Users can register accounts through the web interface
- All user data is isolated using user_id scoping in shared database
- Uses `SharedPantryManager` for user data isolation

**MCP Server Multi-User Setup**:
- Set `MCP_MODE=remote` environment variable to enable multi-user mode
- Use `ADMIN_TOKEN` environment variable to set admin authentication token
- User databases are stored in `user_data/{username}/pantry.db`
- Tokens should be kept secure and not committed to version control
- See `README_MULTIUSER.md` for detailed setup instructions

### OAuth Token Persistence
To prevent Claude Desktop from needing to re-authenticate after server restarts:

1. **Database Persistence** (Automatic): Tokens are now stored in the database and restored on startup
2. **Extended Token Expiry**: Set `OAUTH_TOKEN_EXPIRY=86400` (24 hours) or longer
3. **Token Cleanup**: Run `uv run python cleanup_tokens.py` to remove expired tokens

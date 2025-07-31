# MealMCP: Intelligent Meal Planning and Pantry Management

MealMCP is a sophisticated meal planning and pantry management system that leverages Large Language Models (LLMs) for business logic. The application provides multiple interfaces: a Model Context Protocol (MCP) server for integration with Claude Desktop client, a modern Flask web interface with multi-user authentication support, and a legacy Dash web interface for direct user interaction.

![MealMCP Interface](example.png)

## Features

- 🧾 Recipe Management
- 🥘 Meal Planning
- 🗄️ Pantry Inventory Tracking
- 📊 Interactive Web Dashboard (Flask & Dash)
- 👥 Multi-User Authentication (PostgreSQL mode)
- 🔐 Single-User Local Mode (SQLite mode)
- 🤖 LLM-powered Intelligence
- 🔄 Multiple Interface Options
- 🏢 Production-Ready Architecture

## Architecture

### Data Storage
- **SQLite Mode**: Single-user local database (`pantry.db`) for personal use
- **PostgreSQL Mode**: Multi-user shared database with user isolation via user_id scoping
- Database agnostic design with multiple PantryManager implementations
- Automatic backend detection and configuration
- User data isolation in multi-user scenarios

### Components

#### 1. MCP Server (`mcp_server.py`)
The Model Context Protocol server provides an interface for Claude Desktop client integration with features including:
- Unit management
- Preference handling
- Recipe operations
- Pantry management
- Meal planning capabilities

#### 2. Flask Web Application (`app_flask.py`) - **Primary Interface**
A modern Flask-based web interface offering:
- **Multi-User Authentication**: User registration, login, and session management
- **Backend Mode Detection**: Automatic SQLite (single-user) or PostgreSQL (multi-user) configuration
- **Complete Feature Set**: Recipe management, pantry inventory, meal planning
- **Responsive Design**: Bootstrap-styled responsive interface
- **Smart Launcher**: `run_web.py` with backend validation and helpful startup messages
- **User Data Isolation**: Secure separation of user data in multi-user mode

#### 3. Legacy Dash Web Application (`app.py`)
Original web interface built with Dash offering:
- Interactive recipe management
- Visual pantry inventory
- Recipe formatting and display
- User-friendly forms and tables
- Single-user mode only

#### 4. Pantry Manager System
Multiple implementations for different use cases:

**`SQLitePantryManager`**: Single-user SQLite backend
**`PostgreSQLPantryManager`**: Single-user PostgreSQL backend  
**`SharedPantryManager`**: Multi-user PostgreSQL with user_id scoping

Core business logic handling:
- Ingredient management
- Recipe CRUD operations
- Pantry inventory tracking
- User preference management
- Meal planning and grocery lists
- Data persistence with proper user isolation

## Setup and Installation

### Prerequisites
- Python 3.8+ and uv package manager
- **For PostgreSQL mode**: PostgreSQL server and `psycopg2-binary`

### Basic Setup
1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync
   ```

### PostgreSQL Setup (Multi-User Mode)
For production multi-user deployment:

1. Install PostgreSQL and create a database:
   ```bash
   pip install psycopg2-binary
   createdb meal_manager
   ```

2. Set environment variables:
   ```bash
   export PANTRY_BACKEND=postgresql
   export PANTRY_DATABASE_URL=postgresql://username:password@localhost:5432/meal_manager
   export FLASK_SECRET_KEY=your-secure-secret-key
   ```

## Usage

### Running the Flask Web Interface (Recommended)

**Quick Start (SQLite - Single User):**
```bash
python run_web.py
```
Access at `http://localhost:5000` - No login required

**Multi-User Mode (PostgreSQL):**
```bash
export PANTRY_BACKEND=postgresql
export PANTRY_DATABASE_URL=postgresql://user:pass@host:5432/meal_manager
python run_web.py
```
Access at `http://localhost:5000` - Registration/login required

**Direct Flask Startup:**
```bash
python app_flask.py
```

### Running the Legacy Dash Interface
```bash
uv run app.py
```
Access the web interface at `http://localhost:8050` (Single-user only)

### Using the MCP Server

**Local Mode (Single User):**
Put this in your Claude Desktop config (`claude_desktop_config.json`):
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

**Remote Mode (Multi-User):**
```bash
export MCP_MODE=remote
export ADMIN_TOKEN=your-secure-admin-token
uv run mcp_server.py
```

Connect using Claude Desktop client or any MCP-compatible client.

## Data Structure

### SQLite Mode (Single-User)
Uses local `pantry.db` file with tables for:
- Ingredients
- Recipes and RecipeIngredients
- PantryTransactions (inventory tracking)
- Preferences
- MealPlans

### PostgreSQL Mode (Multi-User)
Shared database with user isolation:
- **Users**: Authentication and account management
- **All other tables**: Include `user_id` foreign keys for data isolation
- **Automatic Setup**: Database schema created automatically on first run

## Configuration Options

### Environment Variables
- `PANTRY_BACKEND`: `sqlite` (default) or `postgresql`
- `PANTRY_DATABASE_URL`: PostgreSQL connection string
- `FLASK_SECRET_KEY`: Flask session encryption key
- `MCP_MODE`: `local` (default) or `remote` for MCP server

### Backend Mode Comparison

| Feature | SQLite Mode | PostgreSQL Mode |
|---------|-------------|------------------|
| Users | Single | Multiple with authentication |
| Database | Local file | Shared server database |
| Authentication | None | Required (registration/login) |
| Deployment | Personal use | Production ready |
| Data Isolation | N/A | Automatic via user_id |

## Security Features

- **Password Security**: Werkzeug password hashing
- **Session Management**: Flask secure sessions
- **Data Isolation**: User-scoped database queries
- **SQL Injection Protection**: Parameterized queries throughout
- **XSS Protection**: Proper template escaping

## Development

### Testing
```bash
pytest
# or
uv run pytest
```

### Development Guidelines
See [CLAUDE.md](CLAUDE.md) for detailed development instructions including:
- Adding new features
- Database schema changes
- Multi-user considerations
- MCP tool development

## Deployment

### Local Development
Use SQLite mode with `python run_web.py`

### Production Deployment
1. Set up PostgreSQL database
2. Configure environment variables
3. Use a production WSGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app_flask:app
   ```

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

See the [LICENSE.txt](LICENSE.txt) file for details.

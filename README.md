# MealMCP: Intelligent Meal Planning and Pantry Management

MealMCP is a sophisticated meal planning and pantry management system that leverages Large Language Models (LLMs) for business logic. The application provides two interfaces: a Model Context Protocol (MCP) server for integration with Claude Desktop client and a Dash web interface for direct user interaction.

## Features

- 🧾 Recipe Management
- 🥘 Meal Planning
- 🗄️ Pantry Inventory Tracking
- 📊 Interactive Web Dashboard
- 🤖 LLM-powered Intelligence
- 🔄 Multiple Interface Options

## Architecture

### Data Storage
- SQLite database for storing recipes, ingredients, and pantry information
- Database agnostic design allows for future storage backend changes
- Managed through the `PantryManager` class for consistent data access

### Components

#### 1. MCP Server (`mcp_server.py`)
The Model Context Protocol server provides an interface for Claude Desktop client integration with features including:
- Unit management
- Preference handling
- Recipe operations
- Pantry management
- Meal planning capabilities

#### 2. Dash Web Application (`app.py`)
A web-based user interface built with Dash offering:
- Interactive recipe management
- Visual pantry inventory
- Recipe formatting and display
- User-friendly forms and tables
- Bootstrap-styled components for modern UI

#### 3. Pantry Manager (`pantry_manager.py`)
Core business logic handling:
- Ingredient management
- Recipe CRUD operations
- Pantry inventory tracking
- Data persistence
- Business rule enforcement

## Setup and Installation

1. Ensure Python and uv are installed on your system
2. Clone this repository
3. Install dependencies using `uv`:
   ```
   uv sync
   ```

## Usage

### Running the Dash Web Interface
```bash
uv run app.py
```
Access the web interface through your browser at `http://localhost:8050`

### Using the MCP Server
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
  },
  "isUsingBuiltInNodeForMcp": true
}
```
Connect to the MCP server using Claude Desktop client or any MCP-compatible client.

## Data Structure

The system uses a SQLite database (`pantry.db`) with tables for:
- Ingredients
- Recipes
- Pantry inventory
- User preferences
- Measurement units

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

See the [LICENSE.txt](LICENSE.txt) file for details.

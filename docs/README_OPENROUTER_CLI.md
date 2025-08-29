# OpenRouter CLI for MealMCP

This CLI provides an interactive interface to your meal planning and pantry management system using various LLM models through OpenRouter.

## Features

- **🤖 Multiple LLM Support**: Access to 30+ models via OpenRouter (Claude, GPT-4, Gemini, Llama, etc.)
- **🔧 29 MCP Tools**: Full access to all meal planning, pantry management, and recipe tools
- **💬 Conversation History**: Maintains context across the conversation
- **🎨 Rich Interface**: Beautiful terminal interface with tables, panels, and formatted output
- **🔄 Function Calling**: Seamless tool execution with result integration
- **📊 Multi-backend**: Supports both SQLite (single-user) and PostgreSQL (multi-user)

## Quick Start

### 1. Get an OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up and get your API key
3. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY=your_api_key_here
   ```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Run the CLI

```bash
# Simple start with SQLite backend
uv run openrouter_cli.py

# Or run directly
uv run openrouter_cli.py --model anthropic/claude-3.5-sonnet

# With PostgreSQL backend
PANTRY_BACKEND=postgresql PANTRY_DATABASE_URL=postgresql://user:pass@host/db uv run openrouter_cli.py
```

## Available Commands

Once in the CLI, you can use these commands:

- `/help` - Show available commands
- `/models` - List popular OpenRouter models
- `/tools` - Show available MCP tools
- `/reset` - Reset conversation history
- `/history` - Show recent conversation
- `/model <name>` - Change the current model
- `quit`, `exit`, or `q` - Exit the CLI

## Example Usage

```
🤖 You: I want to plan meals for this week. What recipes do I have available?

🤖 Assistant: I'll help you plan meals for this week! Let me first check what recipes you have available.

🔧 Executing tool: get_all_recipes
Arguments: {}

Based on your available recipes, here are your options:
- Spaghetti Carbonara (15 min, Rating: 4/5)
- Chicken Stir Fry (20 min, Rating: 5/5)
- Vegetable Curry (30 min, Rating: 4/5)

Would you like me to suggest a weekly meal plan using these recipes?

🤖 You: Yes, please create a plan for the next 7 days

🤖 Assistant: I'll create a balanced meal plan for the next 7 days using your available recipes...

🔧 Executing tool: plan_meals
Arguments: {"meal_assignments": [...]}

Perfect! I've planned your meals for the next week. Here's your schedule:
- Monday: Chicken Stir Fry
- Tuesday: Spaghetti Carbonara
- Wednesday: Vegetable Curry
...

Would you like me to generate a grocery list for these meals?
```

## Available MCP Tools

The CLI provides access to all 29 MCP tools:

### Recipe Management
- `add_recipe` - Add new recipes with ingredients
- `get_recipe` - Get detailed recipe information
- `get_all_recipes` - List all available recipes
- `edit_recipe` - Modify existing recipes
- `search_recipes` - Search recipes with filters
- `suggest_recipes_from_pantry` - Recipe suggestions based on available ingredients

### Pantry Management
- `get_pantry_contents` - View current pantry inventory
- `manage_pantry_item` - Add or remove pantry items
- `add_pantry_item` / `remove_pantry_item` - Individual pantry operations

### Meal Planning
- `get_week_plan` - View planned meals for the week
- `plan_meals` - Plan meals for specific dates
- `set_recipe_for_date` - Set a recipe for a specific date
- `clear_meal_plan` - Clear planned meals

### Grocery Management
- `get_grocery_list` - Generate grocery list for planned meals
- `generate_grocery_list` - Custom grocery list generation

### User Preferences
- `get_user_profile` - Get user preferences and household info
- `add_preference` - Add food preferences (likes, dislikes, allergies)
- `get_food_preferences` - View all food preferences

### Utilities
- `list_units` - View available measurement units
- `add_custom_unit` - Add custom measurement units
- `check_recipe_feasibility` - Check if recipe can be made with current pantry

## Configuration Options

### Environment Variables

- `OPENROUTER_API_KEY` - Your OpenRouter API key (required)
- `PANTRY_BACKEND` - Database backend: `sqlite` or `postgresql` (default: sqlite)
- `PANTRY_DATABASE_URL` - PostgreSQL connection string (for PostgreSQL backend)
- `PANTRY_DB_PATH` - SQLite database file path (default: pantry.db)

### Command Line Options

```bash
uv run openrouter_cli.py --help

options:
  --api-key API_KEY     OpenRouter API key
  --model MODEL         Model to use (default: anthropic/claude-3.5-sonnet)
  --backend {sqlite,postgresql}  Database backend
  --db-url DB_URL      Database connection URL for PostgreSQL
```

## Backend Modes

### SQLite (Single-User)
- Default mode for personal use
- Data stored in local `pantry.db` file
- No authentication required

### PostgreSQL (Multi-User)
- For shared/multi-user installations
- Requires PostgreSQL database setup
- User authentication handled automatically

## Tips for Best Results

1. **Be Specific**: "Add chicken breast, 2 lbs to pantry" works better than "add chicken"
2. **Use Natural Language**: "Plan vegetarian meals for this week"
3. **Context Matters**: The AI remembers your conversation, so follow-up questions work well
4. **Explore Tools**: Use `/tools` to see what's available
5. **Model Selection**: Try different models for different tasks:
   - Claude 3.5 Sonnet: Complex meal planning
   - GPT-4o Mini: Quick pantry updates
   - Gemini Pro: Creative recipe suggestions

## Troubleshooting

### Common Issues

**"No module named 'psycopg2'"**
```bash
# Make sure to run with uv
uv run openrouter_cli.py
```

**"OpenRouter API key required"**
```bash
export OPENROUTER_API_KEY=your_key_here
# Or pass directly
uv run openrouter_cli.py --api-key your_key_here
```

**"Tool execution failed"**
- Check that your database backend is properly configured
- For PostgreSQL, ensure the database is accessible
- For SQLite, check file permissions

## Integration with Existing Web Interface

This CLI uses the same backend and MCP tools as the web interface (`app_flask.py`), so:

- All data is shared between CLI and web interface
- Recipe changes in CLI appear in web interface
- Pantry updates are synchronized
- User preferences are consistent across both interfaces

The CLI is perfect for:
- Quick pantry updates via natural language
- Automated meal planning
- Recipe exploration and management
- Grocery list generation
- Integration with other automation tools

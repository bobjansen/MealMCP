"""
MCP Tool Definitions - Current Implementation
Aligned with the actual tools implemented in mcp_server.py
"""

from typing import List, Dict, Any

# Current MCP tools (23 total) matching mcp_server.py implementation
MCP_TOOLS: List[Dict[str, Any]] = [
    # === USER PROFILE ===
    {
        "name": "get_user_profile",
        "description": "Get comprehensive user profile including preferences, household size, and constraints for personalized meal planning",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # === PREFERENCES MANAGEMENT ===
    {
        "name": "add_preference",
        "description": "Add a new food preference to the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["like", "dislike", "allergy", "dietary"],
                    "description": "Category of preference",
                },
                "item": {
                    "type": "string",
                    "description": "Food item or dietary restriction",
                },
                "level": {
                    "type": "string",
                    "enum": ["required", "preferred", "avoid"],
                    "description": "Preference level",
                },
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["category", "item", "level"],
        },
    },
    # === RECIPE MANAGEMENT ===
    {
        "name": "add_recipe",
        "description": "Add a new recipe to the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Recipe name"},
                "instructions": {
                    "type": "string",
                    "description": "Cooking instructions",
                },
                "time_minutes": {
                    "type": "integer",
                    "description": "Preparation time in minutes",
                },
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string"},
                        },
                        "required": ["name", "quantity", "unit"],
                    },
                },
            },
            "required": ["name", "instructions", "time_minutes", "ingredients"],
        },
    },
    {
        "name": "get_recipe",
        "description": "Get detailed information about a specific recipe",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {"type": "string", "description": "Name of the recipe"},
            },
            "required": ["recipe_name"],
        },
    },
    {
        "name": "get_all_recipes",
        "description": "Get all recipes with basic information",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "edit_recipe",
        "description": "Edit an existing recipe",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Name of recipe to edit",
                },
                "instructions": {
                    "type": "string",
                    "description": "Updated cooking instructions",
                },
                "time_minutes": {
                    "type": "integer",
                    "description": "Updated preparation time",
                },
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string"},
                        },
                        "required": ["name", "quantity", "unit"],
                    },
                },
            },
            "required": ["recipe_name", "instructions", "time_minutes", "ingredients"],
        },
    },
    {
        "name": "edit_recipe_by_id",
        "description": "Edit an existing recipe by short ID with improved error messages. Allows partial updates and recipe renaming. Short IDs are human-friendly (e.g., R123A).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_id": {
                    "type": "string",
                    "description": "Short ID of the recipe to edit (e.g., R123A)",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the recipe (optional)",
                },
                "instructions": {
                    "type": "string",
                    "description": "Updated cooking instructions (optional)",
                },
                "time_minutes": {
                    "type": "integer",
                    "description": "Updated preparation time (optional)",
                },
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string"},
                        },
                        "required": ["name", "quantity", "unit"],
                    },
                    "description": "Updated list of ingredients (optional)",
                },
            },
            "required": ["recipe_id"],
        },
    },
    {
        "name": "get_recipe_id",
        "description": "Get the short ID of a recipe by name for precise editing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {"type": "string", "description": "Name of the recipe"}
            },
            "required": ["recipe_name"],
        },
    },
    {
        "name": "execute_recipe",
        "description": "Execute a recipe by removing required ingredients from pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Name of recipe to execute",
                },
            },
            "required": ["recipe_name"],
        },
    },
    # === PANTRY MANAGEMENT ===
    {
        "name": "get_pantry_contents",
        "description": "Get current pantry inventory",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "manage_pantry_item",
        "description": "Add or remove an item from the pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove"],
                    "description": "Action to perform",
                },
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {
                    "type": "number",
                    "description": "Amount to add or remove",
                },
                "unit": {"type": "string", "description": "Unit of measurement"},
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["action", "item_name", "quantity", "unit"],
        },
    },
    # === MEAL PLANNING ===
    {
        "name": "get_week_plan",
        "description": "Get the meal plan for the next 7 days",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_grocery_list",
        "description": "Get grocery items needed for the coming week's meal plan",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "set_recipe_for_date",
        "description": "Set a recipe for a specific date in the meal plan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {"type": "string", "description": "Name of the recipe"},
                "meal_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Date for the meal (YYYY-MM-DD)",
                },
            },
            "required": ["recipe_name", "meal_date"],
        },
    },
    # === UTILITY TOOLS ===
    {
        "name": "list_units",
        "description": "List all available units of measurement",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # === PANTRY MANAGEMENT (INDIVIDUAL) ===
    {
        "name": "add_pantry_item",
        "description": "Add an item to the pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {"type": "number", "description": "Quantity to add"},
                "unit": {"type": "string", "description": "Unit of measurement"},
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["item_name", "quantity", "unit"],
        },
    },
    {
        "name": "remove_pantry_item",
        "description": "Remove an item from the pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {"type": "number", "description": "Quantity to remove"},
                "unit": {"type": "string", "description": "Unit of measurement"},
            },
            "required": ["item_name", "quantity", "unit"],
        },
    },
    # === PREFERENCES ===
    {
        "name": "get_food_preferences",
        "description": "Get all food preferences",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # === MEAL PLANNING ===
    {
        "name": "plan_meals",
        "description": "Plan meals for specified dates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "meal_assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date in YYYY-MM-DD format",
                            },
                            "recipe_name": {
                                "type": "string",
                                "description": "Recipe name",
                            },
                        },
                        "required": ["date", "recipe_name"],
                    },
                    "description": "Array of meal assignments",
                },
            },
            "required": ["meal_assignments"],
        },
    },
    {
        "name": "get_meal_plan",
        "description": "Get meal plan for specified period",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days (default: 7)",
                },
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "clear_meal_plan",
        "description": "Clear meal plan for specified date range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "generate_grocery_list",
        "description": "Generate grocery list for upcoming meal plan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days (default: 7)",
                },
            },
            "required": [],
        },
    },
    # === RECIPE ANALYSIS ===
    {
        "name": "search_recipes",
        "description": "Search recipes with filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_prep_time": {
                    "type": "integer",
                    "description": "Maximum preparation time in minutes",
                },
                "min_rating": {
                    "type": "integer",
                    "description": "Minimum rating (1-5)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "suggest_recipes_from_pantry",
        "description": "Suggest recipes based on available pantry items",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_recipe_feasibility",
        "description": "Check if a recipe can be made with current pantry items",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Recipe name to check",
                },
            },
            "required": ["recipe_name"],
        },
    },
]


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """Get a specific tool definition by name."""
    for tool in MCP_TOOLS:
        if tool["name"] == tool_name:
            return tool
    raise ValueError(f"Tool '{tool_name}' not found")


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return [tool["name"] for tool in MCP_TOOLS]


def get_tool_count() -> int:
    """Get total number of available tools."""
    return len(MCP_TOOLS)


def get_tools_by_category() -> Dict[str, List[str]]:
    """Get tools organized by category."""
    categories = {
        "User Profile": ["get_user_profile"],
        "Preferences": ["add_preference"],
        "Recipe Management": [
            "add_recipe",
            "get_recipe",
            "get_all_recipes",
            "edit_recipe",
            "edit_recipe_by_id",
            "get_recipe_id",
            "execute_recipe",
        ],
        "Pantry Management": ["get_pantry_contents", "manage_pantry_item"],
        "Meal Planning": ["get_week_plan", "get_grocery_list", "set_recipe_for_date"],
        "Admin/System": ["create_user", "list_users"],
    }
    return categories

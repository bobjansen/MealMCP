"""
MCP Tool Definitions - Current Implementation
Aligned with the actual tools implemented in mcp_server.py
"""

from typing import List, Dict, Any

# Current MCP tools (15 total) matching mcp_server.py implementation
MCP_TOOLS: List[Dict[str, Any]] = [
    # === USER PROFILE ===
    {
        "name": "get_user_profile",
        "description": "Get comprehensive user profile including preferences, household size, and constraints for personalized meal planning",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                }
            },
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                },
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                },
            },
            "required": ["recipe_name"],
        },
    },
    {
        "name": "get_all_recipes",
        "description": "Get all recipes with basic information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                }
            },
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                },
            },
            "required": ["recipe_name", "instructions", "time_minutes", "ingredients"],
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
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
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                }
            },
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                },
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
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_grocery_list",
        "description": "Get grocery items needed for the coming week's meal plan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                }
            },
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
                "token": {
                    "type": "string",
                    "description": "Authentication token (required for remote mode)",
                },
            },
            "required": ["recipe_name", "meal_date"],
        },
    },
    # === ADMIN/SYSTEM ===
    {
        "name": "create_user",
        "description": "Create a new user (admin only)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username for new user"},
                "admin_token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
            },
            "required": ["username", "admin_token"],
        },
    },
    {
        "name": "list_users",
        "description": "List all users (admin only)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "admin_token": {
                    "type": "string",
                    "description": "Admin authentication token",
                }
            },
            "required": ["admin_token"],
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
            "execute_recipe",
        ],
        "Pantry Management": ["get_pantry_contents", "manage_pantry_item"],
        "Meal Planning": ["get_week_plan", "get_grocery_list", "set_recipe_for_date"],
        "Admin/System": ["create_user", "list_users"],
    }
    return categories

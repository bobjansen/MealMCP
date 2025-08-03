"""
MCP Tool Definitions
Centralized tool definitions for the MealMCP server
"""

from typing import List, Dict, Any

# Define all MCP tools in one place
MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_units",
        "description": "List all units of measurement",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_recipe",
        "description": "Add a new recipe to the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the recipe"},
                "instructions": {"type": "string", "description": "Cooking instructions"},
                "time_minutes": {"type": "integer", "description": "Time required to prepare the recipe"},
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
        }
    },
    {
        "name": "get_all_recipes",
        "description": "Get all recipes",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_recipe",
        "description": "Get details for a specific recipe",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Name of the recipe to retrieve"
                }
            },
            "required": ["recipe_name"]
        }
    },
    {
        "name": "get_pantry_contents",
        "description": "Get the current contents of the pantry",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "add_pantry_item",
        "description": "Add an item to the pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item to add"},
                "quantity": {"type": "number", "description": "Amount to add"},
                "unit": {"type": "string", "description": "Unit of measurement"},
                "notes": {"type": "string", "description": "Optional notes about the transaction"},
            },
            "required": ["item_name", "quantity", "unit"],
        }
    }
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
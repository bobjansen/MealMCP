"""
Optimized MCP Tool Definitions for Meal Planning
Designed for maximum LLM effectiveness and meal planning focus
"""

from typing import List, Dict, Any

# Optimized MCP tools focused on meal planning workflow
MCP_TOOLS_OPTIMIZED: List[Dict[str, Any]] = [
    # === CORE MEAL PLANNING TOOLS ===
    {
        "name": "plan_meals",
        "description": "Execute a meal plan by assigning specific recipes to specific dates. The LLM should decide which recipes to assign to which dates, then use this tool to save the plan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "meal_assignments": {
                    "type": "array",
                    "description": "Array of meal assignments to execute",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "format": "date",
                                "description": "Date for this meal (YYYY-MM-DD)",
                            },
                            "recipe_name": {
                                "type": "string",
                                "description": "Name of the recipe to assign",
                            },
                            "meal_type": {
                                "type": "string",
                                "enum": ["breakfast", "lunch", "dinner", "snack"],
                                "default": "dinner",
                                "description": "Type of meal",
                            },
                        },
                        "required": ["date", "recipe_name"],
                    },
                },
                "replace_existing": {
                    "type": "boolean",
                    "default": false,
                    "description": "Replace existing meal plan for these dates",
                },
            },
            "required": ["meal_assignments"],
        },
    },
    {
        "name": "get_meal_plan",
        "description": "Get the current meal plan for a specified date range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date (YYYY-MM-DD)",
                },
                "days": {
                    "type": "integer",
                    "default": 7,
                    "description": "Number of days to retrieve",
                },
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "set_meal_for_date",
        "description": "Assign a specific recipe to a date and meal type",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "Date for the meal (YYYY-MM-DD)",
                },
                "recipe_name": {
                    "type": "string",
                    "description": "Name of the recipe to assign",
                },
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"],
                    "default": "dinner",
                    "description": "Type of meal",
                },
            },
            "required": ["date", "recipe_name"],
        },
    },
    {
        "name": "generate_grocery_list",
        "description": "Generate a smart grocery list based on meal plan and current pantry contents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date for meal plan period",
                },
                "days": {
                    "type": "integer",
                    "default": 7,
                    "description": "Number of days to include",
                },
                "group_by_section": {
                    "type": "boolean",
                    "default": true,
                    "description": "Group items by store section",
                },
            },
            "required": [],
        },
    },
    # === RECIPE INTELLIGENCE TOOLS ===
    {
        "name": "suggest_recipes_from_pantry",
        "description": "Get recipe suggestions based on ingredients currently available in pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_missing_ingredients": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum number of missing ingredients to allow",
                },
                "max_prep_time": {
                    "type": "integer",
                    "description": "Maximum preparation time in minutes",
                },
                "cuisine_type": {
                    "type": "string",
                    "description": "Preferred cuisine type",
                },
            },
            "required": [],
        },
    },
    {
        "name": "search_recipes",
        "description": "Search and filter recipes by multiple criteria",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text search in recipe names and descriptions",
                },
                "ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Must contain these ingredients",
                },
                "exclude_ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Must NOT contain these ingredients",
                },
                "max_prep_time": {
                    "type": "integer",
                    "description": "Maximum prep time in minutes",
                },
                "min_rating": {
                    "type": "number",
                    "description": "Minimum recipe rating (1-5)",
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Recipe difficulty level",
                },
            },
            "required": [],
        },
    },
    {
        "name": "check_recipe_feasibility",
        "description": "Check if a recipe can be made with current pantry contents and what's missing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Name of the recipe to check",
                },
                "servings": {
                    "type": "number",
                    "default": 4,
                    "description": "Number of servings desired",
                },
            },
            "required": ["recipe_name"],
        },
    },
    # === RECIPE MANAGEMENT (Enhanced) ===
    {
        "name": "add_recipe",
        "description": "Add a new recipe with enhanced metadata for better meal planning",
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
                    "description": "Total preparation and cooking time",
                },
                "servings": {
                    "type": "integer",
                    "default": 4,
                    "description": "Number of servings this recipe makes",
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "default": "medium",
                    "description": "Recipe difficulty",
                },
                "cuisine_type": {
                    "type": "string",
                    "description": "Cuisine type (e.g., Italian, Asian, Mexican)",
                },
                "meal_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                    },
                    "description": "What meal types this recipe is suitable for",
                },
                "dietary_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Dietary tags (vegetarian, vegan, gluten-free, etc.)",
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
        "name": "get_all_recipes",
        "description": "Get all recipes with enhanced filtering options",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_metadata": {
                    "type": "boolean",
                    "default": true,
                    "description": "Include difficulty, cuisine, dietary tags",
                },
                "cuisine_filter": {
                    "type": "string",
                    "description": "Filter by cuisine type",
                },
                "dietary_filter": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by dietary requirements",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_recipe",
        "description": "Get detailed recipe information including metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipe_name": {"type": "string", "description": "Name of the recipe"},
                "scale_servings": {
                    "type": "number",
                    "description": "Scale ingredients for this many servings",
                },
            },
            "required": ["recipe_name"],
        },
    },
    # === PANTRY MANAGEMENT (Enhanced) ===
    {
        "name": "get_pantry_contents",
        "description": "Get current pantry inventory with optional filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by ingredient category",
                },
                "low_stock_only": {
                    "type": "boolean",
                    "default": false,
                    "description": "Show only items running low",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_pantry_item",
        "description": "Add items to pantry with optional expiration tracking",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {"type": "number", "description": "Amount to add"},
                "unit": {"type": "string", "description": "Unit of measurement"},
                "expiration_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Expiration date (YYYY-MM-DD)",
                },
                "notes": {"type": "string", "description": "Optional notes"},
            },
            "required": ["item_name", "quantity", "unit"],
        },
    },
    {
        "name": "remove_pantry_item",
        "description": "Remove or consume items from pantry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {"type": "number", "description": "Amount to remove"},
                "unit": {"type": "string", "description": "Unit of measurement"},
                "reason": {
                    "type": "string",
                    "enum": ["consumed", "expired", "spoiled", "other"],
                    "default": "consumed",
                    "description": "Reason for removal",
                },
            },
            "required": ["item_name", "quantity", "unit"],
        },
    },
    # === PREFERENCES MANAGEMENT ===
    {
        "name": "set_food_preference",
        "description": "Set dietary preferences and restrictions for better meal planning",
        "inputSchema": {
            "type": "object",
            "properties": {
                "food_item": {
                    "type": "string",
                    "description": "Food item or ingredient",
                },
                "preference_type": {
                    "type": "string",
                    "enum": ["like", "dislike", "allergy", "dietary"],
                    "description": "Type of preference",
                },
                "category": {
                    "type": "string",
                    "description": "Category (e.g., 'vegetarian', 'gluten-free')",
                },
                "notes": {"type": "string", "description": "Additional notes"},
            },
            "required": ["food_item", "preference_type"],
        },
    },
    {
        "name": "get_food_preferences",
        "description": "Get current food preferences and dietary restrictions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "preference_type": {
                    "type": "string",
                    "enum": ["like", "dislike", "allergy", "dietary"],
                    "description": "Filter by preference type",
                }
            },
            "required": [],
        },
    },
    # === ADVANCED PLANNING ===
    {
        "name": "clear_meal_plan",
        "description": "Clear meal plan for specified date range to allow LLM to create a fresh plan",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Start date",
                },
                "days": {
                    "type": "integer",
                    "default": 7,
                    "description": "Number of days to clear",
                },
            },
            "required": ["start_date"],
        },
    },
]


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """Get a specific tool definition by name."""
    for tool in MCP_TOOLS_OPTIMIZED:
        if tool["name"] == tool_name:
            return tool
    raise ValueError(f"Tool '{tool_name}' not found")


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return [tool["name"] for tool in MCP_TOOLS_OPTIMIZED]

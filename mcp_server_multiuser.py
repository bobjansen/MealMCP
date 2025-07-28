from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional
from constants import UNITS
from mcp_context import MCPContext
from i18n import t
from datetime import date, timedelta
import os

# Create an MCP server
mcp = FastMCP("RecipeManager")

# Create context manager for user handling
context = MCPContext()

# Helper function to get user context
def get_user_pantry(token: Optional[str] = None) -> tuple[Optional[str], Optional[Any]]:
    """Get authenticated user and their PantryManager instance."""
    user_id, pantry = context.authenticate_and_get_pantry(token)
    if not user_id or not pantry:
        return None, None
    context.set_current_user(user_id)
    return user_id, pantry


@mcp.tool()
def list_units() -> List[Dict[str, Any]]:
    """List all units of measurement

    Returns
    -------
    List[str]
        List of measurement units
    """
    return UNITS


@mcp.tool()
def list_preferences(token: Optional[str] = None) -> Dict[str, Any]:
    """Get all food preferences from the database.

    Parameters
    ----------
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Response containing preferences list or error
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}
    
    preferences = pantry.get_preferences()
    return {"status": "success", "preferences": preferences}


@mcp.tool()
def add_preference(
    category: str, item: str, level: str, notes: str = None, token: Optional[str] = None
) -> Dict[str, Any]:
    """Add a new food preference to the database.

    Parameters
    ----------
    category : str
        Type of preference (dietary, allergy, dislike)
    item : str
        The specific preference item
    level : str
        Importance level (required, preferred, avoid)
    notes : str, optional
        Additional notes about the preference
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}
    
    try:
        success = pantry.add_preference(
            category=category,
            item=item,
            level=level,
            notes=notes,
        )
        if success:
            return {"status": "success", "message": t("Preference added successfully")}
        else:
            return {
                "status": "error",
                "message": t(
                    "Failed to add preference. Item may already exist with this category."
                ),
            }
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def add_recipe(
    name: str, instructions: str, time_minutes: int, ingredients: List[Dict[str, Any]], token: Optional[str] = None
) -> Dict[str, Any]:
    """Add a new recipe to the database.

    Parameters
    ----------
    name : str
        Name of the recipe
    instructions : str
        Cooking instructions
    time_minutes : int
        Time required to prepare the recipe
    ingredients : List[Dict[str, Any]]
        List of dictionaries containing:
            - name: ingredient name
            - quantity: amount needed
            - unit: unit of measurement
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    success = pantry.add_recipe(
        name=name,
        instructions=instructions,
        time_minutes=time_minutes,
        ingredients=ingredients,
    )

    if success:
        return {"status": "success", "message": t("Recipe added successfully")}
    else:
        return {"status": "error", "message": t("Failed to add recipe")}


@mcp.tool()
def get_recipe(recipe_name: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Get details for a specific recipe.

    Parameters
    ----------
    recipe_name : str
        Name of the recipe to retrieve
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Recipe details or error message. The instructions are formatted in Markdown.
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    recipe = pantry.get_recipe(recipe_name)

    if recipe:
        return {"status": "success", "recipe": recipe}
    else:
        return {
            "status": "error",
            "message": t("Recipe '{name}' not found").format(name=recipe_name),
        }


@mcp.tool()
def get_all_recipes(token: Optional[str] = None) -> Dict[str, Any]:
    """Get all recipes.

    Parameters
    ----------
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        List of all recipes or empty list
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    recipes = pantry.get_all_recipes()
    return {"status": "success", "recipes": recipes}


@mcp.tool()
def edit_recipe(
    name: str, instructions: str, time_minutes: int, ingredients: List[Dict[str, Any]], token: Optional[str] = None
) -> Dict[str, Any]:
    """Edit an existing recipe in the database.

    Parameters
    ----------
    name : str
        Name of the recipe to edit
    instructions : str
        Updated cooking instructions, in Markdown format
    time_minutes : int
        Updated time required to prepare the recipe
    ingredients : List[Dict[str, Any]]
        Updated list of dictionaries containing:
            - name: ingredient name
            - quantity: amount needed
            - unit: unit of measurement
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    success = pantry.edit_recipe(
        name=name,
        instructions=instructions,
        time_minutes=time_minutes,
        ingredients=ingredients,
    )

    if success:
        return {"status": "success", "message": t("Recipe updated successfully")}
    else:
        return {
            "status": "error",
            "message": t("Failed to update recipe '{name}'").format(name=name),
        }


@mcp.tool()
def execute_recipe(recipe_name: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Execute a recipe by removing its ingredients from the pantry.

    Parameters
    ----------
    recipe_name : str
        Name of the recipe to execute
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Success/error message with details
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    success, message = pantry.execute_recipe(recipe_name)

    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}


@mcp.tool()
def get_pantry_contents(token: Optional[str] = None) -> Dict[str, Any]:
    """Get the current contents of the pantry.

    Parameters
    ----------
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Dictionary containing pantry contents where keys are item names and
        values are dictionaries of quantities by unit
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    contents = pantry.get_pantry_contents()
    return {"status": "success", "contents": contents}


@mcp.tool()
def add_pantry_item(
    item_name: str, quantity: float, unit: str, notes: str = None, token: Optional[str] = None
) -> Dict[str, Any]:
    """Add an item to the pantry.

    Parameters
    ----------
    item_name : str
        Name of the item to add
    quantity : float
        Amount to add
    unit : str
        Unit of measurement
    notes : str, optional
        Optional notes about the transaction
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Success/error message
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    success = pantry.add_item(item_name, quantity, unit, notes)
    if success:
        return {"status": "success", "message": f"Added {quantity} {unit} of {item_name} to pantry"}
    else:
        return {"status": "error", "message": "Failed to add item to pantry"}


@mcp.tool()
def remove_pantry_item(
    item_name: str, quantity: float, unit: str, notes: str = None, token: Optional[str] = None
) -> Dict[str, Any]:
    """Remove an item from the pantry.

    Parameters
    ----------
    item_name : str
        Name of the item to remove
    quantity : float
        Amount to remove
    unit : str
        Unit of measurement
    notes : str, optional
        Optional notes about the transaction
    token : str, optional
        Authentication token (required for remote mode)

    Returns
    -------
    Dict[str, Any]
        Success/error message
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    success = pantry.remove_item(item_name, quantity, unit, notes)
    if success:
        return {"status": "success", "message": f"Removed {quantity} {unit} of {item_name} from pantry"}
    else:
        return {"status": "error", "message": "Failed to remove item from pantry"}


@mcp.tool()
def get_week_plan(token: Optional[str] = None) -> Dict[str, Any]:
    """Get the meal plan for the next 7 days.
    
    Parameters
    ----------
    token : str, optional
        Authentication token (required for remote mode)
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    start = date.today()
    end = start + timedelta(days=6)
    plan = pantry.get_meal_plan(start.isoformat(), end.isoformat())
    return {"status": "success", "plan": plan}


@mcp.tool()
def get_grocery_list(token: Optional[str] = None) -> Dict[str, Any]:
    """Return grocery items needed for the coming week's meal plan.
    
    Parameters
    ----------
    token : str, optional
        Authentication token (required for remote mode)
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    items = pantry.get_grocery_list()
    return {"status": "success", "grocery": items}


@mcp.tool()
def set_recipe_for_date(meal_date: str, recipe_name: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Assign a recipe to a certain date

    Parameters
    ----------
    meal_date : str
        Date to use the recipe
    recipe_name : str
        Name of the recipe to execute
    token : str, optional
        Authentication token (required for remote mode)
        
    Returns
    -------
    Dict[str, Any]
        status: status_string
    """
    user_id, pantry = get_user_pantry(token)
    if not pantry:
        return {"status": "error", "message": "Authentication required"}

    result = pantry.set_meal_plan(meal_date=meal_date, recipe_name=recipe_name)
    if result:
        return {"status": "success"}
    return {"status": "error"}


# Admin-only tools for remote mode
@mcp.tool()
def create_user(username: str, admin_token: str) -> Dict[str, Any]:
    """Create a new user (admin only).

    Parameters
    ----------
    username : str
        Username for the new user
    admin_token : str
        Admin authentication token

    Returns
    -------
    Dict[str, Any]
        Response with new user token or error
    """
    if context.mode == "local":
        return {"status": "error", "message": "User creation not available in local mode"}
    
    return context.create_user(username, admin_token)


@mcp.tool()
def list_users(admin_token: str) -> Dict[str, Any]:
    """List all users (admin only).

    Parameters
    ----------
    admin_token : str
        Admin authentication token

    Returns
    -------
    Dict[str, Any]
        List of users or error
    """
    if context.mode == "local":
        return {"status": "success", "users": ["local_user"]}
    
    # Verify admin token
    admin_user = context.user_manager.authenticate(admin_token)
    if admin_user != "admin":
        return {"status": "error", "message": "Admin access required"}
    
    users = context.user_manager.list_users()
    return {"status": "success", "users": users}


@mcp.tool()
def get_server_info() -> Dict[str, Any]:
    """Get server mode and configuration info."""
    return {
        "status": "success",
        "mode": context.mode,
        "multi_user": context.mode == "remote",
        "authentication_required": context.mode == "remote"
    }


# Entry point to run the server
if __name__ == "__main__":
    mcp.run()
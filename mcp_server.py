from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List
from constants import UNITS
from pantry_manager import PantryManager
from i18n import t
from datetime import date, timedelta

# Create an MCP server
mcp = FastMCP("RecipeManager")

# Create pantry manager instance at server startup
pantry = PantryManager()


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
def list_preferences() -> List[Dict[str, Any]]:
    """Get all food preferences from the database.

    Returns
    -------
    List[Dict[str, Any]]
        List of preferences, each containing:
            - category: Type of preference (dietary, allergy, dislike)
            - item: The specific preference item
            - level: Importance level (required, preferred, avoid)
            - notes: Optional notes about the preference
    """
    preferences = pantry.get_preferences()
    return preferences


@mcp.tool()
def add_preference(
    category: str, item: str, level: str, notes: str = None
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

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
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
                "message": t("Failed to add preference. Item may already exist with this category."),
            }
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def add_recipe(
    name: str, instructions: str, time_minutes: int, ingredients: List[Dict[str, Any]]
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

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
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
def get_recipe(recipe_name: str) -> Dict[str, Any]:
    """Get details for a specific recipe.

    Parameters
    ----------
    recipe_name : str
        Name of the recipe to retrieve

    Returns
    -------
    Dict[str, Any]
        Recipe details or error message. The instructions are formatted in Markdown.
    """
    recipe = pantry.get_recipe(recipe_name)

    if recipe:
        return {"status": "success", "recipe": recipe}
    else:
        return {"status": "error", "message": t("Recipe '{name}' not found").format(name=recipe_name)}


@mcp.tool()
def get_all_recipes() -> Dict[str, Any]:
    """Get all recipes.

    Returns
    -------
    Dict[str, Any]
        List of all recipes or empty list
    """
    recipes = pantry.get_all_recipes()
    return {"status": "success", "recipes": recipes}


@mcp.tool()
def edit_recipe(
    name: str, instructions: str, time_minutes: int, ingredients: List[Dict[str, Any]]
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

    Returns
    -------
    Dict[str, Any]
        Response with success/error message
    """
    success = pantry.edit_recipe(
        name=name,
        instructions=instructions,
        time_minutes=time_minutes,
        ingredients=ingredients,
    )

    if success:
        return {"status": "success", "message": t("Recipe updated successfully")}
    else:
        return {"status": "error", "message": t("Failed to update recipe '{name}'").format(name=name)}


@mcp.tool()
def execute_recipe(recipe_name: str) -> Dict[str, Any]:
    """Execute a recipe by removing its ingredients from the pantry.

    Parameters
    ----------
    recipe_name : str
        Name of the recipe to execute

    Returns
    -------
    Dict[str, Any]
        Success/error message with details
    """
    success, message = pantry.execute_recipe(recipe_name)

    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}


@mcp.tool()
def get_pantry_contents() -> Dict[str, Any]:
    """Get the current contents of the pantry.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing pantry contents where keys are item names and
        values are dictionaries of quantities by unit
    """
    contents = pantry.get_pantry_contents()
    return {"status": "success", "contents": contents}


@mcp.tool()
def generate_week_plan() -> Dict[str, Any]:
    """Generate a meal plan for the upcoming week."""
    plan = pantry.generate_week_plan()
    return {"status": "success", "plan": plan}


@mcp.tool()
def get_week_plan() -> Dict[str, Any]:
    """Get the meal plan for the next 7 days."""
    start = date.today()
    end = start + timedelta(days=6)
    plan = pantry.get_meal_plan(start.isoformat(), end.isoformat())
    return {"status": "success", "plan": plan}


# Entry point to run the server
if __name__ == "__main__":
    mcp.run()

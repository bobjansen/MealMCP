from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List
from pantry_manager import PantryManager

# Create an MCP server
mcp = FastMCP("RecipeManager")

# Create pantry manager instance at server startup
pantry = PantryManager()


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
        return {"status": "success", "message": "Recipe added successfully"}
    else:
        return {"status": "error", "message": "Failed to add recipe"}


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
        Recipe details or error message
    """
    recipe = pantry.get_recipe(recipe_name)

    if recipe:
        return {"status": "success", "recipe": recipe}
    else:
        return {"status": "error", "message": f"Recipe '{recipe_name}' not found"}


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
def execute_recipe(recipe_name: str, scale_factor: float = 1.0) -> Dict[str, Any]:
    """Execute a recipe by removing its ingredients from the pantry.

    Parameters
    ----------
    recipe_name : str
        Name of the recipe to execute
    scale_factor : float, optional
        Factor to scale recipe quantities, by default 1.0

    Returns
    -------
    Dict[str, Any]
        Success/error message with details
    """
    success, message = pantry.execute_recipe(recipe_name, scale_factor)

    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}


# Entry point to run the server
if __name__ == "__main__":
    mcp.run()

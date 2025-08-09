"""
MCP Tool Router - Centralized tool dispatch
"""

import json
import logging
from datetime import datetime, timedelta
from i18n import t
from typing import Dict, Any, Optional, Callable
from constants import UNITS
from mcp_tools import MCP_TOOLS

logger = logging.getLogger(__name__)


class MCPToolRouter:
    """Routes MCP tool calls to appropriate implementations."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available MCP tools."""
        self.tools = {
            "list_units": self._list_units,
            "get_user_profile": self._get_user_profile,
            "add_recipe": self._add_recipe,
            "edit_recipe": self._edit_recipe,
            "edit_recipe_by_id": self._edit_recipe_by_id,
            "get_recipe_id": self._get_recipe_id,
            "get_all_recipes": self._get_all_recipes,
            "get_recipe": self._get_recipe,
            "get_pantry_contents": self._get_pantry_contents,
            "add_pantry_item": self._add_pantry_item,
            "remove_pantry_item": self._remove_pantry_item,
            "plan_meals": self._plan_meals,
            "get_meal_plan": self._get_meal_plan,
            "generate_grocery_list": self._generate_grocery_list,
            "suggest_recipes_from_pantry": self._suggest_recipes_from_pantry,
            "search_recipes": self._search_recipes,
            "check_recipe_feasibility": self._check_recipe_feasibility,
            "get_food_preferences": self._get_food_preferences,
            "clear_meal_plan": self._clear_meal_plan,
            "add_preference": self._add_preference,
            "execute_recipe": self._execute_recipe,
            "get_week_plan": self._get_week_plan,
            "set_recipe_for_date": self._set_recipe_for_date,
        }

    def call_tool(
        self, tool_name: str, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Route tool call to appropriate implementation."""
        if tool_name not in self.tools:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        try:
            return self.tools[tool_name](arguments, pantry_manager)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"status": "error", "message": f"Tool execution failed: {str(e)}"}

    def get_available_tools(self) -> list:
        """Get list of available MCP tools."""
        return MCP_TOOLS

    # Tool implementations
    def _list_units(self, arguments: Dict[str, Any], pantry_manager) -> Dict[str, Any]:
        """List all units of measurement."""
        return {"status": "success", "units": UNITS}

    def _get_user_profile(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get comprehensive user profile."""
        try:
            household = pantry_manager.get_household_characteristics()
            preferences = pantry_manager.get_preferences()

            # Serialize datetime objects
            def serialize_datetime_objects(obj):
                if isinstance(obj, dict):
                    return {k: serialize_datetime_objects(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime_objects(item) for item in obj]
                elif hasattr(obj, "isoformat"):
                    return obj.isoformat()
                else:
                    return obj

            preferences = serialize_datetime_objects(preferences)
            household = serialize_datetime_objects(household)

            # Organize preferences by category
            preferences_summary = {
                "required_dietary": [],
                "preferred_dietary": [],
                "allergies": [],
                "dislikes": [],
                "likes": [],
            }

            for pref in preferences:
                category = pref.get("category", "")
                item = pref.get("item", "")
                level = pref.get("level", "")

                if category == "dietary":
                    if level == "required":
                        preferences_summary["required_dietary"].append(item)
                    elif level == "preferred":
                        preferences_summary["preferred_dietary"].append(item)
                elif category == "allergy":
                    preferences_summary["allergies"].append(item)
                elif category == "dislike":
                    preferences_summary["dislikes"].append(item)
                elif category == "like":
                    preferences_summary["likes"].append(item)

            household["total_people"] = household.get("adults", 2) + household.get(
                "children", 0
            )

            profile_data = {
                "household": household,
                "dietary_preferences": preferences,
                "preferences_summary": preferences_summary,
            }

            return {"status": "success", "data": profile_data}

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error getting user profile: {str(e)}",
            }

    def _add_recipe(self, arguments: Dict[str, Any], pantry_manager) -> Dict[str, Any]:
        """Add a new recipe."""
        success, recipe_id = pantry_manager.add_recipe(
            name=arguments["name"],
            instructions=arguments["instructions"],
            time_minutes=arguments["time_minutes"],
            ingredients=arguments["ingredients"],
        )

        if success:
            return {
                "status": "success",
                "message": t("Recipe added successfully"),
                "recipe_id": recipe_id,
                "recipe_name": arguments["name"],
            }
        else:
            return {"status": "error", "message": t("Failed to add recipe")}

    def _edit_recipe(self, arguments: Dict[str, Any], pantry_manager) -> Dict[str, Any]:
        """Edit an existing recipe."""
        recipe_name = arguments["recipe_name"]

        # Check if recipe exists
        existing_recipe = pantry_manager.get_recipe(recipe_name)
        if not existing_recipe:
            return {"status": "error", "message": f"Recipe '{recipe_name}' not found"}

        # Update the recipe
        success = pantry_manager.edit_recipe(
            name=recipe_name,
            instructions=arguments["instructions"],
            time_minutes=arguments["time_minutes"],
            ingredients=arguments["ingredients"],
        )

        if success:
            return {
                "status": "success",
                "message": f"Recipe '{recipe_name}' updated successfully",
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to update recipe '{recipe_name}'",
            }

    def _edit_recipe_by_id(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Edit an existing recipe by short ID."""
        recipe_id = arguments["recipe_id"]

        # Extract optional fields
        name = arguments.get("name")
        instructions = arguments.get("instructions")
        time_minutes = arguments.get("time_minutes")
        ingredients = arguments.get("ingredients")

        # Check if at least one field is provided for update
        if all(
            field is None for field in [name, instructions, time_minutes, ingredients]
        ):
            return {
                "status": "error",
                "message": "At least one field (name, instructions, time_minutes, or ingredients) must be provided for update",
            }

        # Call the improved edit method with detailed error handling
        success, message = pantry_manager.edit_recipe_by_short_id(
            short_id=recipe_id,
            name=name,
            instructions=instructions,
            time_minutes=time_minutes,
            ingredients=ingredients,
        )

        return {"status": "success" if success else "error", "message": message}

    def _get_recipe_id(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get the short ID of a recipe by name."""
        recipe_name = arguments["recipe_name"]

        recipe_id = pantry_manager.get_recipe_short_id(recipe_name)

        if recipe_id:
            return {
                "status": "success",
                "recipe_name": recipe_name,
                "recipe_id": recipe_id,
            }
        else:
            return {"status": "error", "message": f"Recipe '{recipe_name}' not found"}

    def _get_all_recipes(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get all recipes."""
        recipes = pantry_manager.get_all_recipes()
        return {"status": "success", "recipes": recipes}

    def _get_recipe(self, arguments: Dict[str, Any], pantry_manager) -> Dict[str, Any]:
        """Get a specific recipe."""
        recipe_name = arguments["recipe_name"]
        recipe = pantry_manager.get_recipe(recipe_name)

        if recipe:
            return {"status": "success", "recipe": recipe}
        else:
            return {"status": "error", "message": f"Recipe '{recipe_name}' not found"}

    def _get_pantry_contents(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get current pantry contents."""
        contents = pantry_manager.get_pantry_contents()
        return {"status": "success", "contents": contents}

    def _add_pantry_item(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Add an item to the pantry."""
        success = pantry_manager.add_item(
            arguments["item_name"],
            arguments["quantity"],
            arguments["unit"],
            arguments.get("notes"),
        )

        if success:
            return {
                "status": "success",
                "message": f"Added {arguments['quantity']} {arguments['unit']} of {arguments['item_name']} to pantry",
            }
        else:
            return {"status": "error", "message": "Failed to add item to pantry"}

    def _remove_pantry_item(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Remove an item from the pantry."""
        success = pantry_manager.remove_item(
            arguments["item_name"],
            arguments["quantity"],
            arguments["unit"],
            arguments.get("reason", "consumed"),
        )

        if success:
            return {
                "status": "success",
                "message": f"Removed {arguments['quantity']} {arguments['unit']} of {arguments['item_name']} from pantry",
            }
        else:
            return {"status": "error", "message": "Failed to remove item from pantry"}

    def _plan_meals(self, arguments: Dict[str, Any], pantry_manager) -> Dict[str, Any]:
        """Plan meals for specified dates."""
        meal_assignments = arguments.get("meal_assignments", [])
        success_count = 0
        errors = []

        for assignment in meal_assignments:
            try:
                success = pantry_manager.set_meal_plan(
                    assignment["date"], assignment["recipe_name"]
                )
                if success:
                    success_count += 1
                else:
                    errors.append(
                        f"Failed to assign {assignment['recipe_name']} to {assignment['date']}"
                    )
            except Exception as e:
                errors.append(
                    f"Error with {assignment['recipe_name']} on {assignment['date']}: {str(e)}"
                )

        return {
            "status": "success" if success_count > 0 else "error",
            "message": f"Successfully planned {success_count} meals",
            "assigned": success_count,
            "errors": errors,
        }

    def _get_meal_plan(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get meal plan for specified period."""
        start_date = arguments.get("start_date")
        days = arguments.get("days", 7)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = start + timedelta(days=days - 1)
            meal_plan = pantry_manager.get_meal_plan(
                start_date, end.strftime("%Y-%m-%d")
            )
            return {"status": "success", "meal_plan": meal_plan}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get meal plan: {str(e)}"}

    def _generate_grocery_list(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Generate grocery list."""
        try:
            grocery_list = pantry_manager.get_grocery_list()
            return {"status": "success", "grocery_list": grocery_list}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to generate grocery list: {str(e)}",
            }

    def _suggest_recipes_from_pantry(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Suggest recipes based on pantry contents."""
        max_missing = arguments.get("max_missing_ingredients", 3)
        max_time = arguments.get("max_prep_time")

        try:
            pantry_items = set(pantry_manager.get_pantry_contents().keys())
            all_recipes = pantry_manager.get_all_recipes()

            suggestions = []
            for recipe in all_recipes:
                recipe_ingredients = set(
                    ing["name"] for ing in recipe.get("ingredients", [])
                )
                missing = recipe_ingredients - pantry_items

                if len(missing) <= max_missing:
                    if max_time is None or recipe.get("time_minutes", 0) <= max_time:
                        suggestions.append(
                            {
                                "recipe": recipe,
                                "missing_ingredients": list(missing),
                                "missing_count": len(missing),
                            }
                        )

            suggestions.sort(key=lambda x: x["missing_count"])
            return {"status": "success", "suggestions": suggestions}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get suggestions: {str(e)}",
            }

    def _search_recipes(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Search recipes with filters."""
        query = arguments.get("query")
        max_time = arguments.get("max_prep_time")
        min_rating = arguments.get("min_rating")

        try:
            all_recipes = pantry_manager.get_all_recipes()
            filtered = []

            for recipe in all_recipes:
                if query and query.lower() not in recipe.get("name", "").lower():
                    continue
                if max_time and recipe.get("time_minutes", 0) > max_time:
                    continue
                if min_rating and recipe.get("rating", 0) < min_rating:
                    continue
                filtered.append(recipe)

            return {"status": "success", "recipes": filtered}
        except Exception as e:
            return {"status": "error", "message": f"Failed to search recipes: {str(e)}"}

    def _check_recipe_feasibility(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Check if recipe can be made with current pantry."""
        recipe_name = arguments["recipe_name"]
        servings = arguments.get("servings", 4)

        try:
            recipe = pantry_manager.get_recipe(recipe_name)
            if not recipe:
                return {
                    "status": "error",
                    "message": f"Recipe '{recipe_name}' not found",
                }

            pantry_contents = pantry_manager.get_pantry_contents()
            missing = []
            available = []

            for ingredient in recipe.get("ingredients", []):
                ing_name = ingredient["name"]
                needed_qty = ingredient["quantity"] * (
                    servings / 4
                )  # Assume recipe serves 4
                needed_unit = ingredient["unit"]

                if (
                    ing_name in pantry_contents
                    and needed_unit in pantry_contents[ing_name]
                ):
                    have_qty = pantry_contents[ing_name][needed_unit]
                    if have_qty >= needed_qty:
                        available.append(
                            {
                                "name": ing_name,
                                "needed": needed_qty,
                                "have": have_qty,
                                "unit": needed_unit,
                            }
                        )
                    else:
                        missing.append(
                            {
                                "name": ing_name,
                                "needed": needed_qty,
                                "have": have_qty,
                                "shortage": needed_qty - have_qty,
                                "unit": needed_unit,
                            }
                        )
                else:
                    missing.append(
                        {
                            "name": ing_name,
                            "needed": needed_qty,
                            "have": 0,
                            "shortage": needed_qty,
                            "unit": needed_unit,
                        }
                    )

            return {
                "status": "success",
                "recipe_name": recipe_name,
                "servings": servings,
                "feasible": len(missing) == 0,
                "available_ingredients": available,
                "missing_ingredients": missing,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check feasibility: {str(e)}",
            }

    def _get_food_preferences(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get food preferences."""
        try:
            preferences = pantry_manager.get_preferences()
            pref_type = arguments.get("preference_type")

            if pref_type:
                preferences = [p for p in preferences if p.get("category") == pref_type]

            return {"status": "success", "preferences": preferences}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get preferences: {str(e)}",
            }

    def _clear_meal_plan(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Clear meal plan for specified period."""
        start_date = arguments["start_date"]
        days = arguments.get("days", 7)

        try:
            success_count = 0
            start = datetime.strptime(start_date, "%Y-%m-%d").date()

            for i in range(days):
                current_date = start + timedelta(days=i)
                # Try to clear by setting empty meal plan (implementation dependent)
                if pantry_manager.set_meal_plan(
                    current_date.strftime("%Y-%m-%d"), None
                ):
                    success_count += 1

            return {
                "status": "success",
                "message": f"Cleared {success_count} days from meal plan",
                "cleared_days": success_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to clear meal plan: {str(e)}",
            }

    def _add_preference(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Add a food preference."""
        try:
            success = pantry_manager.add_preference(
                category=arguments["category"],
                item=arguments["item"],
                level=arguments["level"],
                notes=arguments.get("notes"),
            )

            if success:
                return {
                    "status": "success",
                    "message": f"Added {arguments['category']} preference for {arguments['item']}",
                }
            else:
                return {"status": "error", "message": "Failed to add preference"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to add preference: {str(e)}"}

    def _execute_recipe(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Execute a recipe by removing ingredients from pantry."""
        recipe_name = arguments["recipe_name"]

        try:
            # Get recipe details
            recipe = pantry_manager.get_recipe(recipe_name)
            if not recipe:
                return {
                    "status": "error",
                    "message": f"Recipe '{recipe_name}' not found",
                }

            # Remove ingredients from pantry
            success_count = 0
            errors = []

            for ingredient in recipe.get("ingredients", []):
                try:
                    success = pantry_manager.remove_item(
                        ingredient["name"],
                        ingredient["quantity"],
                        ingredient["unit"],
                        f"Used for {recipe_name}",
                    )
                    if success:
                        success_count += 1
                    else:
                        errors.append(f"Could not remove {ingredient['name']}")
                except Exception as e:
                    errors.append(f"Error removing {ingredient['name']}: {str(e)}")

            if success_count > 0:
                return {
                    "status": "success",
                    "message": f"Recipe '{recipe_name}' executed, removed {success_count} ingredients",
                    "removed_ingredients": success_count,
                    "errors": errors,
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to remove any ingredients",
                    "errors": errors,
                }

        except Exception as e:
            return {"status": "error", "message": f"Failed to execute recipe: {str(e)}"}

    def _get_week_plan(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Get the meal plan for the next 7 days."""
        try:
            from datetime import date, timedelta

            start_date = date.today()
            end_date = start_date + timedelta(days=6)

            meal_plan = pantry_manager.get_meal_plan(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            return {"status": "success", "meal_plan": meal_plan}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get week plan: {str(e)}"}

    def _set_recipe_for_date(
        self, arguments: Dict[str, Any], pantry_manager
    ) -> Dict[str, Any]:
        """Set a recipe for a specific date."""
        try:
            success = pantry_manager.set_meal_plan(
                arguments["meal_date"], arguments["recipe_name"]
            )

            if success:
                return {
                    "status": "success",
                    "message": f"Set '{arguments['recipe_name']}' for {arguments['meal_date']}",
                }
            else:
                return {"status": "error", "message": "Failed to set recipe for date"}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set recipe for date: {str(e)}",
            }

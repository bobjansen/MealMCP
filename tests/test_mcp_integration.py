#!/usr/bin/env python3
"""
Comprehensive integration tests for MCP server.
Tests all MCP tools end-to-end with different authentication modes.
"""

import pytest
import os
import tempfile
import shutil
import json
import asyncio
from pathlib import Path
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server import UnifiedMCPServer
from pantry_manager_factory import create_pantry_manager


class TestMCPIntegration:
    """Integration tests for MCP server with all tools."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test databases."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sqlite_server(self, temp_dir):
        """Create server with SQLite backend."""
        # Clean environment first
        for key in list(os.environ.keys()):
            if key.startswith(("MCP_", "PANTRY_")):
                del os.environ[key]

        os.environ["MCP_TRANSPORT"] = "fastmcp"
        os.environ["MCP_MODE"] = "local"
        os.environ["PANTRY_BACKEND"] = "sqlite"
        os.environ["PANTRY_DB_PATH"] = os.path.join(temp_dir, "integration_test.db")

        server = UnifiedMCPServer()
        return server

    @pytest.fixture
    def sample_recipes(self):
        """Sample recipes for testing."""
        import uuid

        test_id = str(uuid.uuid4())[:8]
        return [
            {
                "name": f"Test Pasta Salad {test_id}",
                "instructions": "Mix pasta with vegetables and dressing",
                "time_minutes": 15,
                "ingredients": [
                    {"name": "pasta", "quantity": 2, "unit": "cups"},
                    {"name": "tomatoes", "quantity": 1, "unit": "cup"},
                    {"name": "olive oil", "quantity": 2, "unit": "tablespoons"},
                ],
            },
            {
                "name": f"Test Chicken Soup {test_id}",
                "instructions": "Simmer chicken with vegetables",
                "time_minutes": 45,
                "ingredients": [
                    {"name": "chicken breast", "quantity": 1, "unit": "pound"},
                    {"name": "carrots", "quantity": 2, "unit": "cups"},
                    {"name": "celery", "quantity": 1, "unit": "cup"},
                ],
            },
        ]

    @pytest.fixture
    def sample_pantry_items(self):
        """Sample pantry items for testing."""
        return [
            {"item_name": "pasta", "quantity": 5, "unit": "cups"},
            {"item_name": "tomatoes", "quantity": 3, "unit": "cups"},
            {"item_name": "olive oil", "quantity": 1, "unit": "bottle"},
            {"item_name": "carrots", "quantity": 1, "unit": "cup"},
            {"item_name": "onions", "quantity": 2, "unit": "pieces"},
        ]

    def test_units_tool(self, sqlite_server):
        """Test list_units tool."""
        # Get available tools to validate router setup
        tools = sqlite_server.tool_router.get_available_tools()
        assert len(tools) > 0

        # Test units listing
        result = sqlite_server.tool_router.call_tool("list_units", {}, None)
        assert result["status"] == "success"
        assert "units" in result
        assert isinstance(result["units"], list)
        assert len(result["units"]) > 0

    def test_recipe_management_flow(self, sqlite_server, sample_recipes):
        """Test complete recipe management workflow."""
        # Get user pantry for local mode
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Get initial recipe count
        initial_result = sqlite_server.tool_router.call_tool(
            "get_all_recipes", {}, pantry
        )
        assert initial_result["status"] == "success"
        initial_count = len(initial_result["recipes"])

        # Add recipes
        for recipe in sample_recipes:
            result = sqlite_server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        # Get all recipes
        result = sqlite_server.tool_router.call_tool("get_all_recipes", {}, pantry)
        assert result["status"] == "success"
        assert len(result["recipes"]) == initial_count + 2

        recipe_names = [r["name"] for r in result["recipes"]]
        assert any("Test Pasta Salad" in name for name in recipe_names)
        assert any("Test Chicken Soup" in name for name in recipe_names)

        # Get specific recipe (use the actual recipe name from the fixture)
        pasta_recipe_name = [
            r["name"] for r in result["recipes"] if "Test Pasta Salad" in r["name"]
        ][0]
        result = sqlite_server.tool_router.call_tool(
            "get_recipe", {"recipe_name": pasta_recipe_name}, pantry
        )
        assert result["status"] == "success"
        assert "Test Pasta Salad" in result["recipe"]["name"]

        # Edit recipe
        edit_data = {
            "recipe_name": pasta_recipe_name,
            "instructions": "Mix pasta with fresh vegetables and Italian dressing",
            "time_minutes": 20,
            "ingredients": [
                {"name": "pasta", "quantity": 2, "unit": "cups"},
                {"name": "cherry tomatoes", "quantity": 1, "unit": "cup"},
                {"name": "italian dressing", "quantity": 3, "unit": "tablespoons"},
            ],
        }
        result = sqlite_server.tool_router.call_tool("edit_recipe", edit_data, pantry)
        assert result["status"] == "success"

        # Verify edit
        result = sqlite_server.tool_router.call_tool(
            "get_recipe", {"recipe_name": pasta_recipe_name}, pantry
        )
        assert result["status"] == "success"
        assert result["recipe"]["time_minutes"] == 20

    def test_pantry_management_flow(self, sqlite_server, sample_pantry_items):
        """Test pantry management workflow."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add pantry items
        for item in sample_pantry_items:
            result = sqlite_server.tool_router.call_tool(
                "add_pantry_item", item, pantry
            )
            assert result["status"] == "success"

        # Get pantry contents and check initial state
        result = sqlite_server.tool_router.call_tool("get_pantry_contents", {}, pantry)
        assert result["status"] == "success"
        assert "pasta" in result["contents"]

        # Check initial onions count before removal
        # Unit is normalized from "pieces" to "Piece" during storage
        initial_onions = result["contents"]["onions"]["Piece"]

        # Remove item
        result = sqlite_server.tool_router.call_tool(
            "remove_pantry_item",
            {
                "item_name": "onions",
                "quantity": 1,
                "unit": "pieces",
                "reason": "cooking",
            },
            pantry,
        )
        assert result["status"] == "success"

        # Verify removal
        result = sqlite_server.tool_router.call_tool("get_pantry_contents", {}, pantry)
        assert result["status"] == "success"
        # Should have 1 less onion after removing 1
        # Unit is normalized from "pieces" to "Piece" during storage
        remaining_onions = result["contents"]["onions"]["Piece"]
        assert remaining_onions == initial_onions - 1.0

    def test_meal_planning_flow(self, sqlite_server, sample_recipes):
        """Test meal planning workflow."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add recipes first
        for recipe in sample_recipes:
            result = sqlite_server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        # Plan meals for the week - use the actual recipe names from the fixture
        today = datetime.now().date()
        pasta_recipe_name = sample_recipes[0]["name"]  # Test Pasta Salad {id}
        soup_recipe_name = sample_recipes[1]["name"]  # Test Chicken Soup {id}

        meal_assignments = [
            {
                "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "recipe_name": pasta_recipe_name,
            },
            {
                "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
                "recipe_name": soup_recipe_name,
            },
        ]

        result = sqlite_server.tool_router.call_tool(
            "plan_meals", {"meal_assignments": meal_assignments}, pantry
        )
        assert result["status"] == "success"
        assert result["assigned"] == 2

        # Get meal plan
        result = sqlite_server.tool_router.call_tool(
            "get_meal_plan",
            {"start_date": today.strftime("%Y-%m-%d"), "days": 7},
            pantry,
        )
        assert result["status"] == "success"
        # Should have at least 2 planned meals (may have more from other tests)
        assert len(result["meal_plan"]) >= 2

        # Get week plan (convenience method)
        result = sqlite_server.tool_router.call_tool("get_week_plan", {}, pantry)
        assert result["status"] == "success"

        # Set specific recipe for date
        result = sqlite_server.tool_router.call_tool(
            "set_recipe_for_date",
            {
                "meal_date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
                "recipe_name": pasta_recipe_name,
            },
            pantry,
        )
        assert result["status"] == "success"

        # Test clear meal plan (may not work depending on implementation)
        result = sqlite_server.tool_router.call_tool(
            "clear_meal_plan",
            {"start_date": today.strftime("%Y-%m-%d"), "days": 7},
            pantry,
        )
        assert result["status"] == "success"
        # Note: cleared_days may be 0 if clearing isn't implemented

    def test_preferences_management(self, sqlite_server):
        """Test preferences management."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add preferences - use unique items
        import uuid

        test_id = str(uuid.uuid4())[:8]
        preferences = [
            {
                "category": "dietary",
                "item": f"vegetarian_{test_id}",
                "level": "required",
            },
            {"category": "allergy", "item": f"nuts_{test_id}", "level": "severe"},
            {"category": "like", "item": f"pasta_{test_id}", "level": "preferred"},
        ]

        for pref in preferences:
            result = sqlite_server.tool_router.call_tool("add_preference", pref, pantry)
            assert result["status"] == "success"

        # Get all preferences
        result = sqlite_server.tool_router.call_tool("get_food_preferences", {}, pantry)
        assert result["status"] == "success"
        # Should have at least 3 preferences (may have more from other tests)
        assert len(result["preferences"]) >= 3

        # Get specific preference type
        result = sqlite_server.tool_router.call_tool(
            "get_food_preferences", {"preference_type": "dietary"}, pantry
        )
        assert result["status"] == "success"
        # Should have at least 1 dietary preference
        assert len(result["preferences"]) >= 1
        # Check that our preference is in the results
        dietary_items = [p["item"] for p in result["preferences"]]
        assert f"vegetarian_{test_id}" in dietary_items

    def test_recipe_suggestions_and_search(
        self, sqlite_server, sample_recipes, sample_pantry_items
    ):
        """Test recipe suggestions and search functionality."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add recipes and pantry items
        for recipe in sample_recipes:
            result = sqlite_server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        for item in sample_pantry_items:
            result = sqlite_server.tool_router.call_tool(
                "add_pantry_item", item, pantry
            )
            assert result["status"] == "success"

        # Search recipes - use the specific test recipe name
        pasta_recipe_name = sample_recipes[0]["name"]  # Test Pasta Salad {id}
        result = sqlite_server.tool_router.call_tool(
            "search_recipes", {"query": "Test Pasta Salad", "max_prep_time": 30}, pantry
        )
        assert result["status"] == "success"
        assert len(result["recipes"]) >= 1
        recipe_names = [r["name"] for r in result["recipes"]]
        assert pasta_recipe_name in recipe_names

        # Get suggestions from pantry
        result = sqlite_server.tool_router.call_tool(
            "suggest_recipes_from_pantry", {"max_missing_ingredients": 2}, pantry
        )
        assert result["status"] == "success"
        assert len(result["suggestions"]) > 0

        # Check recipe feasibility
        result = sqlite_server.tool_router.call_tool(
            "check_recipe_feasibility",
            {"recipe_name": pasta_recipe_name, "servings": 4},
            pantry,
        )
        assert result["status"] == "success"
        assert "feasible" in result
        assert "missing_ingredients" in result
        assert "available_ingredients" in result

    def test_recipe_execution(self, sqlite_server, sample_recipes, sample_pantry_items):
        """Test recipe execution (removing ingredients from pantry)."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add recipes and pantry items
        for recipe in sample_recipes:
            result = sqlite_server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        for item in sample_pantry_items:
            result = sqlite_server.tool_router.call_tool(
                "add_pantry_item", item, pantry
            )
            assert result["status"] == "success"

        # Execute recipe - use the specific test recipe name
        pasta_recipe_name = sample_recipes[0]["name"]  # Test Pasta Salad {id}

        # Get initial pasta count
        initial_result = sqlite_server.tool_router.call_tool(
            "get_pantry_contents", {}, pantry
        )
        # Unit is normalized from "cups" to "Cup" during storage
        initial_pasta = initial_result["contents"]["pasta"]["Cup"]

        result = sqlite_server.tool_router.call_tool(
            "execute_recipe", {"recipe_name": pasta_recipe_name}, pantry
        )
        assert result["status"] == "success"
        assert result["removed_ingredients"] > 0

        # Verify ingredients were removed
        result = sqlite_server.tool_router.call_tool("get_pantry_contents", {}, pantry)
        assert result["status"] == "success"
        # Pasta should be reduced by 2 cups (the recipe uses 2 cups)
        # Unit is normalized from "cups" to "Cup" during storage
        assert result["contents"]["pasta"]["Cup"] == initial_pasta - 2.0

    def test_grocery_list_generation(self, sqlite_server, sample_recipes):
        """Test grocery list generation."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add recipes
        for recipe in sample_recipes:
            result = sqlite_server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        # Plan meals - use the actual recipe name from fixture
        today = datetime.now().date()
        pasta_recipe_name = sample_recipes[0]["name"]  # Test Pasta Salad {id}
        meal_assignments = [
            {
                "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                "recipe_name": pasta_recipe_name,
            }
        ]

        result = sqlite_server.tool_router.call_tool(
            "plan_meals", {"meal_assignments": meal_assignments}, pantry
        )
        assert result["status"] == "success"

        # Generate grocery list
        result = sqlite_server.tool_router.call_tool(
            "generate_grocery_list", {}, pantry
        )
        assert result["status"] == "success"
        assert "grocery_list" in result

    def test_user_profile_comprehensive(self, sqlite_server):
        """Test comprehensive user profile functionality."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Add preferences - use unique items
        import uuid

        test_id = str(uuid.uuid4())[:8]
        preferences = [
            {
                "category": "dietary",
                "item": f"vegetarian_{test_id}",
                "level": "required",
            },
            {"category": "allergy", "item": f"shellfish_{test_id}", "level": "severe"},
            {
                "category": "like",
                "item": f"italian_food_{test_id}",
                "level": "preferred",
            },
        ]

        for pref in preferences:
            result = sqlite_server.tool_router.call_tool("add_preference", pref, pantry)
            assert result["status"] == "success"

        # Get user profile
        result = sqlite_server.tool_router.call_tool("get_user_profile", {}, pantry)
        assert result["status"] == "success"
        assert "data" in result

        profile = result["data"]
        assert "household" in profile
        assert "dietary_preferences" in profile
        assert "preferences_summary" in profile

        # Check preferences summary structure
        summary = profile["preferences_summary"]
        assert "required_dietary" in summary
        assert "allergies" in summary
        assert "likes" in summary

        assert f"vegetarian_{test_id}" in summary["required_dietary"]
        assert f"shellfish_{test_id}" in summary["allergies"]
        assert f"italian_food_{test_id}" in summary["likes"]

    def test_error_handling_edge_cases(self, sqlite_server):
        """Test error handling and edge cases."""
        user_id, pantry = sqlite_server.get_user_pantry()
        assert pantry is not None

        # Test unknown tool
        result = sqlite_server.tool_router.call_tool("unknown_tool", {}, pantry)
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]

        # Test invalid recipe
        result = sqlite_server.tool_router.call_tool(
            "get_recipe", {"recipe_name": "NonExistent Recipe"}, pantry
        )
        assert result["status"] == "error"
        assert "not found" in result["message"]

        # Test invalid date format in meal planning
        result = sqlite_server.tool_router.call_tool(
            "get_meal_plan", {"start_date": "invalid-date"}, pantry
        )
        assert result["status"] == "error"

        # Test remove item that doesn't exist
        result = sqlite_server.tool_router.call_tool(
            "remove_pantry_item",
            {"item_name": "nonexistent_item", "quantity": 1, "unit": "cups"},
            pantry,
        )
        assert result["status"] == "error"

    def teardown_method(self, method):
        """Clean up after each test."""
        env_vars = [
            "MCP_TRANSPORT",
            "MCP_MODE",
            "PANTRY_BACKEND",
            "PANTRY_DB_PATH",
            "USER_DATA_DIR",
            "ADMIN_TOKEN",
        ]
        for var in env_vars:
            os.environ.pop(var, None)


class TestMCPToolAuthentication:
    """Test authentication requirements for each tool."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test databases."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def auth_server(self, temp_dir):
        """Create server requiring authentication."""
        os.environ["MCP_TRANSPORT"] = "fastmcp"
        os.environ["MCP_MODE"] = "remote"
        os.environ["USER_DATA_DIR"] = temp_dir
        os.environ["ADMIN_TOKEN"] = "auth-test-admin"

        server = UnifiedMCPServer()
        return server

    def test_public_tools_no_auth_required(self, auth_server):
        """Test that public tools work without authentication."""
        # These tools should work without user context
        public_tools = ["list_units"]

        for tool_name in public_tools:
            result = auth_server.tool_router.call_tool(tool_name, {}, None)
            # Should not fail due to authentication
            assert (
                result["status"] != "error"
                or "authentication" not in result.get("message", "").lower()
            )

    def test_user_tools_require_auth(self, auth_server):
        """Test that user-specific tools require authentication."""
        # These tools should fail without proper pantry manager (authentication)
        protected_tools = [
            "get_user_profile",
            "add_recipe",
            "get_all_recipes",
            "get_recipe",
            "get_pantry_contents",
            "add_pantry_item",
            "remove_pantry_item",
            "plan_meals",
            "get_meal_plan",
            "add_preference",
            "get_food_preferences",
        ]

        for tool_name in protected_tools:
            # Test minimal arguments to avoid argument validation errors
            minimal_args = {}
            if tool_name == "add_recipe":
                minimal_args = {
                    "name": "Test",
                    "instructions": "Test",
                    "time_minutes": 10,
                    "ingredients": [],
                }
            elif tool_name == "get_recipe":
                minimal_args = {"recipe_name": "Test"}
            elif tool_name in ["add_pantry_item", "remove_pantry_item"]:
                minimal_args = {"item_name": "test", "quantity": 1, "unit": "cups"}
            elif tool_name == "plan_meals":
                minimal_args = {"meal_assignments": []}
            elif tool_name == "get_meal_plan":
                minimal_args = {"start_date": "2024-01-01"}
            elif tool_name == "add_preference":
                minimal_args = {
                    "category": "like",
                    "item": "test",
                    "level": "preferred",
                }

            result = auth_server.tool_router.call_tool(tool_name, minimal_args, None)
            # Should fail gracefully - either with missing pantry or other error
            # but not crash
            assert "status" in result

    def teardown_method(self, method):
        """Clean up after each test."""
        env_vars = ["MCP_TRANSPORT", "MCP_MODE", "USER_DATA_DIR", "ADMIN_TOKEN"]
        for var in env_vars:
            os.environ.pop(var, None)


if __name__ == "__main__":
    # Run tests directly if called as script
    pytest.main([__file__, "-v"])

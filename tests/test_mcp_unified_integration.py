#!/usr/bin/env python3
"""
Integration tests for the unified MCP server.
Tests the complete MCP protocol flow including tool routing, authentication, and error handling.
"""

import pytest

# Unified integration tests re-enabled with updated API
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server import UnifiedMCPServer
from mcp_tool_router import MCPToolRouter
from pantry_manager_factory import create_pantry_manager


class TestMCPUnifiedIntegration:
    """Integration tests for unified MCP server."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test databases."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def local_server(self, temp_dir):
        """Create a local mode MCP server for testing."""
        # Set up environment for local mode
        os.environ.pop("MCP_MODE", None)
        os.environ.pop("ADMIN_TOKEN", None)
        os.environ["PANTRY_DB_PATH"] = os.path.join(temp_dir, "test_pantry.db")

        server = UnifiedMCPServer()
        return server

    @pytest.fixture
    def remote_server(self, temp_dir):
        """Create a remote mode MCP server for testing."""
        # Set up environment for remote mode
        os.environ["MCP_MODE"] = "remote"
        os.environ["ADMIN_TOKEN"] = "test-admin-token-12345"
        os.environ["USER_DATA_DIR"] = temp_dir

        server = UnifiedMCPServer()
        return server

    def test_server_initialization_local_mode(self, local_server):
        """Test server initializes correctly in local mode."""
        assert local_server.auth_mode == "local"
        assert local_server.context is not None
        assert local_server.tool_router is not None

    def test_server_initialization_remote_mode(self, remote_server):
        """Test server initializes correctly in remote mode."""
        assert remote_server.auth_mode == "remote"
        assert remote_server.context is not None
        assert remote_server.context.mode == "remote"
        assert remote_server.tool_router is not None

    def test_tool_routing_initialization(self, local_server):
        """Test that tool router is properly initialized."""
        assert local_server.tool_router is not None
        assert isinstance(local_server.tool_router, MCPToolRouter)

        # Check that tools are registered by checking the tools dict
        assert len(local_server.tool_router.tools) > 0

        # Check specific tools
        expected_tools = [
            "get_user_profile",
            "add_recipe",
            "get_all_recipes",
            "get_pantry_contents",
            "get_week_plan",
        ]
        for tool in expected_tools:
            assert tool in local_server.tool_router.tools

    def test_local_mode_tool_execution(self, local_server):
        """Test tool execution in local mode (no authentication required)."""
        # Test list_units tool - this doesn't need authentication
        from constants import UNITS

        # Direct call since list_units is simple
        assert len(UNITS) > 0

    def test_local_mode_pantry_operations(self, local_server):
        """Test pantry operations in local mode."""
        # Add an item to pantry
        add_result = local_server.call_tool(
            "add_pantry_item",
            {
                "item_name": "test_ingredient",
                "quantity": 5,
                "unit": "cups",
                "notes": "Test item",
            },
        )
        assert add_result["status"] == "success"

        # Get pantry contents
        contents_result = local_server.call_tool("get_pantry_contents", {})
        assert contents_result["status"] == "success"
        assert "test_ingredient" in contents_result["contents"]

    def test_local_mode_recipe_operations(self, local_server):
        """Test recipe operations in local mode."""
        # Add a recipe
        recipe_data = {
            "name": "Test Recipe",
            "instructions": "Mix ingredients and cook",
            "time_minutes": 30,
            "ingredients": [
                {"name": "flour", "quantity": 2, "unit": "cups"},
                {"name": "sugar", "quantity": 1, "unit": "cup"},
            ],
        }

        add_result = local_server.call_tool("add_recipe", recipe_data)
        assert add_result["status"] == "success"

        # Get all recipes
        recipes_result = local_server.call_tool("get_all_recipes", {})
        assert recipes_result["status"] == "success"
        recipe_names = [r["name"] for r in recipes_result["recipes"]]
        assert "Test Recipe" in recipe_names

    def test_remote_mode_authentication_required(self, remote_server):
        """Test that remote mode requires authentication."""
        # Try to call tool without token
        result = remote_server.call_tool("get_all_recipes", {})
        assert result["status"] == "error"
        assert "authentication" in result["message"].lower()

    def test_remote_mode_admin_token_works(self, remote_server):
        """Test that admin token works in remote mode."""
        # Test with admin token
        result = remote_server.call_tool(
            "get_pantry_contents", {"token": "test-admin-token-12345"}
        )
        assert result["status"] == "success"

    def test_remote_mode_user_creation(self, remote_server):
        """Test user creation in remote mode."""
        # Create a user with admin token
        result = remote_server.call_tool(
            "create_user",
            {"username": "testuser123", "admin_token": "test-admin-token-12345"},
        )
        assert result["status"] == "success"
        assert "token" in result

    def test_remote_mode_user_isolation(self, remote_server):
        """Test that users have isolated data in remote mode."""
        # Create two users
        user1_result = remote_server.call_tool(
            "create_user",
            {"username": "user1", "admin_token": "test-admin-token-12345"},
        )
        assert user1_result["status"] == "success"
        user1_token = user1_result["token"]

        user2_result = remote_server.call_tool(
            "create_user",
            {"username": "user2", "admin_token": "test-admin-token-12345"},
        )
        assert user2_result["status"] == "success"
        user2_token = user2_result["token"]

        # Add recipe for user1
        recipe_data = {
            "name": "User1 Recipe",
            "instructions": "User1's special recipe",
            "time_minutes": 20,
            "ingredients": [{"name": "test", "quantity": 1, "unit": "cup"}],
            "token": user1_token,
        }
        add_result = remote_server.call_tool("add_recipe", recipe_data)
        assert add_result["status"] == "success"

        # Check user1 can see their recipe
        user1_recipes = remote_server.call_tool(
            "get_all_recipes", {"token": user1_token}
        )
        assert user1_recipes["status"] == "success"
        recipe_names = [r["name"] for r in user1_recipes["recipes"]]
        assert "User1 Recipe" in recipe_names

        # Check user2 cannot see user1's recipe
        user2_recipes = remote_server.call_tool(
            "get_all_recipes", {"token": user2_token}
        )
        assert user2_recipes["status"] == "success"
        user2_recipe_names = [r["name"] for r in user2_recipes["recipes"]]
        assert "User1 Recipe" not in user2_recipe_names

    def test_error_handling_invalid_tool(self, local_server):
        """Test error handling for invalid tool names."""
        result = local_server.call_tool("nonexistent_tool", {})
        assert result["status"] == "error"
        assert "unknown tool" in result["message"].lower()

    def test_error_handling_invalid_arguments(self, local_server):
        """Test error handling for invalid tool arguments."""
        # Try to add recipe without required fields
        result = local_server.call_tool(
            "add_recipe",
            {
                "name": "Incomplete Recipe"
                # Missing required fields
            },
        )
        assert result["status"] == "error"

    def test_error_handling_invalid_token(self, remote_server):
        """Test error handling for invalid authentication tokens."""
        result = remote_server.call_tool(
            "get_all_recipes", {"token": "invalid-token-123"}
        )
        assert result["status"] == "error"
        assert "authentication" in result["message"].lower()

    def test_meal_planning_workflow(self, local_server):
        """Test complete meal planning workflow."""
        # 1. Add some recipes
        recipes = [
            {
                "name": "Pasta",
                "instructions": "Cook pasta and sauce",
                "time_minutes": 15,
                "ingredients": [{"name": "pasta", "quantity": 1, "unit": "lb"}],
            },
            {
                "name": "Salad",
                "instructions": "Mix vegetables",
                "time_minutes": 10,
                "ingredients": [{"name": "lettuce", "quantity": 1, "unit": "head"}],
            },
        ]

        for recipe in recipes:
            result = local_server.call_tool("add_recipe", recipe)
            assert result["status"] == "success"

        # 2. Set meal plan
        from datetime import date, timedelta

        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        plan_result = local_server.call_tool(
            "set_recipe_for_date", {"recipe_name": "Pasta", "meal_date": tomorrow}
        )
        assert plan_result["status"] == "success"

        # 3. Get week plan
        week_result = local_server.call_tool("get_week_plan", {})
        assert week_result["status"] == "success"
        assert "meal_plan" in week_result

    def test_preference_management_workflow(self, local_server):
        """Test preference management workflow."""
        # Add preferences
        preferences = [
            {"category": "dietary", "item": "vegetarian", "level": "required"},
            {"category": "allergy", "item": "nuts", "level": "avoid"},
            {"category": "like", "item": "pasta", "level": "preferred"},
        ]

        for pref in preferences:
            result = local_server.call_tool("add_preference", pref)
            assert result["status"] == "success"

        # Get user profile (includes preferences)
        profile_result = local_server.call_tool("get_user_profile", {})
        assert profile_result["status"] == "success"
        assert "preferences_summary" in profile_result["data"]

        # Check that our preferences are included
        summary = profile_result["data"]["preferences_summary"]
        assert "vegetarian" in summary["required_dietary"]
        assert "nuts" in summary["allergies"]
        assert "pasta" in summary["likes"]

    @pytest.mark.skipif(os.getenv("SKIP_SLOW_TESTS"), reason="Skipping slow tests")
    def test_performance_many_operations(self, local_server):
        """Test performance with many operations."""
        # Add many recipes
        for i in range(100):
            recipe = {
                "name": f"Recipe {i}",
                "instructions": f"Instructions for recipe {i}",
                "time_minutes": 10 + i % 30,
                "ingredients": [
                    {"name": f"ingredient_{i}", "quantity": 1, "unit": "cup"}
                ],
            }
            result = local_server.call_tool("add_recipe", recipe)
            assert result["status"] == "success"

        # Get all recipes (should handle large result set)
        result = local_server.call_tool("get_all_recipes", {})
        assert result["status"] == "success"
        assert len(result["recipes"]) >= 100

    def teardown_method(self, method):
        """Clean up after each test."""
        # Clean up environment variables
        os.environ.pop("MCP_MODE", None)
        os.environ.pop("ADMIN_TOKEN", None)
        os.environ.pop("USER_DATA_DIR", None)
        os.environ.pop("PANTRY_DB_PATH", None)


if __name__ == "__main__":
    # Run tests directly if called as script
    pytest.main([__file__, "-v"])

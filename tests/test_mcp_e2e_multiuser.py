#!/usr/bin/env python3
"""
End-to-End tests for multi-user MCP server scenarios.
Tests complete workflows with multiple users, data isolation, and concurrent operations.
"""

import pytest
import os
import tempfile
import shutil
import json
import asyncio
import threading
import time
from pathlib import Path
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import requests
from urllib.parse import parse_qs, urlparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server import UnifiedMCPServer


class TestMCPMultiUserE2E:
    """End-to-end tests for multi-user scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def multiuser_sqlite_server(self, temp_dir):
        """Create multi-user server with SQLite backend."""
        os.environ["MCP_TRANSPORT"] = "fastmcp"
        os.environ["MCP_MODE"] = "remote"
        os.environ["PANTRY_BACKEND"] = "sqlite"
        os.environ["USER_DATA_DIR"] = temp_dir
        os.environ["ADMIN_TOKEN"] = "e2e-multiuser-admin-token"

        server = UnifiedMCPServer()
        return server

    @pytest.fixture
    def multiuser_postgresql_server(self, temp_dir):
        """Create multi-user server with PostgreSQL backend (mocked)."""
        os.environ["MCP_TRANSPORT"] = "oauth"
        os.environ["MCP_MODE"] = "multiuser"
        os.environ["PANTRY_BACKEND"] = "postgresql"
        os.environ["PANTRY_DATABASE_URL"] = (
            "postgresql://test:test@localhost/test_mealmcp"
        )
        os.environ["MCP_PUBLIC_URL"] = "http://localhost:8000"

        # Mock PostgreSQL components
        with (
            patch("pantry_manager_shared.SharedPantryManager") as mock_pm,
            patch("mcp_server.OAuthServer") as mock_oauth,
            patch("mcp_server.OAuthFlowHandler") as mock_handler,
        ):

            # Setup mocked pantry manager
            mock_pantry = MagicMock()
            mock_pantry.get_all_recipes.return_value = []
            mock_pantry.add_recipe.return_value = True
            mock_pm.return_value = mock_pantry

            # Setup mocked OAuth server
            mock_oauth_instance = MagicMock()
            mock_oauth_instance.validate_access_token.return_value = {"user_id": "1"}
            mock_oauth.return_value = mock_oauth_instance

            server = UnifiedMCPServer()
            server._mock_pantry = mock_pantry
            server._mock_oauth = mock_oauth_instance
            yield server

    def create_test_users(self, server, num_users=3):
        """Create multiple test users."""
        users = []
        for i in range(num_users):
            username = f"e2e_user_{i}"

            if server.auth_mode == "remote":
                # Create user through user manager
                token = server.context.user_manager.create_user(username)
                users.append((username, token))
            else:
                # Mock OAuth user creation
                users.append((username, f"oauth_token_{i}"))

        return users

    def test_multi_user_data_isolation_complete_workflow(self, multiuser_sqlite_server):
        """Test complete workflow with multiple users showing data isolation."""
        server = multiuser_sqlite_server

        # Create three users
        users = self.create_test_users(server, 3)

        # Each user adds different recipes
        user_recipes = {
            "e2e_user_0": {
                "name": "User0 Special Pasta",
                "instructions": "User 0's secret pasta recipe",
                "time_minutes": 20,
                "ingredients": [
                    {"name": "pasta", "quantity": 2, "unit": "cups"},
                    {"name": "special_sauce", "quantity": 1, "unit": "jar"},
                ],
            },
            "e2e_user_1": {
                "name": "User1 Chicken Curry",
                "instructions": "User 1's family curry recipe",
                "time_minutes": 35,
                "ingredients": [
                    {"name": "chicken", "quantity": 1, "unit": "pound"},
                    {"name": "curry_powder", "quantity": 2, "unit": "tablespoons"},
                ],
            },
            "e2e_user_2": {
                "name": "User2 Veggie Stir Fry",
                "instructions": "User 2's healthy stir fry",
                "time_minutes": 15,
                "ingredients": [
                    {"name": "broccoli", "quantity": 2, "unit": "cups"},
                    {"name": "soy_sauce", "quantity": 3, "unit": "tablespoons"},
                ],
            },
        }

        # Add recipes for each user
        for (username, token), recipe in zip(users, user_recipes.values()):
            user_id, pantry = server.get_user_pantry(token=token)
            assert user_id == username
            assert pantry is not None

            result = server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        # Verify data isolation - each user should only see their own recipes
        for i, (username, token) in enumerate(users):
            user_id, pantry = server.get_user_pantry(token=token)

            result = server.tool_router.call_tool("get_all_recipes", {}, pantry)
            assert result["status"] == "success"
            assert len(result["recipes"]) == 1

            recipe_name = result["recipes"][0]["name"]
            expected_recipes = list(user_recipes.values())
            assert recipe_name == expected_recipes[i]["name"]

            # Verify user cannot see others' recipes
            for j, other_recipe in enumerate(expected_recipes):
                if i != j:
                    result = server.tool_router.call_tool(
                        "get_recipe", {"recipe_name": other_recipe["name"]}, pantry
                    )
                    assert result["status"] == "error"
                    assert "not found" in result["message"]

    def test_multi_user_pantry_isolation(self, multiuser_sqlite_server):
        """Test pantry data isolation between users."""
        server = multiuser_sqlite_server
        users = self.create_test_users(server, 2)

        # User 0 adds items
        username0, token0 = users[0]
        user_id0, pantry0 = server.get_user_pantry(token=token0)

        items_user0 = [
            {"item_name": "user0_pasta", "quantity": 5, "unit": "cups"},
            {"item_name": "user0_sauce", "quantity": 2, "unit": "jars"},
        ]

        for item in items_user0:
            result = server.tool_router.call_tool("add_pantry_item", item, pantry0)
            assert result["status"] == "success"

        # User 1 adds different items
        username1, token1 = users[1]
        user_id1, pantry1 = server.get_user_pantry(token=token1)

        items_user1 = [
            {"item_name": "user1_rice", "quantity": 3, "unit": "cups"},
            {"item_name": "user1_spices", "quantity": 1, "unit": "container"},
        ]

        for item in items_user1:
            result = server.tool_router.call_tool("add_pantry_item", item, pantry1)
            assert result["status"] == "success"

        # Verify isolation
        result0 = server.tool_router.call_tool("get_pantry_contents", {}, pantry0)
        assert result0["status"] == "success"
        assert "user0_pasta" in result0["contents"]
        assert "user1_rice" not in result0["contents"]

        result1 = server.tool_router.call_tool("get_pantry_contents", {}, pantry1)
        assert result1["status"] == "success"
        assert "user1_rice" in result1["contents"]
        assert "user0_pasta" not in result1["contents"]

    def test_multi_user_meal_planning_isolation(self, multiuser_sqlite_server):
        """Test meal planning data isolation."""
        server = multiuser_sqlite_server
        users = self.create_test_users(server, 2)

        # Both users add the same recipe name but different content
        for i, (username, token) in enumerate(users):
            user_id, pantry = server.get_user_pantry(token=token)

            recipe = {
                "name": "Weekly Special",
                "instructions": f"User {i}'s version of weekly special",
                "time_minutes": 20 + i * 5,
                "ingredients": [
                    {"name": f"user{i}_ingredient", "quantity": 1, "unit": "cup"}
                ],
            }

            result = server.tool_router.call_tool("add_recipe", recipe, pantry)
            assert result["status"] == "success"

        # Plan meals for both users
        today = datetime.now().date()
        for i, (username, token) in enumerate(users):
            user_id, pantry = server.get_user_pantry(token=token)

            meal_assignment = {
                "meal_assignments": [
                    {
                        "date": (today + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                        "recipe_name": "Weekly Special",
                    }
                ]
            }

            result = server.tool_router.call_tool("plan_meals", meal_assignment, pantry)
            assert result["status"] == "success"

        # Verify isolation in meal plans
        for i, (username, token) in enumerate(users):
            user_id, pantry = server.get_user_pantry(token=token)

            result = server.tool_router.call_tool(
                "get_meal_plan",
                {"start_date": today.strftime("%Y-%m-%d"), "days": 5},
                pantry,
            )
            assert result["status"] == "success"

            # Each user should see only their own meal plan
            assert len(result["meal_plan"]) == 1
            planned_date = (today + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            assert result["meal_plan"][0]["date"] == planned_date

    def test_concurrent_multi_user_operations(self, multiuser_sqlite_server):
        """Test concurrent operations by multiple users."""
        server = multiuser_sqlite_server
        users = self.create_test_users(server, 4)

        results = []
        errors = []

        def user_operations(username, token, user_index):
            """Operations for a single user to run concurrently."""
            try:
                user_id, pantry = server.get_user_pantry(token=token)
                assert user_id == username

                operations_results = []

                # Add recipe
                recipe = {
                    "name": f"Concurrent Recipe {user_index}",
                    "instructions": f"Recipe by {username}",
                    "time_minutes": 15 + user_index,
                    "ingredients": [
                        {
                            "name": f"ingredient_{user_index}",
                            "quantity": 2,
                            "unit": "cups",
                        }
                    ],
                }
                result = server.tool_router.call_tool("add_recipe", recipe, pantry)
                operations_results.append(("add_recipe", result["status"]))

                # Add pantry items
                for i in range(3):
                    item = {
                        "item_name": f"item_{user_index}_{i}",
                        "quantity": i + 1,
                        "unit": "units",
                    }
                    result = server.tool_router.call_tool(
                        "add_pantry_item", item, pantry
                    )
                    operations_results.append(("add_pantry_item", result["status"]))

                # Add preferences
                pref = {
                    "category": "like",
                    "item": f"food_{user_index}",
                    "level": "preferred",
                }
                result = server.tool_router.call_tool("add_preference", pref, pantry)
                operations_results.append(("add_preference", result["status"]))

                # Get profile
                result = server.tool_router.call_tool("get_user_profile", {}, pantry)
                operations_results.append(("get_user_profile", result["status"]))

                # Plan meal
                today = datetime.now().date()
                meal_assignment = {
                    "meal_assignments": [
                        {
                            "date": (today + timedelta(days=user_index)).strftime(
                                "%Y-%m-%d"
                            ),
                            "recipe_name": f"Concurrent Recipe {user_index}",
                        }
                    ]
                }
                result = server.tool_router.call_tool(
                    "plan_meals", meal_assignment, pantry
                )
                operations_results.append(("plan_meals", result["status"]))

                results.append((username, operations_results))

            except Exception as e:
                errors.append((username, str(e)))

        # Start concurrent operations
        threads = []
        for i, (username, token) in enumerate(users):
            thread = threading.Thread(target=user_operations, args=(username, token, i))
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 4, f"Expected 4 users, got {len(results)}"

        # All operations should succeed
        for username, operations in results:
            assert (
                len(operations) == 7
            )  # 7 operations per user (1 recipe + 3 pantry + 1 pref + 1 profile + 1 meal plan)
            for op_name, status in operations:
                assert status == "success", f"Operation {op_name} failed for {username}"

        # Verify data integrity after concurrent operations
        for i, (username, token) in enumerate(users):
            user_id, pantry = server.get_user_pantry(token=token)

            # Check recipes
            result = server.tool_router.call_tool("get_all_recipes", {}, pantry)
            assert result["status"] == "success"
            assert len(result["recipes"]) == 1
            assert result["recipes"][0]["name"] == f"Concurrent Recipe {i}"

            # Check pantry contents
            result = server.tool_router.call_tool("get_pantry_contents", {}, pantry)
            assert result["status"] == "success"
            assert len(result["contents"]) == 3

            # Check preferences
            result = server.tool_router.call_tool("get_food_preferences", {}, pantry)
            assert result["status"] == "success"
            assert len(result["preferences"]) == 1
            assert result["preferences"][0]["item"] == f"food_{i}"

    def test_multi_user_token_security(self, multiuser_sqlite_server):
        """Test security aspects of multi-user tokens."""
        server = multiuser_sqlite_server
        users = self.create_test_users(server, 3)

        # Test that users cannot access each other's data with wrong tokens
        username0, token0 = users[0]
        username1, token1 = users[1]
        username2, token2 = users[2]

        # User 0 adds a recipe
        user_id0, pantry0 = server.get_user_pantry(token=token0)
        recipe = {
            "name": "Secret Recipe",
            "instructions": "Top secret instructions",
            "time_minutes": 30,
            "ingredients": [
                {"name": "secret_ingredient", "quantity": 1, "unit": "cup"}
            ],
        }
        result = server.tool_router.call_tool("add_recipe", recipe, pantry0)
        assert result["status"] == "success"

        # User 1 tries to access User 0's recipe using User 0's token (should fail)
        # This simulates token theft/misuse
        user_id1, pantry1 = server.get_user_pantry(token=token1)
        result = server.tool_router.call_tool(
            "get_recipe", {"recipe_name": "Secret Recipe"}, pantry1
        )
        assert result["status"] == "error"
        assert "not found" in result["message"]

        # Test token format validation
        invalid_tokens = [
            "invalid-format",
            token0 + "x",  # Modified valid token
            token0[:-1],  # Truncated valid token
            "",
            None,
        ]

        for invalid_token in invalid_tokens:
            if invalid_token is None:
                user_id, pantry = server.get_user_pantry(token=None)
            else:
                user_id, pantry = server.get_user_pantry(token=invalid_token)

            # Should fail authentication
            assert user_id is None or pantry is None

    def test_multi_user_database_cleanup(self, multiuser_sqlite_server):
        """Test that user data is properly isolated in file system."""
        server = multiuser_sqlite_server
        users = self.create_test_users(server, 2)

        user_data_dir = server.context.user_manager.data_dir

        # Add data for both users
        for username, token in users:
            user_id, pantry = server.get_user_pantry(token=token)

            # Add some data to create database files
            result = server.tool_router.call_tool(
                "add_recipe",
                {
                    "name": f"Recipe for {username}",
                    "instructions": "Test recipe",
                    "time_minutes": 10,
                    "ingredients": [],
                },
                pantry,
            )
            assert result["status"] == "success"

        # Verify separate database files exist
        user_dirs = list(user_data_dir.glob("*"))
        assert len(user_dirs) >= 2

        # Each user should have their own directory
        for username, token in users:
            user_dir = user_data_dir / username
            assert user_dir.exists()
            assert user_dir.is_dir()

            # Check for database file
            db_files = list(user_dir.glob("*.db"))
            assert len(db_files) >= 1

    def test_postgresql_multiuser_mocked(self, multiuser_postgresql_server):
        """Test PostgreSQL multi-user mode (mocked)."""
        server = multiuser_postgresql_server

        # Simulate OAuth authentication
        test_user_id = "1"

        # Test getting user pantry in OAuth mode
        user_id, pantry = server._get_user_pantry_oauth(test_user_id)
        assert user_id == test_user_id
        assert pantry is not None

        # Test tool execution with mocked components
        result = server.tool_router.call_tool(
            "get_all_recipes", {}, server._mock_pantry
        )
        assert result["status"] == "success"
        assert result["recipes"] == []

    def teardown_method(self, method):
        """Clean up after each test."""
        env_vars = [
            "MCP_TRANSPORT",
            "MCP_MODE",
            "PANTRY_BACKEND",
            "USER_DATA_DIR",
            "ADMIN_TOKEN",
            "PANTRY_DATABASE_URL",
            "MCP_PUBLIC_URL",
        ]
        for var in env_vars:
            os.environ.pop(var, None)


class TestMCPUserManagement:
    """Test user management operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def admin_server(self, temp_dir):
        """Create server for admin operations testing."""
        os.environ["MCP_TRANSPORT"] = "fastmcp"
        os.environ["MCP_MODE"] = "remote"
        os.environ["USER_DATA_DIR"] = temp_dir
        os.environ["ADMIN_TOKEN"] = "admin-management-token"

        server = UnifiedMCPServer()
        return server

    def test_user_lifecycle_management(self, admin_server):
        """Test complete user lifecycle."""
        # Create user
        result = admin_server.context.user_manager.create_user("lifecycle_user")
        assert result is not None
        token = result

        # Verify user can authenticate
        user_id, pantry = admin_server.context.authenticate_and_get_pantry(token)
        assert user_id == "lifecycle_user"
        assert pantry is not None

        # User adds some data
        recipe = {
            "name": "Lifecycle Recipe",
            "instructions": "Test recipe",
            "time_minutes": 15,
            "ingredients": [{"name": "test", "quantity": 1, "unit": "cup"}],
        }
        result = admin_server.tool_router.call_tool("add_recipe", recipe, pantry)
        assert result["status"] == "success"

        # Verify data exists
        result = admin_server.tool_router.call_tool("get_all_recipes", {}, pantry)
        assert result["status"] == "success"
        assert len(result["recipes"]) == 1

        # List users (if admin functionality exists)
        users = admin_server.context.user_manager.list_users()
        assert "lifecycle_user" in users

    def test_multiple_user_creation_and_management(self, admin_server):
        """Test creating and managing multiple users."""
        usernames = ["mgmt_user_1", "mgmt_user_2", "mgmt_user_3"]
        created_users = []

        # Create multiple users
        for username in usernames:
            token = admin_server.context.user_manager.create_user(username)
            assert token is not None
            created_users.append((username, token))

        # Verify all users can authenticate independently
        for username, token in created_users:
            user_id, pantry = admin_server.context.authenticate_and_get_pantry(token)
            assert user_id == username
            assert pantry is not None

            # Add unique data for each user
            result = admin_server.tool_router.call_tool(
                "add_recipe",
                {
                    "name": f"Recipe by {username}",
                    "instructions": f"Made by {username}",
                    "time_minutes": 20,
                    "ingredients": [
                        {"name": "ingredient", "quantity": 1, "unit": "cup"}
                    ],
                },
                pantry,
            )
            assert result["status"] == "success"

        # Verify data isolation
        for username, token in created_users:
            user_id, pantry = admin_server.context.authenticate_and_get_pantry(token)

            result = admin_server.tool_router.call_tool("get_all_recipes", {}, pantry)
            assert result["status"] == "success"
            assert len(result["recipes"]) == 1
            assert result["recipes"][0]["name"] == f"Recipe by {username}"

    def teardown_method(self, method):
        """Clean up after each test."""
        env_vars = ["MCP_TRANSPORT", "MCP_MODE", "USER_DATA_DIR", "ADMIN_TOKEN"]
        for var in env_vars:
            os.environ.pop(var, None)


if __name__ == "__main__":
    # Run tests directly if called as script
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Simple direct test of MCP server tools.
This bypasses the MCP protocol and directly tests the server functions.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_local_mode():
    """Test the server in local mode."""
    print("🧪 Testing MealMCP Server - Local Mode")
    print("=" * 50)

    # Import the server tools
    try:
        from mcp_server import (
            list_units,
            get_all_recipes,
            get_pantry_contents,
        )

        print("✅ Server modules imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return

    # Test 1: List units
    print("\n2. Testing list_units()...")
    try:
        result = list_units()
        print(
            f"   Found {len(result)} units: {result[:5]}..."
            if len(result) > 5
            else f"   Units: {result}"
        )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Add a preference
    print("\n2. Testing add_preference()...")
    try:
        result = add_preference(
            category="dietary",
            item="vegetarian",
            level="required",
            notes="Test preference",
        )
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: List preferences again (should have our new one)
    print("\n3. Testing get_pantry_contents() after adding one...")
    try:
        result = get_pantry_contents()
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: List recipes (initially empty)
    print("\n4. Testing get_all_recipes()...")
    try:
        result = get_all_recipes()
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n✅ Local mode testing completed!")


def test_remote_mode():
    """Test the server in remote mode with authentication."""
    print("\n🔐 Testing MealMCP Server - Remote Mode")
    print("=" * 50)

    import os

    # Set remote mode
    os.environ["MCP_MODE"] = "remote"
    os.environ["ADMIN_TOKEN"] = "test-admin-token-123"

    # Re-import to get remote mode
    import importlib
    import mcp_server

    importlib.reload(mcp_server)

    from mcp_server import UnifiedMCPServer

    mcp_server = UnifiedMCPServer()

    # Test 1: Try without token (should fail)
    print("\n1. Testing get_pantry_contents() without token (should fail)...")
    try:
        result = mcp_server.get_pantry_contents()
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Try with admin token (should work)
    print("\n2. Testing get_pantry_contents() with admin token...")
    try:
        result = mcp_server.get_pantry_contents(token="test-admin-token-123")
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Create a new user
    print("\n3. Testing create_user()...")
    try:
        result = create_user("testuser", "test-admin-token-123")
        print(f"   Result: {json.dumps(result, indent=2)}")

        if result.get("status") == "success":
            user_token = result.get("token")
            print(f"   🎉 Created user with token: {user_token[:20]}...")

            # Test 4: Use the new user token
            print("\n4. Testing get_pantry_contents() with new user token...")
            try:
                result = get_pantry_contents(token=user_token)
                print(f"   Result: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: List all users
    print("\n5. Testing list_users()...")
    try:
        result = list_users("test-admin-token-123")
        print(f"   Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n✅ Remote mode testing completed!")


def run_all_tests():
    """Run all direct function tests."""
    # Test local mode
    test_local_mode()

    # Test remote mode
    test_remote_mode()

    print("\n🎉 All tests completed!")
    print("\nNext steps:")
    print("1. Try running: uv run python tests/mcp_tests/test_direct_functions.py")
    print("2. Test with Claude Desktop (see claude_desktop_config.json example)")
    print("3. Use the MCP Inspector tool for deeper debugging")


if __name__ == "__main__":
    run_all_tests()

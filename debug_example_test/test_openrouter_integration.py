#!/usr/bin/env python3
"""
Test script for OpenRouter CLI integration
Tests tool conversion and execution without requiring API calls
"""

import json
from openrouter_cli import MCPToolConverter, MealMCPCLI
from mcp_tools import MCP_TOOLS


def test_tool_conversion():
    """Test MCP to OpenAI tool conversion."""
    print("🔄 Testing MCP to OpenAI tool conversion...")

    converter = MCPToolConverter()
    openai_tools = converter.convert_mcp_tools_to_openai(MCP_TOOLS)

    print(
        f"✅ Converted {len(MCP_TOOLS)} MCP tools to {len(openai_tools)} OpenAI format tools"
    )

    # Test a sample tool conversion
    sample_tool = openai_tools[0]
    expected_structure = {
        "type": "function",
        "function": {"name": str, "description": str, "parameters": dict},
    }

    assert sample_tool["type"] == "function"
    assert "name" in sample_tool["function"]
    assert "description" in sample_tool["function"]
    assert "parameters" in sample_tool["function"]

    print(f"✅ Tool structure validation passed")
    print(f"   Sample tool: {sample_tool['function']['name']}")
    return True


def test_tool_execution():
    """Test tool execution without API calls."""
    print("\n🔧 Testing tool execution...")

    # Create CLI instance with dummy API key
    cli = MealMCPCLI("dummy_key", "test_model")

    # Test a simple tool execution
    try:
        result = cli.execute_tool("list_units", {})
        result_data = json.loads(result)

        assert "status" in result_data
        print(f"✅ Tool execution successful: {result_data.get('status', 'unknown')}")

        if result_data["status"] == "success":
            units_count = len(result_data.get("units", []))
            print(f"   Found {units_count} measurement units")

    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        return False

    return True


def test_pantry_operations():
    """Test pantry operations."""
    print("\n📦 Testing pantry operations...")

    cli = MealMCPCLI("dummy_key", "test_model")

    # Test getting pantry contents
    try:
        result = cli.execute_tool("get_pantry_contents", {})
        result_data = json.loads(result)

        print(f"✅ Get pantry contents: {result_data.get('status', 'unknown')}")

        # Test adding an item
        add_result = cli.execute_tool(
            "manage_pantry_item",
            {
                "action": "add",
                "item_name": "test_ingredient",
                "quantity": 1.0,
                "unit": "cup",
                "notes": "Test item for CLI validation",
            },
        )
        add_data = json.loads(add_result)
        print(f"✅ Add pantry item: {add_data.get('status', 'unknown')}")

        # Test removing the item
        remove_result = cli.execute_tool(
            "manage_pantry_item",
            {
                "action": "remove",
                "item_name": "test_ingredient",
                "quantity": 1.0,
                "unit": "cup",
            },
        )
        remove_data = json.loads(remove_result)
        print(f"✅ Remove pantry item: {remove_data.get('status', 'unknown')}")

    except Exception as e:
        print(f"❌ Pantry operations failed: {e}")
        return False

    return True


def test_recipe_operations():
    """Test recipe operations."""
    print("\n👨‍🍳 Testing recipe operations...")

    cli = MealMCPCLI("dummy_key", "test_model")

    try:
        # Test getting all recipes
        result = cli.execute_tool("get_all_recipes", {})
        result_data = json.loads(result)

        print(f"✅ Get all recipes: {result_data.get('status', 'unknown')}")

        if result_data["status"] == "success":
            recipes = result_data.get("recipes", [])
            print(f"   Found {len(recipes)} existing recipes")

    except Exception as e:
        print(f"❌ Recipe operations failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("🧪 Testing OpenRouter CLI Integration")
    print("=" * 50)

    tests = [
        test_tool_conversion,
        test_tool_execution,
        test_pantry_operations,
        test_recipe_operations,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! OpenRouter CLI integration is ready.")
        print("\n💡 Next steps:")
        print("   1. Get an OpenRouter API key from https://openrouter.ai")
        print("   2. Set OPENROUTER_API_KEY environment variable")
        print("   3. Run: uv run openrouter_cli.py")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

    return failed == 0


if __name__ == "__main__":
    main()

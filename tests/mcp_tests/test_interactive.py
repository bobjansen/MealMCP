#!/usr/bin/env python3
"""
Interactive MCP server testing.
This provides a menu-driven interface to test different MCP tools.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def call_tool_direct(tool_name, arguments):
    """Test a specific MCP tool by calling it directly."""
    print(f"\n🔧 Testing {tool_name}...")

    try:
        # Import the tool functions directly
        import mcp_server

        # Get the tool function
        if hasattr(mcp_server, tool_name):
            tool_func = getattr(mcp_server, tool_name)

            # Call the function with arguments
            if arguments:
                result = tool_func(**arguments)
            else:
                result = tool_func()

            print(f"✅ Result: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Tool '{tool_name}' not found")

    except Exception as e:
        print(f"❌ Error: {e}")


def interactive_test():
    """Interactive testing mode."""
    print("\n🎮 Interactive MCP Testing")
    print("=" * 40)
    print("Available commands:")
    print("  1. list_units - Show measurement units")
    print("  2. list_preferences - Show food preferences")
    print("  3. add_preference - Add a food preference")
    print("  4. add_pantry_item - Add item to pantry")
    print("  5. get_pantry_contents - Show pantry contents")
    print("  6. get_all_recipes - Show all recipes")
    print("  7. add_recipe - Add a new recipe")
    print("  8. quit - Exit")

    while True:
        choice = input("\nEnter command number (or 'quit'): ").strip()

        if choice == "quit" or choice == "9":
            break
        elif choice == "1":
            call_tool_direct("list_units", {})
        elif choice == "2":
            call_tool_direct("list_preferences", {})
        elif choice == "3":
            category = input("Category (dietary/allergy/dislike/like): ")
            item = input("Item: ")
            level = input("Level (required/preferred/avoid): ")
            notes = input("Notes (optional): ") or None
            call_tool_direct(
                "add_preference",
                {"category": category, "item": item, "level": level, "notes": notes},
            )
        elif choice == "4":
            item_name = input("Item name: ")
            try:
                quantity = float(input("Quantity: "))
            except ValueError:
                print("❌ Invalid quantity")
                continue
            unit = input("Unit: ")
            notes = input("Notes (optional): ") or None
            call_tool_direct(
                "add_pantry_item",
                {
                    "item_name": item_name,
                    "quantity": quantity,
                    "unit": unit,
                    "notes": notes,
                },
            )
        elif choice == "5":
            call_tool_direct("get_pantry_contents", {})
        elif choice == "6":
            call_tool_direct("get_all_recipes", {})
        elif choice == "7":
            print("Adding a recipe...")
            name = input("Recipe name: ")
            instructions = input("Instructions: ")
            try:
                time_minutes = int(input("Prep time (minutes): "))
            except ValueError:
                print("❌ Invalid time")
                continue

            ingredients = []
            print("Enter ingredients (press Enter with empty name to finish):")
            while True:
                ing_name = input("  Ingredient name: ").strip()
                if not ing_name:
                    break
                try:
                    ing_quantity = float(input("  Quantity: "))
                except ValueError:
                    print("  ❌ Invalid quantity, skipping")
                    continue
                ing_unit = input("  Unit: ")
                ingredients.append(
                    {"name": ing_name, "quantity": ing_quantity, "unit": ing_unit}
                )

            if ingredients:
                call_tool_direct(
                    "add_recipe",
                    {
                        "name": name,
                        "instructions": instructions,
                        "time_minutes": time_minutes,
                        "ingredients": ingredients,
                    },
                )
            else:
                print("❌ No ingredients added, skipping recipe")
        else:
            print("Invalid choice. Try again.")


def quick_test():
    """Run a quick automated test."""
    print("🧪 Quick MCP Server Test")
    print("=" * 30)

    # Test basic functionality
    call_tool_direct("list_units", {})
    call_tool_direct("list_preferences", {})
    call_tool_direct("get_pantry_contents", {})

    print("\n✅ Quick test completed!")


def remote_mode_test():
    """Test remote mode functionality with tokens."""
    print("\n🔐 Remote Mode Interactive Test")
    print("=" * 40)

    # Check if we're in remote mode
    import os

    if os.getenv("MCP_MODE") != "remote":
        print("Setting remote mode for this test...")
        os.environ["MCP_MODE"] = "remote"
        os.environ["ADMIN_TOKEN"] = "test-admin-token-123"

    token = input("Enter your token (or press Enter for admin token): ").strip()
    if not token:
        token = "test-admin-token-123"

    print(f"Testing with token: {token[:20]}...")

    # Test with token
    call_tool_direct("list_preferences", {"token": token})
    call_tool_direct("get_pantry_contents", {"token": token})


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            interactive_test()
        elif sys.argv[1] == "quick":
            quick_test()
        elif sys.argv[1] == "remote":
            remote_mode_test()
        else:
            print("Unknown command:", sys.argv[1])
    else:
        print("Usage:")
        print("  python test_interactive.py interactive  # Interactive menu")
        print("  python test_interactive.py quick        # Quick automated test")
        print("  python test_interactive.py remote       # Test remote mode")
        print("  python test_interactive.py              # Show this help")

#!/usr/bin/env python3
"""
Example usage of OpenRouter CLI integration
Demonstrates how to programmatically interact with the CLI components
"""

import json
import os
from openrouter_cli import MealMCPCLI, MCPToolConverter
from mcp_tools import MCP_TOOLS


def demonstrate_tool_conversion():
    """Show how MCP tools are converted to OpenAI format."""
    print("🔧 MCP Tool Conversion Example")
    print("=" * 40)

    converter = MCPToolConverter()
    openai_tools = converter.convert_mcp_tools_to_openai(MCP_TOOLS)

    # Show a sample converted tool
    sample_tool = openai_tools[2]  # add_recipe tool
    print("Original MCP tool structure -> OpenAI function calling format:")
    print(json.dumps(sample_tool, indent=2))


def demonstrate_programmatic_usage():
    """Show how to use the CLI programmatically."""
    print("\n🤖 Programmatic Usage Example")
    print("=" * 40)

    # Create CLI instance (no API key needed for tool execution)
    cli = MealMCPCLI("dummy_key", "anthropic/claude-3.5-sonnet")

    print("Available tools:", len(cli.openai_tools))
    print("Backend type:", type(cli.pantry_manager).__name__)

    # Example 1: Get user profile
    print("\n📊 Getting user profile...")
    result = cli.execute_tool("get_user_profile", {})
    profile_data = json.loads(result)
    print(f"Status: {profile_data.get('status')}")

    # Example 2: List available recipes
    print("\n👨‍🍳 Listing available recipes...")
    result = cli.execute_tool("get_all_recipes", {})
    recipes_data = json.loads(result)
    if recipes_data["status"] == "success":
        recipes = recipes_data["recipes"]
        print(f"Found {len(recipes)} recipes")
        if recipes:
            print("Sample recipes:")
            for recipe in recipes[:3]:
                print(f"  - {recipe['name']} (Rating: {recipe.get('rating', 'N/A')}/5)")

    # Example 3: Check pantry contents
    print("\n📦 Checking pantry contents...")
    result = cli.execute_tool("get_pantry_contents", {})
    pantry_data = json.loads(result)
    if pantry_data["status"] == "success":
        items = pantry_data.get("pantry_items", pantry_data.get("items", []))
        print(f"Pantry has {len(items)} items")
        if items:
            print("Sample pantry items:")
            for item in items[:3]:
                name = item.get("name", item.get("item_name", "Unknown"))
                quantity = item.get("quantity", 0)
                unit = item.get("unit", "unit")
                print(f"  - {name}: {quantity} {unit}")


def show_sample_conversation_flow():
    """Show what a conversation might look like."""
    print("\n💬 Sample Conversation Flow")
    print("=" * 40)

    conversation_example = [
        {
            "role": "user",
            "content": "I want to plan meals for this week. What recipes do I have that take less than 30 minutes?",
        },
        {
            "role": "assistant",
            "content": "I'll help you find quick recipes for meal planning. Let me search your available recipes.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search_recipes",
                        "arguments": json.dumps({"max_prep_time": 30}),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "search_recipes",
            "content": json.dumps(
                {
                    "status": "success",
                    "recipes": [
                        {"name": "Pasta Aglio e Olio", "time_minutes": 15, "rating": 4},
                        {"name": "Quick Stir Fry", "time_minutes": 20, "rating": 5},
                        {"name": "Scrambled Eggs", "time_minutes": 10, "rating": 3},
                    ],
                }
            ),
        },
        {
            "role": "assistant",
            "content": "Great! I found 3 quick recipes under 30 minutes:\n\n1. **Pasta Aglio e Olio** - 15 min (Rating: 4/5)\n2. **Quick Stir Fry** - 20 min (Rating: 5/5) \n3. **Scrambled Eggs** - 10 min (Rating: 3/5)\n\nWould you like me to create a meal plan using these recipes for the week?",
        },
    ]

    for message in conversation_example:
        role = message["role"].upper()
        content = message.get("content", "")

        if message["role"] == "tool":
            print(f"🔧 TOOL RESULT ({message['name']}):")
            tool_result = json.loads(message["content"])
            if tool_result["status"] == "success":
                recipes = tool_result["recipes"]
                print(f"   Found {len(recipes)} recipes")
        else:
            print(f"{role}: {content}")

        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                print(f"🔧 TOOL CALL: {func_name}({args})")

        print()


def main():
    """Run the demonstration."""
    print("🚀 OpenRouter CLI Integration - Examples & Demonstrations")
    print("=" * 60)

    print("This demonstrates the OpenRouter CLI that integrates with your")
    print("MealMCP system to provide LLM-powered meal planning through")
    print("natural language conversations.")
    print()

    demonstrate_tool_conversion()
    demonstrate_programmatic_usage()
    show_sample_conversation_flow()

    print("🎯 Key Benefits:")
    print("=" * 20)
    print("✅ Natural language interface to your meal planning system")
    print("✅ Access to 30+ LLM models through OpenRouter")
    print("✅ Full integration with existing MCP tools (29 tools available)")
    print("✅ Conversation memory and context handling")
    print("✅ Rich terminal interface with beautiful formatting")
    print("✅ Works with both SQLite (single-user) and PostgreSQL (multi-user)")
    print()
    print("🚀 Ready to use! Set OPENROUTER_API_KEY and run:")
    print("   uv run openrouter_cli.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Debug tool conversation flow to find 404 issue
"""

import os
import json
from openrouter_cli import MealMCPCLI, ConversationManager


def debug_conversation_after_tool():
    """Debug what happens to conversation after tool calls."""

    api_key = os.getenv("OPENROUTER_API_KEY", "dummy")
    cli = MealMCPCLI(api_key, "anthropic/claude-3-haiku")

    # Simulate the conversation flow that causes 404
    print("🔄 Simulating conversation flow that causes 404...")

    # Step 1: User asks for recipe
    cli.conversation.add_user_message("Can you look for a salad in my database")
    print(f"📝 After user message: {len(cli.conversation.messages)} messages")

    # Step 2: Assistant responds with tool call (simulate)
    assistant_message_with_tools = {
        "role": "assistant",
        "content": "I'll search for salad recipes in your database.",
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "search_recipes",
                    "arguments": json.dumps({"query": "salad"}),
                },
            }
        ],
    }

    tool_calls = assistant_message_with_tools["tool_calls"]
    cli.conversation.add_assistant_message(
        assistant_message_with_tools["content"], tool_calls
    )
    print(
        f"📝 After assistant message with tool calls: {len(cli.conversation.messages)} messages"
    )

    # Step 3: Execute tool and add result
    tool_call = tool_calls[0]
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    tool_call_id = tool_call["id"]

    # Execute the tool
    result = cli.execute_tool(tool_name, arguments)
    print(f"🔧 Tool execution result length: {len(result)} chars")

    # Add tool result
    cli.conversation.add_tool_result(tool_call_id, tool_name, result)
    print(f"📝 After tool result: {len(cli.conversation.messages)} messages")

    # Step 4: Inspect the full conversation
    messages = cli.conversation.get_messages()
    print(f"\n🔍 Full conversation structure:")
    for i, msg in enumerate(messages):
        print(f"  Message {i+1}: role={msg['role']}")
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            print(f"    - Content: {msg.get('content', '')[:50]}...")
            print(f"    - Tool calls: {len(msg['tool_calls'])}")
        elif msg["role"] == "tool":
            print(f"    - Tool: {msg.get('name')}")
            print(f"    - Call ID: {msg.get('tool_call_id')}")
            print(f"    - Content length: {len(msg.get('content', ''))}")
        else:
            print(f"    - Content: {msg.get('content', '')[:50]}...")

    # Step 5: Test what happens when we send this to API
    print(f"\n📡 Testing API call with {len(messages)} messages...")

    try:
        # This is where the 404 likely happens
        payload = {
            "model": "anthropic/claude-3-haiku",
            "messages": messages,
            "tools": cli.openai_tools[:1],  # Just one tool for testing
            "tool_choice": "auto",
            "max_tokens": 100,
        }

        print("📤 Payload structure:")
        print(f"  - Model: {payload['model']}")
        print(f"  - Messages: {len(payload['messages'])}")
        print(f"  - Tools: {len(payload['tools'])}")

        # Check for any problematic content in messages
        for i, msg in enumerate(messages):
            if msg["role"] == "tool":
                content = msg.get("content", "")
                print(f"  - Tool message {i}: {len(content)} chars")

                # Check if content is valid JSON
                try:
                    json.loads(content)
                    print(f"    ✅ Valid JSON")
                except:
                    print(f"    ❌ Invalid JSON: {content[:100]}...")

        # Don't actually make the request, just analyze
        print("📊 Analysis complete - this would be sent to OpenRouter")

    except Exception as e:
        print(f"❌ Error preparing payload: {e}")


if __name__ == "__main__":
    print("🐛 Debug Tool Conversation Flow")
    print("=" * 40)
    debug_conversation_after_tool()

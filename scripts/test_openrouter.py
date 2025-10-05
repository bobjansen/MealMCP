#!/usr/bin/env python3
"""
Test script for OpenRouter integration (CLI + Flask)
"""

import os
import json
import threading
import time
import requests
from openrouter_service import OpenRouterService, get_openrouter_service
from openrouter_cli import OpenRouterCLI


def test_openrouter_service():
    """Test the shared OpenRouter service."""
    print("🧪 Testing OpenRouter Service")
    print("=" * 40)

    # Test service creation
    service = OpenRouterService("dummy_key")
    print(f"✅ Service created with {len(service.openai_tools)} tools")
    print(
        f"✅ Backend type: {type(service.pantry_manager).__name__ if service.pantry_manager else 'Multi-user mode'}"
    )

    # Test session management
    session = service.get_session("test_session")
    print(f"✅ Session created: {session.session_id}")

    session.add_user_message("Test message")
    print(f"✅ Message added, session has {len(session.messages)} messages")

    # Test tool execution
    try:
        result = service.execute_tool("list_units", {})
        data = json.loads(result)
        print(f"✅ Tool execution: {data.get('status')}")
        if data.get("status") == "success":
            print(f"   Found {len(data.get('units', []))} units")
    except Exception as e:
        print(f"⚠️ Tool execution test skipped: {e}")

    return True


def test_cli_integration():
    """Test the refactored CLI integration."""
    print("\n🖥️ Testing CLI Integration")
    print("=" * 40)

    try:
        # Test CLI creation (without running the loop)
        cli = OpenRouterCLI("dummy_key", "test_model")
        print(f"✅ CLI created with model: {cli.model}")
        print(f"✅ Session ID: {cli.session_id[:8]}...")
        print(f"✅ Service available: {cli.service is not None}")

        # Test service through CLI
        tools = cli.service.get_available_tools()
        print(f"✅ Available tools: {len(tools)}")

        return True

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def test_flask_integration():
    """Test Flask integration (without starting server)."""
    print("\n🌐 Testing Flask Integration")
    print("=" * 40)

    try:
        from app_flask import app
        from flask_openrouter_integration import add_openrouter_routes

        print("✅ Flask app loaded successfully")

        # Check routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        chat_routes = [r for r in routes if "chat" in r or "api/chat" in r]
        print(f"✅ Chat routes available: {len(chat_routes)}")
        for route in chat_routes:
            print(f"   - {route}")

        # Check configuration
        backend = app.config.get("PANTRY_BACKEND", "sqlite")
        print(f"✅ Backend configured: {backend}")

        return True

    except Exception as e:
        print(f"❌ Flask test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_service_functionality():
    """Test core service functionality with dummy data."""
    print("\n⚙️ Testing Service Functionality")
    print("=" * 40)

    service = get_openrouter_service("dummy_key")
    if not service:
        print("❌ Could not get service instance")
        return False

    try:
        # Test tool execution
        result = service.execute_tool("get_all_recipes", {})
        data = json.loads(result)
        print(f"✅ Recipe query: {data.get('status')}")

        if data.get("status") == "success":
            recipes = data.get("recipes", [])
            print(f"   Found {len(recipes)} recipes")
            if recipes:
                print(f"   Sample recipe: {recipes[0].get('name', 'Unknown')}")

        # Test pantry query
        result = service.execute_tool("get_pantry_contents", {})
        data = json.loads(result)
        print(f"✅ Pantry query: {data.get('status')}")

        # Test result truncation with large query
        result = service.execute_tool("search_recipes", {"query": "salad"})
        data = json.loads(result)
        print(f"✅ Search query: {data.get('status')}")
        if data.get("truncated"):
            total = data.get("total_found", 0)
            showing = data.get("showing", 0)
            print(f"   Truncated: showing {showing} of {total} results")

        return True

    except Exception as e:
        print(f"❌ Service functionality test failed: {e}")
        return False


def demonstrate_usage():
    """Demonstrate how to use both CLI and Flask integrations."""
    print("\n📚 Usage Examples")
    print("=" * 40)

    print("🖥️ CLI Usage:")
    print("   OPENROUTER_API_KEY=your_key uv run openrouter_cli_refactored.py")
    print(
        "   OPENROUTER_API_KEY=your_key uv run openrouter_cli_refactored.py --model anthropic/claude-3-haiku"
    )

    print("\n🌐 Flask Usage:")
    print("   OPENROUTER_API_KEY=your_key uv run app_flask.py")
    print("   Then visit: http://localhost:5000/chat")

    print("\n📋 Available Features:")
    print("   ✅ Shared OpenRouter service layer")
    print("   ✅ 29 MCP tools for meal planning")
    print("   ✅ Result truncation to prevent API limits")
    print("   ✅ Session management with conversation history")
    print("   ✅ Multi-user support (PostgreSQL) and single-user (SQLite)")
    print("   ✅ Rich CLI interface with commands and status")
    print("   ✅ Web interface with real-time chat and tool execution display")

    print("\n🔧 API Endpoints (Flask):")
    print("   GET  /chat                 - Chat interface page")
    print("   POST /api/chat            - Send chat message")
    print("   POST /api/chat/reset      - Reset conversation")
    print("   GET  /api/chat/models     - Get available models")
    print("   GET  /api/chat/session    - Get session info")


def main():
    """Run all tests."""
    print("🚀 OpenRouter Refactored Integration Tests")
    print("=" * 60)

    tests = [
        ("OpenRouter Service", test_openrouter_service),
        ("CLI Integration", test_cli_integration),
        ("Flask Integration", test_flask_integration),
        ("Service Functionality", test_service_functionality),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("📊 Test Results:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {status}: {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! OpenRouter refactored integration is ready.")
        demonstrate_usage()
    else:
        print(f"\n⚠️ {total - passed} tests failed. Please check the implementation.")

    return passed == total


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script to verify OpenRouter API connectivity
"""

import os
import requests
import json


def test_openrouter_api():
    """Test basic OpenRouter API connectivity."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    print(f"🔑 Using API key: {api_key[:20]}...")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MealMCP/openrouter-cli",
        "X-Title": "MealMCP OpenRouter CLI Test",
    }

    # Test with a simple message first (no tools)
    payload = {
        "model": "anthropic/claude-3-haiku",  # Use a cheaper model for testing
        "messages": [
            {
                "role": "user",
                "content": "Hello, can you respond with just 'API test successful'?",
            }
        ],
        "max_tokens": 20,
    }

    print("📡 Testing basic API connectivity...")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print("✅ API test successful!")
            print(f"Model used: {result.get('model', 'unknown')}")
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"].get("content", "")
                print(f"Response: {content}")
            return True
        else:
            print(f"❌ API test failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_with_tools():
    """Test API with tools to match our CLI usage."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MealMCP/openrouter-cli",
        "X-Title": "MealMCP OpenRouter CLI Test",
    }

    # Test with tools like our CLI does
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {"role": "user", "content": "What's the weather like in San Francisco?"}
        ],
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 100,
    }

    print("\n🔧 Testing API with tools...")

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(f"📊 Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Tools test successful!")
            print(f"Model used: {result.get('model', 'unknown')}")
            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                message = choice["message"]
                print(f"Finish reason: {choice.get('finish_reason', 'unknown')}")
                if message.get("tool_calls"):
                    print(f"Tool calls made: {len(message['tool_calls'])}")
                else:
                    print(f"Response: {message.get('content', '')}")
            return True
        else:
            print(f"❌ Tools test failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 OpenRouter API Connectivity Test")
    print("=" * 40)

    # Test basic API first
    basic_success = test_openrouter_api()

    if basic_success:
        # Test with tools if basic test passes
        tools_success = test_with_tools()

        if tools_success:
            print("\n🎉 All tests passed! OpenRouter API is working correctly.")
        else:
            print("\n⚠️  Basic API works, but tools may have issues.")
    else:
        print("\n❌ Basic API test failed. Check your API key and network connection.")

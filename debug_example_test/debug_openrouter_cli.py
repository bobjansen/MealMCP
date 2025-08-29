#!/usr/bin/env python3
"""
Debug version of OpenRouter CLI to diagnose 404 errors
"""

import os
import requests
import json
from openrouter_cli import MealMCPCLI


def debug_cli_request():
    """Debug what the CLI is actually sending."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return

    print(f"🔑 Using API key: {api_key[:20]}...")

    # Create CLI instance
    cli = MealMCPCLI(api_key, "anthropic/claude-3-haiku")

    # Check the client setup
    print(f"📡 Base URL: {cli.client.base_url}")
    print(f"📊 Session headers: {dict(cli.client.session.headers)}")

    # Test simple message first
    messages = [{"role": "user", "content": "Hello"}]

    print("\n🧪 Testing simple message (no tools)...")
    try:
        # Make the request manually to see what happens
        payload = {
            "model": "anthropic/claude-3-haiku",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 100,
            "stream": False,
        }

        print(f"📤 Payload: {json.dumps(payload, indent=2)}")

        response = cli.client.session.post(
            f"{cli.client.base_url}/chat/completions", json=payload
        )

        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response URL: {response.url}")

        if response.status_code != 200:
            print(f"❌ Error response: {response.text}")
        else:
            print("✅ Simple request successful!")
            result = response.json()
            print(f"Model: {result.get('model')}")

    except Exception as e:
        print(f"❌ Simple request failed: {e}")
        return

    # Test with tools
    print("\n🔧 Testing with tools...")
    try:
        result = cli.client.chat_completion(
            messages=messages,
            model="anthropic/claude-3-haiku",
            tools=cli.openai_tools[:1],  # Just use one tool for testing
            max_tokens=100,
        )

        print("✅ Tools request successful!")
        print(f"Model: {result.get('model')}")

    except Exception as e:
        print(f"❌ Tools request failed: {e}")


if __name__ == "__main__":
    print("🐛 Debug OpenRouter CLI")
    print("=" * 30)
    debug_cli_request()

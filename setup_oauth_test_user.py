#!/usr/bin/env python3
"""
OAuth Test User Setup Script

This script registers a test user for OAuth sequence tracing.
It handles both the web form registration and direct database user creation.

Usage:
    python setup_oauth_test_user.py [--server-url URL] [--username USER] [--password PASS]
"""

import os
import sys
import json
import argparse
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests package not installed. Install with:")
    print("pip install requests")
    sys.exit(1)


def register_user_via_web(
    server_url: str, username: str, email: str, password: str
) -> bool:
    """Register a user via the web interface."""
    print(f"🌐 Registering user via web interface at {server_url}")

    # First, get the registration form
    try:
        response = requests.get(f"{server_url}/register_user")
        if response.status_code != 200:
            print(f"❌ Failed to get registration form: {response.status_code}")
            return False

        print("✅ Registration form retrieved")

        # Submit registration
        form_data = {"username": username, "email": email, "password": password}

        response = requests.post(f"{server_url}/register_user", data=form_data)

        if response.status_code == 200 and "successful" in response.text.lower():
            print(f"✅ User '{username}' registered successfully")
            return True
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {server_url}")
        print("   Make sure the OAuth server is running")
        return False
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False


def register_user_via_database(username: str, email: str, password: str) -> bool:
    """Register a user directly in the database (PostgreSQL backend)."""
    print(f"💾 Registering user directly in database")

    try:
        # Check if we have database access
        database_url = os.getenv("PANTRY_DATABASE_URL")
        if not database_url:
            print("❌ PANTRY_DATABASE_URL not set - cannot register user directly")
            return False

        # Import database components
        from mcpnp.auth.oauth_server import OAuthServer

        oauth_server = OAuthServer(
            base_url="http://localhost:8000", use_postgresql=True  # Dummy URL
        )

        success = oauth_server.register_user(username, email, password)

        if success:
            print(f"✅ User '{username}' registered directly in database")
            return True
        else:
            print(f"❌ Database registration failed - user might already exist")
            return False

    except ImportError as e:
        print(f"❌ Cannot import OAuth components: {e}")
        return False
    except Exception as e:
        print(f"❌ Database registration error: {e}")
        return False


def check_user_exists(server_url: str, username: str) -> bool:
    """Check if a user can authenticate (i.e., exists)."""
    print(f"🔍 Checking if user '{username}' exists...")

    try:
        # Try to get the authorization page with dummy client
        params = {
            "response_type": "code",
            "client_id": "test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read write",
        }

        response = requests.get(f"{server_url}/authorize", params=params)

        if response.status_code == 200:
            print("✅ Server is responding to auth requests")
            return True
        else:
            print(f"⚠️  Server returned {response.status_code} for auth request")
            return False

    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup OAuth test user")
    parser.add_argument(
        "--server-url", default="http://localhost:8000", help="OAuth server base URL"
    )
    parser.add_argument("--username", default="testuser", help="Username to create")
    parser.add_argument("--email", default="test@example.com", help="Email address")
    parser.add_argument("--password", default="testpass", help="Password")
    parser.add_argument(
        "--database-direct",
        action="store_true",
        help="Register directly in database instead of web form",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if user exists, don't register",
    )

    args = parser.parse_args()

    print("🔧 OAuth Test User Setup")
    print("=" * 40)
    print(f"Server URL: {args.server_url}")
    print(f"Username: {args.username}")
    print(f"Email: {args.email}")
    print()

    if args.check_only:
        exists = check_user_exists(args.server_url, args.username)
        sys.exit(0 if exists else 1)

    success = False

    if args.database_direct:
        # Try database registration first
        success = register_user_via_database(args.username, args.email, args.password)
    else:
        # Try web registration first
        success = register_user_via_web(
            args.server_url, args.username, args.email, args.password
        )

        if not success:
            print("\n🔄 Web registration failed, trying database registration...")
            success = register_user_via_database(
                args.username, args.email, args.password
            )

    if success:
        print("\n✅ User setup complete!")
        print(f"   You can now run: python oauth_sequence_tracer.py")
        print(f"   Username: {args.username}")
        print(f"   Password: {args.password}")
    else:
        print("\n❌ User setup failed!")
        print("   Try running the OAuth server and ensure it's configured correctly")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

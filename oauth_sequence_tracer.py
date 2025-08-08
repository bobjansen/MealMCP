#!/usr/bin/env python3
"""
OAuth 2.1 Sequence Tracer and Replay Script

This script simulates the complete OAuth 2.1 PKCE flow that Claude Desktop would use
to authenticate with the MCP server. It traces all HTTP requests and responses,
providing detailed logging for debugging and documentation purposes.

Usage:
    python oauth_sequence_tracer.py [--server-url URL] [--username USER] [--password PASS]

Environment Variables:
    OAUTH_SERVER_URL: Base URL of the OAuth server (default: http://localhost:8000)
    OAUTH_TEST_USERNAME: Username for authentication (default: testuser)
    OAUTH_TEST_PASSWORD: Password for authentication (default: testpass)
    OAUTH_CLIENT_NAME: Name of the OAuth client (default: Claude Desktop)
"""

import os
import sys
import json
import base64
import hashlib
import secrets
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import argparse
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages not installed. Install with:")
    print("pip install requests beautifulsoup4")
    sys.exit(1)


class OAuthSequenceTracer:
    """Traces and replays the complete OAuth 2.1 PKCE flow."""

    def __init__(
        self, server_url: str = None, username: str = None, password: str = None
    ):
        self.server_url = server_url or os.getenv(
            "OAUTH_SERVER_URL", "http://localhost:8000"
        )
        self.username = username or os.getenv("OAUTH_TEST_USERNAME", "testuser")
        self.password = password or os.getenv("OAUTH_TEST_PASSWORD", "testpass")
        self.client_name = os.getenv("OAUTH_CLIENT_NAME", "Claude Desktop")

        # OAuth state
        self.client_id = None
        self.client_secret = None
        self.code_verifier = None
        self.code_challenge = None
        self.auth_code = None
        self.access_token = None
        self.refresh_token = None

        # HTTP session for cookie persistence
        self.session = requests.Session()

        # Tracing
        self.trace_log = []

        print(f"🔍 OAuth Sequence Tracer initialized")
        print(f"   Server URL: {self.server_url}")
        print(f"   Username: {self.username}")
        print(f"   Client Name: {self.client_name}")
        print()

    def log_request(self, method: str, url: str, **kwargs):
        """Log HTTP request details."""
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "type": "request",
            "method": method,
            "url": url,
            "headers": dict(kwargs.get("headers", {})),
            "params": kwargs.get("params"),
            "data": kwargs.get("data"),
            "json": kwargs.get("json"),
        }

        self.trace_log.append(log_entry)

        print(f"➡️  {method} {url}")
        if kwargs.get("headers"):
            print(f"    Headers: {dict(kwargs['headers'])}")
        if kwargs.get("params"):
            print(f"    Params: {kwargs['params']}")
        if kwargs.get("data"):
            print(f"    Form Data: {kwargs['data']}")
        if kwargs.get("json"):
            print(f"    JSON: {json.dumps(kwargs['json'], indent=2)}")

    def log_response(self, response: requests.Response):
        """Log HTTP response details."""
        timestamp = datetime.now().isoformat()

        # Try to parse JSON content
        try:
            json_content = response.json()
        except:
            json_content = None

        log_entry = {
            "timestamp": timestamp,
            "type": "response",
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "json": json_content,
            "text": (
                response.text[:500] + "..."
                if len(response.text) > 500
                else response.text
            ),
        }

        self.trace_log.append(log_entry)

        status_emoji = "✅" if response.status_code < 400 else "❌"
        print(f"{status_emoji} {response.status_code} {response.reason}")
        print(f"    Headers: {dict(response.headers)}")

        if json_content:
            print(f"    JSON Response: {json.dumps(json_content, indent=2)}")
        elif response.text:
            preview = (
                response.text[:200] + "..."
                if len(response.text) > 200
                else response.text
            )
            print(f"    Text Preview: {preview}")
        print()

    def generate_pkce_params(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate code challenge
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )

        self.code_verifier = code_verifier
        self.code_challenge = code_challenge

        print(f"🔐 Generated PKCE parameters:")
        print(f"    Code Verifier: {code_verifier}")
        print(f"    Code Challenge: {code_challenge}")
        print()

        return code_verifier, code_challenge

    def discover_oauth_endpoints(self) -> Dict[str, Any]:
        """Step 1: Discover OAuth 2.1 authorization server metadata."""
        print("🔍 STEP 1: Discovering OAuth endpoints...")

        url = f"{self.server_url}/.well-known/oauth-authorization-server"
        self.log_request("GET", url)

        response = self.session.get(url)
        self.log_response(response)

        if response.status_code != 200:
            raise Exception(f"OAuth discovery failed: {response.status_code}")

        return response.json()

    def register_client(self) -> Dict[str, Any]:
        """Step 2: Register OAuth client."""
        print("🔍 STEP 2: Registering OAuth client...")

        client_data = {
            "client_name": self.client_name,
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Public client
            "scope": "read write",
        }

        url = f"{self.server_url}/register"
        self.log_request("POST", url, json=client_data)

        response = self.session.post(url, json=client_data)
        self.log_response(response)

        if response.status_code != 201:
            raise Exception(f"Client registration failed: {response.status_code}")

        client_info = response.json()
        self.client_id = client_info["client_id"]
        self.client_secret = client_info.get("client_secret")

        return client_info

    def start_authorization_flow(self) -> str:
        """Step 3: Start authorization flow and get login form."""
        print("🔍 STEP 3: Starting authorization flow...")

        self.generate_pkce_params()

        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": "http://localhost:3000/callback",
            "scope": "read write",
            "state": secrets.token_urlsafe(32),
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
        }

        url = f"{self.server_url}/authorize"
        self.log_request("GET", url, params=auth_params)

        response = self.session.get(url, params=auth_params)
        self.log_response(response)

        if response.status_code != 200:
            raise Exception(f"Authorization request failed: {response.status_code}")

        return response.text

    def submit_login_form(self, login_form_html: str) -> str:
        """Step 4: Submit login form and get authorization code."""
        print("🔍 STEP 4: Submitting login form...")

        # Parse the form to extract hidden fields
        soup = BeautifulSoup(login_form_html, "html.parser")
        form = soup.find("form", {"method": "post"})

        if not form:
            raise Exception("Login form not found in response")

        form_data = {"username": self.username, "password": self.password}

        # Extract hidden form fields
        hidden_inputs = form.find_all("input", {"type": "hidden"})
        for hidden_input in hidden_inputs:
            name = hidden_input.get("name")
            value = hidden_input.get("value", "")
            if name:
                form_data[name] = value

        # Extract other form fields
        for input_field in form.find_all("input"):
            name = input_field.get("name")
            if name and name not in form_data and name not in ["username", "password"]:
                form_data[name] = input_field.get("value", "")

        url = f"{self.server_url}/authorize"
        self.log_request("POST", url, data=form_data)

        response = self.session.post(url, data=form_data, allow_redirects=False)
        self.log_response(response)

        # Should be a redirect to the callback URL with authorization code
        if response.status_code not in [302, 301]:
            raise Exception(
                f"Expected redirect after login, got {response.status_code}"
            )

        location = response.headers.get("Location", "")
        if not location:
            raise Exception("No redirect location in response")

        # Parse authorization code from redirect URL
        parsed_url = urllib.parse.urlparse(location)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if "code" not in query_params:
            error = query_params.get("error", ["unknown"])[0]
            error_desc = query_params.get("error_description", [""])[0]
            raise Exception(f"Authorization failed: {error} - {error_desc}")

        self.auth_code = query_params["code"][0]
        print(f"🎫 Authorization code received: {self.auth_code}")
        print()

        return self.auth_code

    def exchange_code_for_tokens(self) -> Dict[str, Any]:
        """Step 5: Exchange authorization code for access token."""
        print("🔍 STEP 5: Exchanging authorization code for tokens...")

        token_data = {
            "grant_type": "authorization_code",
            "code": self.auth_code,
            "client_id": self.client_id,
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": self.code_verifier,
        }

        if self.client_secret:
            token_data["client_secret"] = self.client_secret

        url = f"{self.server_url}/token"
        self.log_request("POST", url, data=token_data)

        response = self.session.post(url, data=token_data)
        self.log_response(response)

        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code}")

        token_info = response.json()
        self.access_token = token_info["access_token"]
        self.refresh_token = token_info.get("refresh_token")

        print(f"🎟️  Access token received: {self.access_token[:20]}...")
        if self.refresh_token:
            print(f"🔄 Refresh token received: {self.refresh_token[:20]}...")
        print()

        return token_info

    def test_authenticated_request(self) -> Dict[str, Any]:
        """Step 6: Test MCP request with access token."""
        print("🔍 STEP 6: Testing authenticated MCP request...")

        # Test with a tools/list request
        mcp_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.server_url}/"
        self.log_request("POST", url, json=mcp_request, headers=headers)

        response = self.session.post(url, json=mcp_request, headers=headers)
        self.log_response(response)

        if response.status_code != 200:
            raise Exception(f"Authenticated MCP request failed: {response.status_code}")

        return response.json()

    def test_refresh_token(self) -> Dict[str, Any]:
        """Step 7: Test refresh token (if available)."""
        if not self.refresh_token:
            print("🔍 STEP 7: Skipping refresh token test (no refresh token)")
            return {}

        print("🔍 STEP 7: Testing refresh token...")

        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
        }

        if self.client_secret:
            refresh_data["client_secret"] = self.client_secret

        url = f"{self.server_url}/token"
        self.log_request("POST", url, data=refresh_data)

        response = self.session.post(url, data=refresh_data)
        self.log_response(response)

        if response.status_code != 200:
            print(f"⚠️  Refresh token failed: {response.status_code}")
            return {}

        token_info = response.json()
        print(f"🔄 New access token: {token_info['access_token'][:20]}...")
        print()

        return token_info

    def run_complete_sequence(self) -> bool:
        """Run the complete OAuth 2.1 sequence."""
        try:
            print("🚀 Starting OAuth 2.1 PKCE sequence trace...")
            print("=" * 60)

            # Step 1: Discovery
            discovery_info = self.discover_oauth_endpoints()

            # Step 2: Client registration
            client_info = self.register_client()

            # Step 3: Authorization flow
            login_form = self.start_authorization_flow()

            # Step 4: Login and get code
            auth_code = self.submit_login_form(login_form)

            # Step 5: Token exchange
            token_info = self.exchange_code_for_tokens()

            # Step 6: Test authenticated request
            mcp_response = self.test_authenticated_request()

            # Step 7: Test refresh token
            refresh_response = self.test_refresh_token()

            print("=" * 60)
            print("✅ OAuth 2.1 sequence completed successfully!")

            return True

        except Exception as e:
            print("=" * 60)
            print(f"❌ OAuth sequence failed: {e}")
            return False

    def save_trace_log(self, filename: str = None):
        """Save the complete trace log to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"oauth_trace_{timestamp}.json"

        trace_data = {
            "metadata": {
                "server_url": self.server_url,
                "username": self.username,
                "client_name": self.client_name,
                "timestamp": datetime.now().isoformat(),
                "total_requests": len(
                    [entry for entry in self.trace_log if entry["type"] == "request"]
                ),
            },
            "sequence_summary": {
                "client_id": self.client_id,
                "auth_code_received": bool(self.auth_code),
                "access_token_received": bool(self.access_token),
                "refresh_token_received": bool(self.refresh_token),
            },
            "trace_log": self.trace_log,
        }

        with open(filename, "w") as f:
            json.dump(trace_data, f, indent=2)

        print(f"📄 Trace log saved to: {filename}")

    def print_summary(self):
        """Print a summary of the OAuth sequence."""
        print("\n" + "=" * 60)
        print("📊 OAUTH SEQUENCE SUMMARY")
        print("=" * 60)

        total_requests = len(
            [entry for entry in self.trace_log if entry["type"] == "request"]
        )
        successful_responses = len(
            [
                entry
                for entry in self.trace_log
                if entry["type"] == "response" and entry["status_code"] < 400
            ]
        )

        print(f"Total HTTP requests: {total_requests}")
        print(f"Successful responses: {successful_responses}")
        print(f"Client ID: {self.client_id}")
        print(f"Authorization code: {'✅ Received' if self.auth_code else '❌ Failed'}")
        print(f"Access token: {'✅ Received' if self.access_token else '❌ Failed'}")
        print(
            f"Refresh token: {'✅ Received' if self.refresh_token else '❌ Not provided'}"
        )

        print("\nKey OAuth Endpoints Tested:")
        print("  • /.well-known/oauth-authorization-server (Discovery)")
        print("  • /register (Client Registration)")
        print("  • /authorize (Authorization)")
        print("  • /token (Token Exchange)")
        print("  • / (Authenticated MCP Request)")


def main():
    parser = argparse.ArgumentParser(description="Trace OAuth 2.1 PKCE sequence")
    parser.add_argument("--server-url", help="OAuth server base URL")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    parser.add_argument("--save-trace", help="Save trace log to file")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    if args.quiet:
        # Reduce print output in quiet mode
        pass

    tracer = OAuthSequenceTracer(
        server_url=args.server_url, username=args.username, password=args.password
    )

    success = tracer.run_complete_sequence()

    if not args.quiet:
        tracer.print_summary()

    if args.save_trace:
        tracer.save_trace_log(args.save_trace)
    else:
        tracer.save_trace_log()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

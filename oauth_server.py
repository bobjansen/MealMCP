"""
OAuth 2.1 Authorization Server for MCP
Implements OAuth 2.1 with PKCE for secure authentication
"""

import os
import secrets
import hashlib
import base64
import json
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, parse_qs
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path


class OAuthServer:
    """OAuth 2.1 Authorization Server with PKCE support."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.db_path = Path("oauth.db")
        self.init_database()

        # OAuth endpoints
        self.authorization_endpoint = f"{self.base_url}/authorize"
        self.token_endpoint = f"{self.base_url}/token"
        self.registration_endpoint = f"{self.base_url}/register"

        # Cache for authorization codes and tokens
        self.auth_codes: Dict[str, Dict] = {}
        self.access_tokens: Dict[str, Dict] = {}
        self.refresh_tokens: Dict[str, Dict] = {}

    def init_database(self):
        """Initialize OAuth database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    client_secret TEXT,
                    redirect_uris TEXT,
                    client_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_consents (
                    user_id TEXT,
                    client_id TEXT,
                    scopes TEXT,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, client_id)
                )
            """
            )

    def get_discovery_metadata(self) -> Dict:
        """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
        return {
            "issuer": self.base_url,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "registration_endpoint": self.registration_endpoint,
            "scopes_supported": ["read", "write", "admin"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": ["sub", "iss", "aud", "exp", "iat"],
        }

    def get_protected_resource_metadata(self) -> Dict:
        """OAuth 2.0 Protected Resource Metadata."""
        return {
            "resource": self.base_url,
            "authorization_servers": [self.base_url],
            "scopes_supported": ["read", "write", "admin"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": f"{self.base_url}/docs",
        }

    def register_client(self, client_metadata: Dict) -> Dict:
        """Dynamic Client Registration (RFC 7591)."""
        client_id = secrets.token_urlsafe(16)
        client_secret = secrets.token_urlsafe(32)

        client_name = client_metadata.get("client_name", "Unnamed Client")
        redirect_uris = json.dumps(client_metadata.get("redirect_uris", []))

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name)
                VALUES (?, ?, ?, ?)
            """,
                (client_id, client_secret, redirect_uris, client_name),
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": json.loads(redirect_uris),
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_basic",
        }

    def create_user(self, username: str, password: str, email: str = None) -> str:
        """Create a new user account."""
        user_id = secrets.token_urlsafe(16)
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash, email)
                    VALUES (?, ?, ?, ?)
                """,
                    (user_id, username, password_hash, email),
                )
                return user_id
            except sqlite3.IntegrityError:
                raise ValueError("Username already exists")

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user credentials."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT user_id FROM users 
                WHERE username = ? AND password_hash = ?
            """,
                (username, password_hash),
            )

            result = cursor.fetchone()
            return result[0] if result else None

    def validate_client(self, client_id: str, client_secret: str = None) -> bool:
        """Validate client credentials."""
        with sqlite3.connect(self.db_path) as conn:
            if client_secret:
                cursor = conn.execute(
                    """
                    SELECT 1 FROM oauth_clients 
                    WHERE client_id = ? AND client_secret = ?
                """,
                    (client_id, client_secret),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT 1 FROM oauth_clients WHERE client_id = ?
                """,
                    (client_id,),
                )

            return cursor.fetchone() is not None

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI for client."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT redirect_uris FROM oauth_clients WHERE client_id = ?
            """,
                (client_id,),
            )

            result = cursor.fetchone()
            if not result:
                return False

            allowed_uris = json.loads(result[0])
            return redirect_uri in allowed_uris

    def verify_pkce_challenge(
        self, code_verifier: str, code_challenge: str, method: str = "S256"
    ) -> bool:
        """Verify PKCE code challenge."""
        if method == "S256":
            digest = hashlib.sha256(code_verifier.encode()).digest()
            challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
            return challenge == code_challenge
        elif method == "plain":
            return code_verifier == code_challenge
        return False

    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> str:
        """Create authorization code."""
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + 600  # 10 minutes

        self.auth_codes[code] = {
            "client_id": client_id,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "expires_at": expires_at,
        }

        return code

    def exchange_code_for_tokens(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
        client_secret: str = None,
    ) -> Dict:
        """Exchange authorization code for access token."""
        if code not in self.auth_codes:
            raise ValueError("Invalid authorization code")

        auth_data = self.auth_codes[code]

        # Validate authorization code
        if time.time() > auth_data["expires_at"]:
            del self.auth_codes[code]
            raise ValueError("Authorization code expired")

        if auth_data["client_id"] != client_id:
            raise ValueError("Client ID mismatch")

        if auth_data["redirect_uri"] != redirect_uri:
            raise ValueError("Redirect URI mismatch")

        # Verify PKCE
        if not self.verify_pkce_challenge(
            code_verifier,
            auth_data["code_challenge"],
            auth_data["code_challenge_method"],
        ):
            raise ValueError("PKCE verification failed")

        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_in = 3600  # 1 hour

        # Store tokens
        self.access_tokens[access_token] = {
            "user_id": auth_data["user_id"],
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": time.time() + expires_in,
        }

        self.refresh_tokens[refresh_token] = {
            "user_id": auth_data["user_id"],
            "client_id": client_id,
            "scope": auth_data["scope"],
            "access_token": access_token,
        }

        # Clean up authorization code
        del self.auth_codes[code]

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": refresh_token,
            "scope": auth_data["scope"],
        }

    def validate_access_token(self, access_token: str) -> Optional[Dict]:
        """Validate access token and return token info."""
        if access_token not in self.access_tokens:
            return None

        token_data = self.access_tokens[access_token]

        if time.time() > token_data["expires_at"]:
            del self.access_tokens[access_token]
            return None

        return token_data

    def refresh_access_token(self, refresh_token: str, client_id: str) -> Dict:
        """Refresh access token using refresh token."""
        if refresh_token not in self.refresh_tokens:
            raise ValueError("Invalid refresh token")

        refresh_data = self.refresh_tokens[refresh_token]

        if refresh_data["client_id"] != client_id:
            raise ValueError("Client ID mismatch")

        # Revoke old access token
        old_access_token = refresh_data["access_token"]
        if old_access_token in self.access_tokens:
            del self.access_tokens[old_access_token]

        # Generate new tokens
        new_access_token = secrets.token_urlsafe(32)
        new_refresh_token = secrets.token_urlsafe(32)
        expires_in = 3600  # 1 hour

        # Store new tokens
        self.access_tokens[new_access_token] = {
            "user_id": refresh_data["user_id"],
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": time.time() + expires_in,
        }

        self.refresh_tokens[new_refresh_token] = {
            "user_id": refresh_data["user_id"],
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "access_token": new_access_token,
        }

        # Clean up old refresh token
        del self.refresh_tokens[refresh_token]

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": new_refresh_token,
            "scope": refresh_data["scope"],
        }

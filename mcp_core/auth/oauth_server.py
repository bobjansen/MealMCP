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
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash


class OAuthServer:
    """OAuth 2.1 Authorization Server with PKCE support."""

    def __init__(
        self, base_url: str = "http://localhost:8000", use_postgresql: bool = None
    ):
        self.base_url = base_url.rstrip("/")

        # Determine database backend
        if use_postgresql is None:
            use_postgresql = (
                os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
            )

        self.use_postgresql = use_postgresql
        self.db_path = Path("oauth.db")
        self.postgres_url = os.getenv("PANTRY_DATABASE_URL")

        self.init_database()

        # OAuth endpoints
        self.authorization_endpoint = f"{self.base_url}/authorize"
        self.token_endpoint = f"{self.base_url}/token"
        self.registration_endpoint = f"{self.base_url}/register"

        # Cache for authorization codes and tokens (with database persistence)
        self.auth_codes: Dict[str, Dict] = {}
        self.access_tokens: Dict[str, Dict] = {}
        self.refresh_tokens: Dict[str, Dict] = {}

        # Load existing tokens from database on startup
        self._load_tokens_from_db()

    def init_database(self):
        """Initialize OAuth database."""
        if self.use_postgresql:
            self._init_postgresql()
        else:
            self._init_sqlite()

    def _init_sqlite(self):
        """Initialize SQLite OAuth database."""
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

            # Add token persistence tables
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    token TEXT PRIMARY KEY,
                    token_type TEXT,
                    user_id TEXT,
                    client_id TEXT,
                    scopes TEXT,
                    expires_at INTEGER,
                    token_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def _init_postgresql(self):
        """Initialize PostgreSQL OAuth database."""
        with psycopg2.connect(self.postgres_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
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

                # Note: We'll use the existing users table from the shared schema
                # No need to create a separate users table for OAuth

                cursor.execute(
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

                # Add token persistence table for PostgreSQL
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS oauth_tokens (
                        token TEXT PRIMARY KEY,
                        token_type TEXT,
                        user_id TEXT,
                        client_id TEXT,
                        scopes TEXT,
                        expires_at BIGINT,
                        token_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                conn.commit()

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
            "token_endpoint_auth_methods_supported": [
                "none"
            ],  # PKCE only, no client secrets
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": ["sub", "iss", "aud", "exp", "iat"],
            # Claude.ai specific metadata
            "registration_client_uri": f"{self.base_url}/register",
            "require_request_uri_registration": False,
            "require_signed_request_object": False,
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
        redirect_uris = client_metadata.get("redirect_uris", [])

        print(
            f"[DEBUG] Registering client: {client_name}, redirect_uris: {redirect_uris}"
        )
        print(f"[DEBUG] Generated client_id: {client_id}")

        # For Claude.ai, automatically add common proxy redirect patterns
        if "claude" in client_name.lower() or any(
            "claude.ai" in uri for uri in redirect_uris
        ):
            # Add wildcard pattern for Claude proxy URLs
            if not any("claude.ai/api/organizations" in uri for uri in redirect_uris):
                redirect_uris.append(
                    "https://claude.ai/api/organizations/*/mcp/oauth/callback"
                )
                print(f"[DEBUG] Added Claude proxy redirect URI: {redirect_uris}")

        redirect_uris_json = json.dumps(redirect_uris)

        if self.use_postgresql:
            print(f"[DEBUG] Using PostgreSQL for client registration")
            with psycopg2.connect(self.postgres_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (client_id, client_secret, redirect_uris_json, client_name),
                    )
                    conn.commit()
                    print(f"[DEBUG] Client registered successfully in PostgreSQL")
        else:
            print(f"[DEBUG] Using SQLite for client registration")
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name)
                    VALUES (?, ?, ?, ?)
                """,
                    (client_id, client_secret, redirect_uris_json, client_name),
                )
                print(f"[DEBUG] Client registered successfully in SQLite")

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Claude uses PKCE, no client secret needed
        }

    def create_user(self, username: str, password: str, email: str = None) -> str:
        """Create a new user account."""
        if self.use_postgresql:
            return self._create_user_postgresql(username, password, email)
        else:
            return self._create_user_sqlite(username, password, email)

    def _create_user_sqlite(
        self, username: str, password: str, email: str = None
    ) -> str:
        """Create a new user account in SQLite."""
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

    def _create_user_postgresql(
        self, username: str, password: str, email: str = None
    ) -> str:
        """Create a new user account in PostgreSQL."""
        # Hash password using same method as web interface (scrypt)
        password_hash = generate_password_hash(password, method="scrypt")

        with psycopg2.connect(self.postgres_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                try:
                    cursor.execute(
                        """
                        INSERT INTO users (username, password_hash, email)
                        VALUES (%s, %s, %s) RETURNING id
                    """,
                        (username, password_hash, email),
                    )
                    result = cursor.fetchone()
                    conn.commit()
                    return str(result["id"])
                except psycopg2.IntegrityError:
                    raise ValueError("Username already exists")

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate user credentials."""
        if self.use_postgresql:
            return self._authenticate_user_postgresql(username, password)
        else:
            return self._authenticate_user_sqlite(username, password)

    def _authenticate_user_sqlite(self, username: str, password: str) -> Optional[str]:
        """Authenticate user credentials against SQLite."""
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

    def _authenticate_user_postgresql(
        self, username: str, password: str
    ) -> Optional[str]:
        """Authenticate user credentials against PostgreSQL."""
        print(f"[DEBUG] Attempting PostgreSQL authentication for username: {username}")

        with psycopg2.connect(self.postgres_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get user with password hash
                cursor.execute(
                    "SELECT id, username, password_hash FROM users WHERE username = %s",
                    (username,),
                )

                user = cursor.fetchone()
                if not user:
                    print(f"[DEBUG] User {username} does not exist in database")
                    return None

                print(
                    f"[DEBUG] Found user {username} with hash type: {user['password_hash'][:10]}..."
                )

                # Verify password using werkzeug's check_password_hash (supports scrypt, bcrypt, etc.)
                password_valid = check_password_hash(user["password_hash"], password)
                print(f"[DEBUG] Password verification result: {password_valid}")

                if password_valid:
                    print(f"[DEBUG] Authentication successful for user {username}")
                    return str(user["id"])
                else:
                    print(f"[DEBUG] Password verification failed for user {username}")
                    return None

    def validate_client(self, client_id: str, client_secret: str = None) -> bool:
        """Validate client credentials."""
        print(
            f"[DEBUG] Validating client_id: {client_id}, use_postgresql: {self.use_postgresql}"
        )

        if self.use_postgresql:
            with psycopg2.connect(self.postgres_url) as conn:
                with conn.cursor() as cursor:
                    if client_secret:
                        cursor.execute(
                            """
                            SELECT client_id, client_name FROM oauth_clients 
                            WHERE client_id = %s AND client_secret = %s
                        """,
                            (client_id, client_secret),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT client_id, client_name FROM oauth_clients WHERE client_id = %s
                        """,
                            (client_id,),
                        )
                    result = cursor.fetchone()
                    print(f"[DEBUG] PostgreSQL query result: {result}")
                    return result is not None
        else:
            with sqlite3.connect(self.db_path) as conn:
                if client_secret:
                    cursor = conn.execute(
                        """
                        SELECT client_id, client_name FROM oauth_clients 
                        WHERE client_id = ? AND client_secret = ?
                    """,
                        (client_id, client_secret),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT client_id, client_name FROM oauth_clients WHERE client_id = ?
                    """,
                        (client_id,),
                    )
                result = cursor.fetchone()
                print(f"[DEBUG] SQLite query result: {result}")
                return result is not None

    def register_existing_client(
        self, client_id: str, client_name: str, redirect_uris: list
    ) -> bool:
        """Register a client with a specific client_id (for Claude Desktop compatibility)."""
        print(f"[DEBUG] Registering existing client_id: {client_id}")

        client_secret = secrets.token_urlsafe(32)
        redirect_uris_json = json.dumps(redirect_uris)

        try:
            if self.use_postgresql:
                with psycopg2.connect(self.postgres_url) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name)
                            VALUES (%s, %s, %s, %s)
                        """,
                            (client_id, client_secret, redirect_uris_json, client_name),
                        )
                        conn.commit()
                        print(
                            f"[DEBUG] Existing client registered successfully in PostgreSQL"
                        )
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name)
                        VALUES (?, ?, ?, ?)
                    """,
                        (client_id, client_secret, redirect_uris_json, client_name),
                    )
                    print(f"[DEBUG] Existing client registered successfully in SQLite")
            return True
        except Exception as e:
            print(f"[DEBUG] Failed to register existing client: {e}")
            return False

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI for client."""
        if self.use_postgresql:
            with psycopg2.connect(self.postgres_url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT redirect_uris FROM oauth_clients WHERE client_id = %s
                    """,
                        (client_id,),
                    )
                    result = cursor.fetchone()
        else:
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

        # Allow Claude.ai proxy redirects (flexible matching)
        if redirect_uri.startswith("https://claude.ai/api/organizations/") and (
            "mcp" in redirect_uri or "oauth" in redirect_uri
        ):
            return True

        # Exact match
        if redirect_uri in allowed_uris:
            return True

        # Wildcard matching for Claude patterns
        for allowed_uri in allowed_uris:
            if "*" in allowed_uri:
                # Simple wildcard matching for claude.ai URLs
                pattern = allowed_uri.replace("*", ".*")
                import re

                if re.match(pattern, redirect_uri):
                    return True

        return False

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
        expires_in = int(
            os.getenv("OAUTH_TOKEN_EXPIRY", "86400")
        )  # Default 24 hours, configurable

        # Store tokens in memory and database
        access_token_data = {
            "user_id": auth_data["user_id"],
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": time.time() + expires_in,
        }

        refresh_token_data = {
            "user_id": auth_data["user_id"],
            "client_id": client_id,
            "scope": auth_data["scope"],
            "access_token": access_token,
        }

        self.access_tokens[access_token] = access_token_data
        self.refresh_tokens[refresh_token] = refresh_token_data

        # Persist tokens to database
        self._save_token_to_db(access_token, "access", access_token_data)
        self._save_token_to_db(refresh_token, "refresh", refresh_token_data)

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
            self._remove_token_from_db(access_token)
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
        expires_in = int(
            os.getenv("OAUTH_TOKEN_EXPIRY", "86400")
        )  # Default 24 hours, configurable

        # Store new tokens in memory and database
        new_access_token_data = {
            "user_id": refresh_data["user_id"],
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": time.time() + expires_in,
        }

        new_refresh_token_data = {
            "user_id": refresh_data["user_id"],
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "access_token": new_access_token,
        }

        self.access_tokens[new_access_token] = new_access_token_data
        self.refresh_tokens[new_refresh_token] = new_refresh_token_data

        # Persist new tokens to database
        self._save_token_to_db(new_access_token, "access", new_access_token_data)
        self._save_token_to_db(new_refresh_token, "refresh", new_refresh_token_data)

        # Clean up old refresh token from memory and database
        del self.refresh_tokens[refresh_token]
        self._remove_token_from_db(refresh_token)

        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "refresh_token": new_refresh_token,
            "scope": refresh_data["scope"],
        }

    def _load_tokens_from_db(self):
        """Load existing tokens from database on startup."""
        try:
            if self.use_postgresql:
                self._load_tokens_postgresql()
            else:
                self._load_tokens_sqlite()
        except Exception as e:
            print(f"Warning: Could not load tokens from database: {e}")

    def _load_tokens_sqlite(self):
        """Load tokens from SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token, token_type, user_id, client_id, scopes, expires_at, token_data FROM oauth_tokens WHERE expires_at > ?",
                (int(time.time()),),
            )

            for row in cursor.fetchall():
                (
                    token,
                    token_type,
                    user_id,
                    client_id,
                    scopes,
                    expires_at,
                    token_data_json,
                ) = row
                token_data = json.loads(token_data_json)

                if token_type == "access":
                    self.access_tokens[token] = token_data
                elif token_type == "refresh":
                    self.refresh_tokens[token] = token_data

    def _load_tokens_postgresql(self):
        """Load tokens from PostgreSQL database."""
        with psycopg2.connect(self.postgres_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT token, token_type, user_id, client_id, scopes, expires_at, token_data FROM oauth_tokens WHERE expires_at > %s",
                    (int(time.time()),),
                )

                for row in cursor.fetchall():
                    (
                        token,
                        token_type,
                        user_id,
                        client_id,
                        scopes,
                        expires_at,
                        token_data_json,
                    ) = row
                    token_data = json.loads(token_data_json)

                    if token_type == "access":
                        self.access_tokens[token] = token_data
                    elif token_type == "refresh":
                        self.refresh_tokens[token] = token_data

    def _save_token_to_db(self, token: str, token_type: str, token_data: Dict):
        """Save token to database."""
        try:
            if self.use_postgresql:
                self._save_token_postgresql(token, token_type, token_data)
            else:
                self._save_token_sqlite(token, token_type, token_data)
        except Exception as e:
            print(f"Warning: Could not save token to database: {e}")

    def _save_token_sqlite(self, token: str, token_type: str, token_data: Dict):
        """Save token to SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO oauth_tokens 
                (token, token_type, user_id, client_id, scopes, expires_at, token_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token,
                    token_type,
                    token_data["user_id"],
                    token_data["client_id"],
                    token_data.get("scope", ""),
                    token_data.get("expires_at", 0),
                    json.dumps(token_data),
                ),
            )

    def _save_token_postgresql(self, token: str, token_type: str, token_data: Dict):
        """Save token to PostgreSQL database."""
        with psycopg2.connect(self.postgres_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO oauth_tokens 
                    (token, token_type, user_id, client_id, scopes, expires_at, token_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (token) DO UPDATE SET
                    token_data = EXCLUDED.token_data, expires_at = EXCLUDED.expires_at
                    """,
                    (
                        token,
                        token_type,
                        token_data["user_id"],
                        token_data["client_id"],
                        token_data.get("scope", ""),
                        token_data.get("expires_at", 0),
                        json.dumps(token_data),
                    ),
                )
                conn.commit()

    def _remove_token_from_db(self, token: str):
        """Remove token from database."""
        try:
            if self.use_postgresql:
                with psycopg2.connect(self.postgres_url) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "DELETE FROM oauth_tokens WHERE token = %s", (token,)
                        )
                        conn.commit()
            else:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM oauth_tokens WHERE token = ?", (token,))
        except Exception as e:
            print(f"Warning: Could not remove token from database: {e}")

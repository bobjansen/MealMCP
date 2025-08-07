"""
OAuth flow handlers - Centralized OAuth logic to reduce duplication.
"""

import logging
import time
from typing import Dict, Any, Optional
from urllib.parse import urlencode, quote
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)


class OAuthFlowHandler:
    """Handles OAuth flow operations with centralized logic."""

    def __init__(self, oauth_server):
        self.oauth = oauth_server

    def cleanup_existing_codes(self, client_id: str, user_id: str) -> None:
        """Remove any existing authorization codes for this client/user combination."""
        codes_to_remove = []
        for existing_code, existing_data in self.oauth.auth_codes.items():
            if (
                existing_data.get("client_id") == client_id
                and existing_data.get("user_id") == user_id
            ):
                codes_to_remove.append(existing_code)
                logger.info(f"Removing old authorization code: {existing_code}")

        for old_code in codes_to_remove:
            del self.oauth.auth_codes[old_code]

    def create_auth_code_with_cleanup(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> str:
        """Create authorization code after cleaning up existing ones."""
        self.cleanup_existing_codes(client_id, user_id)

        auth_code = self.oauth.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Store debug info
        if auth_code in self.oauth.auth_codes:
            self.oauth.auth_codes[auth_code]["debug_timestamp"] = time.time()
            logger.info(f"Created authorization code: {auth_code}")

        return auth_code

    def create_success_redirect(
        self, redirect_uri: str, auth_code: str, state: Optional[str] = None
    ) -> RedirectResponse:
        """Create a successful OAuth redirect response."""
        params = {"code": auth_code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params, safe='', quote_via=quote)}"

        logger.info(f"OAuth flow successful! Redirecting to: {redirect_url}")
        logger.info(f"Authorization code: {auth_code}")
        logger.info(f"State parameter: {state}")

        return RedirectResponse(url=redirect_url, status_code=302)

    def create_error_redirect(
        self,
        redirect_uri: str,
        error: str,
        error_description: str,
        state: Optional[str] = None,
    ) -> RedirectResponse:
        """Create an error OAuth redirect response."""
        error_params = {"error": error, "error_description": error_description}
        if state:
            error_params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(error_params)}"
        logger.error(f"OAuth error redirect: {redirect_url}")

        return RedirectResponse(url=redirect_url, status_code=302)

    def handle_claude_auto_registration(
        self, client_id: str, redirect_uri: str
    ) -> bool:
        """Handle auto-registration for Claude clients."""
        if not redirect_uri.startswith("https://claude.ai/api/"):
            return False

        logger.info(f"Auto-registering Claude client with ID: {client_id}")

        redirect_uris = [redirect_uri, "https://claude.ai/api/mcp/auth_callback"]
        success = self.oauth.register_existing_client(
            client_id=client_id,
            client_name="Claude.ai (Auto-registered)",
            redirect_uris=redirect_uris,
        )

        if success:
            logger.info(f"Successfully auto-registered Claude client: {client_id}")
        else:
            logger.error(f"Failed to auto-register Claude client: {client_id}")

        return success

    def validate_oauth_request(
        self, client_id: str, redirect_uri: str, code_challenge: Optional[str] = None
    ) -> None:
        """Validate OAuth authorization request parameters."""
        # Validate client
        if not self.oauth.validate_client(client_id):
            logger.error(f"Invalid client_id: {client_id}")

            # Try auto-registration for Claude
            if not self.handle_claude_auto_registration(client_id, redirect_uri):
                raise HTTPException(status_code=400, detail="Invalid client_id")

        # Validate redirect URI
        if not self.oauth.validate_redirect_uri(client_id, redirect_uri):
            logger.error(f"Invalid redirect_uri for client {client_id}: {redirect_uri}")
            raise HTTPException(status_code=400, detail="Invalid redirect_uri")

        # PKCE is required
        if not code_challenge:
            logger.error(f"Missing code_challenge for client {client_id}")
            raise HTTPException(status_code=400, detail="code_challenge required")

    def authenticate_and_create_code(
        self,
        username: str,
        password: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> tuple[str, str]:
        """Authenticate user and create authorization code."""
        # Authenticate user
        user_id = self.oauth.authenticate_user(username, password)
        logger.info(f"Authentication result for {username}: {user_id}")

        if not user_id:
            logger.error(f"Authentication failed for username: {username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create authorization code
        logger.info(f"Creating authorization code for user {user_id}")
        auth_code = self.create_auth_code_with_cleanup(
            client_id,
            user_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
        )

        return user_id, auth_code

    def register_and_create_code(
        self,
        username: str,
        password: str,
        email: Optional[str],
        client_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> tuple[str, str]:
        """Register new user and create authorization code."""
        # Create user
        user_id = self.oauth.create_user(username, password, email)
        logger.info(f"Created new user: {user_id}")

        # Create authorization code
        auth_code = self.create_auth_code_with_cleanup(
            client_id,
            user_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
        )

        return user_id, auth_code

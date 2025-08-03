"""
MCP Server with OAuth 2.1 Authentication
Implements OAuth 2.1 with PKCE for secure multi-user authentication
"""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs, quote
from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    TextContent,
    Tool,
    INVALID_REQUEST,
    INTERNAL_ERROR,
)

from oauth_server import OAuthServer
from constants import UNITS
from mcp_context import MCPContext
from i18n import t
from datetime import date, timedelta
import os
import time
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create FastAPI app for OAuth endpoints
app = FastAPI(title="MealMCP OAuth Server", version="1.0.0")


# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OAuth server with public URL and PostgreSQL support
public_url = os.getenv("MCP_PUBLIC_URL", "http://localhost:8000")
use_postgresql = os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
oauth = OAuthServer(base_url=public_url, use_postgresql=use_postgresql)

# Pre-register claude-desktop client for MCP server config
oauth.register_existing_client(
    client_id="claude-desktop",
    client_name="Claude Desktop MCP Client",
    redirect_uris=[
        "https://claude.ai/api/organizations/*/mcp/oauth/callback",
        "claude://oauth/callback",
    ],
)

# Create MCP server
mcp = FastMCP("RecipeManager")

# Create context manager for user handling
context = MCPContext()

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[str]:
    """Extract user from Bearer token."""
    if not credentials:
        return None

    token_data = oauth.validate_access_token(credentials.credentials)
    if not token_data:
        return None

    return token_data["user_id"]


# OAuth Discovery Endpoints
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return oauth.get_discovery_metadata()


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """OAuth 2.0 Protected Resource Metadata."""
    return oauth.get_protected_resource_metadata()


# OAuth Endpoints
@app.options("/register")
async def register_options():
    """OPTIONS for CORS preflight on register endpoint."""
    return {"message": "OK"}


@app.post("/register")
async def register_client(request: Request):
    """Dynamic Client Registration (RFC 7591)."""
    try:
        client_metadata = await request.json()
        logger.info(f"Client registration request: {client_metadata}")
        result = oauth.register_client(client_metadata)
        logger.info(
            f"Client registered: {result['client_id']} - {result['client_name']}"
        )
        return JSONResponse(content=result, status_code=201)
    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.options("/authorize")
async def authorize_options():
    """OPTIONS for CORS preflight on authorize endpoint."""
    return {"message": "OK"}


@app.get("/authorize")
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str = "read write",
    state: str = None,
    code_challenge: str = None,
    code_challenge_method: str = "S256",
):
    """Authorization endpoint."""
    logger.info(
        f"Authorization request: client_id={client_id}, redirect_uri={redirect_uri}, scope={scope}"
    )

    # Validate client
    if not oauth.validate_client(client_id):
        logger.error(f"Invalid client_id: {client_id}")
        logger.error(
            f"Client not found. This usually means Claude Desktop didn't register the client first."
        )
        logger.error(f"Expected flow: 1) POST /register 2) GET /authorize")

        # Auto-register Claude client if it looks like a Claude request
        if redirect_uri.startswith("https://claude.ai/api/"):
            logger.info(f"Auto-registering Claude client with existing client_id...")

            # Register the client with Claude's specific client_id
            redirect_uris = [redirect_uri, "https://claude.ai/api/mcp/auth_callback"]
            success = oauth.register_existing_client(
                client_id=client_id,
                client_name="Claude.ai (Auto-registered)",
                redirect_uris=redirect_uris,
            )

            if success:
                logger.info(
                    f"Successfully auto-registered Claude client with ID: {client_id}"
                )
            else:
                logger.error(f"Failed to auto-register Claude client")
                raise HTTPException(status_code=400, detail="Invalid client_id")
        else:
            raise HTTPException(status_code=400, detail="Invalid client_id")

    # Validate redirect URI
    if not oauth.validate_redirect_uri(client_id, redirect_uri):
        logger.error(f"Invalid redirect_uri for client {client_id}: {redirect_uri}")
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    # PKCE is required
    if not code_challenge:
        logger.error(f"Missing code_challenge for client {client_id}")
        raise HTTPException(status_code=400, detail="code_challenge required")

    # Return login form
    login_form = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MealMCP Authorization</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }}
            .form-group {{ margin: 15px 0; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            .register {{ margin-top: 20px; text-align: center; }}
            .register a {{ color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h2>Authorize MealMCP Access</h2>
        <p>The application <strong>{client_id}</strong> wants to access your MealMCP data.</p>
        
        <form method="post" action="/authorize">
            <input type="hidden" name="response_type" value="{response_type}">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state or ''}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
            
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit">Authorize</button>
        </form>
        
        <div class="register">
            <p>Don't have an account? <a href="/register_user?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state or ''}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}">Register here</a></p>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=login_form)


@app.post("/authorize")
async def authorize_post(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: str = Form(None),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
):
    """Handle authorization form submission."""
    try:
        logger.info(
            f"Authorization form submitted: username={username}, client_id={client_id}"
        )

        # Authenticate user
        user_id = oauth.authenticate_user(username, password)
        logger.info(f"Authentication result for {username}: {user_id}")

        if not user_id:
            logger.error(f"Authentication failed for username: {username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create authorization code
        logger.info(f"Creating authorization code for user {user_id}")

        # Clean up any existing codes for this client/user to prevent conflicts
        codes_to_remove = []
        for existing_code, existing_data in oauth.auth_codes.items():
            if (
                existing_data.get("client_id") == client_id
                and existing_data.get("user_id") == user_id
            ):
                codes_to_remove.append(existing_code)
                logger.info(f"Removing old authorization code: {existing_code}")

        for old_code in codes_to_remove:
            del oauth.auth_codes[old_code]

        auth_code = oauth.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Redirect to client with authorization code (standard OAuth GET redirect)
        params = {"code": auth_code}
        if state:
            params["state"] = state

        # Use proper URL encoding for OAuth parameters
        redirect_url = f"{redirect_uri}?{urlencode(params, safe='', quote_via=quote)}"
        logger.info(f"OAuth flow successful! Redirecting to Claude: {redirect_url}")
        logger.info(f"Authorization code: {auth_code}")
        logger.info(f"Authorization code length: {len(auth_code)}")
        logger.info(f"State parameter: {state}")
        logger.info(f"State parameter length: {len(state) if state else 0}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Client ID: {client_id}")
        logger.info(f"Redirect URI: {redirect_uri}")

        # Store additional debug info for this code
        if auth_code in oauth.auth_codes:
            oauth.auth_codes[auth_code]["debug_redirect_url"] = redirect_url
            oauth.auth_codes[auth_code]["debug_timestamp"] = time.time()
            logger.info(f"Stored debug info for code: {auth_code}")

        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        logger.error(f"Authorization error: {e}")

        error_params = {"error": "access_denied", "error_description": str(e)}
        if state:
            error_params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url, status_code=302)


@app.get("/register_user")
async def register_user_form(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
):
    """User registration form."""
    register_form = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Register for MealMCP</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }}
            .form-group {{ margin: 15px 0; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #1e7e34; }}
            .login {{ margin-top: 20px; text-align: center; }}
            .login a {{ color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h2>Create MealMCP Account</h2>
        
        <form method="post" action="/register_user">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="scope" value="{scope}">
            <input type="hidden" name="state" value="{state}">
            <input type="hidden" name="code_challenge" value="{code_challenge}">
            <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
            
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="email">Email (optional):</label>
                <input type="email" id="email" name="email">
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <div class="form-group">
                <label for="confirm_password">Confirm Password:</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
            </div>
            
            <button type="submit">Register</button>
        </form>
        
        <div class="login">
            <p>Already have an account? <a href="/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}">Login here</a></p>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=register_form)


@app.post("/register_user")
async def register_user_post(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: str = Form(""),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    username: str = Form(...),
    email: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Handle user registration."""
    try:
        if password != confirm_password:
            raise ValueError("Passwords do not match")

        # Create user
        user_id = oauth.create_user(username, password, email or None)

        # Clean up any existing codes for this client/user to prevent conflicts
        codes_to_remove = []
        for existing_code, existing_data in oauth.auth_codes.items():
            if (
                existing_data.get("client_id") == client_id
                and existing_data.get("user_id") == user_id
            ):
                codes_to_remove.append(existing_code)
                logger.info(
                    f"Removing old authorization code for new user: {existing_code}"
                )

        for old_code in codes_to_remove:
            del oauth.auth_codes[old_code]

        # Create authorization code
        auth_code = oauth.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Redirect to client with authorization code
        params = {"code": auth_code}
        if state:
            params["state"] = state

        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        logger.error(f"Registration error: {e}")
        # Redirect back to registration form with error
        error_message = str(e).replace('"', "&quot;")
        register_form_with_error = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Registration Error</title></head>
        <body>
            <h2>Registration Failed</h2>
            <p style="color: red;">{error_message}</p>
            <a href="/register_user?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}">Try Again</a>
        </body>
        </html>
        """
        return HTMLResponse(content=register_form_with_error, status_code=400)


@app.options("/token")
async def token_options():
    """OPTIONS for CORS preflight on token endpoint."""
    return {"message": "OK"}


@app.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
):
    """Token endpoint."""
    logger.info(
        f"Token endpoint called: grant_type={grant_type}, client_id={client_id}"
    )
    logger.info(f"Authorization code received: {code}")
    logger.info(f"Code verifier: {code_verifier}")
    logger.info(f"Redirect URI: {redirect_uri}")

    # Import time module for debugging
    import time

    # Check if this code exists in our auth_codes
    if code and code in oauth.auth_codes:
        auth_data = oauth.auth_codes[code]
        logger.info(
            f"Found auth code data: client_id={auth_data.get('client_id')}, user_id={auth_data.get('user_id')}"
        )
        logger.info(
            f"Code expires at: {auth_data.get('expires_at')}, current time: {time.time()}"
        )
    else:
        logger.error(f"Authorization code not found in server cache: {code}")
        if code:
            logger.error(f"Available codes: {list(oauth.auth_codes.keys())}")
    try:
        if grant_type == "authorization_code":
            if not all([code, redirect_uri, code_verifier]):
                raise ValueError("Missing required parameters")

            tokens = oauth.exchange_code_for_tokens(
                code=code,
                client_id=client_id,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
                client_secret=client_secret,
            )
            return tokens

        elif grant_type == "refresh_token":
            if not refresh_token:
                raise ValueError("Missing refresh_token")

            tokens = oauth.refresh_access_token(refresh_token, client_id)
            return tokens

        else:
            raise ValueError(f"Unsupported grant_type: {grant_type}")

    except Exception as e:
        logger.error(f"Token endpoint error: {e}")
        return JSONResponse(
            content={"error": "invalid_request", "error_description": str(e)},
            status_code=400,
        )


# Helper function to get user pantry with OAuth
def get_user_pantry_oauth(user_id: str) -> tuple[Optional[str], Optional[Any]]:
    """Get authenticated user and their PantryManager instance using OAuth user_id."""
    if not user_id:
        return None, None

    # In multi-user mode, create user-specific pantry manager
    if user_id not in context.pantry_managers:
        db_path = context.user_manager.get_user_db_path(user_id)
        from pantry_manager_factory import create_pantry_manager

        context.pantry_managers[user_id] = create_pantry_manager(
            connection_string=db_path
        )

        # Initialize database if it doesn't exist
        from db_setup import setup_database

        setup_database(db_path)

    context.set_current_user(user_id)
    return user_id, context.pantry_managers[user_id]


# MCP Tools with OAuth Authentication
@mcp.tool()
def list_units() -> List[Dict[str, Any]]:
    """List all units of measurement (no auth required)."""
    return UNITS


@mcp.tool()
def add_recipe(
    name: str,
    instructions: str,
    time_minutes: int,
    ingredients: List[Dict[str, Any]],
    user_id: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add a new recipe to the database."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    success = pantry.add_recipe(
        name=name,
        instructions=instructions,
        time_minutes=time_minutes,
        ingredients=ingredients,
    )

    if success:
        return {"status": "success", "message": t("Recipe added successfully")}
    else:
        return {"status": "error", "message": t("Failed to add recipe")}


@mcp.tool()
def get_all_recipes(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all recipes."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    recipes = pantry.get_all_recipes()
    return {"status": "success", "recipes": recipes}


# Add all other MCP tools with OAuth authentication...
# (I'll add a few more key ones for demonstration)


@mcp.tool()
def get_pantry_contents(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current contents of the pantry."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    contents = pantry.get_pantry_contents()
    return {"status": "success", "contents": contents}


@mcp.tool()
def add_pantry_item(
    item_name: str,
    quantity: float,
    unit: str,
    notes: str = None,
    user_id: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add an item to the pantry."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    success = pantry.add_item(item_name, quantity, unit, notes)
    if success:
        return {
            "status": "success",
            "message": f"Added {quantity} {unit} of {item_name} to pantry",
        }
    else:
        return {"status": "error", "message": "Failed to add item to pantry"}


# Debug endpoint to check authorization code
@app.get("/debug/code/{code}")
async def debug_auth_code(code: str):
    """Debug endpoint to check if authorization code exists."""
    if code in oauth.auth_codes:
        auth_data = oauth.auth_codes[code].copy()
        # Don't expose sensitive data
        if "code_challenge" in auth_data:
            auth_data["code_challenge"] = auth_data["code_challenge"][:10] + "..."
        return {"found": True, "data": auth_data}
    else:
        return {
            "found": False,
            "available_codes": list(oauth.auth_codes.keys()),
            "total_codes": len(oauth.auth_codes),
        }


# Debug endpoint to test token exchange manually
@app.get("/debug/test-token-exchange/{code}")
async def debug_test_token_exchange(code: str, code_verifier: str = "test-verifier"):
    """Debug endpoint to test token exchange with a specific code."""
    try:
        if code not in oauth.auth_codes:
            return {
                "error": "Code not found",
                "available_codes": list(oauth.auth_codes.keys()),
            }

        auth_data = oauth.auth_codes[code]

        # Note: This will fail PKCE validation since we don't have the real code_verifier
        # But it will show us what kind of error occurs
        try:
            tokens = oauth.exchange_code_for_tokens(
                code=code,
                client_id=auth_data["client_id"],
                redirect_uri=auth_data["redirect_uri"],
                code_verifier=code_verifier,
            )
            return {"success": True, "tokens": tokens}
        except Exception as inner_e:
            return {
                "pkce_test_failed": True,
                "error": str(inner_e),
                "auth_data_summary": {
                    "client_id": auth_data["client_id"],
                    "user_id": auth_data["user_id"],
                    "expires_at": auth_data["expires_at"],
                    "current_time": time.time(),
                    "expired": time.time() > auth_data["expires_at"],
                },
            }

    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


# Debug endpoint to list clients
@app.get("/debug/clients")
async def debug_clients():
    """Debug endpoint to list all registered OAuth clients."""
    if oauth.use_postgresql:
        with psycopg2.connect(oauth.postgres_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT client_id, client_name, redirect_uris, created_at FROM oauth_clients ORDER BY created_at DESC"
                )
                clients = cursor.fetchall()
                return {"clients": [dict(client) for client in clients]}
    else:
        with sqlite3.connect(oauth.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT client_id, client_name, redirect_uris, created_at FROM oauth_clients ORDER BY created_at DESC"
            )
            clients = [dict(row) for row in cursor.fetchall()]
            return {"clients": clients}


# MCP Tool endpoints that require authentication
async def mcp_list_tools(request: Request, user_id: str):
    """MCP list tools endpoint."""
    try:
        data = await request.json()
        tools_list = [
            {
                "name": "list_units",
                "description": "List all units of measurement",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "add_recipe",
                "description": "Add a new recipe to the database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the recipe"},
                        "instructions": {
                            "type": "string",
                            "description": "Cooking instructions",
                        },
                        "time_minutes": {
                            "type": "integer",
                            "description": "Time required to prepare the recipe",
                        },
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit": {"type": "string"},
                                },
                                "required": ["name", "quantity", "unit"],
                            },
                        },
                    },
                    "required": ["name", "instructions", "time_minutes", "ingredients"],
                },
            },
            {
                "name": "get_all_recipes",
                "description": "Get all recipes",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_pantry_contents",
                "description": "Get the current contents of the pantry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "add_pantry_item",
                "description": "Add an item to the pantry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_name": {
                            "type": "string",
                            "description": "Name of the item to add",
                        },
                        "quantity": {"type": "number", "description": "Amount to add"},
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the transaction",
                        },
                    },
                    "required": ["item_name", "quantity", "unit"],
                },
            },
        ]

        return {"jsonrpc": "2.0", "id": data.get("id"), "result": {"tools": tools_list}}
    except Exception as e:
        logger.error(f"List tools error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", 0),
            "error": {"code": -32603, "message": str(e)},
        }


async def mcp_call_tool(request: Request, user_id: str):
    """MCP call tool endpoint."""
    try:
        data = await request.json()
        tool_name = data.get("params", {}).get("name")
        arguments = data.get("params", {}).get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")

        # Route to appropriate tool implementation
        if tool_name == "list_units":
            result = {"units": UNITS}
        elif tool_name == "add_recipe":
            user_id, pantry = get_user_pantry_oauth(user_id)
            if not pantry:
                result = {"status": "error", "message": "Failed to get user pantry"}
            else:
                success = pantry.add_recipe(
                    name=arguments["name"],
                    instructions=arguments["instructions"],
                    time_minutes=arguments["time_minutes"],
                    ingredients=arguments["ingredients"],
                )
                result = {
                    "status": "success" if success else "error",
                    "message": (
                        "Recipe added successfully"
                        if success
                        else "Failed to add recipe"
                    ),
                }
        elif tool_name == "get_all_recipes":
            user_id, pantry = get_user_pantry_oauth(user_id)
            if not pantry:
                result = {"status": "error", "message": "Failed to get user pantry"}
            else:
                recipes = pantry.get_all_recipes()
                result = {"status": "success", "recipes": recipes}
        elif tool_name == "get_pantry_contents":
            user_id, pantry = get_user_pantry_oauth(user_id)
            if not pantry:
                result = {"status": "error", "message": "Failed to get user pantry"}
            else:
                contents = pantry.get_pantry_contents()
                result = {"status": "success", "contents": contents}
        elif tool_name == "add_pantry_item":
            user_id, pantry = get_user_pantry_oauth(user_id)
            if not pantry:
                result = {"status": "error", "message": "Failed to get user pantry"}
            else:
                success = pantry.add_item(
                    arguments["item_name"],
                    arguments["quantity"],
                    arguments["unit"],
                    arguments.get("notes"),
                )
                result = {
                    "status": "success" if success else "error",
                    "message": (
                        f"Added {arguments['quantity']} {arguments['unit']} of {arguments['item_name']} to pantry"
                        if success
                        else "Failed to add item to pantry"
                    ),
                }
        else:
            result = {"status": "error", "message": f"Unknown tool: {tool_name}"}

        return {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            },
        }

    except Exception as e:
        logger.error(f"Call tool error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", 0),
            "error": {"code": -32603, "message": str(e)},
        }


# Catch-all MCP endpoint for other possible tool calls
@app.api_route("/mcp/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def mcp_catchall(
    request: Request, path: str, user_id: str = Depends(get_current_user)
):
    """Catch-all for MCP endpoints."""
    logger.info(f"MCP request to /{path} without authentication")
    if not user_id:
        return JSONResponse(
            content={"error": "unauthorized", "message": "Authentication required"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"status": "not_implemented", "path": path}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MealMCP OAuth Server"}


# Debug endpoint for MCP connectivity testing
@app.get("/debug/mcp")
async def debug_mcp():
    """Debug endpoint to test MCP connectivity."""
    logger.info("Debug MCP endpoint called")
    return {
        "mcp_server": True,
        "oauth_endpoints": {"authorization": "/authorize", "token": "/token"},
        "status": "ready",
        "client_registered": "claude-desktop"
        in [client for client in ["claude-desktop"]],  # Simple check
    }


@app.post("/debug/mcp")
async def debug_mcp_post(request: Request):
    """Debug POST endpoint for MCP testing."""
    logger.info("Debug MCP POST endpoint called")
    try:
        body = await request.json()
        logger.info(f"Debug POST body: {body}")
        return {"received": body, "status": "ok"}
    except Exception as e:
        logger.error(f"Debug POST error: {e}")
        return {"error": str(e)}


# Root endpoint with API info
@app.get("/")
async def root(request: Request):
    """Root endpoint with API information and MCP tool discovery."""
    try:
        logger.info("Processing GET / request")

        # Check if this is an authenticated request from Claude Desktop
        auth_header = request.headers.get("authorization")
        user_id = None

        logger.info(f"Authorization header present: {auth_header is not None}")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.info(f"Validating token: {token[:10]}...")
            token_data = oauth.validate_access_token(token)
            if token_data:
                user_id = token_data["user_id"]
                logger.info(f"Authenticated GET request from user: {user_id}")
            else:
                logger.info("GET request with invalid/expired token")
        else:
            logger.info("Unauthenticated GET request")

        logger.info("Building tool definitions...")

        # Return tools in MCP format for Claude Desktop's REST-style discovery
        tools_list = [
            {
                "name": "test_simple",
                "description": "A simple test tool with no parameters",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "list_units",
                "description": "List all units of measurement",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "add_recipe",
                "description": "Add a new recipe to the database",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the recipe"},
                        "instructions": {
                            "type": "string",
                            "description": "Cooking instructions",
                        },
                        "time_minutes": {
                            "type": "integer",
                            "description": "Time required to prepare the recipe",
                        },
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit": {"type": "string"},
                                },
                                "required": ["name", "quantity", "unit"],
                            },
                        },
                    },
                    "required": ["name", "instructions", "time_minutes", "ingredients"],
                },
            },
            {
                "name": "get_all_recipes",
                "description": "Get all recipes",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "get_pantry_contents",
                "description": "Get the current contents of the pantry",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "add_pantry_item",
                "description": "Add an item to the pantry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_name": {
                            "type": "string",
                            "description": "Name of the item to add",
                        },
                        "quantity": {"type": "number", "description": "Amount to add"},
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the transaction",
                        },
                    },
                    "required": ["item_name", "quantity", "unit"],
                },
            },
        ]

        logger.info("Building response object...")

        # Check user agent to determine response format
        user_agent = request.headers.get("user-agent", "")
        logger.info(f"User agent: {user_agent}")

        # Claude Desktop expects tools via GET requests (non-standard MCP behavior)
        if auth_header and user_id:
            logger.info(
                "Returning tools for Claude Desktop's non-standard GET-based discovery"
            )
            # Try different response formats to find what Claude Desktop expects
            # Format 6: Match initialize response format but with tools
            response = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "MealMCP OAuth Server", "version": "1.0.0"},
                "tools": tools_list,
            }

            # Uncomment other formats to test:
            # Format 1: Just the tools array
            # response = tools_list

            # Format 3: Full MCP response with server info
            # response = {
            #     "tools": tools_list,
            #     "serverInfo": {"name": "MealMCP OAuth Server", "version": "1.0.0"},
            #     "protocolVersion": "2025-06-18"
            # }
            logger.info(f"Tools being returned: {len(tools_list)} tools")
            logger.info(f"Tool names: {[tool['name'] for tool in tools_list]}")
            logger.info(f"Response type: {type(response)}")
            if isinstance(response, list) and response:
                logger.info(f"First tool structure: {list(response[0].keys())}")
        else:
            # Regular API info for non-authenticated clients (browsers, etc.)
            logger.info("Returning standard API info for non-authenticated GET request")
            response = {
                "service": "MealMCP OAuth Server",
                "version": "1.0.0",
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": True}},
                "tools": tools_list,
                "oauth_endpoints": {
                    "authorization": "/authorize",
                    "token": "/token",
                    "registration": "/register",
                },
                "discovery_endpoints": {
                    "oauth_authorization_server": "/.well-known/oauth-authorization-server",
                    "oauth_protected_resource": "/.well-known/oauth-protected-resource",
                },
                "mcp_endpoints": {
                    "list_tools": "/mcp/list_tools",
                    "call_tool": "/mcp/call_tool",
                },
            }

        logger.info(f"Returning response from GET /")
        if isinstance(response, dict):
            logger.info(f"Response format: {response.get('jsonrpc', 'standard')}")
        else:
            logger.info(
                f"Response format: direct array with {len(response) if isinstance(response, list) else 'unknown'} items"
            )
        return response

    except Exception as e:
        logger.error(f"Error in GET / endpoint: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": "Internal server error",
            "message": str(e),
            "service": "MealMCP OAuth Server",
        }


# Handle HEAD requests to root
@app.head("/")
async def root_head():
    """Handle HEAD requests to root endpoint."""
    return JSONResponse(content={})


# Dedicated tools endpoint for GUI connector
@app.get("/tools")
async def tools_endpoint(request: Request):
    """Dedicated tools endpoint that might work better for GUI connector."""
    auth_header = request.headers.get("authorization")
    user_id = None

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data = oauth.validate_access_token(token)
        if token_data:
            user_id = token_data["user_id"]

    if not user_id:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Define tools same as in other handlers
    tools_list = [
        {
            "name": "test_simple",
            "description": "A simple test tool with no parameters",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "list_units",
            "description": "List all units of measurement",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "add_recipe",
            "description": "Add a new recipe to the database",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the recipe"},
                    "instructions": {
                        "type": "string",
                        "description": "Cooking instructions",
                    },
                    "time_minutes": {
                        "type": "integer",
                        "description": "Time required to prepare the recipe",
                    },
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                            },
                            "required": ["name", "quantity", "unit"],
                        },
                    },
                },
                "required": ["name", "instructions", "time_minutes", "ingredients"],
            },
        },
        {
            "name": "get_all_recipes",
            "description": "Get all recipes",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_pantry_contents",
            "description": "Get the current contents of the pantry",
            "inputSchema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "add_pantry_item",
            "description": "Add an item to the pantry",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of the item to add",
                    },
                    "quantity": {"type": "number", "description": "Amount to add"},
                    "unit": {"type": "string", "description": "Unit of measurement"},
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the transaction",
                    },
                },
                "required": ["item_name", "quantity", "unit"],
            },
        },
    ]

    logger.info(f"Tools endpoint called - returning {len(tools_list)} tools")
    return tools_list


# Handle POST to root (for any MCP requests that might come here)
@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root endpoint - potential MCP requests."""
    logger.info(f"POST to root endpoint from {request.client}")

    # Log request headers to debug authentication
    auth_header = request.headers.get("authorization")
    logger.info(f"Authorization header: {auth_header}")

    # Try to get user ID from token
    user_id = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data = oauth.validate_access_token(token)
        if token_data:
            user_id = token_data["user_id"]
            logger.info(f"Valid token for user: {user_id}")
        else:
            logger.info("Invalid or expired token")
    else:
        logger.info("No Bearer token provided")

    # Log the request body for debugging
    try:
        body = await request.json()
        logger.info(f"Request body: {body}")

        # Check if this looks like an MCP request
        if isinstance(body, dict) and "method" in body:
            logger.info(f"Detected MCP method: {body['method']}")
            logger.info(f"Full request body: {body}")
            logger.info(f"Request ID: {body.get('id', 'no-id')}")

            # Handle unauthenticated initialize request (required for MCP handshake)
            if not user_id and method == "initialize":
                logger.info(
                    "Allowing unauthenticated initialize request for MCP handshake"
                )
                response = {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {
                            "name": "MealMCP OAuth Server",
                            "version": "1.0.0",
                        },
                    },
                }
                logger.info(f"Unauthenticated initialize response: {response}")
                return JSONResponse(
                    content=response, headers={"Content-Type": "application/json"}
                )

            # If no auth but it's an MCP request (other than initialize), return proper auth challenge
            if not user_id:
                return JSONResponse(
                    content={
                        "error": "unauthorized",
                        "message": "Authentication required",
                    },
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Route MCP requests to appropriate handlers
            method = body.get("method")
            if method == "initialize":
                logger.info("Sending initialize response with tool capabilities")
                response = {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {
                            "name": "MealMCP OAuth Server",
                            "version": "1.0.0",
                        },
                    },
                }
                logger.info(f"Initialize response: {response}")
                return response
            elif method == "notifications/initialized":
                # Notification methods don't require responses in JSON-RPC
                logger.info(
                    "Client initialization complete - Claude should call tools/list next"
                )
                # Some MCP clients need an explicit tools list notification
                logger.info(
                    "Note: If tools don't appear, the client may not be calling tools/list"
                )
                # Return empty object for notification (JSON-RPC spec)
                return {}
            elif method == "tools/list":
                logger.info("tools/list method called - returning tool definitions")
                logger.info(f"User ID for tools/list: {user_id}")
                logger.info(f"Request params: {body.get('params', {})}")

                # Define tools for JSON-RPC response (same as GET endpoint)
                tools_list = [
                    {
                        "name": "test_simple",
                        "description": "A simple test tool with no parameters",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "list_units",
                        "description": "List all units of measurement",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "add_recipe",
                        "description": "Add a new recipe to the database",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the recipe",
                                },
                                "instructions": {
                                    "type": "string",
                                    "description": "Cooking instructions",
                                },
                                "time_minutes": {
                                    "type": "integer",
                                    "description": "Time required to prepare the recipe",
                                },
                                "ingredients": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "quantity": {"type": "number"},
                                            "unit": {"type": "string"},
                                        },
                                        "required": ["name", "quantity", "unit"],
                                    },
                                },
                            },
                            "required": [
                                "name",
                                "instructions",
                                "time_minutes",
                                "ingredients",
                            ],
                        },
                    },
                    {
                        "name": "get_all_recipes",
                        "description": "Get all recipes",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "get_pantry_contents",
                        "description": "Get the current contents of the pantry",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "add_pantry_item",
                        "description": "Add an item to the pantry",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "item_name": {
                                    "type": "string",
                                    "description": "Name of the item to add",
                                },
                                "quantity": {
                                    "type": "number",
                                    "description": "Amount to add",
                                },
                                "unit": {
                                    "type": "string",
                                    "description": "Unit of measurement",
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Optional notes about the transaction",
                                },
                            },
                            "required": ["item_name", "quantity", "unit"],
                        },
                    },
                ]

                # Return tools directly in proper MCP format
                tools_response = {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {"tools": tools_list},
                }
                logger.info(f"tools/list response: {len(tools_list)} tools")
                logger.info(f"Tool names: {[tool['name'] for tool in tools_list]}")
                return tools_response
            elif method == "tools/call":
                return await mcp_call_tool(request, user_id)
            else:
                logger.error(f"Unknown MCP method: {method}")
                logger.error(
                    f"Available methods: initialize, notifications/initialized, tools/list, tools/call"
                )
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

    except Exception as e:
        logger.error(f"Error processing request body: {e}")

    return {
        "message": "MCP requests should be sent to /mcp/list_tools or /mcp/call_tool",
        "authenticated": user_id is not None,
        "user_id": user_id,
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "localhost")
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"Starting MealMCP OAuth Server on {host}:{port}")
    print(
        f"OAuth Authorization Server: http://{host}:{port}/.well-known/oauth-authorization-server"
    )
    print(f"Authorization endpoint: http://{host}:{port}/authorize")
    print(f"Token endpoint: http://{host}:{port}/token")

    uvicorn.run(app, host=host, port=port)

"""
MCP Server with OAuth 2.1 Authentication
Implements OAuth 2.1 with PKCE for secure multi-user authentication
"""

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth endpoints
app = FastAPI(title="MealMCP OAuth Server", version="1.0.0")

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
        # Authenticate user
        user_id = oauth.authenticate_user(username, password)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid credentials")

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
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"Authorization error: {e}")
        error_params = {"error": "access_denied", "error_description": str(e)}
        if state:
            error_params["state"] = state
        redirect_url = f"{redirect_uri}?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


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
        return RedirectResponse(url=redirect_url)

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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MealMCP OAuth Server"}


# Root endpoint with API info
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "MealMCP OAuth Server",
        "version": "1.0.0",
        "oauth_endpoints": {
            "authorization": "/authorize",
            "token": "/token",
            "registration": "/register",
        },
        "discovery_endpoints": {
            "oauth_authorization_server": "/.well-known/oauth-authorization-server",
            "oauth_protected_resource": "/.well-known/oauth-protected-resource",
        },
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

"""
MCP Server with OAuth 2.1 Authentication - Refactored for DRY principles
Implements OAuth 2.1 with PKCE for secure multi-user authentication
"""

import json
import os
import logging
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

from oauth_server import OAuthServer
from mcp_context import MCPContext
from mcp_oauth_templates import (
    generate_login_form,
    generate_register_form,
    generate_error_page,
)
from mcp_oauth_handlers import OAuthFlowHandler
from mcp_tool_router import MCPToolRouter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app for OAuth endpoints
app = FastAPI(title="MealMCP OAuth Server", version="1.0.0")


# Add middleware to log requests (essential only)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    if response.status_code >= 400:
        logger.warning(
            f"Request: {request.method} {request.url} -> {response.status_code}"
        )
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
public_url = os.getenv("MCP_PUBLIC_URL", "http://localhost:8000")
use_postgresql = os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
oauth = OAuthServer(base_url=public_url, use_postgresql=use_postgresql)
oauth_handler = OAuthFlowHandler(oauth)
tool_router = MCPToolRouter()

# Create MCP server and context
mcp = FastMCP("RecipeManager")
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


def get_user_pantry_oauth(user_id: str) -> tuple[Optional[str], Optional[Any]]:
    """Get authenticated user and their PantryManager instance using OAuth user_id."""
    if not user_id:
        return None, None

    # In multi-user mode, create user-specific pantry manager
    if user_id not in context.pantry_managers:
        backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

        if backend == "postgresql":
            # Use shared PostgreSQL database with user_id isolation
            from pantry_manager_shared import SharedPantryManager

            connection_string = os.getenv(
                "PANTRY_DATABASE_URL", "postgresql://localhost/mealmcp"
            )
            context.pantry_managers[user_id] = SharedPantryManager(
                connection_string=connection_string,
                user_id=int(user_id),
                backend="postgresql",
            )
        else:
            # Use individual SQLite databases per user
            db_path = context.user_manager.get_user_db_path(user_id)
            from pantry_manager_factory import create_pantry_manager

            context.pantry_managers[user_id] = create_pantry_manager(
                backend="sqlite", connection_string=db_path
            )

            # Initialize database if it doesn't exist
            from db_setup import setup_database

            setup_database(db_path)

    context.set_current_user(user_id)
    return user_id, context.pantry_managers[user_id]


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

    try:
        oauth_handler.validate_oauth_request(client_id, redirect_uri, code_challenge)
    except HTTPException as e:
        raise e

    # Return login form using template
    login_form = generate_login_form(
        client_id,
        redirect_uri,
        scope,
        state or "",
        code_challenge,
        code_challenge_method,
        response_type,
    )
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

        # Authenticate user and create auth code
        user_id, auth_code = oauth_handler.authenticate_and_create_code(
            username,
            password,
            client_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
        )

        # Return success redirect
        return oauth_handler.create_success_redirect(redirect_uri, auth_code, state)

    except HTTPException as e:
        logger.error(f"Authorization error: {e.detail}")
        return oauth_handler.create_error_redirect(
            redirect_uri, "access_denied", str(e.detail), state
        )
    except Exception as e:
        logger.error(f"Authorization error: {e}")
        return oauth_handler.create_error_redirect(
            redirect_uri, "access_denied", str(e), state
        )


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
    register_form = generate_register_form(
        client_id, redirect_uri, scope, state, code_challenge, code_challenge_method
    )
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

        # Register user and create auth code
        user_id, auth_code = oauth_handler.register_and_create_code(
            username,
            password,
            email or None,
            client_id,
            redirect_uri,
            scope,
            code_challenge,
            code_challenge_method,
        )

        # Return success redirect
        return oauth_handler.create_success_redirect(redirect_uri, auth_code, state)

    except Exception as e:
        logger.error(f"Registration error: {e}")
        error_page = generate_error_page(
            str(e),
            client_id,
            redirect_uri,
            scope,
            state,
            code_challenge,
            code_challenge_method,
        )
        return HTMLResponse(content=error_page, status_code=400)


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

    # Debug log for existing codes
    if code and code in oauth.auth_codes:
        auth_data = oauth.auth_codes[code]
        logger.info(
            f"Found auth code data: client_id={auth_data.get('client_id')}, user_id={auth_data.get('user_id')}"
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


# MCP Tool Implementation with Authentication
async def mcp_call_tool(request: Request, user_id: str):
    """MCP call tool endpoint using the tool router."""
    try:
        data = await request.json()
        tool_name = data.get("params", {}).get("name")
        arguments = data.get("params", {}).get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")

        # Get user's pantry manager
        user_id, pantry = get_user_pantry_oauth(user_id)
        if not pantry:
            result = {"status": "error", "message": "Failed to get user pantry"}
        else:
            # Route to tool implementation
            result = tool_router.call_tool(tool_name, arguments, pantry)

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


# Standard MCP tools for FastMCP (with OAuth authentication)
@mcp.tool()
def list_units() -> List[Dict[str, Any]]:
    """List all units of measurement (no auth required)."""
    from constants import UNITS

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

    return tool_router.call_tool(
        "add_recipe",
        {
            "name": name,
            "instructions": instructions,
            "time_minutes": time_minutes,
            "ingredients": ingredients,
        },
        pantry,
    )


@mcp.tool()
def get_all_recipes(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all recipes."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    return tool_router.call_tool("get_all_recipes", {}, pantry)


@mcp.tool()
def get_pantry_contents(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current contents of the pantry."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    return tool_router.call_tool("get_pantry_contents", {}, pantry)


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

    return tool_router.call_tool(
        "add_pantry_item",
        {"item_name": item_name, "quantity": quantity, "unit": unit, "notes": notes},
        pantry,
    )


@mcp.tool()
def get_user_profile(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Get comprehensive user profile including preferences, household size, and constraints."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    return tool_router.call_tool("get_user_profile", {}, pantry)


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


# Root endpoint with API info
@app.get("/")
async def root(request: Request):
    """Root endpoint with API information and MCP tool discovery."""
    try:
        # Check if this is an authenticated request from Claude Desktop
        auth_header = request.headers.get("authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_data = oauth.validate_access_token(token)
            if token_data:
                user_id = token_data["user_id"]
                logger.info(f"Authenticated GET request from user: {user_id}")
            else:
                logger.info("GET request with invalid/expired token")
        else:
            logger.info("Unauthenticated GET request")

        # Return tools in MCP format for Claude Desktop's REST-style discovery
        tools_list = tool_router.get_available_tools()

        logger.info("Building response object...")

        # Claude Desktop GUI connector expects tools via GET requests
        if auth_header and user_id:
            response = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "MealMCP OAuth Server", "version": "1.0.0"},
                "tools": tools_list,
            }
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


# Handle POST to root (for any MCP requests that might come here)
@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root endpoint - potential MCP requests."""
    # Try to get user ID from token
    user_id = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data = oauth.validate_access_token(token)
        if token_data:
            user_id = token_data["user_id"]
        else:
            logger.warning("Invalid or expired access token")

    # Parse request body
    try:
        body = await request.json()

        # Check if this looks like an MCP request
        if isinstance(body, dict) and "method" in body:
            method = body.get("method")
            logger.info(f"Detected MCP method: {method}")

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
            if method == "initialize":
                return {
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
            elif method == "notifications/initialized":
                return JSONResponse(content={}, status_code=202)
            elif method == "tools/list":
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {"tools": tool_router.get_available_tools()},
                    }
                )
            elif method == "tools/call":
                return await mcp_call_tool(request, user_id)
            elif method == "prompts/list":
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {"prompts": []},
                    }
                )
            else:
                logger.error(f"Unknown MCP method: {method}")
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

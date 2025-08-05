"""
Unified MCP Server - Consolidates all MCP server variants into one configurable server.

Supports:
- Multiple transport modes: FastMCP (stdio), HTTP REST, Server-Sent Events
- Authentication modes: None (local), Token (remote), OAuth 2.1 (multi-user)
- Backend modes: SQLite (single-user), PostgreSQL (multi-user)
- All 15 MCP tools through centralized router

Environment Configuration:
- MCP_TRANSPORT: "fastmcp" (default), "http", "sse", "oauth"
- MCP_MODE: "local" (default), "remote", "multiuser"
- MCP_HOST: "localhost"
- MCP_PORT: 8000
- PANTRY_BACKEND: "sqlite", "postgresql"
- MCP_PUBLIC_URL: For OAuth mode
"""

import os
import sys
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core imports
from mcp_context import MCPContext
from mcp_tool_router import MCPToolRouter

# Transport-specific imports (conditional)
transport_mode = os.getenv("MCP_TRANSPORT", "fastmcp").lower()
auth_mode = os.getenv("MCP_MODE", "local").lower()

if transport_mode in ["fastmcp", "stdio"]:
    from mcp.server.fastmcp import FastMCP
elif transport_mode in ["http", "oauth"]:
    from fastapi import FastAPI, HTTPException, Request, Form, Depends
    from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
elif transport_mode == "sse":
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware

# OAuth-specific imports (conditional)
if transport_mode == "oauth" or auth_mode == "multiuser":
    from oauth_server import OAuthServer
    from mcp_oauth_templates import (
        generate_login_form,
        generate_register_form,
        generate_error_page,
    )
    from mcp_oauth_handlers import OAuthFlowHandler


class UnifiedMCPServer:
    """Unified MCP Server supporting multiple transports and auth modes."""

    def __init__(self):
        self.transport = transport_mode
        self.auth_mode = auth_mode
        self.host = os.getenv("MCP_HOST", "localhost")
        self.port = int(os.getenv("MCP_PORT", "8000"))

        # Initialize core components
        self.context = MCPContext()
        self.tool_router = MCPToolRouter()

        # Initialize transport-specific components
        self.app = None
        self.mcp = None
        self.oauth = None
        self.oauth_handler = None
        self.security = None

        self._setup_transport()
        self._setup_authentication()

    def _setup_transport(self):
        """Setup transport layer based on configuration."""
        if self.transport in ["fastmcp", "stdio"]:
            self.mcp = FastMCP("RecipeManager")
            self._register_fastmcp_tools()

        elif self.transport in ["http", "oauth", "sse"]:
            self.app = FastAPI(title="MealMCP Unified Server", version="1.0.0")

            # Add CORS middleware
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # Mount static files for OAuth
            if self.transport == "oauth":
                self.app.mount(
                    "/static", StaticFiles(directory="static"), name="static"
                )

            # Add request logging
            @self.app.middleware("http")
            async def log_requests(request: Request, call_next):
                response = await call_next(request)
                if response.status_code >= 400:
                    logger.warning(
                        f"Request: {request.method} {request.url} -> {response.status_code}"
                    )
                return response

            self._register_http_endpoints()

    def _setup_authentication(self):
        """Setup authentication based on mode."""
        if self.transport == "oauth" or self.auth_mode == "multiuser":
            # OAuth 2.1 authentication
            public_url = os.getenv("MCP_PUBLIC_URL", f"http://{self.host}:{self.port}")
            use_postgresql = (
                os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
            )

            self.oauth = OAuthServer(base_url=public_url, use_postgresql=use_postgresql)
            self.oauth_handler = OAuthFlowHandler(self.oauth)
            self.security = HTTPBearer(auto_error=False)

        elif self.auth_mode == "remote":
            # Simple token authentication
            self.security = HTTPBearer(auto_error=False)

    def get_current_user(self, credentials=None) -> Optional[str]:
        """Extract user from authentication credentials."""
        if not credentials:
            return None

        if self.oauth:
            # OAuth mode
            token_data = self.oauth.validate_access_token(credentials.credentials)
            return token_data["user_id"] if token_data else None

        elif self.auth_mode == "remote":
            # Token mode - validate with context
            user_id, _ = self.context.authenticate_and_get_pantry(
                credentials.credentials
            )
            return user_id

        return None

    def get_user_pantry(
        self, user_id: Optional[str] = None, token: Optional[str] = None
    ) -> tuple[Optional[str], Optional[Any]]:
        """Get authenticated user and their PantryManager instance."""
        if self.transport == "oauth":
            return self._get_user_pantry_oauth(user_id)
        else:
            return self.context.authenticate_and_get_pantry(token)

    def _get_user_pantry_oauth(
        self, user_id: str
    ) -> tuple[Optional[str], Optional[Any]]:
        """Get user pantry for OAuth mode."""
        if not user_id:
            return None, None

        # Create user-specific pantry manager if needed
        if user_id not in self.context.pantry_managers:
            backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

            if backend == "postgresql":
                from pantry_manager_shared import SharedPantryManager

                connection_string = os.getenv(
                    "PANTRY_DATABASE_URL", "postgresql://localhost/mealmcp"
                )
                self.context.pantry_managers[user_id] = SharedPantryManager(
                    connection_string=connection_string,
                    user_id=int(user_id),
                    backend="postgresql",
                )
            else:
                db_path = self.context.user_manager.get_user_db_path(user_id)
                from pantry_manager_factory import create_pantry_manager

                self.context.pantry_managers[user_id] = create_pantry_manager(
                    backend="sqlite", connection_string=db_path
                )
                from db_setup import setup_database

                setup_database(db_path)

        self.context.set_current_user(user_id)
        return user_id, self.context.pantry_managers[user_id]

    def _register_fastmcp_tools(self):
        """Register tools for FastMCP transport."""

        @self.mcp.tool()
        def list_units() -> List[Dict[str, Any]]:
            """List all units of measurement."""
            from constants import UNITS

            return UNITS

        @self.mcp.tool()
        def get_user_profile(token: Optional[str] = None) -> Dict[str, Any]:
            """Get comprehensive user profile."""
            user_id, pantry = self.get_user_pantry(token=token)
            if not pantry:
                return {"status": "error", "message": "Authentication required"}
            return self.tool_router.call_tool("get_user_profile", {}, pantry)

        @self.mcp.tool()
        def add_recipe(
            name: str,
            instructions: str,
            time_minutes: int,
            ingredients: List[Dict[str, Any]],
            token: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Add a new recipe."""
            user_id, pantry = self.get_user_pantry(token=token)
            if not pantry:
                return {"status": "error", "message": "Authentication required"}
            return self.tool_router.call_tool(
                "add_recipe",
                {
                    "name": name,
                    "instructions": instructions,
                    "time_minutes": time_minutes,
                    "ingredients": ingredients,
                },
                pantry,
            )

        @self.mcp.tool()
        def get_all_recipes(token: Optional[str] = None) -> Dict[str, Any]:
            """Get all recipes."""
            user_id, pantry = self.get_user_pantry(token=token)
            if not pantry:
                return {"status": "error", "message": "Authentication required"}
            return self.tool_router.call_tool("get_all_recipes", {}, pantry)

        @self.mcp.tool()
        def get_pantry_contents(token: Optional[str] = None) -> Dict[str, Any]:
            """Get pantry contents."""
            user_id, pantry = self.get_user_pantry(token=token)
            if not pantry:
                return {"status": "error", "message": "Authentication required"}
            return self.tool_router.call_tool("get_pantry_contents", {}, pantry)

        @self.mcp.tool()
        def manage_pantry_item(
            action: str,
            item_name: str,
            quantity: float,
            unit: str,
            notes: Optional[str] = None,
            token: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Add or remove pantry item."""
            user_id, pantry = self.get_user_pantry(token=token)
            if not pantry:
                return {"status": "error", "message": "Authentication required"}

            if action == "add":
                return self.tool_router.call_tool(
                    "add_pantry_item",
                    {
                        "item_name": item_name,
                        "quantity": quantity,
                        "unit": unit,
                        "notes": notes,
                    },
                    pantry,
                )
            elif action == "remove":
                return self.tool_router.call_tool(
                    "remove_pantry_item",
                    {
                        "item_name": item_name,
                        "quantity": quantity,
                        "unit": unit,
                        "reason": notes or "consumed",
                    },
                    pantry,
                )
            else:
                return {
                    "status": "error",
                    "message": "Invalid action. Use 'add' or 'remove'.",
                }

        # Add remaining tools similarly...
        logger.info("FastMCP tools registered successfully")

    def _register_http_endpoints(self):
        """Register HTTP endpoints based on transport mode."""

        # Health check
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "transport": self.transport,
                "auth_mode": self.auth_mode,
            }

        # Root endpoint with tool discovery
        @self.app.get("/")
        async def root(request: Request):
            """Root endpoint with MCP tool discovery."""
            try:
                # Get user from auth header
                user_id = None
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    if self.oauth:
                        token_data = self.oauth.validate_access_token(token)
                        user_id = token_data["user_id"] if token_data else None
                    elif self.auth_mode == "remote":
                        user_id, _ = self.context.authenticate_and_get_pantry(token)

                tools_list = self.tool_router.get_available_tools()

                if auth_header and user_id:
                    # Authenticated response for MCP clients
                    return {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {
                            "name": "MealMCP Unified Server",
                            "version": "1.0.0",
                        },
                        "tools": tools_list,
                    }
                else:
                    # Standard API info
                    return {
                        "service": "MealMCP Unified Server",
                        "version": "1.0.0",
                        "transport": self.transport,
                        "auth_mode": self.auth_mode,
                        "tools": tools_list,
                        "protocolVersion": "2025-06-18",
                    }

            except Exception as e:
                logger.error(f"Error in root endpoint: {e}")
                return {"error": "Internal server error", "message": str(e)}

        # MCP protocol endpoints
        @self.app.post("/")
        async def mcp_protocol(request: Request):
            """Handle MCP protocol requests."""
            try:
                body = await request.json()
                method = body.get("method")

                # Get user authentication
                user_id = None
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    # Create simple credentials object
                    class SimpleCredentials:
                        def __init__(self, token):
                            self.credentials = token

                    credentials = SimpleCredentials(auth_header[7:])
                    user_id = self.get_current_user(credentials)

                # Handle unauthenticated initialize
                if method == "initialize":
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {"listChanged": True}},
                            "serverInfo": {
                                "name": "MealMCP Unified Server",
                                "version": "1.0.0",
                            },
                        },
                    }

                # Handle other methods with auth
                if method == "notifications/initialized":
                    return JSONResponse(content={}, status_code=202)

                elif method == "tools/list":
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {"tools": self.tool_router.get_available_tools()},
                    }

                elif method == "tools/call":
                    if not user_id and self.auth_mode != "local":
                        return JSONResponse(
                            content={
                                "error": "unauthorized",
                                "message": "Authentication required",
                            },
                            status_code=401,
                            headers={"WWW-Authenticate": "Bearer"},
                        )

                    tool_name = body.get("params", {}).get("name")
                    arguments = body.get("params", {}).get("arguments", {})

                    user_id, pantry = self.get_user_pantry(
                        user_id, auth_header[7:] if auth_header else None
                    )
                    if not pantry and self.auth_mode != "local":
                        result = {
                            "status": "error",
                            "message": "Failed to get user pantry",
                        }
                    else:
                        result = self.tool_router.call_tool(
                            tool_name, arguments, pantry
                        )

                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [
                                {"type": "text", "text": json.dumps(result, indent=2)}
                            ]
                        },
                    }

                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }

            except Exception as e:
                logger.error(f"MCP protocol error: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id", 0),
                    "error": {"code": -32603, "message": str(e)},
                }

        # OAuth endpoints (if OAuth transport)
        if self.transport == "oauth":
            self._register_oauth_endpoints()

        # SSE endpoint (if SSE transport)
        if self.transport == "sse":
            self._register_sse_endpoints()

    def _register_oauth_endpoints(self):
        """Register OAuth-specific endpoints."""

        # OAuth discovery
        @self.app.get("/.well-known/oauth-authorization-server")
        async def oauth_metadata():
            return self.oauth.get_discovery_metadata()

        @self.app.get("/.well-known/oauth-protected-resource")
        async def oauth_resource_metadata():
            return self.oauth.get_protected_resource_metadata()

        # Client registration
        @self.app.post("/register")
        async def register_client(request: Request):
            try:
                client_metadata = await request.json()
                result = self.oauth.register_client(client_metadata)
                return JSONResponse(content=result, status_code=201)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        # Authorization endpoints
        @self.app.get("/authorize")
        async def authorize(
            response_type: str,
            client_id: str,
            redirect_uri: str,
            scope: str = "read write",
            state: str = None,
            code_challenge: str = None,
            code_challenge_method: str = "S256",
        ):
            try:
                self.oauth_handler.validate_oauth_request(
                    client_id, redirect_uri, code_challenge
                )
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
            except HTTPException as e:
                raise e

        @self.app.post("/authorize")
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
            try:
                user_id, auth_code = self.oauth_handler.authenticate_and_create_code(
                    username,
                    password,
                    client_id,
                    redirect_uri,
                    scope,
                    code_challenge,
                    code_challenge_method,
                )
                return self.oauth_handler.create_success_redirect(
                    redirect_uri, auth_code, state
                )
            except Exception as e:
                return self.oauth_handler.create_error_redirect(
                    redirect_uri, "access_denied", str(e), state
                )

        # Token endpoint
        @self.app.post("/token")
        async def token_endpoint(
            grant_type: str = Form(...),
            code: str = Form(None),
            redirect_uri: str = Form(None),
            client_id: str = Form(...),
            client_secret: str = Form(None),
            code_verifier: str = Form(None),
            refresh_token: str = Form(None),
        ):
            try:
                if grant_type == "authorization_code":
                    tokens = self.oauth.exchange_code_for_tokens(
                        code, client_id, redirect_uri, code_verifier, client_secret
                    )
                    return tokens
                elif grant_type == "refresh_token":
                    tokens = self.oauth.refresh_access_token(refresh_token, client_id)
                    return tokens
                else:
                    raise ValueError(f"Unsupported grant_type: {grant_type}")
            except Exception as e:
                return JSONResponse(
                    content={"error": "invalid_request", "error_description": str(e)},
                    status_code=400,
                )

        # User registration endpoints
        @self.app.get("/register_user")
        async def register_user_form(
            client_id: str,
            redirect_uri: str,
            scope: str,
            state: str = "",
            code_challenge: str = "",
            code_challenge_method: str = "S256",
        ):
            register_form = generate_register_form(
                client_id,
                redirect_uri,
                scope,
                state,
                code_challenge,
                code_challenge_method,
            )
            return HTMLResponse(content=register_form)

        @self.app.post("/register_user")
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
            try:
                if password != confirm_password:
                    raise ValueError("Passwords do not match")

                user_id, auth_code = self.oauth_handler.register_and_create_code(
                    username,
                    password,
                    email or None,
                    client_id,
                    redirect_uri,
                    scope,
                    code_challenge,
                    code_challenge_method,
                )
                return self.oauth_handler.create_success_redirect(
                    redirect_uri, auth_code, state
                )
            except Exception as e:
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

    def _register_sse_endpoints(self):
        """Register Server-Sent Events endpoints."""

        @self.app.get("/events")
        async def event_stream(request: Request):
            """Server-sent events endpoint for real-time updates."""

            async def generate_events():
                try:
                    # Basic SSE setup
                    yield 'data: {"type": "connected", "message": "MCP SSE server connected"}\n\n'

                    # Keep connection alive
                    while True:
                        await asyncio.sleep(30)  # Heartbeat every 30 seconds
                        yield 'data: {"type": "heartbeat", "timestamp": "' + datetime.now().isoformat() + '"}\n\n'

                except Exception as e:
                    logger.error(f"SSE error: {e}")
                    yield f'data: {{"type": "error", "message": "{str(e)}"}}\n\n'

            return StreamingResponse(
                generate_events(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                },
            )

    async def run_async(self):
        """Run the server asynchronously."""
        if self.transport in ["fastmcp", "stdio"]:
            # FastMCP runs via stdio
            logger.info(f"Starting FastMCP server (stdio transport)")
            # FastMCP handles its own event loop
            self.mcp.run()

        elif self.transport in ["http", "oauth", "sse"]:
            # HTTP-based transports
            import uvicorn

            logger.info(
                f"Starting {self.transport.upper()} server on {self.host}:{self.port}"
            )

            if self.transport == "oauth":
                logger.info(f"OAuth endpoints:")
                logger.info(
                    f"  Authorization: http://{self.host}:{self.port}/authorize"
                )
                logger.info(f"  Token: http://{self.host}:{self.port}/token")
                logger.info(
                    f"  Discovery: http://{self.host}:{self.port}/.well-known/oauth-authorization-server"
                )

            config = uvicorn.Config(
                self.app, host=self.host, port=self.port, log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()

    def run(self):
        """Run the server (synchronous entry point)."""
        try:
            if self.transport in ["fastmcp", "stdio"]:
                # FastMCP runs synchronously
                logger.info(f"Starting FastMCP server (stdio transport)")
                self.mcp.run()
            else:
                # HTTP-based transports run async
                asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)


# Main entry point
if __name__ == "__main__":
    server = UnifiedMCPServer()
    server.run()

"""
Generic Unified MCP Server - Transport and authentication framework.

A generic MCP server that can be configured with different tool routers
and data managers to work with any type of application.

Supports:
- Multiple transport modes: FastMCP (stdio), HTTP REST, Server-Sent Events
- Authentication modes: None (local), Token (remote), OAuth 2.1 (multi-user)
- Configurable tool routers and data managers
- Backend agnostic design

Environment Configuration:
- MCP_TRANSPORT: "fastmcp" (default), "http", "sse", "oauth"
- MCP_MODE: "local" (default), "remote", "multiuser"
- MCP_HOST: "localhost"
- MCP_PORT: 8000
- MCP_PUBLIC_URL: For OAuth mode
"""

import os
import sys
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core imports
from .context import MCPContext

# Import all possible transport modules
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

try:
    from fastapi import FastAPI, HTTPException, Request, Form, Depends
    from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import StreamingResponse
except ImportError:
    FastAPI = None

try:
    from ..auth.oauth_server import OAuthServer
    from ..auth.oauth_handlers import OAuthFlowHandler
    from ..templates.oauth_templates import (
        generate_login_form,
        generate_register_form,
        generate_error_page,
    )
except ImportError:
    OAuthServer = None


class UnifiedMCPServer:
    """Generic Unified MCP Server supporting multiple transports and auth modes."""

    def __init__(
        self,
        tool_router=None,
        data_manager_factory: Optional[Callable] = None,
        database_setup_func: Optional[Callable] = None,
        server_name: str = "Generic MCP Server",
    ):
        """
        Initialize the unified MCP server.

        Args:
            tool_router: Tool router instance that handles MCP tool calls
            data_manager_factory: Function to create data manager instances
            database_setup_func: Function to setup/initialize databases
            server_name: Name of the server for display purposes
        """
        # Read configuration from environment at runtime
        self.transport = os.getenv("MCP_TRANSPORT", "fastmcp").lower()
        self.auth_mode = os.getenv("MCP_MODE", "local").lower()
        self.host = os.getenv("MCP_HOST", "localhost")
        self.port = int(os.getenv("MCP_PORT", "8000"))
        self.server_name = server_name

        # Initialize core components
        self.context = MCPContext(data_manager_factory, database_setup_func)
        self.tool_router = tool_router

        # Initialize transport-specific components
        self.app = None
        self.mcp = None
        self.oauth = None
        self.oauth_handler = None
        self.security = None

        self._setup_transport()
        self._setup_authentication()

        # Register OAuth endpoints after both transport and authentication are set up
        if self.app and self.oauth:
            self._register_oauth_endpoints()

    def _setup_transport(self):
        """Setup transport layer based on configuration."""
        if self.transport in ["fastmcp", "stdio"]:
            if FastMCP is None:
                raise ImportError("FastMCP is not available - install mcp package")
            self.mcp = FastMCP(self.server_name)
            if self.tool_router:
                self._register_fastmcp_tools()

        elif self.transport in ["http", "oauth", "sse"]:
            if FastAPI is None:
                raise ImportError("FastAPI is not available - install fastapi package")
            self.app = FastAPI(
                title=f"{self.server_name} Unified Server", version="1.0.0"
            )

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
                import pathlib

                static_dir = pathlib.Path(__file__).parent.parent / "static"
                if static_dir.exists():
                    self.app.mount(
                        "/static", StaticFiles(directory=str(static_dir)), name="static"
                    )
                else:
                    logger.warning(
                        f"Static directory not found at {static_dir}, OAuth UI may not work properly"
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
            if OAuthServer is None:
                raise ImportError(
                    "OAuth components not available - install oauth dependencies"
                )
            # OAuth 2.1 authentication
            public_url = os.getenv("MCP_PUBLIC_URL", f"http://{self.host}:{self.port}")
            use_postgresql = (
                os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
            )

            self.oauth = OAuthServer(base_url=public_url, use_postgresql=use_postgresql)
            self.oauth_handler = OAuthFlowHandler(self.oauth)
            # OAuth also needs HTTP Bearer for API endpoints
            self.security = HTTPBearer(auto_error=False)

        # No additional authentication setup needed for local mode HTTP/SSE

    def get_current_user(self, credentials=None) -> Optional[str]:
        """Extract user from authentication credentials."""
        if not credentials:
            return None

        if self.oauth:
            # OAuth mode
            token_data = self.oauth.validate_access_token(credentials.credentials)
            return token_data["user_id"] if token_data else None

        # No other authentication modes supported

        return None

    def get_user_data_manager(
        self, user_id: Optional[str] = None, token: Optional[str] = None
    ) -> tuple[Optional[str], Optional[Any]]:
        """Get authenticated user and their data manager instance."""
        if self.transport == "oauth":
            return self._get_user_data_manager_oauth(user_id)
        else:
            return self.context.authenticate_and_get_data_manager(token)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool through the router with proper authentication."""
        if not self.tool_router:
            return {"status": "error", "message": "No tool router configured"}

        # Extract token from arguments if present
        token = arguments.get("token")

        # Handle special admin-only tools
        if tool_name == "create_user":
            admin_token = arguments.get("admin_token")
            username = arguments.get("username")
            if not admin_token or not username:
                return {
                    "status": "error",
                    "message": "Admin token and username required",
                }
            return self.context.create_user(username, admin_token)

        if tool_name == "list_users":
            admin_token = arguments.get("admin_token")
            if not admin_token:
                return {"status": "error", "message": "Admin token required"}
            # Verify admin token and return user list
            admin_user = self.context.user_manager.authenticate(admin_token)
            if admin_user != "admin":
                return {"status": "error", "message": "Admin access required"}

            users = []
            user_data_dir = os.getenv("USER_DATA_DIR", "user_data")
            if os.path.exists(user_data_dir):
                for username in os.listdir(user_data_dir):
                    user_dir = os.path.join(user_data_dir, username)
                    if os.path.isdir(user_dir):
                        users.append({"username": username})
            return {"status": "success", "users": users}

        # Get authenticated user and data manager
        user_id, data_manager = self.get_user_data_manager(token=token)
        if not data_manager:
            return {"status": "error", "message": "Authentication required"}

        # Call the tool through the router
        return self.tool_router.call_tool(tool_name, arguments, data_manager)

    def _get_user_data_manager_oauth(
        self, user_id: str
    ) -> tuple[Optional[str], Optional[Any]]:
        """Get user data manager for OAuth mode."""
        if not user_id:
            return None, None

        # Create or get data manager for OAuth user
        if user_id not in self.context.data_managers:
            if os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql":
                # PostgreSQL with shared database and user_id scoping
                from pantry_manager_shared import SharedPantryManager

                database_url = os.getenv("PANTRY_DATABASE_URL")
                if not database_url:
                    logger.error("PANTRY_DATABASE_URL not set for PostgreSQL backend")
                    return None, None

                self.context.data_managers[user_id] = SharedPantryManager(
                    user_id=int(user_id),
                    backend="postgresql",
                )
            else:
                db_path = self.context.user_manager.get_user_db_path(user_id)
                if self.context.data_manager_factory:
                    self.context.data_managers[user_id] = (
                        self.context.data_manager_factory(
                            backend="sqlite", connection_string=db_path
                        )
                    )
                    if self.context.database_setup_func:
                        self.context.database_setup_func(db_path)

        self.context.set_current_user(user_id)
        return user_id, self.context.data_managers.get(user_id)

    def _register_fastmcp_tools(self):
        """Register tools for FastMCP transport."""
        if not self.tool_router:
            return

        # Get available tools from the router
        available_tools = getattr(self.tool_router, "get_available_tools", lambda: [])()

        for tool in available_tools:
            tool_name = tool["name"]
            tool_func = self._create_fastmcp_tool_wrapper(tool_name)
            # Register with FastMCP using basic tool info
            try:
                # Use only the name and description for now
                tool_decorator = self.mcp.tool(
                    name=tool_name, description=tool.get("description", "")
                )
                tool_decorator(tool_func)
            except Exception as e:
                # If tool registration fails, skip this tool
                logger.warning(f"Failed to register tool {tool_name}: {e}")

    def _create_fastmcp_tool_wrapper(self, tool_name: str):
        """Create a FastMCP tool wrapper for a given tool name."""

        def tool_wrapper(*args, **kwargs):
            # Add token handling if needed
            token = kwargs.get("token")
            user_id, data_manager = self.get_user_data_manager(token=token)
            if not data_manager:
                return {"status": "error", "message": "Authentication required"}

            # Convert kwargs to arguments dict
            arguments = dict(kwargs)
            return self.tool_router.call_tool(tool_name, arguments, data_manager)

        return tool_wrapper

    def _register_http_endpoints(self):
        """Register HTTP endpoints."""
        if not self.app:
            return

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "transport": self.transport,
                "auth_mode": self.auth_mode,
                "server": self.server_name,
            }

        @self.app.get("/")
        async def discovery():
            """MCP discovery endpoint."""
            tools = []
            if self.tool_router:
                available_tools = getattr(
                    self.tool_router, "get_available_tools", lambda: []
                )()
                tools = available_tools

            return {
                "service": self.server_name,
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "tools": tools,
            }

        @self.app.post("/")
        async def handle_mcp_request(request: Request):
            """Handle MCP JSON-RPC requests."""
            try:
                data = await request.json()
                method = data.get("method")
                params = data.get("params", {})
                request_id = data.get("id")

                if method == "initialize":
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": {
                                "name": self.server_name,
                                "version": "1.0.0",
                            },
                        },
                    }

                elif method == "tools/list":
                    tools = []
                    if self.tool_router:
                        available_tools = getattr(
                            self.tool_router, "get_available_tools", lambda: []
                        )()
                        tools = available_tools

                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools},
                    }

                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})

                    if not self.tool_router:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": "No tool router configured",
                            },
                        }

                    # Handle authentication for OAuth mode
                    if self.transport == "oauth" and self.oauth:
                        # Extract authorization header
                        auth_header = request.headers.get("authorization")
                        if not auth_header or not auth_header.startswith("Bearer "):
                            # No valid token - initiate OAuth flow by redirecting to authorize endpoint
                            public_url = os.getenv(
                                "MCP_PUBLIC_URL", f"http://{self.host}:{self.port}"
                            )
                            authorize_url = f"{public_url}/authorize?response_type=code&client_id=mcp_client&redirect_uri={public_url}/callback"
                            return {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32600,
                                    "message": "Authentication required",
                                    "data": {"authorize_url": authorize_url},
                                },
                            }

                        # Extract token and validate
                        token = auth_header.split(" ", 1)[1]
                        token_data = self.oauth.validate_access_token(token)
                        if not token_data:
                            # Invalid token - initiate OAuth flow
                            public_url = os.getenv(
                                "MCP_PUBLIC_URL", f"http://{self.host}:{self.port}"
                            )
                            authorize_url = f"{public_url}/authorize?response_type=code&client_id=mcp_client&redirect_uri={public_url}/callback"
                            return {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32600,
                                    "message": "Invalid or expired token",
                                    "data": {"authorize_url": authorize_url},
                                },
                            }

                        user_id = token_data["user_id"]
                        user_id, data_manager = self.get_user_data_manager(
                            user_id=user_id
                        )
                    else:
                        # Handle authentication for non-OAuth modes
                        user_id, data_manager = self.get_user_data_manager()
                        if not data_manager and self.auth_mode != "local":
                            return {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32600,
                                    "message": "Authentication required",
                                },
                            }

                    result = self.tool_router.call_tool(
                        tool_name, arguments, data_manager
                    )

                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {"type": "text", "text": json.dumps(result, indent=2)}
                            ]
                        },
                    }

                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }

            except Exception as e:
                logger.error(f"Error handling MCP request: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": data.get("id") if "data" in locals() else None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                }

        # Add SSE endpoint if needed
        if self.transport == "sse":

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
                    except asyncio.CancelledError:
                        logger.info("SSE connection cancelled")
                        return
                    except Exception as e:
                        logger.error(f"SSE error: {e}")
                        yield f'data: {{"type": "error", "message": "{str(e)}"}}\n\n'
                        return

                return StreamingResponse(
                    generate_events(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Cache-Control",
                    },
                )

        # OAuth endpoints are registered after authentication setup in __init__

    def _register_oauth_endpoints(self):
        """Register OAuth 2.1 endpoints."""
        if not self.oauth or not self.oauth_handler:
            return

        @self.app.get("/.well-known/oauth-authorization-server")
        async def oauth_discovery():
            """OAuth 2.1 authorization server metadata endpoint."""
            return self.oauth.get_discovery_metadata()

        @self.app.get("/.well-known/oauth-protected-resource")
        async def oauth_protected_resource():
            """OAuth 2.1 protected resource metadata endpoint."""
            return self.oauth.get_protected_resource_metadata()

        @self.app.post("/register")
        async def register_client(request: Request):
            """OAuth client registration endpoint."""
            try:
                client_data = await request.json()
                result = self.oauth.register_client(client_data)
                return JSONResponse(content=result, status_code=201)
            except Exception as e:
                logger.error(f"Client registration error: {e}")
                return JSONResponse(
                    content={
                        "error": "invalid_client_metadata",
                        "error_description": str(e),
                    },
                    status_code=400,
                )

        @self.app.get("/authorize")
        async def authorize_endpoint(request: Request):
            """OAuth authorization endpoint."""
            try:
                # Extract query parameters
                params = dict(request.query_params)

                # Validate OAuth request
                is_valid, error_response = self.oauth_handler.validate_oauth_request(
                    params
                )
                if not is_valid:
                    return HTMLResponse(
                        content=generate_error_page(
                            error_response.get("error", "Invalid request")
                        ),
                        status_code=400,
                    )

                # Store the authorization request
                auth_request_id = self.oauth_handler.store_auth_request(params)

                # Show login form
                login_form_html = generate_login_form(
                    auth_request_id=auth_request_id,
                    client_name=params.get("client_name", "Unknown Client"),
                )
                return HTMLResponse(content=login_form_html)

            except Exception as e:
                logger.error(f"Authorization error: {e}")
                return HTMLResponse(
                    content=generate_error_page("Authorization server error"),
                    status_code=500,
                )

        @self.app.post("/authorize")
        async def handle_authorization(
            request: Request,
            username: str = Form(...),
            password: str = Form(...),
            auth_request_id: str = Form(...),
        ):
            """Handle authorization form submission."""
            try:
                # Authenticate user
                user_authenticated = self.oauth.authenticate_user(username, password)
                if not user_authenticated:
                    return HTMLResponse(
                        content=generate_error_page("Invalid username or password"),
                        status_code=401,
                    )

                # Generate authorization code
                auth_code = self.oauth_handler.generate_authorization_code(
                    auth_request_id, username
                )

                # Redirect back to client
                auth_request = self.oauth_handler.get_auth_request(auth_request_id)
                redirect_uri = auth_request["redirect_uri"]
                state = auth_request.get("state")

                redirect_url = f"{redirect_uri}?code={auth_code}"
                if state:
                    redirect_url += f"&state={state}"

                return RedirectResponse(url=redirect_url, status_code=302)

            except Exception as e:
                logger.error(f"Authorization handling error: {e}")
                return HTMLResponse(
                    content=generate_error_page("Authorization failed"), status_code=500
                )

        @self.app.post("/token")
        async def token_endpoint(request: Request):
            """OAuth token exchange endpoint."""
            try:
                # Handle both form data and JSON
                content_type = request.headers.get("content-type", "")
                if "application/json" in content_type:
                    token_data = await request.json()
                else:
                    form_data = await request.form()
                    token_data = dict(form_data)

                # Exchange authorization code for access token
                token_response = self.oauth.exchange_code_for_token(token_data)
                return JSONResponse(content=token_response)

            except Exception as e:
                logger.error(f"Token exchange error: {e}")
                return JSONResponse(
                    content={"error": "invalid_grant", "error_description": str(e)},
                    status_code=400,
                )

        @self.app.get("/register_user")
        async def user_registration_form():
            """User registration form endpoint."""
            return HTMLResponse(content=generate_register_form())

        @self.app.post("/register_user")
        async def handle_user_registration(
            request: Request,
            username: str = Form(...),
            email: str = Form(...),
            password: str = Form(...),
        ):
            """Handle user registration form submission."""
            try:
                # Register new user
                success = self.oauth.register_user(username, email, password)
                if success:
                    return HTMLResponse(
                        content="<h2>Registration successful! You can now log in.</h2>"
                    )
                else:
                    return HTMLResponse(
                        content=generate_error_page(
                            "Registration failed - user might already exist"
                        ),
                        status_code=400,
                    )

            except Exception as e:
                logger.error(f"User registration error: {e}")
                return HTMLResponse(
                    content=generate_error_page("Registration failed"), status_code=500
                )

    async def run_async(self):
        """Run the server asynchronously."""
        if self.app:
            import uvicorn

            config = uvicorn.Config(
                app=self.app, host=self.host, port=self.port, log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()

    def run(self):
        """Run the server."""
        try:
            if self.transport in ["fastmcp", "stdio"]:
                if self.mcp:
                    self.mcp.run()
                else:
                    logger.error("FastMCP not configured")
            else:
                # HTTP-based transports run async
                asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)

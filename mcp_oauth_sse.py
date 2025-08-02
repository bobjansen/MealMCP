"""
MCP Server with OAuth 2.1 and HTTP/SSE Transport
Provides OAuth authentication with Server-Sent Events for MCP tools
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
    INVALID_REQUEST,
    INTERNAL_ERROR,
    Implementation,
    ServerCapabilities,
    InitializeRequest,
    InitializeResult,
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

# Create FastAPI app
app = FastAPI(title="MealMCP OAuth/SSE Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OAuth server with public URL and PostgreSQL support
public_url = os.getenv("MCP_PUBLIC_URL", "http://localhost:8000")
use_postgresql = os.getenv("PANTRY_BACKEND", "sqlite").lower() == "postgresql"
oauth = OAuthServer(base_url=public_url, use_postgresql=use_postgresql)

# Create context manager for user handling
context = MCPContext()

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)

# MCP Server instance
mcp_server = Server("RecipeManager")

# Store active sessions
active_sessions: Dict[str, ServerSession] = {}


def get_current_user_id(authorization: str = Header(None)) -> Optional[str]:
    """Extract user ID from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]  # Remove "Bearer " prefix
    token_data = oauth.validate_access_token(token)
    if not token_data:
        return None

    return token_data["user_id"]


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


# Include OAuth endpoints from the other server
from mcp_server_oauth import (
    oauth_authorization_server_metadata,
    oauth_protected_resource_metadata,
    register_client,
    authorize,
    authorize_post,
    register_user_form,
    register_user_post,
    token_endpoint,
)

# Register OAuth routes
app.get("/.well-known/oauth-authorization-server")(oauth_authorization_server_metadata)
app.get("/.well-known/oauth-protected-resource")(oauth_protected_resource_metadata)
app.post("/register")(register_client)
app.get("/authorize")(authorize)
app.post("/authorize")(authorize_post)
app.get("/register_user")(register_user_form)
app.post("/register_user")(register_user_post)
app.post("/token")(token_endpoint)


# MCP Tool Implementations
async def handle_list_units() -> Dict[str, Any]:
    """List all units of measurement (no auth required)."""
    return {"units": UNITS}


async def handle_add_recipe(
    name: str,
    instructions: str,
    time_minutes: int,
    ingredients: List[Dict[str, Any]],
    user_id: str,
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


async def handle_get_all_recipes(user_id: str) -> Dict[str, Any]:
    """Get all recipes."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    recipes = pantry.get_all_recipes()
    return {"status": "success", "recipes": recipes}


async def handle_get_recipe(recipe_name: str, user_id: str) -> Dict[str, Any]:
    """Get details for a specific recipe."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    recipe = pantry.get_recipe(recipe_name)

    if recipe:
        return {"status": "success", "recipe": recipe}
    else:
        return {
            "status": "error",
            "message": t("Recipe '{name}' not found").format(name=recipe_name),
        }


async def handle_get_pantry_contents(user_id: str) -> Dict[str, Any]:
    """Get the current contents of the pantry."""
    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    user_id, pantry = get_user_pantry_oauth(user_id)
    if not pantry:
        return {"status": "error", "message": "Failed to get user pantry"}

    contents = pantry.get_pantry_contents()
    return {"status": "success", "contents": contents}


async def handle_add_pantry_item(
    item_name: str, quantity: float, unit: str, notes: str, user_id: str
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


# Define MCP tools
TOOLS = [
    Tool(
        name="list_units",
        description="List all units of measurement",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="add_recipe",
        description="Add a new recipe to the database",
        inputSchema={
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
    ),
    Tool(
        name="get_all_recipes",
        description="Get all recipes",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_recipe",
        description="Get details for a specific recipe",
        inputSchema={
            "type": "object",
            "properties": {
                "recipe_name": {
                    "type": "string",
                    "description": "Name of the recipe to retrieve",
                }
            },
            "required": ["recipe_name"],
        },
    ),
    Tool(
        name="get_pantry_contents",
        description="Get the current contents of the pantry",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="add_pantry_item",
        description="Add an item to the pantry",
        inputSchema={
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
    ),
]


class MCPSession:
    """MCP Session with OAuth authentication."""

    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id

    async def handle_list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """Handle list tools request."""
        return ListToolsResult(tools=TOOLS)

    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle call tool request."""
        try:
            tool_name = request.params.name
            arguments = request.params.arguments or {}

            # Route to appropriate handler
            if tool_name == "list_units":
                result = await handle_list_units()
            elif tool_name == "add_recipe":
                result = await handle_add_recipe(
                    name=arguments["name"],
                    instructions=arguments["instructions"],
                    time_minutes=arguments["time_minutes"],
                    ingredients=arguments["ingredients"],
                    user_id=self.user_id,
                )
            elif tool_name == "get_all_recipes":
                result = await handle_get_all_recipes(self.user_id)
            elif tool_name == "get_recipe":
                result = await handle_get_recipe(
                    recipe_name=arguments["recipe_name"], user_id=self.user_id
                )
            elif tool_name == "get_pantry_contents":
                result = await handle_get_pantry_contents(self.user_id)
            elif tool_name == "add_pantry_item":
                result = await handle_add_pantry_item(
                    item_name=arguments["item_name"],
                    quantity=arguments["quantity"],
                    unit=arguments["unit"],
                    notes=arguments.get("notes"),
                    user_id=self.user_id,
                )
            else:
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=f"Unknown tool: {tool_name}")
                    ],
                    isError=True,
                )

            # Format result
            if isinstance(result, dict) and result.get("status") == "error":
                return CallToolResult(
                    content=[TextContent(type="text", text=result["message"])],
                    isError=True,
                )
            else:
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )


# SSE endpoint for MCP
@app.get("/sse")
async def sse_endpoint(request: Request, user_id: str = Depends(get_current_user_id)):
    """Server-Sent Events endpoint for MCP communication."""

    async def event_generator() -> AsyncGenerator[str, None]:
        session = MCPSession(user_id)
        session_id = f"session_{len(active_sessions)}"
        active_sessions[session_id] = session

        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"

            # Keep connection alive and handle messages
            while True:
                # In a real implementation, you'd handle incoming messages
                # For now, just keep the connection alive
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping', 'timestamp': str(date.today())})}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for session {session_id}")
        finally:
            if session_id in active_sessions:
                del active_sessions[session_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


# Standard MCP HTTP endpoints
@app.post("/mcp/list_tools")
async def mcp_list_tools(request: Request, user_id: str = Depends(get_current_user_id)):
    """MCP list tools endpoint."""
    session = MCPSession(user_id)
    try:
        data = await request.json()
        mcp_request = ListToolsRequest(**data)
        result = await session.handle_list_tools(mcp_request)
        return result.model_dump()
    except Exception as e:
        logger.error(f"List tools error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/mcp/call_tool")
async def mcp_call_tool(request: Request, user_id: str = Depends(get_current_user_id)):
    """MCP call tool endpoint."""
    session = MCPSession(user_id)
    try:
        data = await request.json()
        mcp_request = CallToolRequest(**data)
        result = await session.handle_call_tool(mcp_request)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Call tool error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Protected endpoint that requires authentication
@app.get("/protected")
async def protected_endpoint(user_id: str = Depends(get_current_user_id)):
    """Example protected endpoint."""
    if not user_id:
        # Return 401 with WWW-Authenticate header to trigger OAuth flow
        return JSONResponse(
            content={"error": "unauthorized", "message": "Authentication required"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"message": f"Hello user {user_id}!", "user_id": user_id}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MealMCP OAuth/SSE Server"}


# Root endpoint with API info
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "MealMCP OAuth/SSE Server",
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
        "mcp_endpoints": {
            "sse": "/sse",
            "list_tools": "/mcp/list_tools",
            "call_tool": "/mcp/call_tool",
        },
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "localhost")
    port = int(os.getenv("MCP_PORT", "8000"))

    print(f"Starting MealMCP OAuth/SSE Server on {host}:{port}")
    print(
        f"OAuth Discovery: http://{host}:{port}/.well-known/oauth-authorization-server"
    )
    print(f"Authorization: http://{host}:{port}/authorize")
    print(f"Token: http://{host}:{port}/token")
    print(f"SSE Endpoint: http://{host}:{port}/sse")
    print(f"Protected Test: http://{host}:{port}/protected")

    uvicorn.run(app, host=host, port=port)

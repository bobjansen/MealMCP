#!/usr/bin/env python3
"""
Simple MCP Server without OAuth - for testing basic MCP functionality
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Simple MealMCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define tools
TOOLS = [
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
]


@app.post("/")
async def handle_mcp(request: Request):
    """Handle MCP JSON-RPC requests."""
    logger.info(f"Received MCP request from {request.client}")

    try:
        body = await request.json()
        logger.info(f"Request body: {body}")

        # Check if this is an MCP request
        if not isinstance(body, dict) or "method" not in body:
            return JSONResponse(
                status_code=400, content={"error": "Invalid JSON-RPC request"}
            )

        method = body.get("method")
        request_id = body.get("id")

        logger.info(f"MCP method: {method}, ID: {request_id}")

        if method == "initialize":
            logger.info("Handling initialize request")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "Simple MealMCP Server", "version": "1.0.0"},
                },
            }
            logger.info(f"Initialize response: {response}")
            return JSONResponse(content=response)

        elif method == "notifications/initialized":
            logger.info("Handling notifications/initialized")
            # Notifications don't need responses
            return JSONResponse(content={})

        elif method == "tools/list":
            logger.info("Handling tools/list request")
            response = {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
            logger.info(f"Returning {len(TOOLS)} tools")
            return JSONResponse(content=response)

        elif method == "tools/call":
            logger.info("Handling tools/call request")
            params = body.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            logger.info(f"Calling tool: {tool_name} with args: {arguments}")

            # Simple tool implementations
            if tool_name == "test_simple":
                result = {"message": "Test tool executed successfully!"}
            elif tool_name == "list_units":
                result = {
                    "units": ["grams", "kilograms", "liters", "cups", "tablespoons"]
                }
            elif tool_name == "add_recipe":
                result = {
                    "status": "success",
                    "message": f"Added recipe: {arguments.get('name', 'Unknown')}",
                }
            else:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}",
                        },
                    }
                )

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": str(result)}]},
            }
            return JSONResponse(content=response)

        else:
            logger.error(f"Unknown method: {method}")
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            },
        )


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "Simple MealMCP Server",
        "version": "1.0.0",
        "description": "MCP server without OAuth for testing",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "localhost")
    port = int(os.getenv("MCP_PORT", "8001"))

    print(f"Starting Simple MealMCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

#!/usr/bin/env python3
"""
Uvicorn-compatible entry point for MealMCP server.

This module creates a FastAPI app instance that can be run with uvicorn,
supporting SSL certificates and custom host/port configurations.

Usage:
    uvicorn uvicorn_app:app --host 0.0.0.0 --port 8443 --ssl-keyfile ~/key.pem --ssl-certfile ~/cert.pem
    
Environment Variables:
    MCP_TRANSPORT - Transport mode (http, oauth, sse)
    PANTRY_DATABASE_URL - PostgreSQL connection string
    PANTRY_BACKEND - Database backend (postgresql, sqlite)
"""

import os
from recipe_mcp_server import RecipeMCPServer

# Set default transport to HTTP for uvicorn usage
if "MCP_TRANSPORT" not in os.environ:
    os.environ["MCP_TRANSPORT"] = "http"

# Set default backend to postgresql if database URL is provided
if "PANTRY_DATABASE_URL" in os.environ and "PANTRY_BACKEND" not in os.environ:
    os.environ["PANTRY_BACKEND"] = "postgresql"

# Create the server instance
server = RecipeMCPServer()

# Expose the FastAPI app for uvicorn
app = server.app

if __name__ == "__main__":
    # This allows direct execution with python, but uvicorn is recommended
    import uvicorn

    uvicorn.run("uvicorn_app:app", host="0.0.0.0", port=8000, reload=False)

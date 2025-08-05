#!/usr/bin/env python3
"""
MCP Server Launcher - Unified interface for all MCP server modes.

Usage:
    python run_mcp.py [mode] [options]

Modes:
    fastmcp     - FastMCP server (stdio) - default
    http        - HTTP REST API server
    oauth       - OAuth 2.1 authenticated server
    sse         - Server-Sent Events server

Options:
    --host HOST     - Server host (default: localhost)
    --port PORT     - Server port (default: 8000)
    --local         - Local mode (no authentication)
    --remote        - Remote mode (token authentication)
    --multiuser     - Multi-user mode (OAuth required)

Examples:
    python run_mcp.py                          # FastMCP local mode
    python run_mcp.py http --port 8080         # HTTP server on port 8080
    python run_mcp.py oauth --multiuser        # OAuth multi-user server
    python run_mcp.py sse --remote             # SSE with token auth
"""

import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="MealMCP Unified Server Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "transport",
        nargs="?",
        default="fastmcp",
        choices=["fastmcp", "http", "oauth", "sse"],
        help="Transport mode (default: fastmcp)",
    )

    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")

    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument("--local", action="store_true", help="Local mode (no auth)")
    auth_group.add_argument(
        "--remote", action="store_true", help="Remote mode (token auth)"
    )
    auth_group.add_argument(
        "--multiuser", action="store_true", help="Multi-user mode (OAuth)"
    )

    parser.add_argument(
        "--backend", choices=["sqlite", "postgresql"], help="Database backend"
    )
    parser.add_argument("--db-url", help="Database connection URL")

    args = parser.parse_args()

    # Set environment variables based on arguments
    os.environ["MCP_TRANSPORT"] = args.transport
    os.environ["MCP_HOST"] = args.host
    os.environ["MCP_PORT"] = str(args.port)

    # Set auth mode
    if args.local:
        os.environ["MCP_MODE"] = "local"
    elif args.remote:
        os.environ["MCP_MODE"] = "remote"
    elif args.multiuser:
        os.environ["MCP_MODE"] = "multiuser"
        if args.transport != "oauth":
            print(
                "Warning: Multi-user mode requires OAuth transport, switching to OAuth"
            )
            os.environ["MCP_TRANSPORT"] = "oauth"

    # Set database options
    if args.backend:
        os.environ["PANTRY_BACKEND"] = args.backend
    if args.db_url:
        os.environ["PANTRY_DATABASE_URL"] = args.db_url

    # Import after environment is set
    from mcp_server_unified import UnifiedMCPServer

    # Create and run server
    print(f"Starting MealMCP server:")
    print(f"  Transport: {args.transport}")
    print(f"  Auth Mode: {os.environ.get('MCP_MODE', 'local')}")
    print(f"  Address: {args.host}:{args.port}")
    print(f"  Backend: {os.environ.get('PANTRY_BACKEND', 'sqlite')}")
    print()

    try:
        server = UnifiedMCPServer()
        server.run()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

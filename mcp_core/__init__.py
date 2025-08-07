"""
MCP Core - Generic Model Context Protocol implementation.

A standalone, reusable package for building MCP servers with multiple transport modes,
authentication systems, and user management capabilities.
"""

from .server.unified_server import UnifiedMCPServer
from .server.context import MCPContext
from .auth.user_manager import UserManager

__version__ = "1.0.0"

__all__ = ["UnifiedMCPServer", "MCPContext", "UserManager"]

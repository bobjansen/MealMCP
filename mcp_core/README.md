# MCPnp - Model Context Protocol, no problem

A generic, reusable framework for building MCP (Model Context Protocol) servers with multiple transport modes, authentication systems, and user management capabilities.

## Features

- **Multiple Transport Modes**: FastMCP (local), HTTP REST API, OAuth 2.1, Server-Sent Events
- **Authentication Systems**: Token-based auth, OAuth 2.1 with multi-user support
- **User Management**: Built-in user session handling and database isolation
- **Extensible Architecture**: Easy to integrate with any backend data source
- **Production Ready**: Includes error handling, logging, and monitoring

## Quick Start

```python
from mcpnp import UnifiedMCPServer, MCPContext

# Create an MCP server instance
server = UnifiedMCPServer()

# Define your tools
@server.tool("my_tool")
def my_tool(param: str) -> str:
    return f"Hello {param}"

# Start the server
server.run()
```

## Transport Modes

### Local Mode (FastMCP)
Perfect for Claude Desktop integration:
```python
server.run(mode="local")
```

### HTTP REST API
For web applications and API integration:
```python
server.run(mode="http", port=8080)
```

### OAuth Multi-User
For applications requiring user authentication:
```python
server.run(mode="oauth", multiuser=True)
```

## Installation

```bash
pip install mcpnp
```

## Documentation

See the main documentation for detailed setup instructions and examples.

## License

AGPL-3.0-or-later
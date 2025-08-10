# MCP Server Error Logging

The MCP server now includes comprehensive error logging with full tracebacks to help with debugging and monitoring.

## Configuration

### Environment Variables

- `MCP_LOG_DIR`: Directory where log files are stored (default: `logs`)
- `MCP_ERROR_LOG`: Name of the error log file (default: `mcp_errors.log`)

### Example Configuration

```bash
export MCP_LOG_DIR="/var/log/mcp"
export MCP_ERROR_LOG="errors.log"
```

## Log File Location

By default, error logs are written to:
- **File**: `logs/mcp_errors.log` (relative to server working directory)
- **Console**: Errors also appear in console output with INFO level and above

## Log Format

The log file includes detailed information for each error:

```
2025-08-10 20:47:54 - mcp_core.server.unified_server - ERROR - Error in MCP request handling: division by zero

Full traceback:
Traceback (most recent call last):
  File "/home/user/MealMCP/mcp_core/server/unified_server.py", line 123, in handle_request
    result = 1 / 0
             ~~^~~
ZeroDivisionError: division by zero

/home/user/MealMCP/mcp_core/server/unified_server.py:75 in log_error_with_traceback()
```

## Error Categories

The logging system captures errors from different parts of the MCP server:

### 1. Server-Level Errors
- **Context**: Server startup/runtime, MCP request handling, OAuth operations
- **Function**: `log_error_with_traceback(error, context)`
- **Examples**:
  - MCP request parsing errors
  - OAuth token exchange failures
  - Server startup issues

### 2. Tool-Level Errors  
- **Context**: Individual MCP tool execution
- **Function**: `log_tool_error(error, tool_name, context)`
- **Examples**:
  - Recipe addition failures
  - Pantry management errors
  - Database connection issues

## Monitored Error Points

### Server Operations
- MCP request handling
- OAuth client registration
- OAuth authorization flows
- OAuth token exchange
- User registration
- Server-Sent Events (SSE)
- Server startup and runtime

### Tool Operations
- All MCP tool executions (recipe management, pantry operations, etc.)
- Database operations within tools
- Parameter validation errors
- Business logic failures

## Example Usage

### In Application Code

```python
from mcp_core.server.unified_server import log_error_with_traceback

try:
    # Some risky operation
    result = perform_complex_operation()
except Exception as e:
    log_error_with_traceback(e, "complex operation")
    return error_response
```

### In Tool Development

```python  
from mcp_tool_router import log_tool_error

def my_custom_tool(arguments, pantry_manager):
    try:
        # Tool implementation
        return {"status": "success", "data": result}
    except Exception as e:
        log_tool_error(e, "my_custom_tool", "during data processing")
        return {"status": "error", "message": str(e)}
```

## Log Rotation

For production deployments, consider setting up log rotation to prevent log files from growing too large:

```bash
# Example logrotate configuration
/var/log/mcp/mcp_errors.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 mcp mcp
}
```

## Debugging Tips

1. **Check Recent Errors**: Use `tail -f logs/mcp_errors.log` to monitor errors in real-time
2. **Search by Context**: Use `grep "context_name" logs/mcp_errors.log` to find specific error types
3. **Full Stack Traces**: Every error includes the complete call stack for easier debugging
4. **Timestamps**: All errors include precise timestamps for correlation with other logs

## Security Considerations

- Log files may contain sensitive information from error contexts
- Ensure log files have appropriate permissions (e.g., 644 or more restrictive)
- Consider log file encryption for sensitive deployments
- Regularly rotate and archive old log files
- Monitor log file sizes to prevent disk space issues

## Testing Error Logging

Run the test script to verify error logging is working:

```bash
uv run python test_error_logging.py
```

This will generate sample errors and show how they appear in the log file.
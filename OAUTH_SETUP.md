# OAuth Setup for Claude Desktop

## Quick Start

### 1. Start OAuth Server

For local testing:
```bash
MCP_MODE=oauth MCP_TRANSPORT=http uv run start_server.py
```

For production with reverse proxy (like your setup):
```bash
MCP_PUBLIC_URL=https://mcp.bobjansen.net MCP_MODE=oauth MCP_TRANSPORT=http uv run start_server.py
```

The server will start with OAuth endpoints using your public URL:
- Authorization: `https://mcp.bobjansen.net/authorize`
- Token: `https://mcp.bobjansen.net/token`
- Discovery: `https://mcp.bobjansen.net/.well-known/oauth-authorization-server`

### 2. Configure Claude Desktop

Add this to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "meal-planner": {
      "command": "http",
      "args": ["https://mcp.bobjansen.net"],
      "env": {}
    }
  }
}
```

For local testing, use:
```json
{
  "mcpServers": {
    "meal-planner": {
      "command": "http",
      "args": ["http://localhost:8000"],
      "env": {}
    }
  }
}
```

### 3. Authentication Flow

Claude Desktop uses its own OAuth proxy system. Here's the actual flow:

1. **Initial Request**: Claude attempts to call MCP tools
2. **401 Response**: Server responds with `401 Unauthorized` and `WWW-Authenticate: Bearer` header
3. **OAuth Discovery**: Claude fetches `/.well-known/oauth-authorization-server`
4. **Dynamic Client Registration**: Claude automatically registers as OAuth client via `/register`
5. **Claude Proxy**: Claude opens `https://claude.ai/api/organizations/.../mcp/start-auth/...`
6. **Proxy to Your Server**: Claude's proxy redirects to your server's `/authorize` endpoint
7. **User Login**: You log in or register at `https://mcp.bobjansen.net/authorize`
8. **Authorization Code**: Server redirects back to Claude's proxy with auth code
9. **Token Exchange**: Claude exchanges code for access token using PKCE
10. **Authenticated Access**: Claude uses Bearer token for all subsequent requests

**Important**: The redirect URLs you see like `https://claude.ai/api/organizations/...` are Claude's OAuth proxy system, not an error!

### 4. User Registration

First-time users can register at the authorization endpoint:
- Visit authorization URL
- Click "Register here" link
- Create username/password
- Complete OAuth flow

### 5. Multi-User Support

Each user gets:
- Separate SQLite database in `user_data/{user_id}/pantry.db`
- Isolated recipes, pantry contents, and preferences
- Secure token-based authentication
- OAuth 2.1 with PKCE security

## OAuth Endpoints

### Discovery Metadata
- **Authorization Server**: `/.well-known/oauth-authorization-server`
- **Protected Resource**: `/.well-known/oauth-protected-resource`

### Authentication Endpoints
- **Authorization**: `/authorize` (GET/POST)
- **Token**: `/token` (POST)
- **Registration**: `/register` (POST)
- **User Registration**: `/register_user` (GET/POST)

### MCP Endpoints
- **List Tools**: `/mcp/list_tools` (POST)
- **Call Tool**: `/mcp/call_tool` (POST)
- **SSE Stream**: `/sse` (GET)

## Security Features

### OAuth 2.1 Compliance
- **PKCE Required**: All authorization flows use Proof Key for Code Exchange
- **Secure Tokens**: Cryptographically secure token generation
- **Token Expiration**: Access tokens expire in 1 hour
- **Refresh Tokens**: Long-lived refresh tokens for seamless re-authentication

### Authorization Scopes
- `read`: Read-only access to recipes and pantry
- `write`: Full read/write access
- `admin`: Administrative access (not currently used)

### Security Headers
- **CORS**: Configurable cross-origin resource sharing
- **Bearer Tokens**: Standard HTTP Authorization header
- **HTTPS Ready**: Secure transport support

## Troubleshooting

### Common Issues

**Server Won't Start**
```bash
# Check if port is in use
lsof -i :8000

# Use different port
MCP_PORT=8001 MCP_MODE=oauth MCP_TRANSPORT=http uv run start_server.py
```

**Authentication Fails**
- Check OAuth discovery endpoints are accessible
- Verify CORS settings if using different domains
- Ensure authorization endpoint redirects work

**Claude Desktop Won't Connect**
- Verify HTTP transport is configured correctly
- Check server logs for errors
- Test endpoints manually with curl:

```bash
# Test discovery
curl http://localhost:8000/.well-known/oauth-authorization-server

# Test protected endpoint (should return 401)
curl http://localhost:8000/protected
```

### Manual Testing

Test OAuth flow manually:

```bash
# 1. Register a client
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Test Client", "redirect_uris": ["http://localhost:3000/callback"]}'

# 2. Start authorization (in browser)
# http://localhost:8000/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=http://localhost:3000/callback&scope=read+write&code_challenge=CHALLENGE&code_challenge_method=S256

# 3. Exchange code for token
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=AUTH_CODE&redirect_uri=http://localhost:3000/callback&client_id=CLIENT_ID&code_verifier=VERIFIER"

# 4. Use access token
curl http://localhost:8000/mcp/list_tools \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Advanced Configuration

### Environment Variables

```bash
# Server configuration
MCP_HOST=0.0.0.0          # Bind to all interfaces
MCP_PORT=8000             # Server port
MCP_MODE=oauth            # OAuth authentication mode
MCP_TRANSPORT=http        # HTTP transport

# CORS configuration
CORS_ORIGINS=https://claude.ai,https://app.claude.ai
```

### Production Deployment

For production use:

1. **HTTPS**: Use reverse proxy (nginx, Apache) for HTTPS termination
2. **Database**: Consider PostgreSQL for shared user database
3. **Secrets**: Use secure secret storage for tokens
4. **Monitoring**: Add logging and metrics
5. **Rate Limiting**: Implement rate limiting for OAuth endpoints

### Custom OAuth Provider

To use external OAuth provider:

1. Modify `oauth_server.py` to integrate with your provider
2. Implement token validation against external service
3. Map external user IDs to internal user system
4. Update discovery metadata accordingly

## Architecture

```
Claude Desktop
    ↓ HTTP Request (401 Unauthorized)
    ↓ OAuth Discovery
    ↓ Browser Authorization
OAuth Server (FastAPI)
    ↓ User Authentication
    ↓ Token Generation
    ↓ MCP Tool Calls
PantryManager (per-user SQLite)
```

The OAuth implementation provides enterprise-grade security while maintaining the simplicity of the existing MCP architecture.
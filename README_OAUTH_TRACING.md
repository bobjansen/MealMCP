# OAuth Sequence Tracing and Debugging

This directory contains tools for tracing and debugging the OAuth 2.1 PKCE authentication flow used by the MCP server. These tools are essential for understanding how Claude Desktop authenticates with the server and for debugging authentication issues.

## Overview

The OAuth tracing system consists of three main components:

1. **`oauth_sequence_tracer.py`** - Main tracing script that simulates the complete OAuth flow
2. **`setup_oauth_test_user.py`** - Helper script to register test users
3. **Generated trace files** - JSON logs of complete request/response sequences

## Quick Start

### 1. Start the OAuth MCP Server

First, ensure your MCP server is running in OAuth mode:

```bash
# Set environment variables
export PANTRY_BACKEND=postgresql
export PANTRY_DATABASE_URL=postgresql://brj:meal_pw@localhost:5432/meal_manager
export MCP_PUBLIC_URL=https://mcp.bobjansen.net  # or http://localhost:8000 for local
export MCP_MODE=oauth
export MCP_TRANSPORT=http

# Start the server
uv run run_mcp.py oauth
```

### 2. Setup a Test User

```bash
# Create a test user for authentication
python setup_oauth_test_user.py --username testuser --password testpass --email test@example.com
```

### 3. Run the OAuth Sequence Trace

```bash
# Trace the complete OAuth flow
python oauth_sequence_tracer.py --username testuser --password testpass
```

## Detailed Usage

### OAuth Sequence Tracer

The main tracing script simulates exactly what Claude Desktop does when connecting to an MCP server:

```bash
# Basic usage with default settings
python oauth_sequence_tracer.py

# Custom server and credentials
python oauth_sequence_tracer.py \
    --server-url http://localhost:8000 \
    --username myuser \
    --password mypass

# Save trace to specific file
python oauth_sequence_tracer.py --save-trace my_oauth_trace.json

# Quiet mode (less verbose output)
python oauth_sequence_tracer.py --quiet
```

#### Environment Variables

You can also configure the tracer using environment variables:

```bash
export OAUTH_SERVER_URL=http://localhost:8000
export OAUTH_TEST_USERNAME=testuser
export OAUTH_TEST_PASSWORD=testpass
export OAUTH_CLIENT_NAME="Claude Desktop"

python oauth_sequence_tracer.py
```

### Test User Setup

The setup script helps create test users for authentication:

```bash
# Web form registration (default)
python setup_oauth_test_user.py --username testuser --password testpass

# Direct database registration
python setup_oauth_test_user.py --database-direct --username dbuser --password dbpass

# Check if user exists
python setup_oauth_test_user.py --check-only --username testuser

# Custom server
python setup_oauth_test_user.py --server-url https://mcp.bobjansen.net --username remoteuser
```

## OAuth Flow Steps

The tracer simulates these exact steps that Claude Desktop performs:

### Step 1: OAuth Discovery
- **GET** `/.well-known/oauth-authorization-server`
- Discovers OAuth endpoints and capabilities

### Step 2: Client Registration  
- **POST** `/register`
- Registers Claude Desktop as an OAuth client
- Receives `client_id` and optional `client_secret`

### Step 3: Authorization Request
- **GET** `/authorize` with PKCE parameters
- Receives HTML login form

### Step 4: User Authentication
- **POST** `/authorize` with credentials
- Submits login form and receives authorization code

### Step 5: Token Exchange
- **POST** `/token` with authorization code
- Exchanges code for access token using PKCE verification

### Step 6: Authenticated API Request
- **POST** `/` with Bearer token
- Tests MCP request with access token

### Step 7: Token Refresh (Optional)
- **POST** `/token` with refresh token
- Tests token refresh if refresh token provided

## Trace Output

The tracer provides detailed logging of each step:

```
🚀 Starting OAuth 2.1 PKCE sequence trace...
============================================================
🔍 STEP 1: Discovering OAuth endpoints...
➡️  GET http://localhost:8000/.well-known/oauth-authorization-server
✅ 200 OK
    JSON Response: {
      "issuer": "http://localhost:8000",
      "authorization_endpoint": "http://localhost:8000/authorize",
      "token_endpoint": "http://localhost:8000/token",
      ...
    }
```

## Trace Files

Each run generates a comprehensive JSON trace file with:

- **Metadata**: Server URL, username, timestamp, request count
- **Sequence Summary**: Success/failure of each major step  
- **Complete Trace Log**: Every HTTP request and response

### Trace File Structure

```json
{
  "metadata": {
    "server_url": "http://localhost:8000",
    "username": "testuser",
    "timestamp": "2025-01-15T10:30:00",
    "total_requests": 7
  },
  "sequence_summary": {
    "client_id": "client_123",
    "auth_code_received": true,
    "access_token_received": true,
    "refresh_token_received": true
  },
  "trace_log": [
    {
      "timestamp": "2025-01-15T10:30:01",
      "type": "request",
      "method": "GET",
      "url": "http://localhost:8000/.well-known/oauth-authorization-server",
      "headers": {},
      "params": null,
      "data": null,
      "json": null
    },
    {
      "timestamp": "2025-01-15T10:30:02", 
      "type": "response",
      "status_code": 200,
      "headers": {"content-type": "application/json"},
      "json": {...},
      "text": "..."
    }
  ]
}
```

## Debugging Common Issues

### Connection Refused
```
❌ Could not connect to server at http://localhost:8000
```
**Solution**: Ensure MCP server is running and accessible

### Registration Failed
```
❌ Registration failed: 400
   Response: Registration failed - user might already exist
```
**Solution**: User already exists or try database registration:
```bash
python setup_oauth_test_user.py --database-direct
```

### Authorization Failed
```
❌ Authorization failed: invalid_request - Invalid client_id
```
**Solution**: Client registration failed, check server logs

### Token Exchange Failed
```
❌ Token exchange failed: 400
```
**Solution**: PKCE verification failed, check code_verifier/code_challenge

### MCP Request Failed
```
❌ Authenticated MCP request failed: 401
```
**Solution**: Access token invalid or expired

## Integration with Claude Desktop

The traced OAuth flow exactly matches what Claude Desktop performs:

1. **Same endpoints**: Uses identical OAuth 2.1 endpoints
2. **Same parameters**: PKCE, same redirect URIs, same scopes  
3. **Same client registration**: Registers as "Claude Desktop"
4. **Same request format**: JSON-RPC over HTTP with Bearer tokens

This makes the trace files invaluable for:
- Debugging Claude Desktop connection issues
- Understanding the expected request/response flow
- Verifying server OAuth implementation
- Testing authentication before Claude Desktop integration

## Archive and Documentation

The trace files serve as:
- **Historical record** of OAuth flows
- **Debugging reference** for future issues  
- **Documentation** of exact request/response patterns
- **Test data** for automated testing

Keep trace files organized by date and server configuration:
```
traces/
├── oauth_trace_20250115_103000.json  # Local server
├── oauth_trace_20250115_110000.json  # Remote server  
└── oauth_trace_20250116_090000.json  # After config change
```
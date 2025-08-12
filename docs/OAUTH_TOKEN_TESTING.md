# OAuth Token Refresh Testing Guide

This document provides testing procedures for the OAuth refresh token persistence fix that resolves "Invalid refresh token" errors after server restarts.

## Background

The OAuth system previously had an issue where refresh tokens would expire and become invalid after server restarts, requiring users to re-authenticate. This has been fixed by adding proper expiry timestamps to refresh tokens and ensuring they persist correctly across server restarts.

## Testing Procedures

### 1. Staged Testing Approach

Start your MCP server in OAuth mode and monitor for token-related activities:

```bash
# Start your MCP server in OAuth mode
uv run run_mcp.py oauth --multiuser

# Monitor the logs for token refresh attempts
tail -f logs/mcp_server.log | grep -i "refresh\|token\|oauth"
```

### 2. Force Token Refresh Test

Test refresh token persistence by forcing a server restart during an active Claude Desktop session:

1. **Connect Claude Desktop** to your MCP server
2. **Use it for a few interactions** (to establish tokens)
3. **Restart your MCP server**: `Ctrl+C` then restart with `uv run run_mcp.py oauth --multiuser`
4. **Try using Claude Desktop again** - it should automatically refresh tokens without requiring re-authentication

**Expected Result**: Claude Desktop continues working seamlessly without showing authentication prompts.

### 3. Manual Token Inspection

Check that refresh tokens now have proper expiry timestamps:

#### For SQLite Backend:
```bash
sqlite3 oauth.db "SELECT token_type, expires_at, datetime(expires_at, 'unixepoch') as expires_at_readable FROM oauth_tokens WHERE token_type='refresh';"
```

#### For PostgreSQL Backend:
```bash
psql $PANTRY_DATABASE_URL -c "SELECT token_type, expires_at, to_timestamp(expires_at) as expires_at_readable FROM oauth_tokens WHERE token_type='refresh';"
```

**Expected Result**: Refresh tokens should have `expires_at` values that are 24x longer than access tokens (typically 24 days vs 1 day).

### 4. Extended Expiry Testing

Set longer token expiry for easier testing:

```bash
# Set tokens to last 48 hours (172800 seconds)
export OAUTH_TOKEN_EXPIRY=172800

# Start server
uv run run_mcp.py oauth --multiuser
```

This gives you more time to test restart scenarios without worrying about normal token expiry.

### 5. Log Analysis

Monitor your logs for these indicators:

#### ❌ Bad Signs (should NOT appear anymore):
- `"Invalid refresh token"`
- `"Error in OAuth token exchange: Invalid refresh token"`
- `"Traceback (most recent call last):" followed by refresh token errors`

#### ✅ Good Signs (should appear):
- `"Token refresh successful"`
- `"Tokens loaded from database on startup"`
- `"OAuth token exchange successful"`

### 6. Production Monitoring Script

Create a monitoring script to check token health:

```bash
#!/bin/bash
# monitor_tokens.sh
echo "=== OAuth Token Health Check ==="
echo "Refresh tokens in database:"

if [ "$PANTRY_BACKEND" = "postgresql" ]; then
    psql $PANTRY_DATABASE_URL -c "
    SELECT 
        token_type, 
        COUNT(*) as count,
        MIN(to_timestamp(expires_at)) as earliest_expiry,
        MAX(to_timestamp(expires_at)) as latest_expiry
    FROM oauth_tokens 
    WHERE expires_at > extract(epoch from now())
    GROUP BY token_type;"
else
    sqlite3 oauth.db "
    SELECT 
        token_type, 
        COUNT(*) as count,
        datetime(MIN(expires_at), 'unixepoch') as earliest_expiry,
        datetime(MAX(expires_at), 'unixepoch') as latest_expiry
    FROM oauth_tokens 
    WHERE expires_at > strftime('%s', 'now')
    GROUP BY token_type;"
fi
```

Make it executable and run periodically:
```bash
chmod +x monitor_tokens.sh
./monitor_tokens.sh
```

### 7. Gradual Rollout Strategy

If you have multiple users:

1. **Test with your own Claude Desktop first**
2. **Have 1-2 beta users test** the server restart scenario
3. **Monitor for any "Invalid refresh token" errors** in logs
4. **Full rollout** once confident the fix is working

## Success Criteria

The fix is working correctly when:

✅ **No "Invalid refresh token" errors** appear in logs after server restarts
✅ **Claude Desktop continues working seamlessly** without requiring re-authentication
✅ **Refresh tokens have proper expiry timestamps** (24x longer than access tokens)
✅ **Tokens are successfully loaded** from database on server startup
✅ **Token refresh operations succeed** automatically

## Troubleshooting

### If you still see "Invalid refresh token" errors:

1. **Check token expiry settings**:
   ```bash
   echo "Current token expiry: ${OAUTH_TOKEN_EXPIRY:-86400} seconds"
   ```

2. **Verify database tables exist**:
   ```bash
   # SQLite
   sqlite3 oauth.db ".tables"
   
   # PostgreSQL  
   psql $PANTRY_DATABASE_URL -c "\dt"
   ```

3. **Check token data structure**:
   ```bash
   # SQLite
   sqlite3 oauth.db "SELECT * FROM oauth_tokens LIMIT 2;"
   
   # PostgreSQL
   psql $PANTRY_DATABASE_URL -c "SELECT * FROM oauth_tokens LIMIT 2;"
   ```

### If Claude Desktop prompts for re-authentication unexpectedly:

1. **Check if tokens are expiring normally** (not an error if they're genuinely expired)
2. **Verify server logs** for any database connection issues
3. **Ensure proper environment variables** are set (`PANTRY_BACKEND`, `PANTRY_DATABASE_URL`, etc.)

## Environment Variables

Key environment variables for OAuth token management:

- `OAUTH_TOKEN_EXPIRY`: Access token lifetime in seconds (default: 86400 = 24 hours)
- `PANTRY_BACKEND`: Database backend ('sqlite' or 'postgresql')
- `PANTRY_DATABASE_URL`: PostgreSQL connection string (if using PostgreSQL)

## Related Documentation

- [OAuth Setup Guide](OAUTH_SETUP.md)
- [Multi-user Setup](README_MULTIUSER.md)
- [Error Logging](ERROR_LOGGING.md)
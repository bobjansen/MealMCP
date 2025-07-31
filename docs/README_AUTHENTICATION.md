# Meal Manager Authentication System

This document explains how to use the Meal Manager's dual-mode authentication system.

## Overview

The Meal Manager supports two distinct modes:

1. **SQLite Mode** (Local): Single-user, no authentication required
2. **PostgreSQL Mode** (Multi-user): Full user accounts with isolated databases

## SQLite Mode (Default)

Perfect for personal use on your local machine.

### Features:
- ✅ No authentication required
- ✅ Single user access
- ✅ Data stored in local `pantry.db` file
- ✅ Fast and simple setup

### Usage:
```bash
# Run with default SQLite mode
python run_web.py

# Or explicitly set SQLite mode
PANTRY_BACKEND=sqlite python run_web.py
```

## PostgreSQL Mode (Multi-user)

Ideal for hosting online with multiple users.

### Features:
- ✅ User registration and login
- ✅ Password-based authentication
- ✅ Isolated databases per user
- ✅ Secure session management
- ✅ User profile management
- ✅ Password change functionality

### Setup:

1. **Install PostgreSQL** and create a main database:
   ```sql
   CREATE DATABASE meal_manager;
   CREATE USER meal_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE meal_manager TO meal_user;
   ```

2. **Set environment variables**:
   ```bash
   export PANTRY_BACKEND=postgresql
   export PANTRY_DATABASE_URL=postgresql://meal_user:secure_password@localhost:5432/meal_manager
   export FLASK_SECRET_KEY=your-secure-secret-key-here
   ```

3. **Run the application**:
   ```bash
   python run_web.py
   ```

4. **Register your first account** by visiting http://localhost:5000

### User Database Isolation

Each user gets their own PostgreSQL database:
- User `alice` → database `meal_user_alice`
- User `bob` → database `meal_user_bob`

This ensures complete data isolation between users.

## Environment Variables

| Variable | SQLite Mode | PostgreSQL Mode | Description |
|----------|-------------|-----------------|-------------|
| `PANTRY_BACKEND` | `sqlite` (default) | `postgresql` | Backend type |
| `PANTRY_DATABASE_URL` | Not used | **Required** | PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Auto-generated | **Recommended** | Flask session secret |
| `FLASK_ENV` | `development` | `development`/`production` | Flask environment |

## Security Features

### PostgreSQL Mode Security:
- ✅ Password hashing using Werkzeug's secure methods
- ✅ Session-based authentication
- ✅ SQL injection protection (parameterized queries)
- ✅ XSS protection (escaped template output)
- ✅ Database isolation per user
- ✅ Secure password requirements (8+ characters)

### SQLite Mode Security:
- ✅ SQL injection protection (parameterized queries)
- ✅ XSS protection (escaped template output)
- ⚠️ No authentication (intended for local use only)

## API Compatibility

The MCP server (`mcp_server.py`) continues to work in both modes:
- **SQLite mode**: Token-based auth for MCP (optional)
- **PostgreSQL mode**: Token-based auth for MCP (required)

## Migration Between Modes

### SQLite → PostgreSQL:
1. Export your SQLite data
2. Set up PostgreSQL mode
3. Register an account
4. Import your data to the new user database

### PostgreSQL → SQLite:
1. Export your user's PostgreSQL database
2. Switch to SQLite mode
3. Import data to `pantry.db`

## Troubleshooting

### Common Issues:

**PostgreSQL connection fails:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection manually
psql postgresql://meal_user:password@localhost:5432/meal_manager
```

**User registration fails:**
- Check database permissions
- Verify password meets requirements (8+ characters)
- Ensure username/email are unique

**Session issues:**
- Set a secure `FLASK_SECRET_KEY`
- Clear browser cookies
- Check server logs for errors

## Production Deployment

For production deployment with PostgreSQL mode:

1. **Set secure environment variables**:
   ```bash
   export FLASK_ENV=production
   export FLASK_SECRET_KEY=$(openssl rand -base64 32)
   export PANTRY_DATABASE_URL=postgresql://user:pass@host:5432/db
   ```

2. **Use a proper WSGI server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app_enhanced:app
   ```

3. **Enable HTTPS** with nginx or Apache
4. **Set up regular database backups**
5. **Monitor application logs**

## Development

To contribute to the authentication system:

1. **Test both modes**:
   ```bash
   # Test SQLite mode
   PANTRY_BACKEND=sqlite python run_web.py
   
   # Test PostgreSQL mode
   PANTRY_BACKEND=postgresql PANTRY_DATABASE_URL=... python run_web.py
   ```

2. **Run the test suite**:
   ```bash
   pytest tests/
   ```

3. **Follow security best practices**:
   - Always use parameterized queries
   - Escape template output
   - Hash passwords securely
   - Validate user input

## Support

For issues with the authentication system:
1. Check the troubleshooting section above
2. Review server logs for error messages
3. Test with a fresh database
4. Open an issue with detailed error information
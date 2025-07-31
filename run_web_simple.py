#!/usr/bin/env python3
"""
Web application launcher for Meal Manager.

This script automatically detects the backend mode and runs the appropriate web interface:
- SQLite mode: No authentication required, single user
- PostgreSQL mode: Full user authentication system with shared database

Usage:
    # SQLite mode (default)
    python run_web_simple.py
    
    # PostgreSQL mode
    PANTRY_BACKEND=postgresql PANTRY_DATABASE_URL=postgresql://user:pass@host/db python run_web_simple.py
    
Environment Variables:
    PANTRY_BACKEND: 'sqlite' or 'postgresql' (default: sqlite)
    PANTRY_DATABASE_URL: Database connection string
    FLASK_SECRET_KEY: Secret key for Flask sessions (auto-generated if not set)
    FLASK_ENV: 'development' or 'production' (default: development)
"""

import os
import sys
import secrets
from pathlib import Path


def main():
    # Set default environment variables
    backend = os.getenv("PANTRY_BACKEND", "sqlite")

    # Generate secret key if not provided
    if not os.getenv("FLASK_SECRET_KEY"):
        secret_key = secrets.token_urlsafe(32)
        os.environ["FLASK_SECRET_KEY"] = secret_key
        print(f"Generated Flask secret key: {secret_key}")

    # Set Flask environment
    if not os.getenv("FLASK_ENV"):
        os.environ["FLASK_ENV"] = "development"

    print("=" * 60)
    print("🍽️  Meal Manager Web Interface")
    print("=" * 60)

    if backend == "sqlite":
        print("📁 Backend: SQLite (Local Mode)")
        print("🔓 Authentication: Disabled")
        print("👤 Users: Single user")
        print("📊 Database: pantry.db")

        # Check if database exists
        db_path = Path("pantry.db")
        if not db_path.exists():
            print("⚠️  Database not found. Will be created automatically.")

    elif backend == "postgresql":
        print("🐘 Backend: PostgreSQL (Multi-user Mode)")
        print("🔐 Authentication: Enabled")
        print("👥 Users: Multiple users in shared database")
        print("📊 Strategy: User isolation with user_id scoping")

        db_url = os.getenv("PANTRY_DATABASE_URL")
        if not db_url:
            print(
                "❌ Error: PANTRY_DATABASE_URL environment variable required for PostgreSQL mode"
            )
            print("\nExample:")
            print(
                "export PANTRY_DATABASE_URL=postgresql://username:password@localhost:5432/meal_manager"
            )
            sys.exit(1)

        print(f"📊 Database: {db_url.split('@')[1] if '@' in db_url else 'configured'}")

        # Test database connection
        try:
            import psycopg2

            conn = psycopg2.connect(db_url)
            conn.close()
            print("✅ Database connection: OK")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("\nPlease check your PostgreSQL server and connection string.")
            sys.exit(1)

    print("=" * 60)
    print("🚀 Starting web server...")
    print("📍 URL: http://localhost:5000")

    if backend == "postgresql":
        print("👆 Visit the URL above to register your account")

    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print()

    # Import and run the Flask app
    try:
        from app_final import app

        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple script to populate the default database with sample data.
This is a convenience wrapper around populate_database.py for common usage.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from populate_database import populate_database


def main():
    """Populate the default database with sample data."""
    print("🍽️  Populating default MealMCP database...")
    print()

    success = populate_database(verbose=True)

    if success:
        print()
        print("🌟 Ready to use! Try these commands:")
        print("   • uv run run_web.py          # Start web interface")
        print("   • uv run run_mcp.py          # Start MCP server")
        print()
        print("📍 Database location: pantry.db")
        print("🌐 Web interface: http://localhost:5000")
        return 0
    else:
        print("\n❌ Failed to populate database")
        return 1


if __name__ == "__main__":
    sys.exit(main())

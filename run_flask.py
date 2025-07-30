#!/usr/bin/env python3
"""
Simple script to run the Flask version of the Meal Manager app.
"""

if __name__ == '__main__':
    print("🍽️  Starting Meal Manager (Flask version)")
    print("📱 Open http://localhost:5000 in your browser")
    print("🔄 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    from app import app
    app.run(debug=True, host='0.0.0.0', port=5000)

#!/usr/bin/env python3
"""
End-to-end scenario testing for MCP server.
Tests complete workflows like recipe management, pantry operations, etc.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_recipe_management_flow():
    """Test the complete recipe management workflow."""
    print("🍳 Testing Recipe Management Flow")
    print("=" * 40)
    
    try:
        from mcp_server import get_all_recipes, add_recipe, get_recipe, edit_recipe
        
        # Step 1: Check initial state (should be empty or existing recipes)
        print("1. Getting initial recipes...")
        initial_recipes = get_all_recipes()
        print(f"   Found {len(initial_recipes.get('recipes', []))} existing recipes")
        
        # Step 2: Add a test recipe
        print("2. Adding a test recipe...")
        test_recipe = {
            "name": "Test Pasta",
            "instructions": "1. Boil water\n2. Cook pasta\n3. Add sauce",
            "time_minutes": 15,
            "ingredients": [
                {"name": "pasta", "quantity": 100, "unit": "gram"},
                {"name": "tomato sauce", "quantity": 200, "unit": "ml"}
            ]
        }
        
        add_result = add_recipe(
            test_recipe["name"],
            test_recipe["instructions"], 
            test_recipe["time_minutes"],
            test_recipe["ingredients"]
        )
        print(f"   Add result: {json.dumps(add_result, indent=2)}")
        
        # Step 3: Verify recipe was added
        print("3. Verifying recipe was added...")
        all_recipes = get_all_recipes()
        recipe_names = [r["name"] for r in all_recipes.get("recipes", [])]
        if "Test Pasta" in recipe_names:
            print("   ✅ Recipe found in list")
        else:
            print("   ❌ Recipe not found in list")
        
        # Step 4: Get specific recipe details
        print("4. Getting specific recipe details...")
        recipe_details = get_recipe("Test Pasta")
        print(f"   Recipe details: {json.dumps(recipe_details, indent=2)}")
        
        # Step 5: Edit the recipe
        print("5. Editing the recipe...")
        updated_recipe = {
            "name": "Test Pasta",
            "instructions": "1. Boil salted water\n2. Cook pasta al dente\n3. Add sauce and mix",
            "time_minutes": 20,
            "ingredients": [
                {"name": "pasta", "quantity": 150, "unit": "gram"},
                {"name": "tomato sauce", "quantity": 250, "unit": "ml"},
                {"name": "olive oil", "quantity": 1, "unit": "tablespoon"}
            ]
        }
        
        edit_result = edit_recipe(
            updated_recipe["name"],
            updated_recipe["instructions"],
            updated_recipe["time_minutes"], 
            updated_recipe["ingredients"]
        )
        print(f"   Edit result: {json.dumps(edit_result, indent=2)}")
        
        print("✅ Recipe management flow completed!")
        
    except Exception as e:
        print(f"❌ Error in recipe management flow: {e}")

def test_pantry_management_flow():
    """Test the complete pantry management workflow."""
    print("\n🥫 Testing Pantry Management Flow")
    print("=" * 40)
    
    try:
        from mcp_server import get_pantry_contents, add_pantry_item, remove_pantry_item
        
        # Step 1: Check initial pantry state
        print("1. Getting initial pantry contents...")
        initial_pantry = get_pantry_contents()
        print(f"   Initial pantry: {json.dumps(initial_pantry, indent=2)}")
        
        # Step 2: Add some items
        print("2. Adding items to pantry...")
        items_to_add = [
            {"name": "pasta", "quantity": 500, "unit": "gram", "notes": "Test pasta"},
            {"name": "tomato sauce", "quantity": 400, "unit": "ml", "notes": "Test sauce"},
            {"name": "olive oil", "quantity": 250, "unit": "ml", "notes": "Test oil"}
        ]
        
        for item in items_to_add:
            result = add_pantry_item(
                item["name"], item["quantity"], item["unit"], item["notes"]
            )
            print(f"   Added {item['name']}: {json.dumps(result, indent=2)}")
        
        # Step 3: Check pantry contents after adding
        print("3. Checking pantry contents after adding...")
        updated_pantry = get_pantry_contents()
        print(f"   Updated pantry: {json.dumps(updated_pantry, indent=2)}")
        
        # Step 4: Remove some items
        print("4. Removing some items from pantry...")
        result = remove_pantry_item("pasta", 100, "gram", "Used for cooking")
        print(f"   Remove result: {json.dumps(result, indent=2)}")
        
        # Step 5: Final pantry check
        print("5. Final pantry check...")
        final_pantry = get_pantry_contents()
        print(f"   Final pantry: {json.dumps(final_pantry, indent=2)}")
        
        print("✅ Pantry management flow completed!")
        
    except Exception as e:
        print(f"❌ Error in pantry management flow: {e}")

def test_meal_planning_flow():
    """Test the meal planning workflow."""
    print("\n📅 Testing Meal Planning Flow")
    print("=" * 40)
    
    try:
        from mcp_server import get_week_plan, set_recipe_for_date, get_grocery_list
        from datetime import date, timedelta
        
        # Step 1: Check current meal plan
        print("1. Getting current week's meal plan...")
        current_plan = get_week_plan()
        print(f"   Current plan: {json.dumps(current_plan, indent=2)}")
        
        # Step 2: Set a recipe for tomorrow
        print("2. Setting recipe for tomorrow...")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        set_result = set_recipe_for_date(tomorrow, "Test Pasta")
        print(f"   Set result: {json.dumps(set_result, indent=2)}")
        
        # Step 3: Check updated meal plan
        print("3. Checking updated meal plan...")
        updated_plan = get_week_plan()
        print(f"   Updated plan: {json.dumps(updated_plan, indent=2)}")
        
        # Step 4: Generate grocery list
        print("4. Generating grocery list...")
        grocery_list = get_grocery_list()
        print(f"   Grocery list: {json.dumps(grocery_list, indent=2)}")
        
        print("✅ Meal planning flow completed!")
        
    except Exception as e:
        print(f"❌ Error in meal planning flow: {e}")

def test_user_management_flow():
    """Test user management for remote mode."""
    print("\n👥 Testing User Management Flow (Remote Mode)")
    print("=" * 50)
    
    import os
    
    # Set remote mode
    original_mode = os.environ.get('MCP_MODE')
    original_token = os.environ.get('ADMIN_TOKEN')
    
    os.environ['MCP_MODE'] = 'remote'
    os.environ['ADMIN_TOKEN'] = 'test-admin-token-123'
    
    try:
        # Re-import to get remote mode
        import importlib
        import mcp_server
        importlib.reload(mcp_server)
        
        from mcp_server import create_user, list_users, list_preferences, add_preference
        
        # Step 1: List initial users
        print("1. Listing initial users...")
        initial_users = list_users("test-admin-token-123")
        print(f"   Initial users: {json.dumps(initial_users, indent=2)}")
        
        # Step 2: Create a test user
        print("2. Creating a test user...")
        create_result = create_user("testuser", "test-admin-token-123")
        print(f"   Create result: {json.dumps(create_result, indent=2)}")
        
        if create_result.get('status') == 'success':
            user_token = create_result.get('token')
            
            # Step 3: Test user isolation
            print("3. Testing user isolation...")
            
            # Add preference as admin
            admin_pref = add_preference("dietary", "admin-pref", "required", "Admin only", "test-admin-token-123")
            print(f"   Admin preference: {json.dumps(admin_pref, indent=2)}")
            
            # Add preference as user
            user_pref = add_preference("dietary", "user-pref", "required", "User only", user_token)
            print(f"   User preference: {json.dumps(user_pref, indent=2)}")
            
            # Check admin preferences
            admin_prefs = list_preferences("test-admin-token-123")
            print(f"   Admin sees: {len(admin_prefs.get('preferences', []))} preferences")
            
            # Check user preferences  
            user_prefs = list_preferences(user_token)
            print(f"   User sees: {len(user_prefs.get('preferences', []))} preferences")
        
        # Step 4: List all users
        print("4. Listing all users...")
        final_users = list_users("test-admin-token-123")
        print(f"   Final users: {json.dumps(final_users, indent=2)}")
        
        print("✅ User management flow completed!")
        
    except Exception as e:
        print(f"❌ Error in user management flow: {e}")
    finally:
        # Restore original environment
        if original_mode:
            os.environ['MCP_MODE'] = original_mode
        else:
            os.environ.pop('MCP_MODE', None)
            
        if original_token:
            os.environ['ADMIN_TOKEN'] = original_token
        else:
            os.environ.pop('ADMIN_TOKEN', None)

def run_all_scenarios():
    """Run all scenario tests."""
    print("🧪 Running All MCP Server Scenario Tests")
    print("=" * 50)
    
    test_recipe_management_flow()
    test_pantry_management_flow() 
    test_meal_planning_flow()
    test_user_management_flow()
    
    print("\n🎉 All scenario tests completed!")
    print("\nThese tests demonstrate complete workflows:")
    print("- Recipe management (CRUD operations)")
    print("- Pantry management (add/remove items)")
    print("- Meal planning (schedule recipes, generate grocery lists)")
    print("- User management (multi-user isolation)")

if __name__ == "__main__":
    run_all_scenarios()
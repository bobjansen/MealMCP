#!/usr/bin/env python3
"""
Database population script for MealMCP.
Populates the database with sample recipes, pantry items, preferences, and meal plans.
"""

import sys
import os
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pantry_manager_factory import create_pantry_manager
from pantry_manager_shared import SharedPantryManager
from db_setup import setup_database
from db_setup_shared import setup_shared_database
from werkzeug.security import generate_password_hash


def get_sample_recipes() -> List[Dict[str, Any]]:
    """Get a collection of sample recipes."""
    return [
        {
            "name": "Classic Spaghetti Carbonara",
            "instructions": "1. Cook spaghetti according to package instructions.\n2. While pasta cooks, fry pancetta until crispy.\n3. Beat eggs with parmesan and pepper in a large bowl.\n4. Drain pasta and immediately toss with egg mixture and pancetta.\n5. Serve immediately with extra parmesan.",
            "time_minutes": 20,
            "ingredients": [
                {"name": "spaghetti", "quantity": 400, "unit": "Gram"},
                {"name": "pancetta", "quantity": 150, "unit": "Gram"},
                {"name": "eggs", "quantity": 3, "unit": "Piece"},
                {"name": "parmesan cheese", "quantity": 0.5, "unit": "Cup"},
                {"name": "black pepper", "quantity": 1, "unit": "Teaspoon"},
            ],
        },
        {
            "name": "Chicken Stir Fry",
            "instructions": "1. Cut chicken into bite-sized pieces and season.\n2. Heat oil in a wok or large pan over high heat.\n3. Cook chicken until golden, remove and set aside.\n4. Stir-fry vegetables for 3-4 minutes.\n5. Return chicken to pan, add sauce and toss until heated through.",
            "time_minutes": 15,
            "ingredients": [
                {"name": "chicken breast", "quantity": 500, "unit": "Gram"},
                {"name": "bell peppers", "quantity": 2, "unit": "Piece"},
                {"name": "broccoli", "quantity": 200, "unit": "Gram"},
                {"name": "soy sauce", "quantity": 3, "unit": "Tablespoon"},
                {"name": "vegetable oil", "quantity": 2, "unit": "Tablespoon"},
                {"name": "garlic", "quantity": 3, "unit": "Piece"},
                {"name": "ginger", "quantity": 1, "unit": "Tablespoon"},
            ],
        },
        {
            "name": "Beef Tacos",
            "instructions": "1. Brown ground beef in a large skillet over medium-high heat.\n2. Add onions and cook until soft.\n3. Season with cumin, chili powder, salt and pepper.\n4. Warm tortillas and fill with beef mixture.\n5. Top with cheese, lettuce, and tomatoes.",
            "time_minutes": 25,
            "ingredients": [
                {"name": "ground beef", "quantity": 500, "unit": "Gram"},
                {"name": "taco shells", "quantity": 8, "unit": "Piece"},
                {"name": "cheddar cheese", "quantity": 1, "unit": "Cup"},
                {"name": "lettuce", "quantity": 2, "unit": "Cup"},
                {"name": "tomatoes", "quantity": 2, "unit": "Piece"},
                {"name": "onion", "quantity": 1, "unit": "Piece"},
                {"name": "cumin", "quantity": 1, "unit": "Teaspoon"},
                {"name": "chili powder", "quantity": 1, "unit": "Teaspoon"},
            ],
        },
        {
            "name": "Vegetable Curry",
            "instructions": "1. Heat oil in a large pot over medium heat.\n2. Add onion and cook until softened.\n3. Add garlic, ginger, and curry powder, cook for 1 minute.\n4. Add vegetables and coconut milk, simmer for 15 minutes.\n5. Season with salt and serve over rice.",
            "time_minutes": 30,
            "ingredients": [
                {"name": "coconut milk", "quantity": 400, "unit": "Milliliter"},
                {"name": "sweet potato", "quantity": 2, "unit": "Piece"},
                {"name": "cauliflower", "quantity": 1, "unit": "Piece"},
                {"name": "green beans", "quantity": 200, "unit": "Gram"},
                {"name": "onion", "quantity": 1, "unit": "Piece"},
                {"name": "garlic", "quantity": 4, "unit": "Piece"},
                {"name": "ginger", "quantity": 2, "unit": "Tablespoon"},
                {"name": "curry powder", "quantity": 2, "unit": "Tablespoon"},
                {"name": "vegetable oil", "quantity": 2, "unit": "Tablespoon"},
            ],
        },
        {
            "name": "Caesar Salad",
            "instructions": "1. Tear romaine lettuce into bite-sized pieces.\n2. Make dressing by whisking together lemon juice, garlic, anchovy paste, parmesan, and olive oil.\n3. Toss lettuce with dressing.\n4. Top with croutons and extra parmesan.\n5. Serve immediately.",
            "time_minutes": 10,
            "ingredients": [
                {"name": "romaine lettuce", "quantity": 1, "unit": "Piece"},
                {"name": "parmesan cheese", "quantity": 0.5, "unit": "Cup"},
                {"name": "croutons", "quantity": 1, "unit": "Cup"},
                {"name": "lemon juice", "quantity": 2, "unit": "Tablespoon"},
                {"name": "olive oil", "quantity": 0.25, "unit": "Cup"},
                {"name": "garlic", "quantity": 2, "unit": "Piece"},
                {"name": "anchovy paste", "quantity": 1, "unit": "Teaspoon"},
            ],
        },
        {
            "name": "Chocolate Chip Cookies",
            "instructions": "1. Preheat oven to 375°F (190°C).\n2. Cream butter and sugars until light and fluffy.\n3. Beat in eggs and vanilla.\n4. Mix in flour, baking soda, and salt.\n5. Fold in chocolate chips.\n6. Drop spoonfuls onto baking sheet and bake 9-11 minutes.",
            "time_minutes": 45,
            "ingredients": [
                {"name": "butter", "quantity": 1, "unit": "Cup"},
                {"name": "brown sugar", "quantity": 0.75, "unit": "Cup"},
                {"name": "white sugar", "quantity": 0.25, "unit": "Cup"},
                {"name": "eggs", "quantity": 2, "unit": "Piece"},
                {"name": "vanilla extract", "quantity": 1, "unit": "Teaspoon"},
                {"name": "flour", "quantity": 2.25, "unit": "Cup"},
                {"name": "baking soda", "quantity": 1, "unit": "Teaspoon"},
                {"name": "salt", "quantity": 1, "unit": "Teaspoon"},
                {"name": "chocolate chips", "quantity": 2, "unit": "Cup"},
            ],
        },
        {
            "name": "Greek Salad",
            "instructions": "1. Chop tomatoes, cucumber, and red onion into chunks.\n2. Add olives and feta cheese.\n3. Drizzle with olive oil and lemon juice.\n4. Season with oregano, salt, and pepper.\n5. Toss gently and serve.",
            "time_minutes": 15,
            "ingredients": [
                {"name": "tomatoes", "quantity": 4, "unit": "Piece"},
                {"name": "cucumber", "quantity": 1, "unit": "Piece"},
                {"name": "red onion", "quantity": 0.5, "unit": "Piece"},
                {"name": "kalamata olives", "quantity": 0.5, "unit": "Cup"},
                {"name": "feta cheese", "quantity": 200, "unit": "Gram"},
                {"name": "olive oil", "quantity": 0.25, "unit": "Cup"},
                {"name": "lemon juice", "quantity": 2, "unit": "Tablespoon"},
                {"name": "dried oregano", "quantity": 1, "unit": "Teaspoon"},
            ],
        },
    ]


def get_sample_pantry_items() -> List[Dict[str, Any]]:
    """Get a collection of sample pantry items."""
    return [
        # Grains and Pasta
        {
            "item_name": "spaghetti",
            "quantity": 1,
            "unit": "Kilogram",
            "notes": "Whole wheat",
        },
        {
            "item_name": "rice",
            "quantity": 2,
            "unit": "Kilogram",
            "notes": "Jasmine rice",
        },
        {
            "item_name": "flour",
            "quantity": 1,
            "unit": "Kilogram",
            "notes": "All-purpose",
        },
        {
            "item_name": "bread",
            "quantity": 2,
            "unit": "Piece",
            "notes": "Whole grain loaf",
        },
        # Proteins
        {
            "item_name": "chicken breast",
            "quantity": 800,
            "unit": "Gram",
            "notes": "Frozen",
        },
        {"item_name": "ground beef", "quantity": 500, "unit": "Gram", "notes": "Lean"},
        {"item_name": "eggs", "quantity": 12, "unit": "Piece", "notes": "Free-range"},
        {
            "item_name": "salmon fillet",
            "quantity": 400,
            "unit": "Gram",
            "notes": "Fresh",
        },
        # Dairy
        {"item_name": "milk", "quantity": 2, "unit": "Liter", "notes": "Whole milk"},
        {"item_name": "butter", "quantity": 250, "unit": "Gram", "notes": "Unsalted"},
        {
            "item_name": "parmesan cheese",
            "quantity": 200,
            "unit": "Gram",
            "notes": "Aged",
        },
        {
            "item_name": "cheddar cheese",
            "quantity": 300,
            "unit": "Gram",
            "notes": "Sharp",
        },
        {"item_name": "feta cheese", "quantity": 150, "unit": "Gram", "notes": "Greek"},
        # Vegetables
        {
            "item_name": "tomatoes",
            "quantity": 1,
            "unit": "Kilogram",
            "notes": "Roma tomatoes",
        },
        {
            "item_name": "onion",
            "quantity": 3,
            "unit": "Piece",
            "notes": "Yellow onions",
        },
        {"item_name": "garlic", "quantity": 2, "unit": "Piece", "notes": "Fresh bulbs"},
        {
            "item_name": "bell peppers",
            "quantity": 4,
            "unit": "Piece",
            "notes": "Mixed colors",
        },
        {"item_name": "broccoli", "quantity": 500, "unit": "Gram", "notes": "Fresh"},
        {"item_name": "carrots", "quantity": 1, "unit": "Kilogram", "notes": "Organic"},
        {
            "item_name": "lettuce",
            "quantity": 2,
            "unit": "Piece",
            "notes": "Romaine hearts",
        },
        {
            "item_name": "cucumber",
            "quantity": 3,
            "unit": "Piece",
            "notes": "English cucumber",
        },
        # Condiments and Oils
        {
            "item_name": "olive oil",
            "quantity": 750,
            "unit": "Milliliter",
            "notes": "Extra virgin",
        },
        {
            "item_name": "vegetable oil",
            "quantity": 1,
            "unit": "Liter",
            "notes": "Canola oil",
        },
        {
            "item_name": "soy sauce",
            "quantity": 500,
            "unit": "Milliliter",
            "notes": "Low sodium",
        },
        {
            "item_name": "lemon juice",
            "quantity": 250,
            "unit": "Milliliter",
            "notes": "Fresh squeezed",
        },
        {
            "item_name": "balsamic vinegar",
            "quantity": 250,
            "unit": "Milliliter",
            "notes": "Aged",
        },
        # Spices and Herbs
        {
            "item_name": "black pepper",
            "quantity": 50,
            "unit": "Gram",
            "notes": "Ground",
        },
        {"item_name": "salt", "quantity": 500, "unit": "Gram", "notes": "Sea salt"},
        {"item_name": "cumin", "quantity": 30, "unit": "Gram", "notes": "Ground"},
        {"item_name": "chili powder", "quantity": 40, "unit": "Gram", "notes": "Mild"},
        {
            "item_name": "curry powder",
            "quantity": 50,
            "unit": "Gram",
            "notes": "Madras",
        },
        {
            "item_name": "dried oregano",
            "quantity": 20,
            "unit": "Gram",
            "notes": "Mediterranean",
        },
        {
            "item_name": "vanilla extract",
            "quantity": 100,
            "unit": "Milliliter",
            "notes": "Pure",
        },
        {"item_name": "ginger", "quantity": 100, "unit": "Gram", "notes": "Fresh root"},
        # Pantry Staples
        {
            "item_name": "coconut milk",
            "quantity": 800,
            "unit": "Milliliter",
            "notes": "Canned",
        },
        {
            "item_name": "baking soda",
            "quantity": 200,
            "unit": "Gram",
            "notes": "Aluminum-free",
        },
        {
            "item_name": "brown sugar",
            "quantity": 500,
            "unit": "Gram",
            "notes": "Dark brown",
        },
        {
            "item_name": "white sugar",
            "quantity": 1,
            "unit": "Kilogram",
            "notes": "Granulated",
        },
        {
            "item_name": "chocolate chips",
            "quantity": 300,
            "unit": "Gram",
            "notes": "Semi-sweet",
        },
    ]


def get_sample_preferences() -> List[Dict[str, Any]]:
    """Get sample food preferences."""
    return [
        {
            "category": "like",
            "item": "pasta dishes",
            "level": "preferred",
            "notes": "Especially Italian cuisine",
        },
        {
            "category": "like",
            "item": "grilled chicken",
            "level": "preferred",
            "notes": "Prefer herb-seasoned",
        },
        {
            "category": "like",
            "item": "fresh vegetables",
            "level": "preferred",
            "notes": "Locally sourced when possible",
        },
        {
            "category": "like",
            "item": "seafood",
            "level": "preferred",
            "notes": "Salmon and tuna preferred",
        },
        {
            "category": "dislike",
            "item": "spicy food",
            "level": "avoid",
            "notes": "Low spice tolerance",
        },
        {
            "category": "dislike",
            "item": "liver",
            "level": "avoid",
            "notes": "Texture issues",
        },
        {
            "category": "allergy",
            "item": "shellfish",
            "level": "severe",
            "notes": "Anaphylaxis risk - keep EpiPen nearby",
        },
        {
            "category": "allergy",
            "item": "tree nuts",
            "level": "avoid",
            "notes": "Avoid almonds, walnuts, pecans",
        },
        {
            "category": "dietary",
            "item": "low sodium",
            "level": "preferred",
            "notes": "Doctor recommended",
        },
        {
            "category": "dietary",
            "item": "whole grains",
            "level": "preferred",
            "notes": "Better for health",
        },
    ]


def create_meal_plan(pantry_manager, recipes: List[str]) -> bool:
    """Create a sample meal plan for the next week."""
    today = datetime.now().date()

    # Plan meals for the next 7 days
    success_count = 0
    for i in range(7):
        meal_date = today + timedelta(days=i)
        recipe_name = recipes[i % len(recipes)]  # Cycle through available recipes

        if pantry_manager.set_meal_plan(meal_date.strftime("%Y-%m-%d"), recipe_name):
            success_count += 1

    return success_count > 0


def create_default_user(
    connection_string: str,
    username: str = "demo",
    email: str = "demo@example.com",
    password: str = "demo123",
) -> int:
    """
    Create a default user for PostgreSQL population.

    Args:
        connection_string: PostgreSQL connection string
        username: Username for the default user
        email: Email for the default user
        password: Password for the default user

    Returns:
        int: User ID of the created user
    """
    try:
        import psycopg2
        from urllib.parse import urlparse

        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                # Check if user already exists
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                existing_user = cursor.fetchone()

                if existing_user:
                    return existing_user[0]

                # Create password hash
                password_hash = generate_password_hash(password)

                # Insert new user
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, preferred_language)
                    VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                    (username, email, password_hash, "en"),
                )
                user_id = cursor.fetchone()[0]

                # Set household_id to self (for single household)
                cursor.execute(
                    "UPDATE users SET household_id = %s WHERE id = %s",
                    (user_id, user_id),
                )

                return user_id

    except Exception as e:
        raise Exception(f"Failed to create default user: {e}")


def populate_database(
    backend: str = None,
    connection_string: str = None,
    verbose: bool = True,
    user_id: int = 1,
) -> bool:
    """
    Populate the database with sample data.

    Args:
        backend: Database backend ('sqlite' or 'postgresql')
        connection_string: Database connection string
        verbose: Print progress messages
        user_id: User ID for PostgreSQL multi-user mode (default: 1)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize database first
        if verbose:
            print("🍽️  Populating MealMCP Database")
            print("=" * 40)
            print("🔧 Initializing database...")

        # Setup database tables
        if backend == "postgresql":
            # For PostgreSQL, setup shared database
            if not connection_string:
                raise ValueError("PostgreSQL backend requires connection string")

            if verbose:
                print(f"  🐘 Setting up PostgreSQL database...")

            setup_shared_database(connection_string)

            # Create or find default user if user_id is 1 (default)
            if user_id == 1:
                if verbose:
                    print(f"  👤 Creating/finding default demo user...")
                user_id = create_default_user(connection_string)
                if verbose:
                    print(f"  ✅ Demo user ready (ID: {user_id})")

            if verbose:
                print(f"  ✅ PostgreSQL database initialized")
                print(f"  👤 Using user ID: {user_id}")
        else:
            # For SQLite, use the setup function
            db_path = connection_string or os.getenv("PANTRY_DB_PATH", "pantry.db")
            setup_database(db_path)
            if verbose:
                print(f"  ✅ SQLite database initialized: {db_path}")

        # Create pantry manager
        if backend == "postgresql":
            # Use SharedPantryManager directly for PostgreSQL
            pantry_manager = SharedPantryManager(
                connection_string=connection_string,
                user_id=user_id,
                backend="postgresql",
            )
        elif backend and connection_string:
            pantry_manager = create_pantry_manager(
                backend=backend, connection_string=connection_string
            )
        else:
            pantry_manager = create_pantry_manager()

        if verbose:
            print("  ✅ Pantry manager created")

        # Add recipes
        if verbose:
            print("📝 Adding sample recipes...")

        recipes = get_sample_recipes()
        added_recipes = []

        for recipe in recipes:
            success, recipe_id = pantry_manager.add_recipe(
                name=recipe["name"],
                instructions=recipe["instructions"],
                time_minutes=recipe["time_minutes"],
                ingredients=recipe["ingredients"],
            )

            if success:
                added_recipes.append(recipe["name"])
                if verbose:
                    print(f"  ✅ Added: {recipe['name']} (ID: {recipe_id})")
            else:
                if verbose:
                    print(f"  ⚠️  Skipped: {recipe['name']} (already exists)")

        if verbose:
            print(f"📝 Added {len(added_recipes)} recipes")

        # Add pantry items
        if verbose:
            print("\n🥫 Adding pantry items...")

        pantry_items = get_sample_pantry_items()
        added_items = 0

        for item in pantry_items:
            success = pantry_manager.add_item(
                item_name=item["item_name"],
                quantity=item["quantity"],
                unit=item["unit"],
                notes=item.get("notes"),
            )

            if success:
                added_items += 1
                if verbose:
                    print(
                        f"  ✅ Added: {item['quantity']} {item['unit']} of {item['item_name']}"
                    )
            else:
                if verbose:
                    print(f"  ❌ Failed to add: {item['item_name']}")

        if verbose:
            print(f"🥫 Added {added_items} pantry items")

        # Add preferences
        if verbose:
            print("\n❤️  Adding food preferences...")

        preferences = get_sample_preferences()
        added_preferences = 0

        for pref in preferences:
            success = pantry_manager.add_preference(
                category=pref["category"],
                item=pref["item"],
                level=pref["level"],
                notes=pref.get("notes"),
            )

            if success:
                added_preferences += 1
                if verbose:
                    print(
                        f"  ✅ Added: {pref['category']} - {pref['item']} ({pref['level']})"
                    )
            else:
                if verbose:
                    print(
                        f"  ⚠️  Skipped: {pref['category']} - {pref['item']} (already exists)"
                    )

        if verbose:
            print(f"❤️  Added {added_preferences} preferences")

        # Create meal plan
        if verbose:
            print("\n📅 Creating meal plan...")

        # Use existing recipes if we didn't add any new ones
        recipe_names_for_plan = (
            added_recipes if added_recipes else [r["name"] for r in recipes]
        )

        if recipe_names_for_plan and create_meal_plan(
            pantry_manager, recipe_names_for_plan
        ):
            if verbose:
                print("  ✅ Created 7-day meal plan")
        else:
            if verbose:
                print("  ❌ Failed to create meal plan")

        if verbose:
            print("\n" + "=" * 40)
            print("🎉 Database population completed!")
            print(f"   📝 Recipes: {len(added_recipes)}")
            print(f"   🥫 Pantry items: {added_items}")
            print(f"   ❤️  Preferences: {added_preferences}")
            print(f"   📅 Meal plan: 7 days")

        return True

    except Exception as e:
        if verbose:
            print(f"\n❌ Error populating database: {e}")
        return False


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Populate MealMCP database with sample data"
    )
    parser.add_argument(
        "--backend", choices=["sqlite", "postgresql"], help="Database backend to use"
    )
    parser.add_argument(
        "--connection-string", type=str, help="Database connection string"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="User ID for PostgreSQL multi-user mode (default: 1)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Run quietly without progress messages",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before populating (WARNING: destructive)",
    )

    args = parser.parse_args()

    if args.clear:
        print("⚠️  WARNING: --clear flag is not yet implemented")
        print("   This would delete all existing data in the database")
        print("   For now, the script will add to existing data")
        print()

    # Auto-detect backend from connection string if not specified
    backend = args.backend
    if not backend and args.connection_string:
        if args.connection_string.startswith(
            "postgresql://"
        ) or args.connection_string.startswith("postgres://"):
            backend = "postgresql"
        elif (
            args.connection_string.endswith(".db")
            or "sqlite" in args.connection_string.lower()
        ):
            backend = "sqlite"

    # Populate the database
    success = populate_database(
        backend=backend,
        connection_string=args.connection_string,
        verbose=not args.quiet,
        user_id=args.user_id,
    )

    if success:
        if not args.quiet:
            print("\n✅ Success! You can now:")
            print("   • View recipes in the web interface")
            print("   • Check pantry contents")
            print("   • See your meal plan")
            print("   • Test recipe feasibility")
        sys.exit(0)
    else:
        if not args.quiet:
            print("\n❌ Failed to populate database")
        sys.exit(1)


if __name__ == "__main__":
    main()

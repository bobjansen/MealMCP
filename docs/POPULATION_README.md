# Database Population Scripts

This directory contains scripts to populate your MealMCP database with sample data for testing and demonstration purposes.

## Quick Start

### Populate Default Database
```bash
# Populate the default SQLite database (pantry.db) with sample data
uv run python populate_default_db.py
```

This will create:
- 7 sample recipes (pasta, stir fry, tacos, curry, salads, cookies)
- 39 pantry items (ingredients, spices, dairy, proteins)
- 10 food preferences (likes, dislikes, allergies, dietary restrictions)
- 7-day meal plan

### Custom Database Population
```bash
# Full options
uv run python populate_database.py --help

# Populate with custom SQLite database
PANTRY_DB_PATH=/path/to/custom.db uv run python populate_database.py

# Populate quietly (no progress output)
uv run python populate_database.py --quiet

# Populate PostgreSQL database (creates demo user automatically)
uv run python populate_database.py --backend postgresql --connection-string "postgresql://user:pass@host/db"

# Populate PostgreSQL for specific user ID
uv run python populate_database.py --backend postgresql --connection-string "postgresql://user:pass@host/db" --user-id 5
```

## Sample Data Included

### 🍳 Recipes (7)
1. **Classic Spaghetti Carbonara** - 20 min
2. **Chicken Stir Fry** - 15 min
3. **Beef Tacos** - 25 min
4. **Vegetable Curry** - 30 min
5. **Caesar Salad** - 10 min
6. **Chocolate Chip Cookies** - 45 min
7. **Greek Salad** - 15 min

### 🥫 Pantry Items (39)
- **Grains & Pasta**: Spaghetti, rice, flour, bread
- **Proteins**: Chicken, beef, eggs, salmon
- **Dairy**: Milk, butter, various cheeses
- **Vegetables**: Tomatoes, onions, peppers, greens
- **Condiments**: Olive oil, soy sauce, vinegars
- **Spices**: Salt, pepper, cumin, curry powder
- **Baking**: Sugar, vanilla, chocolate chips

### ❤️ Food Preferences (10)
- **Likes**: Pasta dishes, grilled chicken, vegetables, seafood
- **Dislikes**: Spicy food, liver
- **Allergies**: Shellfish (severe), tree nuts (moderate)
- **Dietary**: Low sodium, whole grains

### 📅 Meal Plan
- 7-day plan cycling through the available recipes
- Starts from today's date

## After Population

Once populated, you can:

1. **Start the web interface**:
   ```bash
   uv run run_web.py
   ```
   Visit http://localhost:5000

2. **Start the MCP server**:
   ```bash
   uv run run_mcp.py
   ```

3. **Test recipe feasibility** - Most recipes should be makeable with the provided pantry items!

4. **Explore the meal plan** - Check what's planned for the next 7 days

5. **View your preferences** - See the sample food preferences and restrictions

## Notes

- **SQLite**: Automatically initializes databases with required tables
- **PostgreSQL**: Automatically sets up schema and creates a demo user (username: `demo`, password: `demo123`)
- All quantities use proper units that work with the unit conversion system
- Sample data is realistic and represents a well-stocked home kitchen
- Recipes are designed to be feasible with the provided pantry items
- For PostgreSQL multi-user scenarios, the script creates user-scoped data
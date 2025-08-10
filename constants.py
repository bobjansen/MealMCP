"""
Application constants for MealMCP.
Centralized location for all constant values used throughout the application.
"""

# Measurement Units
# Each unit includes a base measurement type and its size expressed
# in that base unit. These provide sensible defaults for new users.
DEFAULT_UNITS = [
    {"name": "Teaspoon", "base_unit": "ml", "size": 5.0},
    {"name": "Tablespoon", "base_unit": "ml", "size": 15.0},
    {"name": "Fluid ounce", "base_unit": "ml", "size": 30.0},
    {"name": "Cup", "base_unit": "ml", "size": 240.0},
    {"name": "Pint", "base_unit": "ml", "size": 473.0},
    {"name": "Quart", "base_unit": "ml", "size": 946.0},
    {"name": "Gallon", "base_unit": "ml", "size": 3785.0},
    {"name": "Milliliter", "base_unit": "ml", "size": 1.0},
    {"name": "Liter", "base_unit": "ml", "size": 1000.0},
    {"name": "Ounce", "base_unit": "g", "size": 28.35},
    {"name": "Pound", "base_unit": "g", "size": 453.59},
    {"name": "Gram", "base_unit": "g", "size": 1.0},
    {"name": "Kilogram", "base_unit": "g", "size": 1000.0},
    {"name": "Piece", "base_unit": "count", "size": 1.0},
]

# Combined units list for backwards compatibility
UNITS = [u["name"] for u in DEFAULT_UNITS]

# Preference Categories
PREFERENCE_CATEGORIES = {"dietary", "allergy", "like", "dislike", "cuisine", "other"}

# Database Limits
MAX_INGREDIENT_NAME_LENGTH = 100
MAX_RECIPE_NAME_LENGTH = 200
MAX_INSTRUCTIONS_LENGTH = 10000
MAX_NOTES_LENGTH = 1000
MAX_QUANTITY_VALUE = 999999
MAX_TIME_MINUTES = 10080  # 1 week in minutes

# Rating Constraints
MIN_RATING = 1
MAX_RATING = 5

# Default Values
DEFAULT_HOUSEHOLD_ADULTS = 2
DEFAULT_HOUSEHOLD_CHILDREN = 0
DEFAULT_LANGUAGE = "en"

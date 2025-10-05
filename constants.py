"""
Application constants for MealMCP.
Centralized location for all constant values used throughout the application.
"""

# Measurement Units by Locale
# Each unit includes a base measurement type and its size expressed
# in that base unit. Different locales prefer different measurement systems.
UNITS_BY_LOCALE = {
    "en": [
        # Imperial/US measurements (common in English-speaking countries)
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
    ],
    "nl": [
        # Metric measurements (common in Netherlands and Europe)
        {"name": "Theelepel", "base_unit": "ml", "size": 5.0},
        {"name": "Eetlepel", "base_unit": "ml", "size": 15.0},
        {"name": "Milliliter", "base_unit": "ml", "size": 1.0},
        {"name": "Deciliter", "base_unit": "ml", "size": 100.0},
        {"name": "Liter", "base_unit": "ml", "size": 1000.0},
        {"name": "Gram", "base_unit": "g", "size": 1.0},
        {"name": "Kilogram", "base_unit": "g", "size": 1000.0},
        {"name": "Stuk", "base_unit": "count", "size": 1.0},
        {"name": "Blik", "base_unit": "count", "size": 1.0},  # Can/tin
        {"name": "Pak", "base_unit": "count", "size": 1.0},  # Package
        {"name": "Zakje", "base_unit": "count", "size": 1.0},  # Small bag/packet
    ],
}

# Default units (English) for backwards compatibility
DEFAULT_UNITS = UNITS_BY_LOCALE["en"]

# Combined units list for backwards compatibility
UNITS = [u["name"] for u in DEFAULT_UNITS]


def get_units_for_locale(locale="en"):
    """Get the appropriate unit set for the specified locale."""
    return UNITS_BY_LOCALE.get(locale, UNITS_BY_LOCALE["en"])


# Preference Categories
PREFERENCE_CATEGORIES = {"dietary", "allergy", "like", "dislike", "cuisine", "other"}

# Ingredients that are considered to have infinite quantities (don't need to be purchased)
# Organized by language for internationalization support
INFINITE_INGREDIENTS_BY_LANG = {
    "en": {
        "water",
        "tap water",
        "drinking water",
        "salt",
        "table salt",
        "sea salt",
        "black pepper",
        "white pepper",
        "pepper",
        "ground pepper",
        "peppercorns",
    },
    "nl": {
        "water",
        "kraanwater",
        "drinkwater",
        "zout",
        "tafelzout",
        "zeezout",
        "zwarte peper",
        "witte peper",
        "peper",
        "gemalen peper",
        "peperkorrels",
    },
}

# Default infinite ingredients (English) for backward compatibility
INFINITE_INGREDIENTS = INFINITE_INGREDIENTS_BY_LANG["en"]


def get_infinite_ingredients(lang="en"):
    """Get infinite ingredients list for the specified language."""
    return INFINITE_INGREDIENTS_BY_LANG.get(lang, INFINITE_INGREDIENTS_BY_LANG["en"])


def is_infinite_ingredient(ingredient_name, lang="en"):
    """Check if an ingredient is considered to have infinite quantities."""
    infinite_set = get_infinite_ingredients(lang)
    return ingredient_name.lower() in infinite_set


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

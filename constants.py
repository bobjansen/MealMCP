"""
Application constants for MealMCP.
Centralized location for all constant values used throughout the application.
"""

# Measurement Units
VOLUME_UNITS_IMPERIAL = [
    "Teaspoon",
    "Tablespoon",
    "Fluid ounce",
    "Cup",
    "Pint",
    "Quart",
    "Gallon",
]

VOLUME_UNITS_METRIC = [
    "Milliliter",
    "Liter",
]

WEIGHT_UNITS_IMPERIAL = [
    "Ounce",
    "Pound",
]

WEIGHT_UNITS_METRIC = [
    "Gram",
    "Kilogram",
]

COUNT_UNITS = [
    "Piece",
]

# Combined units list for backwards compatibility
UNITS = (
    VOLUME_UNITS_IMPERIAL
    + VOLUME_UNITS_METRIC
    + WEIGHT_UNITS_IMPERIAL
    + WEIGHT_UNITS_METRIC
    + COUNT_UNITS
)

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

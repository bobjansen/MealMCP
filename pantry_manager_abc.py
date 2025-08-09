from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


class PantryManager(ABC):
    """
    Abstract base class for pantry management implementations.

    This interface defines all the methods that a pantry manager must implement
    to handle ingredients, recipes, preferences, and meal planning.
    """

    @abstractmethod
    def __init__(self, connection_string: str, **kwargs):
        """
        Initialize the pantry manager with database connection details.

        Args:
            connection_string: Database connection string (format depends on implementation)
            **kwargs: Additional configuration options
        """
        pass

    # Ingredient Management
    @abstractmethod
    def add_ingredient(self, name: str, default_unit: str) -> bool:
        """
        Add a new ingredient to the database.

        Args:
            name: Name of the ingredient
            default_unit: Default unit of measurement for this ingredient

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_ingredient_id(self, name: str) -> Optional[int]:
        """
        Get the ID of an ingredient by name.

        Args:
            name: Name of the ingredient

        Returns:
            Optional[int]: Ingredient ID if found, None otherwise
        """
        pass

    # Preference Management
    @abstractmethod
    def add_preference(
        self, category: str, item: str, level: str, notes: str = None
    ) -> bool:
        """
        Add a new food preference to the database.

        Args:
            category: Type of preference (dietary, allergy, dislike, like)
            item: The specific preference item
            level: Importance level (required, preferred, avoid)
            notes: Optional notes about the preference

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If category, item, or level is empty
        """
        pass

    @abstractmethod
    def update_preference(
        self, preference_id: int, level: str, notes: str = None
    ) -> bool:
        """
        Update an existing food preference.

        Args:
            preference_id: ID of the preference to update
            level: New importance level (required/preferred/avoid)
            notes: Optional new notes

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If level is empty
        """
        pass

    @abstractmethod
    def delete_preference(self, preference_id: int) -> bool:
        """
        Delete a food preference by ID.

        Args:
            preference_id: ID of the preference to delete

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_preferences(self) -> List[Dict[str, Any]]:
        """
        Get all food preferences.

        Returns:
            List[Dict[str, Any]]: List of preferences with their details
        """
        pass

    # Pantry Item Management
    @abstractmethod
    def add_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Add a new item to the pantry or increase existing item quantity.

        Args:
            item_name: Name of the item to add
            quantity: Amount to add
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def remove_item(
        self, item_name: str, quantity: float, unit: str, notes: Optional[str] = None
    ) -> bool:
        """
        Remove a quantity of an item from the pantry.

        Args:
            item_name: Name of the item to remove
            quantity: Amount to remove
            unit: Unit of measurement
            notes: Optional notes about the transaction

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_item_quantity(self, item_name: str, unit: str) -> float:
        """
        Get the current quantity of an item in the pantry.

        Args:
            item_name: Name of the item to check
            unit: Unit of measurement

        Returns:
            float: Current quantity of the item (can be negative if more removals than additions)
        """
        pass

    @abstractmethod
    def get_pantry_contents(self) -> Dict[str, Dict[str, float]]:
        """
        Get the current contents of the pantry.

        Returns:
            Dict[str, Dict[str, float]]: Dictionary with item names as keys and their quantities by unit as values
        """
        pass

    @abstractmethod
    def get_transaction_history(
        self, item_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the transaction history for all items or a specific item.

        Args:
            item_name: Optional name of item to filter transactions

        Returns:
            List[Dict[str, Any]]: List of transactions with their details
        """
        pass

    # Recipe Management
    @abstractmethod
    def add_recipe(
        self,
        name: str,
        instructions: str,
        time_minutes: int,
        ingredients: List[Dict[str, Any]],
    ) -> tuple[bool, Optional[str]]:
        """
        Add a new recipe to the database.

        Args:
            name: Name of the recipe
            instructions: Cooking instructions
            time_minutes: Time required to prepare the recipe
            ingredients: List of dictionaries containing:
                - name: ingredient name
                - quantity: amount needed
                - unit: unit of measurement

        Returns:
            tuple[bool, Optional[str]]: (Success status, Recipe Short ID)
        """
        pass

    @abstractmethod
    def get_recipe(self, recipe_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a recipe and its ingredients by name.

        Args:
            recipe_name: Name of the recipe to retrieve

        Returns:
            Optional[Dict[str, Any]]: Recipe details including ingredients, or None if not found
        """
        pass

    @abstractmethod
    def get_all_recipes(self) -> List[Dict[str, Any]]:
        """
        Get all recipes from the database.

        Returns:
            List[Dict[str, Any]]: List of all recipes with their details
        """
        pass

    @abstractmethod
    def edit_recipe(
        self,
        name: str,
        instructions: str,
        time_minutes: int,
        ingredients: List[Dict[str, Any]],
    ) -> bool:
        """
        Edit an existing recipe in the database.

        Args:
            name: Name of the recipe to edit
            instructions: Updated cooking instructions
            time_minutes: Updated time required to prepare the recipe
            ingredients: Updated list of dictionaries containing:
                - name: ingredient name
                - quantity: amount needed
                - unit: unit of measurement

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def rate_recipe(self, recipe_name: str, rating: int) -> bool:
        """
        Rate a recipe on a scale of 1-5.

        Args:
            recipe_name: Name of the recipe to rate
            rating: Rating from 1 (poor) to 5 (excellent)

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def execute_recipe(self, recipe_name: str) -> tuple[bool, str]:
        """
        Execute a recipe by removing its ingredients from the pantry.

        Args:
            recipe_name: Name of the recipe to execute

        Returns:
            tuple[bool, str]: (Success status, Message with details or error)
        """
        pass

    # Short ID-based Recipe Methods
    @abstractmethod
    def get_recipe_by_short_id(self, short_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a recipe and its ingredients by short ID.

        Args:
            short_id: Short ID of the recipe (e.g., "R123A")

        Returns:
            Optional[Dict[str, Any]]: Recipe details including ingredients, or None if not found
        """
        pass

    @abstractmethod
    def get_recipe_short_id(self, recipe_name: str) -> Optional[str]:
        """
        Get the short ID of a recipe by name.

        Args:
            recipe_name: Name of the recipe

        Returns:
            Optional[str]: Recipe short ID if found, None otherwise
        """
        pass

    @abstractmethod
    def edit_recipe_by_short_id(
        self,
        short_id: str,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        time_minutes: Optional[int] = None,
        ingredients: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[bool, str]:
        """
        Edit an existing recipe by short ID with detailed error messages.

        Args:
            short_id: Short ID of the recipe to edit (e.g., "R123A")
            name: New name for the recipe (optional)
            instructions: Updated cooking instructions (optional)
            time_minutes: Updated time required (optional)
            ingredients: Updated list of ingredient dictionaries (optional)

        Returns:
            tuple[bool, str]: (Success status, detailed message)
        """
        pass

    # Meal Planning
    @abstractmethod
    def set_meal_plan(self, meal_date: str, recipe_name: str) -> bool:
        """
        Assign a recipe to a specific date in the MealPlan table.

        Args:
            meal_date: Date in ISO format (YYYY-MM-DD)
            recipe_name: Name of the recipe to assign

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_meal_plan(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Retrieve planned meals between two dates.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List[Dict[str, Any]]: List of planned meals with dates and recipe names
        """
        pass

    @abstractmethod
    def get_grocery_list(self) -> List[Dict[str, Any]]:
        """
        Calculate grocery items needed for the coming week's meal plan.

        Returns:
            List[Dict[str, Any]]: List of items needed with quantities
        """
        pass

    # Household Characteristics
    @abstractmethod
    def get_household_characteristics(self) -> Dict[str, Any]:
        """
        Get household characteristics including number of adults and children.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - adults: number of adults in household
                - children: number of children in household
                - notes: additional notes about household
                - updated_date: last update date
        """
        pass

    @abstractmethod
    def set_household_characteristics(
        self, adults: int, children: int, notes: str = ""
    ) -> bool:
        """
        Set household characteristics.

        Args:
            adults: Number of adults in household (minimum 1)
            children: Number of children in household (minimum 0)
            notes: Additional notes about household characteristics

        Returns:
            bool: True if successful, False otherwise
        """
        pass

"""
Common error handling utilities to reduce code duplication.
"""

import logging
import functools
from typing import Optional, Callable, Any, Union

logger = logging.getLogger(__name__)


def safe_execute(
    operation_name: str,
    default_return: Any = False,
    log_errors: bool = True,
    raise_on_error: bool = False,
    raise_validation_errors: bool = True,
):
    """
    Decorator for safe execution of operations with standardized error handling.

    Args:
        operation_name: Human-readable name of the operation for logging
        default_return: Value to return if operation fails (default: False)
        log_errors: Whether to log errors (default: True)
        raise_on_error: Whether to re-raise exceptions (default: False)
        raise_validation_errors: Whether to re-raise ValueError exceptions (default: True)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                # Always re-raise validation errors unless explicitly disabled
                if raise_validation_errors:
                    raise
                if log_errors:
                    logger.error(f"Error in {operation_name}: {e}")
                return default_return
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {operation_name}: {e}")

                if raise_on_error:
                    raise

                return default_return

        return wrapper

    return decorator


def handle_database_error(operation_name: str, error: Exception) -> bool:
    """
    Standardized database error handling.

    Args:
        operation_name: Name of the database operation
        error: The exception that occurred

    Returns:
        bool: False (indicating operation failure)
    """
    logger.error(f"Database error in {operation_name}: {error}")
    return False


def validate_required_params(**params) -> None:
    """
    Validate that required parameters are not None or empty.

    Args:
        **params: Named parameters to validate

    Raises:
        ValueError: If any parameter is None or empty string
    """
    for name, value in params.items():
        if value is None:
            raise ValueError(f"Parameter '{name}' is required")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"Parameter '{name}' cannot be empty")


def safe_int_conversion(
    value: Any,
    default: int = 0,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
) -> int:
    """
    Safely convert a value to integer with bounds checking.

    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        int: Converted and validated integer
    """
    try:
        result = int(value)

        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default

        return result
    except (ValueError, TypeError):
        return default


def safe_float_conversion(
    value: Any,
    default: float = 0.0,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> float:
    """
    Safely convert a value to float with bounds checking.

    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        float: Converted and validated float
    """
    try:
        result = float(value)

        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default

        return result
    except (ValueError, TypeError):
        return default


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""

    pass


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass

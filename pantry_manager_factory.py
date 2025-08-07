import os
from typing import Dict, Any, Optional

from pantry_manager_abc import PantryManager
from pantry_manager_sqlite import SQLitePantryManager


# Lazy import PostgreSQL to avoid dependency issues
class PantryManagerFactory:
    """
    Factory class for creating PantryManager instances.

    Note: PostgreSQL multi-user scenarios use SharedPantryManager directly.
    This factory only supports SQLite for single-user local mode.
    """

    _backends = {
        "sqlite": SQLitePantryManager,
    }

    @classmethod
    def create(
        self, backend: str = None, connection_string: str = None, **kwargs
    ) -> PantryManager:
        """
        Create a PantryManager instance for single-user local mode.

        Args:
            backend: Backend type. Only 'sqlite' is supported.
                    If None, determined from environment (defaults to 'sqlite')
            connection_string: Database connection string
            **kwargs: Additional configuration options

        Returns:
            PantryManager: Configured pantry manager instance

        Raises:
            ValueError: If backend is unsupported or configuration is invalid
        """
        # Determine backend from environment or connection string
        if backend is None:
            backend = os.getenv("PANTRY_BACKEND", "sqlite").lower()

        # Validate that PostgreSQL is not requested through factory
        if backend in ("postgresql", "postgres"):
            raise ValueError(
                "PostgreSQL backend is not supported through factory. "
                "Use SharedPantryManager directly for multi-user PostgreSQL scenarios."
            )

        # Auto-detect backend from connection string
        if connection_string and connection_string.startswith(
            ("postgresql://", "postgres://")
        ):
            raise ValueError(
                "PostgreSQL connection strings not supported through factory. "
                "Use SharedPantryManager directly for multi-user PostgreSQL scenarios."
            )

        # Set default connection string
        if connection_string is None:
            connection_string = os.getenv("PANTRY_DB_PATH", "pantry.db")

        # Get backend class
        if backend not in self._backends:
            raise ValueError(
                f"Unsupported backend: {backend}. "
                f"Supported backends: {list(self._backends.keys())}"
            )

        backend_class = self._backends[backend]

        # Create and return instance
        return backend_class(connection_string, **kwargs)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> PantryManager:
        """
        Create a PantryManager from a configuration dictionary for single-user local mode.

        Args:
            config: Configuration dictionary with keys:
                - backend: Backend type (only 'sqlite' supported)
                - connection_string: Database connection
                - Additional backend-specific options

        Returns:
            PantryManager: Configured pantry manager instance
        """
        backend = config.get("backend")
        connection_string = config.get("connection_string")

        # Remove factory-specific keys from kwargs
        kwargs = {
            k: v for k, v in config.items() if k not in ("backend", "connection_string")
        }

        return cls.create(backend, connection_string, **kwargs)

    @classmethod
    def from_environment(cls) -> PantryManager:
        """
        Create a PantryManager from environment variables for single-user local mode.

        Environment variables:
        - PANTRY_BACKEND: Backend type (only 'sqlite' supported, default: 'sqlite')
        - PANTRY_DB_PATH: SQLite database path (default: 'pantry.db')

        Returns:
            PantryManager: Configured pantry manager instance
        """
        return cls.create()

    @classmethod
    def list_backends(cls) -> list[str]:
        """Get list of supported backend names."""
        return list(cls._backends.keys())


# Convenience functions
def create_pantry_manager(
    backend: str = None, connection_string: str = None, **kwargs
) -> PantryManager:
    """
    Convenience function to create a PantryManager instance for single-user local mode.

    See PantryManagerFactory.create() for parameter details.
    """
    return PantryManagerFactory.create(backend, connection_string, **kwargs)


def create_pantry_manager_from_url(url: str, **kwargs) -> PantryManager:
    """
    Create a PantryManager from a database URL for single-user local mode.

    Args:
        url: Database URL (only SQLite supported, e.g., 'sqlite:///path/to/db.sqlite')
        **kwargs: Additional configuration options

    Returns:
        PantryManager: Configured pantry manager instance

    Raises:
        ValueError: If PostgreSQL URL is provided
    """
    if url.startswith("sqlite://"):
        # Remove sqlite:// prefix
        path = url[9:] if url.startswith("sqlite:///") else url[7:]
        return PantryManagerFactory.create("sqlite", path, **kwargs)
    elif url.startswith(("postgresql://", "postgres://")):
        raise ValueError(
            "PostgreSQL URLs not supported through factory. "
            "Use SharedPantryManager directly for multi-user PostgreSQL scenarios."
        )
    else:
        # Assume it's a file path for SQLite
        return PantryManagerFactory.create("sqlite", url, **kwargs)

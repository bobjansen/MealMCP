import os
from typing import Dict, Any, Optional

from pantry_manager_abc import PantryManager
from pantry_manager_sqlite import SQLitePantryManager


# Lazy import PostgreSQL to avoid dependency issues
def _get_postgresql_manager():
    """Lazy import PostgreSQL manager to avoid dependency issues."""
    try:
        from pantry_manager_postgresql import PostgreSQLPantryManager

        return PostgreSQLPantryManager
    except ImportError as e:
        raise ImportError(
            "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
        ) from e


class PantryManagerFactory:
    """Factory class for creating PantryManager instances."""

    _backends = {
        "sqlite": SQLitePantryManager,
        "postgresql": _get_postgresql_manager,
        "postgres": _get_postgresql_manager,  # Alias
    }

    @classmethod
    def create(
        self, backend: str = None, connection_string: str = None, **kwargs
    ) -> PantryManager:
        """
        Create a PantryManager instance based on configuration.

        Args:
            backend: Backend type ('sqlite', 'postgresql').
                    If None, determined from environment or connection_string
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

        # Auto-detect backend from connection string
        if connection_string and backend == "sqlite":
            if connection_string.startswith(("postgresql://", "postgres://")):
                backend = "postgresql"

        # Set default connection string
        if connection_string is None:
            if backend == "sqlite":
                connection_string = os.getenv("PANTRY_DB_PATH", "pantry.db")
            elif backend in ("postgresql", "postgres"):
                connection_string = os.getenv(
                    "PANTRY_DATABASE_URL", "postgresql://localhost/mealmcp"
                )

        # Get backend class
        if backend not in self._backends:
            raise ValueError(
                f"Unsupported backend: {backend}. "
                f"Supported backends: {list(self._backends.keys())}"
            )

        backend_class = self._backends[backend]
        if callable(backend_class) and not isinstance(backend_class, type):
            # Handle lazy imports
            backend_class = backend_class()

        # Create and return instance
        return backend_class(connection_string, **kwargs)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> PantryManager:
        """
        Create a PantryManager from a configuration dictionary.

        Args:
            config: Configuration dictionary with keys:
                - backend: Backend type
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
        Create a PantryManager from environment variables.

        Environment variables:
        - PANTRY_BACKEND: Backend type ('sqlite', 'postgresql')
        - PANTRY_DB_PATH: SQLite database path (default: 'pantry.db')
        - PANTRY_DATABASE_URL: PostgreSQL connection URL

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
    Convenience function to create a PantryManager instance.

    See PantryManagerFactory.create() for parameter details.
    """
    return PantryManagerFactory.create(backend, connection_string, **kwargs)


def create_pantry_manager_from_url(url: str, **kwargs) -> PantryManager:
    """
    Create a PantryManager from a database URL.

    Args:
        url: Database URL (e.g., 'sqlite:///path/to/db.sqlite' or 'postgresql://...')
        **kwargs: Additional configuration options

    Returns:
        PantryManager: Configured pantry manager instance
    """
    if url.startswith("sqlite://"):
        # Remove sqlite:// prefix
        path = url[9:] if url.startswith("sqlite:///") else url[7:]
        return PantryManagerFactory.create("sqlite", path, **kwargs)
    elif url.startswith(("postgresql://", "postgres://")):
        return PantryManagerFactory.create("postgresql", url, **kwargs)
    else:
        # Assume it's a file path for SQLite
        return PantryManagerFactory.create("sqlite", url, **kwargs)

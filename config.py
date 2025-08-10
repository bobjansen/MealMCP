"""
Centralized configuration management for MealMCP.
Consolidates all environment variable access and default values.
"""

import os
from typing import Optional
from error_utils import safe_int_conversion, safe_float_conversion


def get_env_str(key: str, default: str = "") -> str:
    """Get environment variable as string."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    return safe_int_conversion(os.getenv(key), default=default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default


# Configuration getters (evaluated at runtime)
def get_transport() -> str:
    """Get MCP transport mode."""
    return get_env_str("MCP_TRANSPORT", "fastmcp").lower()


def get_mode() -> str:
    """Get MCP mode."""
    return get_env_str("MCP_MODE", "local").lower()


def get_host() -> str:
    """Get MCP host."""
    return get_env_str("MCP_HOST", "localhost")


def get_port() -> int:
    """Get MCP port."""
    return safe_int_conversion(
        os.getenv("MCP_PORT"), default=8000, min_val=1, max_val=65535
    )


def get_public_url() -> str:
    """Get MCP public URL."""
    default_url = f"http://{get_host()}:{get_port()}"
    return get_env_str("MCP_PUBLIC_URL", default_url)


def get_language() -> str:
    """Get MCP language."""
    return get_env_str("MCP_LANG", "en")


def get_pantry_backend() -> str:
    """Get pantry database backend."""
    return get_env_str("PANTRY_BACKEND", "sqlite").lower()


def get_pantry_db_path() -> str:
    """Get pantry database path."""
    return get_env_str("PANTRY_DB_PATH", "pantry.db")


def get_pantry_database_url() -> Optional[str]:
    """Get pantry database URL."""
    return os.getenv("PANTRY_DATABASE_URL")


def get_pantry_db_strategy() -> str:
    """Get pantry database strategy."""
    return get_env_str("PANTRY_DB_STRATEGY", "shared")


def get_flask_secret_key() -> Optional[str]:
    """Get Flask secret key."""
    return os.getenv("FLASK_SECRET_KEY")


def get_oauth_token_expiry() -> int:
    """Get OAuth token expiry in seconds."""
    return safe_int_conversion(
        os.getenv("OAUTH_TOKEN_EXPIRY"),
        default=3600,
        min_val=60,  # At least 1 minute
        max_val=86400 * 30,  # At most 30 days
    )


def get_admin_token() -> Optional[str]:
    """Get admin token."""
    return os.getenv("ADMIN_TOKEN")


def get_database_config() -> dict:
    """Get database configuration based on backend type."""
    backend = get_pantry_backend()
    config = {"backend": backend, "strategy": get_pantry_db_strategy()}

    if backend == "postgresql":
        database_url = get_pantry_database_url()
        if not database_url:
            raise ValueError("PANTRY_DATABASE_URL required for PostgreSQL backend")
        config["connection_string"] = database_url
    else:
        config["connection_string"] = get_pantry_db_path()

    return config


def get_server_config() -> dict:
    """Get server configuration."""
    return {
        "transport": get_transport(),
        "mode": get_mode(),
        "host": get_host(),
        "port": get_port(),
        "public_url": get_public_url(),
        "language": get_language(),
    }


def get_oauth_config() -> dict:
    """Get OAuth configuration."""
    return {
        "token_expiry": get_oauth_token_expiry(),
        "admin_token": get_admin_token(),
        "public_url": get_public_url(),
    }


def is_postgresql() -> bool:
    """Check if using PostgreSQL backend."""
    return get_pantry_backend() == "postgresql"


def is_multiuser_mode() -> bool:
    """Check if running in multi-user mode."""
    return get_mode() in ("remote", "multiuser", "oauth")


def validate_config() -> list:
    """Validate configuration and return list of issues."""
    issues = []

    # Database validation
    if is_postgresql() and not get_pantry_database_url():
        issues.append("PANTRY_DATABASE_URL required for PostgreSQL backend")

    # Multi-user validation
    if is_multiuser_mode() and not get_admin_token():
        issues.append("ADMIN_TOKEN required for multi-user mode")

    # Port validation
    port = get_port()
    if port < 1 or port > 65535:
        issues.append(f"Invalid MCP_PORT: {port}")

    # Transport validation
    transport = get_transport()
    if transport not in ("fastmcp", "http", "sse", "oauth"):
        issues.append(f"Invalid MCP_TRANSPORT: {transport}")

    # Mode validation
    mode = get_mode()
    if mode not in ("local", "remote", "multiuser", "oauth"):
        issues.append(f"Invalid MCP_MODE: {mode}")

    return issues

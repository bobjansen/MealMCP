"""MCP Core Templates."""

from .oauth_templates import (
    generate_login_form,
    generate_register_form,
    generate_error_page,
)

__all__ = ["generate_login_form", "generate_register_form", "generate_error_page"]

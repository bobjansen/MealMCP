"""Authentication, session handling, and per-request user context for the web app.

This centralizes what used to be a handful of module-level helpers and closures in
``app_flask``:

* :func:`configure_session` - session cookie hardening.
* :class:`AuthContext` - resolves the current user, builds a user/household-scoped
  :class:`SharedPantryManager`, and provides the ``requires_auth`` decorator plus
  login/logout helpers.

Behavior is unchanged from the previous inline implementation; only the
``SESSION_COOKIE_*`` defaults are new (and ``SESSION_COOKIE_SECURE`` stays opt-in
so plain-HTTP local development keeps working).
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import flash, redirect, session, url_for

from config import get_env_bool
from i18n import set_lang
from pantry_manager_shared import SharedPantryManager

logger = logging.getLogger("app_flask")


def configure_session(app) -> None:
    """Apply session-cookie hardening to a Flask app."""
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault(
        "SESSION_COOKIE_SECURE", get_env_bool("SESSION_COOKIE_SECURE", False)
    )


class AuthContext:
    """Per-deployment authentication/session context."""

    def __init__(
        self,
        backend: str,
        auth_manager,
        connection_string: str,
        local_pantry,
    ):
        self.backend = backend
        self.auth_manager = auth_manager
        self.connection_string = connection_string
        self._local_pantry = local_pantry

    @property
    def is_multiuser(self) -> bool:
        return self.backend == "postgresql"

    # -- user lookup ---------------------------------------------------------
    def get_user(self, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Return the user record for ``user_id`` (or the session user)."""
        if not self.is_multiuser:
            return {"id": 1, "username": "local_user"}

        uid = user_id if user_id is not None else session.get("user_id")
        if uid is None:
            return None
        try:
            user_info = self.auth_manager.get_user_by_id(uid)
            if not user_info:
                logger.warning("User ID %s not found in database (stale session)", uid)
            return user_info
        except Exception as e:  # pragma: no cover - defensive
            logger.error("Database error getting user %s: %s", uid, e)
            return None

    def current_pantry(self):
        """Return a pantry manager scoped to the current user's household."""
        if not self.is_multiuser:
            set_lang(session.get("language", "en"))
            return self._local_pantry

        if "user_id" not in session:
            return None

        user_info = self.get_user()
        if not user_info:
            return None

        set_lang(user_info.get("preferred_language", "en"))
        household_id = user_info.get("household_id") or user_info["id"]
        return SharedPantryManager(
            connection_string=self.connection_string,
            user_id=household_id,
            backend="postgresql",
        )

    # -- session lifecycle -------------------------------------------------
    def login(self, user_info: Dict[str, Any]) -> None:
        session.permanent = True
        session["user_id"] = user_info["id"]
        session["username"] = user_info["username"]
        session["is_first_login"] = user_info.get("is_first_login", False)
        session["is_admin"] = user_info.get("is_admin", False)

    def logout(self) -> None:
        session.clear()

    # -- guard -----------------------------------------------------------
    def requires_auth(self, f: Callable) -> Callable:
        """Decorator enforcing an authenticated session in multi-user mode."""

        @wraps(f)
        def decorated(*args, **kwargs):
            if not self.is_multiuser:
                return f(*args, **kwargs)

            if "user_id" not in session:
                logger.info("User not authenticated, redirecting to login")
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))

            try:
                if not self.auth_manager.get_user_by_id(session["user_id"]):
                    logger.warning(
                        "User ID %s not found in database, clearing session",
                        session["user_id"],
                    )
                    session.clear()
                    flash("Your session has expired. Please log in again.", "warning")
                    return redirect(url_for("login"))
            except Exception as e:
                logger.error("Database error during authentication check: %s", e)
                flash(
                    "A database error occurred. Please try logging in again.", "error"
                )
                return redirect(url_for("login"))

            return f(*args, **kwargs)

        return decorated

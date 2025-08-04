import os
import secrets
from typing import Dict, Optional, Tuple
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from db_setup_shared import setup_shared_database


class WebUserManager:
    """Simple user management for shared database multi-user mode."""

    def __init__(self, backend: str = "sqlite", connection_string: str = None):
        """
        Initialize the user manager.

        Args:
            backend: 'sqlite' or 'postgresql'
            connection_string: Database connection string
        """
        self.backend = backend
        self.connection_string = connection_string

        if backend == "postgresql" and connection_string:
            self._init_shared_database()

    def _init_shared_database(self):
        """Initialize the shared database with user-scoped tables."""
        try:
            setup_shared_database(self.connection_string)
        except Exception as e:
            print(f"Error initializing shared database: {e}")

    def create_user(
        self, username: str, email: str, password: str, language: str = "en"
    ) -> Tuple[bool, str]:
        """Create a new user account."""
        if self.backend == "sqlite":
            return False, "User registration not available in SQLite mode"

        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if self.user_exists(username):
            return False, "Username already exists"

        if self.email_exists(email):
            return False, "Email already registered"

        # Validate language
        if language not in ["en", "nl"]:
            language = "en"

        try:
            password_hash = generate_password_hash(password)

            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (username, email, password_hash, preferred_language)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (username, email, password_hash, language),
                    )

            return True, "User created successfully"

        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def authenticate_user(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user with username and password."""
        if self.backend == "sqlite":
            # In SQLite mode, no authentication needed
            return True, {"id": 1, "username": "local_user"}

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, email, password_hash, is_active
                        FROM users WHERE username = %s
                    """,
                        (username,),
                    )

                    user = cursor.fetchone()
                    if not user:
                        return False, None

                    user_id, username, email, password_hash, is_active = user

                    if not is_active:
                        return False, None

                    if check_password_hash(password_hash, password):
                        return True, {
                            "id": user_id,
                            "username": username,
                            "email": email,
                        }
                    else:
                        return False, None

        except Exception as e:
            print(f"Authentication error: {e}")
            return False, None

    def user_exists(self, username: str) -> bool:
        """Check if username already exists."""
        if self.backend == "sqlite":
            return False

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM users WHERE username = %s", (username,)
                    )
                    return cursor.fetchone() is not None
        except:
            return False

    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        if self.backend == "sqlite":
            return False

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                    return cursor.fetchone() is not None
        except:
            return False

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        if self.backend == "sqlite":
            return {"id": 1, "username": "local_user"}

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, email, created_at, is_active, preferred_language
                        FROM users WHERE id = %s AND is_active = TRUE
                    """,
                        (user_id,),
                    )

                    user = cursor.fetchone()
                    if user:
                        return {
                            "id": user[0],
                            "username": user[1],
                            "email": user[2],
                            "created_at": user[3],
                            "is_active": user[4],
                            "preferred_language": user[5] or "en",
                        }
        except Exception as e:
            print(f"Error getting user: {e}")
        return None

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> Tuple[bool, str]:
        """Change user's password."""
        if self.backend == "sqlite":
            return False, "Password change not available in SQLite mode"

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters long"

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    # Verify old password
                    cursor.execute(
                        "SELECT password_hash FROM users WHERE id = %s", (user_id,)
                    )
                    result = cursor.fetchone()

                    if not result or not check_password_hash(result[0], old_password):
                        return False, "Current password is incorrect"

                    # Update password
                    new_password_hash = generate_password_hash(new_password)
                    cursor.execute(
                        """
                        UPDATE users SET password_hash = %s WHERE id = %s
                    """,
                        (new_password_hash, user_id),
                    )

                    return True, "Password changed successfully"

        except Exception as e:
            return False, f"Error changing password: {str(e)}"

    def get_user_language(self, user_id: int) -> str:
        """Get user's preferred language."""
        if self.backend == "sqlite":
            return "en"  # Default language for SQLite mode

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT preferred_language FROM users WHERE id = %s", (user_id,)
                    )
                    result = cursor.fetchone()
                    return result[0] if result and result[0] else "en"
        except Exception as e:
            print(f"Error getting user language: {e}")
            return "en"

    def set_user_language(self, user_id: int, language: str) -> Tuple[bool, str]:
        """Set user's preferred language."""
        if self.backend == "sqlite":
            return False, "Language preference not available in SQLite mode"

        if language not in ["en", "nl"]:
            return False, "Unsupported language. Available: en, nl"

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET preferred_language = %s WHERE id = %s",
                        (language, user_id),
                    )

                    if cursor.rowcount > 0:
                        return True, "Language preference updated successfully"
                    else:
                        return False, "User not found"

        except Exception as e:
            return False, f"Error updating language preference: {str(e)}"

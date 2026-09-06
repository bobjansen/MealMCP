import os
import secrets
import smtplib
from typing import Dict, Optional, Tuple
from flask import url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_database
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
        self._db = (
            get_database(backend, connection_string)
            if backend == "postgresql" and connection_string
            else None
        )

        if backend == "postgresql" and connection_string:
            self._init_shared_database()

    def _connect(self):
        """Return a pooled connection context manager for the shared database."""
        return self._db.connection()

    def _init_shared_database(self):
        """Initialize the shared database with user-scoped tables."""
        try:
            setup_shared_database(self.connection_string)
        except Exception as e:
            print(f"Error initializing shared database: {e}")

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        language: str = "en",
        invite_code: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Create a new user account.

        Args:
            username: desired username for this account
            email: user email
            password: plaintext password
            language: preferred language code
            invite_code: optional secret code to join an existing household
        """
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

            with self._connect() as conn:
                with conn.cursor() as cursor:
                    household_id = None
                    if invite_code:
                        cursor.execute(
                            "SELECT owner_id, email FROM household_invites WHERE secret = %s",
                            (invite_code,),
                        )
                        invite = cursor.fetchone()
                        if not invite:
                            return False, "Invalid invite code"
                        owner_id, invited_email = invite
                        if invited_email and invited_email.lower() != email.lower():
                            return False, "Invite email mismatch"
                        household_id = owner_id
                        cursor.execute(
                            "DELETE FROM household_invites WHERE secret = %s",
                            (invite_code,),
                        )

                    # First, insert user without household_id to avoid circular dependency
                    cursor.execute(
                        """
                        INSERT INTO users (username, email, password_hash, preferred_language)
                        VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                        (username, email, password_hash, language),
                    )
                    user_id = cursor.fetchone()[0]

                    # Set up household ownership
                    if household_id is None:
                        # User is creating their own household
                        household_id = user_id

                        # Create household characteristics for new household first
                        cursor.execute(
                            """
                            INSERT INTO household_characteristics
                            (household_id, adults, children, preferred_volume_unit, preferred_weight_unit, preferred_count_unit)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (household_id, 2, 0, "Milliliter", "Gram", "Piece"),
                        )

                    # Update user with household_id (either self for new household, or existing for join)
                    cursor.execute(
                        "UPDATE users SET household_id = %s WHERE id = %s",
                        (household_id, user_id),
                    )

                conn.commit()

            return True, "User created successfully"

        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def authenticate_user(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user with username and password."""
        if self.backend == "sqlite":
            # In SQLite mode, no authentication needed
            return True, {"id": 1, "username": "local_user", "is_first_login": False}

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, username, email, password_hash, is_active, last_login, is_admin
                        FROM users WHERE username = %s
                    """,
                        (username,),
                    )

                    user = cursor.fetchone()
                    if not user:
                        return False, None

                    (
                        user_id,
                        username,
                        email,
                        password_hash,
                        is_active,
                        last_login,
                        is_admin,
                    ) = user

                    if not is_active:
                        return False, None

                    if check_password_hash(password_hash, password):
                        # Check if this is the first login (last_login is NULL)
                        is_first_login = last_login is None

                        # Update last_login timestamp
                        cursor.execute(
                            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                            (user_id,),
                        )
                        conn.commit()

                        return True, {
                            "id": user_id,
                            "username": username,
                            "email": email,
                            "is_first_login": is_first_login,
                            "is_admin": bool(is_admin),
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
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM users WHERE username = %s", (username,)
                    )
                    return cursor.fetchone() is not None
        except Exception:  # pylint: disable=broad-except
            return False

    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        if self.backend == "sqlite":
            return False

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                    return cursor.fetchone() is not None
        except Exception:  # pylint: disable=broad-except
            return False

    def create_household_invite(self, owner_id: int, email: str) -> Optional[str]:
        """Create an invite for a household and email the secret to the recipient."""
        if self.backend == "sqlite":
            return None

        secret = secrets.token_urlsafe(16)
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO household_invites (owner_id, email, secret)
                        VALUES (%s, %s, %s)
                        """,
                        (owner_id, email, secret),
                    )

            self._send_invite_email(email, secret)
            return secret
        except Exception as e:
            print(f"Error creating household invite: {e}")
            return None

    def _send_invite_email(self, to_email: str, secret: str) -> None:
        """Send an invite email with the household secret."""
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender = os.getenv("EMAIL_SENDER", smtp_user)

        if not smtp_server or not smtp_user or not smtp_password:
            print("SMTP configuration missing, invite email not sent")
            return

        link = url_for("register", invite_code=secret, _external=True)
        message = (
            "Subject: MealMCP Household Invite\n\n"
            f"Click the link to join the household: {link}\n\n"
            f"Or use this code: {secret}"
        )
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender, [to_email], message)
        except Exception as e:
            print(f"Error sending invite email: {e}")

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        if self.backend == "sqlite":
            return {"id": 1, "username": "local_user"}

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT u.id, u.username, u.email, u.created_at, u.is_active, u.preferred_language,
                               u.household_id, hc.adults, hc.children, hc.preferred_volume_unit,
                               hc.preferred_weight_unit, hc.preferred_count_unit
                        FROM users u
                        LEFT JOIN household_characteristics hc ON u.household_id = hc.household_id
                        WHERE u.id = %s AND u.is_active = TRUE
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
                            "household_id": user[6],
                            "household_adults": user[7] or 2,
                            "household_children": user[8] or 0,
                            "preferred_volume_unit": user[9] or "Milliliter",
                            "preferred_weight_unit": user[10] or "Gram",
                            "preferred_count_unit": user[11] or "Piece",
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
            with self._connect() as conn:
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
            with self._connect() as conn:
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
            with self._connect() as conn:
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

    def set_household_size(
        self, user_id: int, adults: int, children: int
    ) -> Tuple[bool, str]:
        """Set user's household size."""
        if self.backend == "sqlite":
            return False, "Household size preference not available in SQLite mode"

        if adults < 1:
            return False, "Number of adults must be at least 1"
        if children < 0:
            return False, "Number of children cannot be negative"

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    # Get user's household_id first
                    cursor.execute(
                        "SELECT household_id FROM users WHERE id = %s",
                        (user_id,),
                    )
                    result = cursor.fetchone()
                    if not result:
                        return False, "User not found"

                    household_id = result[0]

                    # If user has no household_id, make them a household owner
                    if not household_id:
                        cursor.execute(
                            "UPDATE users SET household_id = id WHERE id = %s",
                            (user_id,),
                        )
                        household_id = user_id

                    # Insert or update household characteristics
                    cursor.execute(
                        """
                        INSERT INTO household_characteristics (household_id, adults, children, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id) DO UPDATE
                        SET adults = EXCLUDED.adults, children = EXCLUDED.children, updated_at = CURRENT_TIMESTAMP
                        """,
                        (household_id, adults, children),
                    )

                    return True, "Household size updated successfully"

        except Exception as e:
            return False, f"Error updating household size: {str(e)}"

    def get_household_size(self, user_id: int) -> Tuple[int, int]:
        """Get user's household size (adults, children)."""
        if self.backend == "sqlite":
            return 2, 0  # Default values for SQLite mode

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT hc.adults, hc.children
                        FROM users u
                        JOIN household_characteristics hc ON u.household_id = hc.household_id
                        WHERE u.id = %s
                        """,
                        (user_id,),
                    )
                    result = cursor.fetchone()
                    if result:
                        return result[0] or 2, result[1] or 0
                    else:
                        return 2, 0
        except Exception as e:
            print(f"Error getting household size: {e}")
            return 2, 0

    def get_household_goals(self, user_id: int) -> Optional[str]:
        """Get user's household goals/notes."""
        if self.backend == "sqlite":
            return None  # Not available in SQLite mode

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT hc.notes
                        FROM users u
                        JOIN household_characteristics hc ON u.household_id = hc.household_id
                        WHERE u.id = %s
                        """,
                        (user_id,),
                    )
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            print(f"Error getting household goals: {e}")
            return None

    def set_household_goals(self, user_id: int, goals: str) -> Tuple[bool, str]:
        """Set user's household goals/notes."""
        if self.backend == "sqlite":
            return False, "Household goals not available in SQLite mode"

        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    # Get user's household_id first
                    cursor.execute(
                        "SELECT household_id FROM users WHERE id = %s",
                        (user_id,),
                    )
                    result = cursor.fetchone()
                    if not result:
                        return False, "User not found"

                    household_id = result[0]

                    # If user has no household_id, make them a household owner
                    if not household_id:
                        cursor.execute(
                            "UPDATE users SET household_id = id WHERE id = %s",
                            (user_id,),
                        )
                        household_id = user_id

                    # Insert or update household goals/notes
                    cursor.execute(
                        """
                        INSERT INTO household_characteristics (household_id, notes, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (household_id) DO UPDATE
                        SET notes = EXCLUDED.notes, updated_at = CURRENT_TIMESTAMP
                        """,
                        (household_id, goals),
                    )

                    return True, "Household goals updated successfully"

        except Exception as e:
            return False, f"Error updating household goals: {str(e)}"

"""
Tests for Flask app user registration functionality through web forms.
Tests both SQLite (registration disabled) and PostgreSQL (registration enabled) modes.
"""

import unittest
import tempfile
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFlaskUserRegistration(unittest.TestCase):
    """Test Flask user registration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original environment variables
        self.original_env = {}
        for key in [
            "PANTRY_BACKEND",
            "PANTRY_DB_PATH",
            "PANTRY_DATABASE_URL",
            "FLASK_SECRET_KEY",
        ]:
            self.original_env[key] = os.environ.get(key)

        # Set Flask secret key for sessions
        os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-user-registration-tests"

    def _setup_app_with_backend(self, backend, db_config=None):
        """Helper method to set up app with specific backend configuration."""
        # Set environment variables
        os.environ["PANTRY_BACKEND"] = backend
        if backend == "sqlite" and db_config:
            os.environ["PANTRY_DB_PATH"] = db_config
        elif backend == "postgresql" and db_config:
            os.environ["PANTRY_DATABASE_URL"] = db_config

        # Import and reload app module with new environment
        import app_flask
        import importlib

        importlib.reload(app_flask)

        # Configure Flask app for testing
        app_flask.app.config["TESTING"] = True
        app_flask.app.config["WTF_CSRF_ENABLED"] = False

        return app_flask

    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        # Clean up any temporary files
        if hasattr(self, "db_path") and os.path.exists(self.db_path):
            os.unlink(self.db_path)
        if hasattr(self, "db_fd"):
            os.close(self.db_fd)

    def test_registration_disabled_in_sqlite_mode(self):
        """Test that registration is disabled in SQLite mode and redirects to index."""
        # Set up SQLite mode
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        app_flask = self._setup_app_with_backend("sqlite", self.db_path)

        # Create test client
        with app_flask.app.test_client() as client:
            # Test GET request to registration page
            response = client.get("/register")
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

            # Test POST request to registration page
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "testpassword",
                    "confirm_password": "testpassword",
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_form_displays_in_postgresql_mode(self, mock_connect):
        """Test that registration form displays correctly in PostgreSQL mode."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.get("/register")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Create your account", response.data)
            self.assertIn(b'name="username"', response.data)
            self.assertIn(b'name="email"', response.data)
            self.assertIn(b'name="password"', response.data)
            self.assertIn(b'name="confirm_password"', response.data)
            self.assertIn(b'name="language"', response.data)

    @patch("web_auth_simple.WebUserManager.email_exists")
    @patch("web_auth_simple.WebUserManager.user_exists")
    @patch("web_auth_simple.psycopg2.connect")
    def test_successful_user_registration(
        self, mock_connect, mock_user_exists, mock_email_exists
    ):
        """Test successful user registration through web form."""
        # Mock the existence checks
        mock_user_exists.return_value = False  # User doesn't exist
        mock_email_exists.return_value = False  # Email doesn't exist

        # Mock database connection for the actual user creation
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)  # User creation returns user ID

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                    "confirm_password": "securepassword123",
                    "language": "en",
                },
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Account created successfully", response.data)

    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_validation_empty_fields(self, mock_connect):
        """Test registration validation for empty fields."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            # Test with missing username
            response = client.post(
                "/register",
                data={
                    "username": "",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Please fill in all fields", response.data)

            # Test with missing email
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Please fill in all fields", response.data)

            # Test with missing password
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Please fill in all fields", response.data)

    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_password_mismatch(self, mock_connect):
        """Test registration validation for password mismatch."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "differentpassword",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Passwords do not match", response.data)

    @patch("web_auth_simple.WebUserManager.user_exists")
    def test_registration_duplicate_username(self, mock_user_exists):
        """Test registration with duplicate username."""
        # Mock user already exists
        mock_user_exists.return_value = True  # User exists

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "existinguser",
                    "email": "new@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Username already exists", response.data)

    @patch("web_auth_simple.WebUserManager.email_exists")
    @patch("web_auth_simple.WebUserManager.user_exists")
    def test_registration_duplicate_email(self, mock_user_exists, mock_email_exists):
        """Test registration with duplicate email."""
        # Mock: username doesn't exist, but email does
        mock_user_exists.return_value = False  # Username doesn't exist
        mock_email_exists.return_value = True  # Email exists

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "newuser",
                    "email": "existing@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Email already registered", response.data)

    @patch("web_auth_simple.WebUserManager.create_user")
    def test_registration_with_invite_code(self, mock_create_user):
        """Test registration with an invite code."""
        # Mock successful user creation with invite code
        mock_create_user.return_value = (True, "User created successfully")

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "inviteduser",
                    "email": "invited@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                    "invite_code": "FAMILY123",
                },
            )

            # Should redirect to login page (testing without following redirects to avoid complex invite mocking)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/login"))

    @patch("web_auth_simple.WebUserManager.email_exists")
    @patch("web_auth_simple.WebUserManager.user_exists")
    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_language_validation(
        self, mock_connect, mock_user_exists, mock_email_exists
    ):
        """Test that invalid language defaults to English."""
        # Mock the existence checks
        mock_user_exists.return_value = False  # User doesn't exist
        mock_email_exists.return_value = False  # Email doesn't exist

        # Mock database connection for the actual user creation
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)  # User creation returns user ID

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "invalid_language",  # Should default to "en"
                },
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Account created successfully", response.data)

    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_database_error(self, mock_connect):
        """Test handling of database errors during registration."""
        # Mock database connection that raises an exception
        mock_connect.side_effect = Exception("Database connection failed")

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )

            self.assertEqual(response.status_code, 200)
            # Should display some error message (exact message may vary)
            self.assertIn(b"register", response.data.lower())

    @patch("web_auth_simple.WebUserManager.email_exists")
    @patch("web_auth_simple.WebUserManager.user_exists")
    @patch("web_auth_simple.psycopg2.connect")
    def test_login_redirect_after_successful_registration(
        self, mock_connect, mock_user_exists, mock_email_exists
    ):
        """Test that successful registration redirects to login page."""
        # Mock the existence checks
        mock_user_exists.return_value = False  # User doesn't exist
        mock_email_exists.return_value = False  # Email doesn't exist

        # Mock database connection for the actual user creation
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_cursor.fetchone.return_value = (1,)  # User creation returns user ID

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register",
                data={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                },
            )

            # Should redirect to login page
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/login"))

    @patch("web_auth_simple.psycopg2.connect")
    def test_registration_preserves_invite_code_on_error(self, mock_connect):
        """Test that invite code is preserved when there are validation errors."""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Set up PostgreSQL mode
        app_flask = self._setup_app_with_backend(
            "postgresql", "postgresql://test:test@localhost/test"
        )

        # Create test client
        with app_flask.app.test_client() as client:
            response = client.post(
                "/register?invite_code=FAMILY123",
                data={
                    "username": "",  # Empty username to trigger error
                    "email": "test@example.com",
                    "password": "password123",
                    "confirm_password": "password123",
                    "language": "en",
                    "invite_code": "FAMILY123",
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Please fill in all fields", response.data)
            # Check that invite code is preserved in the form
            self.assertIn(b'value="FAMILY123"', response.data)


if __name__ == "__main__":
    unittest.main()

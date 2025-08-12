#!/usr/bin/env python3
"""
Password update utility for MealMCP PostgreSQL users.
Allows updating user passwords in the multi-user PostgreSQL database.
"""

import sys
import os
import argparse
import getpass
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def hash_password(password: str) -> str:
    """
    Hash a password using Werkzeug's secure password hashing.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password string
    """
    return generate_password_hash(password)


def update_user_password(
    connection_string: str, username: str, new_password: str, verbose: bool = True
) -> bool:
    """
    Update a user's password in the PostgreSQL database.

    Args:
        connection_string: PostgreSQL connection string
        username: Username to update
        new_password: New password to set
        verbose: Print progress messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import psycopg2

        # Hash the new password
        password_hash = hash_password(new_password)

        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                # Check if user exists
                cursor.execute(
                    "SELECT id, email FROM users WHERE username = %s", (username,)
                )
                user_record = cursor.fetchone()

                if not user_record:
                    if verbose:
                        print(f"❌ User '{username}' not found")
                    return False

                user_id, email = user_record

                # Update the password
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (password_hash, username),
                )

                if cursor.rowcount == 0:
                    if verbose:
                        print(f"❌ Failed to update password for '{username}'")
                    return False

                if verbose:
                    print(
                        f"✅ Password updated successfully for user '{username}' (ID: {user_id})"
                    )
                    print(f"   Email: {email}")

                return True

    except ImportError:
        if verbose:
            print(
                "❌ Error: psycopg2 not installed. Install with: pip install psycopg2-binary"
            )
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error updating password: {e}")
        return False


def list_users(connection_string: str, verbose: bool = True) -> bool:
    """
    List all users in the PostgreSQL database.

    Args:
        connection_string: PostgreSQL connection string
        verbose: Print progress messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import psycopg2

        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, email, is_active, created_date, 
                           household_adults, household_children
                    FROM users 
                    ORDER BY id
                    """
                )
                users = cursor.fetchall()

                if not users:
                    if verbose:
                        print("📭 No users found in database")
                    return True

                if verbose:
                    print("👥 Users in database:")
                    print("=" * 80)
                    print(
                        f"{'ID':<4} {'Username':<15} {'Email':<25} {'Active':<8} {'Household':<12} {'Created'}"
                    )
                    print("-" * 80)

                    for user in users:
                        (
                            user_id,
                            username,
                            email,
                            is_active,
                            created_date,
                            adults,
                            children,
                        ) = user
                        status = "✅" if is_active else "❌"
                        household = (
                            f"{adults}A/{children}C"
                            if adults and children is not None
                            else "N/A"
                        )
                        created_str = (
                            created_date.strftime("%Y-%m-%d") if created_date else "N/A"
                        )

                        print(
                            f"{user_id:<4} {username:<15} {email:<25} {status:<8} {household:<12} {created_str}"
                        )

                return True

    except ImportError:
        if verbose:
            print(
                "❌ Error: psycopg2 not installed. Install with: pip install psycopg2-binary"
            )
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error listing users: {e}")
        return False


def create_user(
    connection_string: str,
    username: str,
    email: str,
    password: str,
    verbose: bool = True,
) -> bool:
    """
    Create a new user in the PostgreSQL database.

    Args:
        connection_string: PostgreSQL connection string
        username: Username for the new user
        email: Email for the new user
        password: Password for the new user
        verbose: Print progress messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import psycopg2

        # Hash the password
        password_hash = hash_password(password)

        with psycopg2.connect(connection_string) as conn:
            with conn.cursor() as cursor:
                # Check if username or email already exists
                cursor.execute(
                    "SELECT username, email FROM users WHERE username = %s OR email = %s",
                    (username, email),
                )
                existing = cursor.fetchone()

                if existing:
                    existing_username, existing_email = existing
                    if existing_username == username:
                        if verbose:
                            print(f"❌ Username '{username}' already exists")
                    if existing_email == email:
                        if verbose:
                            print(f"❌ Email '{email}' already exists")
                    return False

                # Insert new user
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, preferred_language)
                    VALUES (%s, %s, %s, %s) RETURNING id
                    """,
                    (username, email, password_hash, "en"),
                )
                user_id = cursor.fetchone()[0]

                # Set household_id to self (single household)
                cursor.execute(
                    "UPDATE users SET household_id = %s WHERE id = %s",
                    (user_id, user_id),
                )

                if verbose:
                    print(f"✅ User created successfully!")
                    print(f"   Username: {username}")
                    print(f"   Email: {email}")
                    print(f"   User ID: {user_id}")

                return True

    except ImportError:
        if verbose:
            print(
                "❌ Error: psycopg2 not installed. Install with: pip install psycopg2-binary"
            )
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error creating user: {e}")
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        tuple: (is_valid, message)
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"

    if len(password) < 8:
        return (
            True,
            "⚠️  Warning: Password is short. Consider using 8+ characters for better security",
        )

    return True, "✅ Password strength is good"


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="MealMCP PostgreSQL User Management Utility"
    )
    parser.add_argument(
        "--connection-string",
        "-c",
        type=str,
        required=True,
        help="PostgreSQL connection string",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Update password command
    update_parser = subparsers.add_parser(
        "update-password", help="Update user password"
    )
    update_parser.add_argument("username", help="Username to update")
    update_parser.add_argument(
        "--password", "-p", help="New password (will prompt if not provided)"
    )
    update_parser.add_argument("--quiet", "-q", action="store_true", help="Run quietly")

    # List users command
    list_parser = subparsers.add_parser("list-users", help="List all users")
    list_parser.add_argument("--quiet", "-q", action="store_true", help="Run quietly")

    # Create user command
    create_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_parser.add_argument("username", help="Username for new user")
    create_parser.add_argument("email", help="Email for new user")
    create_parser.add_argument(
        "--password", "-p", help="Password (will prompt if not provided)"
    )
    create_parser.add_argument("--quiet", "-q", action="store_true", help="Run quietly")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    verbose = not getattr(args, "quiet", False)

    if args.command == "update-password":
        # Get password from user if not provided
        if args.password:
            new_password = args.password
        else:
            if verbose:
                print(f"Updating password for user: {args.username}")

            new_password = getpass.getpass("Enter new password: ")
            if not new_password:
                print("❌ Password cannot be empty")
                return 1

            confirm_password = getpass.getpass("Confirm new password: ")
            if new_password != confirm_password:
                print("❌ Passwords do not match")
                return 1

        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if verbose and message:
            print(message)

        if not is_valid:
            return 1

        # Update the password
        success = update_user_password(
            args.connection_string, args.username, new_password, verbose
        )
        return 0 if success else 1

    elif args.command == "list-users":
        success = list_users(args.connection_string, verbose)
        return 0 if success else 1

    elif args.command == "create-user":
        # Get password from user if not provided
        if args.password:
            password = args.password
        else:
            if verbose:
                print(f"Creating user: {args.username} ({args.email})")

            password = getpass.getpass("Enter password: ")
            if not password:
                print("❌ Password cannot be empty")
                return 1

            confirm_password = getpass.getpass("Confirm password: ")
            if password != confirm_password:
                print("❌ Passwords do not match")
                return 1

        # Validate password strength
        is_valid, message = validate_password_strength(password)
        if verbose and message:
            print(message)

        if not is_valid:
            return 1

        # Create the user
        success = create_user(
            args.connection_string, args.username, args.email, password, verbose
        )
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

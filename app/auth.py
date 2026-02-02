"""
Authentication utilities for the WPL Auction application.

Provides secure password hashing using bcrypt.
"""

import bcrypt

from app.logger import get_logger

logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password as a string.

    Example:
        >>> hashed = hash_password('my_secure_password')
        >>> verify_password('my_secure_password', hashed)
        True
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: The plaintext password to verify.
        hashed: The bcrypt hash to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def generate_password_hash_cli() -> None:
    """CLI helper to generate a password hash.

    Run from command line:
        python -c "from app.auth import generate_password_hash_cli; generate_password_hash_cli()"
    """
    import sys
    import getpass

    password = getpass.getpass("Enter password to hash: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        logger.error("Password mismatch during hash generation")
        sys.stderr.write("Error: Passwords do not match\n")
        return

    hashed = hash_password(password)
    # CLI output to stdout for user to copy the hash
    sys.stdout.write(f"\nHashed password (set as ADMIN_PASSWORD_HASH env var):\n{hashed}\n")

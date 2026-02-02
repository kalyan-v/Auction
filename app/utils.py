"""
Utility functions for the WPL Auction application.

Contains input validation, error handling, and common helper functions
used across the application.
"""

from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from flask import jsonify, request, session
from zoneinfo import ZoneInfo

from app.constants import DEFAULT_TIMEZONE

# Type variable for generic function decoration
F = TypeVar('F', bound=Callable[..., Any])


# ==================== TIMEZONE UTILITIES ====================

PACIFIC_TZ = ZoneInfo(DEFAULT_TIMEZONE)


def get_pacific_time() -> datetime:
    """Get current time in Pacific timezone."""
    return datetime.now(PACIFIC_TZ)


def to_pacific(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert datetime to Pacific time.

    Args:
        dt: Datetime to convert (can be None)

    Returns:
        Converted datetime or None if input is None
    """
    if dt is None:
        return None
    # If naive datetime, assume it's UTC and convert
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(PACIFIC_TZ)


# ==================== RESPONSE HELPERS ====================

def success_response(
    data: Optional[Dict[str, Any]] = None,
    message: Optional[str] = None,
    **kwargs: Any
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized success response.

    Args:
        data: Optional data dictionary to include
        message: Optional success message
        **kwargs: Additional key-value pairs to include

    Returns:
        Tuple of (response dict, status code)
    """
    response = {'success': True}
    if message:
        response['message'] = message
    if data:
        response.update(data)
    response.update(kwargs)
    return jsonify(response), 200


def error_response(
    error: str,
    status_code: int = 400,
    **kwargs: Any
) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response.

    Args:
        error: Error message
        status_code: HTTP status code (default: 400)
        **kwargs: Additional key-value pairs to include

    Returns:
        Tuple of (response dict, status code)
    """
    response = {'success': False, 'error': error}
    response.update(kwargs)
    return jsonify(response), status_code


# ==================== AUTHENTICATION HELPERS ====================

def is_admin() -> bool:
    """Check if current user is logged in as admin."""
    return session.get('is_admin', False)


def admin_required(f: F) -> F:
    """
    Decorator to check if user is logged in as admin.

    Returns 403 error if not authenticated as admin.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not is_admin():
            return error_response('Admin login required', 403)
        return f(*args, **kwargs)
    return decorated_function  # type: ignore


# ==================== INPUT VALIDATION ====================

def get_json_body() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Dict[str, Any], int]]]:
    """Get and validate JSON request body.

    Validates that the request contains a non-empty JSON body.

    Returns:
        Tuple of (data dict, None) on success, or (None, error_response) on failure.

    Example:
        data, error = get_json_body()
        if error:
            return error
        # Use data safely here
    """
    data = request.get_json()
    if not data:
        return None, error_response('Request body is required')
    return data, None


def get_json_with_fields(
    required_fields: List[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Dict[str, Any], int]]]:
    """Get JSON body and validate required fields.

    Validates that the request contains a non-empty JSON body with all
    required fields present.

    Args:
        required_fields: List of field names that must be present.

    Returns:
        Tuple of (data dict, None) on success, or (None, error_response) on failure.

    Example:
        data, error = get_json_with_fields(['player_id', 'amount'])
        if error:
            return error
        # Use data safely here
    """
    data, error = get_json_body()
    if error:
        return None, error

    missing = [f for f in required_fields if f not in data or data[f] is None]
    if missing:
        return None, error_response(f"Missing required fields: {', '.join(missing)}")

    return data, None


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str]
) -> Optional[str]:
    """
    Validate that required fields are present in data.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names

    Returns:
        Error message if validation fails, None otherwise
    """
    missing = [f for f in required_fields if f not in data or data[f] is None]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


def validate_positive_int(
    value: Any,
    field_name: str,
    allow_zero: bool = False
) -> Tuple[Optional[int], Optional[str]]:
    """
    Validate and convert value to positive integer.

    Args:
        value: Value to validate
        field_name: Name of field for error message
        allow_zero: Whether to allow zero value

    Returns:
        Tuple of (converted value or None, error message or None)
    """
    try:
        int_value = int(value)
        if allow_zero:
            if int_value < 0:
                return None, f"{field_name} must be non-negative"
        else:
            if int_value <= 0:
                return None, f"{field_name} must be positive"
        return int_value, None
    except (TypeError, ValueError):
        return None, f"{field_name} must be a valid integer"


def validate_positive_float(
    value: Any,
    field_name: str,
    allow_zero: bool = False
) -> Tuple[Optional[float], Optional[str]]:
    """
    Validate and convert value to positive float.

    Args:
        value: Value to validate
        field_name: Name of field for error message
        allow_zero: Whether to allow zero value

    Returns:
        Tuple of (converted value or None, error message or None)
    """
    try:
        float_value = float(value)
        if allow_zero:
            if float_value < 0:
                return None, f"{field_name} must be non-negative"
        else:
            if float_value <= 0:
                return None, f"{field_name} must be positive"
        return float_value, None
    except (TypeError, ValueError):
        return None, f"{field_name} must be a valid number"


def validate_url(url: str) -> bool:
    """
    Validate URL format for safe image sources.

    SECURITY: Validates URLs to prevent SSRF attacks by:
    - Only allowing local static paths
    - Only allowing external URLs from trusted domains

    Accepts:
    - Local static paths starting with /static/
    - HTTPS URLs from trusted image sources

    Args:
        url: URL string to validate

    Returns:
        True if valid and safe, False otherwise
    """
    if not url:
        return False
    url = url.strip()

    # Allow local static paths only (not arbitrary paths)
    if url.startswith('/static/'):
        return True

    # Validate external URLs against allowlist
    if url.startswith('https://'):
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # Allowlist of trusted domains for player images
        TRUSTED_DOMAINS = {
            'upload.wikimedia.org',
            'documents.iplt20.com',
            'scores.iplt20.com',
            'www.wplt20.com',
            'bcciplayerimages.s3.ap-south-1.amazonaws.com',
        }

        return parsed.netloc in TRUSTED_DOMAINS

    # Reject http:// (insecure) and other schemes
    return False


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int, handling dashes and empty values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Converted integer or default
    """
    if value is None or value == '' or value == '-':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float, handling dashes and empty values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Converted float or default
    """
    if value is None or value == '' or value == '-':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ==================== STRING UTILITIES ====================

def normalize_player_name(name: str) -> str:
    """
    Normalize a player name for comparison.

    Removes periods, extra spaces, and converts to lowercase.

    Args:
        name: Player name to normalize

    Returns:
        Normalized name
    """
    if not name:
        return ''
    return name.lower().replace('.', '').replace('  ', ' ').strip()


def create_safe_filename(name: str) -> str:
    """
    Create a safe filename from a string.

    Replaces non-alphanumeric characters with underscores.

    Args:
        name: String to convert

    Returns:
        Safe filename string
    """
    return "".join(c if c.isalnum() else "_" for c in name.lower().strip())

"""
Centralized error handling for the application.

Provides Flask error handlers and utility functions for consistent
error responses across the application.
"""

from flask import Flask, jsonify

from app.logger import get_logger
from app.services.base import ServiceError

logger = get_logger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register centralized error handlers with the Flask app.

    Args:
        app: Flask application instance.
    """

    @app.errorhandler(ServiceError)
    def handle_service_error(error: ServiceError):
        """Handle ServiceError exceptions (including subclasses).

        Returns JSON error response with appropriate status code.
        """
        logger.warning("Service error: %s", error.message)
        return jsonify({
            'success': False,
            'error': error.message
        }), error.status_code

    # Data-driven HTTP error handlers
    _HTTP_ERRORS = {
        400: 'Bad request',
        403: 'Access forbidden',
        404: 'Resource not found',
        405: 'Method not allowed',
        429: 'Too many requests. Please try again later.',
    }

    for _code, _message in _HTTP_ERRORS.items():
        app.register_error_handler(
            _code,
            lambda error, msg=_message, c=_code: (jsonify({'success': False, 'error': msg}), c)
        )

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server errors.

        Logs the error and returns a generic message to avoid
        exposing internal details.
        """
        logger.error("Internal server error: %s", error, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An internal error occurred'
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected exceptions.

        Catches any unhandled exceptions and returns a 500 response.
        """
        logger.error("Unexpected error: %s", error, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

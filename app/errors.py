"""
Centralized error handling for the application.

Provides Flask error handlers and utility functions for consistent
error responses across the application.
"""

from flask import Flask, jsonify

from app.logger import get_logger
from app.services.base import NotFoundError, ServiceError, ValidationError

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
        logger.warning(f"Service error: {error.message}")
        return jsonify({
            'success': False,
            'error': error.message
        }), error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Handle validation errors.

        Returns JSON error response with 400 status.
        """
        logger.warning(f"Validation error: {error.message}")
        return jsonify({
            'success': False,
            'error': error.message
        }), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error: NotFoundError):
        """Handle not found errors.

        Returns JSON error response with 404 status.
        """
        logger.warning(f"Not found: {error.message}")
        return jsonify({
            'success': False,
            'error': error.message
        }), 404

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors."""
        return jsonify({
            'success': False,
            'error': 'Bad request'
        }), 400

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors."""
        return jsonify({
            'success': False,
            'error': 'Access forbidden'
        }), 403

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            'success': False,
            'error': 'Resource not found'
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        return jsonify({
            'success': False,
            'error': 'Method not allowed'
        }), 405

    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle 429 Too Many Requests errors."""
        return jsonify({
            'success': False,
            'error': 'Too many requests. Please try again later.'
        }), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server errors.

        Logs the error and returns a generic message to avoid
        exposing internal details.
        """
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An internal error occurred'
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected exceptions.

        Catches any unhandled exceptions and returns a 500 response.
        """
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

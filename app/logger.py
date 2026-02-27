"""
Centralized logging configuration for the WPL Auction application.

Provides consistent logging across all modules with proper formatting
and configurable log levels. Supports structured JSON logging for production.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Check if running in production for JSON logging
USE_JSON_LOGGING = os.environ.get('FLASK_CONFIG') == 'production'


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production.

    Outputs logs in JSON format suitable for log aggregation tools
    like ELK Stack, CloudWatch, or Datadog.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            JSON string representation of the log.
        """
        log_data: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }

        # Add request context if available
        try:
            from flask import g, request
            if hasattr(g, 'request_id'):
                log_data['request_id'] = g.request_id
            if request:
                log_data['path'] = request.path
                log_data['method'] = request.method
        except (RuntimeError, ImportError):
            # Outside request context
            pass

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if any
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class RequestContextFilter(logging.Filter):
    """Filter that adds request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to the log record if available.

        Args:
            record: The log record.

        Returns:
            True to include the record.
        """
        try:
            from flask import g
            record.request_id = getattr(g, 'request_id', '-')
        except (RuntimeError, ImportError):
            record.request_id = '-'
        return True


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None,
    use_json: Optional[bool] = None
) -> logging.Logger:
    """
    Set up and return a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: INFO)
        log_format: Custom format string (optional)
        use_json: Force JSON formatting (default: auto-detect from environment)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Add request context filter
    logger.addFilter(RequestContextFilter())

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Determine formatter based on environment
    should_use_json = use_json if use_json is not None else USE_JSON_LOGGING

    if should_use_json:
        formatter = JSONFormatter()
    else:
        if log_format is None:
            log_format = '[%(asctime)s] %(levelname)s [%(request_id)s] %(module)s: %(message)s'
        formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for the given name.

    This is the primary function to use when getting a logger in application code.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Logger instance

    Example:
        from app.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.error("Something went wrong", exc_info=True)
    """
    return setup_logger(name)

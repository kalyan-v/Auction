"""
Centralized logging configuration for the WPL Auction application.

Provides consistent logging across all modules with proper formatting
and configurable log levels.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up and return a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ of the calling module)
        level: Logging level (default: INFO)
        log_format: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Create formatter
    if log_format is None:
        log_format = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'

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


# Pre-configured loggers for common modules
def get_api_logger() -> logging.Logger:
    """Get logger for API/route operations."""
    return get_logger('app.api')


def get_cricket_logger() -> logging.Logger:
    """Get logger for cricket data scraping operations."""
    return get_logger('app.cricket')


def get_fantasy_logger() -> logging.Logger:
    """Get logger for fantasy points calculations."""
    return get_logger('app.fantasy')


def get_db_logger() -> logging.Logger:
    """Get logger for database operations."""
    return get_logger('app.db')

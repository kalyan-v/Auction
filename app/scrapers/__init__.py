"""
Scrapers package for cricket league data.

Provides a unified interface for scraping different cricket leagues.
Currently supports WPL, with architecture ready for IPL, BBL, etc.

Usage:
    from app.scrapers import get_scraper, ScraperType

    # Get the WPL scraper
    scraper = get_scraper(ScraperType.WPL)
    orange_cap = scraper.get_orange_cap()

    # Or use the default (currently WPL)
    scraper = get_scraper()
"""

from typing import Optional, Type

from app.enums import LeagueType
from app.scrapers.base import BaseScraper
from app.scrapers.wpl import WPLScraper

# Alias for cleaner imports
ScraperType = LeagueType

# Registry of available scrapers
_SCRAPER_REGISTRY: dict[LeagueType, Type[BaseScraper]] = {
    LeagueType.WPL: WPLScraper,
    # Add new scrapers here as they're implemented:
    # LeagueType.IPL: IPLScraper,
    # LeagueType.BBL: BBLScraper,
}

# Default scraper type
DEFAULT_SCRAPER_TYPE = LeagueType.WPL


def get_scraper(
    league_type: Optional[LeagueType] = None,
    **kwargs
) -> BaseScraper:
    """
    Factory function to get a scraper instance for the specified league.

    Args:
        league_type: The league to get a scraper for (defaults to WPL)
        **kwargs: Additional arguments passed to the scraper constructor

    Returns:
        BaseScraper instance for the specified league

    Raises:
        ValueError: If the league type is not supported

    Example:
        # Get WPL scraper
        wpl = get_scraper(ScraperType.WPL)

        # Get default scraper
        scraper = get_scraper()

        # Get scraper with custom series ID
        wpl_2025 = get_scraper(ScraperType.WPL, series_id="12345")
    """
    if league_type is None:
        league_type = DEFAULT_SCRAPER_TYPE

    scraper_class = _SCRAPER_REGISTRY.get(league_type)
    if scraper_class is None:
        available = ", ".join(t.value for t in _SCRAPER_REGISTRY.keys())
        raise ValueError(
            f"No scraper available for {league_type.value}. "
            f"Available: {available}"
        )

    return scraper_class(**kwargs)


def get_available_scrapers() -> list[LeagueType]:
    """
    Get list of available scraper types.

    Returns:
        List of LeagueType enums for implemented scrapers
    """
    return list(_SCRAPER_REGISTRY.keys())


def is_scraper_available(league_type: LeagueType) -> bool:
    """
    Check if a scraper is available for the given league type.

    Args:
        league_type: The league type to check

    Returns:
        True if scraper is available, False otherwise
    """
    return league_type in _SCRAPER_REGISTRY


def register_scraper(
    league_type: LeagueType,
    scraper_class: Type[BaseScraper]
) -> None:
    """
    Register a new scraper type.

    This allows dynamically adding new scrapers at runtime.

    Args:
        league_type: The league type to register
        scraper_class: The scraper class (must inherit from BaseScraper)

    Raises:
        TypeError: If scraper_class doesn't inherit from BaseScraper
    """
    if not issubclass(scraper_class, BaseScraper):
        raise TypeError(
            f"{scraper_class.__name__} must inherit from BaseScraper"
        )
    _SCRAPER_REGISTRY[league_type] = scraper_class


# Export public API
__all__ = [
    "BaseScraper",
    "WPLScraper",
    "ScraperType",
    "get_scraper",
    "get_available_scrapers",
    "is_scraper_available",
    "register_scraper",
]

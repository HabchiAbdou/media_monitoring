"""
Placeholder scraping layer.

The previous ZIP-based scraping implementation has been removed. These stubs
keep imports stable without performing any real scraping or network calls.
"""

from __future__ import annotations

from typing import Any, Dict, List


def fetch_website_articles(*, max_articles_per_site: int = 0, delay: float = 0.0) -> List[Dict[str, Any]]:
    """Return an empty list to indicate no scraped articles are available."""
    return []


def run_scraper(url: str | None = None, *, max_articles_per_site: int = 0, delay: float = 0.0) -> List[Dict[str, Any]]:
    """Entry point kept for compatibility; currently returns no data."""
    return []


def scrape(**kwargs) -> List[Dict[str, Any]]:
    return run_scraper(**kwargs)


def scrape_site(**kwargs) -> List[Dict[str, Any]]:
    return run_scraper(**kwargs)

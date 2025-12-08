"""
Placeholder ingestion glue.

Original scraping integration has been removed. This stub keeps the API surface
intact for views/URLs while performing no work.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from django.utils import timezone


def ingest_latest_articles(
    *,
    force: bool = False,
    max_articles_per_site: int = 0,
    refresh_interval_minutes: int = 0,
    urls: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Stub ingestion that, if URLs are provided, runs the standalone scraper module.
    Replace this with real DB persistence/LLM processing later.
    """
    summary: Dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "total_seen": 0,
        "last_run": timezone.now(),
    }

    if urls:
        try:
            # Lazy import to avoid hard dependency when not needed.
            from scraper.ocp_scraper import process_urls  # type: ignore

            scrape_summary = process_urls(urls)
            summary.update(
                {
                    "total_seen": scrape_summary.get("processed", 0),
                    "matched": scrape_summary.get("matched", 0),
                    "errors": scrape_summary.get("errors", 0),
                    "results": scrape_summary.get("results", []),
                }
            )
        except Exception as exc:  # noqa: BLE001
            summary["error"] = str(exc)

    return summary

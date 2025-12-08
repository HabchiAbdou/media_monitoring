"""
Lightweight OCP-focused web scraping utilities.

Pipeline (per URL):
1) fetch_html: download page HTML with requests.
2) extract_text: strip scripts/styles and return clean visible text.
3) contains_ocp_keywords: check for OCP-related terms (FR/EN/AR).
4) save_text: persist URL + text to data/ for inspection.
5) process_with_llm: placeholder hook to send text to an LLM.
6) process_url: orchestrates the above, guards failures.

To plug in a real LLM:
- Replace the body of process_with_llm with your API call (Cerebras/OpenAI/etc.).
- Keep the signature intact so integration stays simple.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from datetime import datetime
from typing import Iterable, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

OCP_KEYWORDS: tuple[str, ...] = (
    "ocp",
    "o.c.p",
    "ocp group",
    "office chérifien des phosphates",
    "office cherifien des phosphates",
    "المكتب الشريف للفوسفاط",
    "مجموعة المكتب الشريف للفوسفاط",
)

DATA_DIR = "data"


def fetch_html(url: str, timeout: float = 15.0) -> Optional[str]:
    """
    Download HTML for a URL. Returns None on failure.
    """
    try:
        logger.info("Fetching URL: %s", url)
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:

            logger.warning("Non-200 status for %s: %s", url, resp.status_code)
            return None
        resp.encoding = resp.encoding or resp.apparent_encoding or "utf-8"
        print("rentrer")
        return resp.text
    except requests.RequestException as exc:  # network/timeout/etc.
        logger.error("Request failed for %s: %s", url, exc)
        return None


def _strip_unwanted(soup: BeautifulSoup) -> None:
    """Remove script/style/noscript/etc. to keep only readable content."""
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
        tag.decompose()


def extract_text(html: str) -> str:
    """
    Extract visible text from HTML. Returns a cleaned string.
    """
    soup = BeautifulSoup(html, "html.parser")
    _strip_unwanted(soup)
    raw_text = soup.get_text(separator="\n")
    # Clean whitespace and empty lines
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _safe_filename(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_") or "page"
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"{stamp}_{host}_{digest}.txt"


def save_text(url: str, text: str) -> str:
    """
    Save URL + text into data/ directory. Returns the filepath.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = _safe_filename(url)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(url.strip())
        f.write("\n\n")
        f.write(text)
    logger.info("Saved text for %s to %s", url, path)
    return path


def contains_ocp_keywords(text: str) -> bool:
    """
    Case-insensitive substring check for OCP-related phrases.
    """
    norm = text.lower()
    for kw in OCP_KEYWORDS:
        if kw.lower() in norm:
            return True
    return False


def process_with_llm(url: str, text: str, preview_chars: int = 500) -> None:
    """
    Placeholder for LLM integration.

    Replace this body with your real API call (Cerebras, OpenAI, etc.).
    """
    logger.info("Sending content from %s to LLM for processing...", url)
    snippet = text[:preview_chars].replace("\n", " ")
    logger.debug("LLM preview (first %s chars): %s", preview_chars, snippet)
    # TODO: Plug real LLM API here.


def process_url(url: str) -> dict[str, Any]:
    """
    Full pipeline for a single URL: fetch -> extract -> save -> keyword check -> LLM hook.
    Returns a result dict with status info.
    """
    result: dict[str, Any] = {"url": url, "status": "ok", "matched": False, "saved_path": None, "error": None}

    html = fetch_html(url)
    if not html:
        logger.warning("Skipping %s due to fetch failure", url)
        result.update({"status": "error", "error": "fetch_failed"})
        return result

    text = extract_text(html)
    if not text.strip():
        logger.warning("No visible text extracted for %s", url)
        result.update({"status": "error", "error": "empty_text"})
        return result

    saved_path = save_text(url, text)
    result["saved_path"] = saved_path

    if not contains_ocp_keywords(text):
        logger.info("No OCP-related keywords found for URL: %s", url)
        return result

    result["matched"] = True
    process_with_llm(url, text)
    return result


def process_urls(urls: Iterable[str]) -> dict[str, Any]:
    """
    Iterate over URLs, running the full pipeline for each.
    Returns a summary dict with counts and per-url results.
    """
    summary: dict[str, Any] = {
        "processed": 0,
        "matched": 0,
        "errors": 0,
        "results": [],
    }

    for url in urls:
        if not url or not url.strip():
            continue
        trimmed = url.strip()
        logger.info("Processing URL: %s", trimmed)
        res = process_url(trimmed)
        summary["results"].append(res)
        summary["processed"] += 1
        if res.get("status") != "ok":
            summary["errors"] += 1
        if res.get("matched"):
            summary["matched"] += 1
        time.sleep(0.1)  # polite pause; adjust as needed

    return summary

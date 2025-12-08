"""
CLI entry point to run the OCP-focused scraper.

Usage:
    python run_scraper.py https://example.com
    python run_scraper.py https://site1.com https://site2.com
    python run_scraper.py          # will read URLs from urls.txt (one per line)

Notes:
- Uses scraper/ocp_scraper.py for the main pipeline.
- Replace process_with_llm in ocp_scraper.py to hook up a real LLM.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from ocp_scraper import process_urls

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def load_urls_from_file(file_path: Path) -> List[str]:
    if not file_path.exists():
        logging.error("No URLs provided and %s not found.", file_path)
        return []
    lines = file_path.read_text(encoding="utf-8").splitlines()
    urls = [line.strip() for line in lines if line.strip()]
    logging.info("Loaded %d URL(s) from %s", len(urls), file_path)
    return urls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OCP-focused web scraper.")
    parser.add_argument("urls", nargs="*", help="One or more URLs to scrape.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.urls:
        urls = args.urls
    else:
        urls = load_urls_from_file(Path("urls.txt"))

    if not urls:
        logging.error("No URLs to process. Provide URLs via CLI or urls.txt.")
        sys.exit(1)

    process_urls(urls)


if __name__ == "__main__":
    main()

# Example usage (uncomment to test quickly):
# if __name__ == "__main__":
#     process_urls([
#         "https://www.example.com",
#         "https://www.ocpgroup.ma",
#     ])

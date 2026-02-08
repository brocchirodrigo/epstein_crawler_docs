"""
Epstein Files Scraper - Entry Point
"""

import argparse
import sys
from src.app import run_scraper, run_scan_mode
from src.logging_config import logger


def main():
    parser = argparse.ArgumentParser(description="Epstein Files Scraper")
    parser.add_argument(
        "--search",
        action="store_true",
        help="Run in legacy search mode (iterate letters)",
    )

    args = parser.parse_args()

    pdfs = []

    if args.search:
        logger.info("🚀 Starting in SEARCH MODE (Legacy)...")
        pdfs = run_scraper()
    else:
        logger.info("🚀 Starting in SCAN MODE (DOJ Disclosures)...")
        pdfs = run_scan_mode()

    logger.info(f"\n✅ Done! Found {len(pdfs)} unique PDFs.")


if __name__ == "__main__":
    main()

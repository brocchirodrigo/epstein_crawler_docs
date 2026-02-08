"""
Epstein Files Scraper - Entry Point

Commands:
    uv run main.py          # Run scraper (default: scan mode)
    uv run main.py --search # Run scraper (legacy search mode)
    uv run main.py api      # Start the RAG API server
"""

import argparse

from src.logging_config import logger


def run_scraper_command(args):
    """Run the scraper."""
    from src.app import run_scan_mode, run_scraper

    if args.search:
        logger.info("🚀 Starting in SEARCH MODE (Legacy)...")
        pdfs = run_scraper()
    else:
        logger.info("🚀 Starting in SCAN MODE (DOJ Disclosures)...")
        pdfs = run_scan_mode()

    logger.info(f"\n✅ Done! Found {len(pdfs)} unique PDFs.")


def run_api_command():
    """Start the RAG API server."""
    from src.api import start_server

    start_server()


def main():
    parser = argparse.ArgumentParser(
        description="Epstein Files Scraper & RAG API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser.add_argument(
        "--search",
        action="store_true",
        help="Run in legacy search mode (iterate letters)",
    )

    api_parser = subparsers.add_parser("api", help="Start the RAG API server")
    api_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to run the API server on (default: 8000)",
    )

    args = parser.parse_args()

    if args.command == "api":
        run_api_command()
    else:
        run_scraper_command(args)


if __name__ == "__main__":
    main()

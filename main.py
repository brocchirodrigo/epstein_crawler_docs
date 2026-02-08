"""
Epstein Files Scraper - Entry Point
"""

from src import run_scraper, logger

if __name__ == "__main__":
    pdfs = run_scraper()
    logger.info(f"\n✅ Done! Found {len(pdfs)} unique PDFs.")

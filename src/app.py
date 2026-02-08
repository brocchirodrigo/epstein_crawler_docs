"""
Application orchestrator for the Epstein Files Scraper.
Coordinates the scraping and downloading workflow.
"""

import json
from playwright.sync_api import sync_playwright

from .config import settings, paths
from .logging_config import logger
from .scraper import (
    create_browser_context,
    pass_gates,
    collect_pdfs_for_letter,
)
from .downloader import download_all_pdfs


def run_scraper(
    letters: list = None,
    max_pages_per_letter: int = None,
    max_downloads: int = None,
    skip_download: bool = False,
) -> list:
    """
    Main scraper orchestrator.

    Args:
        letters: List of letters to search (default: from settings)
        max_pages_per_letter: Max result pages per letter (default: from settings)
        max_downloads: Max files to download (default: from settings)
        skip_download: If True, only collect links without downloading

    Returns:
        List of unique PDF info dicts
    """
    if letters is None:
        letters = settings.letters
    if max_pages_per_letter is None:
        max_pages_per_letter = settings.max_pages_per_letter
    if max_downloads is None:
        max_downloads = settings.max_downloads

    logger.info("=" * 60)
    logger.info("🔍 EPSTEIN FILES SCRAPER")
    logger.info("=" * 60)
    logger.info(f"Letters: {letters}")
    logger.info(f"Max pages/letter: {max_pages_per_letter or 'unlimited'}")
    logger.info(f"Max downloads: {max_downloads or 'unlimited'}")
    logger.info("=" * 60)

    all_pdfs = []

    with sync_playwright() as p:
        browser, context, page = create_browser_context(p)

        try:
            all_pdfs = _collect_links(page, letters, max_pages_per_letter)
            unique_pdfs = _deduplicate(all_pdfs)
            _save_json(unique_pdfs, letters, max_pages_per_letter)

            if not skip_download and unique_pdfs:
                _download_files(context, unique_pdfs, max_downloads)

        finally:
            browser.close()

    return unique_pdfs


def _collect_links(page, letters: list, max_pages: int) -> list:
    """Phase 1: Collect PDF links from all letters."""
    logger.info("\n" + "=" * 60)
    logger.info("📥 PHASE 1: LINK COLLECTION")
    logger.info("=" * 60)

    all_pdfs = []

    for i, letter in enumerate(letters):
        logger.info(f"\n{'=' * 40}")
        logger.info(f"LETTER {letter.upper()} ({i + 1}/{len(letters)})")
        logger.info(f"{'=' * 40}")

        try:
            logger.info(f"🌐 Accessing {settings.epstein_page}...")
            page.goto(
                settings.epstein_page,
                wait_until="networkidle",
                timeout=settings.navigation_timeout,
            )

            pass_gates(page)
            pdfs = collect_pdfs_for_letter(page, letter, max_pages)
            all_pdfs.extend(pdfs)

            logger.info(f"📈 Partial total: {len(all_pdfs)} PDFs")

        except Exception as e:
            logger.error(f"Failed to process letter '{letter}': {e}")
            continue

    return all_pdfs


def _deduplicate(all_pdfs: list) -> list:
    """Phase 2: Remove duplicate PDFs."""
    logger.info("\n" + "=" * 60)
    logger.info("🔄 PHASE 2: DEDUPLICATION")
    logger.info("=" * 60)

    logger.info(f"Total collected: {len(all_pdfs)}")
    unique_pdfs = list({pdf["url"]: pdf for pdf in all_pdfs}.values())
    logger.info(f"After deduplication: {len(unique_pdfs)} unique")

    return unique_pdfs


def _save_json(unique_pdfs: list, letters: list, max_pages: int) -> None:
    """Save results to JSON file."""
    result = {
        "total_files": len(unique_pdfs),
        "letters_searched": letters,
        "max_pages_per_letter": max_pages,
        "files": unique_pdfs,
    }

    with open(paths.output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 JSON saved: {paths.output_json}")


def _download_files(context, unique_pdfs: list, max_downloads: int) -> None:
    """Phase 3: Download PDF files."""
    logger.info("\n" + "=" * 60)
    logger.info(f"⬇️ PHASE 3: DOWNLOADING {len(unique_pdfs)} FILES")
    logger.info("=" * 60)

    downloaded, failed = download_all_pdfs(context, unique_pdfs, max_downloads)

    logger.info("\n" + "=" * 60)
    logger.info("📊 FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Unique PDFs identified: {len(unique_pdfs)}")
    logger.info(f"Successfully downloaded: {downloaded}")
    logger.info(f"Failed: {len(failed)}")
    logger.info(f"JSON: {paths.output_json}")
    logger.info(f"Downloads: {paths.downloads_dir}")

    if failed:
        logger.warning("Failed files:")
        for f in failed:
            logger.warning(f"  - {f}")

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
    expand_transparency_accordion,
    get_dataset_links,
    collect_pdfs_from_dataset,
)
from .downloader import download_all_pdfs, download_batch, load_downloaded_urls


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


def _load_existing_progress() -> tuple[list, set]:
    """Load existing progress from JSON file if available, or create it."""
    all_pdfs = []
    existing_urls = set()

    if paths.output_json.is_dir():
        logger.warning("⚠️ epstein_urls.json is a directory (Docker mount issue)")
        logger.warning("⚠️ Please run: rm -rf epstein_urls.json && touch epstein_urls.json")
        return all_pdfs, existing_urls

    if paths.output_json.exists():
        try:
            with open(paths.output_json, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing_data = json.loads(content)
                    all_pdfs = existing_data.get("files", [])
                    existing_urls = {pdf["url"] for pdf in all_pdfs}
                    logger.info(f"📂 Resuming: loaded {len(all_pdfs)} existing PDFs")
        except Exception as e:
            logger.warning(f"Could not load existing JSON: {e}")
    else:
        try:
            with open(paths.output_json, "w", encoding="utf-8") as f:
                json.dump({"total_files": 0, "files": []}, f)
            logger.info("📄 Created new epstein_urls.json")
        except Exception as e:
            logger.warning(f"Could not create JSON file: {e}")

    return all_pdfs, existing_urls


def _process_dataset(page, link: str, i: int, total: int, all_pdfs: list,
                     existing_urls: set, save_progress: callable) -> list:
    """Process a single dataset and return new PDFs."""
    pdfs = collect_pdfs_from_dataset(page, link, save_progress, existing_urls)

    new_pdfs = [p for p in pdfs if p["url"] not in existing_urls]
    all_pdfs.extend(new_pdfs)

    for p in new_pdfs:
        existing_urls.add(p["url"])

    unique_pdfs = list({pdf["url"]: pdf for pdf in all_pdfs}.values())
    _save_json(unique_pdfs, ["SCAN_MODE"], 0)
    logger.info(f"💾 Dataset complete: {len(unique_pdfs)} unique PDFs ({i + 1}/{total} datasets)")

    return unique_pdfs


def _navigate_to_disclosures(page) -> bool:
    """Navigate to disclosures page and pass gates."""
    logger.info(f"🌐 Accessing {settings.base_url}{settings.disclosures_path}...")
    page.goto(
        f"{settings.base_url}{settings.disclosures_path}",
        wait_until="networkidle",
        timeout=settings.navigation_timeout,
    )
    pass_gates(page)
    return expand_transparency_accordion(page)


def _process_all_datasets(page, context, all_pdfs, existing_urls, downloaded_urls, save_progress, skip_download):
    """Process all datasets with incremental downloads."""
    dataset_links = get_dataset_links(page)
    unique_pdfs = []

    for i, link in enumerate(dataset_links):
        unique_pdfs = _process_dataset(
            page, link, i, len(dataset_links),
            all_pdfs, existing_urls, save_progress
        )

        if not skip_download:
            download_batch(context, unique_pdfs, downloaded_urls)

    return unique_pdfs


def _emergency_save(all_pdfs):
    """Save progress in case of error."""
    if all_pdfs:
        unique_pdfs = list({pdf["url"]: pdf for pdf in all_pdfs}.values())
        _save_json(unique_pdfs, ["SCAN_MODE"], 0)
        logger.info(f"💾 Emergency save: {len(unique_pdfs)} unique PDFs preserved")
        return unique_pdfs
    return []


def run_scan_mode(
    max_downloads: int = None,
    skip_download: bool = False,
) -> list:
    """
    Orchestrator for the new 'Scan Mode' (DOJ Disclosures).
    Navigates to the page, expands the accordion, and collects PDFs from datasets.
    Saves progress incrementally and resumes from existing JSON if available.
    Downloads happen after each page during scraping.
    """
    if max_downloads is None:
        max_downloads = settings.max_downloads

    logger.info("=" * 60)
    logger.info("🕵️‍♂️ EPSTEIN FILES SCRAPER - SCAN MODE")
    logger.info("=" * 60)
    logger.info(f"Target: {settings.disclosures_path}")
    logger.info(f"Max downloads: {max_downloads or 'unlimited'}")
    logger.info("=" * 60)

    all_pdfs, existing_urls = _load_existing_progress()
    unique_pdfs = []
    downloaded_urls = load_downloaded_urls()
    context_holder = [None]

    def save_progress(dataset_pdfs: list):
        """Callback to save progress and download new PDFs incrementally."""
        nonlocal unique_pdfs
        new_pdfs = [p for p in dataset_pdfs if p["url"] not in existing_urls]
        temp_all = all_pdfs + new_pdfs
        unique_pdfs = list({pdf["url"]: pdf for pdf in temp_all}.values())
        _save_json(unique_pdfs, ["SCAN_MODE"], 0)
        logger.info(f"💾 Auto-save: {len(unique_pdfs)} unique PDFs")

        if not skip_download and context_holder[0]:
            download_batch(context_holder[0], unique_pdfs, downloaded_urls)

    with sync_playwright() as p:
        browser, context, page = create_browser_context(p)
        context_holder[0] = context

        try:
            if _navigate_to_disclosures(page):
                unique_pdfs = _process_all_datasets(
                    page, context, all_pdfs, existing_urls,
                    downloaded_urls, save_progress, skip_download
                )

        except Exception as e:
            logger.error(f"Scan mode failed: {e}")
            unique_pdfs = _emergency_save(all_pdfs)
        finally:
            browser.close()

    return unique_pdfs

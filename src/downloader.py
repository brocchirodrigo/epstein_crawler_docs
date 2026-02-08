"""
PDF download module for the Epstein Files Scraper.
Handles downloading PDFs using Playwright session cookies.
"""

from playwright.sync_api import BrowserContext

from .config import paths
from .logging_config import logger


def ensure_downloads_dir() -> None:
    """Creates downloads directory if it doesn't exist."""
    paths.downloads_dir.mkdir(exist_ok=True)


def download_pdf(context: BrowserContext, url: str, filename: str) -> bool:
    """
    Downloads a single PDF using the Playwright context session.
    Validates response is actually a PDF before saving.
    Returns True if download was successful.
    """
    ensure_downloads_dir()

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filepath = paths.downloads_dir / filename

    if filepath.exists():
        logger.info(f"  ⏭️ {filename} (already exists)")
        return True

    try:
        response = context.request.get(url)

        if response.status != 200:
            logger.error(f"HTTP {response.status} for {filename}")
            return False

        body = response.body()

        if body[:4] != b"%PDF":
            logger.error(f"Response is not a PDF for {filename}")
            return False

        with open(filepath, "wb") as f:
            f.write(body)

        size_kb = len(body) / 1024
        logger.info(f"  ✅ {filename} ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return False


def download_all_pdfs(
    context: BrowserContext, files: list, max_downloads: int = None
) -> tuple:
    """
    Downloads all PDFs from the files list using the Playwright session.
    Returns (downloaded_count, failed_list) tuple.
    """
    ensure_downloads_dir()

    if max_downloads:
        files = files[:max_downloads]

    total = len(files)
    downloaded = 0
    failed = []

    logger.info(f"\n{'='*60}")
    logger.info(f"⬇️ DOWNLOADING {total} FILES")
    logger.info(f"{'='*60}")

    for i, file_info in enumerate(files):
        url = file_info["url"]
        filename = file_info["filename"]

        logger.info(f"[{i+1}/{total}] {filename}")

        if download_pdf(context, url, filename):
            downloaded += 1
        else:
            failed.append(filename)

    return downloaded, failed

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


def load_downloaded_urls() -> set:
    """Load set of already downloaded URLs from downloaded.txt."""
    downloaded_file = paths.downloads_dir / "downloaded.txt"
    if not downloaded_file.exists():
        return set()

    try:
        with open(downloaded_file, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.warning(f"Could not load downloaded.txt: {e}")
        return set()


def mark_as_downloaded(url: str) -> None:
    """Append URL to downloaded.txt."""
    ensure_downloads_dir()
    downloaded_file = paths.downloads_dir / "downloaded.txt"
    try:
        with open(downloaded_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")
    except Exception as e:
        logger.warning(f"Could not write to downloaded.txt: {e}")


def load_failed_urls() -> set:
    """Load set of URLs that failed to download (404, etc)."""
    failed_file = paths.downloads_dir / "failed_downloads.txt"
    if not failed_file.exists():
        return set()

    try:
        with open(failed_file, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.warning(f"Could not load failed_downloads.txt: {e}")
        return set()


def mark_as_failed(url: str) -> None:
    """Mark URL as failed download."""
    ensure_downloads_dir()
    failed_file = paths.downloads_dir / "failed_downloads.txt"
    try:
        with open(failed_file, "a", encoding="utf-8") as f:
            f.write(url + "\n")
    except Exception as e:
        logger.warning(f"Could not write to failed_downloads.txt: {e}")


def download_pdf(context: BrowserContext, url: str, filename: str,
                 downloaded_urls: set = None, failed_urls: set = None) -> bool:
    """
    Downloads a single PDF using the Playwright context session.
    Validates response is actually a PDF before saving.
    Returns True if download was successful or should be skipped.
    """
    ensure_downloads_dir()

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filepath = paths.downloads_dir / filename

    if downloaded_urls and url in downloaded_urls:
        return True

    if failed_urls and url in failed_urls:
        return True

    if filepath.exists():
        mark_as_downloaded(url)
        return True

    try:
        response = context.request.get(url)

        if response.status == 404:
            logger.error(f"HTTP 404 for {filename}")
            mark_as_failed(url)
            if failed_urls is not None:
                failed_urls.add(url)
            return True

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
        mark_as_downloaded(url)
        return True

    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return False


def download_batch(context: BrowserContext, files: list, downloaded_urls: set) -> int:
    """
    Download a batch of PDFs incrementally.
    Skips files already in downloaded_urls or failed_urls.
    Returns number of files downloaded.
    """
    failed_urls = load_failed_urls()
    to_download = [f for f in files
                   if f["url"] not in downloaded_urls
                   and f["url"] not in failed_urls]
    if not to_download:
        return 0

    count = 0
    for file_info in to_download:
        url = file_info["url"]
        filename = file_info["filename"]

        if download_pdf(context, url, filename, downloaded_urls, failed_urls):
            downloaded_urls.add(url)
            count += 1

    if count > 0:
        logger.info(f"⬇️ Downloaded {count} PDFs")

    return count


def download_all_pdfs(
    context: BrowserContext, files: list, max_downloads: int = None
) -> tuple:
    """
    Downloads all PDFs from the files list using the Playwright session.
    Skips files already in downloaded.txt.
    Returns (downloaded_count, failed_list) tuple.
    """
    ensure_downloads_dir()
    downloaded_urls = load_downloaded_urls()

    if max_downloads:
        files = files[:max_downloads]

    files_to_download = [f for f in files if f["url"] not in downloaded_urls]
    skipped = len(files) - len(files_to_download)

    total = len(files_to_download)
    downloaded = 0
    failed = []

    logger.info(f"\n{'=' * 60}")
    logger.info(f"⬇️ DOWNLOADING {total} FILES ({skipped} already downloaded)")
    logger.info(f"{'=' * 60}")

    for i, file_info in enumerate(files_to_download):
        url = file_info["url"]
        filename = file_info["filename"]

        logger.info(f"[{i + 1}/{total}] {filename}")

        if download_pdf(context, url, filename, downloaded_urls):
            downloaded += 1
            downloaded_urls.add(url)
        else:
            failed.append(filename)

    return downloaded + skipped, failed

"""
PDF download module for the Epstein Files Scraper.
Handles downloading PDFs using Playwright session cookies.
Supports background parallel downloads with resume capability.
"""

import threading
from queue import Queue, Empty
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


def download_pdf(context: BrowserContext, url: str, filename: str, downloaded_urls: set = None) -> bool:
    """
    Downloads a single PDF using the Playwright context session.
    Validates response is actually a PDF before saving.
    Returns True if download was successful.
    """
    ensure_downloads_dir()

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    filepath = paths.downloads_dir / filename

    # Skip if already downloaded (by URL or file exists)
    if downloaded_urls and url in downloaded_urls:
        return True

    if filepath.exists():
        logger.info(f"  ⏭️ {filename} (already exists)")
        mark_as_downloaded(url)
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
        mark_as_downloaded(url)
        return True

    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return False


class BackgroundDownloader:
    """
    Background downloader that processes PDFs in parallel threads.
    """

    def __init__(self, context: BrowserContext, num_workers: int = 3):
        self.context = context
        self.queue = Queue()
        self.workers = []
        self.running = True
        self.downloaded_urls = load_downloaded_urls()
        self.downloaded_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()

        for _ in range(num_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

        logger.info(f"🚀 Background downloader started with {num_workers} workers")

    def _worker(self):
        """Worker thread that processes download queue."""
        while self.running:
            try:
                file_info = self.queue.get(timeout=1)
                if file_info is None:
                    break

                url = file_info["url"]
                filename = file_info["filename"]

                # Skip if already downloaded
                with self.lock:
                    if url in self.downloaded_urls:
                        self.queue.task_done()
                        continue

                success = download_pdf(self.context, url, filename, self.downloaded_urls)

                with self.lock:
                    if success:
                        self.downloaded_urls.add(url)
                        self.downloaded_count += 1
                    else:
                        self.failed_count += 1

                self.queue.task_done()

            except Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def add_pdfs(self, pdfs: list):
        """Add PDFs to download queue (skips already downloaded)."""
        added = 0
        for pdf in pdfs:
            if pdf["url"] not in self.downloaded_urls:
                self.queue.put(pdf)
                added += 1
        if added > 0:
            logger.info(f"📥 Added {added} PDFs to download queue")

    def stop(self):
        """Stop all workers gracefully."""
        self.running = False
        for _ in self.workers:
            self.queue.put(None)
        for worker in self.workers:
            worker.join(timeout=5)
        logger.info(f"📊 Downloads complete: {self.downloaded_count} OK, {self.failed_count} failed")

    def wait(self):
        """Wait for all queued downloads to complete."""
        self.queue.join()


def download_all_pdfs(
    context: BrowserContext, files: list, max_downloads: int = None
) -> tuple:
    """
    Downloads all PDFs from the files list using the Playwright session.
    Returns (downloaded_count, failed_list) tuple.
    """
    ensure_downloads_dir()
    downloaded_urls = load_downloaded_urls()

    if max_downloads:
        files = files[:max_downloads]

    total = len(files)
    downloaded = 0
    failed = []

    logger.info(f"\n{'=' * 60}")
    logger.info(f"⬇️ DOWNLOADING {total} FILES")
    logger.info(f"{'=' * 60}")

    for i, file_info in enumerate(files):
        url = file_info["url"]
        filename = file_info["filename"]

        logger.info(f"[{i + 1}/{total}] {filename}")

        if download_pdf(context, url, filename, downloaded_urls):
            downloaded += 1
            downloaded_urls.add(url)
        else:
            failed.append(filename)

    return downloaded, failed

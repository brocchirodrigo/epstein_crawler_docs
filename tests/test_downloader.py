"""Tests for the downloader module."""

from unittest.mock import MagicMock, patch

from src.downloader import (
    download_pdf,
    download_batch,
    load_downloaded_urls,
    load_failed_urls,
)


class TestLoadDownloadedUrls:
    """Tests for load_downloaded_urls function."""

    def test_load_empty_when_file_not_exists(self, temp_downloads_dir):
        """Should return empty set when file doesn't exist."""
        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = load_downloaded_urls()
            assert result == set()

    def test_load_urls_from_file(self, temp_downloads_dir):
        """Should load URLs from downloaded.txt."""
        downloaded_file = temp_downloads_dir / "downloaded.txt"
        downloaded_file.write_text("https://example.com/1.pdf\nhttps://example.com/2.pdf\n")

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = load_downloaded_urls()
            assert result == {"https://example.com/1.pdf", "https://example.com/2.pdf"}


class TestLoadFailedUrls:
    """Tests for load_failed_urls function."""

    def test_load_empty_when_file_not_exists(self, temp_downloads_dir):
        """Should return empty set when file doesn't exist."""
        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = load_failed_urls()
            assert result == set()

    def test_load_failed_urls_from_file(self, temp_downloads_dir):
        """Should load URLs from failed_downloads.txt."""
        failed_file = temp_downloads_dir / "failed_downloads.txt"
        failed_file.write_text("https://example.com/404.pdf\n")

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = load_failed_urls()
            assert result == {"https://example.com/404.pdf"}


class TestDownloadPdf:
    """Tests for download_pdf function."""

    def test_skip_already_downloaded_url(self, mock_context, temp_downloads_dir):
        """Should skip URL already in downloaded_urls set."""
        downloaded_urls = {"https://example.com/file.pdf"}

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = download_pdf(
                mock_context, "https://example.com/file.pdf", "file.pdf",
                downloaded_urls=downloaded_urls
            )
            assert result == "skipped"
            mock_context.request.get.assert_not_called()

    def test_skip_failed_url(self, mock_context, temp_downloads_dir):
        """Should skip URL in failed_urls set."""
        failed_urls = {"https://example.com/failed.pdf"}

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = download_pdf(
                mock_context, "https://example.com/failed.pdf", "failed.pdf",
                failed_urls=failed_urls
            )
            assert result == "skipped"
            mock_context.request.get.assert_not_called()

    def test_skip_existing_file(self, mock_context, temp_downloads_dir):
        """Should skip if file already exists on disk."""
        (temp_downloads_dir / "existing.pdf").write_bytes(b"%PDF-1.4")

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                result = download_pdf(
                    mock_context, "https://example.com/existing.pdf", "existing.pdf"
                )
                assert result == "skipped"

    def test_download_success(self, mock_context, temp_downloads_dir, mock_pdf_response):
        """Should download and save PDF successfully."""
        mock_context.request.get.return_value = mock_pdf_response

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                result = download_pdf(
                    mock_context, "https://example.com/new.pdf", "new.pdf"
                )
                assert result == "downloaded"
                assert (temp_downloads_dir / "new.pdf").exists()

    def test_download_404_marks_as_failed(self, mock_context, temp_downloads_dir, mock_404_response):
        """Should mark URL as failed on 404."""
        mock_context.request.get.return_value = mock_404_response
        failed_urls = set()

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_failed"):
                result = download_pdf(
                    mock_context, "https://example.com/404.pdf", "404.pdf",
                    failed_urls=failed_urls
                )
                assert result == "skipped"
                assert "https://example.com/404.pdf" in failed_urls

    def test_download_invalid_pdf(self, mock_context, temp_downloads_dir):
        """Should return None for non-PDF response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.body.return_value = b"<html>Not a PDF</html>"
        mock_context.request.get.return_value = mock_response

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            result = download_pdf(
                mock_context, "https://example.com/fake.pdf", "fake.pdf"
            )
            assert result is None


class TestDownloadBatch:
    """Tests for download_batch function."""

    def test_batch_counts_only_downloads(self, mock_context, temp_downloads_dir, sample_pdf_files):
        """Should count only actual downloads, not skips."""
        mock_pdf_response = MagicMock()
        mock_pdf_response.status = 200
        mock_pdf_response.body.return_value = b"%PDF-1.4 content"
        mock_context.request.get.return_value = mock_pdf_response

        downloaded_urls = set()
        failed_urls = set()

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                count = download_batch(
                    mock_context, sample_pdf_files, downloaded_urls, failed_urls
                )
                assert count == 3
                assert len(downloaded_urls) == 3

    def test_batch_skips_already_downloaded(self, mock_context, temp_downloads_dir, sample_pdf_files):
        """Should skip files already in downloaded_urls."""
        downloaded_urls = {"https://example.com/file1.pdf", "https://example.com/file2.pdf"}
        failed_urls = set()

        mock_pdf_response = MagicMock()
        mock_pdf_response.status = 200
        mock_pdf_response.body.return_value = b"%PDF-1.4 content"
        mock_context.request.get.return_value = mock_pdf_response

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                count = download_batch(
                    mock_context, sample_pdf_files, downloaded_urls, failed_urls
                )
                assert count == 1  # Only file3.pdf

    def test_batch_returns_zero_when_nothing_to_download(self, mock_context, sample_pdf_files):
        """Should return 0 when all files already downloaded."""
        downloaded_urls = {f["url"] for f in sample_pdf_files}
        failed_urls = set()

        count = download_batch(mock_context, sample_pdf_files, downloaded_urls, failed_urls)
        assert count == 0


class TestDownloadAllPdfs:
    """Tests for download_all_pdfs function."""

    def test_respects_max_downloads(self, mock_context, temp_downloads_dir, sample_pdf_files):
        """Should limit downloads to max_downloads."""
        from src.downloader import download_all_pdfs

        mock_pdf_response = MagicMock()
        mock_pdf_response.status = 200
        mock_pdf_response.body.return_value = b"%PDF-1.4 content"
        mock_context.request.get.return_value = mock_pdf_response

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                # Pass 3 files but limit to 2
                downloaded, failed = download_all_pdfs(mock_context, sample_pdf_files, max_downloads=2)

        # Should only attempt 2 downloads
        assert mock_context.request.get.call_count == 2

    def test_returns_failed_list(self, mock_context, temp_downloads_dir):
        """Should return list of failed downloads."""
        from src.downloader import download_all_pdfs

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.body.return_value = b"<html>Not PDF</html>"  # Invalid PDF
        mock_context.request.get.return_value = mock_response

        files = [{"url": "https://example.com/bad.pdf", "filename": "bad.pdf"}]

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            downloaded, failed = download_all_pdfs(mock_context, files)

        assert "bad.pdf" in failed

    def test_skips_already_downloaded(self, mock_context, temp_downloads_dir):
        """Should skip files in downloaded.txt."""
        from src.downloader import download_all_pdfs

        # Create downloaded.txt with one URL
        downloaded_file = temp_downloads_dir / "downloaded.txt"
        downloaded_file.write_text("https://example.com/file1.pdf\n")

        files = [
            {"url": "https://example.com/file1.pdf", "filename": "file1.pdf"},
            {"url": "https://example.com/file2.pdf", "filename": "file2.pdf"},
        ]

        mock_pdf_response = MagicMock()
        mock_pdf_response.status = 200
        mock_pdf_response.body.return_value = b"%PDF-1.4 content"
        mock_context.request.get.return_value = mock_pdf_response

        with patch("src.downloader.paths") as mock_paths:
            mock_paths.downloads_dir = temp_downloads_dir
            with patch("src.downloader.mark_as_downloaded"):
                downloaded, failed = download_all_pdfs(mock_context, files)

        # Only file2 should be attempted
        assert mock_context.request.get.call_count == 1


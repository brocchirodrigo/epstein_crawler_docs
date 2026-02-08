"""Tests for the app orchestrator module."""

import json
from unittest.mock import MagicMock, patch


class TestSaveJson:
    """Tests for _save_json function."""

    def test_atomic_write_success(self, tmp_path):
        """Should write JSON atomically using temp file."""
        from src.app import _save_json

        output_file = tmp_path / "output.json"

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file

            pdfs = [{"url": "https://example.com/1.pdf", "filename": "1.pdf"}]
            _save_json(pdfs, ["A", "B"], 10)

            assert output_file.exists()
            data = json.loads(output_file.read_text())
            assert data["total_files"] == 1
            assert data["letters_searched"] == ["A", "B"]

    def test_atomic_write_no_temp_on_success(self, tmp_path):
        """Should not leave temp file after successful write."""
        from src.app import _save_json

        output_file = tmp_path / "output.json"
        temp_file = tmp_path / "output.tmp"

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file

            _save_json([], ["A"], 5)

            assert not temp_file.exists()


class TestLoadExistingProgress:
    """Tests for _load_existing_progress function."""

    def test_loads_existing_json(self, tmp_path):
        """Should load PDFs from existing JSON file."""
        from src.app import _load_existing_progress

        output_file = tmp_path / "epstein_urls.json"
        output_file.write_text(json.dumps({
            "total_files": 2,
            "files": [
                {"url": "https://example.com/1.pdf", "filename": "1.pdf"},
                {"url": "https://example.com/2.pdf", "filename": "2.pdf"},
            ]
        }))

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file

            all_pdfs, existing_urls = _load_existing_progress()

            assert len(all_pdfs) == 2
            assert "https://example.com/1.pdf" in existing_urls

    def test_creates_new_json_if_not_exists(self, tmp_path):
        """Should create new JSON file if it doesn't exist."""
        from src.app import _load_existing_progress

        output_file = tmp_path / "epstein_urls.json"

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file

            all_pdfs, existing_urls = _load_existing_progress()

            assert all_pdfs == []
            assert existing_urls == set()
            assert output_file.exists()

    def test_handles_empty_file(self, tmp_path):
        """Should handle empty JSON file gracefully."""
        from src.app import _load_existing_progress

        output_file = tmp_path / "epstein_urls.json"
        output_file.write_text("")

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file

            all_pdfs, existing_urls = _load_existing_progress()

            assert all_pdfs == []
            assert existing_urls == set()


class TestDeduplicate:
    """Tests for _deduplicate function."""

    def test_removes_duplicates(self):
        """Should remove duplicate PDFs by URL."""
        from src.app import _deduplicate

        pdfs = [
            {"url": "https://example.com/1.pdf", "filename": "1.pdf"},
            {"url": "https://example.com/2.pdf", "filename": "2.pdf"},
            {"url": "https://example.com/1.pdf", "filename": "1.pdf"},  # duplicate
        ]

        result = _deduplicate(pdfs)

        assert len(result) == 2

    def test_preserves_order_approximately(self):
        """Should keep unique PDFs."""
        from src.app import _deduplicate

        pdfs = [
            {"url": "https://example.com/a.pdf", "filename": "a.pdf"},
            {"url": "https://example.com/b.pdf", "filename": "b.pdf"},
        ]

        result = _deduplicate(pdfs)

        assert len(result) == 2


class TestEmergencySave:
    """Tests for _emergency_save function."""

    def test_saves_on_error(self, tmp_path):
        """Should save progress during emergency."""
        from src.app import _emergency_save

        output_file = tmp_path / "output.json"

        with patch("src.app.paths") as mock_paths:
            mock_paths.output_json = output_file
            with patch("src.app._save_json") as mock_save:
                pdfs = [{"url": "https://example.com/1.pdf", "filename": "1.pdf"}]
                _emergency_save(pdfs)

                mock_save.assert_called_once()

    def test_returns_empty_when_no_pdfs(self):
        """Should return empty list when no PDFs to save."""
        from src.app import _emergency_save

        result = _emergency_save([])
        assert result == []


class TestCollectLinks:
    """Tests for _collect_links function."""

    def test_handles_letter_failure_gracefully(self, tmp_path):
        """Should continue processing other letters if one fails."""
        from src.app import _collect_links

        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Network error")

        # Should not raise, just log and continue
        result = _collect_links(mock_page, ["A", "B"], max_pages=1)
        assert result == []


class TestProcessDataset:
    """Tests for _process_dataset function."""

    def test_filters_existing_urls(self, tmp_path):
        """Should not add PDFs that already exist."""
        from src.app import _process_dataset

        mock_page = MagicMock()
        all_pdfs = []
        existing_urls = {"https://example.com/existing.pdf"}
        save_progress = MagicMock()

        with patch("src.app.collect_pdfs_from_dataset") as mock_collect:
            mock_collect.return_value = [
                {"url": "https://example.com/existing.pdf", "filename": "existing.pdf"},
                {"url": "https://example.com/new.pdf", "filename": "new.pdf"},
            ]
            with patch("src.app._save_json"):
                _process_dataset(
                    mock_page, "https://example.com/dataset", 0, 1,
                    all_pdfs, existing_urls, save_progress
                )

        # Only new.pdf should be added
        assert len(all_pdfs) == 1
        assert all_pdfs[0]["url"] == "https://example.com/new.pdf"


class TestRunScanMode:
    """Tests for run_scan_mode orchestrator."""

    def test_handles_navigation_failure(self):
        """Should handle navigation errors gracefully."""
        from src.app import run_scan_mode

        with patch("src.app.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            # Simulate navigation failure
            mock_page.goto.side_effect = Exception("Navigation failed")

            with patch("src.app._load_existing_progress", return_value=([], set())):
                with patch("src.app.load_downloaded_urls", return_value=set()):
                    with patch("src.app.load_failed_urls", return_value=set()):
                        result = run_scan_mode(skip_download=True)

            # Should return empty list on failure
            assert result == []


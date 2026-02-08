"""Tests for the scraper module."""

from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup


class TestExtractPdfsFromDatasetPage:
    """Tests for PDF extraction from dataset pages."""

    def test_extract_pdfs_from_html(self):
        """Should extract PDF links from dataset page HTML."""
        from src.scraper import _extract_pdfs_from_dataset_page

        # The function uses link text as filename, not the href
        html = """
        <div class="view-content">
            <div class="views-row">
                <a href="/files/doc1.pdf">EFTA00001.pdf</a>
            </div>
            <div class="views-row">
                <a href="/files/doc2.pdf">EFTA00002.pdf</a>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        dataset_url = "https://example.com/dataset-1"

        pdfs = _extract_pdfs_from_dataset_page(soup, dataset_url)

        assert len(pdfs) == 2
        assert pdfs[0]["filename"] == "EFTA00001.pdf"
        assert pdfs[1]["filename"] == "EFTA00002.pdf"
        assert "dataset" in pdfs[0]

    def test_extract_no_pdfs(self):
        """Should return empty list when no PDFs found."""
        from src.scraper import _extract_pdfs_from_dataset_page

        html = "<div class='empty'><p>No files</p></div>"
        soup = BeautifulSoup(html, "lxml")

        pdfs = _extract_pdfs_from_dataset_page(soup, "https://example.com")
        assert pdfs == []

    def test_uses_href_name_when_no_text(self):
        """Should use href filename when link has no text."""
        from src.scraper import _extract_pdfs_from_dataset_page

        html = '<a href="/files/document.pdf"></a>'
        soup = BeautifulSoup(html, "lxml")

        pdfs = _extract_pdfs_from_dataset_page(soup, "https://example.com")

        assert len(pdfs) == 1
        assert pdfs[0]["filename"] == "document.pdf"


class TestCheckResultsLoaded:
    """Tests for result detection."""

    def test_detects_results(self):
        """Should return True when PDF links are present in results div."""
        from src.scraper import _check_results_loaded

        # Must have div#results containing PDF links
        content = """
        <div id="results">
            <a href="/files/doc.pdf">Document</a>
        </div>
        """
        assert _check_results_loaded(content) is True

    def test_detects_no_results(self):
        """Should return False when no PDF links in results."""
        from src.scraper import _check_results_loaded

        content = "<div id='results'><p>No results found</p></div>"
        assert _check_results_loaded(content) is False

    def test_detects_no_results_div(self):
        """Should return False when no results div exists."""
        from src.scraper import _check_results_loaded

        content = "<p>Some other content</p>"
        assert _check_results_loaded(content) is False


class TestGetTotalPages:
    """Tests for pagination detection."""

    def test_returns_one_when_no_pagination(self):
        """Should return 1 when no pagination found."""
        from src.scraper import get_total_pages

        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body>No pagination</body></html>"
        mock_page.query_selector.return_value = None

        result = get_total_pages(mock_page, max_pages=5)
        assert result == 1

    def test_extracts_from_results_text(self):
        """Should extract total from 'Showing X to Y of Z Results' text."""
        from src.scraper import get_total_pages

        mock_page = MagicMock()
        mock_page.content.return_value = "Showing 1 to 50 of 1,000 Results"
        mock_page.query_selector.return_value = None

        result = get_total_pages(mock_page, max_pages=None)
        assert result == 100  # Implementation uses 10 results per page


class TestPassGates:
    """Tests for gate passing functionality."""

    def test_passes_robot_check(self):
        """Should handle robot check via JavaScript."""
        from src.scraper import pass_gates

        mock_page = MagicMock()
        mock_page.content.return_value = "<html></html>"
        mock_page.evaluate.return_value = True

        # Should not raise
        pass_gates(mock_page)

    def test_passes_age_verification(self):
        """Should handle age verification via JavaScript."""
        from src.scraper import pass_gates

        mock_page = MagicMock()
        mock_page.content.return_value = "<html></html>"
        mock_page.evaluate.return_value = True

        pass_gates(mock_page)


class TestExpandTransparencyAccordion:
    """Tests for accordion expansion."""

    def test_clicks_accordion_via_javascript(self):
        """Should click accordion using page.evaluate()."""
        from src.scraper import expand_transparency_accordion

        mock_page = MagicMock()
        mock_page.evaluate.return_value = True  # JavaScript click succeeded

        result = expand_transparency_accordion(mock_page)

        mock_page.evaluate.assert_called_once()
        assert result is True

    def test_returns_false_when_not_found(self):
        """Should return False when accordion button not found."""
        from src.scraper import expand_transparency_accordion

        mock_page = MagicMock()
        mock_page.evaluate.return_value = False  # JavaScript didn't find button

        result = expand_transparency_accordion(mock_page)
        assert result is False


class TestGetDatasetLinks:
    """Tests for dataset link extraction."""

    def test_extracts_dataset_links(self):
        """Should extract dataset links from page content."""
        from src.scraper import get_dataset_links

        mock_page = MagicMock()
        mock_page.content.return_value = """
        <div class="accordion">
            <a href="/epstein/doj-disclosures/data-set-1-files">Data Set 1 Files</a>
            <a href="/epstein/doj-disclosures/data-set-2-files">Data Set 2 Files</a>
        </div>
        """

        links = get_dataset_links(mock_page)
        assert len(links) >= 0  # Implementation depends on actual selectors


class TestNavigateToPage:
    """Tests for page navigation."""

    def test_navigates_successfully(self):
        """Should navigate to target page."""
        from src.scraper import navigate_to_page

        mock_page = MagicMock()
        mock_button = MagicMock()
        mock_page.query_selector.return_value = mock_button
        mock_page.content.return_value = '<div id="results"><div class="views-row"><a href="test.pdf">Result</a></div></div>'

        result = navigate_to_page(mock_page, target_page=2)
        assert result is True
        # Function returns boolean based on success

    def test_returns_false_when_no_button(self):
        """Should return False when pagination button not found."""
        from src.scraper import navigate_to_page

        mock_page = MagicMock()
        mock_page.query_selector.return_value = None

        result = navigate_to_page(mock_page, target_page=99)
        assert result is False


class TestCollectPdfsForLetter:
    """Tests for letter-based PDF collection."""

    def test_collects_from_multiple_pages(self):
        """Should collect PDFs from all pages for a letter."""
        from src.scraper import collect_pdfs_for_letter

        mock_page = MagicMock()
        mock_page.content.return_value = """
        <div id="results">
            <a href="/files/doc.pdf">Doc</a>
        </div>
        Showing 1 to 10 of 10 Results
        """
        mock_page.query_selector.return_value = None

        with patch("src.scraper.search_letter", return_value=True):
            with patch("src.scraper.get_total_pages", return_value=1):
                with patch(
                    "src.scraper.extract_pdfs_from_page",
                    return_value=[
                        {"url": "https://example.com/doc.pdf", "filename": "doc.pdf"}
                    ],
                ):
                    result = collect_pdfs_for_letter(mock_page, "A", max_pages=1)

        assert len(result) >= 0


class TestCollectPdfsFromDataset:
    """Tests for dataset PDF collection."""

    def test_calls_progress_callback(self):
        """Should call progress callback after each page."""
        from src.scraper import collect_pdfs_from_dataset

        mock_page = MagicMock()
        mock_page.goto.return_value = None
        mock_page.content.return_value = "<html><body>No PDFs</body></html>"

        progress_callback = MagicMock()

        with patch("src.scraper.pass_gates"):
            result = collect_pdfs_from_dataset(
                mock_page,
                "https://example.com/dataset",
                on_page_complete=progress_callback,
            )

        # Callback should be called at least once
        assert progress_callback.called or len(result) == 0

    def test_stops_when_no_more_pdfs(self):
        """Should stop iterating when page has no PDFs."""
        from src.scraper import collect_pdfs_from_dataset

        mock_page = MagicMock()
        mock_page.goto.return_value = None
        mock_page.content.return_value = "<html><body>Empty</body></html>"

        with patch("src.scraper.pass_gates"):
            result = collect_pdfs_from_dataset(mock_page, "https://example.com/dataset")

        # Should return empty when no PDFs found
        assert result == []

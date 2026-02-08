"""Shared fixtures for tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def temp_downloads_dir(tmp_path):
    """Create a temporary downloads directory."""
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    return downloads


@pytest.fixture
def mock_pdf_response():
    """Create a mock PDF response."""
    mock = MagicMock()
    mock.status = 200
    mock.body.return_value = b"%PDF-1.4 fake pdf content"
    return mock


@pytest.fixture
def mock_404_response():
    """Create a mock 404 response."""
    mock = MagicMock()
    mock.status = 404
    return mock


@pytest.fixture
def sample_pdf_files():
    """Sample PDF file list for testing."""
    return [
        {"url": "https://example.com/file1.pdf", "filename": "file1.pdf"},
        {"url": "https://example.com/file2.pdf", "filename": "file2.pdf"},
        {"url": "https://example.com/file3.pdf", "filename": "file3.pdf"},
    ]


@pytest.fixture
def mock_context(mock_pdf_response):
    """Create a mock Playwright context."""
    context = MagicMock()
    context.request.get.return_value = mock_pdf_response
    return context

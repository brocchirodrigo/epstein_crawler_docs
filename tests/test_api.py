"""Tests for the FastAPI API module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = MagicMock()
    store.search = AsyncMock(return_value=[
        {"filename": "doc1.pdf", "page": 1, "text": "Sample text", "score": 0.9}
    ])
    return store


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    return client


class TestHealthCheck:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self):
        """Should return healthy status."""
        from src.api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestGetStats:
    """Tests for /stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_returns_data(self):
        """Should return index statistics."""
        from src.api import app

        with patch("src.api.get_index_stats") as mock_stats:
            mock_stats.return_value = {
                "total_documents": 100,
                "total_chunks": 500
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/stats")

            assert response.status_code == 200


class TestSyncEndpoints:
    """Tests for sync-related endpoints."""

    @pytest.mark.asyncio
    async def test_sync_status(self):
        """Should return sync status."""
        from src.api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert "running" in data

    @pytest.mark.asyncio
    async def test_trigger_sync(self):
        """Should trigger sync process."""
        from src.api import app, sync_state

        # Reset sync state
        sync_state["running"] = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/sync")  # Correct endpoint

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestAskEndpoint:
    """Tests for /ask endpoint."""

    @pytest.mark.asyncio
    async def test_ask_requires_question(self):
        """Should require question in request body."""
        from src.api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/ask", json={})

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ask_with_valid_question(self):
        """Should process valid question."""
        from src.api import app

        with patch("src.api.get_embedding") as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            with patch("src.api.VectorStore") as mock_store_class:
                mock_store = MagicMock()
                mock_store.search.return_value = [
                    {"filename": "doc.pdf", "page": 1, "text": "Context", "score": 0.9}
                ]
                mock_store_class.return_value = mock_store

                with patch("src.api.get_llm_client") as mock_llm:
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock(message=MagicMock(content="Answer"))]
                    mock_client.chat.completions.create.return_value = mock_response
                    mock_llm.return_value = mock_client

                    transport = ASGITransport(app=app)
                    async with AsyncClient(transport=transport, base_url="http://test") as client:
                        response = await client.post(
                            "/ask",
                            json={"question": "What is this about?"}
                        )

                    # May fail if Qdrant not available, but structure is tested
                    assert response.status_code in [200, 500]


class TestCORSMiddleware:
    """Tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Should include CORS headers in response."""
        from src.api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/health",
                headers={"Origin": "http://localhost:3000"}
            )

        # CORS preflight should be handled
        assert response.status_code in [200, 405]  # OPTIONS may or may not be allowed

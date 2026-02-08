"""
Qdrant Vector Store wrapper.

Manages the vector database for RAG.
"""

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import rag_settings
from ..logging_config import logger

COLLECTION_NAME = "epstein_files"


@dataclass
class SearchResult:
    """A single search result."""

    text: str
    filename: str
    chunk_index: int
    score: float


class VectorStore:
    """Qdrant vector store for RAG."""

    def __init__(self):
        """Initialize the Qdrant client."""
        self.client = QdrantClient(
            host=rag_settings.qdrant_host,
            port=rag_settings.qdrant_port,
        )
        self._ensure_collection()

    def _ensure_collection(self):
        """Create the collection if it doesn't exist or has wrong dimension."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME in collection_names:
            # Check existing dimension
            info = self.client.get_collection(COLLECTION_NAME)
            current_dim = info.config.params.vectors.size
            target_dim = rag_settings.openai_embedding_dimension

            if current_dim != target_dim:
                logger.warning(
                    f"⚠️ Collection dimension mismatch! Found {current_dim}, expected {target_dim}. Recreating..."
                )
                self.client.delete_collection(COLLECTION_NAME)
                collection_names.remove(COLLECTION_NAME)
            else:
                logger.info(
                    f"Collection {COLLECTION_NAME} exists with correct dimension ({current_dim})."
                )

        if COLLECTION_NAME not in collection_names:
            logger.info(
                f"Creating collection: {COLLECTION_NAME} with dim {rag_settings.openai_embedding_dimension}"
            )
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=rag_settings.openai_embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )

    def upsert(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        filename: str,
    ) -> int:
        """
        Insert or update vectors in the store.

        Args:
            texts: List of text chunks.
            embeddings: Corresponding embedding vectors.
            filename: Source PDF filename.

        Returns:
            Number of points inserted.
        """
        points = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            point_id = hash(f"{filename}_{i}") % (2**63)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": text,
                        "filename": filename,
                        "chunk_index": i,
                    },
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

        logger.info(f"Upserted {len(points)} chunks from {filename}")
        return len(points)

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_embedding: The query vector.
            top_k: Number of results to return.

        Returns:
            List of SearchResult objects.
        """

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k,
        ).points

        return [
            SearchResult(
                text=r.payload["text"],
                filename=r.payload["filename"],
                chunk_index=r.payload["chunk_index"],
                score=r.score,
            )
            for r in results
        ]

    def delete_by_filename(self, filename: str):
        """Delete all vectors from a specific file."""
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector={
                "filter": {"must": [{"key": "filename", "match": {"value": filename}}]}
            },
        )
        logger.info(f"Deleted vectors for {filename}")

    def get_stats(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(COLLECTION_NAME)
        return {
            "points_count": info.points_count,
            "status": str(info.status),
        }

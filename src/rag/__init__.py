"""
RAG (Retrieval-Augmented Generation) module for the Epstein Files API.

This module provides:
- PDF parsing via Vision LLM (text + image understanding)
- Text embeddings
- Vector storage via Qdrant
- Sync logic for keeping the index up-to-date
"""

from .parser import parse_pdf
from .embeddings import get_embeddings
from .store import VectorStore
from .sync import sync_documents

__all__ = ["parse_pdf", "get_embeddings", "VectorStore", "sync_documents"]

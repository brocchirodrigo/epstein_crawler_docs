"""
Document synchronization logic.

Tracks which PDFs have been indexed and keeps the vector store up-to-date.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..config import paths
from ..logging_config import logger
from .embeddings import get_embeddings
from .parser import chunk_text, parse_pdf
from .store import VectorStore

INDEX_FILE = paths.downloads_dir / ".rag_index.json"


@dataclass
class IndexEntry:
    """Metadata for an indexed file."""

    hash: str
    indexed_at: str
    chunk_count: int


def _compute_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _load_index() -> dict[str, IndexEntry]:
    """Load the index file."""
    if not INDEX_FILE.exists():
        return {}

    with open(INDEX_FILE) as f:
        data = json.load(f)

    return {
        filename: IndexEntry(**entry)
        for filename, entry in data.get("indexed_files", {}).items()
    }


def _save_index(index: dict[str, IndexEntry]):
    """Save the index file."""
    data = {
        "indexed_files": {
            filename: {
                "hash": entry.hash,
                "indexed_at": entry.indexed_at,
                "chunk_count": entry.chunk_count,
            }
            for filename, entry in index.items()
        },
        "last_sync": datetime.now().isoformat(),
    }

    with open(INDEX_FILE, "w") as f:
        json.dump(data, f, indent=2)


def sync_documents(
    force: bool = False,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> dict:
    """
    Synchronize PDFs in downloads/ with the vector store.

    Args:
        force: If True, re-index all files regardless of hash.
        progress_callback: Optional callback to report progress updates.

    Returns:
        Summary of sync operation.
    """
    def report_progress(status: str, current_file: str = None, processed: int = 0, total: int = 0):
        if progress_callback:
            progress_callback({
                "status": status,
                "current_file": current_file,
                "processed": processed,
                "total": total,
            })

    store = VectorStore()
    index = _load_index()

    pdf_files = list(paths.downloads_dir.glob("*.pdf"))
    total_files = len(pdf_files)
    logger.info(f"Found {total_files} PDF files in downloads/")

    report_progress("scanning", total=total_files)

    stats = {
        "total_files": total_files,
        "new_files": 0,
        "updated_files": 0,
        "skipped_files": 0,
        "total_chunks": 0,
        "errors": [],
    }

    for i, pdf_path in enumerate(pdf_files, 1):
        filename = pdf_path.name
        current_hash = _compute_hash(pdf_path)

        needs_processing = force
        if filename not in index:
            needs_processing = True
            stats["new_files"] += 1
        elif index[filename].hash != current_hash:
            needs_processing = True
            stats["updated_files"] += 1
            store.delete_by_filename(filename)

        if not needs_processing:
            stats["skipped_files"] += 1
            continue

        report_progress("parsing", filename, i, total_files)

        try:
            markdown = parse_pdf(pdf_path)

            chunks = chunk_text(markdown)
            if not chunks:
                logger.warning(f"No text extracted from {filename}")
                continue

            report_progress("embedding", filename, i, total_files)
            embeddings = get_embeddings(chunks)

            report_progress("storing", filename, i, total_files)
            chunk_count = store.upsert(chunks, embeddings, filename)

            index[filename] = IndexEntry(
                hash=current_hash,
                indexed_at=datetime.now().isoformat(),
                chunk_count=chunk_count,
            )

            stats["total_chunks"] += chunk_count
            logger.info(f"✅ Indexed {filename}: {chunk_count} chunks")

        except Exception as e:
            error_msg = f"Error processing {filename}: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

    _save_index(index)

    report_progress("complete", processed=total_files, total=total_files)

    logger.info(
        f"Sync complete: {stats['new_files']} new, "
        f"{stats['updated_files']} updated, "
        f"{stats['skipped_files']} skipped"
    )

    return stats


def get_index_stats() -> dict:
    """Get statistics about the current index."""
    index = _load_index()
    store = VectorStore()

    return {
        "indexed_files": len(index),
        "total_chunks": sum(e.chunk_count for e in index.values()),
        "store_stats": store.get_stats(),
    }

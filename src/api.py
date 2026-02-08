"""
FastAPI server for RAG queries.

Provides endpoints for asking questions and checking system status.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import paths, rag_settings
from .logging_config import logger
from .rag.embeddings import get_embedding
from .rag.llm import get_llm_client
from .rag.store import VectorStore
from .rag.sync import get_index_stats, sync_documents


class QuestionRequest(BaseModel):
    """Request body for /ask endpoint."""

    question: str
    top_k: int = 5


class AnswerResponse(BaseModel):
    """Response body for /ask endpoint."""

    answer: str
    sources: list[dict]


class SyncStatusResponse(BaseModel):
    """Response body for sync status."""

    running: bool
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: Optional[dict]
    result: Optional[dict]
    error: Optional[str]


sync_state = {
    "running": False,
    "started_at": None,
    "completed_at": None,
    "progress": None,
    "result": None,
    "error": None,
}

background_tasks = set()


def run_sync_task(force: bool = False):
    """Run sync in background."""
    global sync_state

    def update_progress(progress: dict):
        sync_state["progress"] = progress

    sync_state["running"] = True
    sync_state["started_at"] = datetime.now().isoformat()
    sync_state["completed_at"] = None
    sync_state["progress"] = {"status": "starting", "current_file": None}
    sync_state["result"] = None
    sync_state["error"] = None

    try:
        logger.info("🔄 Background sync started...")
        result = sync_documents(force=force, progress_callback=update_progress)

        sync_state["result"] = result
        sync_state["completed_at"] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("✅ SYNC COMPLETE!")
        logger.info(f"   New files: {result.get('new_files', 0)}")
        logger.info(f"   Updated files: {result.get('updated_files', 0)}")
        logger.info(f"   Skipped: {result.get('skipped_files', 0)}")
        logger.info(f"   Total chunks: {result.get('total_chunks', 0)}")
        if result.get("errors"):
            logger.warning(f"   Errors: {len(result['errors'])}")
        logger.info("=" * 60)

    except Exception as e:
        sync_state["error"] = str(e)
        sync_state["completed_at"] = datetime.now().isoformat()
        logger.error(f"❌ SYNC FAILED: {e}")

    finally:
        sync_state["running"] = False
        sync_state["progress"] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting RAG API...")

    try:
        stats = get_index_stats()
        pdf_count = len(list(paths.downloads_dir.glob("*.pdf")))

        if stats["indexed_files"] < pdf_count:
            logger.info(
                f"⚠️  Found {pdf_count} PDFs but only {stats['indexed_files']} indexed. "
                "Starting background sync..."
            )
            task = asyncio.create_task(asyncio.to_thread(run_sync_task, False))
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)
        else:
            logger.info(
                f"✅ Index is up-to-date: {stats['indexed_files']} files indexed."
            )
    except Exception as e:
        logger.warning(f"Could not check index on startup: {e}")
        logger.info("Starting background sync anyway...")
        task = asyncio.create_task(asyncio.to_thread(run_sync_task, False))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    yield

    logger.info("Shutting down RAG API...")


app = FastAPI(
    title="Epstein Files RAG API",
    description="Query the Epstein Files using natural language.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = rag_settings.api_cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "sync_running": sync_state["running"]}


@app.get("/stats")
async def get_stats():
    """Get index statistics."""
    try:
        stats = get_index_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync")
async def trigger_sync(force: bool = False):
    """
    Trigger document synchronization in background.

    Returns immediately and runs sync in background.
    Check GET /sync/status for progress.
    """
    if sync_state["running"]:
        raise HTTPException(
            status_code=409,
            detail="Sync already in progress. Check GET /sync/status for progress.",
        )

    task = asyncio.create_task(asyncio.to_thread(run_sync_task, force))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    return {
        "message": "Sync started in background",
        "status_url": "/sync/status",
        "started_at": datetime.now().isoformat(),
    }


@app.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status():
    """Get current sync status."""
    return SyncStatusResponse(
        running=sync_state["running"],
        started_at=sync_state["started_at"],
        completed_at=sync_state["completed_at"],
        progress=sync_state["progress"],
        result=sync_state["result"],
        error=sync_state["error"],
    )


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the Epstein Files.

    The system will:
    1. Embed the question
    2. Search for relevant document chunks
    3. Generate an answer using the LLM
    """
    if not rag_settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        query_embedding = get_embedding(request.question)

        store = VectorStore()
        results = store.search(query_embedding, top_k=request.top_k)

        if not results:
            return AnswerResponse(
                answer="No relevant documents found.",
                sources=[],
            )

        context_parts = []
        sources = []
        for r in results:
            context_parts.append(f"[From {r.filename}]:\n{r.text}")
            sources.append(
                {
                    "filename": r.filename,
                    "chunk_index": r.chunk_index,
                    "score": r.score,
                    "preview": r.text[:200] + "..." if len(r.text) > 200 else r.text,
                }
            )

        context = "\n\n---\n\n".join(context_parts)

        client = get_llm_client()

        system_prompt = (
            "You are a helpful assistant analyzing documents from the Epstein Files. "
            "Answer questions based ONLY on the provided context. "
            "If the answer is not in the context, say so. "
            "Cite the source filename when referencing specific information."
        )

        response = client.chat.completions.create(
            model=rag_settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {request.question}",
                },
            ],
        )

        answer = response.choices[0].message.content

        return AnswerResponse(answer=answer, sources=sources)

    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start_server():
    """Start the FastAPI server."""
    import uvicorn

    logger.info(f"Starting server on port {rag_settings.api_port}...")
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=rag_settings.api_port,
        reload=False,
    )

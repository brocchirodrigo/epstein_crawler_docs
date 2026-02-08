# Epstein Files Scraper & RAG API

A Python-based web scraper and RAG (Retrieval-Augmented Generation) API for the U.S. Department of Justice Epstein Files.

## Features

### Scraper
- **Automated Browser Control**: Uses Playwright to bypass bot detection and age verification.
- **DOJ Disclosures Scan (Default)**: Automatically navigates the disclosures page and downloads datasets.
- **Legacy Alphabet Search**: Optional mode to search through documents using letter-based queries.
- **Deduplication**: Removes duplicate files before downloading.

### RAG API
- **Vision PDF Parsing**: Uses GPT-4o-mini Vision to extract text AND understand images from PDFs.
- **Multimodal Understanding**: Images, signatures, and diagrams are described and indexed.
- **Vector Search**: Qdrant vector database for semantic search.
- **OpenAI-Compatible**: Supports custom API endpoints (Ollama, Azure, etc).
- **Background Sync**: Indexes PDFs in background without blocking the API.

## Project Structure

```
eua_gov/
├── src/
│   ├── __init__.py         # Package exports
│   ├── app.py              # Scraper orchestrator
│   ├── api.py              # FastAPI RAG server
│   ├── config.py           # Pydantic Settings
│   ├── logging_config.py   # Loguru setup
│   ├── scraper.py          # Web scraping logic
│   ├── downloader.py       # PDF download logic
│   └── rag/                # RAG module
│       ├── llm.py          # LLM client wrapper
│       ├── parser.py       # Vision PDF parser
│       ├── embeddings.py   # Embeddings wrapper
│       ├── store.py        # Qdrant wrapper
│       └── sync.py         # Document sync logic
├── downloads/              # Downloaded PDF files
├── logs/                   # Log files
├── main.py                 # Entry point
├── routes.http             # HTTP client tests
├── .env                    # Environment configuration
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose
└── pyproject.toml          # Dependencies
```

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Docker (for Qdrant)

## Installation

```bash
cd epstein_crawler_docs

# Install dependencies
uv sync

# Install Playwright browsers (for scraper)
uv run playwright install chromium
```

## Environment Variables

Create a `.env` file in the project root:


```env
# ============================================================
# Scraper Configuration (Optional)
# ============================================================
MAX_DOWNLOADS=              # Max files to download (default: unlimited)
NAVIGATION_TIMEOUT=60000    # Navigation timeout in ms

# ============================================================
# RAG API Configuration (Required for API)
# ============================================================
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=            # Optional: Custom API URL (Ollama, Azure, etc)

# Models (optional, these are defaults for OpenAI)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSION=1536  # Dimension of the embedding model
OPENAI_CHAT_MODEL=gpt-5-mini
OPENAI_VISION_MODEL=        # Optional: Separate model for PDF parsing (defaults to CHAT_MODEL)

# PDF Parsing
MAX_PAGES_PER_PDF=0         # 0 = no limit

# Qdrant (optional if running locally)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# API Server (optional)
API_PORT=8000
API_CORS_ORIGINS=*
```

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key (or "ollama" for Ollama) |
| `OPENAI_BASE_URL` | (none) | Custom API URL for Ollama, Azure, etc |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `OPENAI_EMBEDDING_DIMENSION` | `1536` | **Must match the model's output size.** |
| `OPENAI_CHAT_MODEL` | `gpt-5-mini` | Chat model for Q&A |
| `OPENAI_VISION_MODEL` | (chat model) | Vision model for PDF parsing |
| `MAX_PAGES_PER_PDF` | `0` (unlimited) | Max pages per PDF to process |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `API_PORT` | `8000` | FastAPI server port |
| `API_CORS_ORIGINS` | `*` | CORS allowed origins |
| `MAX_DOWNLOADS` | (none) | Max PDFs to download (scraper) |

### Common Embedding Dimensions

| Model | Dimension |
|-------|-----------|
| `text-embedding-3-small` (OpenAI) | 1536 |
| `text-embedding-3-large` (OpenAI) | 3072 |
| `text-embedding-ada-002` (OpenAI) | 1536 |
| `qwen3-embedding` (Ollama) | 1024 (or 4096, check model card) |

## Usage

### Scraper

#### 🚀 Default: Scan Mode (DOJ Disclosures)

**Local:**
```bash
uv run main.py
```

**Docker Compose:**
```bash
docker compose --profile scraper up
```

#### 🔍 Legacy: Search Mode

**Local:**
```bash
ALPHABET=abc uv run main.py --search
```

**Docker Compose:**
```bash
docker compose --profile search up
```

---

### RAG API

> **Note:** The API needs PDFs in the `downloads/` directory to work. Run the **Scraper** first (or manually add PDFs).

#### 1. Start RAG API + Qdrant

```bash
docker compose --profile api up --build
```

On startup, the API will:
1. Check for unindexed PDFs in `downloads/`
2. Start background sync (parse PDFs with Vision, generate embeddings)
3. API is immediately available while sync runs

#### 2. Monitor Sync Status

```bash
curl http://localhost:8000/sync/status
```

#### 3. Query the API

**Ask a question:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Who visited the island?"}'
```

**Response:**
```json
{
  "answer": "Based on the documents...",
  "sources": [
    {
      "filename": "EFTA00001234.pdf",
      "score": 0.89,
      "preview": "Flight log showing..."
    }
  ]
}
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (includes sync status) |
| `GET` | `/stats` | Index statistics |
| `POST` | `/sync` | Trigger background sync |
| `GET` | `/sync/status` | Check sync progress |
| `POST` | `/ask` | Ask a question |

---

## Docker Compose

### Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| `scraper` | scraper-scan | Download PDFs from DOJ |
| `search` | scraper-search | Legacy search mode |
| `api` | qdrant, api | RAG API + Vector DB |

### Commands

```bash
# Run scraper
docker compose --profile scraper up

# Start RAG API + Qdrant
docker compose --profile api up --build

# Stop all services (must specify profile if active)
docker compose --profile api down

# Stop and remove volumes (clean Qdrant data)
docker compose --profile api down -v
```

## Using Custom LLM Providers

### Ollama (Local)

```env
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_CHAT_MODEL=llava  # Vision model
```

### Azure OpenAI

```env
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/v1
OPENAI_CHAT_MODEL=gpt-4o-mini
```

## Dependencies

**Scraper:**
- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `loguru` - Logging
- `pydantic-settings` - Configuration

**RAG API:**
- `pdf2image` - PDF to image conversion
- `pillow` - Image processing
- `openai` - Vision, Embeddings & chat
- `qdrant-client` - Vector database
- `fastapi` - Web framework
- `uvicorn` - ASGI server

## 📦 Release

Images are automatically built and published to **Docker Hub** (`rodrigobrocchi/epstein_crawler_docs`) when a new tag is pushed.

```bash
git tag v1.0.6
git push origin v1.0.6
```

## License

MIT

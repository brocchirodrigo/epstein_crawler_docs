# Epstein Files Scraper & RAG API (Docker Edition)

A specialized toolset for analyzing the U.S. Department of Justice Epstein Files. Includes an automated scraper and a RAG (Retrieval-Augmented Generation) API powered by OpenAI/Ollama and Qdrant.

## 🚀 Key Features

- **🛡️ Scraper**: Automated PDF download from DOJ, bypassing age verification and bot detection.
- **🧠 RAG API**: Ask questions about the documents using natural language.
- **👁️ Vision**: Uses GPT-4o-mini (or compatible models) to read text and understand images in PDFs.
- **⚡ Vector Search**: Powered by Qdrant.
- **🔄 Background Sync**: Automatically indexes PDFs as they are downloaded.

## ⚙️ Standard Workflow

1.  **Scrape**: Run the `scraper-scan` service to download PDFs from the DOJ website into the `./downloads` folder.
2.  **Index**: Start the `api` service. It detects new PDFs in `./downloads`, reads them with Vision AI, and stores embeddings in Qdrant.
3.  **Query**: Use the `/ask` endpoint to query the documents.

## 🐳 Usage (Docker Compose)

The recommended way to run is via Docker Compose, using **profiles** to select the desired service.

### `docker-compose.yml` Example

```yaml
services:
  # 1. Scraper Service (Optional)
  scraper-scan:
    image: rodrigobrocchi/epstein_crawler_docs:latest
    container_name: epstein_scraper_scan
    volumes:
      - ./downloads:/app/downloads      # Persist PDFs
      - ./logs:/app/logs
    shm_size: 2gb
    restart: "no"
    user: root
    profiles: ["scraper"]

  # 2. Vector DB (Required for API)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: epstein_qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage     # Persist Vectors
    restart: unless-stopped
    profiles: ["api"]

  # 3. RAG API Service
  api:
    image: rodrigobrocchi/epstein_crawler_docs:latest
    container_name: epstein_api
    command: ["api"]
    ports:
      - "8000:8000"
    volumes:
      - ./downloads:/app/downloads      # Read PDFs
    environment:
      - OPENAI_API_KEY=sk-your-key-here
      - OPENAI_VISION_MODEL=gpt-4o-mini
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    shm_size: 4gb
    depends_on:
      - qdrant
    profiles: ["api"]

volumes:
  qdrant_data:
```

### 📥 1. Run Scraper (Download PDFs)

Downloads PDFs from the DOJ website to the `./downloads` folder.

```bash
docker compose --profile scraper up
```

### 🧠 2. Start RAG API + Qdrant

Starts the API and the Vector Database. It will automatically scan and index any PDFs found in `./downloads`.

```bash
docker compose --profile api up
```

- **API URL**: `http://localhost:8000`
- **Docs**: `http://localhost:8000/docs`

### 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (includes sync status) |
| `GET` | `/stats` | Index statistics |
| `POST` | `/sync` | Trigger background sync |
| `GET` | `/sync/status` | Check sync progress |
| `POST` | `/ask` | Ask a question |

### 🧹 Cleaning Up

To stop services and **remove Qdrant data**:

```bash
# Stop services
docker compose --profile api down

# Stop AND remove volumes (resets database)
docker compose --profile api down -v
```

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key (or "ollama" for local) |
| `OPENAI_BASE_URL` | (none) | Custom API URL (e.g. for Ollama / Azure) |
| `OPENAI_EMBEDDING_DIMENSION` | `1536` | Dimension of the embedding model |
| `OPENAI_CHAT_MODEL` | `gpt-5-mini` | Chat model for Q&A |
| `OPENAI_VISION_MODEL` | `gpt-4o-mini` | Vision model for PDF parsing |
| `QDRANT_HOST` | `qdrant` | Hostname of Qdrant service |
| `MAX_DOWNLOADS` | (unlimited) | Limit scraper downloads |

## 📜 License

MIT License. For educational and research purposes only.

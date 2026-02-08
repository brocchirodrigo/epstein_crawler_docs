# Epstein Files Scraper

A Python-based web scraper that downloads PDF documents from the U.S. Department of Justice Epstein Library.

## Features

- **Automated Browser Control**: Uses Playwright to bypass bot detection and age verification.
- **DOJ Disclosures Scan (Default)**: Automatically navigates the disclosures page, expands the transparency act menu, and downloads datasets.
- **Legacy Alphabet Search**: Optional mode to search through documents using letter-based queries.
- **Deduplication**: Removes duplicate files before downloading.
- **Session-Based Downloads**: Uses authenticated browser session for PDF downloads.
- **Error Logging**: Saves errors to log files for debugging.

## Project Structure

```
eua_gov/
├── src/
│   ├── __init__.py         # Package exports
│   ├── app.py              # Application orchestrator
│   ├── config.py           # Pydantic Settings configuration
│   ├── logging_config.py   # Loguru setup
│   ├── scraper.py          # Web scraping logic
│   └── downloader.py       # PDF download logic
├── downloads/              # Downloaded PDF files
├── logs/                   # Log files
├── main.py                 # Entry point
├── .env                    # Environment configuration
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose
├── docker-entrypoint.sh    # Docker entrypoint with Xvfb
├── epstein_urls.json       # Collected URLs
├── pyproject.toml          # Dependencies
└── README.md
```

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
cd epstein_crawler_docs

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

## Configuration

You can configure the scraper using environment variables. These are optional as sensible defaults are provided.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_DOWNLOADS` | int | `None` (unlimited) | Max files to download |
| `BASE_URL` | string | `https://www.justice.gov` | Base URL for scraping |
| `NAVIGATION_TIMEOUT` | int | `60000` | Navigation timeout in ms |
| `VIEWPORT_WIDTH` | int | `1920` | Browser viewport width |
| `VIEWPORT_HEIGHT` | int | `1080` | Browser viewport height |
| `ALPHABET` | string | `abcdefghijklmnopqrstuvwxyz` | Letters to search (Legacy Mode only) |
| `MAX_PAGES_PER_LETTER` | int | `None` (unlimited) | Max result pages per letter (Legacy Mode only) |

> **Note**: The browser always runs in GUI mode (headless=false) because the site blocks headless browsers.

### Example `.env` for testing

```env
MAX_DOWNLOADS=10
```

## Usage

### 🚀 Default: Scan Mode (DOJ Disclosures)
This is the new default method. It navigates to the DOJ Disclosures page, handles the "Epstein Files Transparency Act" menu, and downloads all datasets.

**Local:**
```bash
uv run main.py
```

**Docker Compose:**
```bash
# Builds and runs the default 'scraper-scan' service
docker compose up --build
```

### 🔍 Legacy: Search Mode
This method iterates through letters of the alphabet to find documents (old behavior).

**Local:**
```bash
# Example: Search only letters A, B, and C
ALPHABET=abc uv run main.py --search
```

**Docker Compose:**
```bash
# Runs the 'scraper-search' service (one-off container)
docker compose run --rm scraper-search

# OR with custom environment variables
docker compose run -e ALPHABET=abc --rm scraper-search
```

## Docker Instructions

### Detailed Usage

1.  **Run Scan Mode (Default)**:
    ```bash
    docker compose up
    ```

2.  **Run Legacy Search Mode**:
    ```bash
    docker compose run --rm scraper-search
    ```

3.  **Run Both Modes**:
    ```bash
    # '--profile all' enables the search service, and 'up' starts default + enabled
    docker compose --profile all up
    ```

4.  **Stop & Clean**:
    ```bash
    docker compose down
    ```

### Output Directory

- **epstein_urls.json**: JSON file with all collected PDF URLs.
- **downloads/**: Directory containing downloaded PDF files.
- **logs/**: Log files.

- **epstein_urls.json**: JSON file with all collected PDF URLs
- **downloads/**: Directory containing downloaded PDF files
- **logs/**: Log files
  - `scraper_YYYY-MM-DD.log` - Warnings and errors
  - `errors_YYYY-MM-DD.log` - Critical errors only

## Dependencies

- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `lxml` - XML parser
- `loguru` - Logging
- `pydantic-settings` - Configuration management

## 📦 Release

Images are automatically built and published to **Docker Hub** (`rodrigobrocchi/epstein_crawler_docs`) when a new tag is pushed.

### How to Release

1. Update version in `pyproject.toml`

2. Tag the commit:

    ```bash
    git tag v1.0.1
    git push origin v1.0.1
    ```

3. The workflow will build and push:
    - `rodrigobrocchi/epstein_crawler_docs:latest`

## License

MIT

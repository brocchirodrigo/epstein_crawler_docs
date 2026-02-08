# Epstein Files Scraper

A Python-based web scraper that downloads PDF documents from the U.S. Department of Justice Epstein Library.

## Features

- **Automated Browser Control**: Uses Playwright to bypass bot detection and age verification
- **Alphabet-Based Search**: Searches through documents using letter-based queries
- **Pagination Handling**: Automatically navigates through multiple result pages
- **Deduplication**: Removes duplicate files before downloading
- **Session-Based Downloads**: Uses authenticated browser session for PDF downloads
- **Error Logging**: Saves errors to log files for debugging

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

## Environment Variables

Create a `.env` file in the project root:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALPHABET` | string | `abcdefghijklmnopqrstuvwxyz` | Letters to search (e.g., `abc` for only A, B, C) |
| `MAX_PAGES_PER_LETTER` | int | `None` (unlimited) | Max result pages per letter |
| `MAX_DOWNLOADS` | int | `None` (unlimited) | Max files to download |
| `BASE_URL` | string | `https://www.justice.gov` | Base URL for scraping |
| `NAVIGATION_TIMEOUT` | int | `60000` | Navigation timeout in ms |
| `VIEWPORT_WIDTH` | int | `1920` | Browser viewport width |
| `VIEWPORT_HEIGHT` | int | `1080` | Browser viewport height |

> **Note**: The browser always runs in GUI mode (headless=false) because the site blocks headless browsers.

### Example `.env` for testing

```env
ALPHABET=abc
MAX_PAGES_PER_LETTER=2
MAX_DOWNLOADS=10
```

### Example `.env` for full scrape

```env
# Leave empty for unlimited - all letters, all pages, all downloads
```

## Usage

### Local Execution

```bash
uv run main.py
```

### Docker

Docker uses Xvfb (virtual display) to run the browser in GUI mode without requiring a real display.

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f
```

## Output

- **epstein_urls.json**: JSON file with all collected PDF URLs
- **downloads/**: Directory containing downloaded PDF files
- **logs/**: Log files
  - `scraper_YYYY-MM-DD.log` - Warnings and errors
  - `errors_YYYY-MM-DD.log` - Critical errors only

## How It Works

1. **Gate Passing**: Automatically clicks through robot verification and age confirmation
2. **Search**: Searches for each letter in the document library
3. **Collection**: Extracts PDF links from search results, navigating through pagination
4. **Deduplication**: Removes duplicate URLs based on file URL
5. **Download**: Downloads unique PDFs using the authenticated browser session

## Dependencies

- `playwright` - Browser automation
- `beautifulsoup4` - HTML parsing
- `lxml` - XML parser
- `loguru` - Logging
- `pydantic-settings` - Configuration management

## License

MIT

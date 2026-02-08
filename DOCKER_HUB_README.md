# Epstein Files Scraper (Docker Edition)

A specialized web scraper for the U.S. Department of Justice Epstein Files library (`https://www.justice.gov/epstein`). This image comes pre-configured with **Playwright**, **stealth patches**, and **Xvfb**, allowing it to bypass sophisticated bot detection and run in headless environments (like servers) where standard headless browsers fail.

## 🚀 Key Features

-   **Anti-Detection**: Built-in stealth patches to bypass bot protections.
-   **Headless Bypass (Xvfb)**: Runs a virtual display server (Xvfb) inside the container. This tricks the site into thinking it's running on a real desktop, bypassing strict "headless browser" blocks.
-   **Automated Workflow**: Handles age verification ("I am 18+"), pagination, alphabet-based search, and PDF downloading.
-   **Smart Logic**: Deduplicates files and logs errors efficiently.

## 🐳 Usage

### Quick Start (Docker Run)

Run the scraper and mount a local directory to save the downloaded PDFs:

```bash
docker run --rm -it \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  rodrigobrocchi/epstein_crawler_docs:latest
```

### Using Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  scraper:
    image: rodrigobrocchi/epstein_crawler_docs:latest
    container_name: epstein_scraper
    volumes:
      - ./downloads:/app/downloads  # Where PDFs will be saved
      - ./logs:/app/logs            # Where logs will be saved
    environment:
      - ALPHABET=abc                # Optional: Letters to search (default: a-z)
      - MAX_PAGES_PER_LETTER=2      # Optional: Limit pages per letter
      # - MAX_DOWNLOADS=10          # Optional: Limit total downloads
    shm_size: 2gb                   # Important for browser stability
```

Then run:

```bash
docker-compose up
```

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALPHABET` | `abcdefghijklmnopqrstuvwxyz` | Letters to search. Set to `a` or `abc` for partial scrapes. |
| `MAX_PAGES_PER_LETTER` | `None` (Unlimited) | Crawl only N pages per letter. Good for testing. |
| `MAX_DOWNLOADS` | `None` (Unlimited) | Stop after downloading N files. |
| `NAVIGATION_TIMEOUT` | `60000` | Timeout in ms for page loads. |

## ⚠️ Notes

-   **Headless Mode**: The container runs Xvfb by default. You do **not** need to set any headless flags. The application is hardcoded to run in GUI mode (which Xvfb simulates) to bypass detection.
-   **Memory**: It is recommended to set `shm_size: 2gb` to prevent Chromum from crashing on large pages.

## 📜 License

MIT License. For educational and research purposes only.

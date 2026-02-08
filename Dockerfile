FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && uv sync --frozen && rm -rf /root/.cache/uv

COPY src/ ./src/
COPY main.py ./
COPY docker-entrypoint.sh ./

RUN mkdir -p downloads logs && chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]

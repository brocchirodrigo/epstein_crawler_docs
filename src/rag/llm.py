"""
LLM Client wrapper with configurable base URL.

Supports OpenAI and OpenAI-compatible APIs (Ollama, Azure, etc).
"""

from openai import OpenAI

from ..config import rag_settings


def get_llm_client(base_url: str | None = None) -> OpenAI:
    """
    Get an OpenAI client with optional custom base URL.

    Args:
        base_url: Custom API base URL. If None, uses config or OpenAI default.
                  Examples:
                  - "http://localhost:11434/v1" for Ollama
                  - "https://your-azure.openai.azure.com/v1" for Azure
                  - None for OpenAI (default)

    Returns:
        OpenAI client configured for the specified endpoint.
    """
    url = base_url or rag_settings.openai_base_url
    api_key = rag_settings.openai_api_key or "ollama"

    if not api_key and not url:
        raise ValueError("OPENAI_API_KEY is required when using OpenAI API")

    client_kwargs = {"api_key": api_key}

    if url:
        client_kwargs["base_url"] = url

    return OpenAI(**client_kwargs)

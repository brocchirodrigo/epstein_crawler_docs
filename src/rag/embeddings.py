"""
Embeddings wrapper.

Generates vector embeddings for text chunks.
Supports both OpenAI (batch) and Ollama (one-by-one) APIs.
"""

from ..config import rag_settings
from ..logging_config import logger
from .llm import get_llm_client


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    client = get_llm_client()
    is_ollama = bool(rag_settings.openai_base_url)

    logger.info(f"Generating embeddings for {len(texts)} chunks...")

    all_embeddings = []

    if is_ollama:
        for i, text in enumerate(texts, 1):
            response = client.embeddings.create(
                model=rag_settings.openai_embedding_model,
                input=text,
            )
            all_embeddings.append(response.data[0].embedding)

            if i % 10 == 0 or i == len(texts):
                logger.info(f"Embedded {i}/{len(texts)}")
    else:
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = client.embeddings.create(
                model=rag_settings.openai_embedding_model,
                input=batch,
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            logger.info(
                f"Embedded batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}"
            )

    return all_embeddings


def get_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text string to embed.

    Returns:
        Embedding vector.
    """
    client = get_llm_client()

    response = client.embeddings.create(
        model=rag_settings.openai_embedding_model,
        input=text,
    )

    return response.data[0].embedding

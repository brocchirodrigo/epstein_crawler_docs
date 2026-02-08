"""
PDF parser using Vision LLM.

Converts PDF pages to images and uses a vision model to extract text and describe images.
"""

import base64
import io
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image

from ..config import rag_settings
from ..logging_config import logger
from .llm import get_llm_client

DPI = 150
MAX_IMAGE_SIZE = (768, 768)


def _image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

    if image.mode != "RGB":
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def _extract_text_from_image(client, image_b64: str, page_num: int) -> str:
    """Extract text from a page image using vision model."""
    vision_model = rag_settings.openai_vision_model or rag_settings.openai_chat_model
    response = client.chat.completions.create(
        model=vision_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document OCR assistant. Extract ALL text from the image. "
                    "If there are images, photos, signatures, or diagrams, describe them briefly. "
                    "Preserve the document structure (headings, paragraphs, lists). "
                    "Output plain text only, no markdown formatting."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {
                        "type": "text",
                        "text": f"Extract all text from page {page_num}. Describe any images or handwritten content.",
                    },
                ],
            },
        ],
        max_completion_tokens=4096,
    )

    return response.choices[0].message.content or ""


def parse_pdf(pdf_path: Path) -> str:
    """
    Parse a PDF using vision model.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text from the PDF.
    """
    if not rag_settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for PDF parsing")

    logger.info(f"Parsing {pdf_path.name}...")

    try:
        images = convert_from_path(pdf_path, dpi=DPI)
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        raise

    max_pages = rag_settings.max_pages_per_pdf
    if max_pages > 0 and len(images) > max_pages:
        logger.warning(
            f"{pdf_path.name} has {len(images)} pages, limiting to {max_pages}"
        )
        images = images[:max_pages]

    logger.info(f"Processing {len(images)} pages...")

    client = get_llm_client()

    all_text = []
    for i, image in enumerate(images, 1):
        try:
            image_b64 = _image_to_base64(image)
            text = _extract_text_from_image(client, image_b64, i)
            all_text.append(f"--- Page {i} ---\n{text}")
            logger.debug(f"  Page {i}/{len(images)} extracted")
        except Exception as e:
            logger.warning(f"  Page {i} failed: {e}")
            all_text.append(f"--- Page {i} ---\n[Error extracting text: {e}]")

    full_text = "\n\n".join(all_text)
    logger.info(
        f"Parsed {pdf_path.name}: {len(full_text)} characters from {len(images)} pages"
    )

    return full_text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk.
        chunk_size: Target size of each chunk in characters.
        overlap: Overlap between chunks.

    Returns:
        List of text chunks.
    """
    if not text or len(text) < chunk_size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                sentence_break = text.rfind(". ", start, end)
                if sentence_break > start + chunk_size // 2:
                    end = sentence_break + 2

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]

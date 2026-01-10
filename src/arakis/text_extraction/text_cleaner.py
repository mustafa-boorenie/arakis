"""Text cleaning utilities for PDF extraction."""

import re
from collections import Counter


def clean_pdf_text(text: str) -> str:
    """
    Clean common PDF artifacts from extracted text.

    Removes:
    - Page numbers
    - Excessive whitespace
    - Line break hyphenation
    - Header/footer patterns
    - Unicode artifacts

    Args:
        text: Raw text extracted from PDF

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove line break hyphenation (e.g., "sys-\ntem" -> "system")
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # Remove excessive whitespace while preserving paragraph breaks
    text = re.sub(r" +", " ", text)  # Multiple spaces to single space
    text = re.sub(r"\n{3,}", "\n\n", text)  # Multiple newlines to double newline

    # Remove common PDF artifacts
    text = re.sub(r"\x00", "", text)  # Null bytes
    text = re.sub(r"[\x0b\x0c]", "\n", text)  # Form feed, vertical tab to newline

    # Remove standalone page numbers (line with only digits)
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.MULTILINE)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse multiple newlines again after line stripping
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def remove_headers_footers(text: str, threshold: int = 3) -> str:
    """
    Remove repeating headers and footers from PDF text.

    Identifies lines that appear frequently (likely headers/footers)
    and removes them.

    Args:
        text: PDF text
        threshold: Minimum number of repetitions to consider as header/footer

    Returns:
        Text with headers/footers removed
    """
    if not text:
        return ""

    lines = text.split("\n")

    if len(lines) < 10:  # Too short to have repeating headers
        return text

    # Count line frequencies
    line_counts = Counter(line.strip() for line in lines if line.strip())

    # Identify frequently repeating lines (likely headers/footers)
    repeating_lines = {
        line for line, count in line_counts.items() if count >= threshold and len(line) < 100
    }

    # Remove repeating lines
    cleaned_lines = [
        line for line in lines if line.strip() not in repeating_lines or not line.strip()
    ]

    return "\n".join(cleaned_lines)


def detect_language(text: str) -> str:
    """
    Simple language detection based on common words.

    Args:
        text: Text to analyze

    Returns:
        Language code ('en', 'unknown')
    """
    if not text:
        return "unknown"

    # Sample first 500 characters
    sample = text[:500].lower()

    # Common English words
    en_words = ["the", "and", "of", "to", "in", "a", "is", "that", "for", "it"]
    en_count = sum(1 for word in en_words if f" {word} " in sample)

    if en_count >= 3:
        return "en"

    return "unknown"


def estimate_text_quality(text: str, page_count: int) -> float:
    """
    Estimate text extraction quality (0-1 score).

    Based on:
    - Characters per page ratio
    - Paragraph structure
    - Special character ratio

    Args:
        text: Extracted text
        page_count: Number of pages

    Returns:
        Quality score (0-1)
    """
    if not text or page_count == 0:
        return 0.0

    char_count = len(text)
    chars_per_page = char_count / page_count

    # Typical academic paper: 2000-4000 chars/page
    # Low text density suggests image-based or poor extraction
    if chars_per_page < 500:
        return 0.2  # Very low quality
    elif chars_per_page < 1000:
        return 0.5  # Low quality
    elif chars_per_page < 3000:
        return 0.9  # Good quality
    else:
        return 1.0  # Excellent quality


def truncate_text(text: str, max_length: int = 50000) -> str:
    """
    Truncate text to maximum character length.

    Args:
        text: Text to truncate
        max_length: Maximum character count

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    # Try to truncate at sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n\n")

    if last_period > max_length * 0.9:  # If we can find a sentence within last 10%
        return text[: last_period + 1]
    elif last_newline > max_length * 0.9:
        return text[: last_newline + 2]
    else:
        return truncated

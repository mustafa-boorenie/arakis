"""PDF text extraction module."""

from arakis.text_extraction.exceptions import (
    PDFCorruptedError,
    PDFEncryptedError,
    PDFExtractionError,
    PDFNoTextError,
)
from arakis.text_extraction.pdf_parser import (
    PDFExtractionResult,
    PDFParser,
    extract_text_from_pdf,
)
from arakis.text_extraction.text_cleaner import (
    clean_pdf_text,
    detect_language,
    estimate_text_quality,
    remove_headers_footers,
    truncate_text,
)

__all__ = [
    # Parser
    "PDFParser",
    "PDFExtractionResult",
    "extract_text_from_pdf",
    # Exceptions
    "PDFExtractionError",
    "PDFEncryptedError",
    "PDFCorruptedError",
    "PDFNoTextError",
    # Text cleaning
    "clean_pdf_text",
    "remove_headers_footers",
    "detect_language",
    "estimate_text_quality",
    "truncate_text",
]

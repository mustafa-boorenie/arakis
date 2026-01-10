"""Custom exceptions for PDF text extraction."""


class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""

    pass


class PDFEncryptedError(PDFExtractionError):
    """Raised when PDF is encrypted and cannot be read."""

    pass


class PDFCorruptedError(PDFExtractionError):
    """Raised when PDF is corrupted or malformed."""

    pass


class PDFNoTextError(PDFExtractionError):
    """Raised when PDF contains no extractable text (likely image-only)."""

    pass

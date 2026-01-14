"""PDF text extraction with waterfall fallback strategy."""

import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from arakis.text_extraction.exceptions import (
    PDFCorruptedError,
    PDFEncryptedError,
    PDFExtractionError,
    PDFNoTextError,
)
from arakis.text_extraction.text_cleaner import (
    clean_pdf_text,
    estimate_text_quality,
    remove_headers_footers,
)


@dataclass
class PDFExtractionResult:
    """Result from PDF text extraction."""

    success: bool
    text: str | None
    page_count: int
    extraction_method: str  # "pymupdf", "pdfplumber", "failed"
    extraction_time_ms: int
    char_count: int
    quality_score: float  # 0-1
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


class PDFParser:
    """
    Robust PDF text extractor with waterfall fallback strategy.

    Tries multiple extraction methods in order:
    1. PyMuPDF (fitz) - Fast and handles most cases
    2. pdfplumber - Better for complex tables
    3. OCR (pytesseract) - For image-based PDFs
    4. Fail gracefully with error message
    """

    def __init__(self, clean: bool = True, remove_repeating: bool = True, use_ocr: bool = True):
        """
        Initialize PDF parser.

        Args:
            clean: Apply text cleaning (remove artifacts)
            remove_repeating: Remove repeating headers/footers
            use_ocr: Enable OCR fallback for image-based PDFs
        """
        self.clean = clean
        self.remove_repeating = remove_repeating
        self.use_ocr = use_ocr

    async def extract_text(
        self,
        pdf_source: str | bytes | Path | BinaryIO,
        clean: bool | None = None,
    ) -> PDFExtractionResult:
        """
        Extract text from PDF with waterfall fallback.

        Args:
            pdf_source: PDF file path, bytes, or file-like object
            clean: Override cleaning setting (None = use instance setting)

        Returns:
            PDFExtractionResult with extracted text and metadata
        """
        start_time = time.time()
        clean_text = clean if clean is not None else self.clean

        # Convert source to bytes for processing
        pdf_bytes = self._to_bytes(pdf_source)

        # Try PyMuPDF first (fastest, handles most cases)
        try:
            result = await self._extract_with_pymupdf(pdf_bytes, clean_text)
            if result.success:
                return result
        except Exception as e:
            # Log and continue to fallback
            warnings = [f"PyMuPDF failed: {str(e)}"]

        # Try pdfplumber as fallback
        try:
            result = await self._extract_with_pdfplumber(pdf_bytes, clean_text)
            if result.success:
                result.warnings.extend(warnings)
                return result
        except Exception as e:
            warnings.append(f"pdfplumber failed: {str(e)}")

        # Try OCR as final fallback if enabled
        if self.use_ocr:
            try:
                result = await self._extract_with_ocr(pdf_bytes, clean_text)
                if result.success:
                    result.warnings.extend(warnings)
                    result.warnings.append("Text extracted using OCR (image-based PDF)")
                    return result
            except Exception as e:
                warnings.append(f"OCR failed: {str(e)}")

        # All methods failed
        elapsed_ms = int((time.time() - start_time) * 1000)
        return PDFExtractionResult(
            success=False,
            text=None,
            page_count=0,
            extraction_method="failed",
            extraction_time_ms=elapsed_ms,
            char_count=0,
            quality_score=0.0,
            error="All extraction methods failed",
            warnings=warnings,
        )

    async def _extract_with_pymupdf(self, pdf_bytes: bytes, clean: bool) -> PDFExtractionResult:
        """
        Extract text using PyMuPDF (fitz).

        Args:
            pdf_bytes: PDF content as bytes
            clean: Apply text cleaning

        Returns:
            PDFExtractionResult

        Raises:
            PDFEncryptedError: If PDF is encrypted
            PDFCorruptedError: If PDF is corrupted
            PDFNoTextError: If no text found
        """
        start_time = time.time()

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise PDFExtractionError("PyMuPDF not installed. Run: pip install pymupdf")

        try:
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Check if encrypted
            if doc.is_encrypted:
                doc.close()
                raise PDFEncryptedError("PDF is encrypted")

            page_count = doc.page_count
            if page_count == 0:
                doc.close()
                raise PDFCorruptedError("PDF has no pages")

            # Extract text from all pages
            text_parts = []
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)

            doc.close()

            # Combine all text
            raw_text = "\n\n".join(text_parts)

            if len(raw_text.strip()) < 100:
                raise PDFNoTextError(
                    f"Minimal text extracted ({len(raw_text)} chars). Likely image-based PDF."
                )

            # Clean text if requested
            if clean:
                text = clean_pdf_text(raw_text)
                if self.remove_repeating:
                    text = remove_headers_footers(text)
            else:
                text = raw_text

            # Calculate quality
            quality = estimate_text_quality(text, page_count)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Generate warnings
            warnings = []
            if quality < 0.5:
                warnings.append(
                    f"Low text density ({len(text) / page_count:.0f} chars/page). "
                    "May be image-based PDF."
                )

            return PDFExtractionResult(
                success=True,
                text=text,
                page_count=page_count,
                extraction_method="pymupdf",
                extraction_time_ms=elapsed_ms,
                char_count=len(text),
                quality_score=quality,
                warnings=warnings,
            )

        except (PDFEncryptedError, PDFCorruptedError, PDFNoTextError):
            raise
        except Exception as e:
            raise PDFExtractionError(f"PyMuPDF extraction failed: {str(e)}")

    async def _extract_with_pdfplumber(self, pdf_bytes: bytes, clean: bool) -> PDFExtractionResult:
        """
        Extract text using pdfplumber (fallback method).

        Args:
            pdf_bytes: PDF content as bytes
            clean: Apply text cleaning

        Returns:
            PDFExtractionResult

        Raises:
            PDFExtractionError: If extraction fails
        """
        start_time = time.time()

        try:
            import pdfplumber
        except ImportError:
            raise PDFExtractionError("pdfplumber not installed. Run: pip install pdfplumber")

        try:
            # Open PDF from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf = pdfplumber.open(pdf_file)

            page_count = len(pdf.pages)
            if page_count == 0:
                pdf.close()
                raise PDFCorruptedError("PDF has no pages")

            # Extract text from all pages
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text)

            pdf.close()

            # Combine all text
            raw_text = "\n\n".join(text_parts)

            if len(raw_text.strip()) < 100:
                raise PDFNoTextError(
                    f"Minimal text extracted ({len(raw_text)} chars). Likely image-based PDF."
                )

            # Clean text if requested
            if clean:
                text = clean_pdf_text(raw_text)
                if self.remove_repeating:
                    text = remove_headers_footers(text)
            else:
                text = raw_text

            # Calculate quality
            quality = estimate_text_quality(text, page_count)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Generate warnings
            warnings = []
            if quality < 0.5:
                warnings.append(
                    f"Low text density ({len(text) / page_count:.0f} chars/page). "
                    "May be image-based PDF."
                )

            return PDFExtractionResult(
                success=True,
                text=text,
                page_count=page_count,
                extraction_method="pdfplumber",
                extraction_time_ms=elapsed_ms,
                char_count=len(text),
                quality_score=quality,
                warnings=warnings,
            )

        except (PDFCorruptedError, PDFNoTextError):
            raise
        except Exception as e:
            raise PDFExtractionError(f"pdfplumber extraction failed: {str(e)}")

    async def _extract_with_ocr(self, pdf_bytes: bytes, clean: bool) -> PDFExtractionResult:
        """
        Extract text using OCR (Optical Character Recognition).

        This is the fallback for image-based PDFs where normal text
        extraction fails. It's slower but handles scanned documents.

        Args:
            pdf_bytes: PDF content as bytes
            clean: Apply text cleaning

        Returns:
            PDFExtractionResult

        Raises:
            PDFExtractionError: If OCR fails
        """
        start_time = time.time()

        try:
            import pytesseract
            from pdf2image import convert_from_bytes
        except ImportError:
            raise PDFExtractionError(
                "OCR libraries not installed. Run: pip install pytesseract pdf2image"
            )

        try:
            # Convert PDF pages to images
            # Use lower DPI for speed (200 is good balance)
            images = convert_from_bytes(pdf_bytes, dpi=200)
            page_count = len(images)

            if page_count == 0:
                raise PDFCorruptedError("PDF has no pages")

            # Run OCR on each page
            text_parts = []
            for img in images:
                # pytesseract.image_to_string returns text from image
                page_text = pytesseract.image_to_string(img, lang="eng")
                if page_text.strip():
                    text_parts.append(page_text)

            # Combine all text
            raw_text = "\n\n".join(text_parts)

            if len(raw_text.strip()) < 100:
                raise PDFNoTextError(
                    f"Minimal text extracted via OCR ({len(raw_text)} chars). "
                    "PDF may be blank or unreadable."
                )

            # Clean text if requested
            if clean:
                text = clean_pdf_text(raw_text)
                if self.remove_repeating:
                    text = remove_headers_footers(text)
            else:
                text = raw_text

            # Calculate quality (OCR quality is usually lower)
            quality = estimate_text_quality(text, page_count)

            elapsed_ms = int((time.time() - start_time) * 1000)

            return PDFExtractionResult(
                success=True,
                text=text,
                page_count=page_count,
                extraction_method="ocr",
                extraction_time_ms=elapsed_ms,
                char_count=len(text),
                quality_score=quality * 0.8,  # Reduce quality score for OCR (less reliable)
                warnings=[],
            )

        except (PDFCorruptedError, PDFNoTextError):
            raise
        except Exception as e:
            raise PDFExtractionError(f"OCR extraction failed: {str(e)}")

    def _to_bytes(self, source: str | bytes | Path | BinaryIO) -> bytes:
        """
        Convert various source types to bytes.

        Args:
            source: PDF source (file path, bytes, or file-like)

        Returns:
            PDF content as bytes

        Raises:
            PDFExtractionError: If source is invalid
        """
        if isinstance(source, bytes):
            return source

        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise PDFExtractionError(f"PDF file not found: {path}")
            return path.read_bytes()

        # File-like object
        if hasattr(source, "read"):
            data = source.read()
            if isinstance(data, bytes):
                return data
            elif isinstance(data, str):
                return data.encode("utf-8")

        raise PDFExtractionError(f"Invalid PDF source type: {type(source)}")


# Convenience function
async def extract_text_from_pdf(
    pdf_source: str | bytes | Path | BinaryIO,
    clean: bool = True,
) -> PDFExtractionResult:
    """
    Extract text from PDF (convenience function).

    Args:
        pdf_source: PDF file path, bytes, or file-like object
        clean: Apply text cleaning

    Returns:
        PDFExtractionResult
    """
    parser = PDFParser(clean=clean)
    return await parser.extract_text(pdf_source, clean=clean)

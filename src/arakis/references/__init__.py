"""Reference management submodule for Arakis.

This module provides tools for managing academic citations and references:
- Citation formatting in multiple styles (APA 6, APA 7, Vancouver, Chicago, Harvard)
- Citation extraction from generated text
- Reference validation and collection
- Reference list generation

Example usage:
    from arakis.references import ReferenceManager, CitationStyle

    # Create manager with APA 6 style (default)
    manager = ReferenceManager()

    # Or with a different style
    manager = ReferenceManager(style=CitationStyle.VANCOUVER)

    # Register papers
    for paper in papers:
        manager.register_paper(paper)

    # Validate citations in a section
    result = manager.validate_citations(section)
    if not result.valid:
        print(f"Missing: {result.missing_papers}")

    # Generate formatted reference list
    references = manager.generate_reference_list(section)
    for ref in references:
        print(f"{ref.number}. {ref.formatted_citation}")
"""

from arakis.references.extractor import CitationExtractor, ExtractedCitation
from arakis.references.formatter import CitationFormatter
from arakis.references.manager import (
    FormattedReference,
    ReferenceManager,
    ReferenceValidationResult,
)
from arakis.references.styles import CitationStyle, StyleConfig, get_style_config

__all__ = [
    # Styles
    "CitationStyle",
    "StyleConfig",
    "get_style_config",
    # Formatter
    "CitationFormatter",
    # Extractor
    "CitationExtractor",
    "ExtractedCitation",
    # Manager
    "ReferenceManager",
    "ReferenceValidationResult",
    "FormattedReference",
]

"""Citation extractor for parsing [Paper ID] citations from text."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedCitation:
    """A citation extracted from text.

    Attributes:
        paper_id: The paper identifier (DOI, PMID, etc.)
        start_pos: Start position in the text
        end_pos: End position in the text
        original_text: The original citation text including brackets
    """

    paper_id: str
    start_pos: int
    end_pos: int
    original_text: str


class CitationExtractor:
    """Extracts [Paper ID] citations from generated text.

    Supports various identifier formats:
    - DOI: [10.1234/abc], [doi:10.1234/abc]
    - PMID: [pmid:12345678], [PMID:12345678]
    - Semantic Scholar: [s2_xxxxx]
    - OpenAlex: [openalex_Wxxxxx]
    - Internal IDs: [paper_xxxxx]
    """

    # Pattern matches [Paper ID] format used by writing agents
    # Matches content between square brackets that isn't empty
    CITATION_PATTERN = re.compile(r"\[([^\[\]]+)\]")

    # Patterns that indicate a valid paper ID
    VALID_ID_PATTERNS = [
        re.compile(r"^10\.\d{4,}/.+"),  # DOI
        re.compile(r"^doi:10\.\d{4,}/.+", re.IGNORECASE),  # DOI with prefix
        re.compile(r"^pmid:\d+", re.IGNORECASE),  # PMID with prefix
        re.compile(r"^pmc\d+", re.IGNORECASE),  # PMCID
        re.compile(r"^s2_\w+"),  # Semantic Scholar
        re.compile(r"^openalex_\w+"),  # OpenAlex
        re.compile(r"^arxiv:\d+\.\d+", re.IGNORECASE),  # arXiv
        re.compile(r"^paper_\w+"),  # Internal paper ID
        re.compile(r"^perplexity_\w+"),  # Perplexity source ID
    ]

    # Patterns that indicate NON-citation brackets (to filter out)
    INVALID_PATTERNS = [
        re.compile(r"^\d+$"),  # Pure numbers like [1], [2]
        re.compile(r"^[a-z]$", re.IGNORECASE),  # Single letters like [a], [b]
        re.compile(r"^fig(ure)?\.?\s*\d+", re.IGNORECASE),  # Figure references
        re.compile(r"^tab(le)?\.?\s*\d+", re.IGNORECASE),  # Table references
        re.compile(r"^eq(uation)?\.?\s*\d+", re.IGNORECASE),  # Equation references
        re.compile(r"^sec(tion)?\.?\s*\d+", re.IGNORECASE),  # Section references
        re.compile(r"^app(endix)?\.?\s*[a-z\d]+", re.IGNORECASE),  # Appendix refs
        re.compile(r"^ref\.?\s*\d+", re.IGNORECASE),  # Ref. 1 style
        re.compile(r"^p\.?\s*\d+", re.IGNORECASE),  # Page references
        re.compile(r"^et al\.?", re.IGNORECASE),  # et al. in brackets
        re.compile(r"^emphasis|original|sic|italic", re.IGNORECASE),  # Editorial
        re.compile(r"^see\s+", re.IGNORECASE),  # "see Figure 1" style
        re.compile(r"^\d+[-–]\d+$"),  # Page ranges like [123-456]
    ]

    def extract_citations(self, text: str) -> list[ExtractedCitation]:
        """Extract all citations from text.

        Args:
            text: Generated text containing [Paper ID] citations

        Returns:
            List of extracted citations with positions
        """
        citations = []

        for match in self.CITATION_PATTERN.finditer(text):
            paper_id = match.group(1).strip()

            if self._is_valid_paper_id(paper_id):
                # Normalize the paper ID
                normalized_id = self._normalize_paper_id(paper_id)

                citations.append(
                    ExtractedCitation(
                        paper_id=normalized_id,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        original_text=match.group(0),
                    )
                )

        return citations

    def extract_unique_paper_ids(self, text: str) -> list[str]:
        """Extract unique paper IDs from text, preserving order of first appearance.

        Args:
            text: Generated text containing [Paper ID] citations

        Returns:
            List of unique paper IDs in order of appearance
        """
        citations = self.extract_citations(text)

        seen = set()
        unique_ids = []

        for citation in citations:
            if citation.paper_id not in seen:
                seen.add(citation.paper_id)
                unique_ids.append(citation.paper_id)

        return unique_ids

    def count_citations(self, text: str) -> int:
        """Count the number of citations in text.

        Args:
            text: Text to analyze

        Returns:
            Total citation count (including duplicates)
        """
        return len(self.extract_citations(text))

    def replace_citations_with_numbers(self, text: str, citation_order: list[str]) -> str:
        """Replace [Paper ID] citations with numbered references [1], [2], etc.

        Args:
            text: Text containing [Paper ID] citations
            citation_order: Ordered list of paper IDs defining the numbering

        Returns:
            Text with citations replaced by numbers
        """
        id_to_number = {pid: i + 1 for i, pid in enumerate(citation_order)}

        def replacer(match: re.Match) -> str:
            paper_id = match.group(1).strip()
            if not self._is_valid_paper_id(paper_id):
                return match.group(0)

            normalized = self._normalize_paper_id(paper_id)
            if normalized in id_to_number:
                return f"[{id_to_number[normalized]}]"
            return match.group(0)

        return self.CITATION_PATTERN.sub(replacer, text)

    def replace_citations_with_author_year(
        self, text: str, paper_lookup: dict[str, tuple[str, Optional[int]]]
    ) -> str:
        """Replace [Paper ID] with (Author, Year) format.

        Args:
            text: Text containing citations
            paper_lookup: Dict mapping paper_id to (author_string, year)

        Returns:
            Text with author-year citations
        """

        def replacer(match: re.Match) -> str:
            paper_id = match.group(1).strip()
            if not self._is_valid_paper_id(paper_id):
                return match.group(0)

            normalized = self._normalize_paper_id(paper_id)
            if normalized in paper_lookup:
                author, year = paper_lookup[normalized]
                if year:
                    return f"({author}, {year})"
                return f"({author})"
            return match.group(0)

        return self.CITATION_PATTERN.sub(replacer, text)

    def _is_valid_paper_id(self, text: str) -> bool:
        """Check if text looks like a paper ID.

        Args:
            text: Potential paper ID

        Returns:
            True if it appears to be a valid paper identifier
        """
        text = text.strip()

        if not text or len(text) < 3:
            return False

        # Check against invalid patterns first
        for pattern in self.INVALID_PATTERNS:
            if pattern.match(text):
                return False

        # Check if it matches any valid ID pattern
        for pattern in self.VALID_ID_PATTERNS:
            if pattern.match(text):
                return True

        # Heuristic: if it contains a forward slash (likely DOI) or underscore
        # (likely internal ID) and is reasonably long, accept it
        if ("/" in text or "_" in text) and len(text) > 5:
            return True

        # Accept IDs that look like author-year citations with DOI-like structure
        if "doi" in text.lower():
            return True

        return False

    def _normalize_paper_id(self, paper_id: str) -> str:
        """Normalize a paper ID to a consistent format.

        Args:
            paper_id: Raw paper ID

        Returns:
            Normalized paper ID
        """
        paper_id = paper_id.strip()

        # Remove common prefixes for consistency
        lower = paper_id.lower()
        if lower.startswith("doi:"):
            paper_id = paper_id[4:]
        elif lower.startswith("pmid:"):
            # Keep PMID prefix but normalize case
            paper_id = "pmid:" + paper_id[5:]
        elif lower.startswith("arxiv:"):
            paper_id = "arxiv:" + paper_id[6:]

        return paper_id

    # ==================== Numeric Citation Methods ====================

    # Pattern for numeric citations [1], [2], etc.
    NUMERIC_CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    def extract_numeric_citations(self, text: str) -> list[int]:
        """Extract numeric citations [1], [2], etc. from text.

        Args:
            text: Generated text containing [1], [2] style citations

        Returns:
            List of citation numbers in order of appearance
        """
        numbers = []
        for match in self.NUMERIC_CITATION_PATTERN.finditer(text):
            num = int(match.group(1))
            numbers.append(num)
        return numbers

    def extract_unique_numeric_citations(self, text: str) -> list[int]:
        """Extract unique numeric citations, preserving order of first appearance.

        Args:
            text: Generated text containing numeric citations

        Returns:
            List of unique citation numbers in order of appearance
        """
        numbers = self.extract_numeric_citations(text)
        seen = set()
        unique = []
        for num in numbers:
            if num not in seen:
                seen.add(num)
                unique.append(num)
        return unique

    def validate_numeric_citations(
        self, text: str, max_valid: int
    ) -> tuple[list[int], list[int]]:
        """Validate that all numeric citations are in valid range.

        Args:
            text: Text containing numeric citations
            max_valid: Maximum valid citation number (e.g., 3 means [1], [2], [3] are valid)

        Returns:
            Tuple of (valid_citations, invalid_citations)
        """
        all_citations = self.extract_unique_numeric_citations(text)
        valid = []
        invalid = []

        for num in all_citations:
            if 1 <= num <= max_valid:
                valid.append(num)
            else:
                invalid.append(num)

        return valid, invalid

    def remove_invalid_numeric_citations(
        self, text: str, max_valid: int
    ) -> tuple[str, list[int]]:
        """Remove invalid numeric citations from text.

        Args:
            text: Text containing numeric citations
            max_valid: Maximum valid citation number

        Returns:
            Tuple of (cleaned_text, removed_citations)
        """
        removed = []

        def replacer(match: re.Match) -> str:
            num = int(match.group(1))
            if 1 <= num <= max_valid:
                return match.group(0)  # Keep valid citations
            removed.append(num)
            return ""  # Remove invalid citations

        cleaned = self.NUMERIC_CITATION_PATTERN.sub(replacer, text)

        # Clean up any double spaces left by removed citations
        cleaned = re.sub(r"  +", " ", cleaned)
        # Clean up spaces before punctuation
        cleaned = re.sub(r" ([.,;:])", r"\1", cleaned)

        return cleaned, removed

    def convert_numeric_to_paper_ids(
        self, text: str, mapping: dict[int, str]
    ) -> str:
        """Convert numeric citations [1], [2] to paper ID citations [paper_id].

        Args:
            text: Text with numeric citations
            mapping: Dict mapping numbers to paper IDs, e.g., {1: "perplexity_abc123"}

        Returns:
            Text with paper ID citations
        """

        def replacer(match: re.Match) -> str:
            num = int(match.group(1))
            if num in mapping:
                return f"[{mapping[num]}]"
            return match.group(0)  # Keep as-is if not in mapping

        return self.NUMERIC_CITATION_PATTERN.sub(replacer, text)

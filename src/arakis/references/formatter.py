"""Citation formatter for various academic styles.

Supports APA 7 (default), APA 6, Vancouver, Chicago, and Harvard styles.
"""

import re

from arakis.models.paper import Author, Paper
from arakis.references.styles import CitationStyle, get_style_config


class CitationFormatter:
    """Formats citations in various academic styles.

    Default style is APA 7th Edition.
    """

    def __init__(self, style: CitationStyle = CitationStyle.APA_7):
        """Initialize the citation formatter.

        Args:
            style: Citation style to use (default: APA 7)
        """
        self.style = style
        self.config = get_style_config(style)

    def format_citation(self, paper: Paper) -> str:
        """Format a paper as a full reference citation.

        Args:
            paper: Paper to format

        Returns:
            Formatted citation string
        """
        if self.style == CitationStyle.APA_6:
            return self._format_apa6(paper)
        elif self.style == CitationStyle.APA_7:
            return self._format_apa7(paper)
        elif self.style == CitationStyle.VANCOUVER:
            return self._format_vancouver(paper)
        elif self.style == CitationStyle.CHICAGO:
            return self._format_chicago(paper)
        elif self.style == CitationStyle.HARVARD:
            return self._format_harvard(paper)
        else:
            return self._format_apa6(paper)

    def format_in_text(self, paper: Paper, include_year: bool = True) -> str:
        """Format an in-text citation.

        Args:
            paper: Paper to cite
            include_year: Whether to include the year

        Returns:
            In-text citation string (e.g., "Smith et al., 2023")
        """
        if not paper.authors:
            first_author = "Unknown"
        else:
            first_author = self._get_last_name(paper.authors[0])

        if len(paper.authors) == 1:
            author_part = first_author
        elif len(paper.authors) == 2:
            second_author = self._get_last_name(paper.authors[1])
            if self.config.use_ampersand:
                author_part = f"{first_author} & {second_author}"
            else:
                author_part = f"{first_author} and {second_author}"
        else:
            author_part = f"{first_author} et al."

        if include_year and paper.year:
            return f"{author_part}, {paper.year}"
        return author_part

    def _format_apa6(self, paper: Paper) -> str:
        """Format citation in APA 6th edition style.

        Format:
        Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article.
        Journal Name, Volume(Issue), Pages. https://doi.org/xxxxx
        """
        parts = []

        # Authors
        authors_str = self._format_authors_apa(paper.authors)
        if authors_str:
            parts.append(authors_str)

        # Year
        year_str = f"({paper.year})." if paper.year else "(n.d.)."
        parts.append(year_str)

        # Title (sentence case)
        if paper.title:
            title = self._to_sentence_case(paper.title)
            parts.append(f"{title}.")

        # Journal (italicized in markdown)
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            # Add volume/issue/pages if available (not in Paper model currently)
            parts.append(f"{journal_part}.")

        # DOI
        if paper.doi:
            parts.append(f"https://doi.org/{paper.doi}")

        return " ".join(parts)

    def _format_apa7(self, paper: Paper) -> str:
        """Format citation in APA 7th edition style.

        Similar to APA 6 but with different et al. rules (21+ authors).
        """
        parts = []

        # Authors (APA 7 allows up to 20 authors before et al.)
        authors_str = self._format_authors_apa(paper.authors, et_al_threshold=21)
        if authors_str:
            parts.append(authors_str)

        # Year
        year_str = f"({paper.year})." if paper.year else "(n.d.)."
        parts.append(year_str)

        # Title (sentence case)
        if paper.title:
            title = self._to_sentence_case(paper.title)
            parts.append(f"{title}.")

        # Journal
        if paper.journal:
            parts.append(f"*{paper.journal}*.")

        # DOI
        if paper.doi:
            parts.append(f"https://doi.org/{paper.doi}")

        return " ".join(parts)

    def _format_vancouver(self, paper: Paper) -> str:
        """Format citation in Vancouver style.

        Format:
        Author AA, Author BB, Author CC. Title. Journal. Year;Volume(Issue):Pages.
        doi:xxxxx
        """
        parts = []

        # Authors (Vancouver uses initials without periods)
        authors_str = self._format_authors_vancouver(paper.authors)
        if authors_str:
            parts.append(f"{authors_str}.")

        # Title
        if paper.title:
            parts.append(f"{paper.title}.")

        # Journal and year
        if paper.journal:
            journal_part = paper.journal
            if paper.year:
                journal_part += f". {paper.year}"
            parts.append(f"{journal_part}.")

        # DOI
        if paper.doi:
            parts.append(f"doi:{paper.doi}")

        return " ".join(parts)

    def _format_chicago(self, paper: Paper) -> str:
        """Format citation in Chicago style.

        Format:
        Last, First, First Last, and First Last. "Title." Journal Volume, no. Issue
        (Year): Pages. https://doi.org/xxxxx.
        """
        parts = []

        # Authors
        authors_str = self._format_authors_chicago(paper.authors)
        if authors_str:
            parts.append(f"{authors_str}.")

        # Title in quotes
        if paper.title:
            parts.append(f'"{paper.title}."')

        # Journal (italicized)
        if paper.journal:
            journal_part = f"*{paper.journal}*"
            if paper.year:
                journal_part += f" ({paper.year})"
            parts.append(f"{journal_part}.")

        # DOI
        if paper.doi:
            parts.append(f"https://doi.org/{paper.doi}.")

        return " ".join(parts)

    def _format_harvard(self, paper: Paper) -> str:
        """Format citation in Harvard style.

        Format:
        Author, A.A., Author, B.B. & Author, C.C. (Year) 'Title', Journal, Volume(Issue),
        pp. Pages. doi:xxxxx.
        """
        parts = []

        # Authors
        authors_str = self._format_authors_harvard(paper.authors)
        if authors_str:
            parts.append(authors_str)

        # Year in parentheses
        year_str = f"({paper.year})" if paper.year else "(n.d.)"
        parts.append(year_str)

        # Title in single quotes
        if paper.title:
            parts.append(f"'{paper.title}',")

        # Journal (italicized)
        if paper.journal:
            parts.append(f"*{paper.journal}*.")

        # DOI
        if paper.doi:
            parts.append(f"doi:{paper.doi}.")

        return " ".join(parts)

    def _format_authors_apa(self, authors: list[Author], et_al_threshold: int = 8) -> str:
        """Format authors list for APA style.

        Rules:
        - 1 author: Last, F. M.
        - 2 authors: Last, F. M., & Last, F. M.
        - 3-7 authors: All listed with & before last
        - 8+ authors: First 6, ..., last author
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return self._format_author_name_apa(authors[0])

        if len(authors) == 2:
            return (
                f"{self._format_author_name_apa(authors[0])}, "
                f"& {self._format_author_name_apa(authors[1])}"
            )

        if len(authors) < et_al_threshold:
            # All authors with & before last
            formatted = [self._format_author_name_apa(a) for a in authors[:-1]]
            last = self._format_author_name_apa(authors[-1])
            return ", ".join(formatted) + f", & {last}"

        # 8+ authors: first 6, ..., last
        formatted = [self._format_author_name_apa(a) for a in authors[:6]]
        last = self._format_author_name_apa(authors[-1])
        return ", ".join(formatted) + f", ... {last}"

    def _format_authors_vancouver(self, authors: list[Author]) -> str:
        """Format authors list for Vancouver style.

        Format: Last AA, Last BB, Last CC
        6+ authors: First 6 et al.
        """
        if not authors:
            return ""

        if len(authors) <= 6:
            formatted = [self._format_author_name_vancouver(a) for a in authors]
            return ", ".join(formatted)

        # 7+ authors: first 6 et al.
        formatted = [self._format_author_name_vancouver(a) for a in authors[:6]]
        return ", ".join(formatted) + ", et al"

    def _format_authors_chicago(self, authors: list[Author]) -> str:
        """Format authors list for Chicago style.

        Format: Last, First, First Last, and First Last
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return self._format_author_name_chicago_first(authors[0])

        if len(authors) == 2:
            return (
                f"{self._format_author_name_chicago_first(authors[0])} "
                f"and {self._format_author_name_chicago_subsequent(authors[1])}"
            )

        if len(authors) <= 3:
            first = self._format_author_name_chicago_first(authors[0])
            middle = [self._format_author_name_chicago_subsequent(a) for a in authors[1:-1]]
            last = self._format_author_name_chicago_subsequent(authors[-1])
            return f"{first}, " + ", ".join(middle) + f", and {last}"

        # 4+ authors: first author et al.
        return f"{self._format_author_name_chicago_first(authors[0])} et al"

    def _format_authors_harvard(self, authors: list[Author]) -> str:
        """Format authors list for Harvard style.

        Format: Last, F.M., Last, F.M. & Last, F.M.
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return self._format_author_name_apa(authors[0])

        if len(authors) == 2:
            return (
                f"{self._format_author_name_apa(authors[0])} "
                f"& {self._format_author_name_apa(authors[1])}"
            )

        if len(authors) <= 3:
            formatted = [self._format_author_name_apa(a) for a in authors[:-1]]
            last = self._format_author_name_apa(authors[-1])
            return ", ".join(formatted) + f" & {last}"

        # 4+ authors: first author et al.
        return f"{self._format_author_name_apa(authors[0])} et al."

    def _format_author_name_apa(self, author: Author) -> str:
        """Format single author name as 'Last, F. M.' for APA."""
        name = author.name.strip()
        if not name:
            return ""

        parts = name.split()
        if len(parts) == 1:
            return parts[0]

        # Assume last word is last name
        last_name = parts[-1]
        initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
        return f"{last_name}, {initials}"

    def _format_author_name_vancouver(self, author: Author) -> str:
        """Format single author name as 'Last AB' for Vancouver."""
        name = author.name.strip()
        if not name:
            return ""

        parts = name.split()
        if len(parts) == 1:
            return parts[0]

        last_name = parts[-1]
        initials = "".join(p[0].upper() for p in parts[:-1])
        return f"{last_name} {initials}"

    def _format_author_name_chicago_first(self, author: Author) -> str:
        """Format first author for Chicago as 'Last, First'."""
        name = author.name.strip()
        if not name:
            return ""

        parts = name.split()
        if len(parts) == 1:
            return parts[0]

        last_name = parts[-1]
        first_names = " ".join(parts[:-1])
        return f"{last_name}, {first_names}"

    def _format_author_name_chicago_subsequent(self, author: Author) -> str:
        """Format subsequent authors for Chicago as 'First Last'."""
        return author.name.strip()

    def _get_last_name(self, author: Author) -> str:
        """Extract last name from author."""
        name = author.name.strip()
        if not name:
            return "Unknown"
        parts = name.split()
        return parts[-1] if parts else "Unknown"

    def _to_sentence_case(self, text: str) -> str:
        """Convert text to sentence case.

        Only first word and words after colons are capitalized.
        Preserves acronyms and proper nouns where detectable.
        """
        if not text:
            return ""

        # Split on sentence-ending punctuation
        result = []
        sentences = re.split(r"([.!?:]\s*)", text)

        for i, part in enumerate(sentences):
            if i % 2 == 0 and part:  # Content parts
                # Lowercase everything except acronyms (all caps words)
                words = part.split()
                new_words = []
                for j, word in enumerate(words):
                    if j == 0:
                        # Capitalize first word
                        new_words.append(
                            word[0].upper() + word[1:].lower() if len(word) > 1 else word.upper()
                        )
                    elif word.isupper() and len(word) > 1:
                        # Preserve acronyms
                        new_words.append(word)
                    else:
                        new_words.append(word.lower())
                result.append(" ".join(new_words))
            else:
                result.append(part)

        return "".join(result)

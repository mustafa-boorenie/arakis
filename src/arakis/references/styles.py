"""Citation style definitions for reference formatting."""

from dataclasses import dataclass
from enum import Enum


class CitationStyle(str, Enum):
    """Supported citation styles."""

    APA_6 = "apa6"
    APA_7 = "apa7"
    VANCOUVER = "vancouver"
    CHICAGO = "chicago"
    HARVARD = "harvard"


@dataclass
class StyleConfig:
    """Configuration for a citation style.

    Attributes:
        name: Human-readable style name
        style: CitationStyle enum value
        et_al_threshold: Number of authors before using "et al."
        et_al_first: How many authors to show before "et al."
        use_ampersand: Use "&" before last author
        year_in_parens: Place year in parentheses
        italicize_journal: Italicize journal name
        include_doi: Include DOI in citation
        doi_format: Format for DOI ("url" for https://doi.org/..., "doi" for doi:...)
        title_case: "sentence" for sentence case, "title" for title case
    """

    name: str
    style: CitationStyle
    et_al_threshold: int
    et_al_first: int
    use_ampersand: bool
    year_in_parens: bool
    italicize_journal: bool
    include_doi: bool
    doi_format: str
    title_case: str


# Pre-defined style configurations
STYLE_CONFIGS = {
    CitationStyle.APA_6: StyleConfig(
        name="APA 6th Edition",
        style=CitationStyle.APA_6,
        et_al_threshold=8,
        et_al_first=6,
        use_ampersand=True,
        year_in_parens=True,
        italicize_journal=True,
        include_doi=True,
        doi_format="url",
        title_case="sentence",
    ),
    CitationStyle.APA_7: StyleConfig(
        name="APA 7th Edition",
        style=CitationStyle.APA_7,
        et_al_threshold=21,
        et_al_first=19,
        use_ampersand=True,
        year_in_parens=True,
        italicize_journal=True,
        include_doi=True,
        doi_format="url",
        title_case="sentence",
    ),
    CitationStyle.VANCOUVER: StyleConfig(
        name="Vancouver",
        style=CitationStyle.VANCOUVER,
        et_al_threshold=7,
        et_al_first=6,
        use_ampersand=False,
        year_in_parens=False,
        italicize_journal=False,
        include_doi=True,
        doi_format="doi",
        title_case="sentence",
    ),
    CitationStyle.CHICAGO: StyleConfig(
        name="Chicago",
        style=CitationStyle.CHICAGO,
        et_al_threshold=4,
        et_al_first=1,
        use_ampersand=False,
        year_in_parens=False,
        italicize_journal=True,
        include_doi=True,
        doi_format="url",
        title_case="title",
    ),
    CitationStyle.HARVARD: StyleConfig(
        name="Harvard",
        style=CitationStyle.HARVARD,
        et_al_threshold=4,
        et_al_first=1,
        use_ampersand=True,
        year_in_parens=True,
        italicize_journal=True,
        include_doi=True,
        doi_format="url",
        title_case="sentence",
    ),
}


def get_style_config(style: CitationStyle) -> StyleConfig:
    """Get the configuration for a citation style.

    Args:
        style: The citation style

    Returns:
        StyleConfig for the requested style
    """
    return STYLE_CONFIGS[style]

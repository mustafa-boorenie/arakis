from __future__ import annotations

"""Multi-strategy deduplication engine for papers."""

from collections import defaultdict
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from arakis.models.audit import AuditEventType
from arakis.models.paper import Paper


@dataclass
class DeduplicationResult:
    """Result of deduplication process."""

    unique_papers: list[Paper]
    duplicates_removed: int
    duplicate_groups: list[list[str]] = field(default_factory=list)  # Groups of duplicate IDs

    @property
    def dedup_rate(self) -> float:
        """Percentage of papers that were duplicates."""
        total = len(self.unique_papers) + self.duplicates_removed
        return self.duplicates_removed / total if total > 0 else 0


class Deduplicator:
    """
    Multi-strategy paper deduplication.

    Strategies (in order of priority):
    1. Exact DOI matching
    2. Exact PMID matching
    3. Title fuzzy matching (>90% similarity)
    4. Author + Year + Title prefix matching
    """

    def __init__(
        self,
        title_similarity_threshold: float = 0.90,
        title_prefix_length: int = 50,
    ):
        self.title_threshold = title_similarity_threshold
        self.title_prefix_length = title_prefix_length

    def deduplicate(self, papers: list[Paper]) -> DeduplicationResult:
        """
        Deduplicate papers using multiple strategies.

        Returns unique papers with merged metadata from duplicates.
        """
        if not papers:
            return DeduplicationResult(unique_papers=[], duplicates_removed=0)

        # Track canonical papers and their duplicates
        canonical: dict[str, Paper] = {}  # Internal ID -> canonical paper
        duplicate_groups: dict[str, list[str]] = defaultdict(list)

        # Index structures for matching
        doi_index: dict[str, str] = {}  # DOI -> canonical ID
        pmid_index: dict[str, str] = {}  # PMID -> canonical ID
        title_index: dict[str, str] = {}  # Normalized title -> canonical ID

        for paper in papers:
            match_id = self._find_match(paper, doi_index, pmid_index, title_index, canonical)

            if match_id:
                # This is a duplicate - merge into canonical
                canonical_paper = canonical[match_id]

                # Record duplicate detection in both papers' audit trails
                paper.ensure_audit_trail().add_event(
                    event_type=AuditEventType.DUPLICATE_DETECTED,
                    description=f"Detected as duplicate of {match_id}",
                    actor="Deduplicator",
                    details={
                        "canonical_id": match_id,
                        "match_strategy": self._get_match_strategy(paper, canonical_paper),
                    },
                    stage="search",
                )
                paper.duplicate_of = match_id

                canonical_paper.ensure_audit_trail().add_event(
                    event_type=AuditEventType.METADATA_MERGED,
                    description=f"Merged metadata from duplicate {paper.id}",
                    actor="Deduplicator",
                    details={"duplicate_id": paper.id, "source": paper.source.value},
                    stage="search",
                )

                self._merge_papers(canonical_paper, paper)
                duplicate_groups[match_id].append(paper.id)
            else:
                # This is a new unique paper
                canonical[paper.id] = paper
                paper.ensure_audit_trail()  # Ensure audit trail exists

                # Index for future matching
                if paper.doi:
                    doi_index[self._normalize_doi(paper.doi)] = paper.id
                if paper.pmid:
                    pmid_index[paper.pmid] = paper.id

                norm_title = self._normalize_title(paper.title)
                if norm_title:
                    title_index[norm_title] = paper.id

        # Build result
        unique_papers = list(canonical.values())
        duplicates_removed = len(papers) - len(unique_papers)

        # Convert duplicate groups to list of lists
        groups = [
            [canonical_id] + dup_ids
            for canonical_id, dup_ids in duplicate_groups.items()
            if dup_ids
        ]

        return DeduplicationResult(
            unique_papers=unique_papers,
            duplicates_removed=duplicates_removed,
            duplicate_groups=groups,
        )

    def _find_match(
        self,
        paper: Paper,
        doi_index: dict[str, str],
        pmid_index: dict[str, str],
        title_index: dict[str, str],
        canonical: dict[str, Paper],
    ) -> str | None:
        """Find a matching canonical paper for the given paper."""
        # Strategy 1: DOI match
        if paper.doi:
            norm_doi = self._normalize_doi(paper.doi)
            if norm_doi in doi_index:
                return doi_index[norm_doi]

        # Strategy 2: PMID match
        if paper.pmid and paper.pmid in pmid_index:
            return pmid_index[paper.pmid]

        # Strategy 3: Title fuzzy match
        norm_title = self._normalize_title(paper.title)
        if norm_title:
            for indexed_title, canonical_id in title_index.items():
                similarity = fuzz.ratio(norm_title, indexed_title) / 100
                if similarity >= self.title_threshold:
                    return canonical_id

        # Strategy 4: Author + Year + Title prefix
        if paper.authors and paper.year:
            first_author = paper.authors[0].name.lower() if paper.authors else ""
            title_prefix = norm_title[: self.title_prefix_length] if norm_title else ""
            key = f"{first_author}_{paper.year}_{title_prefix}"

            for canonical_id, canonical_paper in canonical.items():
                if canonical_paper.authors and canonical_paper.year == paper.year:
                    canon_first = canonical_paper.authors[0].name.lower()
                    canon_prefix = self._normalize_title(canonical_paper.title)[
                        : self.title_prefix_length
                    ]
                    canon_key = f"{canon_first}_{canonical_paper.year}_{canon_prefix}"

                    if key == canon_key:
                        return canonical_id

        return None

    def _get_match_strategy(self, paper: Paper, canonical: Paper) -> str:
        """Determine which strategy matched the papers."""
        # Check DOI match
        if paper.doi and canonical.doi:
            if self._normalize_doi(paper.doi) == self._normalize_doi(canonical.doi):
                return "doi"

        # Check PMID match
        if paper.pmid and canonical.pmid and paper.pmid == canonical.pmid:
            return "pmid"

        # Check title similarity
        norm_paper = self._normalize_title(paper.title)
        norm_canonical = self._normalize_title(canonical.title)
        if norm_paper and norm_canonical:
            similarity = fuzz.ratio(norm_paper, norm_canonical) / 100
            if similarity >= self.title_threshold:
                return "title_fuzzy"

        # Must be author+year+title prefix
        return "author_year_title"

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for matching."""
        doi = doi.lower().strip()
        # Remove common prefixes
        for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
            if doi.startswith(prefix):
                doi = doi[len(prefix) :]
        return doi

    def _normalize_title(self, title: str) -> str:
        """Normalize title for matching."""
        if not title:
            return ""
        # Lowercase, remove punctuation, collapse whitespace
        title = title.lower()
        title = "".join(c if c.isalnum() or c.isspace() else " " for c in title)
        title = " ".join(title.split())
        return title

    def _merge_papers(self, canonical: Paper, duplicate: Paper) -> None:
        """Merge metadata from duplicate into canonical paper."""
        # Fill in missing identifiers
        if not canonical.doi and duplicate.doi:
            canonical.doi = duplicate.doi
        if not canonical.pmid and duplicate.pmid:
            canonical.pmid = duplicate.pmid
        if not canonical.pmcid and duplicate.pmcid:
            canonical.pmcid = duplicate.pmcid
        if not canonical.arxiv_id and duplicate.arxiv_id:
            canonical.arxiv_id = duplicate.arxiv_id
        if not canonical.s2_id and duplicate.s2_id:
            canonical.s2_id = duplicate.s2_id
        if not canonical.openalex_id and duplicate.openalex_id:
            canonical.openalex_id = duplicate.openalex_id

        # Prefer abstract if canonical is missing
        if not canonical.abstract and duplicate.abstract:
            canonical.abstract = duplicate.abstract

        # Merge keywords
        canonical.keywords = list(set(canonical.keywords + duplicate.keywords))
        canonical.mesh_terms = list(set(canonical.mesh_terms + duplicate.mesh_terms))

        # Update open access info
        if duplicate.open_access and not canonical.open_access:
            canonical.open_access = True
        if duplicate.pdf_url and not canonical.pdf_url:
            canonical.pdf_url = duplicate.pdf_url

        # Keep higher citation count
        if duplicate.citation_count:
            if canonical.citation_count is None:
                canonical.citation_count = duplicate.citation_count
            else:
                canonical.citation_count = max(canonical.citation_count, duplicate.citation_count)

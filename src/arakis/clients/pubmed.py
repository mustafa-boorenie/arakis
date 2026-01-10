from __future__ import annotations
"""PubMed search client using NCBI E-utilities."""

import asyncio
import hashlib
import time
from typing import Any
from xml.etree import ElementTree

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from arakis.clients.base import BaseSearchClient, RateLimitError, SearchClientError
from arakis.config import get_settings
from arakis.models.paper import Author, Paper, PaperSource, SearchResult


class PubMedClient(BaseSearchClient):
    """
    PubMed search client using NCBI E-utilities.

    Supports MeSH term queries and field-tagged searches.
    Rate limited to 3 requests/second (10 with API key).
    """

    source = PaperSource.PUBMED

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self):
        self.settings = get_settings()
        self._last_request_time = 0.0
        self._min_interval = 1.0 / self.settings.pubmed_rate_limit

    async def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get_params(self) -> dict[str, str]:
        """Get common API parameters."""
        params = {"db": "pubmed", "retmode": "xml"}
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        return params

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, endpoint: str, params: dict[str, Any]) -> str:
        """Make a request to the E-utilities API."""
        await self._rate_limit()

        url = f"{self.BASE_URL}/{endpoint}"
        all_params = {**self._get_params(), **params}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=all_params)

            if response.status_code == 429:
                raise RateLimitError("PubMed rate limit exceeded")
            response.raise_for_status()

            return response.text

    async def _esearch(self, query: str, max_results: int) -> tuple[list[str], int]:
        """
        Search PubMed and return PMIDs.

        Returns:
            Tuple of (list of PMIDs, total available count)
        """
        params = {
            "term": query,
            "retmax": max_results,
            "usehistory": "n",
        }

        xml_text = await self._request("esearch.fcgi", params)
        root = ElementTree.fromstring(xml_text)

        # Check for errors
        error = root.find(".//ErrorList")
        if error is not None:
            error_msgs = [e.text for e in error if e.text]
            raise SearchClientError(f"PubMed search error: {', '.join(error_msgs)}")

        # Get total count
        count_elem = root.find(".//Count")
        total_count = int(count_elem.text) if count_elem is not None else 0

        # Get PMIDs
        pmids = [id_elem.text for id_elem in root.findall(".//Id") if id_elem.text]

        return pmids, total_count

    async def _efetch(self, pmids: list[str]) -> list[dict[str, Any]]:
        """Fetch detailed records for a list of PMIDs."""
        if not pmids:
            return []

        # Batch PMIDs to avoid URL length limits (414 errors)
        # PubMed can handle ~200 IDs per request safely
        batch_size = 200
        all_articles = []

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            params = {
                "id": ",".join(batch),
                "rettype": "abstract",
            }

            xml_text = await self._request("efetch.fcgi", params)
            articles = self._parse_pubmed_xml(xml_text)
            all_articles.extend(articles)

        return all_articles

    def _parse_pubmed_xml(self, xml_text: str) -> list[dict[str, Any]]:
        """Parse PubMed XML response into structured data."""
        root = ElementTree.fromstring(xml_text)
        articles = []

        for article in root.findall(".//PubmedArticle"):
            try:
                data = self._parse_article(article)
                articles.append(data)
            except Exception:
                continue  # Skip malformed articles

        return articles

    def _parse_article(self, article: ElementTree.Element) -> dict[str, Any]:
        """Parse a single PubmedArticle element."""
        medline = article.find(".//MedlineCitation")
        article_data = medline.find(".//Article") if medline is not None else None

        if article_data is None:
            return {}

        # PMID
        pmid_elem = medline.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else None

        # Title
        title_elem = article_data.find(".//ArticleTitle")
        title = self._get_text(title_elem)

        # Abstract
        abstract_parts = []
        for abs_text in article_data.findall(".//AbstractText"):
            label = abs_text.get("Label", "")
            text = self._get_text(abs_text)
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts) if abstract_parts else None

        # Authors
        authors = []
        for author in article_data.findall(".//Author"):
            last_name = author.findtext("LastName", "")
            first_name = author.findtext("ForeName", "")
            if last_name:
                name = f"{last_name}, {first_name}".strip(", ")
                affil = author.findtext(".//Affiliation", None)
                authors.append({"name": name, "affiliation": affil})

        # Journal
        journal_elem = article_data.find(".//Journal")
        journal = journal_elem.findtext("Title", None) if journal_elem is not None else None

        # Publication date
        pub_date = article_data.find(".//PubDate")
        year = None
        if pub_date is not None:
            year_text = pub_date.findtext("Year")
            if year_text and year_text.isdigit():
                year = int(year_text)

        # DOI
        doi = None
        for id_elem in article.findall(".//ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text
                break

        # MeSH terms
        mesh_terms = []
        for mesh in medline.findall(".//MeshHeading/DescriptorName"):
            if mesh.text:
                mesh_terms.append(mesh.text)

        # Publication types
        pub_types = []
        for pt in article_data.findall(".//PublicationType"):
            if pt.text:
                pub_types.append(pt.text)

        # PMC ID
        pmcid = None
        for id_elem in article.findall(".//ArticleId"):
            if id_elem.get("IdType") == "pmc":
                pmcid = id_elem.text
                break

        return {
            "pmid": pmid,
            "doi": doi,
            "pmcid": pmcid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "year": year,
            "mesh_terms": mesh_terms,
            "publication_types": pub_types,
        }

    def _get_text(self, elem: ElementTree.Element | None) -> str:
        """Extract text content from an element, including nested elements."""
        if elem is None:
            return ""
        return "".join(elem.itertext()).strip()

    def normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Convert raw PubMed data to normalized Paper."""
        pmid = raw_data.get("pmid", "")
        paper_id = f"pubmed_{pmid}" if pmid else hashlib.md5(
            str(raw_data).encode()
        ).hexdigest()[:12]

        authors = [
            Author(name=a.get("name", ""), affiliation=a.get("affiliation"))
            for a in raw_data.get("authors", [])
        ]

        return Paper(
            id=paper_id,
            pmid=pmid,
            pmcid=raw_data.get("pmcid"),
            doi=raw_data.get("doi"),
            title=raw_data.get("title", ""),
            abstract=raw_data.get("abstract"),
            authors=authors,
            journal=raw_data.get("journal"),
            year=raw_data.get("year"),
            source=PaperSource.PUBMED,
            source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            mesh_terms=raw_data.get("mesh_terms", []),
            publication_types=raw_data.get("publication_types", []),
            open_access=bool(raw_data.get("pmcid")),
            raw_data=raw_data,
        )

    async def search(self, query: str, max_results: int = 100) -> SearchResult:
        """Execute a PubMed search."""
        start_time = time.time()

        # Search for PMIDs
        pmids, total_count = await self._esearch(query, max_results)

        # Fetch detailed records
        raw_articles = await self._efetch(pmids)

        # Convert to normalized papers
        papers = [self.normalize_paper(article) for article in raw_articles]

        execution_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            query=query,
            source=PaperSource.PUBMED,
            papers=papers,
            total_available=total_count,
            execution_time_ms=execution_time,
        )

    async def get_paper_by_id(self, paper_id: str) -> Paper | None:
        """Get a paper by PMID."""
        pmid = paper_id.replace("pubmed_", "")
        articles = await self._efetch([pmid])
        if articles:
            return self.normalize_paper(articles[0])
        return None

    def get_query_syntax_help(self) -> str:
        """Return PubMed query syntax help."""
        return """
PubMed uses a Boolean search syntax with field tags:

FIELD TAGS:
- [MeSH Terms] or [mh] - Medical Subject Headings
- [Title/Abstract] or [tiab] - Search title and abstract
- [Title] or [ti] - Title only
- [Author] or [au] - Author name
- [Publication Type] or [pt] - e.g., "Randomized Controlled Trial"
- [Date - Publication] or [dp] - Publication date

OPERATORS:
- AND, OR, NOT (must be uppercase)
- Parentheses for grouping

EXAMPLES:
1. "aspirin"[MeSH Terms] AND "sepsis"[MeSH Terms]
2. (aspirin OR acetylsalicylic acid) AND mortality[tiab]
3. "Randomized Controlled Trial"[pt] AND diabetes[mh]
4. cancer[tiab] AND 2020:2024[dp]

TIPS:
- Use MeSH terms for comprehensive concept searches
- Explode MeSH terms automatically included (use [mh:noexp] to disable)
- Use * for truncation: therap* matches therapy, therapeutic, etc.
"""


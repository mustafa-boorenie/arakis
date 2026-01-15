"""Semantic Scholar retrieval source for open access PDFs."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class SemanticScholarSource(BaseRetrievalSource):
    """
    Semantic Scholar API for finding open access PDFs.

    Free API with rate limits. Uses s2_id or DOI to lookup papers.
    API key optional but recommended for higher rate limits.
    """

    name = "semantic_scholar"
    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.semantic_scholar_api_key

    async def can_retrieve(self, paper: Paper) -> bool:
        """Can retrieve if we have s2_id or DOI."""
        return bool(paper.s2_id or paper.doi)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query Semantic Scholar for open access PDF."""
        # Build paper identifier
        if paper.s2_id:
            paper_ref = paper.s2_id
        elif paper.doi:
            paper_ref = f"DOI:{paper.doi}"
        else:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No S2 ID or DOI available",
            )

        url = f"{self.BASE_URL}/{paper_ref}"
        params = {"fields": "openAccessPdf"}
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 404:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="Paper not found in Semantic Scholar",
                    )

                if response.status_code == 429:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="Rate limited by Semantic Scholar",
                    )

                response.raise_for_status()
                data = response.json()

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}",
            )

        # Check for open access PDF
        oa_pdf = data.get("openAccessPdf", {}) or {}
        pdf_url = oa_pdf.get("url")

        if not pdf_url:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No open access PDF available",
            )

        result = RetrievalResult(
            success=True,
            paper_id=paper.id,
            source_name=self.name,
            content_url=pdf_url,
            content_type=ContentType.PDF,
        )

        if download:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    pdf_response = await client.get(pdf_url, follow_redirects=True)
                    if pdf_response.status_code == 200:
                        result.content = pdf_response.content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

"""PubMed Central retrieval source for free full-text papers."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


class PMCSource(BaseRetrievalSource):
    """
    PubMed Central source for free full-text biomedical papers.

    Retrieves papers via PMCID.
    """

    name = "pmc"
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles"

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _head_request(self, url: str) -> int:
        """Make a HEAD request with retry logic, returns status code."""
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.head(url)
            return response.status_code

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _download_content(self, url: str) -> bytes | None:
        """Download content with retry logic."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.content
        return None

    async def can_retrieve(self, paper: Paper) -> bool:
        """PMC requires a PMCID."""
        return bool(paper.pmcid)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Retrieve paper from PubMed Central."""
        if not paper.pmcid:
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error="No PMCID available"
            )

        pmcid = paper.pmcid
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"

        # PMC article URL
        article_url = f"{self.BASE_URL}/{pmcid}/"
        pdf_url = f"{self.BASE_URL}/{pmcid}/pdf/"

        # Check if PDF exists
        try:
            # Try PDF first
            pdf_status = await self._head_request(pdf_url)

            if pdf_status == 200:
                result = RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=pdf_url,
                    content_type=ContentType.PDF,
                    version="published",
                )

                if download:
                    content = await self._download_content(pdf_url)
                    if content:
                        result.content = content

                return result

            # Fall back to HTML
            html_status = await self._head_request(article_url)

            if html_status == 200:
                return RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=article_url,
                    content_type=ContentType.HTML,
                    version="published",
                )

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error=f"HTTP error: {e}"
            )

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not accessible in PMC",
        )

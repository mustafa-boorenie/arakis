"""arXiv retrieval source for preprints."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


class ArxivSource(BaseRetrievalSource):
    """
    arXiv source for preprint papers.

    All arXiv papers are freely available.
    """

    name = "arxiv"
    BASE_URL = "https://arxiv.org"

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
        """arXiv requires an arXiv ID."""
        return bool(paper.arxiv_id)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Retrieve paper from arXiv."""
        if not paper.arxiv_id:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No arXiv ID available",
            )

        arxiv_id = paper.arxiv_id
        # Clean up ID format
        if arxiv_id.lower().startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]

        pdf_url = f"{self.BASE_URL}/pdf/{arxiv_id}.pdf"

        try:
            # Check PDF availability
            status_code = await self._head_request(pdf_url)

            if status_code == 200:
                result = RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=pdf_url,
                    content_type=ContentType.PDF,
                    license="arXiv",
                    version="preprint",
                )

                if download:
                    content = await self._download_content(pdf_url)
                    if content:
                        result.content = content

                return result

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error=f"HTTP error: {e}"
            )

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not found on arXiv",
        )

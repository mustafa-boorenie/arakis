"""bioRxiv/medRxiv retrieval source for preprints."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


class BiorxivSource(BaseRetrievalSource):
    """
    bioRxiv/medRxiv source for biology and medical preprints.

    Free access, all papers are openly available.
    Uses DOI to identify papers (bioRxiv DOIs start with 10.1101/).
    """

    name = "biorxiv"
    BIORXIV_DOI_PREFIX = "10.1101/"

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
        """Can retrieve if DOI is a bioRxiv/medRxiv DOI."""
        if not paper.doi:
            return False
        return paper.doi.startswith(self.BIORXIV_DOI_PREFIX)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Retrieve paper from bioRxiv/medRxiv."""
        if not paper.doi or not paper.doi.startswith(self.BIORXIV_DOI_PREFIX):
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Not a bioRxiv/medRxiv DOI",
            )

        # Try bioRxiv first
        pdf_url = f"https://www.biorxiv.org/content/{paper.doi}.full.pdf"

        try:
            status_code = await self._head_request(pdf_url)

            if status_code == 200:
                result = RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=pdf_url,
                    content_type=ContentType.PDF,
                    version="preprint",
                )

                if download:
                    content = await self._download_content(pdf_url)
                    if content:
                        result.content = content

                return result

        except httpx.HTTPError:
            # Try medRxiv as fallback
            pass

        # Try medRxiv if bioRxiv fails
        medrxiv_url = f"https://www.medrxiv.org/content/{paper.doi}.full.pdf"
        try:
            status_code = await self._head_request(medrxiv_url)

            if status_code == 200:
                result = RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=medrxiv_url,
                    content_type=ContentType.PDF,
                    version="preprint",
                )

                if download:
                    content = await self._download_content(medrxiv_url)
                    if content:
                        result.content = content

                return result

        except httpx.HTTPError:
            pass

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not found on bioRxiv/medRxiv",
        )

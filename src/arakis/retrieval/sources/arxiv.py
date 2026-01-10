"""arXiv retrieval source for preprints."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class ArxivSource(BaseRetrievalSource):
    """
    arXiv source for preprint papers.

    All arXiv papers are freely available.
    """

    name = "arxiv"
    BASE_URL = "https://arxiv.org"

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
                error="No arXiv ID available"
            )

        arxiv_id = paper.arxiv_id
        # Clean up ID format
        if arxiv_id.lower().startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]

        pdf_url = f"{self.BASE_URL}/pdf/{arxiv_id}.pdf"
        abs_url = f"{self.BASE_URL}/abs/{arxiv_id}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Check PDF availability
                response = await client.head(pdf_url)

                if response.status_code == 200:
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
                        pdf_response = await client.get(pdf_url)
                        if pdf_response.status_code == 200:
                            result.content = pdf_response.content

                    return result

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}"
            )

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not found on arXiv"
        )

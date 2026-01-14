"""PubMed Central retrieval source for free full-text papers."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class PMCSource(BaseRetrievalSource):
    """
    PubMed Central source for free full-text biomedical papers.

    Retrieves papers via PMCID.
    """

    name = "pmc"
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/articles"

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
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Try PDF first
                pdf_response = await client.head(pdf_url)

                if pdf_response.status_code == 200:
                    result = RetrievalResult(
                        success=True,
                        paper_id=paper.id,
                        source_name=self.name,
                        content_url=pdf_url,
                        content_type=ContentType.PDF,
                        version="published",
                    )

                    if download:
                        pdf_get = await client.get(pdf_url)
                        if pdf_get.status_code == 200:
                            result.content = pdf_get.content

                    return result

                # Fall back to HTML
                html_response = await client.head(article_url)

                if html_response.status_code == 200:
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

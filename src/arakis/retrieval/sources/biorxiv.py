"""bioRxiv/medRxiv retrieval source for preprints."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class BiorxivSource(BaseRetrievalSource):
    """
    bioRxiv/medRxiv source for biology and medical preprints.

    Free access, all papers are openly available.
    Uses DOI to identify papers (bioRxiv DOIs start with 10.1101/).
    """

    name = "biorxiv"
    BIORXIV_DOI_PREFIX = "10.1101/"

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
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.head(pdf_url)

                if response.status_code == 200:
                    result = RetrievalResult(
                        success=True,
                        paper_id=paper.id,
                        source_name=self.name,
                        content_url=pdf_url,
                        content_type=ContentType.PDF,
                        version="preprint",
                    )

                    if download:
                        pdf_response = await client.get(pdf_url)
                        if pdf_response.status_code == 200:
                            result.content = pdf_response.content

                    return result

        except httpx.HTTPError:
            # Try medRxiv as fallback
            pass

        # Try medRxiv if bioRxiv fails
        medrxiv_url = f"https://www.medrxiv.org/content/{paper.doi}.full.pdf"
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.head(medrxiv_url)

                if response.status_code == 200:
                    result = RetrievalResult(
                        success=True,
                        paper_id=paper.id,
                        source_name=self.name,
                        content_url=medrxiv_url,
                        content_type=ContentType.PDF,
                        version="preprint",
                    )

                    if download:
                        pdf_response = await client.get(medrxiv_url)
                        if pdf_response.status_code == 200:
                            result.content = pdf_response.content

                    return result

        except httpx.HTTPError:
            pass

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not found on bioRxiv/medRxiv",
        )

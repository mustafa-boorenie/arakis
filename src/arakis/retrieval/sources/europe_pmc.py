"""Europe PMC retrieval source - broader than US PubMed Central."""

import httpx

from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class EuropePMCSource(BaseRetrievalSource):
    """
    Europe PMC source for full-text biomedical papers.

    Europe PMC aggregates content from PubMed Central plus
    additional European repositories. No API key required.
    """

    name = "europe_pmc"
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    async def can_retrieve(self, paper: Paper) -> bool:
        """Can retrieve if we have PMID, PMCID, or DOI."""
        return bool(paper.pmid or paper.pmcid or paper.doi)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query Europe PMC for full text."""
        # Build query based on available identifiers
        if paper.pmcid:
            pmcid = paper.pmcid
            if not pmcid.startswith("PMC"):
                pmcid = f"PMC{pmcid}"
            query = f"PMCID:{pmcid}"
        elif paper.pmid:
            query = f"EXT_ID:{paper.pmid} SRC:MED"
        elif paper.doi:
            query = f'DOI:"{paper.doi}"'
        else:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No PMID, PMCID, or DOI available",
            )

        search_url = f"{self.BASE_URL}/search"
        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}",
            )

        # Parse results
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Paper not found in Europe PMC",
            )

        article = results[0]

        # Check for full text availability
        is_open_access = article.get("isOpenAccess") == "Y"
        pmcid = article.get("pmcid")

        if not is_open_access and not pmcid:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Paper is not open access",
            )

        # Europe PMC full text URL
        if pmcid:
            pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf"
        else:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No PMCID for PDF retrieval",
            )

        result = RetrievalResult(
            success=True,
            paper_id=paper.id,
            source_name=self.name,
            content_url=pdf_url,
            content_type=ContentType.PDF,
            version="published",
        )

        if download:
            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    pdf_response = await client.get(pdf_url)
                    if pdf_response.status_code == 200:
                        result.content = pdf_response.content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

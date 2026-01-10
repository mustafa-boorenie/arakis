"""Unpaywall retrieval source for open access papers."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class UnpaywallSource(BaseRetrievalSource):
    """
    Unpaywall API for finding open access versions of papers.

    Requires an email address for API access.
    """

    name = "unpaywall"
    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self):
        self.settings = get_settings()
        self.email = self.settings.unpaywall_email

    async def can_retrieve(self, paper: Paper) -> bool:
        """Unpaywall requires a DOI."""
        return bool(paper.doi and self.email)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query Unpaywall for an open access version."""
        if not paper.doi:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No DOI available"
            )

        if not self.email:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Unpaywall email not configured"
            )

        # Query Unpaywall
        url = f"{self.BASE_URL}/{paper.doi}"
        params = {"email": self.email}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)

                if response.status_code == 404:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="DOI not found in Unpaywall"
                    )

                response.raise_for_status()
                data = response.json()

        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}"
            )

        # Check if open access
        if not data.get("is_oa"):
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Paper is not open access"
            )

        # Find best OA location
        best_location = data.get("best_oa_location") or {}
        pdf_url = best_location.get("url_for_pdf")
        landing_url = best_location.get("url_for_landing_page")
        license_info = best_location.get("license")
        version = best_location.get("version")

        if not pdf_url and not landing_url:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No accessible URL found"
            )

        content_url = pdf_url or landing_url
        content_type = ContentType.PDF if pdf_url else ContentType.HTML

        result = RetrievalResult(
            success=True,
            paper_id=paper.id,
            source_name=self.name,
            content_url=content_url,
            content_type=content_type,
            license=license_info,
            version=version,
        )

        # Optionally download
        if download and pdf_url:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    pdf_response = await client.get(pdf_url, follow_redirects=True)
                    if pdf_response.status_code == 200:
                        result.content = pdf_response.content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

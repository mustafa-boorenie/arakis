"""Unpaywall retrieval source for open access papers."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


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

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _fetch_unpaywall_data(self, url: str, params: dict) -> dict:
        """Fetch data from Unpaywall API with retry logic."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _download_pdf(self, pdf_url: str) -> bytes | None:
        """Download PDF content with retry logic."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_url, follow_redirects=True)
            if response.status_code == 200:
                return response.content
        return None

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query Unpaywall for an open access version."""
        if not paper.doi:
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error="No DOI available"
            )

        if not self.email:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Unpaywall email not configured",
            )

        # Query Unpaywall
        url = f"{self.BASE_URL}/{paper.doi}"
        params = {"email": self.email}

        try:
            data = await self._fetch_unpaywall_data(url, params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return RetrievalResult(
                    success=False,
                    paper_id=paper.id,
                    source_name=self.name,
                    error="DOI not found in Unpaywall",
                )
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error=f"HTTP error: {e}"
            )
        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False, paper_id=paper.id, source_name=self.name, error=f"HTTP error: {e}"
            )

        # Check if open access
        if not data.get("is_oa"):
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Paper is not open access",
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
                error="No accessible URL found",
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
                content = await self._download_pdf(pdf_url)
                if content:
                    result.content = content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

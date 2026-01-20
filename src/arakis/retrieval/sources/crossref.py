"""Crossref retrieval source - follows publisher links for open access."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


class CrossrefSource(BaseRetrievalSource):
    """
    Crossref source - follows links to publisher-hosted open access PDFs.

    Crossref metadata includes license information and links.
    No API key required (polite pool with email).
    """

    name = "crossref"
    BASE_URL = "https://api.crossref.org/works"

    def __init__(self):
        self.settings = get_settings()
        # Use unpaywall email or a default for polite pool
        self.email = self.settings.unpaywall_email or self.settings.openalex_email or ""

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _fetch_crossref_data(self, url: str, headers: dict) -> dict:
        """Fetch data from Crossref API with retry logic."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _head_request(self, url: str) -> int:
        """Make a HEAD request with retry logic, returns status code."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(url)
            return response.status_code

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _download_pdf(self, pdf_url: str) -> bytes | None:
        """Download PDF content with retry logic."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            if response.status_code == 200:
                return response.content
        return None

    async def can_retrieve(self, paper: Paper) -> bool:
        """Requires DOI."""
        return bool(paper.doi)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query Crossref for open access links."""
        if not paper.doi:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No DOI available",
            )

        url = f"{self.BASE_URL}/{paper.doi}"
        headers = {}
        if self.email:
            headers["User-Agent"] = f"Arakis/1.0 (mailto:{self.email})"

        try:
            data = await self._fetch_crossref_data(url, headers)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return RetrievalResult(
                    success=False,
                    paper_id=paper.id,
                    source_name=self.name,
                    error="DOI not found in Crossref",
                )
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}",
            )
        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}",
            )

        message = data.get("message", {})

        # Get license info for result metadata
        licenses = message.get("license", [])

        # Get links
        links = message.get("link", [])

        # Find PDF link (prefer application/pdf)
        pdf_url = None
        for link in links:
            content_type = link.get("content-type", "")
            if "pdf" in content_type.lower():
                pdf_url = link.get("URL")
                break

        if not pdf_url:
            # Try resource link as fallback
            resource = message.get("resource", {}).get("primary", {})
            pdf_url = resource.get("URL")

        if not pdf_url:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No PDF link available",
            )

        # Verify the URL is accessible
        try:
            status_code = await self._head_request(pdf_url)
            if status_code not in (200, 301, 302, 303, 307, 308):
                return RetrievalResult(
                    success=False,
                    paper_id=paper.id,
                    source_name=self.name,
                    error="PDF URL not accessible",
                )
        except httpx.HTTPError:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Could not verify PDF URL",
            )

        license_url = licenses[0].get("URL") if licenses else None

        result = RetrievalResult(
            success=True,
            paper_id=paper.id,
            source_name=self.name,
            content_url=pdf_url,
            content_type=ContentType.PDF,
            license=license_url,
        )

        if download:
            try:
                content = await self._download_pdf(pdf_url)
                if content:
                    result.content = content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

"""Crossref retrieval source - follows publisher links for open access."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


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
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="DOI not found in Crossref",
                    )

                response.raise_for_status()
                data = response.json()

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
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                head_response = await client.head(pdf_url)
                if head_response.status_code not in (200, 301, 302, 303, 307, 308):
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
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    pdf_response = await client.get(pdf_url)
                    if pdf_response.status_code == 200:
                        result.content = pdf_response.content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

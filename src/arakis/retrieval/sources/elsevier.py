"""Elsevier ScienceDirect retrieval source for institutional access."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult


class ElsevierSource(BaseRetrievalSource):
    """
    Elsevier ScienceDirect API for full-text article retrieval.

    Requires an institutional API key with text mining entitlements.
    Covers ~18% of all academic papers (Elsevier journals like Lancet,
    Cell, etc.).

    API Documentation: https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
    Get API key: https://dev.elsevier.com/apikey/manage
    """

    name = "elsevier"
    BASE_URL = "https://api.elsevier.com/content/article"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.elsevier_api_key

    async def can_retrieve(self, paper: Paper) -> bool:
        """Can retrieve if we have API key and DOI."""
        return bool(self.api_key and paper.doi)

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Retrieve full-text article from ScienceDirect."""
        if not self.api_key:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Elsevier API key not configured",
            )

        if not paper.doi:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No DOI available",
            )

        # Check if this is an Elsevier DOI (optional optimization)
        # Elsevier DOIs typically start with 10.1016/
        # But we'll try anyway since the API will tell us if not found

        url = f"{self.BASE_URL}/doi/{paper.doi}"
        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/pdf",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, check if we have access (HEAD request)
                head_response = await client.head(url, headers=headers)

                if head_response.status_code == 404:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="Article not found in ScienceDirect",
                    )

                if head_response.status_code == 401:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="Invalid or unauthorized API key",
                    )

                if head_response.status_code == 403:
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error="No entitlement to access this article",
                    )

                if head_response.status_code not in (200, 202):
                    return RetrievalResult(
                        success=False,
                        paper_id=paper.id,
                        source_name=self.name,
                        error=f"Unexpected status: {head_response.status_code}",
                    )

                # Build the PDF URL
                pdf_url = url

                result = RetrievalResult(
                    success=True,
                    paper_id=paper.id,
                    source_name=self.name,
                    content_url=pdf_url,
                    content_type=ContentType.PDF,
                    version="published",
                )

                # Download PDF if requested
                if download:
                    get_response = await client.get(url, headers=headers, follow_redirects=True)
                    if get_response.status_code == 200:
                        content = get_response.content
                        # Verify it's a PDF
                        if content[:4] == b"%PDF":
                            result.content = content
                        else:
                            # Might be XML error response
                            result.error = "Response was not a PDF"
                            result.success = False
                            return result

                return result

        except httpx.TimeoutException:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="Request timed out",
            )
        except httpx.HTTPError as e:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error=f"HTTP error: {e}",
            )

    def _is_elsevier_doi(self, doi: str) -> bool:
        """Check if DOI belongs to Elsevier (optimization hint)."""
        # Common Elsevier DOI prefixes
        elsevier_prefixes = [
            "10.1016/",  # Main Elsevier prefix (ScienceDirect)
            "10.1006/",  # Academic Press (Elsevier)
            "10.1053/",  # Elsevier
            "10.1054/",  # Elsevier
            "10.1067/",  # Elsevier
            "10.1078/",  # Urban & Fischer (Elsevier)
            "10.1205/",  # Institution of Chemical Engineers (Elsevier)
            "10.1529/",  # Biophysical Society (Elsevier)
            "10.1615/",  # Begell House (some via Elsevier)
            "10.3182/",  # IFAC (Elsevier)
        ]
        return any(doi.startswith(prefix) for prefix in elsevier_prefixes)

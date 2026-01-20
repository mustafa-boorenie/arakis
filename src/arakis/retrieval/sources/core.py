"""CORE API retrieval source - aggregates 250M+ open access outputs."""

import httpx

from arakis.config import get_settings
from arakis.models.paper import Paper
from arakis.retrieval.sources.base import BaseRetrievalSource, ContentType, RetrievalResult
from arakis.utils import retry_http_request


class CORESource(BaseRetrievalSource):
    """
    CORE API for aggregated open access content.

    CORE aggregates content from 250M+ research outputs from
    repositories and journals worldwide.

    Free tier: 10,000 requests/month
    API key required: https://core.ac.uk/services/api
    """

    name = "core"
    BASE_URL = "https://api.core.ac.uk/v3"

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.core_api_key

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _fetch_core_data(self, url: str, headers: dict, params: dict | None = None) -> dict:
        """Fetch data from CORE API with retry logic."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    @retry_http_request(max_retries=3, initial_delay=1.0, max_delay=30.0)
    async def _download_pdf(self, download_url: str) -> bytes | None:
        """Download PDF content with retry logic."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(download_url, follow_redirects=True)
            if response.status_code == 200:
                return response.content
        return None

    async def can_retrieve(self, paper: Paper) -> bool:
        """Can retrieve if we have API key and DOI or title."""
        return bool(self.api_key and (paper.doi or paper.title))

    async def retrieve(self, paper: Paper, download: bool = False) -> RetrievalResult:
        """Query CORE for open access version."""
        if not self.api_key:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="CORE API key not configured",
            )

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Try DOI lookup first (more reliable)
        if paper.doi:
            url = f"{self.BASE_URL}/outputs/doi/{paper.doi}"
            try:
                data = await self._fetch_core_data(url, headers)
                return await self._process_core_result(paper, data, download)
            except httpx.HTTPError:
                pass

        # Fall back to title search
        if paper.title:
            search_url = f"{self.BASE_URL}/search/outputs"
            params = {"q": f'title:"{paper.title}"', "limit": 1}

            try:
                data = await self._fetch_core_data(search_url, headers, params)
                results = data.get("results", [])
                if results:
                    return await self._process_core_result(paper, results[0], download)

            except httpx.HTTPError as e:
                return RetrievalResult(
                    success=False,
                    paper_id=paper.id,
                    source_name=self.name,
                    error=f"HTTP error: {e}",
                )

        return RetrievalResult(
            success=False,
            paper_id=paper.id,
            source_name=self.name,
            error="Paper not found in CORE",
        )

    async def _process_core_result(
        self, paper: Paper, data: dict, download: bool
    ) -> RetrievalResult:
        """Process CORE API result and extract PDF URL."""
        # CORE provides downloadUrl for full text
        download_url = data.get("downloadUrl")

        if not download_url:
            # Try links array
            links = data.get("links", [])
            for link in links:
                if link.get("type") == "download":
                    download_url = link.get("url")
                    break

        if not download_url:
            # Try sourceFulltextUrls
            fulltext_urls = data.get("sourceFulltextUrls", [])
            if fulltext_urls:
                download_url = fulltext_urls[0]

        if not download_url:
            return RetrievalResult(
                success=False,
                paper_id=paper.id,
                source_name=self.name,
                error="No download URL available",
            )

        result = RetrievalResult(
            success=True,
            paper_id=paper.id,
            source_name=self.name,
            content_url=download_url,
            content_type=ContentType.PDF,
            license=data.get("license"),
        )

        if download:
            try:
                content = await self._download_pdf(download_url)
                if content:
                    result.content = content
            except httpx.HTTPError:
                pass  # Download failed but URL is still valid

        return result

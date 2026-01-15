"""Settings and configuration endpoints."""

from fastapi import APIRouter

from arakis.config import get_settings
from arakis.retrieval.fetcher import PaperFetcher

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/")
async def get_settings_status():
    """
    Get status of all configured API keys and services.

    Returns which services are configured (without exposing actual keys).
    """
    settings = get_settings()

    # Get configured retrieval sources
    fetcher = PaperFetcher()
    retrieval_sources = [source.name for source in fetcher.sources]

    return {
        "retrieval": {
            "sources": retrieval_sources,
            "total_sources": len(retrieval_sources),
        },
        "api_keys": {
            "openai": {
                "configured": bool(settings.openai_api_key),
                "description": "Required for AI-powered query generation and screening",
            },
            "unpaywall": {
                "configured": bool(settings.unpaywall_email),
                "description": "Email for Unpaywall API (open access lookup)",
            },
            "elsevier": {
                "configured": bool(settings.elsevier_api_key),
                "description": "Institutional access to ScienceDirect (~18% of papers)",
            },
            "semantic_scholar": {
                "configured": bool(settings.semantic_scholar_api_key),
                "description": "Higher rate limits for Semantic Scholar",
            },
            "core": {
                "configured": bool(settings.core_api_key),
                "description": "CORE API for 250M+ open access outputs",
            },
            "ncbi": {
                "configured": bool(settings.ncbi_api_key),
                "description": "Higher rate limits for PubMed",
            },
            "openalex": {
                "configured": bool(settings.openalex_email),
                "description": "Polite pool access for OpenAlex",
            },
            "serpapi": {
                "configured": bool(settings.serpapi_key),
                "description": "Google Scholar access via SerpAPI",
            },
        },
        "storage": {
            "s3_configured": bool(
                settings.s3_endpoint and settings.s3_access_key and settings.s3_secret_key
            ),
            "bucket_name": settings.s3_bucket_name if settings.s3_endpoint else None,
        },
    }


@router.get("/retrieval-sources")
async def get_retrieval_sources():
    """
    Get detailed information about available retrieval sources.

    Shows which sources are active and their capabilities.
    """
    settings = get_settings()
    fetcher = PaperFetcher()

    sources_info = []
    for source in fetcher.sources:
        info = {
            "name": source.name,
            "active": True,
            "requires_api_key": False,
            "api_key_configured": True,
        }

        # Check if source requires API key
        if source.name == "elsevier":
            info["requires_api_key"] = True
            info["api_key_configured"] = bool(settings.elsevier_api_key)
            info["description"] = "Elsevier ScienceDirect (Lancet, Cell, etc.)"
            info["coverage"] = "~18% of papers"
        elif source.name == "semantic_scholar":
            info["requires_api_key"] = False  # Optional but recommended
            info["api_key_configured"] = bool(settings.semantic_scholar_api_key)
            info["description"] = "Semantic Scholar PDFs"
            info["coverage"] = "~200M papers"
        elif source.name == "core":
            info["requires_api_key"] = True
            info["api_key_configured"] = bool(settings.core_api_key)
            info["description"] = "CORE aggregator"
            info["coverage"] = "~250M outputs"
        elif source.name == "unpaywall":
            info["requires_api_key"] = True
            info["api_key_configured"] = bool(settings.unpaywall_email)
            info["description"] = "Unpaywall OA finder"
            info["coverage"] = "All OA papers with DOI"
        elif source.name == "biorxiv":
            info["description"] = "bioRxiv/medRxiv preprints"
            info["coverage"] = "~500k preprints"
        elif source.name == "arxiv":
            info["description"] = "arXiv preprints"
            info["coverage"] = "~2M preprints"
        elif source.name == "pmc":
            info["description"] = "PubMed Central"
            info["coverage"] = "~8M free articles"
        elif source.name == "europe_pmc":
            info["description"] = "Europe PMC"
            info["coverage"] = "~40M articles"
        elif source.name == "crossref":
            info["description"] = "Crossref publisher links"
            info["coverage"] = "~130M DOIs"

        # Mark inactive if API key required but not configured
        if info["requires_api_key"] and not info["api_key_configured"]:
            info["active"] = False

        sources_info.append(info)

    active_count = sum(1 for s in sources_info if s["active"])

    return {
        "sources": sources_info,
        "total": len(sources_info),
        "active": active_count,
        "inactive": len(sources_info) - active_count,
    }

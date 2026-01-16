"""Configuration management for Arakis."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"  # Default model for query generation
    openai_research_model: str = "gpt-4o"  # For deep research tasks
    openai_requests_per_minute: int = 3  # Rate limit (3 for free tier, 500+ for paid)

    # Paper retrieval
    unpaywall_email: str = ""

    # PubMed (optional - higher rate limits)
    ncbi_api_key: str = ""

    # Elsevier/Embase (optional - requires institutional subscription)
    elsevier_api_key: str = ""

    # Semantic Scholar (optional - higher rate limits: 100 req/sec vs 1 req/sec)
    # Get key at: https://www.semanticscholar.org/product/api#api-key
    semantic_scholar_api_key: str = ""

    # CORE API (optional - aggregates 250M+ open access outputs)
    # Free tier: 10k requests/month. Get key at: https://core.ac.uk/services/api
    core_api_key: str = ""

    # OpenAlex polite pool email (optional - faster responses)
    # Just use any email to get into the "polite pool" with better rate limits
    openalex_email: str = ""

    # SerpAPI (optional - alternative to scholarly for Google Scholar)
    serpapi_key: str = ""

    # Perplexity API (for introduction literature research)
    # Used to fetch background literature for introductions (separate from review search)
    # Get key at: https://www.perplexity.ai/settings/api
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar"  # "sonar" or "sonar-pro"

    # Rate limiting
    pubmed_requests_per_second: float = 3.0  # 10 with API key
    scholarly_min_delay: float = 5.0  # Seconds between Google Scholar requests
    scholarly_max_delay: float = 15.0  # Random delay for anti-blocking

    # Search defaults
    default_max_results_per_query: int = 500
    default_queries_per_database: int = 3

    # Database
    database_url: str = "postgresql+asyncpg://arakis:password@localhost:5432/arakis"

    # Redis cache
    redis_url: str = "redis://localhost:6379/0"

    # Object Storage (S3/MinIO)
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket_name: str = "arakis-pdfs"
    s3_region: str = "us-east-1"

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = ""  # For JWT - generate with: openssl rand -hex 32
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # Apple OAuth
    apple_client_id: str = ""  # Service ID (e.g., com.example.app.signin)
    apple_team_id: str = ""  # 10-character Team ID
    apple_key_id: str = ""  # Key ID from Apple Developer Portal
    apple_private_key: str = ""  # Contents of .p8 file (newlines as \n)

    # Frontend URLs for OAuth redirects
    frontend_url: str = "http://localhost:3000"
    oauth_success_redirect: str = "/auth/success"
    oauth_error_redirect: str = "/auth/error"

    # Rate Limiting
    rate_limit_auth_requests: int = 10  # Auth endpoints per minute
    rate_limit_login_requests: int = 5  # Login attempts per minute
    rate_limit_oauth_requests: int = 10  # OAuth attempts per 5 minutes
    rate_limit_token_refresh_requests: int = 10  # Token refreshes per minute

    # Debug mode
    debug: bool = False

    @property
    def pubmed_rate_limit(self) -> float:
        """Return appropriate rate limit based on API key presence."""
        return 10.0 if self.ncbi_api_key else 3.0

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to async-compatible format.

        Railway provides DATABASE_URL as postgresql://... but we need
        postgresql+asyncpg://... for async SQLAlchemy.
        """
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Convert DATABASE_URL to sync format for Alembic migrations.

        Handles both postgresql:// and postgresql+asyncpg:// formats.
        """
        url = self.database_url
        if "+asyncpg" in url:
            return url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

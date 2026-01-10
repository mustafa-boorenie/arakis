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

    # SerpAPI (optional - alternative to scholarly for Google Scholar)
    serpapi_key: str = ""

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

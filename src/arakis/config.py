"""Configuration management for Arakis."""

from dataclasses import dataclass
from enum import Enum
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

    # Batch processing configuration
    # Controls how many items are processed concurrently to balance speed vs rate limits
    batch_size_screening: int = 5  # Papers to screen concurrently (dual-review = 2x API calls each)
    batch_size_extraction: int = 3  # Papers to extract concurrently (triple-review = 3x API calls each)
    batch_size_fetch: int = 10  # Papers to fetch concurrently (HTTP requests, not LLM)
    batch_size_embedding: int = 100  # Texts to embed per API call (OpenAI supports up to 2048)

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


# =============================================================================
# Cost Mode Configuration
# =============================================================================

class CostMode(str, Enum):
    """Cost/quality optimization modes.
    
    All modes use full text for screening and extraction.
    Cost savings come from cheaper models and fewer review passes.
    """
    QUALITY = "QUALITY"       # Maximum accuracy - gpt-5-mini dual/triple + gpt-5.2-max reasoning
    BALANCED = "BALANCED"     # Good quality at reasonable cost - gpt-5-nano single + o3-mini (DEFAULT)
    FAST = "FAST"             # Speed focused - gpt-5-nano single, skips RoB/Analysis
    ECONOMY = "ECONOMY"       # Minimum cost - gpt-5-nano single, minimal prompts, skips RoB/Analysis


@dataclass(frozen=True)
class ModeConfig:
    """Configuration for a specific cost mode.
    
    Attributes:
        name: Mode name for display
        description: Human-readable description
        screening_model: Model for screening agent
        screening_dual_review: Whether to use dual-review (2 passes)
        extraction_model: Model for extraction agent
        extraction_triple_review: Whether to use triple-review (3 passes)
        use_full_text: Whether to use full text (ALWAYS True in all modes)
        writing_model: Model for writing agents
        max_reasoning_effort: For reasoning models, use max effort (QUALITY mode only)
        skip_rob: Skip Risk of Bias stage
        skip_analysis: Skip meta-analysis stage
        minimal_writing: Use minimal prompts for writing
    """
    name: str
    description: str
    screening_model: str
    screening_dual_review: bool
    extraction_model: str
    extraction_triple_review: bool
    use_full_text: bool  # Always True - we never use abstracts only
    writing_model: str
    max_reasoning_effort: bool
    skip_rob: bool
    skip_analysis: bool
    minimal_writing: bool


# Mode configurations
# PRISMA is ALWAYS programmatic SVG in ALL modes (no LLM cost)
MODE_CONFIGS: dict[CostMode, ModeConfig] = {
    CostMode.QUALITY: ModeConfig(
        name="Quality",
        description="Maximum accuracy for publication-quality reviews. Uses best models with multiple review passes.",
        screening_model="gpt-5-mini",
        screening_dual_review=True,  # 2 passes at different temperatures
        extraction_model="gpt-5-mini",
        extraction_triple_review=True,  # 3 passes at different temperatures
        use_full_text=True,  # Always True
        writing_model="gpt-5.2-2025-12-11",
        max_reasoning_effort=True,  # Use max reasoning effort
        skip_rob=False,
        skip_analysis=False,
        minimal_writing=False,
    ),
    
    CostMode.BALANCED: ModeConfig(
        name="Balanced",
        description="Good quality at reasonable cost. Recommended for most systematic reviews.",
        screening_model="gpt-5-nano",
        screening_dual_review=False,  # Single pass
        extraction_model="gpt-5-nano",
        extraction_triple_review=False,  # Single pass
        use_full_text=True,  # Always True
        writing_model="o3-mini",
        max_reasoning_effort=False,
        skip_rob=False,
        skip_analysis=False,
        minimal_writing=False,
    ),
    
    CostMode.FAST: ModeConfig(
        name="Fast",
        description="Speed focused. Skips RoB and Analysis stages for faster results.",
        screening_model="gpt-5-nano",
        screening_dual_review=False,
        extraction_model="gpt-5-nano",
        extraction_triple_review=False,
        use_full_text=True,  # Always True
        writing_model="o3-mini",
        max_reasoning_effort=False,
        skip_rob=True,  # Skip Risk of Bias
        skip_analysis=True,  # Skip meta-analysis
        minimal_writing=False,
    ),
    
    CostMode.ECONOMY: ModeConfig(
        name="Economy",
        description="Minimum cost for proof of concept or very large reviews. Skips non-essential stages.",
        screening_model="gpt-5-nano",
        screening_dual_review=False,
        extraction_model="gpt-5-nano",
        extraction_triple_review=False,
        use_full_text=True,  # Always True
        writing_model="o3-mini",
        max_reasoning_effort=False,
        skip_rob=True,  # Skip Risk of Bias
        skip_analysis=True,  # Skip meta-analysis
        minimal_writing=True,  # Use minimal writing prompts
    ),
}


def get_mode_config(mode: CostMode | str) -> ModeConfig:
    """Get configuration for a cost mode.
    
    Args:
        mode: Cost mode enum or string name
        
    Returns:
        ModeConfig for the specified mode
        
    Raises:
        ValueError: If mode is not recognized
    """
    if isinstance(mode, str):
        try:
            mode = CostMode(mode.upper())
        except ValueError:
            valid_modes = [m.value for m in CostMode]
            raise ValueError(f"Invalid cost mode: {mode}. Valid modes: {valid_modes}")
    
    return MODE_CONFIGS[mode]


def get_default_mode() -> CostMode:
    """Get the default cost mode.
    
    Returns:
        Default cost mode (BALANCED)
    """
    return CostMode.BALANCED


def get_default_mode_config() -> ModeConfig:
    """Get configuration for the default cost mode.
    
    Returns:
        ModeConfig for BALANCED mode
    """
    return MODE_CONFIGS[CostMode.BALANCED]


def list_modes() -> list[dict[str, str]]:
    """List all available modes with descriptions.
    
    Returns:
        List of mode info dictionaries
    """
    return [
        {
            "value": mode.value,
            "name": config.name,
            "description": config.description,
        }
        for mode, config in MODE_CONFIGS.items()
    ]


def validate_mode(mode: str) -> CostMode:
    """Validate and normalize a cost mode string.
    
    Args:
        mode: Mode string to validate
        
    Returns:
        Normalized CostMode enum
        
    Raises:
        ValueError: If mode is invalid
    """
    try:
        return CostMode(mode.upper())
    except ValueError:
        valid = [m.value for m in CostMode]
        raise ValueError(f"Invalid cost mode '{mode}'. Must be one of: {', '.join(valid)}")

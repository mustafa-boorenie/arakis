"""FastAPI application for Arakis systematic review platform."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from arakis.api.routers import workflows, manuscripts
from arakis.config import get_settings
from arakis.database.connection import async_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Arakis API...")
    print(f"📊 Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    print(f"🔑 Debug mode: {settings.debug}")

    yield

    # Shutdown
    print("🛑 Shutting down Arakis API...")
    await async_engine.dispose()
    print("✅ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Arakis Systematic Review Platform API",
    description="""
    REST API for automated systematic reviews using AI.

    ## Features

    - **Workflow Management**: Create and manage systematic review workflows
    - **Automated Search**: Search multiple academic databases (PubMed, OpenAlex, etc.)
    - **AI Screening**: Automated paper screening with dual-review support
    - **Data Extraction**: Structured data extraction from papers
    - **Statistical Analysis**: Meta-analysis and statistical testing
    - **Manuscript Generation**: Automated manuscript writing
    - **Export**: Export manuscripts in JSON, Markdown, PDF, and DOCX formats

    ## Workflow

    1. **Create Workflow**: POST /api/workflows with research question and criteria
    2. **Monitor Progress**: GET /api/workflows/{id} to check status
    3. **Export Results**: GET /api/manuscripts/{id}/{format} when completed

    ## Authentication

    Currently in development mode - authentication will be added in production.
    """,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware - allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflows.router)
app.include_router(manuscripts.router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Arakis Systematic Review Platform API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "workflows": "/api/workflows",
            "manuscripts": "/api/manuscripts",
        },
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns 200 OK if the API is running and can connect to the database.
    """
    try:
        # Test database connection
        from sqlalchemy import text

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            },
        )


@app.get("/health/storage", tags=["health"])
async def storage_health_check():
    """
    Storage health check endpoint.

    Returns status of S3-compatible object storage (R2, S3, MinIO).
    """
    from arakis.storage import get_storage_client

    storage = get_storage_client()
    health = storage.health_check()

    response = {
        "status": "healthy" if health.connected and health.bucket_exists else "unhealthy",
        "storage": {
            "connected": health.connected,
            "bucket_exists": health.bucket_exists,
            "bucket_name": health.bucket_name,
            "endpoint": health.endpoint,
        },
    }

    if health.error:
        response["storage"]["error"] = health.error

    if not health.connected or not health.bucket_exists:
        return JSONResponse(status_code=503, content=response)

    return response


@app.get("/health/all", tags=["health"])
async def full_health_check():
    """
    Full health check for all services.

    Checks database, storage, and other dependencies.
    """
    from sqlalchemy import text
    from arakis.storage import get_storage_client

    health_status = {
        "status": "healthy",
        "services": {},
    }
    all_healthy = True

    # Database check
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = {"status": "connected"}
    except Exception as e:
        health_status["services"]["database"] = {"status": "disconnected", "error": str(e)}
        all_healthy = False

    # Storage check
    storage = get_storage_client()
    storage_health = storage.health_check()
    health_status["services"]["storage"] = {
        "status": "connected" if storage_health.connected and storage_health.bucket_exists else "disconnected",
        "bucket": storage_health.bucket_name,
        "configured": storage.is_configured,
    }
    if storage_health.error:
        health_status["services"]["storage"]["error"] = storage_health.error
    if not storage_health.connected or not storage_health.bucket_exists:
        # Storage is optional, don't fail health check
        health_status["services"]["storage"]["status"] = "unavailable"

    health_status["status"] = "healthy" if all_healthy else "degraded"

    status_code = 200 if all_healthy else 503
    return JSONResponse(status_code=status_code, content=health_status)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found. See /docs for available endpoints."},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please try again or contact support."
        },
    )


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "arakis.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

# Database Setup Guide

This guide covers Phase 1: Database Layer setup for the Arakis production deployment.

## Overview

Arakis now includes a complete database layer with:
- **PostgreSQL** - Persistent storage for workflows, papers, extractions, and manuscripts
- **Redis** - Caching layer for improved performance
- **MinIO** - S3-compatible object storage for PDF files
- **Alembic** - Database migration management

## Quick Start (Local Development)

### 1. Prerequisites

Ensure you have the following installed:
- Docker Desktop (or Docker Engine + Docker Compose)
- Python 3.9+ with pip

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs all required packages including:
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- asyncpg (async PostgreSQL driver)
- FastAPI (API framework)
- Redis client
- boto3/minio (S3 storage)

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here
UNPAYWALL_EMAIL=your.email@example.com
```

The database credentials are pre-configured for local development.

### 4. Start Services

Start PostgreSQL, Redis, and MinIO with Docker Compose:

```bash
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

You should see:
- `arakis-postgres` on port 5432
- `arakis-redis` on port 6379
- `arakis-minio` on ports 9000 (API) and 9001 (Console)

### 5. Run Database Migrations

Create the initial database schema:

```bash
alembic upgrade head
```

If you need to generate a new migration after changing models:

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### 6. Verify Setup

Check that the database is accessible:

```bash
docker-compose exec postgres psql -U arakis -d arakis -c "\dt"
```

You should see tables: `workflows`, `papers`, `screening_decisions`, `extractions`, `manuscripts`, `users`

## Database Schema

### Workflow
Main systematic review workflow tracking.

**Fields:**
- `id` (UUID) - Primary key
- `research_question` - The research question
- `inclusion_criteria`, `exclusion_criteria` - Screening criteria
- `databases` (JSON) - List of databases searched
- `status` - "running", "completed", "failed"
- `papers_found`, `papers_screened`, `papers_included` - Statistics
- `total_cost` - Total API cost in USD
- `created_at`, `completed_at` - Timestamps

### Paper
Academic papers from literature search.

**Key Fields:**
- `id` (String) - Primary key (e.g., "pubmed_12345")
- `workflow_id` - Foreign key to Workflow
- `doi`, `pmid`, `pmcid` - Paper identifiers
- `title`, `abstract`, `full_text` - Paper content
- `text_extraction_method` - "pymupdf", "pdfplumber", "ocr"
- `text_quality_score` - Quality score (0.0-1.0)
- `pdf_file_path` - S3/MinIO path to PDF
- `open_access` - Boolean

### ScreeningDecision
AI-powered screening decisions.

**Fields:**
- `paper_id` - Foreign key to Paper
- `status` - "INCLUDE", "EXCLUDE", "MAYBE"
- `reason` - Explanation
- `confidence` - Confidence score (0.0-1.0)
- `matched_inclusion`, `matched_exclusion` (JSON) - Matched criteria
- `is_conflict` - Dual-review conflict flag
- `human_reviewed`, `human_decision` - Human review tracking

### Extraction
Structured data extraction from papers.

**Fields:**
- `paper_id` - Foreign key to Paper
- `schema_name` - "rct", "cohort", "case_control"
- `data` (JSON) - Extracted fields
- `confidence` (JSON) - Per-field confidence scores
- `extraction_quality` - Overall quality (0.0-1.0)
- `needs_human_review` - Boolean flag
- `reviewer_decisions` (JSON) - Triple-review audit trail

### Manuscript
Generated manuscript sections.

**Fields:**
- `workflow_id` - Foreign key to Workflow (one-to-one)
- `title`, `abstract` - Manuscript metadata
- `introduction`, `methods`, `results`, `discussion`, `conclusions` - Sections (Markdown)
- `figures`, `tables` (JSON) - Figure and table data
- `meta` (JSON) - Authors, affiliations, keywords
- `references` (JSON) - Bibliography

### User
User accounts (for future multi-user support).

**Fields:**
- `id` (UUID) - Primary key
- `email` - Unique email address
- `hashed_password` - Bcrypt password hash
- `is_active`, `is_admin` - Status flags
- `total_workflows`, `total_cost` - Usage tracking

## Accessing Services

### PostgreSQL
```bash
# Connect to database
docker-compose exec postgres psql -U arakis -d arakis

# Backup database
docker-compose exec postgres pg_dump -U arakis arakis > backup.sql

# Restore database
docker-compose exec -T postgres psql -U arakis -d arakis < backup.sql
```

### Redis
```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Check cache stats
docker-compose exec redis redis-cli INFO stats
```

### MinIO Console
Open http://localhost:9001 in your browser.
- Username: `minioadmin`
- Password: `minioadmin`

Browse the `arakis-pdfs` bucket to see stored PDF files.

### MinIO API
Access via http://localhost:9000

The S3-compatible API can be used with boto3:
```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# List PDFs
s3.list_objects_v2(Bucket='arakis-pdfs')
```

## Troubleshooting

### Port Already in Use
If ports 5432, 6379, 9000, or 9001 are already in use:

1. Stop existing services using those ports
2. Or modify `docker-compose.yml` to use different ports:
```yaml
postgres:
  ports:
    - "5433:5432"  # Change host port
```

### Database Connection Refused
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Alembic Connection Error
Ensure:
1. Docker services are running: `docker-compose ps`
2. `.env` file has correct `DATABASE_URL`
3. PostgreSQL is healthy: `docker-compose exec postgres pg_isready`

### Reset Everything
To start fresh:
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Restart services
docker-compose up -d

# Re-run migrations
alembic upgrade head
```

## Production Deployment

For production deployment (Phase 4):
- Use managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- Use managed Redis (AWS ElastiCache, Redis Cloud, etc.)
- Use AWS S3 or managed MinIO
- Set strong passwords in environment variables
- Enable SSL/TLS for all connections
- Configure backups and monitoring

See the full deployment plan in `/Users/mustafaboorenie/.claude/plans/imperative-popping-rabbit.md`

## Next Steps

Phase 1 is complete! Next up:

**Phase 2: REST API** (Week 2)
- Create FastAPI application
- Implement workflow CRUD endpoints
- Add manuscript export endpoints (JSON, PDF, DOCX)
- Background task execution

**Phase 3: Dockerization** (Week 3)
- Create Dockerfile for API
- Update docker-compose.yml with API service
- Test complete stack locally

**Phase 4: VM Deployment** (Week 4)
- Deploy to production VM
- Configure nginx reverse proxy
- Setup SSL certificates

**Phase 5: CI/CD** (Week 5)
- GitHub Actions workflow
- Automated testing and deployment

## Phase 1 Summary

✅ **Completed:**
1. Added all database dependencies to `pyproject.toml`
2. Created SQLAlchemy models (`src/arakis/database/models.py`)
3. Created database connection module (`src/arakis/database/connection.py`)
4. Updated configuration (`src/arakis/config.py`)
5. Initialized Alembic migrations (`src/arakis/database/migrations/`)
6. Created `.env.example` with all required environment variables
7. Created `docker-compose.yml` for local development
8. Documentation and setup guide

**Database Infrastructure:**
- PostgreSQL 15 with async support (asyncpg + SQLAlchemy 2.0)
- Redis 7 for caching
- MinIO for object storage (S3-compatible)
- Alembic for version-controlled schema migrations
- Docker Compose for local development

**Time Spent:** ~2 hours
**Next Phase:** REST API Development (Phase 2)

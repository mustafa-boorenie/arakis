# Phase 1: Database Layer - COMPLETED ✅

**Date:** January 9, 2026
**Duration:** ~3 hours
**Status:** Successfully Completed

## Summary

Phase 1 of the production deployment plan has been successfully completed. The Arakis systematic review platform now has a complete database layer with PostgreSQL, Redis, MinIO, and Alembic migrations.

## Accomplishments

### 1. Dependencies Added ✅
Added all required database and API dependencies to `pyproject.toml`:
- **Database:** SQLAlchemy 2.0, Alembic 1.13, asyncpg 0.29, psycopg2-binary 2.9
- **API:** FastAPI 0.109, Uvicorn 0.27, python-multipart, pyjwt 2.8
- **Caching:** Redis 5.0 with async support
- **Storage:** boto3 1.34, minio 7.2
- **Development:** mypy 1.5, pytest-cov 4.0, ruff 0.1

### 2. Database Models Created ✅
Complete SQLAlchemy ORM models (`src/arakis/database/models.py`):

**Workflow Table:**
- Tracks systematic review workflows
- Stores research question, criteria, statistics, and costs
- Relationships to papers, screening decisions, extractions, and manuscripts

**Paper Table:**
- Academic papers with full metadata
- Identifiers: DOI, PMID, PMCID, arXiv, Semantic Scholar, OpenAlex
- Full text extraction support with quality scores
- PDF storage paths (S3/MinIO)

**ScreeningDecision Table:**
- AI-powered screening decisions
- Dual-review support with conflict detection
- Human review tracking and override capability

**Extraction Table:**
- Structured data extraction from papers
- Triple-review support with confidence scores
- Flexible schema support (RCT, cohort, case-control, diagnostic)

**Manuscript Table:**
- Generated manuscript sections (Markdown)
- Figures and tables storage (JSON)
- Complete metadata and references

**User Table:**
- Multi-user support (for future)
- Authentication with hashed passwords
- Usage tracking (workflows, costs)

### 3. Database Connection Module ✅
Created `src/arakis/database/connection.py`:
- Async engine for API operations (asyncpg)
- Sync engine for migrations (psycopg2)
- FastAPI dependency (`get_db()`)
- Connection pooling (20 connections, 40 overflow)
- Health checks enabled

### 4. Configuration Updated ✅
Enhanced `src/arakis/config.py` with:
- Database URL configuration
- Redis URL
- S3/MinIO settings (endpoint, credentials, bucket)
- API settings (host, port, JWT secret, algorithm)
- Debug mode flag
- Python 3.9+ compatibility (Optional instead of | syntax)

### 5. Alembic Migrations ✅
Complete migration setup:
- Initialized Alembic in `src/arakis/database/migrations/`
- Created `alembic.ini` configuration
- Custom `env.py` with automatic settings loading
- Generated initial schema migration
- Applied migration successfully

**Migration:** `2026_01_09_1950_initial_schema.py`
**Tables Created:** 7 (alembic_version, workflows, papers, screening_decisions, extractions, manuscripts, users)
**Indexes Created:** 4 (email, doi, pmid, pmcid)

### 6. Environment Configuration ✅
- Created `.env.example` with all required variables
- Updated `.env` with database credentials
- Documented all configuration options

### 7. Docker Compose ✅
Created `docker-compose.yml` with services:

**PostgreSQL 15 (Port 5433):**
- User: arakis
- Database: arakis
- Health checks enabled
- Persistent volume

**Redis 7 (Port 6379):**
- Append-only file persistence
- Health checks enabled
- Persistent volume

**MinIO (Ports 9000, 9001):**
- S3-compatible object storage
- Console at http://localhost:9001
- Auto-created `arakis-pdfs` bucket
- Persistent volume

**Notes:**
- Changed PostgreSQL port from 5432 → 5433 to avoid conflict with local installation
- All services networked via `arakis-network`
- Health checks ensure dependencies start in correct order

### 8. Documentation ✅
Created comprehensive guides:
- `DATABASE_SETUP.md` - Complete setup and troubleshooting guide
- `PHASE_1_COMPLETE.md` - This summary document

## Technical Details

### Database Schema
```
users
  id (UUID PK)
  email (unique, indexed)
  hashed_password
  full_name, affiliation
  is_active, is_admin
  created_at, last_login
  total_workflows, total_cost

workflows
  id (UUID PK)
  research_question
  inclusion_criteria, exclusion_criteria
  databases (JSON)
  status
  papers_found, papers_screened, papers_included
  total_cost
  created_at, completed_at
  user_id (FK → users)

papers
  id (String PK) e.g., "pubmed_12345"
  workflow_id (FK → workflows)
  doi (indexed), pmid (indexed), pmcid (indexed)
  arxiv_id, s2_id, openalex_id
  title, abstract, full_text
  text_extraction_method, text_quality_score
  pdf_url, pdf_file_path (S3)
  journal, year, authors (JSON), keywords (JSON)
  source, retrieved_at

screening_decisions
  id (Integer PK)
  workflow_id (FK → workflows)
  paper_id (FK → papers)
  status (INCLUDE/EXCLUDE/MAYBE)
  reason, confidence
  matched_inclusion, matched_exclusion (JSON)
  is_conflict, second_opinion (JSON)
  human_reviewed, ai_decision, human_decision
  created_at

extractions
  id (Integer PK)
  workflow_id (FK → workflows)
  paper_id (FK → papers)
  schema_name (rct/cohort/case_control/diagnostic)
  extraction_method
  data (JSON), confidence (JSON)
  extraction_quality
  needs_human_review
  reviewer_decisions (JSON)
  conflicts, low_confidence_fields (JSON)
  created_at

manuscripts
  id (Integer PK)
  workflow_id (FK → workflows, unique)
  title, abstract
  introduction, methods, results, discussion, conclusions (Markdown)
  references, figures, tables (JSON)
  meta (JSON) - authors, keywords, funding
  created_at, updated_at
```

### Connection String
```
postgresql+asyncpg://arakis:arakis_dev_password@127.0.0.1:5433/arakis
```

## Verified Working

✅ PostgreSQL database created and accessible
✅ All 7 tables created with correct schema
✅ Alembic migrations working
✅ Redis running and accessible
✅ MinIO running with `arakis-pdfs` bucket
✅ Docker Compose orchestration
✅ Database connection from host machine

## Issues Resolved

### Python Version Compatibility
**Issue:** `str | None` syntax not supported in Python 3.9
**Fix:** Changed to `Optional[str]` from typing module

### Reserved Attribute Name
**Issue:** `metadata` is reserved in SQLAlchemy
**Fix:** Renamed Manuscript.metadata → Manuscript.meta

### Port Conflict
**Issue:** Local PostgreSQL installation on port 5432
**Fix:** Changed Docker port mapping to 5433

### IPv6 vs IPv4
**Issue:** localhost resolving to IPv6 (::1)
**Fix:** Used 127.0.0.1 explicitly in DATABASE_URL

## File Changes Summary

### Created Files:
- `src/arakis/database/__init__.py`
- `src/arakis/database/models.py`
- `src/arakis/database/connection.py`
- `src/arakis/database/migrations/env.py`
- `src/arakis/database/migrations/versions/2026_01_09_1950_initial_schema.py`
- `alembic.ini`
- `docker-compose.yml`
- `.env.example`
- `DATABASE_SETUP.md`
- `PHASE_1_COMPLETE.md`

### Modified Files:
- `pyproject.toml` - Added database/API dependencies
- `src/arakis/config.py` - Added database/API settings
- `.env` - Added database configuration

## What's Next

### Phase 2: REST API (Week 2)
**Goals:**
- Create FastAPI application structure
- Implement workflow CRUD endpoints
- Add manuscript export endpoints (JSON, Markdown, PDF, DOCX)
- Background task execution for workflows
- Pydantic schemas for validation

**Key Files to Create:**
- `src/arakis/api/main.py` - FastAPI app
- `src/arakis/api/routers/workflows.py` - Workflow endpoints
- `src/arakis/api/routers/manuscripts.py` - Export endpoints
- `src/arakis/api/schemas/` - Pydantic models
- `src/arakis/api/dependencies.py` - Auth and DB dependencies

**Endpoints to Implement:**
```
POST   /api/workflows              - Create and start workflow
GET    /api/workflows              - List all workflows
GET    /api/workflows/{id}         - Get workflow details
DELETE /api/workflows/{id}         - Delete workflow

GET    /api/manuscripts/{id}/json  - Export as JSON (for UI)
GET    /api/manuscripts/{id}/md    - Export as Markdown
GET    /api/manuscripts/{id}/pdf   - Export as PDF
GET    /api/manuscripts/{id}/docx  - Export as Word document
```

### Phase 3: Dockerization (Week 3)
- Create Dockerfile for API
- Update docker-compose.yml to include API service
- Multi-stage build for smaller images
- Test complete stack locally

### Phase 4: VM Deployment (Week 4)
- Deploy to production VM
- Configure nginx reverse proxy
- Setup SSL with Let's Encrypt
- Configure backups

### Phase 5: CI/CD (Week 5)
- GitHub Actions workflow
- Automated testing on PRs
- Automated deployment on merge to main
- Health checks and rollback

## Testing the Setup

### 1. Check Services
```bash
docker-compose ps
```

All should show "healthy" status.

### 2. Connect to Database
```bash
docker-compose exec postgres psql -U arakis -d arakis
```

### 3. List Tables
```sql
\dt
```

Should show 7 tables.

### 4. Check Alembic History
```bash
alembic history
```

Should show the initial schema migration.

### 5. Access MinIO Console
Open http://localhost:9001
- Username: minioadmin
- Password: minioadmin

### 6. Check Redis
```bash
docker-compose exec redis redis-cli ping
```

Should return "PONG".

## Resources

- **Plan:** `/Users/mustafaboorenie/.claude/plans/imperative-popping-rabbit.md`
- **Setup Guide:** `DATABASE_SETUP.md`
- **Docker Logs:** `docker-compose logs -f`
- **PostgreSQL Logs:** `docker-compose logs postgres`

## Success Metrics

**Alpha Criteria (Phase 1):**
✅ Database models defined
✅ Migrations system working
✅ Local development environment
✅ All services running in Docker
✅ Connection pooling configured
✅ Documentation complete

**Status:** READY FOR PHASE 2

---

**Phase 1 Complete!** 🎉

The database foundation is now in place for Arakis. We can now proceed with Phase 2 to build the REST API on top of this solid data layer.

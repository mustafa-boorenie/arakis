# Changelog

All notable changes to the Arakis project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-09

### Production Deployment Release - Full Infrastructure Stack

This release transforms Arakis from a CLI-only tool into a production-ready web service with complete database, API, containerization, deployment, and CI/CD infrastructure.

### Added

#### Phase 1: Database Layer
- PostgreSQL database with SQLAlchemy ORM models
- Alembic migrations for schema management
- Redis caching layer
- MinIO/S3 object storage for PDFs
- Models: Workflow, Paper, Extraction, Manuscript, User
- Database connection pooling and async support
- Migration scripts and database initialization

#### Phase 2: REST API
- FastAPI application with async endpoints
- Workflow management API (create, list, get, delete)
- Manuscript export endpoints (JSON, Markdown, PDF, DOCX)
- Background task execution for long-running workflows
- Authentication and authorization middleware
- API documentation with OpenAPI/Swagger
- Health check and monitoring endpoints
- Rate limiting and request validation
- CORS configuration for frontend integration

#### Phase 3: Dockerization
- Multi-stage Dockerfile for optimized builds
- Docker Compose for local development
- Production Docker Compose configuration
- Service orchestration (API, PostgreSQL, Redis, MinIO)
- Volume management for data persistence
- Network configuration and service discovery
- Health checks for all services
- Environment-based configuration

#### Phase 4: VM Deployment Infrastructure
- Automated VM setup script (Ubuntu 22.04)
- Nginx reverse proxy configuration
- UFW firewall configuration
- Let's Encrypt SSL/TLS automation with Certbot
- Systemd service for application management
- Automated backup scripts with rotation
- Health check monitoring scripts
- System optimization and tuning
- Log aggregation and rotation
- Deployment checklists and documentation

#### Phase 5: CI/CD Pipeline
- GitHub Actions continuous integration workflow
  - Linting (ruff, mypy)
  - Testing with coverage reports
  - Security scanning (bandit, safety)
  - Docker build validation
  - Integration tests with full stack
- GitHub Actions Docker build workflow
  - Multi-architecture builds (linux/amd64, linux/arm64)
  - Container security scanning (Trivy, Grype)
  - SBOM generation for supply chain security
  - GitHub Container Registry publishing
  - Image tagging and versioning
- GitHub Actions continuous deployment workflow
  - Pre-deployment database backup
  - Zero-downtime rolling deployments
  - Comprehensive health checks
  - Smoke testing
  - Automatic rollback on failure
  - Deployment notifications
- Deployment automation scripts
  - `scripts/deploy.sh` - Automated deployment with validation
  - `scripts/rollback.sh` - One-command rollback with database restore
- Documentation
  - Comprehensive CI/CD guide
  - Scripts documentation and troubleshooting
  - Deployment workflows and best practices

### Infrastructure

- **Database**: PostgreSQL 15 with connection pooling
- **Cache**: Redis 7 for session and data caching
- **Storage**: MinIO for S3-compatible object storage
- **API**: FastAPI with Uvicorn ASGI server
- **Reverse Proxy**: Nginx with SSL/TLS termination
- **Orchestration**: Docker Compose for service management
- **CI/CD**: GitHub Actions with multi-stage pipelines
- **Security**: Firewall, SSL certificates, secret scanning, vulnerability scanning

### Documentation

- Production deployment guide
- API reference documentation
- CI/CD setup and usage guide
- Database schema documentation
- Docker configuration guide
- Troubleshooting and FAQ
- Development workflow documentation
- Security best practices

### Performance

- Async/await throughout for I/O operations
- Database connection pooling
- Redis caching for frequent queries
- Multi-worker Uvicorn deployment
- Optimized Docker images (~400MB)
- CDN-ready static asset serving

### Security

- JWT-based authentication
- Rate limiting on API endpoints
- SQL injection prevention via ORM
- XSS protection headers
- CORS whitelist configuration
- Secret scanning in CI/CD
- Container vulnerability scanning
- Dependency security auditing
- Automated security updates

### Changed

- Moved all documentation to `docs/` directory
- Reorganized demo scripts into `examples/` directory
- Consolidated output files into `data/` directory
- Updated repository structure for better organization
- Enhanced .gitignore for production files

### Infrastructure Metrics

- **CI/CD Pipeline Time**: ~40-60 minutes (PR to production)
- **Deployment Time**: ~5-10 minutes (zero-downtime)
- **Rollback Time**: <2 minutes (automated)
- **Test Coverage**: Comprehensive with integration tests
- **Container Size**: ~400MB (multi-stage optimized)
- **Startup Time**: <30 seconds (all services)

---

## [0.1.0] - 2024-12-XX

### Initial CLI Release

The foundational release establishing Arakis as an AI-powered systematic review automation tool.

### Added

#### Core Search Capabilities
- Multi-database search orchestration
- QueryGeneratorAgent with LLM-powered query optimization
- Support for PubMed, OpenAlex, Semantic Scholar, Google Scholar
- MeSH term and controlled vocabulary integration
- PICO framework extraction
- Query validation and refinement
- Comprehensive deduplication (DOI, PMID, fuzzy title matching)

#### Paper Screening
- ScreeningAgent with dual-review mode (default)
- Confidence scoring and conflict detection
- Human-in-the-loop review support
- Inclusion/exclusion criteria matching
- Conservative conflict resolution

#### Full-Text Retrieval
- Waterfall retrieval pattern
- Unpaywall, PMC, and arXiv integration
- Open access detection
- PDF download and management

#### Data Extraction
- DataExtractionAgent with triple-review mode
- Pre-built schemas (RCT, cohort, case-control, diagnostic)
- Majority voting for extraction conflicts
- Quality assessment and confidence scoring
- Structured JSON output

#### Analysis
- AnalysisRecommenderAgent for statistical test selection
- StatisticalEngine with parametric and non-parametric tests
- MetaAnalysisEngine with random/fixed effects models
- Heterogeneity assessment (I², tau², Q-statistic)
- Effect size calculations
- Publication bias detection

#### Visualization
- PRISMA 2020 flow diagrams
- Forest plots for meta-analysis
- Funnel plots for publication bias
- Box plots and bar charts
- Publication-ready 300 DPI output

#### Manuscript Writing
- ResultsWriterAgent for results sections
- IntroductionWriterAgent with funnel approach
- DiscussionWriterAgent with literature comparison
- RAG system for literature context retrieval
- Embedding cache for efficient retrieval
- PRISMA 2020 compliance

#### RAG System
- Embedder with OpenAI text-embedding-3-small
- FAISS-based vector store
- Retriever with semantic similarity search
- EmbeddingCacheStore with SQLite persistence
- Diversity filtering and score thresholding

### CLI Commands
- `arakis search` - Multi-database literature search
- `arakis screen` - AI-powered paper screening
- `arakis fetch` - Full-text paper retrieval
- `arakis extract` - Structured data extraction
- `arakis analyze` - Statistical analysis and meta-analysis
- `arakis prisma-diagram` - PRISMA flow diagram generation
- `arakis write-results` - Results section writing
- `arakis write-intro` - Introduction section writing
- `arakis write-discussion` - Discussion section writing
- `arakis workflow` - End-to-end systematic review pipeline

### Configuration
- Environment-based configuration with .env support
- API key management (OpenAI, NCBI, Elsevier, SerpAPI, Unpaywall)
- Rate limit configuration
- Customizable retry logic with exponential backoff

### Documentation
- Comprehensive README with architecture overview
- API client documentation
- Data model specifications
- Rate limit handling guide
- Paper full-text extraction guide
- Manuscript template
- Workflow guide
- Quick start guide
- Examples and use cases

### Testing
- Async test suite with pytest-asyncio
- Mock-based tests to avoid API costs
- Integration tests for key workflows
- Coverage reporting

---

## Release Links

- [0.2.0] - Production Deployment (Database, API, Docker, VM, CI/CD)
- [0.1.0] - Initial CLI Release

---

## Detailed Phase Documentation

For detailed technical documentation of each development phase, see:
- `docs/development/PHASE_1_COMPLETE.md` - Database Layer
- `docs/development/PHASE_2_COMPLETE.md` - REST API
- `docs/development/PHASE_3_COMPLETE.md` - Dockerization
- `docs/development/PHASE_4_COMPLETE.md` - VM Deployment
- `docs/development/PHASE_5_COMPLETE.md` - CI/CD Pipeline

# Arakis: AI-Powered Systematic Review Platform

[![CI](https://github.com/mustafa-boorenie/arakis/workflows/Continuous%20Integration/badge.svg)](https://github.com/mustafa-boorenie/arakis/actions)
[![Docker](https://github.com/mustafa-boorenie/arakis/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)](https://github.com/mustafa-boorenie/arakis/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Arakis is a production-ready AI-powered systematic review platform that automates literature searches, paper screening, data extraction, statistical analysis, and manuscript writing for academic research. Built with LLM agents and enterprise-grade infrastructure, it transforms months of manual work into hours of automated processing.

**🚀 From research question to publishable manuscript in hours, not months.**

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [CLI Usage](#cli-usage)
  - [API Usage](#api-usage)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker](#docker)
- [Usage](#usage)
  - [Complete Workflow](#complete-workflow)
  - [Individual Commands](#individual-commands)
  - [REST API](#rest-api)
- [Deployment](#deployment)
  - [Production Deployment](#production-deployment)
  - [CI/CD Pipeline](#cicd-pipeline)
- [Documentation](#documentation)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)
- [Support](#support)
- [Citation](#citation)

---

## Features

### 🔍 **Intelligent Literature Search**
- **Multi-database search**: PubMed, OpenAlex, Semantic Scholar, Google Scholar, Embase
- **AI-powered query generation**: GPT-4 generates optimized database-specific queries with MeSH terms
- **Query validation**: Result count verification and refinement
- **Multi-strategy deduplication**: DOI, PMID, fuzzy title matching
- **PRISMA flow tracking**: Automatic PRISMA 2020-compliant reporting

### 📄 **Smart Paper Screening**
- **Dual-review mode** (default): Two independent AI reviews with automatic conflict detection
- **Human-in-the-loop**: Optional human verification of AI decisions
- **Confidence scoring**: Transparent decision-making with confidence levels
- **Fast mode**: Single-pass screening for rapid processing

### 📥 **Automated Full-Text Retrieval**
- **Waterfall strategy**: Tries multiple sources (Unpaywall → PMC → arXiv) until success
- **PDF extraction**: Automatic text extraction with quality scoring
- **Quality assessment**: Text quality metrics for extraction reliability

### 📊 **Structured Data Extraction**
- **Triple-review mode** (default): Three independent extractions with majority voting
- **Pre-built schemas**: RCT, cohort, case-control, diagnostic studies
- **Confidence scoring**: Agreement-based confidence metrics
- **Quality flagging**: Automatic detection of low-quality extractions requiring human review
- **Fast mode**: Single-pass extraction for speed

### 📈 **Statistical Analysis**
- **AI-powered test recommendation**: Recommends appropriate statistical tests
- **Meta-analysis**: Random-effects and fixed-effects models with heterogeneity assessment
- **Effect sizes**: Cohen's d, odds ratio, risk ratio, mean difference, Hedges' g
- **Publication bias**: Egger's test, funnel plots
- **Subgroup analysis**: Automatic subgroup comparisons
- **Pure Python**: No LLM costs for statistical computations

### 📝 **Automated Manuscript Writing**
- **Complete sections**: Introduction, methods, results, discussion
- **PRISMA compliance**: Follows PRISMA 2020 guidelines
- **RAG-powered**: Retrieval-Augmented Generation for literature context
- **Publication-ready figures**: Forest plots, funnel plots, PRISMA diagrams (300 DPI)
- **Export formats**: JSON, Markdown, PDF, DOCX

### 🚀 **Production-Ready Infrastructure**
- **REST API**: FastAPI with OpenAPI documentation
- **Database persistence**: PostgreSQL with Alembic migrations
- **Caching**: Redis for performance optimization
- **Object storage**: S3/MinIO for PDF storage
- **Docker containerization**: Multi-stage builds with health checks
- **Automated deployment**: Complete VM setup with Nginx, SSL, backups
- **CI/CD pipeline**: Automated testing, building, deployment with auto-rollback
- **Zero-downtime deployments**: Rolling updates with comprehensive health checks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Arakis Platform                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   CLI Tool   │  │   REST API   │  │  Web UI      │    │
│  │   (Typer)    │  │  (FastAPI)   │  │  (Future)    │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                            │                               │
│         ┌──────────────────┴──────────────────┐           │
│         │                                      │           │
│  ┌──────▼────────┐                    ┌───────▼───────┐  │
│  │  LLM Agents   │                    │   Database    │  │
│  │               │                    │               │  │
│  │ • Query Gen.  │◄───────────────────┤  PostgreSQL   │  │
│  │ • Screener    │                    │               │  │
│  │ • Extractor   │                    │ • Workflows   │  │
│  │ • Analyzer    │                    │ • Papers      │  │
│  │ • Writer      │                    │ • Extractions │  │
│  └───────────────┘                    │ • Manuscripts │  │
│         │                             └───────────────┘  │
│         │                                      │          │
│  ┌──────▼────────┐                    ┌───────▼───────┐  │
│  │   External    │                    │     Cache     │  │
│  │   Services    │                    │     Redis     │  │
│  │ • OpenAI API  │                    └───────────────┘  │
│  │ • PubMed      │                             │         │
│  │ • OpenAlex    │                    ┌────────▼──────┐  │
│  │ • Unpaywall   │                    │    Storage    │  │
│  │ • Semantic    │                    │  MinIO (S3)   │  │
│  │   Scholar     │                    │  • PDF files  │  │
│  └───────────────┘                    └───────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘

                    Production Infrastructure

        ┌────────────────────────────────────────┐
        │        GitHub Actions CI/CD            │
        │  • Automated Testing                   │
        │  • Docker Image Builds                 │
        │  • Security Scanning                   │
        │  • Production Deployment               │
        │  • Automatic Rollback                  │
        └──────────────┬─────────────────────────┘
                       ▼
        ┌────────────────────────────────────────┐
        │       Production Server (VM)           │
        │                                        │
        │  Nginx ──► Docker Compose:            │
        │   SSL        ├── API                   │
        │              ├── PostgreSQL            │
        │              ├── Redis                 │
        │              └── MinIO                 │
        │                                        │
        │  • Automated Backups (daily)          │
        │  • Health Monitoring                   │
        │  • systemd Service                     │
        └────────────────────────────────────────┘
```

---

## Quick Start

### CLI Usage

```bash
# Install Arakis
pip install -e .

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run a complete systematic review
arakis workflow \
  --question "Effect of aspirin on sepsis mortality" \
  --include "Adult patients,Sepsis,Aspirin intervention,Mortality" \
  --exclude "Pediatric,Animal studies" \
  --databases pubmed,openalex \
  --max-results 50 \
  --output ./my_review

# Output includes:
# - search_results.json (all papers found)
# - screening_results.json (included/excluded papers)
# - extraction_results.json (structured data)
# - analysis_results.json (meta-analysis)
# - introduction.md, results.md, discussion.md (manuscript sections)
# - figures/ (forest plots, funnel plots, PRISMA diagram)
```

**Time**: ~10-15 minutes | **Cost**: ~$5-10 (50 papers)

### API Usage

```bash
# Start the API with Docker
docker compose up -d

# Access API documentation
open http://localhost:8000/docs

# Create a workflow via API
curl -X POST http://localhost:8000/api/workflows/ \
  -H "Content-Type: application/json" \
  -d '{
    "research_question": "Effect of aspirin on sepsis mortality",
    "inclusion_criteria": "Adult patients, Sepsis, Aspirin",
    "exclusion_criteria": "Pediatric, Animal studies",
    "databases": ["pubmed", "openalex"],
    "max_results_per_query": 50
  }'

# Get workflow status
curl http://localhost:8000/api/workflows/{workflow_id}

# Export manuscript as PDF
curl http://localhost:8000/api/manuscripts/{workflow_id}/pdf \
  -o manuscript.pdf
```

---

## Installation

### Prerequisites

- **Python 3.11+**
- **OpenAI API key** (for GPT-4)
- **Email address** (for Unpaywall API)
- **Optional**: Docker (for containerized deployment)

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/mustafa-boorenie/arakis.git
cd arakis

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and UNPAYWALL_EMAIL

# 5. Install system dependencies (for PDF processing)
# macOS
brew install tesseract poppler pandoc

# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils pandoc

# 6. Run tests
pytest tests/

# 7. Try the CLI
arakis --help
```

### Docker

```bash
# 1. Clone repository
git clone https://github.com/mustafa-boorenie/arakis.git
cd arakis

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec api alembic upgrade head

# 5. Verify services
docker compose ps
curl http://localhost:8000/health

# 6. Access API documentation
open http://localhost:8000/docs
```

---

## Usage

### Complete Workflow

```bash
arakis workflow \
  --question "Research question here" \
  --include "Inclusion criteria, comma separated" \
  --exclude "Exclusion criteria, comma separated" \
  --databases pubmed,openalex \
  --max-results 100 \
  --output ./output_dir

# Options:
#   --fast              Single-pass mode (faster, lower cost)
#   --skip-analysis     Skip statistical analysis
#   --skip-writing      Skip manuscript generation
#   --validate          Enable query validation
```

### Individual Commands

#### Search Databases
```bash
arakis search "Effect of vitamin D on COVID-19" \
  --databases pubmed,openalex \
  --max-results 200 \
  --output search_results.json
```

#### Screen Papers
```bash
# Dual-review mode (default)
arakis screen search_results.json \
  --include "Human RCTs, COVID-19, Vitamin D" \
  --exclude "Animal studies" \
  --output screening_results.json

# Fast mode (single-pass)
arakis screen search_results.json \
  --include "..." \
  --no-dual-review
```

#### Extract Data
```bash
# Triple-review mode (default)
arakis extract screening_results.json \
  --schema rct \
  --output extraction_results.json

# Fast mode
arakis extract screening_results.json \
  --schema rct \
  --mode fast
```

#### Analyze Data
```bash
arakis analyze extraction_results.json \
  --output analysis_results.json \
  --figures ./figures/
```

#### Generate Visualizations
```bash
# PRISMA diagram
arakis prisma-diagram search_results.json \
  --output prisma_flow.png
```

#### Write Manuscript
```bash
# Introduction
arakis write-intro "Research question" \
  --literature papers.json \
  --use-rag \
  --output introduction.md

# Results
arakis write-results \
  --search search_results.json \
  --screening screening_results.json \
  --analysis analysis_results.json \
  --output results.md

# Discussion
arakis write-discussion analysis_results.json \
  --literature papers.json \
  --use-rag \
  --output discussion.md
```

### REST API

**API Documentation**: http://localhost:8000/docs

**Key Endpoints:**
- `POST /api/workflows/` - Create and start a workflow
- `GET /api/workflows/{id}` - Get workflow status and results
- `GET /api/manuscripts/{id}/json` - Get manuscript as JSON
- `GET /api/manuscripts/{id}/pdf` - Export manuscript as PDF
- `GET /api/manuscripts/{id}/docx` - Export manuscript as DOCX

---

## Deployment

### Production Deployment

Arakis includes complete production deployment infrastructure:

```bash
# 1. Provision Ubuntu 22.04 server
# 2. Point domain to server IP
# 3. SSH to server

# 4. Download and run automated setup script
wget https://raw.githubusercontent.com/yourusername/arakis/main/deploy/setup_vm.sh
sudo bash setup_vm.sh arakis.example.com admin@example.com

# 5. Configure environment
sudo nano /opt/arakis/.env
# Add OPENAI_API_KEY and other credentials

# 6. Start services
sudo systemctl start arakis

# 7. Initialize database
cd /opt/arakis
docker compose exec api alembic upgrade head

# 8. Verify deployment
curl https://arakis.example.com/health
open https://arakis.example.com/docs
```

**The setup script automatically configures:**
- ✅ Docker and Docker Compose
- ✅ Nginx reverse proxy with SSL/TLS (Let's Encrypt)
- ✅ UFW firewall (ports 22, 80, 443)
- ✅ Systemd service for auto-start
- ✅ Automated daily backups
- ✅ Health monitoring
- ✅ System optimizations

**See**: [`deploy/README.md`](deploy/README.md) for detailed deployment guide.

### CI/CD Pipeline

Arakis includes a complete CI/CD pipeline with GitHub Actions:

**Continuous Integration** (`.github/workflows/ci.yml`):
- ✅ Automated testing on every PR
- ✅ Code linting (ruff) and type checking (mypy)
- ✅ Security scanning (bandit, safety)
- ✅ Integration tests with Docker Compose
- ✅ Coverage reporting

**Docker Builds** (`.github/workflows/docker-build.yml`):
- ✅ Multi-architecture builds (amd64, arm64)
- ✅ Push to GitHub Container Registry
- ✅ Vulnerability scanning (Trivy, Grype)
- ✅ SBOM generation

**Continuous Deployment** (`.github/workflows/cd.yml`):
- ✅ Automated deployment on merge to main
- ✅ Pre-deployment backup
- ✅ Zero-downtime rolling updates
- ✅ Comprehensive health checks
- ✅ **Automatic rollback on failure**
- ✅ Deployment notifications

**Setup Steps:**
1. Configure GitHub Secrets (`DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_DOMAIN`)
2. Update workflow files with your repository name
3. Push to GitHub
4. CI/CD runs automatically

**See**: [`CICD_GUIDE.md`](CICD_GUIDE.md) for complete CI/CD setup guide.

---

## Documentation

### Core Documentation
- **[CICD_GUIDE.md](CICD_GUIDE.md)** - Complete CI/CD setup and usage guide
- **[deploy/README.md](deploy/README.md)** - Production deployment guide
- **[scripts/README.md](scripts/README.md)** - Automation scripts documentation
- **[CLAUDE.md](CLAUDE.md)** - Project architecture and development guide

### Phase Completion Documents
- **[PHASE_1_COMPLETE.md](PHASE_1_COMPLETE.md)** - Database Layer
- **[PHASE_2_COMPLETE.md](PHASE_2_COMPLETE.md)** - REST API
- **[PHASE_3_COMPLETE.md](PHASE_3_COMPLETE.md)** - Dockerization
- **[PHASE_4_COMPLETE.md](PHASE_4_COMPLETE.md)** - VM Deployment
- **[PHASE_5_COMPLETE.md](PHASE_5_COMPLETE.md)** - CI/CD Pipeline

### API Documentation
- **OpenAPI/Swagger**: http://localhost:8000/docs (when running)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI spec**: http://localhost:8000/openapi.json

---

## Development

### Project Structure

```
arakis/
├── src/arakis/
│   ├── api/                # FastAPI application
│   ├── agents/             # LLM agents
│   ├── analysis/           # Statistical analysis
│   ├── clients/            # Database clients
│   ├── database/           # PostgreSQL models & migrations
│   ├── models/             # Data models
│   ├── rag/                # Retrieval-Augmented Generation
│   ├── retrieval/          # PDF fetching
│   └── cli/                # CLI commands
├── tests/                  # Test suite
├── deploy/                 # Deployment scripts
├── scripts/                # Automation scripts
├── .github/workflows/      # CI/CD workflows
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Development orchestration
├── docker-compose.prod.yml # Production overrides
└── requirements.txt        # Python dependencies
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=arakis --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py -v

# Run integration tests
pytest tests/integration/ -v
```

### Code Quality

```bash
# Lint code
ruff check src/

# Auto-fix issues
ruff check src/ --fix

# Format code
ruff format src/

# Type checking
mypy src/
```

### Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run tests: `pytest tests/`
5. Lint code: `ruff check src/`
6. Commit: `git commit -m "Add my feature"`
7. Push: `git push origin feature/my-feature`
8. Create a pull request

**Guidelines:**
- Write tests for new features
- Follow existing code style
- Add docstrings to public functions
- Update documentation as needed
- Keep PRs focused and small

---

## Roadmap

### Current Status: v0.2.0 (Production Ready ✅)

**Core Features:**
- ✅ Complete systematic review pipeline
- ✅ Multi-database search with AI query generation
- ✅ Dual-review screening with conflict detection
- ✅ Triple-review data extraction
- ✅ Meta-analysis and statistical testing
- ✅ Automated manuscript writing with RAG
- ✅ REST API with FastAPI
- ✅ PostgreSQL database persistence
- ✅ Docker containerization
- ✅ Production VM deployment
- ✅ CI/CD pipeline with auto-rollback
- ✅ Comprehensive documentation

### Planned Features

**v0.3.0 - Web UI**
- [ ] React + Next.js web interface
- [ ] Interactive workflow builder
- [ ] Real-time progress tracking
- [ ] Manual review interface
- [ ] Collaborative features

**v0.4.0 - Advanced Analytics**
- [ ] Network meta-analysis
- [ ] Bayesian meta-analysis
- [ ] Trial sequential analysis
- [ ] Advanced subgroup analysis

**v0.5.0 - Quality Assessment**
- [ ] Automated risk of bias (RoB 2)
- [ ] GRADE quality assessment
- [ ] Study quality scoring

**v0.6.0 - Extended Sources**
- [ ] Cochrane Library
- [ ] CINAHL database
- [ ] ClinicalTrials.gov
- [ ] Web of Science

**v1.0.0 - Enterprise**
- [ ] Multi-user authentication
- [ ] Multi-tenancy
- [ ] Custom LLM support
- [ ] Advanced monitoring
- [ ] SLA guarantees

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

### Getting Help

- **Documentation**: See docs listed above
- **API Documentation**: http://localhost:8000/docs (when running)
- **GitHub Issues**: [Report bugs or request features](https://github.com/mustafa-boorenie/arakis/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/mustafa-boorenie/arakis/discussions)

### Common Issues

**OpenAI API Rate Limits:**
- Free tier: 3 requests/minute
- Paid tier: 500+ requests/minute
- Configure in `.env`: `OPENAI_REQUESTS_PER_MINUTE=3`

**Cost Estimation (100 papers):**
- Screening (dual-review): ~$2.00
- Extraction (single-pass, 20 papers): ~$4.00
- Writing (3 sections): ~$3.00
- **Total**: ~$9.00

**See troubleshooting sections in**:
- `CICD_GUIDE.md` for CI/CD issues
- `deploy/README.md` for deployment issues
- `CLAUDE.md` for development issues

---

## Citation

If you use Arakis in your research, please cite:

```bibtex
@software{arakis2026,
  title = {Arakis: AI-Powered Systematic Review Platform},
  author = {[Your Name]},
  year = {2026},
  url = {https://github.com/mustafa-boorenie/arakis},
  version = {0.2.0}
}
```

---

## Acknowledgments

Built with:
- [OpenAI GPT-4](https://openai.com/) - LLM for intelligent agents
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [PostgreSQL](https://www.postgresql.org/) - Relational database
- [Docker](https://www.docker.com/) - Containerization
- [GitHub Actions](https://github.com/features/actions) - CI/CD
- [Biopython](https://biopython.org/) - PubMed integration
- [Matplotlib](https://matplotlib.org/) - Visualization
- [SciPy](https://scipy.org/) - Statistical analysis

Special thanks to the open-source community and researchers advancing systematic review methodology.

---

## Project Status

**Status**: ✅ Production Ready

- **Version**: 0.2.0
- **Last Updated**: January 2026
- **Maintainers**: Active
- **CI/CD**: Automated
- **Documentation**: Comprehensive
- **Deployment**: One-command setup

---

<div align="center">

**[⬆ Back to Top](#arakis-ai-powered-systematic-review-platform)**

Made with ❤️ for researchers, by researchers

[Documentation](./CICD_GUIDE.md) • [API Docs](http://localhost:8000/docs) • [Report Bug](https://github.com/mustafa-boorenie/arakis/issues) • [Request Feature](https://github.com/mustafa-boorenie/arakis/issues)

</div>

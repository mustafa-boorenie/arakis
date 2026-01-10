# Arakis Documentation

Complete documentation index for the Arakis systematic review pipeline.

---

## Getting Started

### New Users Start Here

1. **[README.md](../README.md)** - Project overview and quick introduction
2. **[guides/QUICK_START.md](guides/QUICK_START.md)** - Get started in 5 minutes with step-by-step guide
3. **[guides/EXAMPLES.md](guides/EXAMPLES.md)** - Practical code examples for common tasks

### For Developers

1. **[api/API_REFERENCE.md](api/API_REFERENCE.md)** - Complete API documentation with all methods
2. **[../CLAUDE.md](../CLAUDE.md)** - Architecture, development commands, and codebase guide

---

## Documentation Structure

### 📖 Guides (`docs/guides/`)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [QUICK_START.md](guides/QUICK_START.md) | 5-minute tutorial | Want to start coding |
| [WORKFLOW_GUIDE.md](guides/WORKFLOW_GUIDE.md) | Complete workflow documentation | Planning a systematic review |
| [EXAMPLES.md](guides/EXAMPLES.md) | Practical examples | Need specific examples |
| [MANUSCRIPT_TEMPLATE.md](guides/MANUSCRIPT_TEMPLATE.md) | Manuscript structure guide | Writing up results |
| [PAPER_FULL_TEXT_EXTRACTION.md](guides/PAPER_FULL_TEXT_EXTRACTION.md) | Full-text retrieval guide | Need PDF access |
| [RATE_LIMIT_HANDLING.md](guides/RATE_LIMIT_HANDLING.md) | Rate limit handling | Troubleshoot API limits |

### 🚀 Deployment (`docs/deployment/`)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [CICD_GUIDE.md](deployment/CICD_GUIDE.md) | CI/CD pipeline setup | Setting up automation |
| [DATABASE_SETUP.md](deployment/DATABASE_SETUP.md) | Database configuration | Production deployment |
| [DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md) | Pre-deployment checklist | Before going live |

### 🔧 API Documentation (`docs/api/`)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [API_REFERENCE.md](api/API_REFERENCE.md) | Complete API docs | Need detailed API info |

### 💻 Development (`docs/development/`)

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [PHASE_1_COMPLETE.md](development/PHASE_1_COMPLETE.md) | Database layer details | Understanding database architecture |
| [PHASE_2_COMPLETE.md](development/PHASE_2_COMPLETE.md) | REST API implementation | Understanding API architecture |
| [PHASE_3_COMPLETE.md](development/PHASE_3_COMPLETE.md) | Dockerization details | Understanding containerization |
| [PHASE_4_COMPLETE.md](development/PHASE_4_COMPLETE.md) | VM deployment details | Understanding infrastructure |
| [PHASE_5_COMPLETE.md](development/PHASE_5_COMPLETE.md) | CI/CD pipeline details | Understanding automation |

### 📊 Root Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [../README.md](../README.md) | Project overview | First time here |
| [../CHANGELOG.md](../CHANGELOG.md) | Version history | Check what's new |
| [../CLAUDE.md](../CLAUDE.md) | Architecture & dev guide | Contributing to codebase |

---

## Quick Navigation

### By Task

**I want to...**

- **Search for papers** → [Quick Start: Search](guides/QUICK_START.md#1-search-for-papers) | [API: SearchOrchestrator](api/API_REFERENCE.md#searchorchestrator)
- **Screen papers** → [Quick Start: Screen](guides/QUICK_START.md#2-screen-papers-with-ai) | [API: ScreeningAgent](api/API_REFERENCE.md#screeningagent)
- **Extract data** → [Quick Start: Extract](guides/QUICK_START.md#3-extract-data) | [API: DataExtractionAgent](api/API_REFERENCE.md#dataextractionagent)
- **Analyze data** → [Quick Start: Analysis](guides/QUICK_START.md#4-statistical-analysis) | [API: StatisticalEngine](api/API_REFERENCE.md#statisticalengine)
- **Generate diagrams** → [Quick Start: PRISMA](guides/QUICK_START.md#5-generate-prisma-diagram) | [API: PRISMADiagramGenerator](api/API_REFERENCE.md#prismadiagramgenerator)
- **Write manuscript** → [Quick Start: Writing](guides/QUICK_START.md#6-write-manuscript-sections) | [API: Writing Agents](api/API_REFERENCE.md#writing)
- **Deploy to production** → [Deployment: CI/CD Guide](deployment/CICD_GUIDE.md) | [Deployment: Checklist](deployment/DEPLOYMENT_CHECKLIST.md)
- **See complete example** → [Quick Start: Complete Example](guides/QUICK_START.md#complete-example) | [Examples: Complete Workflow](guides/EXAMPLES.md#complete-workflow)

### By Component

| Component | Quick Start | API Docs | Examples |
|-----------|-------------|----------|----------|
| Search | [Link](guides/QUICK_START.md#1-search-for-papers) | [Link](api/API_REFERENCE.md#search) | [Link](guides/EXAMPLES.md#basic-search) |
| Screening | [Link](guides/QUICK_START.md#2-screen-papers-with-ai) | [Link](api/API_REFERENCE.md#screening) | [Link](guides/EXAMPLES.md#paper-screening) |
| Extraction | [Link](guides/QUICK_START.md#3-extract-data) | [Link](api/API_REFERENCE.md#extraction) | [Link](guides/EXAMPLES.md#data-extraction) |
| Analysis | [Link](guides/QUICK_START.md#4-statistical-analysis) | [Link](api/API_REFERENCE.md#analysis) | [Link](guides/EXAMPLES.md#meta-analysis) |
| Visualization | [Link](guides/QUICK_START.md#5-generate-prisma-diagram) | [Link](api/API_REFERENCE.md#visualization) | [Examples: PRISMA](guides/EXAMPLES.md#basic-search) |
| Writing | [Link](guides/QUICK_START.md#6-write-manuscript-sections) | [Link](api/API_REFERENCE.md#writing) | [Examples: Writing](guides/EXAMPLES.md#complete-workflow) |

---

## API Quick Reference

### Essential Methods

```python
# Search
orchestrator = SearchOrchestrator()
result = await orchestrator.search_single_database(query, database, max_results)
result = await orchestrator.comprehensive_search(research_question, databases)

# Screening
screener = ScreeningAgent()
decision = await screener.screen_paper(paper, criteria, dual_review=True)
decisions = await screener.screen_batch(papers, criteria, dual_review=True)

# Extraction
extractor = DataExtractionAgent()
extraction = await extractor.extract_paper(paper, schema, triple_review=True)
result = await extractor.extract_batch(papers, schema, triple_review=True)

# Analysis (synchronous)
engine = StatisticalEngine()
result = engine.independent_t_test(group1, group2)

meta_engine = MetaAnalysisEngine()
result = meta_engine.random_effects_meta_analysis(studies, effect_measure)

# Visualization (synchronous)
generator = PRISMADiagramGenerator()
diagram = generator.generate(flow, output_filename)

viz = VisualizationGenerator()
figure = viz.create_forest_plot(meta_result, output_path)

# Writing
intro_writer = IntroductionWriterAgent()
intro = await intro_writer.write_complete_introduction(research_question)

results_writer = ResultsWriterAgent()
results = await results_writer.write_study_selection(prisma_flow, total_papers)

discussion_writer = DiscussionWriterAgent()
discussion = await discussion_writer.write_complete_discussion(analysis_result, outcome)
```

---

## Common Questions

### Installation & Setup

**Q: How do I install Arakis?**
→ See [README: Installation](../README.md#installation)

**Q: What API keys do I need?**
→ See [README: Configuration](../README.md#configuration)

### Usage

**Q: How do I search for papers?**
→ See [Quick Start: Search](guides/QUICK_START.md#1-search-for-papers)

**Q: What's the difference between dual-review and single-pass screening?**
→ See [Quick Start: Screening Modes](guides/QUICK_START.md#2-screen-papers-with-ai)

**Q: How does quality control work in extraction?**
→ See [API Reference: Data Extraction](api/API_REFERENCE.md#dataextractionagent)

**Q: How much does it cost to run a systematic review?**
→ See [README: Cost Estimation](../README.md#cost-estimation)

### Deployment

**Q: How do I deploy to production?**
→ See [CI/CD Guide](deployment/CICD_GUIDE.md) and [Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md)

**Q: How do I set up the database?**
→ See [Database Setup](deployment/DATABASE_SETUP.md)

### Development

**Q: How do I run tests?**
→ See [CLAUDE.md: Testing](../CLAUDE.md#testing)

**Q: What's the architecture?**
→ See [CLAUDE.md: Architecture](../CLAUDE.md#architecture)

**Q: How do I add a new database?**
→ See [CLAUDE.md: Common Modifications](../CLAUDE.md#common-modifications)

---

## Project Structure

```
arakis/
├── README.md                 # Project overview
├── CHANGELOG.md             # Version history
├── CLAUDE.md                # Development guide
├── docs/
│   ├── DOCUMENTATION_INDEX.md    # This file
│   ├── guides/                   # User guides
│   │   ├── QUICK_START.md
│   │   ├── WORKFLOW_GUIDE.md
│   │   ├── EXAMPLES.md
│   │   └── ...
│   ├── deployment/               # Deployment docs
│   │   ├── CICD_GUIDE.md
│   │   ├── DATABASE_SETUP.md
│   │   └── DEPLOYMENT_CHECKLIST.md
│   ├── api/                      # API documentation
│   │   └── API_REFERENCE.md
│   └── development/              # Development phase docs
│       ├── PHASE_1_COMPLETE.md
│       ├── PHASE_2_COMPLETE.md
│       └── ...
├── examples/                # Demo scripts
│   ├── demo_systematic_review.py
│   └── demo_human_review.py
├── src/arakis/             # Source code
├── tests/                  # Test suite
├── deploy/                 # Deployment scripts
└── scripts/                # Automation scripts
```

---

## Support

- **Documentation Issues**: Check this index first, then search docs
- **API Questions**: See [API Reference](api/API_REFERENCE.md)
- **Usage Examples**: See [Examples Guide](guides/EXAMPLES.md)
- **Deployment Help**: See [CI/CD Guide](deployment/CICD_GUIDE.md)
- **Bug Reports**: [GitHub Issues](https://github.com/mustafa-boorenie/arakis/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/mustafa-boorenie/arakis/issues)

---

**Last Updated:** 2026-01-09
**Documentation Version:** 2.0
**Project Version:** 0.2.0

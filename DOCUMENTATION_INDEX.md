# Arakis Documentation

Complete documentation index for the Arakis systematic review pipeline.

---

## Getting Started

### New Users Start Here

1. **[README.md](README.md)** - Project overview and quick introduction
2. **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes with step-by-step guide
3. **[EXAMPLES.md](EXAMPLES.md)** - Practical code examples for common tasks

### For Developers

1. **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation with all methods
2. **[CLAUDE.md](CLAUDE.md)** - Architecture, development commands, and codebase guide

---

## Documentation Structure

### User Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [README.md](README.md) | Project overview | First time here |
| [QUICK_START.md](QUICK_START.md) | 5-minute tutorial | Want to start coding |
| [EXAMPLES.md](EXAMPLES.md) | Practical examples | Need specific examples |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API docs | Need detailed info |

### Developer Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [CLAUDE.md](CLAUDE.md) | Architecture & dev guide | Contributing to codebase |
| [TEST_COMPLETION_SUMMARY.md](TEST_COMPLETION_SUMMARY.md) | Test results & status | Check test coverage |
| [EXTRACTION_TESTS_FIXED.md](EXTRACTION_TESTS_FIXED.md) | Extraction fixes | Understand quality control |
| [FULL_PIPELINE_TEST_RESULTS.md](FULL_PIPELINE_TEST_RESULTS.md) | Pipeline test results | Verify end-to-end functionality |

### Feature Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| [DUAL_REVIEW_UPDATE.md](DUAL_REVIEW_UPDATE.md) | Dual-review screening | Understand screening modes |
| [HUMAN_REVIEW_FEATURE.md](HUMAN_REVIEW_FEATURE.md) | Human-in-the-loop | Setup human verification |
| [RATE_LIMIT_HANDLING.md](RATE_LIMIT_HANDLING.md) | Rate limit handling | Troubleshoot API limits |

---

## Quick Navigation

### By Task

**I want to...**

- **Search for papers** → [Quick Start: Search](QUICK_START.md#1-search-for-papers) | [API: SearchOrchestrator](API_REFERENCE.md#searchorchestrator)
- **Screen papers** → [Quick Start: Screen](QUICK_START.md#2-screen-papers-with-ai) | [API: ScreeningAgent](API_REFERENCE.md#screeningagent)
- **Extract data** → [Quick Start: Extract](QUICK_START.md#3-extract-data) | [API: DataExtractionAgent](API_REFERENCE.md#dataextractionagent)
- **Analyze data** → [Quick Start: Analysis](QUICK_START.md#4-statistical-analysis) | [API: StatisticalEngine](API_REFERENCE.md#statisticalengine)
- **Generate diagrams** → [Quick Start: PRISMA](QUICK_START.md#5-generate-prisma-diagram) | [API: PRISMADiagramGenerator](API_REFERENCE.md#prismadiagramgenerator)
- **Write manuscript** → [Quick Start: Writing](QUICK_START.md#6-write-manuscript-sections) | [API: Writing Agents](API_REFERENCE.md#writing)
- **See complete example** → [Quick Start: Complete Example](QUICK_START.md#complete-example) | [Examples: Complete Workflow](EXAMPLES.md#complete-workflow)

### By Component

| Component | Quick Start | API Docs | Examples |
|-----------|-------------|----------|----------|
| Search | [Link](QUICK_START.md#1-search-for-papers) | [Link](API_REFERENCE.md#search) | [Link](EXAMPLES.md#basic-search) |
| Screening | [Link](QUICK_START.md#2-screen-papers-with-ai) | [Link](API_REFERENCE.md#screening) | [Link](EXAMPLES.md#paper-screening) |
| Extraction | [Link](QUICK_START.md#3-extract-data) | [Link](API_REFERENCE.md#extraction) | [Link](EXAMPLES.md#data-extraction) |
| Analysis | [Link](QUICK_START.md#4-statistical-analysis) | [Link](API_REFERENCE.md#analysis) | [Link](EXAMPLES.md#meta-analysis) |
| Visualization | [Link](QUICK_START.md#5-generate-prisma-diagram) | [Link](API_REFERENCE.md#visualization) | [Examples: PRISMA](EXAMPLES.md#basic-search) |
| Writing | [Link](QUICK_START.md#6-write-manuscript-sections) | [Link](API_REFERENCE.md#writing) | [Examples: Writing](EXAMPLES.md#complete-workflow) |

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
→ See [README: Installation](README.md#installation)

**Q: What API keys do I need?**
→ See [README: Configuration](README.md#configuration)

### Usage

**Q: How do I search for papers?**
→ See [Quick Start: Search](QUICK_START.md#1-search-for-papers)

**Q: What's the difference between dual-review and single-pass screening?**
→ See [DUAL_REVIEW_UPDATE.md](DUAL_REVIEW_UPDATE.md)

**Q: How does quality control work in extraction?**
→ See [EXTRACTION_TESTS_FIXED.md](EXTRACTION_TESTS_FIXED.md)

**Q: How much does it cost to run a systematic review?**
→ See [README: Cost Estimation](README.md#cost-estimation) | [API: Cost Reference](API_REFERENCE.md#cost-reference)

### Development

**Q: How do I run tests?**
→ See [CLAUDE.md: Testing](CLAUDE.md#testing)

**Q: What's the architecture?**
→ See [CLAUDE.md: Architecture](CLAUDE.md#architecture)

**Q: How do I add a new database?**
→ See [CLAUDE.md: Common Modifications](CLAUDE.md#common-modifications)

---

## API Changes & Corrections

The following API naming corrections were made (documented for reference):

| Old (Incorrect) | New (Correct) | Notes |
|-----------------|---------------|-------|
| `screen_papers()` | `screen_batch()` | ScreeningAgent batch method |
| `extract_data()` | `extract_paper()` | DataExtractionAgent single paper |
| `extract_single()` | `extract_paper()` | Same as above |
| `independent_samples_ttest()` | `independent_t_test()` | StatisticalEngine method |
| `generate_diagram()` | `generate()` | PRISMADiagramGenerator method |
| `PRISMAFlow(records_identified=...)` | `PRISMAFlow(records_identified_total=...)` | Parameter name |
| `literature_papers=` | `literature_context=` | IntroductionWriterAgent parameter |

All documentation now uses the correct API names.

---

## Test Coverage

All tests passing: **46/46 (100%)**

See [TEST_COMPLETION_SUMMARY.md](TEST_COMPLETION_SUMMARY.md) for detailed test results.

---

## Contributing

Before contributing, read:
1. [CLAUDE.md](CLAUDE.md) - Understand the architecture
2. [TEST_COMPLETION_SUMMARY.md](TEST_COMPLETION_SUMMARY.md) - See test requirements
3. CONTRIBUTING.md (if available) - Contribution guidelines

---

## Support

- **Documentation Issues**: Check this index first, then search docs
- **API Questions**: See [API_REFERENCE.md](API_REFERENCE.md)
- **Usage Examples**: See [EXAMPLES.md](EXAMPLES.md)
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Issues

---

**Last Updated:** 2026-01-09
**Documentation Version:** 1.0
**Test Coverage:** 100% (46/46 tests passing)

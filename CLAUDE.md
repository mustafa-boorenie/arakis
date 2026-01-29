# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arakis is an AI-powered systematic review pipeline for academic research that automates literature searches across multiple databases using LLM agents with tool functions.

**Core capabilities:**
- Multi-database search with AI-optimized queries (PubMed, OpenAlex, Semantic Scholar, Google Scholar, Embase)
- LLM-powered query generation using GPT with MeSH terms and database-specific syntax
- Multi-strategy deduplication (DOI, PMID, fuzzy title matching)
- AI-based paper screening with dual-review support
- Waterfall paper retrieval from open access sources (Unpaywall, PMC, arXiv)
- PRISMA flow tracking for systematic review reporting

## Development Commands

### Installation
```bash
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=arakis

# Run single test file
pytest tests/test_specific.py

# Run single test function
pytest tests/test_specific.py::test_function_name
```

### Linting and Type Checking
```bash
# Lint code
ruff check src/

# Format code
ruff format src/

# Type checking
mypy src/
```

### Running the CLI

#### Streamlined Workflow (Recommended)
```bash
# Run complete systematic review pipeline end-to-end
arakis workflow \
  --question "Effect of aspirin on sepsis mortality" \
  --include "Adult patients,Sepsis,Aspirin intervention,Mortality" \
  --exclude "Pediatric,Animal studies" \
  --databases pubmed \
  --max-results 20 \
  --output ./my_review

# Fast mode (single-pass screening and extraction)
arakis workflow \
  --question "Research question" \
  --include "Criteria" \
  --exclude "Exclusions" \
  --output ./review \
  --fast

# Schema is auto-detected from research question and inclusion criteria
# This will auto-detect "cohort" from the inclusion criteria
arakis workflow \
  --question "Effect of metformin on mortality in type 2 diabetes" \
  --include "Type 2 diabetes,Metformin,Mortality,Cohort studies" \
  --exclude "Animal studies,Reviews" \
  --output ./cohort_review

# Explicitly specify schema (overrides auto-detection)
arakis workflow \
  --question "Effect of aspirin on heart disease" \
  --include "RCTs,Placebo-controlled" \
  --schema rct \
  --output ./rct_review

# Available extraction schemas: auto (default), rct, cohort, case_control, diagnostic

# Skip certain stages
arakis workflow --question "..." --include "..." --skip-analysis --skip-writing
```

#### Individual Commands
```bash
# Search databases
arakis search "Research question here"

# With specific databases
arakis search "Question" --databases pubmed,openalex

# Enable query validation (checks result counts, may use more API calls)
arakis search "Question" --validate

# Screen papers (dual-review mode by default)
arakis screen results.json --include "Human RCTs" --exclude "Animal studies"

# Disable dual-review for faster screening (less reliable)
arakis screen results.json --include "Human RCTs" --no-dual-review

# Human-in-the-loop review (single-pass + human verification)
arakis screen results.json --include "Human RCTs" --no-dual-review --human-review

# Fetch full texts
arakis fetch results.json --output ./papers/

# Extract structured data from papers (schema auto-detected from paper content)
arakis extract screening_results.json --output extractions.json

# Fast extraction (single-pass, lower cost)
arakis extract screening_results.json --mode fast --output extractions.json

# Explicitly specify schema (overrides auto-detection)
arakis extract screening_results.json --schema cohort --output extractions.json

# Available extraction schemas: auto (default), rct, cohort, case_control, diagnostic

# Analyze extracted data (with meta-analysis if feasible)
arakis analyze extractions.json --output analysis.json --figures ./figures/

# Specify analysis method
arakis analyze extractions.json --method random_effects --output analysis.json

# Generate PRISMA 2020 flow diagram
arakis prisma-diagram search_results.json --output prisma.png
# Or from screening results
arakis prisma-diagram screening_results.json --output prisma.png

# Write results section for manuscript
arakis write-results --search search_results.json --screening screening_results.json --output results.md
# Include meta-analysis results
arakis write-results --search search.json --screening screening.json --analysis analysis.json --output results.md

# Write introduction section (uses OpenAI web search by default for literature)
arakis write-intro "Effect of antihypertensive therapy on blood pressure" --output intro.md
# Disable web search (use provided literature or RAG instead)
arakis write-intro "Research question" --no-web-search --literature papers.json --output intro.md
# With RAG for automatic literature retrieval (when web search disabled)
arakis write-intro "Research question" --no-web-search --literature papers.json --use-rag --output intro.md
# Don't save separate references file
arakis write-intro "Research question" --no-references --output intro.md

# Write discussion section
arakis write-discussion analysis.json --outcome "mortality" --output discussion.md
# With literature for comparison
arakis write-discussion analysis.json --literature papers.json --use-rag --output discussion.md
# With user interpretation notes
arakis write-discussion analysis.json --interpretation "The effect is clinically significant" --implications "This suggests..." --output discussion.md

# Show version
arakis version
```

## Architecture

### Core Components

**1. SearchOrchestrator** (`orchestrator.py`)
- Central coordinator for multi-database searches
- Orchestrates: query generation → parallel database searches → deduplication → PRISMA tracking
- Returns `ComprehensiveSearchResult` with unique papers and metadata

**2. QueryGeneratorAgent** (`agents/query_generator.py`)
- LLM-powered agent using OpenAI GPT with tool functions
- Generates database-specific queries with controlled vocabulary (MeSH, Emtree)
- PICO extraction from research questions
- Query validation and refinement based on result counts
- Tool functions: `generate_pubmed_query`, `generate_openalex_query`, `generate_semantic_scholar_query`, `generate_google_scholar_query`, `extract_pico`

**3. Deduplicator** (`deduplication.py`)
- Multi-strategy deduplication with priority order:
  1. Exact DOI matching
  2. Exact PMID matching
  3. Title fuzzy matching (>90% similarity using rapidfuzz)
  4. Author + Year + Title prefix matching
- Merges metadata from duplicates into canonical papers
- Tracks duplicate groups for transparency

**4. ScreeningAgent** (`agents/screener.py`)
- LLM-powered paper screening using GPT with tool functions
- Three decision states: INCLUDE, EXCLUDE, MAYBE
- **Default: Dual-review mode** - runs two passes with different temperatures (0.3 and 0.7), flags conflicts
- Automatic conflict detection and conservative resolution (defaults to MAYBE on disagreement)
- Single-review mode available via `dual_review=False` for faster processing
- **Human-in-the-loop review** - when `dual_review=False`, set `human_review=True` to prompt human verification of AI decisions
- Returns `ScreeningDecision` with confidence scores, matched criteria, and human review tracking

**5. PaperFetcher** (`retrieval/fetcher.py`)
- Waterfall retrieval pattern: tries sources in priority order until success
- Default order: Unpaywall → PMC → arXiv
- Updates `Paper.pdf_url` and `Paper.open_access` on success

**6. DataExtractionAgent** (`agents/extractor.py`)
- LLM-powered structured data extraction from papers
- **Triple-review mode** (default): 3 passes with temps (0.2, 0.5, 0.8), majority voting for conflicts
- **Single-pass mode**: Fast extraction (use `--mode fast`)
- Confidence scoring based on reviewer agreement (3/3 = 1.0, 2/3 = 0.67)
- Pre-built schemas: RCT, cohort, case-control, diagnostic studies
- Field validation against schema constraints
- Automatic quality assessment and flagging for human review
- Cost: ~$0.50-0.70 per paper (triple-review), ~$0.15-0.20 (single-pass)

**7. AnalysisRecommenderAgent** (`analysis/recommender.py`)
- LLM-powered statistical test recommendation
- Analyzes extracted data characteristics to recommend appropriate tests
- Considers: data type, study design, sample size, distribution
- Recommends primary, secondary, and sensitivity analyses
- Assesses meta-analysis feasibility
- Tool function: `recommend_statistical_tests`
- Cost: ~$0.20 per analysis (single-pass)

**8. StatisticalEngine** (`analysis/engine.py`)
- Pure Python statistical computations (NO LLM COST)
- Parametric tests: t-test, paired t-test, one-way ANOVA
- Non-parametric tests: Mann-Whitney U, Wilcoxon signed-rank, Kruskal-Wallis
- Categorical tests: chi-square, Fisher's exact test
- Effect sizes: Cohen's d, odds ratio, risk ratio, mean difference
- Correlation: Pearson, Spearman
- All tests return `AnalysisResult` with statistics, p-values, confidence intervals

**9. MetaAnalysisEngine** (`analysis/meta_analysis.py`)
- Random-effects meta-analysis (DerSimonian-Laird method)
- Fixed-effects meta-analysis (inverse variance weighting)
- Heterogeneity assessment: I², tau², Q-statistic
- Effect measures: mean difference, SMD (Hedges' g), odds ratio, risk ratio, risk difference
- Publication bias: Egger's test
- Subgroup analysis and leave-one-out sensitivity analysis
- All calculations use scipy/statsmodels (NO LLM COST)

**10. VisualizationGenerator** (`analysis/visualizer.py`)
- Publication-ready plots using matplotlib/seaborn (NO LLM COST)
- **Forest plots**: Pooled effects with CI, study weights, diamond for pooled estimate
- **Funnel plots**: Publication bias detection with pseudo-CI limits
- **Box plots**: Distribution comparisons with individual data points
- **Bar charts**: Categorical comparisons with error bars
- **Scatter plots**: With optional regression lines and R²
- 300 DPI output suitable for journal submission

**11. PRISMADiagramGenerator** (`visualization/prisma.py`)
- PRISMA 2020-compliant flow diagrams (NO LLM COST)
- Automatically generates from search/screening results
- Tracks: identification, screening, eligibility, inclusion stages
- Color-coded boxes (blue for main flow, red for exclusions)
- Outputs: PNG (300 DPI) or SVG format
- Professional formatting suitable for publication

**12. ResultsWriterAgent** (`agents/results_writer.py`)
- LLM-powered results section writer using reasoning models (o3-mini default, gpt-5.2 for quality mode)
- Generates three subsections:
  - **Study Selection**: Search results and PRISMA narrative
  - **Study Characteristics**: Summary of included studies
  - **Synthesis of Results**: Meta-analysis findings with statistics
- References figures and tables appropriately
- Follows PRISMA 2020 guidelines
- Tool functions: `write_study_selection`, `write_study_characteristics`, `write_synthesis_of_results`
- Cost: ~$0.50-2.00 per complete results section (o3-mini default)

**13. Embedder** (`rag/embedder.py`)
- Generates text embeddings using OpenAI's text-embedding-3-small model
- Creates chunks from papers: title and abstract
- Batch processing: 100 texts per API call for efficiency
- Automatic caching to avoid re-embedding same text
- Token counting with tiktoken for cost estimation
- Cost: ~$0.00002 per 1K tokens (~$0.001 per paper)

**14. VectorStore** (`rag/vector_store.py`)
- FAISS-based vector similarity search (NO LLM COST)
- Supports exact search (L2 distance) and approximate search (IVF index)
- Persistent storage: save/load to disk
- Maps vectors to TextChunk metadata
- Efficient search: finds top-k similar vectors in milliseconds

**15. Retriever** (`rag/retriever.py`)
- High-level interface for literature context retrieval
- Combines embedder and vector store
- Features:
  - Index papers for retrieval
  - Semantic similarity search with configurable top-k
  - Diversity filtering to ensure variety in results
  - Minimum score thresholding
  - Filter by chunk type (title, abstract, etc.)
- Save/load functionality for persistent indices
- Cost: Embedding ~$0.20 for 200 papers (one-time, cached), retrieval is free

**16. EmbeddingCacheStore** (`rag/cache.py`)
- SQLite-based persistent cache for embeddings (NO LLM COST)
- Prevents re-embedding same text across sessions
- Hash-based validation: invalidates cache if text changes
- Stores: embeddings, metadata, token counts, creation timestamps
- Provides statistics: cache size, hit rate, total tokens embedded

**17. OpenAILiteratureClient** (`clients/openai_literature.py`)
- Literature research client using OpenAI Responses API with web search
- Uses reasoning models for high-quality research (o3-mini default)
- **Purpose**: Fetches background literature SEPARATE from systematic review search
- Key methods:
  - `research_topic(topic)` → AI-generated summary with citations
  - `search_for_papers(query, max_results)` → list of Paper objects
  - `get_literature_context(question, max_papers)` → (summary, papers) tuple
- Converts search results to `Paper` objects for ReferenceManager
- Rate limiting: 1 request/second
- Cost: ~$0.05-0.20 per research query (o3-mini default)

**18. ReferenceManager** (`references/manager.py`)
- Central coordinator for citation management in manuscripts
- Collects papers, validates citations, generates reference lists
- Key methods:
  - `register_paper(paper)` → stores paper by best_identifier
  - `validate_citations(section)` → checks all citations have registered papers
  - `generate_reference_list(section)` → formatted APA 7 citations
  - `extract_citations_from_section(section)` → paper IDs from text
- Integrates with `CitationExtractor` for parsing `[Paper ID]` patterns
- Integrates with `CitationFormatter` for APA 7 formatting

**19. CitationFormatter** (`references/formatter.py`)
- Formats citations in various styles (default: APA 7)
- Supported styles: APA_7, APA_6, VANCOUVER, CHICAGO, HARVARD
- APA 7 features:
  - Authors: `Last, F. M., Last, F. M., & Last, F. M.`
  - 21+ authors: First 19, `...`, last author
  - Title in sentence case, journal italicized
  - DOI as `https://doi.org/...`
- Methods: `format_citation(paper)`, `format_in_text(paper)`

**20. CitationExtractor** (`references/extractor.py`)
- Regex-based extraction of `[Paper ID]` citations from text
- Validates IDs (filters out `[Figure 1]`, `[Table 2]`, `[1]`, etc.)
- Supports: DOI, PMID, Semantic Scholar, OpenAlex, OpenAI IDs
- Methods:
  - `extract_citations(text)` → list of ExtractedCitation with positions
  - `extract_unique_paper_ids(text)` → unique IDs in order of appearance
  - `replace_citations_with_numbers(text, order)` → `[1]`, `[2]` format

**21. IntroductionWriterAgent** (`agents/intro_writer.py`)
- LLM-powered introduction section writer using reasoning models
- Generates three subsections:
  - **Background**: Broad context → specific problem (200-250 words)
  - **Rationale**: Gaps in literature, justification for review (100-150 words)
  - **Objectives**: Clear, specific aims (80-120 words)
- **OpenAI Web Search Integration** (default): Uses Responses API with web search
  - Literature is separate from systematic review search results
  - Papers automatically registered with ReferenceManager
  - Citations validated against provided papers only
- Fallback chain: OpenAI Web Search → RAG → provided literature
- Returns `tuple[Section, list[Paper]]` with cited papers for reference section
- Tool functions: `write_background`, `write_rationale`, `write_objectives`
- Cost: ~$0.50-2.00 per complete introduction (o3-mini default)

**22. DiscussionWriterAgent** (`agents/discussion_writer.py`)
- LLM-powered discussion section writer using reasoning models
- Generates four subsections:
  - **Summary of Main Findings**: Interpret results (150-200 words)
  - **Comparison with Existing Literature**: Compare with previous work (250-300 words)
  - **Limitations**: Acknowledge study limitations (150-200 words)
  - **Implications**: Clinical and research implications (150-200 words)
- Uses RAG system for literature comparison (optional)
- Accepts user input for interpretation and opinions
- Tool functions: `write_key_findings`, `write_comparison_to_literature`, `write_limitations`, `write_implications`
- Cost: ~$0.50-1.50 per complete discussion (o3-mini default)

**23. MethodsWriterAgent** (`agents/methods_writer.py`)
- LLM-powered methods section writer using reasoning models
- Generates systematic review methods subsections:
  - **Protocol and Registration**: Review protocol details
  - **Eligibility Criteria**: PICO components with inclusion/exclusion
  - **Information Sources**: Databases searched with dates
  - **Search Strategy**: Query construction methodology
  - **Selection Process**: Screening and selection workflow
  - **Data Collection Process**: Extraction methodology
  - **Data Items**: Variables and outcomes extracted
  - **Risk of Bias Assessment**: Bias assessment tools used
  - **Synthesis Methods**: Statistical analysis approach
- Follows PRISMA 2020 checklist requirements
- Tool functions: `write_protocol`, `write_eligibility`, `write_information_sources`, etc.
- Cost: ~$0.50-1.50 per complete methods section (o3-mini default)

**24. AbstractWriterAgent** (`agents/abstract_writer.py`)
- LLM-powered abstract writer using reasoning models
- Extracts key components from complete manuscript
- Supports two formats:
  - **Structured (IMRAD)**: Background/Objective, Methods, Results, Conclusions
  - **Unstructured**: Single flowing paragraph
- Features:
  - Extracts objectives, methods, results, conclusions using tool functions
  - Includes specific statistics (effect sizes, CIs, p-values, I²)
  - Targets 250-300 words
- Tool functions: `extract_objective`, `extract_methods`, `extract_results`, `extract_conclusions`
- Cost: ~$0.20-0.50 per abstract (o3-mini default)

**25. Model Configuration** (`agents/models.py`)
- Shared model constants for all agents with cost mode support
- Available models:
  - `REASONING_MODEL = "o3-mini"`: Default reasoning model for complex tasks
  - `REASONING_MODEL_PRO = "gpt-5.2-2025-12-11"`: High-quality reasoning with max effort
  - `FAST_MODEL = "gpt-5-nano"`: Fast model for simpler tasks
  - `SCREENING_MODEL = "gpt-5-nano"`: Default screening model (overridden by cost mode)
  - `EXTRACTION_MODEL = "gpt-5-nano"`: Default extraction model (overridden by cost mode)
  - `QUALITY_SCREENING_MODEL = "gpt-5-mini"`: Quality mode screening
  - `QUALITY_EXTRACTION_MODEL = "gpt-5-mini"`: Quality mode extraction
  - `QUALITY_WRITING_MODEL = "gpt-5.2-2025-12-11"`: Quality mode writing
- Model pricing dict for cost estimation
- Helper functions: `get_model_pricing()`, `estimate_cost()`
- Cost modes (in progress): QUALITY, BALANCED, FAST, ECONOMY

**26. Retry Logic with Exponential Backoff** (`utils.py`)
- `@retry_with_exponential_backoff` decorator for OpenAI API calls
- Handles rate limits (429) and transient errors (5xx) automatically
- Exponential backoff with jitter prevents overwhelming the API
- Default: 5 retries, 1s initial delay, up to 60s max delay
- Used by QueryGeneratorAgent and ScreeningAgent
- See `RATE_LIMIT_HANDLING.md` for details

### Client Architecture

**BaseSearchClient** (`clients/base.py`)
- Abstract base for all database clients
- Key methods: `search()`, `get_paper_by_id()`, `validate_query()`, `normalize_paper()`
- Raises: `SearchClientError`, `RateLimitError`, `NotConfiguredError`

**Implementations:**
- `PubMedClient`: Uses Biopython E-utilities, respects NCBI rate limits (3/s default, 10/s with API key)
- `OpenAlexClient`: Supports text search and filter syntax
- `SemanticScholarClient`: Simple text search
- `GoogleScholarClient`: Uses scholarly library (requires careful rate limiting)

### Data Models

**Paper** (`models/paper.py`)
- Central data model with normalized fields across all databases
- Identifiers: `doi`, `pmid`, `pmcid`, `arxiv_id`, `s2_id`, `openalex_id`
- Metadata: `title`, `abstract`, `authors`, `journal`, `year`, `keywords`, `mesh_terms`
- Source tracking: `source`, `source_url`, `retrieved_at`
- Access: `pdf_url`, `open_access`
- Property: `best_identifier` returns first available ID for deduplication

**SearchResult** (`models/paper.py`)
- Container for single database search results
- Includes: `query`, `source`, `papers`, `total_available`, `execution_time_ms`

**PRISMAFlow** (`models/paper.py`)
- Tracks systematic review statistics
- Stages: identification, screening, eligibility, inclusion
- Per-database tracking of records identified

**ScreeningDecision** (`models/screening.py`)
- Contains: `paper_id`, `status`, `reason`, `confidence`, `matched_inclusion/exclusion`
- Supports dual-review with `is_conflict` and `second_opinion` fields

**ExtractionSchema** (`models/extraction.py`)
- Defines fields to extract from papers
- Field types: NUMERIC, CATEGORICAL, TEXT, DATE, BOOLEAN, LIST
- Validation rules: min/max, allowed values, length constraints
- Pre-built schemas available: RCT, cohort, case-control, diagnostic

**ExtractedData** (`models/extraction.py`)
- Contains extracted data for one paper
- Fields: `paper_id`, `data` dict, `confidence` scores per field
- Quality metrics: `extraction_quality`, `needs_human_review`
- Audit trail: `reviewer_decisions`, `conflicts`, `low_confidence_fields`

**AnalysisResult** (`models/analysis.py`)
- Result from a statistical test
- Contains: `test_statistic`, `p_value`, `confidence_interval`, `effect_size`
- Property: `is_significant` (p < 0.05)
- Additional statistics stored in `additional_stats` dict

**MetaAnalysisResult** (`models/analysis.py`)
- Result from meta-analysis
- Pooled effect with CI, heterogeneity statistics (I², tau², Q)
- Individual study data with weights
- Paths to forest plot and funnel plot
- Properties: `is_significant`, `has_high_heterogeneity` (I² > 50%)

**PRISMAFlow** (`models/visualization.py`)
- Complete PRISMA 2020 flow tracking
- Stages: identification (databases + registers), screening, eligibility, inclusion
- Tracks: records identified, duplicates removed, records screened/excluded, reports assessed, studies included
- Properties: `records_after_deduplication`, `exclusion_rate`, `retrieval_rate`

**Figure** (`models/visualization.py`)
- Manuscript figure metadata
- Contains: `id`, `title`, `caption`, `file_path`, `figure_type`
- Dimensions and DPI settings for publication

**Table** (`models/visualization.py`)
- Manuscript table with headers and rows
- Methods: `markdown` and `html` for different export formats
- Support for footnotes

**Section** (`models/writing.py`)
- Manuscript section with title and content
- Hierarchical structure with subsections
- Tracks citations, figures, and tables referenced
- Methods: `to_markdown()`, `add_subsection()`, `add_citation()`
- Property: `total_word_count` (includes subsections)

**Manuscript** (`models/writing.py`)
- Complete manuscript structure
- Sections: abstract, introduction, methods, results, discussion, conclusions
- Collections: figures, tables, references
- Metadata: authors, affiliations, keywords, funding

**TextChunk** (`models/rag.py`)
- A chunk of text from a paper for embedding
- Contains: `paper_id`, `chunk_type`, `text`, `metadata`
- Property: `chunk_id` (unique identifier combining paper_id and chunk_type)

**Embedding** (`models/rag.py`)
- Vector embedding of a text chunk
- Contains: `chunk_id`, `vector` (list of floats), `model`, `dimensions`, `created_at`
- Used by VectorStore for similarity search

**RetrievalQuery** (`models/rag.py`)
- Query parameters for document retrieval
- Fields: `query_text`, `top_k`, `min_score`, `chunk_types`, `exclude_paper_ids`, `diversity_weight`

**RetrievalResult** (`models/rag.py`)
- A single retrieved document with relevance score
- Contains: `chunk`, `score`, `rank`

**RetrievalResponse** (`models/rag.py`)
- Response from a retrieval query
- Contains: `query`, `results`, `total_candidates`, `search_time_ms`, `model_used`
- Properties: `paper_ids`, `avg_score`

**EmbeddingStats** (`models/rag.py`)
- Statistics about the embedding cache
- Contains: total chunks/embeddings, cache size, models used, oldest/newest embeddings, total tokens
- Property: `cache_hit_rate`

### Configuration

**Settings** (`config.py`)
- Uses pydantic-settings with `.env` file support
- Required: `OPENAI_API_KEY`, `UNPAYWALL_EMAIL`
- Optional: `NCBI_API_KEY`, `ELSEVIER_API_KEY`, `SERPAPI_KEY`
- Writing uses o3-mini reasoning model by default (gpt-5.2 for quality mode)
- Rate limits: `pubmed_requests_per_second`, `scholarly_min_delay`, `scholarly_max_delay`
- Access via: `get_settings()` (cached singleton)

### Frontend Architecture

**Stack:**
- Next.js 16 with Turbopack
- TypeScript with strict mode
- Zustand for state management with localStorage persistence
- Shadcn/ui components with Tailwind CSS

**Key Files:**
- `frontend-next/src/store/index.ts` - Global Zustand store with auth, workflow, layout state
- `frontend-next/src/lib/api/client.ts` - API client with automatic token refresh
- `frontend-next/src/hooks/useAuth.ts` - Authentication hook for OAuth flow
- `frontend-next/src/hooks/useWorkflow.ts` - Workflow management with polling

**State Management:**
- Workflow history persisted to localStorage via Zustand persist middleware
- Auth tokens stored in localStorage (`arakis_access_token`, `arakis_refresh_token`)
- Workflow polling uses `updateWorkflow()` to sync both `current` and `history` state

### Authentication Architecture

**OAuth Flow (Google/Apple):**
1. Frontend calls `/api/auth/{provider}/login` to get authorization URL
2. User redirected to OAuth provider
3. Provider redirects back to `/api/auth/{provider}/callback` with code
4. Backend exchanges code for tokens and creates/updates user
5. Backend redirects to `/auth/success` with JWT tokens in URL fragment
6. Frontend extracts tokens, stores in localStorage, fetches user profile

**JWT Tokens:**
- `create_access_token()` - Short-lived (default 15 min), contains user_id and email
- `create_refresh_token()` - Long-lived (default 30 days), stored hashed in DB
- `create_oauth_state()` - 5-minute JWT for OAuth CSRF protection (stateless, survives server restarts)

**Key Files:**
- `src/arakis/auth/jwt.py` - JWT creation and validation utilities
- `src/arakis/api/routers/auth.py` - OAuth endpoints for Google/Apple
- `src/arakis/auth/service.py` - User management and token operations
- `src/arakis/auth/providers/` - OAuth provider implementations

**Token Refresh:**
- API client automatically attempts refresh on 401 responses
- If refresh fails, throws `SessionExpiredError` for graceful logout
- Frontend catches `SessionExpiredError` and logs out silently

**OAuth State (CSRF Protection):**
- Uses signed JWT tokens instead of in-memory storage
- State contains: expiration, nonce, redirect_url
- Survives server restarts (unlike in-memory dict)
- 5-minute expiration prevents replay attacks

## Key Patterns

### LLM Agent Pattern
Both `QueryGeneratorAgent` and `ScreeningAgent` use OpenAI function calling:
1. Define tool schemas with type definitions
2. System prompt provides context and guidelines
3. Call `client.chat.completions.create()` with `tools` parameter
4. Parse `tool_calls` from response to extract structured data
5. Fallback to default behavior if parsing fails

### Waterfall Retrieval Pattern
`PaperFetcher` implements priority-ordered source checking:
1. Iterate through sources in priority order
2. Check `can_retrieve()` before attempting
3. Return on first success
4. Track all sources tried for debugging

### Async-First Design
All I/O operations are async:
- Database clients use `httpx.AsyncClient`
- OpenAI client uses `AsyncOpenAI`
- CLI wraps async calls with `asyncio.run_until_complete()`

### Normalization Strategy
Each client implements `normalize_paper()` to convert raw API responses to the canonical `Paper` model. This enables:
- Uniform deduplication across sources
- Consistent screening regardless of origin
- Simplified downstream processing

### OpenAI Web Search Integration Pattern
Introduction writing uses OpenAI Responses API with web search for background literature (separate from review search):
1. `OpenAILiteratureClient.get_literature_context(question)` fetches papers using web search
2. Papers registered with `ReferenceManager.register_paper(paper)`
3. Reasoning model generates text with `[paper_id]` citations
4. `CitationExtractor` validates citations against registered papers
5. LLM is restricted to citing ONLY provided papers (no training data citations)
6. `CitationFormatter` generates APA 7 reference list

**Key Design Decision**: Introduction references come from OpenAI web search, NOT from the systematic review search results. This ensures proper separation between background context and reviewed papers.

### Model Tiers and Cost Modes
The system supports multiple model tiers for different use cases:

**Reasoning Models:**
- `o3-mini`: Default reasoning model ($1.10/$4.40 per 1M tokens)
- `gpt-5.2-2025-12-11`: Pro reasoning with max effort ($10/$30 per 1M tokens)
- `o1`: Extended thinking model ($15/$60 per 1M tokens)

**Fast Models:**
- `gpt-5-nano`: Ultra-fast, lowest cost ($0.10/$0.40 per 1M tokens)
- `gpt-5-mini`: Balanced speed/quality ($0.50/$2.00 per 1M tokens)
- `gpt-4o`: Legacy fast model ($2.50/$10 per 1M tokens)

**Cost Modes (in progress):**
| Mode | Screening | Extraction | Writing | Est. Cost/Review |
|------|-----------|------------|---------|------------------|
| QUALITY | gpt-5-mini (dual) | gpt-5-mini (triple) | gpt-5.2 | ~$15 |
| BALANCED | gpt-5-nano (single) | gpt-5-nano (single) | o3-mini | ~$4 |
| FAST | gpt-5-nano (single) | gpt-5-nano (single) | o3-mini | ~$1.50 |
| ECONOMY | gpt-5-nano (single) | gpt-5-nano (single) | gpt-5-nano | ~$0.80 |

**Note:** PRISMA diagram generation is always programmatic (no LLM cost) in all modes.

### Retry Pattern with Exponential Backoff
OpenAI API calls use `@retry_with_exponential_backoff` decorator:
1. Wrap API call method with decorator
2. On rate limit (429) or server error (5xx), automatically retry
3. Exponential backoff: 1s → 2s → 4s → 8s → 16s (with jitter)
4. User-friendly progress messages during retries
5. Give up after max retries (default: 5) and raise error
6. Client errors (4xx) don't retry - fail immediately

**Usage:**
```python
@retry_with_exponential_backoff(max_retries=5, initial_delay=1.0)
async def _call_openai(self, messages, tools=None):
    return await self.client.chat.completions.create(...)
```

## Testing Considerations

When adding tests:
- Use `pytest-asyncio` for async test functions (mark with `@pytest.mark.asyncio`)
- Mock OpenAI API calls to avoid costs and flakiness
- Mock HTTP clients using `httpx` testing utilities
- Test deduplication with known duplicate sets
- Verify PRISMA flow calculations

## Common Modifications

**Adding a new database:**
1. Create client in `clients/` extending `BaseSearchClient`
2. Implement: `search()`, `get_paper_by_id()`, `get_query_syntax_help()`, `normalize_paper()`
3. Add to `SearchOrchestrator._clients` dict
4. Add tool function to `query_generator.py` QUERY_TOOLS
5. Update system prompt in `QueryGeneratorAgent._get_system_prompt()`

**Adding a new retrieval source:**
1. Create source in `retrieval/sources/` extending `BaseRetrievalSource`
2. Implement: `can_retrieve()`, `retrieve()`
3. Add to `PaperFetcher` default sources list

**Modifying deduplication:**
- Edit `Deduplicator._find_match()` to add new matching strategies
- Adjust `title_similarity_threshold` in `Deduplicator.__init__()`
- Update `_merge_papers()` to handle new metadata fields

## Current Development State

### Cost Optimization (In Progress)

**Completed:**
- ✅ PRISMA diagram generation is 100% programmatic (no LLM cost)
- ✅ Database schema updated with `cost_mode` column
- ✅ Migration created: `2026_01_29_1531_add_cost_mode_to_workflows.py`
- ✅ Model constants defined in `agents/models.py`

**In Progress:**
- ⏳ Cost mode configuration system (`src/arakis/config/cost_modes.py`)
- ⏳ Agent integration to read from cost mode config
- ⏳ Orchestrator integration to pass cost mode to agents
- ⏳ Frontend settings UI for cost mode selection

**Cost Mode Design:**
- Workflows store `cost_mode` (QUALITY, BALANCED, FAST, ECONOMY)
- Each mode maps to specific models, review passes, and features
- PRISMA is always programmatic regardless of mode

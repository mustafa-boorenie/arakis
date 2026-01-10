# Arakis API Reference

Complete API reference for the Arakis systematic review pipeline.

---

## Table of Contents

1. [Search](#search)
2. [Screening](#screening)
3. [Extraction](#extraction)
4. [Analysis](#analysis)
5. [Visualization](#visualization)
6. [Writing](#writing)
7. [Models](#models)

---

## Search

### SearchOrchestrator

Coordinates literature searches across multiple databases.

```python
from arakis.orchestrator import SearchOrchestrator
```

#### Methods

##### `search_single_database(query, database, max_results=100)`

Search a single database with a direct query.

**Parameters:**
- `query` (str): Database-specific search query
- `database` (str): Database name: `"pubmed"`, `"openalex"`, `"semantic_scholar"`, or `"google_scholar"`
- `max_results` (int): Maximum papers to retrieve (default: 100)

**Returns:** `SearchResult`

**Example:**
```python
orchestrator = SearchOrchestrator()

result = await orchestrator.search_single_database(
    query="aspirin[tiab] AND sepsis[tiab]",
    database="pubmed",
    max_results=50
)

print(f"Found {len(result.papers)} papers")
```

##### `comprehensive_search(research_question, databases=None, max_results_per_db=100, validate_queries=False)`

Run a complete search with AI-generated queries across multiple databases.

**Parameters:**
- `research_question` (str): Plain English research question
- `databases` (list[str], optional): List of databases to search. Default: `["pubmed", "openalex", "semantic_scholar"]`
- `max_results_per_db` (int): Maximum papers per database (default: 100)
- `validate_queries` (bool): Check result counts and refine queries (default: False, uses more API calls)

**Returns:** `ComprehensiveSearchResult`

**Example:**
```python
result = await orchestrator.comprehensive_search(
    research_question="Effect of aspirin on mortality in patients with sepsis",
    databases=["pubmed", "openalex"],
    max_results_per_db=100
)

print(f"Total papers: {len(result.unique_papers)}")
print(f"Duplicates removed: {result.prisma_flow.records_removed_duplicates}")
```

---

## Screening

### ScreeningAgent

AI-powered paper screening with dual-review support.

```python
from arakis.agents.screener import ScreeningAgent
from arakis.models.screening import ScreeningCriteria
```

#### Methods

##### `screen_paper(paper, criteria, dual_review=True, human_review=False)`

Screen a single paper against inclusion/exclusion criteria.

**Parameters:**
- `paper` (Paper): Paper to screen
- `criteria` (ScreeningCriteria): Inclusion and exclusion criteria
- `dual_review` (bool): Use two-pass review with conflict detection (default: True)
- `human_review` (bool): Prompt for human verification (default: False)

**Returns:** `ScreeningDecision`

**Example:**
```python
agent = ScreeningAgent()

criteria = ScreeningCriteria(
    inclusion=[
        "Human adult patients (≥18 years)",
        "Randomized controlled trials",
        "Clinical outcomes reported"
    ],
    exclusion=[
        "Animal studies",
        "Pediatric patients",
        "Review articles"
    ]
)

decision = await agent.screen_paper(
    paper=paper,
    criteria=criteria,
    dual_review=True  # Default: enables conflict detection
)

print(f"Status: {decision.status.value}")  # INCLUDE, EXCLUDE, or MAYBE
print(f"Confidence: {decision.confidence}")
print(f"Reason: {decision.reason}")
```

##### `screen_batch(papers, criteria, dual_review=True, human_review=False, progress_callback=None)`

Screen multiple papers in batch.

**Parameters:**
- `papers` (list[Paper]): Papers to screen
- `criteria` (ScreeningCriteria): Inclusion and exclusion criteria
- `dual_review` (bool): Use two-pass review (default: True)
- `human_review` (bool): Prompt for human verification (default: False)
- `progress_callback` (callable, optional): Function called with progress updates

**Returns:** `list[ScreeningDecision]`

**Example:**
```python
decisions = await agent.screen_batch(
    papers=papers,
    criteria=criteria,
    dual_review=True
)

included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
print(f"Included: {len(included)} papers")
```

---

## Extraction

### DataExtractionAgent

Extract structured data from papers using AI.

```python
from arakis.agents.extractor import DataExtractionAgent
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType
```

#### Methods

##### `extract_paper(paper, schema, triple_review=True, use_full_text=False)`

Extract data from a single paper.

**Parameters:**
- `paper` (Paper): Paper to extract from
- `schema` (ExtractionSchema): Fields to extract
- `triple_review` (bool): Use three-pass extraction with majority voting (default: True)
- `use_full_text` (bool): Use full text if available (default: False)

**Returns:** `ExtractedData`

**Example:**
```python
agent = DataExtractionAgent()

# Define extraction schema
schema = ExtractionSchema(
    name="RCT Schema",
    description="Extract RCT data",
    fields=[
        ExtractionField(
            name="sample_size",
            description="Total number of participants",
            field_type=FieldType.NUMERIC,
            required=True,
            validation_rules={"min": 1, "max": 100000}
        ),
        ExtractionField(
            name="primary_outcome",
            description="Primary outcome measured",
            field_type=FieldType.TEXT,
            required=True
        )
    ]
)

# Extract with triple-review (default)
extraction = await agent.extract_paper(
    paper=paper,
    schema=schema,
    triple_review=True
)

print(f"Sample size: {extraction.data['sample_size']}")
print(f"Quality: {extraction.extraction_quality}")
print(f"Needs review: {extraction.needs_human_review}")
```

##### `extract_batch(papers, schema, triple_review=True, progress_callback=None)`

Extract from multiple papers in batch.

**Parameters:**
- `papers` (list[Paper]): Papers to extract from
- `schema` (ExtractionSchema): Fields to extract
- `triple_review` (bool): Use three-pass extraction (default: True)
- `progress_callback` (callable, optional): Progress callback function

**Returns:** `ExtractionResult`

**Example:**
```python
result = await agent.extract_batch(
    papers=papers,
    schema=schema,
    triple_review=False  # Single-pass for speed
)

print(f"Success rate: {result.success_rate:.1%}")
print(f"Papers needing review: {result.papers_needing_review}")
```

---

## Analysis

### StatisticalEngine

Perform statistical tests (no LLM cost).

```python
from arakis.analysis.engine import StatisticalEngine
```

#### Methods

##### `independent_t_test(group1, group2, paired=False)`

Independent samples t-test.

**Parameters:**
- `group1` (list[float]): First group data
- `group2` (list[float]): Second group data
- `paired` (bool): Use paired test (default: False)

**Returns:** `AnalysisResult`

**Example:**
```python
engine = StatisticalEngine()

result = engine.independent_t_test(
    group1=[12.5, 13.2, 11.8, 14.1],
    group2=[15.3, 16.1, 14.8, 15.9]
)

print(f"p-value: {result.p_value:.4f}")
print(f"Significant: {result.is_significant}")  # p < 0.05
print(f"Effect size: {result.effect_size}")
```

##### `chi_square_test(observed, expected=None)`

Chi-square test for categorical data.

**Parameters:**
- `observed` (list[int] or list[list[int]]): Observed frequencies
- `expected` (list[int], optional): Expected frequencies

**Returns:** `AnalysisResult`

##### `mann_whitney_u_test(group1, group2)`

Non-parametric alternative to t-test.

**Parameters:**
- `group1` (list[float]): First group data
- `group2` (list[float]): Second group data

**Returns:** `AnalysisResult`

### MetaAnalysisEngine

Perform meta-analysis (no LLM cost).

```python
from arakis.analysis.meta_analysis import MetaAnalysisEngine, EffectMeasure, AnalysisMethod
```

#### Methods

##### `random_effects_meta_analysis(studies, effect_measure=EffectMeasure.MEAN_DIFFERENCE)`

Random-effects meta-analysis.

**Parameters:**
- `studies` (list[dict]): Study data with effect sizes and sample sizes
- `effect_measure` (EffectMeasure): Type of effect to pool

**Returns:** `MetaAnalysisResult`

**Example:**
```python
engine = MetaAnalysisEngine()

studies = [
    {"study_id": "study1", "effect": -15, "se": 5, "n": 60},
    {"study_id": "study2", "effect": -12, "se": 4, "n": 80},
    {"study_id": "study3", "effect": -18, "se": 6, "n": 50}
]

result = engine.random_effects_meta_analysis(
    studies=studies,
    effect_measure=EffectMeasure.MEAN_DIFFERENCE
)

print(f"Pooled effect: {result.pooled_effect} {result.pooled_ci}")
print(f"I²: {result.i_squared:.1f}%")
print(f"p-value: {result.p_value:.4f}")
```

---

## Visualization

### PRISMADiagramGenerator

Generate PRISMA 2020 flow diagrams (no LLM cost).

```python
from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow
```

#### Methods

##### `generate(flow, output_filename="prisma_diagram.png")`

Generate PRISMA diagram.

**Parameters:**
- `flow` (PRISMAFlow): Flow data
- `output_filename` (str): Output file path

**Returns:** `PRISMADiagram`

**Example:**
```python
generator = PRISMADiagramGenerator()

flow = PRISMAFlow(
    records_identified_total=1000,
    records_identified_databases={"pubmed": 500, "openalex": 500},
    records_removed_duplicates=200,
    records_screened=800,
    records_excluded=700,
    studies_included=100
)

diagram = generator.generate(flow, "prisma.png")
print(f"Saved to: {diagram.png_path}")
```

### VisualizationGenerator

Generate publication-quality plots (no LLM cost).

```python
from arakis.analysis.visualizer import VisualizationGenerator
```

#### Methods

##### `create_forest_plot(meta_result, output_path)`

Create forest plot from meta-analysis results.

**Parameters:**
- `meta_result` (MetaAnalysisResult): Meta-analysis results
- `output_path` (str): Output file path

**Returns:** `Figure`

##### `create_funnel_plot(meta_result, output_path)`

Create funnel plot for publication bias assessment.

---

## Writing

### IntroductionWriterAgent

Generate introduction sections.

```python
from arakis.agents.intro_writer import IntroductionWriterAgent
```

#### Methods

##### `write_complete_introduction(research_question, inclusion_criteria=None, primary_outcome=None, literature_context=None, retriever=None)`

Write complete introduction with all subsections.

**Parameters:**
- `research_question` (str): Research question
- `inclusion_criteria` (list[str], optional): Inclusion criteria
- `primary_outcome` (str, optional): Primary outcome
- `literature_context` (list[Paper], optional): Related papers for context
- `retriever` (Retriever, optional): RAG retriever for literature search

**Returns:** `Section`

**Example:**
```python
writer = IntroductionWriterAgent()

introduction = await writer.write_complete_introduction(
    research_question="Effect of aspirin on mortality in sepsis patients",
    inclusion_criteria=["Human adults", "Sepsis diagnosis", "RCTs"],
    primary_outcome="30-day mortality"
)

print(introduction.to_markdown())
print(f"Word count: {introduction.total_word_count}")
```

### ResultsWriterAgent

Generate results sections.

```python
from arakis.agents.results_writer import ResultsWriterAgent
```

#### Methods

##### `write_study_selection(prisma_flow, total_papers_searched, screening_summary=None)`

Write study selection subsection.

**Parameters:**
- `prisma_flow` (PRISMAFlow): PRISMA flow data
- `total_papers_searched` (int): Total papers from search
- `screening_summary` (dict, optional): Screening statistics

**Returns:** `WritingResult`

**Example:**
```python
writer = ResultsWriterAgent()

result = await writer.write_study_selection(
    prisma_flow=flow,
    total_papers_searched=1000,
    screening_summary={
        "screened": 800,
        "included": 100,
        "excluded": 700
    }
)

print(result.section.content)
```

### DiscussionWriterAgent

Generate discussion sections.

```python
from arakis.agents.discussion_writer import DiscussionWriterAgent
```

#### Methods

##### `write_complete_discussion(analysis_result, outcome, interpretation=None, limitations=None, literature_context=None, retriever=None)`

Write complete discussion with all subsections.

**Parameters:**
- `analysis_result` (MetaAnalysisResult or AnalysisResult): Analysis results
- `outcome` (str): Primary outcome name
- `interpretation` (str, optional): User's interpretation
- `limitations` (list[str], optional): Study limitations
- `literature_context` (list[Paper], optional): Related papers
- `retriever` (Retriever, optional): RAG retriever

**Returns:** `Section`

---

## Models

### Paper

Represents a research paper.

**Fields:**
- `id` (str): Unique identifier
- `title` (str): Paper title
- `abstract` (str): Abstract text
- `authors` (list[Author]): Authors
- `year` (int): Publication year
- `doi` (str, optional): DOI
- `pmid` (str, optional): PubMed ID
- `journal` (str, optional): Journal name
- `source` (PaperSource): Origin database

### ScreeningCriteria

Inclusion and exclusion criteria.

**Fields:**
- `inclusion` (list[str]): Inclusion criteria
- `exclusion` (list[str]): Exclusion criteria

### ScreeningDecision

Result of paper screening.

**Fields:**
- `paper_id` (str): Paper ID
- `status` (ScreeningStatus): INCLUDE, EXCLUDE, or MAYBE
- `reason` (str): Explanation
- `confidence` (float): Confidence score (0-1)
- `matched_inclusion` (list[str]): Matched inclusion criteria
- `matched_exclusion` (list[str]): Matched exclusion criteria
- `is_conflict` (bool): True if dual-review conflict detected

### ExtractionSchema

Defines fields to extract.

**Fields:**
- `name` (str): Schema name
- `description` (str): Schema description
- `fields` (list[ExtractionField]): Fields to extract

### ExtractionField

A single field to extract.

**Fields:**
- `name` (str): Field name
- `description` (str): Field description
- `field_type` (FieldType): NUMERIC, CATEGORICAL, TEXT, DATE, BOOLEAN, or LIST
- `required` (bool): Is required field
- `validation_rules` (dict): Validation constraints

**Example:**
```python
field = ExtractionField(
    name="sample_size",
    description="Total number of participants",
    field_type=FieldType.NUMERIC,
    required=True,
    validation_rules={"min": 1, "max": 100000}
)

is_valid, error = field.validate(120)  # (True, None)
is_valid, error = field.validate(-5)   # (False, "below minimum 1")
```

### ExtractedData

Data extracted from a paper.

**Fields:**
- `paper_id` (str): Paper ID
- `data` (dict): Extracted field values
- `confidence` (dict): Confidence per field
- `extraction_quality` (float): Overall quality (0-1)
- `needs_human_review` (bool): Auto-set if quality issues detected
- `low_confidence_fields` (list[str]): Auto-populated fields with confidence < 0.8
- `conflicts` (list[str]): Fields with reviewer disagreement

**Note:** `needs_human_review` and `low_confidence_fields` are automatically set based on quality metrics.

### PRISMAFlow

PRISMA 2020 flow tracking.

**Fields:**
- `records_identified_total` (int): Total records found
- `records_identified_databases` (dict[str, int]): Per-database counts
- `records_removed_duplicates` (int): Duplicates removed
- `records_screened` (int): Records screened
- `records_excluded` (int): Records excluded
- `studies_included` (int): Final included studies

---

## Cost Reference

| Component | LLM Cost | Notes |
|-----------|----------|-------|
| Search | FREE | No LLM calls |
| Query generation | ~$0.01-0.05 | Per query set |
| Screening (single) | ~$0.02 | Per paper, dual-review |
| Screening (batch) | ~$0.02 × N | Per paper |
| Extraction (single-pass) | ~$0.20 | Per paper |
| Extraction (triple-review) | ~$0.50-0.70 | Per paper |
| Statistical tests | FREE | Pure Python |
| Meta-analysis | FREE | Pure Python |
| Visualization | FREE | Matplotlib |
| Writing (intro) | ~$1.00 | Per section |
| Writing (results) | ~$0.30 | Per subsection |
| Writing (discussion) | ~$1.00 | Per section |

**Cost-saving tips:**
- Use `triple_review=False` for faster, cheaper extraction
- Disable `validate_queries` unless needed
- Statistical analysis and visualization are free

---

## Error Handling

All async methods may raise:
- `SearchClientError`: Database search errors
- `RateLimitError`: API rate limit exceeded (auto-retry with backoff)
- `NotConfiguredError`: Missing API keys or configuration

**Example:**
```python
from arakis.clients.base import RateLimitError

try:
    result = await orchestrator.search_single_database(...)
except RateLimitError as e:
    print(f"Rate limited: {e}")
    # Automatic retry with exponential backoff
except SearchClientError as e:
    print(f"Search failed: {e}")
```

---

## Rate Limits

- **PubMed**: 3 requests/second (10/s with API key)
- **OpenAI**: 10,000 RPM (tier 1)
- **Unpaywall**: Polite rate limiting (1/s recommended)

Rate limiting is handled automatically with exponential backoff.

# Arakis Examples

Practical examples for common systematic review tasks.

---

## Table of Contents

1. [Basic Search](#basic-search)
2. [Multi-Database Search](#multi-database-search)
3. [Paper Screening](#paper-screening)
4. [Data Extraction](#data-extraction)
5. [Meta-Analysis](#meta-analysis)
6. [Complete Workflow](#complete-workflow)
7. [Advanced Usage](#advanced-usage)

---

## Basic Search

### Search PubMed with a Simple Query

```python
import asyncio
from arakis.orchestrator import SearchOrchestrator

async def simple_search():
    orchestrator = SearchOrchestrator()

    result = await orchestrator.search_single_database(
        query="aspirin[tiab] AND sepsis[tiab]",
        database="pubmed",
        max_results=50
    )

    print(f"Found {len(result.papers)} papers in {result.execution_time_ms}ms")

    # Display results
    for paper in result.papers[:5]:
        print(f"\nTitle: {paper.title}")
        print(f"Year: {paper.year}")
        print(f"PMID: {paper.pmid}")
        print(f"Abstract: {paper.abstract[:200]}...")

asyncio.run(simple_search())
```

### Search with AI-Generated Query

```python
async def ai_search():
    orchestrator = SearchOrchestrator()

    # Let AI generate the PubMed query
    result = await orchestrator.comprehensive_search(
        research_question="Effect of aspirin on mortality in patients with sepsis",
        databases=["pubmed"],
        max_results_per_db=100
    )

    print(f"AI-generated query: {result.queries['pubmed']}")
    print(f"Found {len(result.unique_papers)} papers")

asyncio.run(ai_search())
```

---

## Multi-Database Search

### Search Across Multiple Databases

```python
async def multi_database_search():
    orchestrator = SearchOrchestrator()

    result = await orchestrator.comprehensive_search(
        research_question="Machine learning for predicting sepsis outcomes",
        databases=["pubmed", "openalex", "semantic_scholar"],
        max_results_per_db=100
    )

    # Check results
    print(f"Total papers found: {result.prisma_flow.records_identified_total}")
    print(f"After deduplication: {len(result.unique_papers)}")
    print(f"Duplicates removed: {result.prisma_flow.records_removed_duplicates}")

    # Per-database breakdown
    print("\nPer-database results:")
    for db, count in result.prisma_flow.records_identified_databases.items():
        print(f"  {db}: {count} papers")

asyncio.run(multi_database_search())
```

### Save Search Results

```python
import json
from arakis.models.paper import Paper

async def search_and_save():
    orchestrator = SearchOrchestrator()

    result = await orchestrator.search_single_database(
        query="diabetes[tiab] AND diet[tiab]",
        database="pubmed",
        max_results=100
    )

    # Save to JSON
    with open("search_results.json", "w") as f:
        json.dump(
            {
                "query": "diabetes[tiab] AND diet[tiab]",
                "database": "pubmed",
                "total": len(result.papers),
                "papers": [p.dict() for p in result.papers]
            },
            f,
            indent=2,
            default=str
        )

    print(f"Saved {len(result.papers)} papers to search_results.json")

# Load results later
def load_results():
    with open("search_results.json", "r") as f:
        data = json.load(f)
        papers = [Paper(**p) for p in data["papers"]]
        print(f"Loaded {len(papers)} papers")
        return papers

asyncio.run(search_and_save())
```

---

## Paper Screening

### Basic Screening

```python
from arakis.agents.screener import ScreeningAgent
from arakis.models.screening import ScreeningCriteria, ScreeningStatus

async def screen_papers(papers):
    agent = ScreeningAgent()

    criteria = ScreeningCriteria(
        inclusion=[
            "Human adult patients (≥18 years)",
            "Randomized controlled trials",
            "Mortality or clinical outcomes reported"
        ],
        exclusion=[
            "Pediatric patients (<18 years)",
            "Animal or in vitro studies",
            "Review articles or meta-analyses"
        ]
    )

    # Screen with dual-review (default)
    decisions = await agent.screen_batch(papers, criteria)

    # Analyze results
    included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
    excluded = [d for d in decisions if d.status == ScreeningStatus.EXCLUDE]
    maybe = [d for d in decisions if d.status == ScreeningStatus.MAYBE]
    conflicts = [d for d in decisions if d.is_conflict]

    print(f"Screening results:")
    print(f"  Included: {len(included)}")
    print(f"  Excluded: {len(excluded)}")
    print(f"  Maybe: {len(maybe)}")
    print(f"  Conflicts detected: {len(conflicts)}")

    # Save decisions
    with open("screening_decisions.json", "w") as f:
        json.dump([d.dict() for d in decisions], f, indent=2, default=str)

    return included

# asyncio.run(screen_papers(papers))
```

### Fast Single-Pass Screening

```python
async def fast_screening(papers):
    agent = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=["Human adults", "RCTs"],
        exclusion=["Animals", "Reviews"]
    )

    # Single-pass screening (faster, cheaper)
    decisions = await agent.screen_batch(
        papers=papers,
        criteria=criteria,
        dual_review=False  # Disable dual-review
    )

    print(f"Screened {len(decisions)} papers (single-pass)")
    return decisions
```

### Human-in-the-Loop Screening

```python
async def human_review_screening(papers):
    agent = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=["Human adults", "RCTs"],
        exclusion=["Animals"]
    )

    # AI screens first, then prompts human for verification
    decisions = await agent.screen_batch(
        papers=papers,
        criteria=criteria,
        dual_review=False,
        human_review=True  # Enable human verification
    )

    return decisions
```

### Progress Tracking

```python
async def screening_with_progress(papers):
    agent = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=["Human adults", "RCTs"],
        exclusion=["Animals"]
    )

    def progress_callback(current, total, status):
        percent = (current / total) * 100
        print(f"Progress: {current}/{total} ({percent:.1f}%) - {status}")

    decisions = await agent.screen_batch(
        papers=papers,
        criteria=criteria,
        progress_callback=progress_callback
    )

    return decisions
```

---

## Data Extraction

### Extract RCT Data

```python
from arakis.agents.extractor import DataExtractionAgent
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType

async def extract_rct_data(papers):
    agent = DataExtractionAgent()

    # Define RCT extraction schema
    schema = ExtractionSchema(
        name="RCT Standard Schema",
        description="Extract standard RCT data",
        fields=[
            ExtractionField(
                name="study_design",
                description="Type of study design",
                field_type=FieldType.CATEGORICAL,
                required=True,
                validation_rules={"allowed_values": ["RCT", "quasi-RCT", "cluster-RCT"]}
            ),
            ExtractionField(
                name="sample_size",
                description="Total number of participants",
                field_type=FieldType.NUMERIC,
                required=True,
                validation_rules={"min": 1, "max": 100000}
            ),
            ExtractionField(
                name="intervention_group_n",
                description="Number in intervention group",
                field_type=FieldType.NUMERIC,
                required=False,
                validation_rules={"min": 1}
            ),
            ExtractionField(
                name="control_group_n",
                description="Number in control group",
                field_type=FieldType.NUMERIC,
                required=False,
                validation_rules={"min": 1}
            ),
            ExtractionField(
                name="intervention_description",
                description="Description of the intervention",
                field_type=FieldType.TEXT,
                required=True
            ),
            ExtractionField(
                name="control_description",
                description="Description of the control",
                field_type=FieldType.TEXT,
                required=True
            ),
            ExtractionField(
                name="primary_outcome",
                description="Primary outcome measured",
                field_type=FieldType.TEXT,
                required=True
            ),
            ExtractionField(
                name="follow_up_duration",
                description="Follow-up duration in days",
                field_type=FieldType.NUMERIC,
                required=False,
                validation_rules={"min": 0}
            )
        ],
        study_types=["RCT"]
    )

    # Extract with triple-review (high quality)
    result = await agent.extract_batch(
        papers=papers,
        schema=schema,
        triple_review=True
    )

    print(f"Extraction results:")
    print(f"  Total papers: {result.total_papers}")
    print(f"  Success rate: {result.success_rate:.1%}")
    print(f"  Avg quality: {result.average_quality:.2f}")
    print(f"  Papers needing review: {result.papers_needing_review}")

    # Save extractions
    with open("extractions.json", "w") as f:
        json.dump(
            {
                "schema": schema.dict(),
                "extractions": [e.dict() for e in result.extractions]
            },
            f,
            indent=2,
            default=str
        )

    return result

# asyncio.run(extract_rct_data(papers))
```

### Fast Single-Pass Extraction

```python
async def fast_extraction(papers):
    agent = DataExtractionAgent()

    schema = ExtractionSchema(
        name="Quick Schema",
        description="Extract key fields only",
        fields=[
            ExtractionField(
                name="sample_size",
                description="Number of participants",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="outcome",
                description="Primary outcome",
                field_type=FieldType.TEXT,
                required=True
            )
        ]
    )

    # Single-pass extraction (faster, cheaper)
    result = await agent.extract_batch(
        papers=papers,
        schema=schema,
        triple_review=False  # Single pass
    )

    print(f"Extracted {len(result.extractions)} papers")
    print(f"Cost estimate: ${result.estimated_cost:.2f}")

    return result
```

### Handle Low-Quality Extractions

```python
async def handle_quality_issues(papers):
    agent = DataExtractionAgent()
    schema = create_schema()  # Your schema

    result = await agent.extract_batch(papers, schema, triple_review=True)

    # Get extractions needing human review
    needs_review = result.get_extractions_needing_review()

    print(f"Extractions needing review: {len(needs_review)}")
    for extraction in needs_review:
        print(f"\nPaper: {extraction.paper_id}")
        print(f"Quality: {extraction.extraction_quality}")
        print(f"Conflicts: {extraction.conflicts}")
        print(f"Low confidence fields: {extraction.low_confidence_fields}")

        # Manual review process here
        # ...

    # Get successful extractions
    successful = result.get_successful_extractions()
    print(f"\nSuccessful extractions: {len(successful)}")

    return successful
```

---

## Meta-Analysis

### Random-Effects Meta-Analysis

```python
from arakis.analysis.meta_analysis import MetaAnalysisEngine
from arakis.models.analysis import EffectMeasure

def perform_meta_analysis():
    engine = MetaAnalysisEngine()

    # Study data (from extraction)
    studies = [
        {
            "study_id": "Smith 2020",
            "effect": -15.2,  # Mean difference
            "se": 4.8,        # Standard error
            "n": 60           # Sample size
        },
        {
            "study_id": "Jones 2021",
            "effect": -12.4,
            "se": 3.9,
            "n": 80
        },
        {
            "study_id": "Brown 2022",
            "effect": -18.1,
            "se": 5.2,
            "n": 50
        },
        {
            "study_id": "Davis 2023",
            "effect": -10.5,
            "se": 4.1,
            "n": 70
        }
    ]

    # Perform random-effects meta-analysis
    result = engine.random_effects_meta_analysis(
        studies=studies,
        effect_measure=EffectMeasure.MEAN_DIFFERENCE
    )

    print(f"Meta-analysis results:")
    print(f"  Pooled effect: {result.pooled_effect:.2f} {result.pooled_ci}")
    print(f"  p-value: {result.p_value:.4f}")
    print(f"  Significant: {result.is_significant}")
    print(f"  I²: {result.i_squared:.1f}%")
    print(f"  Tau²: {result.tau_squared:.4f}")

    if result.has_high_heterogeneity:
        print("  ⚠ High heterogeneity detected")

    return result

# No async needed
result = perform_meta_analysis()
```

### Generate Forest Plot

```python
from arakis.analysis.visualizer import VisualizationGenerator

def create_forest_plot(meta_result):
    generator = VisualizationGenerator()

    # Create forest plot
    figure = generator.create_forest_plot(
        meta_result=meta_result,
        output_path="forest_plot.png"
    )

    print(f"Forest plot saved: {figure.file_path}")
    return figure

# create_forest_plot(result)
```

### Subgroup Analysis

```python
def subgroup_meta_analysis():
    engine = MetaAnalysisEngine()

    # Group 1: Studies with sample size > 60
    large_studies = [
        {"study_id": "Jones 2021", "effect": -12.4, "se": 3.9, "n": 80},
        {"study_id": "Davis 2023", "effect": -10.5, "se": 4.1, "n": 70}
    ]

    # Group 2: Studies with sample size <= 60
    small_studies = [
        {"study_id": "Smith 2020", "effect": -15.2, "se": 4.8, "n": 60},
        {"study_id": "Brown 2022", "effect": -18.1, "se": 5.2, "n": 50}
    ]

    # Analyze each subgroup
    large_result = engine.random_effects_meta_analysis(large_studies, EffectMeasure.MEAN_DIFFERENCE)
    small_result = engine.random_effects_meta_analysis(small_studies, EffectMeasure.MEAN_DIFFERENCE)

    print("Large studies:")
    print(f"  Effect: {large_result.pooled_effect:.2f}")
    print(f"  I²: {large_result.i_squared:.1f}%")

    print("\nSmall studies:")
    print(f"  Effect: {small_result.pooled_effect:.2f}")
    print(f"  I²: {small_result.i_squared:.1f}%")
```

---

## Complete Workflow

### End-to-End Systematic Review

```python
import asyncio
import json
from arakis.orchestrator import SearchOrchestrator
from arakis.agents.screener import ScreeningAgent
from arakis.agents.extractor import DataExtractionAgent
from arakis.agents.intro_writer import IntroductionWriterAgent
from arakis.agents.results_writer import ResultsWriterAgent
from arakis.models.screening import ScreeningCriteria, ScreeningStatus
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType
from arakis.analysis.meta_analysis import MetaAnalysisEngine
from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow
from arakis.models.analysis import EffectMeasure

async def complete_systematic_review():
    print("=" * 60)
    print("SYSTEMATIC REVIEW PIPELINE")
    print("=" * 60)

    # ========== 1. SEARCH ==========
    print("\n[1/6] SEARCHING DATABASES...")
    orchestrator = SearchOrchestrator()

    search_result = await orchestrator.comprehensive_search(
        research_question="Effect of aspirin on mortality in adult sepsis patients",
        databases=["pubmed", "openalex"],
        max_results_per_db=100
    )

    print(f"  ✓ Found {search_result.prisma_flow.records_identified_total} papers")
    print(f"  ✓ After deduplication: {len(search_result.unique_papers)} papers")

    # Save search results
    with open("1_search_results.json", "w") as f:
        json.dump([p.dict() for p in search_result.unique_papers], f, indent=2, default=str)

    # ========== 2. SCREENING ==========
    print("\n[2/6] SCREENING PAPERS...")
    screener = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=[
            "Human adult patients (≥18 years)",
            "Sepsis or septic shock diagnosis",
            "Aspirin intervention",
            "Mortality outcome reported"
        ],
        exclusion=[
            "Pediatric patients",
            "Animal studies",
            "Review articles"
        ]
    )

    decisions = await screener.screen_batch(
        papers=search_result.unique_papers,
        criteria=criteria,
        dual_review=True
    )

    included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
    excluded = [d for d in decisions if d.status == ScreeningStatus.EXCLUDE]

    print(f"  ✓ Screened {len(decisions)} papers")
    print(f"  ✓ Included: {len(included)}, Excluded: {len(excluded)}")

    # Save decisions
    with open("2_screening_decisions.json", "w") as f:
        json.dump([d.dict() for d in decisions], f, indent=2, default=str)

    # ========== 3. EXTRACTION ==========
    print("\n[3/6] EXTRACTING DATA...")
    extractor = DataExtractionAgent()

    schema = ExtractionSchema(
        name="RCT Schema",
        description="Extract RCT data",
        fields=[
            ExtractionField(
                name="sample_size",
                description="Total participants",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="intervention_n",
                description="Intervention group size",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="control_n",
                description="Control group size",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="intervention_deaths",
                description="Deaths in intervention group",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="control_deaths",
                description="Deaths in control group",
                field_type=FieldType.NUMERIC,
                required=True
            )
        ]
    )

    # Get included papers
    included_papers = [p for p in search_result.unique_papers if p.id in [d.paper_id for d in included]]

    extraction_result = await extractor.extract_batch(
        papers=included_papers,
        schema=schema,
        triple_review=True
    )

    print(f"  ✓ Extracted {len(extraction_result.extractions)} papers")
    print(f"  ✓ Success rate: {extraction_result.success_rate:.1%}")

    # Save extractions
    with open("3_extractions.json", "w") as f:
        json.dump([e.dict() for e in extraction_result.extractions], f, indent=2, default=str)

    # ========== 4. META-ANALYSIS ==========
    print("\n[4/6] PERFORMING META-ANALYSIS...")
    engine = MetaAnalysisEngine()

    # Convert extractions to study data
    studies = []
    for extraction in extraction_result.extractions:
        if extraction.extraction_quality > 0.8:  # High quality only
            # Calculate risk ratio
            intervention_deaths = extraction.data.get("intervention_deaths")
            control_deaths = extraction.data.get("control_deaths")
            intervention_n = extraction.data.get("intervention_n")
            control_n = extraction.data.get("control_n")

            if all([intervention_deaths, control_deaths, intervention_n, control_n]):
                rr = (intervention_deaths / intervention_n) / (control_deaths / control_n)
                se_log_rr = ((1 - intervention_deaths/intervention_n) / intervention_deaths +
                            (1 - control_deaths/control_n) / control_deaths) ** 0.5

                studies.append({
                    "study_id": extraction.paper_id,
                    "effect": rr,
                    "se": se_log_rr,
                    "n": intervention_n + control_n
                })

    if len(studies) >= 2:
        meta_result = engine.random_effects_meta_analysis(
            studies=studies,
            effect_measure=EffectMeasure.RISK_RATIO
        )

        print(f"  ✓ Pooled RR: {meta_result.pooled_effect:.2f} {meta_result.pooled_ci}")
        print(f"  ✓ p-value: {meta_result.p_value:.4f}")
        print(f"  ✓ I²: {meta_result.i_squared:.1f}%")
    else:
        print(f"  ⚠ Not enough studies for meta-analysis ({len(studies)} studies)")

    # ========== 5. VISUALIZATION ==========
    print("\n[5/6] GENERATING VISUALIZATIONS...")

    # PRISMA diagram
    flow = PRISMAFlow(
        records_identified_total=search_result.prisma_flow.records_identified_total,
        records_identified_databases=search_result.prisma_flow.records_identified_databases,
        records_removed_duplicates=search_result.prisma_flow.records_removed_duplicates,
        records_screened=len(decisions),
        records_excluded=len(excluded),
        studies_included=len(included)
    )

    prisma_gen = PRISMADiagramGenerator()
    diagram = prisma_gen.generate(flow, "4_prisma_diagram.png")

    print(f"  ✓ PRISMA diagram: {diagram.png_path}")

    # ========== 6. WRITING ==========
    print("\n[6/6] WRITING MANUSCRIPT SECTIONS...")

    # Introduction
    intro_writer = IntroductionWriterAgent()
    intro = await intro_writer.write_complete_introduction(
        research_question="Effect of aspirin on mortality in adult sepsis patients",
        inclusion_criteria=criteria.inclusion,
        primary_outcome="mortality"
    )

    with open("5_introduction.md", "w") as f:
        f.write(intro.to_markdown())

    print(f"  ✓ Introduction: {intro.total_word_count} words")

    # Results
    results_writer = ResultsWriterAgent()
    results = await results_writer.write_study_selection(
        prisma_flow=flow,
        total_papers_searched=search_result.prisma_flow.records_identified_total,
        screening_summary={
            "screened": len(decisions),
            "included": len(included),
            "excluded": len(excluded)
        }
    )

    with open("6_results.md", "w") as f:
        f.write(results.section.to_markdown())

    print(f"  ✓ Results: {results.section.total_word_count} words")

    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print("SYSTEMATIC REVIEW COMPLETE!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  1_search_results.json        - {len(search_result.unique_papers)} papers")
    print(f"  2_screening_decisions.json   - {len(decisions)} decisions")
    print(f"  3_extractions.json           - {len(extraction_result.extractions)} extractions")
    print(f"  4_prisma_diagram.png         - PRISMA flow diagram")
    print(f"  5_introduction.md            - {intro.total_word_count} words")
    print(f"  6_results.md                 - {results.section.total_word_count} words")

# Run the complete workflow
asyncio.run(complete_systematic_review())
```

---

## Advanced Usage

### Custom Field Validation

```python
from arakis.models.extraction import ExtractionField, FieldType

# Numeric with range
field = ExtractionField(
    name="age",
    description="Patient age",
    field_type=FieldType.NUMERIC,
    validation_rules={"min": 0, "max": 120}
)

# Validate
is_valid, error = field.validate(45)   # (True, None)
is_valid, error = field.validate(150)  # (False, "exceeds maximum")

# Categorical with allowed values
field = ExtractionField(
    name="outcome",
    description="Clinical outcome",
    field_type=FieldType.CATEGORICAL,
    validation_rules={"allowed_values": ["mortality", "morbidity", "recovery"]}
)

# Text with length limits
field = ExtractionField(
    name="abstract",
    description="Study abstract",
    field_type=FieldType.TEXT,
    validation_rules={"max_length": 5000}
)
```

### Batch Processing with Rate Limiting

```python
import asyncio

async def process_large_dataset(papers, batch_size=10):
    """Process papers in batches to respect rate limits."""
    screener = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=["Human adults", "RCTs"],
        exclusion=["Animals"]
    )

    all_decisions = []

    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}...")

        decisions = await screener.screen_batch(batch, criteria)
        all_decisions.extend(decisions)

        # Small delay between batches
        await asyncio.sleep(1)

    return all_decisions
```

---

## Tips and Best Practices

1. **Save intermediate results** - Save after each major step (search, screening, extraction)
2. **Use progress callbacks** - Monitor long-running operations
3. **Start with small samples** - Test with 5-10 papers before full run
4. **Balance cost vs quality** - Use triple-review only when needed
5. **Validate extracted data** - Check quality scores and review flagged papers
6. **Handle errors gracefully** - Wrap API calls in try-except blocks

For more information, see [API Reference](API_REFERENCE.md) and [Quick Start](QUICK_START.md).

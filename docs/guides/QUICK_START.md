# Quick Start Guide

Get started with Arakis in 5 minutes.

---

## Installation

```bash
# 1. Install Arakis
pip install -e .

# 2. Set up API keys
cp .env.example .env
```

Edit `.env` and add your keys:
```bash
OPENAI_API_KEY=sk-...              # Required
UNPAYWALL_EMAIL=your@email.com    # Required
NCBI_API_KEY=...                   # Optional (for higher PubMed rate limits)
```

---

## Basic Usage

### 1. Search for Papers

```python
import asyncio
from arakis.orchestrator import SearchOrchestrator

async def main():
    # Create orchestrator
    orchestrator = SearchOrchestrator()

    # Search one database
    result = await orchestrator.search_single_database(
        query="aspirin[tiab] AND sepsis[tiab]",
        database="pubmed",
        max_results=50
    )

    print(f"Found {len(result.papers)} papers")
    for paper in result.papers[:3]:
        print(f"- {paper.title}")

# Run
asyncio.run(main())
```

### 2. Screen Papers with AI

```python
from arakis.agents.screener import ScreeningAgent
from arakis.models.screening import ScreeningCriteria, ScreeningStatus

async def screen_papers():
    agent = ScreeningAgent()

    # Define criteria
    criteria = ScreeningCriteria(
        inclusion=[
            "Human adult patients (≥18 years)",
            "Randomized controlled trials",
            "Clinical outcomes reported"
        ],
        exclusion=[
            "Animal studies",
            "Review articles"
        ]
    )

    # Screen papers (dual-review by default)
    decisions = await agent.screen_batch(
        papers=result.papers,
        criteria=criteria
    )

    # Filter included papers
    included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
    print(f"Included {len(included)} papers")

asyncio.run(screen_papers())
```

### 3. Extract Data

```python
from arakis.agents.extractor import DataExtractionAgent
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType

async def extract_data():
    agent = DataExtractionAgent()

    # Define what to extract
    schema = ExtractionSchema(
        name="RCT Data",
        description="Extract RCT information",
        fields=[
            ExtractionField(
                name="sample_size",
                description="Total number of participants",
                field_type=FieldType.NUMERIC,
                required=True
            ),
            ExtractionField(
                name="intervention",
                description="Intervention description",
                field_type=FieldType.TEXT,
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

    # Extract from papers
    result = await agent.extract_batch(
        papers=included_papers,
        schema=schema,
        triple_review=False  # Single-pass for speed
    )

    print(f"Success rate: {result.success_rate:.1%}")

    # Access extracted data
    for extraction in result.extractions:
        print(f"\nPaper: {extraction.paper_id}")
        print(f"Sample size: {extraction.data.get('sample_size')}")
        print(f"Quality: {extraction.extraction_quality}")

asyncio.run(extract_data())
```

### 4. Statistical Analysis

```python
from arakis.analysis.engine import StatisticalEngine

# No async needed - statistical tests are synchronous
engine = StatisticalEngine()

# Example: Compare two groups
control_group = [12.5, 13.2, 11.8, 14.1, 12.9]
treatment_group = [15.3, 16.1, 14.8, 15.9, 16.4]

result = engine.independent_t_test(control_group, treatment_group)

print(f"p-value: {result.p_value:.4f}")
print(f"Effect size: {result.effect_size:.2f}")
print(f"Significant: {result.is_significant}")  # True if p < 0.05
```

### 5. Generate PRISMA Diagram

```python
from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow

# Create flow data
flow = PRISMAFlow(
    records_identified_total=1000,
    records_identified_databases={"pubmed": 500, "openalex": 500},
    records_removed_duplicates=200,
    records_screened=800,
    records_excluded=700,
    studies_included=100
)

# Generate diagram
generator = PRISMADiagramGenerator()
diagram = generator.generate(flow, "prisma.png")

print(f"Diagram saved: {diagram.png_path}")
```

### 6. Write Manuscript Sections

```python
from arakis.agents.intro_writer import IntroductionWriterAgent

async def write_intro():
    writer = IntroductionWriterAgent()

    # Write introduction
    intro = await writer.write_complete_introduction(
        research_question="Effect of aspirin on mortality in sepsis patients",
        inclusion_criteria=["Human adults", "Sepsis", "RCTs"],
        primary_outcome="30-day mortality"
    )

    # Save to file
    with open("introduction.md", "w") as f:
        f.write(intro.to_markdown())

    print(f"Wrote {intro.total_word_count} words")

asyncio.run(write_intro())
```

---

## Complete Example

Here's a complete workflow from search to manuscript:

```python
import asyncio
from arakis.orchestrator import SearchOrchestrator
from arakis.agents.screener import ScreeningAgent
from arakis.agents.extractor import DataExtractionAgent
from arakis.agents.intro_writer import IntroductionWriterAgent
from arakis.models.screening import ScreeningCriteria, ScreeningStatus
from arakis.models.extraction import ExtractionSchema, ExtractionField, FieldType
from arakis.visualization.prisma import PRISMADiagramGenerator
from arakis.models.visualization import PRISMAFlow

async def systematic_review():
    # 1. SEARCH
    print("1. Searching...")
    orchestrator = SearchOrchestrator()
    search_result = await orchestrator.search_single_database(
        query="aspirin[tiab] AND sepsis[tiab]",
        database="pubmed",
        max_results=20
    )
    print(f"   Found {len(search_result.papers)} papers")

    # 2. SCREENING
    print("\n2. Screening...")
    screener = ScreeningAgent()
    criteria = ScreeningCriteria(
        inclusion=["Human adults", "RCTs", "Clinical outcomes"],
        exclusion=["Animal studies", "Reviews"]
    )
    decisions = await screener.screen_batch(search_result.papers, criteria)
    included = [d for d in decisions if d.status == ScreeningStatus.INCLUDE]
    excluded = [d for d in decisions if d.status == ScreeningStatus.EXCLUDE]
    print(f"   Included: {len(included)}, Excluded: {len(excluded)}")

    # 3. EXTRACTION
    print("\n3. Extracting data...")
    extractor = DataExtractionAgent()
    schema = ExtractionSchema(
        name="RCT",
        description="RCT data",
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

    # Get included papers
    included_papers = [p for p in search_result.papers if p.id in [d.paper_id for d in included]]

    if included_papers:
        extraction_result = await extractor.extract_batch(
            papers=included_papers,
            schema=schema,
            triple_review=False
        )
        print(f"   Extracted data from {len(extraction_result.extractions)} papers")

    # 4. PRISMA DIAGRAM
    print("\n4. Generating PRISMA diagram...")
    flow = PRISMAFlow(
        records_identified_total=len(search_result.papers),
        records_identified_databases={"pubmed": len(search_result.papers)},
        records_removed_duplicates=0,
        records_screened=len(decisions),
        records_excluded=len(excluded),
        studies_included=len(included)
    )
    generator = PRISMADiagramGenerator()
    diagram = generator.generate(flow, "prisma.png")
    print(f"   Saved: {diagram.png_path}")

    # 5. WRITE INTRODUCTION
    print("\n5. Writing introduction...")
    writer = IntroductionWriterAgent()
    intro = await writer.write_complete_introduction(
        research_question="Effect of aspirin on mortality in sepsis",
        inclusion_criteria=criteria.inclusion,
        primary_outcome="mortality"
    )
    with open("introduction.md", "w") as f:
        f.write(intro.to_markdown())
    print(f"   Wrote {intro.total_word_count} words")

    print("\n✓ Complete!")

# Run the workflow
asyncio.run(systematic_review())
```

**Output:**
```
1. Searching...
   Found 20 papers

2. Screening...
   Included: 3, Excluded: 17

3. Extracting data...
   Extracted data from 3 papers

4. Generating PRISMA diagram...
   Saved: prisma.png

5. Writing introduction...
   Wrote 487 words

✓ Complete!
```

---

## CLI Usage

For quick tasks, use the CLI:

```bash
# Search
arakis search "aspirin for sepsis" --databases pubmed --max-results 50

# Screen
arakis screen results.json --include "Human RCTs" --exclude "Animal studies"

# Extract
arakis extract screening_results.json --schema rct --output extractions.json

# Generate PRISMA diagram
arakis prisma-diagram search_results.json --output prisma.png

# Write sections
arakis write-intro "Research question" --output intro.md
arakis write-results --search search.json --screening screening.json --output results.md
```

---

## Common Patterns

### Save and Load Results

```python
import json

# Save search results
with open("search_results.json", "w") as f:
    json.dump([p.dict() for p in result.papers], f, indent=2)

# Load search results
from arakis.models.paper import Paper
with open("search_results.json", "r") as f:
    data = json.load(f)
    papers = [Paper(**item) for item in data]
```

### Progress Tracking

```python
def progress_callback(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

decisions = await screener.screen_batch(
    papers=papers,
    criteria=criteria,
    progress_callback=progress_callback
)
```

### Error Handling

```python
from arakis.clients.base import RateLimitError, SearchClientError

try:
    result = await orchestrator.search_single_database(...)
except RateLimitError:
    print("Rate limited - waiting and retrying automatically")
    # Automatic retry with exponential backoff
except SearchClientError as e:
    print(f"Search failed: {e}")
```

---

## Next Steps

- Read the [API Reference](API_REFERENCE.md) for complete documentation
- See [Examples](EXAMPLES.md) for more use cases
- Check [CLAUDE.md](CLAUDE.md) for architecture details

---

## Cost Estimation

For a typical systematic review with 100 papers:

| Task | Quantity | Cost |
|------|----------|------|
| Search | 1 | FREE |
| Query generation | 1 | $0.05 |
| Screening (dual) | 100 papers | $2.00 |
| Extraction (single-pass) | 20 papers | $4.00 |
| Statistical tests | Any | FREE |
| PRISMA diagram | 1 | FREE |
| Write intro | 1 | $1.00 |
| Write results | 1 | $0.30 |
| **Total** | | **~$7.35** |

**Tips to reduce cost:**
- Use `dual_review=False` for screening ($1/100 papers)
- Use `triple_review=False` for extraction ($0.20/paper instead of $0.50-0.70)
- Statistical analysis and visualization are free

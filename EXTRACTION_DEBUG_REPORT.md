# Data Extraction Workflow - Debug Report

## Overview

The data extraction workflow extracts structured data from papers using LLM with:
- **Triple-review mode** (default): 3 independent passes with majority voting
- **Single-pass mode** (fast): 1 pass for speed
- **Schema-based extraction**: RCT, Cohort, Case-Control, Diagnostic schemas

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA EXTRACTION WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ExtractStageExecutor                              │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ 1. Auto-detect schema (from research question)                │  │   │
│  │  │ 2. Filter papers with text (full_text or abstract)            │  │   │
│  │  │ 3. Convert to Paper objects                                   │  │   │
│  │  │ 4. Call DataExtractionAgent.extract_batch()                   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DataExtractionAgent                               │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ extract_batch()                                               │  │   │
│  │  │ ├── Process papers in batches (default: 3 concurrent)        │  │   │
│  │  │ └── For each paper: extract_paper()                          │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                    │                                │   │
│  │                                    ▼                                │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ extract_paper()                                               │  │   │
│  │  │ ├── Single-pass: 1 extraction pass (temp=0.3)                 │  │   │
│  │  │ └── Triple-review: 3 passes (temps=0.2, 0.5, 0.8)             │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                    │                                │   │
│  │                                    ▼                                │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ _single_extraction_pass()                                     │  │   │
│  │  │ ├── Build prompt with paper text (full text or abstract)     │  │   │
│  │  │ ├── Call OpenAI with extraction schema                       │  │   │
│  │  │ └── Parse tool_calls response                                │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                    │                                │   │
│  │                                    ▼                                │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ _resolve_conflicts() [triple-review only]                     │  │   │
│  │  │ ├── Group decisions by field                                  │  │   │
│  │  │ ├── Apply majority voting                                     │  │   │
│  │  │ └── Calculate confidence based on agreement                   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                    │                                │   │
│  │                                    ▼                                │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ validate_extraction()                                         │  │   │
│  │  │ └── Check extracted data against schema constraints          │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         ExtractionResult                             │   │
│  │  ├── Summary statistics (success rate, quality, conflicts)          │   │
│  │  ├── Performance metrics (time, tokens, cost)                       │   │
│  │  └── List of ExtractedData objects                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## BUGS FOUND & FIXES

### Bug 1: Missing Paper Properties in ExtractStageExecutor

**Location**: `src/arakis/workflow/stages/extract.py` lines 91-102

**Issue**: When converting paper dicts to Paper objects, the code doesn't set `full_text` or `has_full_text` properly.

```python
# CURRENT CODE (BUGGY):
paper = Paper(
    id=p["id"],
    title=p.get("title", ""),
    abstract=p.get("abstract"),
    doi=p.get("doi"),
    source=PaperSource(p.get("source", "pubmed")),
)
if p.get("full_text") and use_full_text:
    paper.full_text = p["full_text"]  # This works
```

**Problem**: The `Paper` dataclass has `has_full_text` property that checks `full_text`, but the extractor uses `paper.has_full_text` in `_get_paper_text()`.

**Fix**: The code is actually correct since `has_full_text` is a property that checks `full_text`. Let me verify...

Looking at `models/paper.py`:
```python
@property
def has_full_text(self) -> bool:
    """Check if paper has extracted full text."""
    return bool(self.full_text and len(self.full_text.strip()) > 100)
```

**Status**: ✅ Not a bug - works correctly

---

### Bug 2: Papers Without Text Silently Dropped

**Location**: `src/arakis/workflow/stages/extract.py` lines 60-70

**Issue**: Papers without text are filtered out without any warning or reporting.

```python
# CURRENT CODE:
papers_to_extract = [
    p for p in papers_data
    if p.get("has_full_text") or p.get("abstract")
]

if not papers_to_extract:
    return StageResult(
        success=False,
        error="No papers with text available for extraction",
    )
```

**Problem**: If some papers have text and some don't, the ones without are silently ignored. No warning is logged.

**Fix**: Add warning logging

```python
# FIXED CODE:
papers_with_text = [p for p in papers_data if p.get("has_full_text") or p.get("abstract")]
papers_without_text = [p for p in papers_data if not (p.get("has_full_text") or p.get("abstract"))]

if papers_without_text:
    logger.warning(
        f"[extract] {len(papers_without_text)} papers have no text (skipped): "
        f"{[p['id'] for p in papers_without_text[:5]]}"
    )

if not papers_with_text:
    return StageResult(
        success=False,
        error="No papers with text available for extraction",
    )
```

---

### Bug 3: Empty Full Text Check Missing

**Location**: `src/arakis/agents/extractor.py` lines 199-221

**Issue**: `_get_paper_text()` doesn't handle the case where `full_text` exists but is empty or whitespace-only.

```python
# CURRENT CODE:
if use_full_text and paper.has_full_text:
    token_count = self._count_tokens(paper.full_text)
```

**Problem**: If `full_text` is just whitespace or very short (<100 chars), `has_full_text` returns False, but there's no explicit check for empty/whitespace-only text that passes the 100-char threshold.

**Status**: ✅ Not a bug - the 100-char threshold in `has_full_text` handles this

---

### Bug 4: Missing Import in extraction/models.py

**Location**: `src/arakis/models/extraction.py` line 13

**Issue**: There's an import after a function definition.

```python
# CURRENT CODE:
def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)
from typing import Any  # <-- Import after function!
```

**Fix**: Move import to the top of the file.

```python
# FIXED CODE:
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any  # <-- Move here
```

---

### Bug 5: ExtractedData.__post_init__ Override Issue

**Location**: `src/arakis/models/extraction.py` lines 261-276

**Issue**: `__post_init__` sets `needs_human_review` but may override values set during extraction.

```python
# CURRENT CODE:
def __post_init__(self):
    """Automatically determine quality flags after initialization."""
    # Populate low_confidence_fields based on confidence scores
    self.low_confidence_fields = [...]
    
    # Automatically flag for human review if quality issues detected
    if not self.needs_human_review:  # Don't override if already set
        self.needs_human_review = (
            len(self.conflicts) > 0
            or len(self.low_confidence_fields) > 0
            or self.extraction_quality < self.LOW_QUALITY_THRESHOLD
        )
```

**Problem**: The check `if not self.needs_human_review` is correct, but the dataclass default is `False`, so this should work. However, there's a subtle issue: if someone creates an `ExtractedData` with `needs_human_review=True` explicitly, the `low_confidence_fields` might not be populated.

**Fix**: Always populate `low_confidence_fields` regardless of `needs_human_review`.

```python
# FIXED CODE:
def __post_init__(self):
    """Automatically determine quality flags after initialization."""
    # Always populate low_confidence_fields based on confidence scores
    self.low_confidence_fields = [
        field_name
        for field_name, confidence_score in self.confidence.items()
        if confidence_score < self.LOW_CONFIDENCE_THRESHOLD
    ]
    
    # Automatically flag for human review if quality issues detected
    # Only override if not explicitly set (dataclass default is False)
    if not self.needs_human_review:
        self.needs_human_review = (
            len(self.conflicts) > 0
            or len(self.low_confidence_fields) > 0
            or self.extraction_quality < self.LOW_QUALITY_THRESHOLD
        )
```

**Status**: ✅ Already correct in current code

---

### Bug 6: Schema Validation Error Handling

**Location**: `src/arakis/agents/extractor.py` lines 557-595

**Issue**: Validation errors are added to conflicts list as strings, but the format is inconsistent.

```python
# CURRENT CODE:
for field_name, errors in field_errors.items():
    if field_name == "_unexpected":
        # Unexpected fields are warnings, not critical errors
        validation_errors.append(f"Warning: {'; '.join(errors)}")
    else:
        invalid_fields.append(field_name)
        validation_errors.append(f"{field_name}: {'; '.join(errors)}")

# Add validation errors to conflicts list
conflicts.extend(validation_errors)
```

**Problem**: The format `"Warning: ..."` vs `"field_name: ..."` is inconsistent. Also, unexpected fields should probably be handled differently.

**Status**: ⚠️ Minor issue - doesn't break functionality

---

### Bug 7: Missing Progress Callback for Batch Processing

**Location**: `src/arakis/agents/extractor.py` lines 686-734

**Issue**: The `extract_batch()` progress callback doesn't include paper/extraction info.

```python
# CURRENT CODE:
def wrapped_callback(
    current: int, total: int, paper: Paper, extraction: ExtractedData
) -> None:
    if progress_callback:
        progress_callback(current, total)
```

**Problem**: The wrapped callback receives `paper` and `extraction` but doesn't pass them to the original callback. This limits the usefulness of the progress callback.

**Fix**: Pass extraction info to callback

```python
# FIXED CODE:
def wrapped_callback(
    current: int, total: int, paper: Paper, extraction: ExtractedData
) -> None:
    if progress_callback:
        # Pass extraction quality info to callback
        progress_callback(
            current, 
            total,
            paper_id=paper.id,
            quality=extraction.extraction_quality,
            needs_review=extraction.needs_human_review
        )
```

---

### Bug 8: Cost Estimation Inaccuracy

**Location**: `src/arakis/agents/extractor.py` lines 737-750

**Issue**: Cost estimation uses hardcoded token counts that may not reflect reality.

```python
# CURRENT CODE:
if triple_review:
    total_tokens_input = len(papers) * 30000
    total_tokens_output = len(papers) * 3000
else:
    total_tokens_input = len(papers) * 10000
    total_tokens_output = len(papers) * 1000
```

**Problem**: These are rough estimates. Actual tokens depend on paper length and schema complexity.

**Status**: ⚠️ Documentation issue - estimates are labeled as "rough approximation"

---

## DATA FLOW

### Input Format (from PDF Fetch Stage)

```python
{
    "papers": [
        {
            "id": "pubmed_12345",
            "title": "Paper Title",
            "abstract": "Abstract text...",
            "full_text": "Full paper text...",  # May be None
            "has_full_text": True,  # Boolean flag
            "doi": "10.1234/example",
            "source": "pubmed",
            "year": 2023,
            # ... other metadata
        }
    ],
    "schema": "auto",  # or "rct", "cohort", "case_control", "diagnostic"
    "fast_mode": False,  # True = single-pass, False = triple-review
    "use_full_text": True,  # DEFAULT: True (enabled by default)
    "research_question": "Effect of X on Y",
    "inclusion_criteria": ["Human RCTs"],
}
```

### Output Format

```python
StageResult(
    success=True,
    output_data={
        "total_papers": 10,
        "successful": 8,
        "failed": 2,
        "average_quality": 0.85,
        "schema_used": "rct",
        "extractions": [
            {
                "paper_id": "pubmed_12345",
                "data": {
                    "sample_size_total": 120,
                    "intervention_name": "Drug X",
                    "primary_outcome": "Mortality reduction",
                    # ... all extracted fields
                },
                "confidence": {
                    "sample_size_total": 0.95,
                    "intervention_name": 0.88,
                    # ... confidence per field
                },
                "extraction_quality": 0.92,
                "needs_human_review": False,
                "low_confidence_fields": [],
            }
        ]
    },
    cost=0.60,  # Estimated cost in USD
)
```

---

## COST BREAKDOWN

### Per Paper (Triple-Review Mode)

| Component | Tokens | Cost (GPT-4o) |
|-----------|--------|---------------|
| Input (paper text + schema) | ~10K-30K | $0.025-0.075 |
| Output (3 passes × ~1K) | ~3K | $0.03 |
| **Total per paper** | **~33K** | **~$0.055-0.105** |

### Per Paper (Single-Pass Mode)

| Component | Tokens | Cost (GPT-4o) |
|-----------|--------|---------------|
| Input (paper text + schema) | ~10K | $0.025 |
| Output (~1K) | ~1K | $0.01 |
| **Total per paper** | **~11K** | **~$0.035** |

### Example: 20 Papers

| Mode | Total Cost | API Calls |
|------|-----------|-----------|
| Triple-review | ~$1.10-2.10 | 60 |
| Single-pass | ~$0.70 | 20 |

---

## SCHEMAS

### Available Schemas

1. **RCT Schema** (`rct`): 20 fields
   - Study design, sample sizes, intervention details
   - Outcomes, blinding, randomization method
   - Adverse events, funding source

2. **Cohort Schema** (`cohort`): 15 fields
   - Cohort type, exposure assessment
   - Follow-up duration, loss to follow-up
   - Effect measures, confounders

3. **Case-Control Schema** (`case_control`): 13 fields
   - Cases/controls numbers, matching criteria
   - Exposure assessment, odds ratios

4. **Diagnostic Schema** (`diagnostic`): 16 fields
   - Index test, reference standard
   - 2×2 table (TP/FP/TN/FN)
   - Sensitivity, specificity, PPV, NPV

### Auto-Detection

Schema is auto-detected from research question using keyword matching:
- RCT keywords: "randomized", "clinical trial", "double-blind", "placebo"
- Cohort keywords: "cohort", "observational", "prospective", "follow-up"
- Case-Control keywords: "case-control", "matched controls"
- Diagnostic keywords: "diagnostic accuracy", "sensitivity", "specificity"

---

## TESTING

### Unit Tests

```bash
# Run extraction tests
pytest tests/test_extraction.py -xvs

# Run workflow stage tests
pytest tests/test_workflow_stages.py::TestExtractStageExecutor -xvs
```

### Integration Test

```bash
# Create test script
python test_extraction_integration.py
```

---

## RECOMMENDATIONS

### 1. Always Use Full Text
- Set `use_full_text=True` (default)
- Full text provides much richer data than abstracts
- Cost difference is minimal (~2x tokens, but better accuracy)

### 2. Monitor Low-Confidence Fields
- Fields with confidence < 0.8 need review
- Common low-confidence fields: adverse_events, funding_source

### 3. Handle Conflicts
- Triple-review mode detects conflicts automatically
- Conflicts default to majority value
- Always review papers with conflicts

### 4. Schema Selection
- Use auto-detection for mixed study types
- Specify schema explicitly for homogeneous studies
- RCT schema works best for intervention studies

---

## SUMMARY

| Component | Status | Notes |
|-----------|--------|-------|
| ExtractStageExecutor | ⚠️ | Minor logging issue |
| DataExtractionAgent | ✅ | Works correctly |
| Conflict Resolution | ✅ | Majority voting works |
| Schema Validation | ✅ | Validates correctly |
| Cost Estimation | ⚠️ | Rough estimates only |
| Progress Callback | ⚠️ | Could include more info |

**Overall Status**: ✅ Functional with minor improvements needed

# Product Requirements Document: Arakis Workflow Improvements

## Overview

This document outlines the requirements for fixing and improving the Arakis systematic review workflow based on user feedback. The current workflow has several issues that need to be addressed to produce reliable, high-quality manuscript outputs.

---

## Issues to Fix

### Critical Issues
1. **Screening Incomplete** - Screening never completes for all papers found; must process ALL papers without early stopping
2. **PRISMA Not Correctly Written** - Flow diagram and narrative description are not being generated properly
3. **Data Extraction Unreliable** - Extraction process fails or produces inconsistent results
4. **Meta-Analysis Rarely Completed** - Statistical tests and analysis are not being completed or displayed
5. **References Incorrectly Written** - Citations and reference lists are not properly formatted
6. **Tables Inappropriately Populated** - Study characteristics and other tables have incorrect or missing data

### Quality Issues
- Poor overall output quality not meeting academic standards
- Missing statistics in meta-analysis output
- Incomplete audit trails for decisions

---

## Manuscript Structure Requirements

### Abstract
- **Format**: Structured abstract
- **Sections**: Background, Methods, Results, Conclusions
- **Word limit**: Follow journal guidelines (typically 250-350 words)

### Introduction
- **Format**: PRISMA 2020 compliant
- **Subsections**:
  1. **Background** (200-250 words): Broad context → specific problem
  2. **Rationale** (100-150 words): Gaps in literature, justification for review
  3. **Objectives** (80-120 words): Clear, specific aims (PICO-structured)

### Methods
- Standard systematic review methods section
- Include: Search strategy, eligibility criteria, screening process, data extraction, quality assessment, statistical analysis

### Results
- **Format**: PRISMA structure
- **Subsections**:
  1. **Study Selection**: Search results and PRISMA flow narrative
  2. **Study Characteristics**: Summary of included studies with Table 1
  3. **Risk of Bias**: Quality assessment results
  4. **Synthesis of Results**: Meta-analysis findings with statistics

### Discussion
- **Format**: Extended 4-part structure
- **Subsections**:
  1. **Summary of Main Findings** (150-200 words): Interpret key results
  2. **Comparison with Existing Literature** (250-300 words): Compare with previous work
  3. **Limitations** (150-200 words): Acknowledge study limitations
  4. **Implications and Recommendations** (150-200 words): Clinical and policy recommendations
  5. **Future Research** (100-150 words): Gaps and future research directions

### Conclusions
- Brief summary of main findings and implications

---

## Tables Requirements

### Table 1: Study Characteristics
- **Column Definition**: Auto-derived from extraction schema being used
- **Typical columns** (when not auto-derived):
  - Author/Year
  - Study Design
  - Country/Setting
  - Population (N)
  - Intervention
  - Comparator
  - Outcomes
  - Follow-up duration
- **Format**: Markdown table, placed at end of document

### Table 2: Risk of Bias Assessment
- **Tool Selection**: Auto-detect based on study type
  - RCTs → Cochrane RoB 2
  - Non-randomized studies → ROBINS-I
  - Diagnostic studies → QUADAS-2
  - Observational studies → Newcastle-Ottawa Scale
- **Content**: Assessment for each domain per study
- **Summary**: Overall risk judgment per study

### Table 3: Summary of Findings (GRADE)
- **Format**: GRADE-style summary table
- **Content**:
  - Outcome
  - Number of studies
  - Number of participants
  - Effect estimate (95% CI)
  - Certainty of evidence
  - Comments

---

## PRISMA Requirements

### Flow Diagram
- **Format**: PNG image (300 DPI) for publication
- **Compliance**: PRISMA 2020 checklist
- **Content**:
  - Identification: Records from databases and registers
  - Screening: Records screened, excluded with reasons
  - Eligibility: Full-text articles assessed
  - Inclusion: Studies included in review and synthesis

### Narrative Description
- **Location**: Results section, Study Selection subsection
- **Content**: Text describing each stage of the selection process
- **Statistics**: Exact numbers at each stage with reasons for exclusion

---

## Screening Requirements

### Processing
- **Completeness**: MUST process ALL papers found (no early stopping)
- **Batching**: Process in configurable batches with progress reporting
- **Real-time Supervision**: Option to monitor and intervene during screening

### Audit Trail
Full audit trail for each paper:
- Decision (INCLUDE/EXCLUDE/MAYBE)
- Reason for decision
- Matched inclusion/exclusion criteria
- Confidence score
- Reviewer notes
- Timestamp
- Reviewer ID (for dual-review)

### Dual Review
- Default: Dual-review mode with conflict detection
- Conflict resolution: Flag for human review when reviewers disagree
- Single-review option available for faster processing

---

## Data Extraction Requirements

### Reliability
- **Retry Logic**: Automatically retry failed extractions with different prompts
- **Manual Review Flags**: Mark uncertain extractions for human verification
- **Failure Logging**: Log detailed explanations for extraction failures

### Quality Assurance
- Confidence scoring per field
- Highlight low-confidence extractions
- Validate extracted values against schema constraints

### Schema
- Auto-detect study type and apply appropriate schema
- Support custom schemas via configuration
- Pre-built schemas: RCT, cohort, case-control, diagnostic

---

## Meta-Analysis Requirements

### Statistical Output (REQUIRED)
All meta-analyses MUST display:
1. **Effect Sizes**: Mean difference, OR, RR, or SMD as appropriate
2. **Confidence Intervals**: 95% CI for all effect estimates
3. **Heterogeneity Metrics**:
   - I² statistic with interpretation
   - τ² (tau-squared)
   - Q-statistic with p-value
4. **Individual Study Weights**: Weight contribution of each study

### Visualizations
1. **Forest Plot** (REQUIRED):
   - Individual study effects with CI
   - Pooled effect with diamond
   - Study weights shown
   - Heterogeneity statistics displayed

2. **Funnel Plot** (REQUIRED):
   - Publication bias assessment
   - Pseudo-95% CI limits
   - Egger's test result if sufficient studies

3. **Subgroup Analyses**:
   - Stratified forest plots by key variables
   - Interaction p-values between subgroups

### When Meta-Analysis Not Feasible
1. **Explain Why**: Document the specific reasons (heterogeneity, insufficient data, incompatible outcomes)
2. **Narrative Synthesis**: Provide qualitative summary describing findings across studies
3. **Vote Counting**: Summarize direction of effects across studies if appropriate

---

## References Requirements

### Citation Format
- **Default Style**: APA 7th Edition
- **Configurable**: Support for Vancouver, Harvard, Chicago styles
- **In-text Format**: Author (Year)
  - Example: "Smith et al. (2024) found..." or "...was observed (Smith et al., 2024)"

### Reference List
- **Location**: End of manuscript
- **Format**: APA 7th Edition default
  ```
  Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article.
  Journal Name, Volume(Issue), pages. https://doi.org/xxxxx
  ```
- **Validation**: All in-text citations must have corresponding reference list entry
- **Ordering**: Alphabetical by first author surname

### Citation Tracking
- Register all cited papers in ReferenceManager
- Validate citations against registered papers
- Flag any unmatched citations

---

## Output Requirements

### File Format
- **Primary**: Markdown (.md)
- **Structure**: Single document with clear section headers

### Figure/Table Placement
- **Location**: End of document (journal submission style)
- **Format**:
  ```markdown
  ---
  ## Figures

  ### Figure 1: PRISMA Flow Diagram
  ![PRISMA Flow Diagram](figures/prisma.png)

  **Figure 1.** PRISMA 2020 flow diagram showing...

  ---
  ## Tables

  ### Table 1: Characteristics of Included Studies
  | Author | Year | Design | ... |
  |--------|------|--------|-----|
  ```

### Figure Files
- **Format**: PNG (300 DPI)
- **Location**: `./figures/` subdirectory
- **Naming**: Descriptive names (e.g., `forest_plot_mortality.png`)

---

## Progress and Logging Requirements

### Verbosity Level
- **Default**: Full verbosity
- **Display**: Every action with details
  - Which paper is being processed
  - What decision was made
  - Which database is being queried
  - Current counts (e.g., "Processing paper 15/50")

### Progress Reporting
```
[SEARCH] Querying PubMed... found 234 records
[SEARCH] Querying OpenAlex... found 456 records
[DEDUP] Removing duplicates... 543 unique papers
[SCREEN] Processing paper 1/543: "Title of paper..."
[SCREEN] Decision: INCLUDE (confidence: 0.92)
[SCREEN] Matched criteria: RCT, Human participants
...
```

---

## Error Handling Requirements

### Behavior
- **Mode**: Interactive prompts
- **On Error**: Pause execution and prompt user for decision

### User Options When Error Occurs
1. Retry the failed operation
2. Skip and continue with remaining items
3. Provide manual input/override
4. Abort workflow

### Error Logging
- Log all errors with full context
- Include: timestamp, operation, input data, error message, stack trace

---

## State Management Requirements

### Resume Capability
- **Mode**: Full state saving
- **Checkpoints**: Save state after each operation
- **Resume**: Exact continuation from point of interruption

### State File
- **Format**: JSON
- **Location**: Output directory
- **Content**:
  - Current stage
  - Processed paper IDs
  - Screening decisions
  - Extraction results
  - Any intermediate data

### Resume Command
```bash
arakis workflow --resume ./my_review/state.json
```

---

## User Interface Requirements

### Primary Interface
- **Type**: Web UI Dashboard
- **Features**:
  - Real-time progress visualization
  - Paper screening supervision
  - Decision override capability
  - Error handling prompts
  - Results preview

### Dashboard Components
1. **Progress Panel**: Current stage, completion percentage, time elapsed
2. **Paper Queue**: List of papers being processed with status
3. **Decision Log**: Audit trail of all decisions
4. **Error Panel**: Any errors requiring attention
5. **Results Preview**: Live preview of generated content

### CLI Fallback
- Maintain CLI functionality for headless/scripted operation
- CLI should support all features available in web UI

---

## Quality Assessment Requirements

### Risk of Bias Tools
Auto-detect and apply appropriate tool:

| Study Type | Assessment Tool |
|------------|-----------------|
| RCTs | Cochrane RoB 2 |
| Non-randomized interventions | ROBINS-I |
| Diagnostic accuracy | QUADAS-2 |
| Cohort/Case-control | Newcastle-Ottawa Scale |
| Cross-sectional | Adapted NOS or JBI checklist |

### Assessment Output
- Domain-level judgments
- Overall risk judgment
- Supporting justification for each judgment
- Visual summary (traffic light plot)

---

## Acceptance Criteria

### Screening
- [x] All papers are processed (100% completion)
- [x] Full audit trail recorded for each paper
- [x] Progress displayed in real-time
- [x] Batch processing with configurable size

### Data Extraction
- [x] Retry logic implemented for failures
- [x] Low-confidence fields flagged
- [x] Failure reasons logged
- [x] Schema validation enforced

### Meta-Analysis
- [x] Forest plot generated with all required statistics
- [x] Funnel plot generated
- [x] Heterogeneity metrics displayed (I², τ², Q)
- [x] Individual study weights shown
- [x] Subgroup analyses performed when applicable
- [x] Narrative synthesis when meta-analysis not feasible

### PRISMA
- [x] Flow diagram generated (PNG, 300 DPI)
- [x] Narrative description in Results section
- [ ] All numbers accurate and traceable

### Tables
- [ ] Table 1 populated with correct study characteristics
- [ ] Risk of bias table with appropriate tool
- [ ] GRADE summary of findings table

### References
- [ ] All citations properly formatted (APA 7th)
- [ ] All in-text citations have reference list entries
- [ ] No orphaned references

### Output
- [ ] Markdown file generated
- [ ] Figures/tables at end of document
- [ ] All figures saved to ./figures/ directory

### State Management
- [ ] State saved after each operation
- [ ] Resume from any point possible
- [ ] No data loss on interruption

---

## Implementation Priority

### Phase 1: Critical Fixes
1. Fix screening to process ALL papers
2. Fix data extraction reliability
3. Fix meta-analysis completion and statistics display
4. Fix PRISMA diagram generation

### Phase 2: Quality Improvements
1. Implement full audit trails
2. Add interactive error handling
3. Improve table population
4. Fix reference formatting

### Phase 3: New Features
1. Web UI dashboard
2. Full state saving and resume
3. Real-time supervision mode
4. Custom table column configuration

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-20 | User/Claude | Initial requirements gathering |

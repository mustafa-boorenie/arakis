# Arakis Workflow Guide

## Streamlined CLI Workflow

The `arakis workflow` command runs the complete systematic review pipeline end-to-end with a single command.

### Quick Start

```bash
arakis workflow \
  --question "Effect of aspirin on sepsis mortality" \
  --include "Adult patients,Sepsis,Aspirin intervention,Mortality outcomes" \
  --exclude "Pediatric studies,Animal studies" \
  --databases pubmed \
  --max-results 20 \
  --output ./my_review
```

### Pipeline Stages

The workflow command automatically runs all 7 stages:

1. **Literature Search** - Searches databases and deduplicates results
2. **Paper Screening** - AI-powered screening with dual-review (or single-pass in fast mode)
3. **Data Extraction** - Extracts structured data with triple-review (or single-pass in fast mode)
4. **Statistical Analysis** - Recommends tests and performs meta-analysis if feasible
5. **PRISMA Diagram** - Generates publication-ready flow diagram
6. **Introduction Writing** - AI-generated background, rationale, and objectives
7. **Results Writing** - AI-generated study selection and synthesis

### Command Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--question` | `-q` | *required* | Research question for the systematic review |
| `--include` | `-i` | *required* | Inclusion criteria (comma-separated) |
| `--exclude` | `-e` | `""` | Exclusion criteria (comma-separated) |
| `--databases` | `-d` | `pubmed` | Databases to search (comma-separated) |
| `--max-results` | `-n` | `20` | Maximum results per database |
| `--output` | `-o` | `./workflow_output` | Output directory for all files |
| `--fast` | | `False` | Fast mode: single-pass screening & extraction |
| `--skip-analysis` | | `False` | Skip statistical analysis stage |
| `--skip-writing` | | `False` | Skip manuscript writing stages |

### Output Files

The workflow creates the following files in the output directory:

```
my_review/
├── 1_search_results.json          # Papers found from literature search
├── 2_screening_decisions.json     # Screening decisions for each paper
├── 3_extraction_results.json      # Extracted structured data
├── 4_analysis_results.json        # Statistical analysis results
├── 5_prisma_diagram.png           # PRISMA 2020 flow diagram (300 DPI)
├── 6_introduction.md              # Introduction section
├── 7_results.md                   # Results section
└── workflow_summary.json          # Complete workflow metadata
```

### Examples

#### Basic Workflow

```bash
arakis workflow \
  --question "Effect of metformin on cardiovascular outcomes in diabetes" \
  --include "Type 2 diabetes,Metformin,Cardiovascular outcomes,RCTs" \
  --exclude "Type 1 diabetes,Animal studies" \
  --output ./metformin_review
```

#### Fast Mode (Single-Pass)

Use `--fast` for quicker results with lower cost but reduced reliability:

```bash
arakis workflow \
  --question "Efficacy of statins in primary prevention" \
  --include "Primary prevention,Statins,Cardiovascular events" \
  --exclude "Secondary prevention" \
  --output ./statins_review \
  --fast
```

**Cost comparison:**
- Standard mode: ~$2.50 for 20 papers (dual-review screening + triple-review extraction)
- Fast mode: ~$1.20 for 20 papers (single-pass screening + single-pass extraction)

#### Multi-Database Search

```bash
arakis workflow \
  --question "Impact of exercise on depression in elderly" \
  --include "Elderly adults,Exercise intervention,Depression outcomes" \
  --exclude "Children,Adolescents" \
  --databases "pubmed,openalex,semantic_scholar" \
  --max-results 50 \
  --output ./exercise_depression
```

#### Skip Stages

Skip analysis and writing if you only need search and screening:

```bash
arakis workflow \
  --question "Prevalence of chronic kidney disease in hypertension" \
  --include "Hypertension,Chronic kidney disease" \
  --exclude "Acute kidney injury" \
  --output ./ckd_screening \
  --skip-analysis \
  --skip-writing
```

### Performance

Typical workflow times (based on `--fast` mode):

| Papers Found | Duration | Estimated Cost |
|-------------|----------|----------------|
| 10-20 papers | 2-3 min | $1.20-1.50 |
| 20-50 papers | 3-5 min | $1.50-2.50 |
| 50-100 papers | 5-10 min | $2.50-4.00 |

**Note:** Standard mode (dual/triple-review) takes ~2x longer and costs ~2x more, but provides higher quality results.

### Quality Modes

#### Standard Mode (Recommended)

- **Screening**: Dual-review with conflict detection
- **Extraction**: Triple-review with majority voting
- **Best for**: Publication-ready systematic reviews
- **Cost**: ~$2.50 for 20 papers

```bash
arakis workflow --question "..." --include "..." --output ./review
```

#### Fast Mode

- **Screening**: Single-pass AI decision
- **Extraction**: Single-pass data extraction
- **Best for**: Exploratory reviews, rapid assessments
- **Cost**: ~$1.20 for 20 papers

```bash
arakis workflow --question "..." --include "..." --output ./review --fast
```

### Workflow Summary

After completion, check `workflow_summary.json` for:

- Total duration and cost
- Papers found, included, and extracted
- File paths for all outputs
- Stage-specific metrics

```bash
cat my_review/workflow_summary.json | jq
```

### Next Steps

After running the workflow:

1. **Review screening decisions**: Check `2_screening_decisions.json` for conflicts or "maybe" papers
2. **Verify extracted data**: Review `3_extraction_results.json` for low-quality extractions
3. **Check PRISMA diagram**: View `5_prisma_diagram.png` to ensure flow is correct
4. **Edit manuscript sections**: Refine `6_introduction.md` and `7_results.md` as needed

### Troubleshooting

**No papers found:**
- Try broader inclusion criteria
- Increase `--max-results`
- Add more databases with `--databases`

**No papers included after screening:**
- Review exclusion criteria - may be too strict
- Check `2_screening_decisions.json` for exclusion reasons
- Consider adjusting inclusion/exclusion criteria

**Low extraction quality:**
- Check that papers contain the expected data fields
- Review papers with `needs_human_review: true`
- Consider using standard mode instead of `--fast`

**Meta-analysis not feasible:**
- Ensure papers report compatible outcome measures
- Check that sample sizes and statistics are reported
- May need more homogeneous studies

### API Keys Required

Set these environment variables before running:

```bash
export OPENAI_API_KEY="sk-..."        # Required for all AI features
export UNPAYWALL_EMAIL="you@email.com"  # Required for PDF retrieval
export NCBI_API_KEY="..."             # Optional: faster PubMed access
```

### Cost Breakdown

Typical costs per stage (20 papers):

| Stage | Standard Mode | Fast Mode |
|-------|--------------|-----------|
| Search | $0.00 (free) | $0.00 (free) |
| Screening | $0.60 | $0.30 |
| Extraction | $1.00 | $0.40 |
| Analysis | $0.20 | $0.20 |
| Writing | $1.70 | $1.70 |
| **Total** | **~$3.50** | **~$2.60** |

**Note:** Costs vary based on paper length and number of papers proceeding through each stage.

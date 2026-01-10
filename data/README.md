# Data Directory

This directory contains sample output files and data generated during systematic review workflows.

## Purpose

The `data/` directory is used for:
- JSON output files from search, screening, and extraction
- Sample datasets for testing and examples
- Temporary workflow outputs
- CSV exports of results

## Gitignore

**Note:** This directory is excluded from version control via `.gitignore`. Output files (`*.json`, `*.csv`, `*.pdf`) in this directory will not be committed to git.

## Contents

After running example workflows, you may find:

- `search_results.json` - Papers found during literature search
- `screening_results.json` - Screening decisions for papers
- `extractions.json` - Structured data extracted from papers
- `analysis_results.json` - Statistical analysis outputs
- Other workflow-specific outputs

## Cleanup

To clean up data files:

```bash
# Remove all JSON outputs
rm data/*.json

# Remove all CSV exports
rm data/*.csv

# Remove all PDFs
rm data/*.pdf
```

## Production Use

For production deployments:
- Use a dedicated object storage service (S3, MinIO) for PDFs
- Use PostgreSQL database for structured data
- Configure backups for important datasets

See [Database Setup Guide](../docs/deployment/DATABASE_SETUP.md) for production data management.

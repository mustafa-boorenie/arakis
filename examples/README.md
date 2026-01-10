# Arakis Examples

This directory contains example scripts and demonstrations of Arakis capabilities.

## Demo Scripts

### demo_systematic_review.py

Complete end-to-end systematic review demonstration that:
- Searches PubMed for papers on a research question
- Screens papers using AI with inclusion/exclusion criteria
- Extracts structured data from included papers
- Performs statistical analysis
- Generates PRISMA flow diagrams and forest plots
- Writes manuscript sections

**Usage:**
```bash
python examples/demo_systematic_review.py
```

**Note:** Requires OpenAI API key in `.env` file.

### demo_human_review.py

Demonstrates human-in-the-loop review workflow that:
- Performs initial AI screening (single-pass mode)
- Prompts human reviewers to verify AI decisions
- Tracks human review outcomes
- Resolves conflicts between AI and human decisions

**Usage:**
```bash
python examples/demo_human_review.py
```

## Running Examples

1. **Install Arakis:**
   ```bash
   pip install -e .
   ```

2. **Configure API keys:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run any example:**
   ```bash
   python examples/demo_systematic_review.py
   ```

## More Examples

For more code examples and usage patterns, see:
- [Quick Start Guide](../docs/guides/QUICK_START.md)
- [Examples Documentation](../docs/guides/EXAMPLES.md)
- [Workflow Guide](../docs/guides/WORKFLOW_GUIDE.md)

## Creating Your Own Scripts

Use these examples as templates for your own systematic review automation:

1. Copy a demo script to your project directory
2. Modify the research question, criteria, and parameters
3. Adjust the output paths and formats
4. Run and iterate on your workflow

## Support

- Questions about examples: See [EXAMPLES.md](../docs/guides/EXAMPLES.md)
- API documentation: See [API_REFERENCE.md](../docs/api/API_REFERENCE.md)
- Issues: [GitHub Issues](https://github.com/mustafa-boorenie/arakis/issues)

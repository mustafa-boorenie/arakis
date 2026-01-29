"""Model configurations for writing agents.

This module defines the model configurations used across all writing agents.
Uses OpenAI's extended thinking models (o1) for high-quality reasoning.
"""

# Extended thinking models for complex writing tasks
# o1 is OpenAI's current extended thinking model with deep reasoning capabilities
REASONING_MODEL = "o1"  # Default reasoning model with extended thinking
REASONING_MODEL_PRO = "o1"  # Same as REASONING_MODEL (o1 is the most capable)

# Fast model for simpler tasks
FAST_MODEL = "gpt-4o"

# Screening and extraction models (can use faster models)
SCREENING_MODEL = "gpt-4o"
EXTRACTION_MODEL = "gpt-4o"

# Default model for writing tasks
DEFAULT_WRITING_MODEL = REASONING_MODEL

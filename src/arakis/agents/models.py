"""Model configurations for writing agents.

This module defines the model configurations used across all writing agents.
Uses OpenAI's extended thinking models (o3/o3-pro) for high-quality reasoning.
"""

# Extended thinking models for complex writing tasks
REASONING_MODEL = "o3"  # Default reasoning model
REASONING_MODEL_PRO = "o3-pro"  # More thorough reasoning (slower, more reliable)

# Fast model for simpler tasks
FAST_MODEL = "gpt-4o"

# Screening and extraction models (can use faster models)
SCREENING_MODEL = "gpt-4o"
EXTRACTION_MODEL = "gpt-4o"

# Default model for writing tasks
DEFAULT_WRITING_MODEL = REASONING_MODEL

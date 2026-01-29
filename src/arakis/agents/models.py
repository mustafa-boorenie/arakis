"""Model configurations for agents.

This module defines the model configurations used across all agents.
Supports both legacy static configs and new dynamic cost mode configs.
"""

# Legacy model definitions (for backward compatibility)
# These are overridden by cost mode configuration when in use

# Extended thinking models for complex writing tasks
REASONING_MODEL = "o3-mini"  # Default reasoning model
REASONING_MODEL_PRO = "gpt-5.2-2025-12-11"  # High-quality reasoning with max effort

# Fast model for simpler tasks
FAST_MODEL = "gpt-5-nano"

# Screening and extraction models (overridden by cost mode)
SCREENING_MODEL = "gpt-5-nano"
EXTRACTION_MODEL = "gpt-5-nano"

# Quality mode models
QUALITY_SCREENING_MODEL = "gpt-5-mini"
QUALITY_EXTRACTION_MODEL = "gpt-5-mini"
QUALITY_WRITING_MODEL = "gpt-5.2-2025-12-11"

# Default model for writing tasks
DEFAULT_WRITING_MODEL = REASONING_MODEL


# Model pricing (approximate, per 1M tokens)
# Used for cost estimation
MODEL_PRICING = {
    "o1": {"input": 15.00, "output": 60.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5-mini": {"input": 0.50, "output": 2.00},  # Estimated
    "gpt-5-nano": {"input": 0.10, "output": 0.40},  # Estimated
    "gpt-5.2-2025-12-11": {"input": 10.00, "output": 30.00},  # Estimated with max reasoning
}


def get_model_pricing(model: str) -> dict[str, float]:
    """Get pricing for a model.
    
    Args:
        model: Model name
        
    Returns:
        Dict with input and output pricing per 1M tokens
    """
    return MODEL_PRICING.get(model, {"input": 2.50, "output": 10.00})  # Default to gpt-4o pricing


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate API cost for a call.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name
        
    Returns:
        Estimated cost in USD
    """
    pricing = get_model_pricing(model)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost

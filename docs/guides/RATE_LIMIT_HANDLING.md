# Rate Limit Handling Implementation

## Overview

Added automatic retry logic with exponential backoff for OpenAI API calls to handle rate limiting gracefully. This prevents the CLI from crashing when hitting OpenAI's rate limits during search and screening operations.

## Problem

Previously, when Arakis hit OpenAI's rate limits during query generation or screening, the application would crash with:
```
Error: RetryError[<Future ... raised RateLimitError>]
```

This occurred during:
- Query generation (research question → database-specific queries)
- Query validation
- Query refinement
- Paper screening

## Solution

### 1. Retry Decorator (`src/arakis/utils.py`)

Created a reusable `@retry_with_exponential_backoff` decorator that:
- Automatically retries on `RateLimitError` and transient `APIError` (5xx)
- Uses exponential backoff with jitter to prevent thundering herd
- Displays user-friendly progress messages
- Configurable retry parameters

**Default configuration:**
- Max retries: 5
- Initial delay: 1 second
- Max delay: 60 seconds
- Exponential base: 2.0
- Jitter: Enabled (0.5-1.5x randomization)

**Example backoff pattern:**
```
Attempt 1: Fail → Wait ~1s (1.0s ± jitter)
Attempt 2: Fail → Wait ~2s (2.0s ± jitter)
Attempt 3: Fail → Wait ~4s (4.0s ± jitter)
Attempt 4: Fail → Wait ~8s (8.0s ± jitter)
Attempt 5: Fail → Wait ~16s (16.0s ± jitter)
Attempt 6: Fail → Give up, raise error
```

### 2. QueryGeneratorAgent Updates (`src/arakis/agents/query_generator.py`)

Added `_call_openai()` wrapper method with retry decorator:
```python
@retry_with_exponential_backoff(max_retries=5, initial_delay=1.0)
async def _call_openai(self, messages: list[dict], tools: list | None = None):
    """Call OpenAI API with retry logic for rate limits."""
    # ...
```

Updated all OpenAI calls to use the wrapper:
- `generate_queries()` - Main query generation
- `_generate_additional_queries()` - Additional queries when needed
- `refine_query()` - Query refinement

### 3. ScreeningAgent Updates (`src/arakis/agents/screener.py`)

Added similar `_call_openai()` wrapper with retry decorator:
```python
@retry_with_exponential_backoff(max_retries=5, initial_delay=1.0)
async def _call_openai(
    self,
    messages: list[dict],
    tools: list | None = None,
    tool_choice: dict | str = "auto",
    temperature: float = 0.3
):
    """Call OpenAI API with retry logic for rate limits."""
    # ...
```

Updated screening call:
- `_single_screen()` - Paper screening with AI

## User Experience

### Before
```bash
$ arakis search "catheter-associated UTI"
Error: RetryError[<Future ... raised RateLimitError>]
```
**Result:** Crash, no results, user must wait and retry manually

### After
```bash
$ arakis search "catheter-associated UTI"
Rate limit hit. Retrying in 1.2s (attempt 1/5)...
Rate limit hit. Retrying in 2.1s (attempt 2/5)...
[continues with search...]
```
**Result:** Automatic retry, eventual success, no manual intervention needed

## Benefits

1. **Resilience**: Gracefully handles rate limits without crashing
2. **User-friendly**: Clear progress messages during retries
3. **Automatic**: No manual intervention required
4. **Configurable**: Easy to adjust retry parameters if needed
5. **Smart backoff**: Exponential with jitter prevents overwhelming the API

## Testing

Created `test_retry_logic.py` to verify:
- ✅ Retries on rate limit errors
- ✅ Eventually succeeds after retries
- ✅ Uses exponential backoff
- ✅ Displays progress messages

**Test output:**
```
Attempt 1: Simulating rate limit error...
Rate limit hit. Retrying in 1.0s (attempt 1/5)...
Attempt 2: Simulating rate limit error...
Rate limit hit. Retrying in 2.1s (attempt 2/5)...
Attempt 3: Success!
✓ Test passed: Retry logic works correctly
```

## Rate Limit Recommendations

### OpenAI Tier Limits
- **Free tier**: Very limited (3 RPM)
- **Tier 1**: 500 RPM, 30,000 TPM
- **Tier 2**: 5,000 RPM, 450,000 TPM
- **Higher tiers**: See https://platform.openai.com/docs/guides/rate-limits

### For Heavy Usage
If you frequently hit rate limits:

1. **Upgrade OpenAI tier**: Higher tiers = higher limits
2. **Reduce concurrent operations**: Process fewer papers at once
3. **Use caching**: Cache query generation results
4. **Batch operations**: Use larger batches with lower frequency

### Monitoring
Check your OpenAI usage:
```bash
# Visit OpenAI dashboard
open https://platform.openai.com/usage
```

## Configuration

To customize retry behavior, modify the decorator parameters in `utils.py`:

```python
@retry_with_exponential_backoff(
    max_retries=10,        # More retries
    initial_delay=2.0,     # Start with longer delay
    max_delay=120.0,       # Allow longer max wait
    exponential_base=2.0,  # Default exponential growth
    jitter=True,           # Add randomization
)
```

## Error Handling

The retry logic handles:
- **RateLimitError**: Retry with backoff (429 status)
- **APIError (5xx)**: Retry for server errors
- **APIError (4xx)**: Don't retry (client errors like invalid auth)
- **Other exceptions**: Don't retry (propagate immediately)

## Backward Compatibility

✅ **Fully backward compatible**
- No breaking changes to API
- Existing code works without modification
- Retry behavior is transparent to callers

## Files Changed

1. **Created**: `src/arakis/utils.py` - Retry decorator utility
2. **Modified**: `src/arakis/agents/query_generator.py` - Added retry wrapper
3. **Modified**: `src/arakis/agents/screener.py` - Added retry wrapper
4. **Created**: `test_retry_logic.py` - Unit tests
5. **Created**: `RATE_LIMIT_HANDLING.md` - This documentation

## Future Enhancements

Potential improvements:
- [ ] Adaptive backoff based on retry-after headers
- [ ] Per-operation retry configuration
- [ ] Metrics tracking (retry count, success rate)
- [ ] Circuit breaker pattern for persistent failures
- [ ] Local caching to reduce API calls

## Conclusion

The rate limit handling implementation makes Arakis more robust and user-friendly by automatically recovering from OpenAI rate limits without manual intervention or crashes.

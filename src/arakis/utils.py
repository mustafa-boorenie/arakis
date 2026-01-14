"""Utility functions for Arakis."""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from openai import APIError, RateLimitError
from rich.console import Console

console = Console()

T = TypeVar("T")


class RateLimiter:
    """Simple rate limiter to prevent hitting API limits."""

    def __init__(self, calls_per_minute: int = 3):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call = 0.0
        self._lock = None
        self._loop = None

    def _get_lock(self):
        """Get or create lock for current event loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # Create new lock if we don't have one or we're in a different event loop
        if self._lock is None or self._loop != current_loop:
            self._lock = asyncio.Lock()
            self._loop = current_loop
        return self._lock

    async def wait(self):
        """Wait if necessary to respect rate limit."""
        async with self._get_lock():
            now = time.time()
            time_since_last = now - self.last_call

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_call = time.time()


# Global rate limiter for OpenAI calls
# Will be initialized with config settings on first use
_openai_rate_limiter = None


def get_openai_rate_limiter() -> RateLimiter:
    """Get or create the global OpenAI rate limiter."""
    global _openai_rate_limiter
    if _openai_rate_limiter is None:
        from arakis.config import get_settings

        settings = get_settings()
        _openai_rate_limiter = RateLimiter(calls_per_minute=settings.openai_requests_per_minute)
    return _openai_rate_limiter


def retry_with_exponential_backoff(
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    use_rate_limiter: bool = True,
) -> Callable:
    """
    Decorator to retry async functions with exponential backoff.

    Handles OpenAI rate limits and transient errors gracefully.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        use_rate_limiter: Use global rate limiter to prevent hitting limits

    Returns:
        Decorated function that retries on errors
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                # Proactive rate limiting before making call
                if use_rate_limiter:
                    await get_openai_rate_limiter().wait()

                try:
                    return await func(*args, **kwargs)

                except RateLimitError as e:
                    last_exception = e
                    if attempt == max_retries:
                        console.print(
                            f"[red]Rate limit exceeded after {max_retries} retries. Please wait a few minutes.[/red]"
                        )
                        raise

                    # Add jitter to prevent synchronized retries
                    actual_delay = delay
                    if jitter:
                        import random

                        actual_delay = delay * (0.5 + random.random())

                    console.print(
                        f"[yellow]Rate limit hit. Retrying in {actual_delay:.1f}s (attempt {attempt + 1}/{max_retries})...[/yellow]"
                    )
                    await asyncio.sleep(actual_delay)

                    # Exponential backoff
                    delay = min(delay * exponential_base, max_delay)

                except APIError as e:
                    last_exception = e
                    # For server errors (5xx), retry
                    if hasattr(e, "status_code") and 500 <= e.status_code < 600:
                        if attempt == max_retries:
                            console.print(f"[red]API error after {max_retries} retries: {e}[/red]")
                            raise

                        actual_delay = delay
                        if jitter:
                            import random

                            actual_delay = delay * (0.5 + random.random())

                        console.print(
                            f"[yellow]API error. Retrying in {actual_delay:.1f}s (attempt {attempt + 1}/{max_retries})...[/yellow]"
                        )
                        await asyncio.sleep(actual_delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        # For client errors (4xx), don't retry
                        raise

                except Exception:
                    # For other exceptions, don't retry
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator

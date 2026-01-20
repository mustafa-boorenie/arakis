"""Utility functions for Arakis."""

import asyncio
import random
import time
from collections.abc import Awaitable
from functools import wraps
from typing import Any, Callable, TypeVar

import httpx
from openai import APIError, RateLimitError
from rich.console import Console

console = Console()

T = TypeVar("T")
R = TypeVar("R")


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


def retry_http_request(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Callable:
    """
    Decorator to retry async HTTP functions with exponential backoff.

    Designed for httpx-based HTTP requests in retrieval sources.
    Handles rate limits (429) and transient server errors (5xx).

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retry_on_status: HTTP status codes that trigger a retry

    Returns:
        Decorated function that retries on transient errors
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except httpx.HTTPStatusError as e:
                    last_exception = e
                    if e.response.status_code in retry_on_status:
                        if attempt == max_retries:
                            raise

                        # Add jitter to prevent synchronized retries
                        actual_delay = delay * (0.5 + random.random())
                        await asyncio.sleep(actual_delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        # Non-retryable status code
                        raise

                except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    # Network errors are retryable
                    last_exception = e
                    if attempt == max_retries:
                        raise

                    actual_delay = delay * (0.5 + random.random())
                    await asyncio.sleep(actual_delay)
                    delay = min(delay * exponential_base, max_delay)

                except httpx.HTTPError:
                    # Other HTTP errors - don't retry
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


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


async def process_batch_concurrent(
    items: list[T],
    process_func: Callable[[T], Awaitable[R]],
    batch_size: int,
    progress_callback: Callable[[int, int, T, R], None] | None = None,
) -> list[R]:
    """
    Process items in concurrent batches with configurable batch size.

    This utility processes items concurrently within each batch while maintaining
    order and providing progress tracking. Rate limiting is handled by the individual
    process functions (via @retry_with_exponential_backoff decorator).

    Args:
        items: List of items to process
        process_func: Async function that processes a single item and returns a result
        batch_size: Number of items to process concurrently in each batch
        progress_callback: Optional callback(current, total, item, result) for progress updates.
            Called after each item completes (may be out of order within batch).

    Returns:
        List of results in the same order as input items

    Example:
        async def screen_paper(paper):
            return await screener.screen_paper(paper, criteria)

        results = await process_batch_concurrent(
            papers,
            screen_paper,
            batch_size=5,
            progress_callback=lambda c, t, p, r: print(f"{c}/{t}: {r.status}")
        )
    """
    results: list[R] = []
    total = len(items)
    completed = 0

    # Process items in batches
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_items = items[batch_start:batch_end]

        # Create tasks for concurrent processing within batch
        async def process_with_index(index: int, item: T) -> tuple[int, T, R]:
            result = await process_func(item)
            return (index, item, result)

        tasks = [process_with_index(batch_start + i, item) for i, item in enumerate(batch_items)]

        # Process batch concurrently and collect results as they complete
        batch_results: dict[int, R] = {}
        for coro in asyncio.as_completed(tasks):
            index, item, result = await coro
            batch_results[index] = result
            completed += 1

            # Call progress callback if provided
            if progress_callback:
                progress_callback(completed, total, item, result)

        # Add results in order
        for i in range(batch_start, batch_end):
            results.append(batch_results[i])

    return results


class BatchProcessor:
    """
    Configurable batch processor for async operations.

    Provides a reusable interface for processing items in batches with:
    - Configurable batch size from settings or override
    - Progress tracking with callbacks
    - Result ordering preserved
    - Integration with rate limiting

    Example:
        processor = BatchProcessor(batch_size=5)

        async def process_paper(paper):
            return await agent.screen_paper(paper, criteria)

        results = await processor.process(papers, process_paper, progress_callback)
    """

    def __init__(self, batch_size: int | None = None, batch_size_key: str | None = None):
        """
        Initialize batch processor.

        Args:
            batch_size: Explicit batch size to use. Takes precedence over batch_size_key.
            batch_size_key: Settings attribute name to get batch size from config
                           (e.g., "batch_size_screening", "batch_size_extraction").
                           Used when batch_size is None.
        """
        self._explicit_batch_size = batch_size
        self._batch_size_key = batch_size_key

    @property
    def batch_size(self) -> int:
        """Get the effective batch size."""
        if self._explicit_batch_size is not None:
            return self._explicit_batch_size

        if self._batch_size_key:
            from arakis.config import get_settings

            settings = get_settings()
            return getattr(settings, self._batch_size_key, 5)

        return 5  # Default

    async def process(
        self,
        items: list[T],
        process_func: Callable[[T], Awaitable[R]],
        progress_callback: Callable[[int, int, T, R], None] | None = None,
    ) -> list[R]:
        """
        Process items in concurrent batches.

        Args:
            items: List of items to process
            process_func: Async function to process each item
            progress_callback: Optional callback(current, total, item, result)

        Returns:
            List of results in same order as input
        """
        return await process_batch_concurrent(
            items=items,
            process_func=process_func,
            batch_size=self.batch_size,
            progress_callback=progress_callback,
        )

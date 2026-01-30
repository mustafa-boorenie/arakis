"""Rate limiting for API endpoints.

Provides rate limiting with Redis backend (production) and in-memory fallback (development).
Uses sliding window algorithm for accurate rate limiting.
"""

import asyncio
import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from arakis.config import get_settings


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""

    requests: int  # Number of requests allowed
    window_seconds: int  # Time window in seconds
    key_prefix: str = ""  # Prefix for the rate limit key


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )
        self.retry_after = retry_after


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window algorithm.

    Suitable for development and single-instance deployments.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier for the rate limit (e.g., IP address)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            # Clean up old requests
            self._requests[key] = [
                req_time for req_time in self._requests[key] if req_time > window_start
            ]

            current_count = len(self._requests[key])

            if current_count >= limit:
                # Calculate retry-after time
                oldest_request = min(self._requests[key]) if self._requests[key] else now
                retry_after = int(oldest_request + window_seconds - now) + 1
                return False, 0, max(retry_after, 1)

            # Add current request
            self._requests[key].append(now)
            remaining = limit - current_count - 1

            return True, remaining, 0

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        async with self._lock:
            self._requests.pop(key, None)

    async def cleanup(self) -> int:
        """Remove expired entries. Returns number of cleaned entries."""
        now = time.time()
        cleaned = 0

        async with self._lock:
            keys_to_remove = []
            for key, requests in self._requests.items():
                # Remove entries older than 1 hour (max reasonable window)
                self._requests[key] = [r for r in requests if r > now - 3600]
                if not self._requests[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]
                cleaned += 1

        return cleaned


class RedisRateLimiter:
    """Redis-backed rate limiter using sliding window algorithm.

    Suitable for production multi-instance deployments.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def connect(self) -> bool:
        """Connect to Redis. Returns True if successful."""
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            return True
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            self._redis = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Uses Redis sorted sets for sliding window implementation.
        """
        if not self._redis:
            # Fallback: allow all if Redis is not connected
            return True, limit, 0

        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"

        try:
            pipe = self._redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count current requests in window
            pipe.zcard(redis_key)

            # Add current request (will be undone if over limit)
            pipe.zadd(redis_key, {f"{now}": now})

            # Set expiry on the key
            pipe.expire(redis_key, window_seconds + 1)

            results = await pipe.execute()
            current_count = results[1]

            if current_count >= limit:
                # Remove the request we just added
                await self._redis.zrem(redis_key, f"{now}")

                # Get oldest request to calculate retry-after
                oldest = await self._redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(oldest_time + window_seconds - now) + 1
                else:
                    retry_after = window_seconds

                return False, 0, max(retry_after, 1)

            remaining = limit - current_count - 1
            return True, remaining, 0

        except Exception as e:
            print(f"⚠️ Redis rate limit error: {e}")
            # Fallback: allow request on Redis errors
            return True, limit, 0

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if self._redis:
            try:
                await self._redis.delete(f"ratelimit:{key}")
            except Exception:
                pass


class RateLimiter:
    """
    Main rate limiter with automatic backend selection.

    Uses Redis if available, falls back to in-memory.
    """

    def __init__(self):
        self._redis_limiter: Optional[RedisRateLimiter] = None
        self._memory_limiter = InMemoryRateLimiter()
        self._use_redis = False

    async def initialize(self) -> None:
        """Initialize rate limiter with Redis if available."""
        settings = get_settings()

        if settings.redis_url:
            self._redis_limiter = RedisRateLimiter(settings.redis_url)
            self._use_redis = await self._redis_limiter.connect()

            if self._use_redis:
                print("✅ Rate limiter: Redis backend connected")
            else:
                print("⚠️ Rate limiter: Falling back to in-memory backend")
        else:
            print("ℹ️ Rate limiter: Using in-memory backend (no Redis configured)")

    async def shutdown(self) -> None:
        """Shutdown rate limiter connections."""
        if self._redis_limiter:
            await self._redis_limiter.disconnect()

    async def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """Check if request is allowed."""
        if self._use_redis and self._redis_limiter:
            return await self._redis_limiter.is_allowed(key, limit, window_seconds)
        return await self._memory_limiter.is_allowed(key, limit, window_seconds)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if self._use_redis and self._redis_limiter:
            await self._redis_limiter.reset(key)
        await self._memory_limiter.reset(key)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
        await _rate_limiter.initialize()
    return _rate_limiter


async def shutdown_rate_limiter() -> None:
    """Shutdown the global rate limiter."""
    global _rate_limiter
    if _rate_limiter:
        await _rate_limiter.shutdown()
        _rate_limiter = None


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    # Check X-Forwarded-For header (set by reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def hash_key(key: str) -> str:
    """Hash a key for privacy (e.g., IP addresses in logs)."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def rate_limit(
    requests: int = 10,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
    error_message: str = "Too many requests. Please try again later.",
):
    """
    Decorator for rate limiting endpoints.

    Args:
        requests: Maximum number of requests allowed in the window
        window_seconds: Time window in seconds
        key_func: Optional function to generate rate limit key from request.
                  Defaults to client IP address.
        error_message: Message to return when rate limit is exceeded

    Usage:
        @router.post("/login")
        @rate_limit(requests=5, window_seconds=60)
        async def login(request: Request):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the Request object in args or kwargs
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                # No request object found, skip rate limiting
                return await func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                key = get_client_ip(request)

            # Add endpoint to key to have per-endpoint limits
            endpoint_key = f"{request.url.path}:{key}"

            # Check rate limit
            limiter = await get_rate_limiter()
            allowed, remaining, retry_after = await limiter.is_allowed(
                endpoint_key, requests, window_seconds
            )

            if not allowed:
                raise RateLimitExceeded(
                    retry_after=retry_after,
                    detail=f"{error_message} Try again in {retry_after} seconds.",
                )

            # Execute the endpoint
            response = await func(*args, **kwargs)

            return response

        return wrapper

    return decorator


# Pre-configured rate limits for common scenarios
AUTH_RATE_LIMIT = rate_limit(
    requests=10,
    window_seconds=60,
    error_message="Too many authentication attempts.",
)

LOGIN_RATE_LIMIT = rate_limit(
    requests=5,
    window_seconds=60,
    error_message="Too many login attempts.",
)

TOKEN_REFRESH_RATE_LIMIT = rate_limit(
    requests=10,
    window_seconds=60,
    error_message="Too many token refresh attempts.",
)

OAUTH_RATE_LIMIT = rate_limit(
    requests=10,
    window_seconds=300,  # 5 minutes
    error_message="Too many OAuth attempts.",
)

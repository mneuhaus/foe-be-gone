"""Rate limiting utilities for API calls."""

import asyncio
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0, burst: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second (e.g., 0.5 = 1 call every 2 seconds)
            burst: Maximum burst size (calls that can be made immediately)
        """
        self.calls_per_second = calls_per_second
        self.interval = 1.0 / calls_per_second  # Time between calls in seconds
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a call. Will wait if rate limit is exceeded."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on time elapsed
            self.tokens = min(self.burst, self.tokens + elapsed * self.calls_per_second)
            
            if self.tokens < 1:
                # Need to wait
                wait_time = (1 - self.tokens) / self.calls_per_second
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1
            
            self.tokens -= 1


class PerResourceRateLimiter:
    """Rate limiter that tracks limits per resource (e.g., per integration)."""
    
    def __init__(self, default_calls_per_second: float = 1.0, default_burst: int = 1):
        """
        Initialize per-resource rate limiter.
        
        Args:
            default_calls_per_second: Default maximum calls per second
            default_burst: Default burst size
        """
        self.default_calls_per_second = default_calls_per_second
        self.default_burst = default_burst
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
    
    async def acquire(self, resource_id: str, 
                     calls_per_second: Optional[float] = None,
                     burst: Optional[int] = None):
        """
        Acquire permission for a specific resource.
        
        Args:
            resource_id: Unique identifier for the resource
            calls_per_second: Override default calls per second for this resource
            burst: Override default burst for this resource
        """
        async with self._lock:
            if resource_id not in self._limiters:
                cps = calls_per_second or self.default_calls_per_second
                b = burst or self.default_burst
                self._limiters[resource_id] = RateLimiter(cps, b)
        
        await self._limiters[resource_id].acquire()


# Global rate limiters
camera_rate_limiter = PerResourceRateLimiter(
    default_calls_per_second=0.5,  # 1 call every 2 seconds per integration
    default_burst=3  # Allow 3 immediate calls
)
"""
In-Memory Cache Module for CP Coach.

Provides thread-safe caching with TTL support per CF handle.
Prevents duplicate API calls for the same handle within cache window.
"""

import threading
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

from .config import CACHE_TTL_SECONDS, CACHE_MAX_ENTRIES

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with data and expiry time."""
    data: Any
    expires_at: float
    created_at: float


class HandleCache:
    """
    Thread-safe in-memory cache for CF handle data.
    
    Features:
    - TTL-based expiration (default 6 hours)
    - Thread-safe operations
    - Automatic cleanup of expired entries
    - Max entries limit with LRU-like eviction
    """
    
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS, max_entries: int = CACHE_MAX_ENTRIES):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._access_order: Dict[str, float] = {}  # For LRU tracking
    
    def get(self, handle: str) -> Tuple[Optional[Any], bool]:
        """
        Get cached data for a handle.
        
        Args:
            handle: CF handle (case-insensitive)
            
        Returns:
            Tuple of (data, cache_hit). If cache miss or expired, returns (None, False).
        """
        key = handle.lower()
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                logger.debug(f"Cache MISS for handle: {handle}")
                return None, False
            
            # Check expiration
            if time.time() > entry.expires_at:
                logger.debug(f"Cache EXPIRED for handle: {handle}")
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                return None, False
            
            # Update access time for LRU
            self._access_order[key] = time.time()
            logger.debug(f"Cache HIT for handle: {handle}")
            return entry.data, True
    
    def set(self, handle: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Cache data for a handle.
        
        Args:
            handle: CF handle (case-insensitive)
            data: Data to cache
            ttl: Optional custom TTL in seconds (uses default if None)
        """
        key = handle.lower()
        ttl_seconds = ttl if ttl is not None else self._ttl
        now = time.time()
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(
                data=data,
                expires_at=now + ttl_seconds,
                created_at=now
            )
            self._access_order[key] = now
            logger.debug(f"Cache SET for handle: {handle}, TTL: {ttl_seconds}s")
    
    def invalidate(self, handle: str) -> bool:
        """
        Remove cached data for a handle.
        
        Args:
            handle: CF handle (case-insensitive)
            
        Returns:
            True if entry was removed, False if not found
        """
        key = handle.lower()
        
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                logger.debug(f"Cache INVALIDATED for handle: {handle}")
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear all cached entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            logger.info(f"Cache CLEARED: {count} entries removed")
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        removed = 0
        
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() 
                if now > v.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    del self._access_order[key]
                removed += 1
        
        if removed > 0:
            logger.info(f"Cache CLEANUP: {removed} expired entries removed")
        return removed
    
    def _evict_oldest(self) -> None:
        """Evict the least recently accessed entry."""
        if not self._access_order:
            return
        
        oldest_key = min(self._access_order, key=self._access_order.get)
        if oldest_key in self._cache:
            del self._cache[oldest_key]
        del self._access_order[oldest_key]
        logger.debug(f"Cache EVICTED oldest entry: {oldest_key}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = time.time()
            active = sum(1 for v in self._cache.values() if now <= v.expires_at)
            expired = len(self._cache) - active
            
            return {
                "total_entries": len(self._cache),
                "active_entries": active,
                "expired_entries": expired,
                "max_entries": self._max_entries,
                "ttl_seconds": self._ttl
            }


# Global cache instances
user_data_cache = HandleCache()
analysis_cache = HandleCache()
recommendation_cache = HandleCache(ttl_seconds=300)  # 5 min for recommendations

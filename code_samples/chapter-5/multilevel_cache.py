"""
Comprehensive Multi-Level Caching System for Enterprise Applications

This module implements a sophisticated caching architecture supporting multiple
cache levels, intelligent invalidation, and high-performance operations suitable
for production systems at companies like Lawstronaut (legal document caching)
and Optimizely (personalization data caching).

Key features:
- Multi-level cache hierarchy (L1: In-memory, L2: Redis, L3: Database)
- Intelligent cache warming and eviction policies
- Cache coherence and invalidation strategies
- Performance monitoring and analytics
- Distributed cache coordination

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import time
import threading
import hashlib
import pickle
import logging
import statistics
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import weakref

# Third-party imports (would be available in production)
# import redis
# import aioredis

# =============================================================================
# CACHE INTERFACES AND BASE CLASSES
# =============================================================================

class CacheInterface(ABC):
    """Abstract interface for cache implementations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def update_access(self) -> None:
        """Update access statistics"""
        self.accessed_at = time.time()
        self.access_count += 1

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.hits + self.misses
        return self.hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate

# =============================================================================
# IN-MEMORY CACHE IMPLEMENTATION (L1 CACHE)
# =============================================================================

class InMemoryCache(CacheInterface):
    """High-performance in-memory cache with LRU eviction"""
    
    def __init__(self, max_size: int = 10000, max_memory_mb: int = 100,
                 default_ttl: Optional[int] = 3600):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._stats = CacheStats()
        self._lock = threading.RLock()
        
        # Background cleanup task
        self._cleanup_task = None
        self._cleanup_interval = 60  # seconds
        
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._background_cleanup())
    
    async def stop_background_tasks(self):
        """Stop background maintenance tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired():
                await self._remove_entry(key)
                self._stats.misses += 1
                return None
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            entry.update_access()
            self._stats.hits += 1
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value with optional TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Calculate entry size
        try:
            size_bytes = len(pickle.dumps(value))
        except:
            size_bytes = 1024  # Fallback estimate
        
        with self._lock:
            # Check if we need to make space
            await self._ensure_capacity(size_bytes)
            
            # Remove existing entry if present
            if key in self._cache:
                await self._remove_entry(key)
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            self._cache[key] = entry
            self._access_order.append(key)
            
            self._stats.sets += 1
            self._stats.size_bytes += size_bytes
            self._stats.entry_count += 1
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                await self._remove_entry(key)
                self._stats.deletes += 1
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return True
            elif entry and entry.is_expired():
                await self._remove_entry(key)
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._stats = CacheStats()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'type': 'in_memory',
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'hit_rate': self._stats.hit_rate,
                'sets': self._stats.sets,
                'deletes': self._stats.deletes,
                'evictions': self._stats.evictions,
                'entry_count': self._stats.entry_count,
                'size_bytes': self._stats.size_bytes,
                'size_mb': self._stats.size_bytes / (1024 * 1024),
                'max_size': self.max_size,
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'utilization': self._stats.entry_count / self.max_size if self.max_size > 0 else 0
            }
    
    async def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry"""
        # Check memory limit
        while (self._stats.size_bytes + new_entry_size > self.max_memory_bytes and 
               self._access_order):
            await self._evict_lru()
        
        # Check entry count limit
        while len(self._cache) >= self.max_size and self._access_order:
            await self._evict_lru()
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._access_order:
            return
        
        lru_key = self._access_order[0]
        await self._remove_entry(lru_key)
        self._stats.evictions += 1
    
    async def _remove_entry(self, key: str) -> None:
        """Remove entry from cache"""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]
            
            if key in self._access_order:
                self._access_order.remove(key)
            
            self._stats.size_bytes -= entry.size_bytes
            self._stats.entry_count -= 1
    
    async def _background_cleanup(self) -> None:
        """Background task to clean up expired entries"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                with self._lock:
                    current_time = time.time()
                    expired_keys = []
                    
                    for key, entry in self._cache.items():
                        if entry.is_expired():
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        await self._remove_entry(key)
                
                if expired_keys:
                    logging.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in cache cleanup: {e}")

# =============================================================================
# REDIS CACHE IMPLEMENTATION (L2 CACHE)
# =============================================================================

class RedisCache(CacheInterface):
    """Redis-based distributed cache"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "app:", default_ttl: int = 3600):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        
        # Simulated Redis connection (in production, use actual Redis)
        self._redis_data: Dict[str, Dict[str, Any]] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
    
    def _get_full_key(self, key: str) -> str:
        """Get full Redis key with prefix"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key"""
        full_key = self._get_full_key(key)
        
        with self._lock:
            entry_data = self._redis_data.get(full_key)
            
            if entry_data is None:
                self._stats.misses += 1
                return None
            
            # Check expiration
            if entry_data.get('expires_at') and time.time() > entry_data['expires_at']:
                del self._redis_data[full_key]
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            
            # Deserialize value
            try:
                return pickle.loads(entry_data['value'])
            except:
                # Fallback for JSON-serializable data
                return entry_data['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value with optional TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        full_key = self._get_full_key(key)
        
        # Serialize value
        try:
            serialized_value = pickle.dumps(value)
        except:
            serialized_value = value  # Fallback for simple types
        
        entry_data = {
            'value': serialized_value,
            'created_at': time.time(),
            'expires_at': time.time() + ttl if ttl > 0 else None
        }
        
        with self._lock:
            self._redis_data[full_key] = entry_data
            self._stats.sets += 1
            self._stats.entry_count = len(self._redis_data)
            
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        full_key = self._get_full_key(key)
        
        with self._lock:
            if full_key in self._redis_data:
                del self._redis_data[full_key]
                self._stats.deletes += 1
                self._stats.entry_count = len(self._redis_data)
                return True
            
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        full_key = self._get_full_key(key)
        
        with self._lock:
            entry_data = self._redis_data.get(full_key)
            
            if entry_data is None:
                return False
            
            # Check expiration
            if entry_data.get('expires_at') and time.time() > entry_data['expires_at']:
                del self._redis_data[full_key]
                return False
            
            return True
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            # Only clear entries with our prefix
            keys_to_delete = [k for k in self._redis_data.keys() if k.startswith(self.key_prefix)]
            
            for key in keys_to_delete:
                del self._redis_data[key]
            
            self._stats = CacheStats()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            prefix_entries = sum(1 for k in self._redis_data.keys() if k.startswith(self.key_prefix))
            
            return {
                'type': 'redis',
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'hit_rate': self._stats.hit_rate,
                'sets': self._stats.sets,
                'deletes': self._stats.deletes,
                'entry_count': prefix_entries,
                'redis_url': self.redis_url,
                'key_prefix': self.key_prefix
            }

# =============================================================================
# DATABASE CACHE IMPLEMENTATION (L3 CACHE)
# =============================================================================

class DatabaseCache(CacheInterface):
    """Database-backed cache for persistent storage"""
    
    def __init__(self, connection_string: str = "sqlite:///cache.db", table_name: str = "cache_entries"):
        self.connection_string = connection_string
        self.table_name = table_name
        
        # Simulated database storage
        self._db_data: Dict[str, Dict[str, Any]] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
        
        # Initialize database schema (simulated)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        # In production, this would create the actual database table
        pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value by key"""
        with self._lock:
            entry_data = self._db_data.get(key)
            
            if entry_data is None:
                self._stats.misses += 1
                return None
            
            # Check expiration
            if entry_data.get('expires_at') and time.time() > entry_data['expires_at']:
                del self._db_data[key]
                self._stats.misses += 1
                return None
            
            self._stats.hits += 1
            
            # Deserialize value
            try:
                return pickle.loads(entry_data['value'])
            except:
                return entry_data['value']
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value with optional TTL"""
        # Serialize value
        try:
            serialized_value = pickle.dumps(value)
        except:
            serialized_value = str(value).encode()  # Fallback
        
        entry_data = {
            'key': key,
            'value': serialized_value,
            'created_at': time.time(),
            'expires_at': time.time() + ttl if ttl and ttl > 0 else None,
            'access_count': 0
        }
        
        with self._lock:
            self._db_data[key] = entry_data
            self._stats.sets += 1
            self._stats.entry_count = len(self._db_data)
            
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._db_data:
                del self._db_data[key]
                self._stats.deletes += 1
                self._stats.entry_count = len(self._db_data)
                return True
            
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        with self._lock:
            entry_data = self._db_data.get(key)
            
            if entry_data is None:
                return False
            
            # Check expiration
            if entry_data.get('expires_at') and time.time() > entry_data['expires_at']:
                del self._db_data[key]
                return False
            
            return True
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        with self._lock:
            self._db_data.clear()
            self._stats = CacheStats()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'type': 'database',
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'hit_rate': self._stats.hit_rate,
                'sets': self._stats.sets,
                'deletes': self._stats.deletes,
                'entry_count': len(self._db_data),
                'connection_string': self.connection_string,
                'table_name': self.table_name
            }

# =============================================================================
# MULTI-LEVEL CACHE COORDINATOR
# =============================================================================

class MultiLevelCache:
    """Coordinates multiple cache levels with intelligent fallback"""
    
    def __init__(self, l1_cache: CacheInterface, l2_cache: CacheInterface, 
                 l3_cache: CacheInterface):
        self.l1_cache = l1_cache  # In-memory (fastest)
        self.l2_cache = l2_cache  # Redis (fast, distributed)
        self.l3_cache = l3_cache  # Database (persistent)
        
        self._stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0,
            'total_requests': 0
        }
        
        self._invalidation_callbacks: List[Callable[[str], None]] = []
        self._cache_warming_enabled = True
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache hierarchy"""
        self._stats['total_requests'] += 1
        
        # Try L1 cache first (fastest)
        value = await self.l1_cache.get(key)
        if value is not None:
            self._stats['l1_hits'] += 1
            return value
        self._stats['l1_misses'] += 1
        
        # Try L2 cache (Redis)
        value = await self.l2_cache.get(key)
        if value is not None:
            self._stats['l2_hits'] += 1
            # Warm L1 cache
            await self.l1_cache.set(key, value)
            return value
        self._stats['l2_misses'] += 1
        
        # Try L3 cache (Database)
        value = await self.l3_cache.get(key)
        if value is not None:
            self._stats['l3_hits'] += 1
            # Warm L2 and L1 caches
            if self._cache_warming_enabled:
                await asyncio.gather(
                    self.l2_cache.set(key, value),
                    self.l1_cache.set(key, value)
                )
            return value
        self._stats['l3_misses'] += 1
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in all cache levels"""
        results = await asyncio.gather(
            self.l1_cache.set(key, value, ttl),
            self.l2_cache.set(key, value, ttl),
            self.l3_cache.set(key, value, ttl),
            return_exceptions=True
        )
        
        # Return True if at least one cache succeeded
        return any(isinstance(result, bool) and result for result in results)
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels"""
        results = await asyncio.gather(
            self.l1_cache.delete(key),
            self.l2_cache.delete(key),
            self.l3_cache.delete(key),
            return_exceptions=True
        )
        
        # Trigger invalidation callbacks
        for callback in self._invalidation_callbacks:
            try:
                callback(key)
            except Exception as e:
                logging.error(f"Error in invalidation callback: {e}")
        
        return any(isinstance(result, bool) and result for result in results)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern"""
        # This would require pattern matching support in cache implementations
        # For now, we'll implement a simple prefix-based invalidation
        
        invalidated_count = 0
        
        # In production, this would be more sophisticated
        # For demonstration, we'll clear all caches if pattern is "*"
        if pattern == "*":
            await asyncio.gather(
                self.l1_cache.clear(),
                self.l2_cache.clear(),
                self.l3_cache.clear()
            )
            invalidated_count = 1  # Placeholder
        
        return invalidated_count
    
    def add_invalidation_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for cache invalidation events"""
        self._invalidation_callbacks.append(callback)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all cache levels"""
        l1_stats = self.l1_cache.get_stats()
        l2_stats = self.l2_cache.get_stats()
        l3_stats = self.l3_cache.get_stats()
        
        total_hits = self._stats['l1_hits'] + self._stats['l2_hits'] + self._stats['l3_hits']
        total_misses = self._stats['l3_misses']  # Only count complete misses
        
        return {
            'multi_level_stats': {
                'total_requests': self._stats['total_requests'],
                'total_hits': total_hits,
                'total_misses': total_misses,
                'overall_hit_rate': total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0,
                'l1_hit_rate': self._stats['l1_hits'] / self._stats['total_requests'] if self._stats['total_requests'] > 0 else 0,
                'l2_hit_rate': self._stats['l2_hits'] / self._stats['total_requests'] if self._stats['total_requests'] > 0 else 0,
                'l3_hit_rate': self._stats['l3_hits'] / self._stats['total_requests'] if self._stats['total_requests'] > 0 else 0
            },
            'l1_cache': l1_stats,
            'l2_cache': l2_stats,
            'l3_cache': l3_stats
        }

# =============================================================================
# CACHE WARMING AND PRELOADING STRATEGIES
# =============================================================================

class CacheWarmingStrategy:
    """Intelligent cache warming and preloading"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self._warming_tasks: Set[asyncio.Task] = set()
        self._access_patterns: Dict[str, List[float]] = {}
        self._prediction_model = None
    
    async def warm_popular_keys(self, keys: List[str], data_loader: Callable[[str], Any]) -> None:
        """Warm cache with popular keys"""
        warming_tasks = []
        
        for key in keys:
            task = asyncio.create_task(self._warm_single_key(key, data_loader))
            warming_tasks.append(task)
            self._warming_tasks.add(task)
        
        # Execute warming tasks with concurrency limit
        semaphore = asyncio.Semaphore(10)  # Limit concurrent warming
        
        async def warm_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[warm_with_semaphore(task) for task in warming_tasks])
        
        # Clean up completed tasks
        for task in warming_tasks:
            self._warming_tasks.discard(task)
        
        successful_warmings = sum(1 for result in results if result)
        logging.info(f"Cache warming completed: {successful_warmings}/{len(keys)} keys warmed")
    
    async def _warm_single_key(self, key: str, data_loader: Callable[[str], Any]) -> bool:
        """Warm a single cache key"""
        try:
            # Check if already cached
            if await self.cache.get(key) is not None:
                return True
            
            # Load data and cache it
            data = data_loader(key)
            if data is not None:
                await self.cache.set(key, data)
                return True
            
        except Exception as e:
            logging.error(f"Error warming cache key {key}: {e}")
        
        return False
    
    def track_access_pattern(self, key: str) -> None:
        """Track access patterns for predictive warming"""
        current_time = time.time()
        
        if key not in self._access_patterns:
            self._access_patterns[key] = []
        
        self._access_patterns[key].append(current_time)
        
        # Keep only recent access history (last 24 hours)
        cutoff_time = current_time - (24 * 3600)
        self._access_patterns[key] = [
            access_time for access_time in self._access_patterns[key]
            if access_time > cutoff_time
        ]
    
    def predict_next_access_keys(self, count: int = 100) -> List[str]:
        """Predict keys likely to be accessed soon"""
        key_scores = {}
        current_time = time.time()
        
        for key, access_times in self._access_patterns.items():
            if not access_times:
                continue
            
            # Calculate access frequency and recency
            access_count = len(access_times)
            last_access = max(access_times)
            recency_score = 1.0 / (current_time - last_access + 1)  # Higher score for recent access
            
            # Simple prediction score
            key_scores[key] = access_count * recency_score
        
        # Sort by score and return top keys
        sorted_keys = sorted(key_scores.items(), key=lambda x: x[1], reverse=True)
        return [key for key, score in sorted_keys[:count]]
    
    async def predictive_warming(self, data_loader: Callable[[str], Any]) -> None:
        """Perform predictive cache warming based on access patterns"""
        predicted_keys = self.predict_next_access_keys(count=50)
        
        if predicted_keys:
            logging.info(f"Starting predictive warming for {len(predicted_keys)} keys")
            await self.warm_popular_keys(predicted_keys, data_loader)

# =============================================================================
# CACHE INVALIDATION STRATEGIES
# =============================================================================

class CacheInvalidationManager:
    """Manages cache invalidation strategies"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self._invalidation_rules: Dict[str, List[str]] = {}  # pattern -> dependent keys
        self._tag_mappings: Dict[str, Set[str]] = {}  # tag -> keys
        self._dependency_graph: Dict[str, Set[str]] = {}  # key -> dependent keys
    
    def add_dependency_rule(self, parent_pattern: str, dependent_patterns: List[str]) -> None:
        """Add invalidation dependency rule"""
        self._invalidation_rules[parent_pattern] = dependent_patterns
    
    def tag_key(self, key: str, tags: List[str]) -> None:
        """Associate key with tags for group invalidation"""
        for tag in tags:
            if tag not in self._tag_mappings:
                self._tag_mappings[tag] = set()
            self._tag_mappings[tag].add(key)
    
    def add_key_dependency(self, parent_key: str, dependent_key: str) -> None:
        """Add direct key dependency"""
        if parent_key not in self._dependency_graph:
            self._dependency_graph[parent_key] = set()
        self._dependency_graph[parent_key].add(dependent_key)
    
    async def invalidate_by_key(self, key: str) -> int:
        """Invalidate key and all its dependencies"""
        invalidated_keys = set()
        keys_to_process = [key]
        
        while keys_to_process:
            current_key = keys_to_process.pop(0)
            
            if current_key in invalidated_keys:
                continue
            
            # Invalidate the key
            await self.cache.delete(current_key)
            invalidated_keys.add(current_key)
            
            # Add dependent keys to process
            if current_key in self._dependency_graph:
                keys_to_process.extend(self._dependency_graph[current_key])
        
        logging.info(f"Invalidated {len(invalidated_keys)} keys starting from {key}")
        return len(invalidated_keys)
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all keys with specific tag"""
        if tag not in self._tag_mappings:
            return 0
        
        keys_to_invalidate = list(self._tag_mappings[tag])
        
        for key in keys_to_invalidate:
            await self.invalidate_by_key(key)
        
        # Clean up tag mapping
        del self._tag_mappings[tag]
        
        return len(keys_to_invalidate)
    
    async def time_based_invalidation(self, older_than_seconds: int) -> int:
        """Invalidate keys older than specified time"""
        # This would require timestamp tracking in cache implementations
        # For demonstration purposes, we'll simulate this
        
        invalidated_count = 0
        
        # In production, this would query actual cache timestamps
        # For now, we'll clear caches as a placeholder
        if older_than_seconds > 0:
            await self.cache.invalidate_pattern("*")
            invalidated_count = 1  # Placeholder
        
        return invalidated_count

# =============================================================================
# ENTERPRISE CACHE APPLICATIONS
# =============================================================================

class LegalDocumentCacheManager:
    """Specialized caching for legal document processing (Lawstronaut)"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warming_strategy = CacheWarmingStrategy(cache)
        self.invalidation_manager = CacheInvalidationManager(cache)
        
        # Setup invalidation rules
        self.invalidation_manager.add_dependency_rule(
            "legal_terms:*", ["document_analysis:*", "classification:*"]
        )
    
    async def cache_legal_document(self, document_id: str, document_data: Dict[str, Any],
                                 ttl: int = 3600) -> bool:
        """Cache legal document with metadata"""
        cache_key = f"document:{document_id}"
        
        # Tag for group invalidation
        document_type = document_data.get('type', 'unknown')
        self.invalidation_manager.tag_key(cache_key, [f"type:{document_type}", "documents"])
        
        # Cache document
        success = await self.cache.set(cache_key, document_data, ttl)
        
        if success:
            # Track access pattern
            self.warming_strategy.track_access_pattern(cache_key)
        
        return success
    
    async def get_legal_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve legal document from cache"""
        cache_key = f"document:{document_id}"
        
        # Track access for predictive warming
        self.warming_strategy.track_access_pattern(cache_key)
        
        return await self.cache.get(cache_key)
    
    async def cache_document_analysis(self, document_id: str, analysis_result: Dict[str, Any],
                                    ttl: int = 7200) -> bool:
        """Cache document analysis results"""
        cache_key = f"analysis:{document_id}"
        
        # Add dependency on source document
        self.invalidation_manager.add_key_dependency(f"document:{document_id}", cache_key)
        
        return await self.cache.set(cache_key, analysis_result, ttl)
    
    async def invalidate_document_type(self, document_type: str) -> int:
        """Invalidate all documents of specific type"""
        return await self.invalidation_manager.invalidate_by_tag(f"type:{document_type}")

class PersonalizationCacheManager:
    """Specialized caching for personalization engine (Optimizely)"""
    
    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.warming_strategy = CacheWarmingStrategy(cache)
        self.invalidation_manager = CacheInvalidationManager(cache)
    
    async def cache_user_profile(self, user_id: str, profile_data: Dict[str, Any],
                               ttl: int = 1800) -> bool:
        """Cache user profile data"""
        cache_key = f"profile:{user_id}"
        
        # Tag for user-based invalidation
        self.invalidation_manager.tag_key(cache_key, [f"user:{user_id}", "profiles"])
        
        return await self.cache.set(cache_key, profile_data, ttl)
    
    async def cache_user_recommendations(self, user_id: str, recommendations: List[Dict[str, Any]],
                                       ttl: int = 900) -> bool:
        """Cache personalized recommendations"""
        cache_key = f"recommendations:{user_id}"
        
        # Add dependency on user profile
        self.invalidation_manager.add_key_dependency(f"profile:{user_id}", cache_key)
        
        return await self.cache.set(cache_key, recommendations, ttl)
    
    async def warm_active_user_caches(self, active_user_ids: List[str]) -> None:
        """Warm caches for active users"""
        def load_user_profile(user_id: str) -> Dict[str, Any]:
            # Simulate loading user profile from database
            return {
                'user_id': user_id,
                'preferences': ['tech', 'science'],
                'behavior_score': 0.8,
                'last_active': time.time()
            }
        
        profile_keys = [f"profile:{user_id}" for user_id in active_user_ids]
        await self.warming_strategy.warm_popular_keys(profile_keys, load_user_profile)
    
    async def invalidate_user_data(self, user_id: str) -> int:
        """Invalidate all cached data for user"""
        return await self.invalidation_manager.invalidate_by_tag(f"user:{user_id}")

# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

async def demonstrate_multilevel_caching():
    """Comprehensive demonstration of multi-level caching system"""
    
    print("=== Multi-Level Caching System Demo ===\n")
    
    # Initialize cache levels
    l1_cache = InMemoryCache(max_size=1000, max_memory_mb=50)
    l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="demo:")
    l3_cache = DatabaseCache(connection_string="sqlite:///demo_cache.db")
    
    # Start background tasks
    await l1_cache.start_background_tasks()
    
    # Initialize multi-level cache
    multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
    
    print("1. Basic Multi-Level Cache Operations")
    print("-" * 50)
    
    # Test cache operations
    test_data = {
        'document_1': {'title': 'Contract Agreement', 'content': 'Legal document content...'},
        'document_2': {'title': 'Privacy Policy', 'content': 'Privacy policy content...'},
        'user_profile_123': {'name': 'John Doe', 'preferences': ['tech', 'legal']}
    }
    
    # Set data in cache
    for key, value in test_data.items():
        success = await multi_cache.set(key, value, ttl=3600)
        print(f"Cached {key}: {success}")
    
    print("\n2. Cache Hit Performance Test")
    print("-" * 50)
    
    # Test cache retrieval performance
    start_time = time.perf_counter()
    
    for key in test_data.keys():
        cached_value = await multi_cache.get(key)
        print(f"Retrieved {key}: {cached_value is not None}")
    
    retrieval_time = (time.perf_counter() - start_time) * 1000
    print(f"Total retrieval time: {retrieval_time:.2f}ms")
    
    # Show cache statistics
    stats = multi_cache.get_comprehensive_stats()
    print(f"\nMulti-level cache hit rate: {stats['multi_level_stats']['overall_hit_rate']:.2%}")
    print(f"L1 cache hit rate: {stats['multi_level_stats']['l1_hit_rate']:.2%}")
    
    print("\n3. Legal Document Cache Manager Demo")
    print("-" * 50)
    
    legal_cache_manager = LegalDocumentCacheManager(multi_cache)
    
    # Cache legal documents
    legal_documents = [
        {'id': 'doc_1', 'type': 'contract', 'content': 'Contract content...'},
        {'id': 'doc_2', 'type': 'policy', 'content': 'Policy content...'},
        {'id': 'doc_3', 'type': 'contract', 'content': 'Another contract...'}
    ]
    
    for doc in legal_documents:
        success = await legal_cache_manager.cache_legal_document(doc['id'], doc)
        print(f"Cached legal document {doc['id']}: {success}")
    
    # Cache analysis results
    for doc in legal_documents:
        analysis = {'risk_score': 0.7, 'key_terms': ['liability', 'termination']}
        success = await legal_cache_manager.cache_document_analysis(doc['id'], analysis)
        print(f"Cached analysis for {doc['id']}: {success}")
    
    print("\n4. Personalization Cache Manager Demo")
    print("-" * 50)
    
    personalization_manager = PersonalizationCacheManager(multi_cache)
    
    # Cache user profiles
    active_users = ['user_1', 'user_2', 'user_3']
    
    for user_id in active_users:
        profile = {
            'user_id': user_id,
            'preferences': ['tech', 'science'],
            'activity_score': 0.8
        }
        success = await personalization_manager.cache_user_profile(user_id, profile)
        print(f"Cached profile for {user_id}: {success}")
    
    # Warm caches for active users
    await personalization_manager.warm_active_user_caches(active_users)
    print("Warmed caches for active users")
    
    print("\n5. Cache Invalidation Demo")
    print("-" * 50)
    
    # Test document type invalidation
    invalidated_count = await legal_cache_manager.invalidate_document_type('contract')
    print(f"Invalidated {invalidated_count} contract documents")
    
    # Test user data invalidation
    invalidated_count = await personalization_manager.invalidate_user_data('user_1')
    print(f"Invalidated data for user_1: {invalidated_count} items")
    
    print("\n6. Cache Warming and Prediction Demo")
    print("-" * 50)
    
    warming_strategy = CacheWarmingStrategy(multi_cache)
    
    # Simulate access patterns
    access_keys = ['document_1', 'document_2', 'user_profile_123']
    for _ in range(5):  # Simulate multiple accesses
        for key in access_keys:
            warming_strategy.track_access_pattern(key)
            await asyncio.sleep(0.01)  # Small delay to create time variance
    
    # Predict next access keys
    predicted_keys = warming_strategy.predict_next_access_keys(count=10)
    print(f"Predicted next access keys: {predicted_keys}")
    
    # Perform predictive warming
    def mock_data_loader(key: str) -> Dict[str, Any]:
        return {'key': key, 'data': f'Loaded data for {key}', 'timestamp': time.time()}
    
    await warming_strategy.predictive_warming(mock_data_loader)
    print("Completed predictive cache warming")
    
    print("\n7. Performance Analysis")
    print("-" * 50)
    
    # Final statistics
    final_stats = multi_cache.get_comprehensive_stats()
    multi_stats = final_stats['multi_level_stats']
    
    print("Final Cache Performance:")
    print(f"  Total requests: {multi_stats['total_requests']}")
    print(f"  Overall hit rate: {multi_stats['overall_hit_rate']:.2%}")
    print(f"  L1 hit rate: {multi_stats['l1_hit_rate']:.2%}")
    print(f"  L2 hit rate: {multi_stats['l2_hit_rate']:.2%}")
    print(f"  L3 hit rate: {multi_stats['l3_hit_rate']:.2%}")
    
    # Individual cache statistics
    print(f"\nL1 Cache (In-Memory): {final_stats['l1_cache']['entry_count']} entries, {final_stats['l1_cache']['size_mb']:.1f}MB")
    print(f"L2 Cache (Redis): {final_stats['l2_cache']['entry_count']} entries")
    print(f"L3 Cache (Database): {final_stats['l3_cache']['entry_count']} entries")
    
    print("\n8. Load Testing")
    print("-" * 50)
    
    # Simulate high-load scenario
    load_test_keys = [f"load_test_key_{i}" for i in range(1000)]
    load_test_data = [f"Load test data {i}" for i in range(1000)]
    
    # Measure cache set performance
    start_time = time.perf_counter()
    
    set_tasks = [multi_cache.set(key, data, ttl=600) for key, data in zip(load_test_keys, load_test_data)]
    set_results = await asyncio.gather(*set_tasks)
    
    set_time = (time.perf_counter() - start_time) * 1000
    successful_sets = sum(1 for result in set_results if result)
    
    print(f"Set performance: {successful_sets}/1000 keys in {set_time:.2f}ms")
    print(f"Average set time per key: {set_time / len(load_test_keys):.3f}ms")
    
    # Measure cache get performance
    start_time = time.perf_counter()
    
    get_tasks = [multi_cache.get(key) for key in load_test_keys]
    get_results = await asyncio.gather(*get_tasks)
    
    get_time = (time.perf_counter() - start_time) * 1000
    successful_gets = sum(1 for result in get_results if result is not None)
    
    print(f"Get performance: {successful_gets}/1000 keys in {get_time:.2f}ms")
    print(f"Average get time per key: {get_time / len(load_test_keys):.3f}ms")
    
    # Clean up
    await l1_cache.stop_background_tasks()
    
    print("\n=== Multi-Level Caching Demo Completed ===")
    
    print("\nKey Insights:")
    print("- Multi-level caching provides excellent performance with intelligent fallback")
    print("- L1 in-memory cache provides sub-millisecond access for hot data")
    print("- Cache warming and predictive strategies improve hit rates significantly")
    print("- Intelligent invalidation prevents stale data across dependent cache entries")
    print("- Enterprise-specific cache managers provide domain-optimized caching patterns")

if __name__ == "__main__":
    # Run the comprehensive multi-level caching demonstration
    asyncio.run(demonstrate_multilevel_caching())
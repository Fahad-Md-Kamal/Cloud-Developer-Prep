"""
Intelligent Caching System for LLM API Optimization

This module demonstrates advanced caching strategies for LLM API responses
designed for enterprise applications like those used at Lawstronaut (legal document
processing) and Optimizely (real-time AI interactions).

Key concepts covered:
- Multi-layer caching architecture (memory, Redis, persistent storage)
- Semantic similarity-based cache matching
- Cost-aware cache eviction policies
- Response quality-based caching decisions
- Cache warming and precomputation strategies

Real-world applications:
- Legal document analysis with expensive LLM calls
- Customer service responses with high query similarity
- Content generation with reusable components

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from decimal import Decimal
import pickle
import gzip
import redis.asyncio as redis
from abc import ABC, abstractmethod
import numpy as np

# =============================================================================
# CACHING DATA MODELS AND CONFIGURATION
# =============================================================================

class CacheLayer(Enum):
    """Different cache layers in the hierarchy"""
    MEMORY = "memory"
    REDIS = "redis"
    PERSISTENT = "persistent"
    DISTRIBUTED = "distributed"

class CacheStrategy(Enum):
    """Cache storage and eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used  
    COST_AWARE = "cost_aware"  # Based on original request cost
    QUALITY_AWARE = "quality_aware"  # Based on response quality
    TTL_BASED = "ttl_based"  # Time-based expiration
    ADAPTIVE = "adaptive"  # Dynamic strategy selection

@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    response: Dict[str, Any]
    original_cost: Decimal
    quality_score: float
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: int
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    @property
    def is_expired(self) -> bool:
        return self.age_seconds > self.ttl_seconds
    
    @property
    def cost_savings(self) -> Decimal:
        return self.original_cost * self.access_count
    
    @property
    def access_frequency(self) -> float:
        """Access frequency per hour"""
        age_hours = max(self.age_seconds / 3600, 0.1)
        return self.access_count / age_hours

@dataclass
class CacheConfig:
    """Configuration for cache layers and policies"""
    memory_max_size: int = 1000
    redis_max_size: int = 10000
    default_ttl_seconds: int = 3600
    max_entry_size_bytes: int = 1024 * 1024  # 1MB
    eviction_strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    similarity_threshold: float = 0.85
    quality_threshold: float = 0.7
    cost_threshold: Decimal = Decimal("0.001")
    enable_compression: bool = True
    enable_semantic_matching: bool = True

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_cost_savings: Decimal = Decimal("0")
    average_response_time: float = 0.0
    cache_size_bytes: int = 0
    hit_rate: float = 0.0
    cost_savings_rate: float = 0.0
    
    def update_hit_rate(self):
        total_requests = self.hits + self.misses
        self.hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

# =============================================================================
# SEMANTIC SIMILARITY ENGINE
# =============================================================================

class SemanticSimilarityEngine:
    """Engine for computing semantic similarity between prompts"""
    
    def __init__(self):
        # In production, you would use actual embedding models
        # This is a simplified implementation for demonstration
        self.embedding_cache = {}
        
        # Common legal/business terms for domain-specific similarity
        self.domain_terms = {
            "legal": [
                "contract", "agreement", "clause", "liability", "damages",
                "breach", "jurisdiction", "arbitration", "indemnification"
            ],
            "customer_service": [
                "help", "support", "issue", "problem", "question",
                "account", "billing", "refund", "cancel"
            ],
            "technical": [
                "api", "code", "function", "error", "debug",
                "implementation", "architecture", "performance"
            ]
        }
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text (simplified implementation)
        In production, use actual embedding models like OpenAI embeddings
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Simplified embedding based on word features
        words = text.lower().split()
        
        # Feature vector components
        features = []
        
        # Length features
        features.append(len(words) / 100.0)  # Normalized length
        features.append(len(text) / 1000.0)   # Character length
        
        # Domain-specific features
        for domain, terms in self.domain_terms.items():
            domain_score = sum(1 for word in words if word in terms) / max(len(words), 1)
            features.append(domain_score)
        
        # Common word patterns
        question_words = ["what", "how", "why", "when", "where", "which"]
        question_score = sum(1 for word in words if word in question_words) / max(len(words), 1)
        features.append(question_score)
        
        # Padding to fixed size
        while len(features) < 50:
            features.append(0.0)
        
        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = [f / norm for f in features]
        
        embedding = features[:50]  # Fixed size embedding
        self.embedding_cache[text] = embedding
        
        return embedding
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        emb1 = np.array(self.get_embedding(text1))
        emb2 = np.array(self.get_embedding(text2))
        
        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, similarity)  # Ensure non-negative
    
    def find_similar_entries(self, query_text: str, cache_entries: List[CacheEntry],
                           threshold: float = 0.85) -> List[Tuple[CacheEntry, float]]:
        """Find cache entries similar to query text"""
        similar_entries = []
        
        for entry in cache_entries:
            # Extract original prompt from cache entry metadata
            original_prompt = entry.metadata.get("original_prompt", "")
            if not original_prompt:
                continue
            
            similarity = self.compute_similarity(query_text, original_prompt)
            
            if similarity >= threshold:
                similar_entries.append((entry, similarity))
        
        # Sort by similarity (descending)
        similar_entries.sort(key=lambda x: x[1], reverse=True)
        
        return similar_entries

# =============================================================================
# MEMORY CACHE LAYER
# =============================================================================

class MemoryCache:
    """High-performance in-memory cache with intelligent eviction"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: Dict[str, CacheEntry] = OrderedDict()
        self.access_order: Dict[str, datetime] = {}
        self.stats = CacheStats()
        
    def generate_key(self, prompt: str, model: str, temperature: float = 0.7,
                    additional_params: Optional[Dict[str, Any]] = None) -> str:
        """Generate consistent cache key"""
        key_components = {
            "prompt": prompt,
            "model": model,
            "temperature": round(temperature, 2)
        }
        
        if additional_params:
            key_components.update(additional_params)
        
        key_string = json.dumps(key_components, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve entry from cache"""
        if key not in self.cache:
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if entry.is_expired:
            self.evict(key)
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None
        
        # Update access information
        entry.last_accessed = datetime.utcnow()
        entry.access_count += 1
        self.access_order[key] = entry.last_accessed
        
        # Move to end for LRU
        self.cache.move_to_end(key)
        
        # Update statistics
        self.stats.hits += 1
        self.stats.total_cost_savings += entry.original_cost
        self.stats.update_hit_rate()
        
        logging.debug(f"Cache hit for key {key}")
        return entry.response
    
    def put(self, key: str, response: Dict[str, Any], original_cost: Decimal,
            quality_score: float = 1.0, ttl_seconds: Optional[int] = None,
            tags: Optional[Set[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store entry in cache"""
        
        # Calculate entry size
        serialized = json.dumps(response)
        entry_size = len(serialized.encode('utf-8'))
        
        # Check size limits
        if entry_size > self.config.max_entry_size_bytes:
            logging.warning(f"Entry too large ({entry_size} bytes), not caching")
            return False
        
        # Use default TTL if not specified
        if ttl_seconds is None:
            ttl_seconds = self._calculate_dynamic_ttl(original_cost, quality_score)
        
        # Create cache entry
        entry = CacheEntry(
            key=key,
            response=response,
            original_cost=original_cost,
            quality_score=quality_score,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=1,
            size_bytes=entry_size,
            ttl_seconds=ttl_seconds,
            tags=tags or set(),
            metadata=metadata or {}
        )
        
        # Evict if necessary
        while (len(self.cache) >= self.config.memory_max_size or
               self._would_exceed_memory_limit(entry)):
            if not self._evict_least_valuable():
                logging.error("Failed to evict entry, cache may be full")
                return False
        
        # Store entry
        self.cache[key] = entry
        self.access_order[key] = entry.last_accessed
        self.stats.cache_size_bytes += entry_size
        
        logging.debug(f"Cached entry with key {key}, size {entry_size} bytes")
        return True
    
    def _calculate_dynamic_ttl(self, cost: Decimal, quality_score: float) -> int:
        """Calculate TTL based on cost and quality"""
        base_ttl = self.config.default_ttl_seconds
        
        # Higher cost = longer TTL
        cost_multiplier = min(float(cost) * 1000, 5.0)
        
        # Higher quality = longer TTL
        quality_multiplier = max(quality_score, 0.5)
        
        dynamic_ttl = int(base_ttl * cost_multiplier * quality_multiplier)
        
        # Clamp to reasonable bounds
        return max(300, min(dynamic_ttl, 86400))  # 5 minutes to 24 hours
    
    def _would_exceed_memory_limit(self, new_entry: CacheEntry) -> bool:
        """Check if adding entry would exceed memory limits"""
        # Simple check - could be more sophisticated
        estimated_new_size = self.stats.cache_size_bytes + new_entry.size_bytes
        max_size = self.config.memory_max_size * 1000  # Rough bytes estimate
        return estimated_new_size > max_size
    
    def _evict_least_valuable(self) -> bool:
        """Evict least valuable entry based on strategy"""
        if not self.cache:
            return False
        
        if self.config.eviction_strategy == CacheStrategy.LRU:
            key_to_evict = next(iter(self.cache))
        elif self.config.eviction_strategy == CacheStrategy.COST_AWARE:
            key_to_evict = self._find_least_cost_effective()
        elif self.config.eviction_strategy == CacheStrategy.ADAPTIVE:
            key_to_evict = self._adaptive_eviction_selection()
        else:
            # Default to LRU
            key_to_evict = next(iter(self.cache))
        
        if key_to_evict:
            self.evict(key_to_evict)
            return True
        
        return False
    
    def _find_least_cost_effective(self) -> Optional[str]:
        """Find least cost-effective entry for eviction"""
        if not self.cache:
            return None
        
        min_value = float('inf')
        least_valuable_key = None
        
        for key, entry in self.cache.items():
            # Value score combines cost savings and access frequency
            value_score = float(entry.cost_savings) * entry.access_frequency
            
            if value_score < min_value:
                min_value = value_score
                least_valuable_key = key
        
        return least_valuable_key
    
    def _adaptive_eviction_selection(self) -> Optional[str]:
        """Adaptive eviction strategy that considers multiple factors"""
        if not self.cache:
            return None
        
        current_time = datetime.utcnow()
        candidate_scores = []
        
        for key, entry in self.cache.items():
            # Calculate composite score for eviction
            age_penalty = entry.age_seconds / self.config.default_ttl_seconds
            access_bonus = entry.access_frequency
            cost_bonus = float(entry.original_cost) * 100
            quality_bonus = entry.quality_score
            
            # Lower score = more likely to be evicted
            eviction_score = age_penalty - (access_bonus + cost_bonus + quality_bonus)
            candidate_scores.append((key, eviction_score))
        
        # Sort by eviction score (ascending)
        candidate_scores.sort(key=lambda x: x[1])
        
        return candidate_scores[0][0] if candidate_scores else None
    
    def evict(self, key: str) -> bool:
        """Evict specific entry from cache"""
        if key not in self.cache:
            return False
        
        entry = self.cache.pop(key)
        self.access_order.pop(key, None)
        self.stats.cache_size_bytes -= entry.size_bytes
        self.stats.evictions += 1
        
        logging.debug(f"Evicted cache entry {key}")
        return True
    
    def clear_expired(self) -> int:
        """Clear expired entries and return count"""
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.is_expired:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.evict(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        return self.stats
    
    def find_by_tags(self, tags: Set[str]) -> List[CacheEntry]:
        """Find entries by tags"""
        matching_entries = []
        
        for entry in self.cache.values():
            if entry.tags and tags.intersection(entry.tags):
                matching_entries.append(entry)
        
        return matching_entries

# =============================================================================
# REDIS CACHE LAYER  
# =============================================================================

class RedisCache:
    """Redis-based distributed cache layer"""
    
    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        self.config = config
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.stats = CacheStats()
        self.key_prefix = "llm_cache:"
        
    async def initialize(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(
            self.redis_url,
            decode_responses=False,  # We'll handle encoding ourselves
            max_connections=20
        )
        
        # Test connection
        try:
            await self.redis_client.ping()
            logging.info("Redis cache initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_redis_key(self, key: str) -> str:
        """Create Redis key with prefix"""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve entry from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            redis_key = self._make_redis_key(key)
            
            # Get serialized data
            serialized_data = await self.redis_client.get(redis_key)
            
            if serialized_data is None:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
            
            # Deserialize
            if self.config.enable_compression:
                decompressed_data = gzip.decompress(serialized_data)
                entry_data = pickle.loads(decompressed_data)
            else:
                entry_data = pickle.loads(serialized_data)
            
            # Update access information
            entry_data["access_count"] += 1
            entry_data["last_accessed"] = datetime.utcnow()
            
            # Store updated entry back
            await self._store_entry_data(redis_key, entry_data)
            
            # Update statistics
            self.stats.hits += 1
            self.stats.total_cost_savings += Decimal(str(entry_data["original_cost"]))
            self.stats.update_hit_rate()
            
            return entry_data["response"]
            
        except Exception as e:
            logging.error(f"Error retrieving from Redis cache: {e}")
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None
    
    async def put(self, key: str, response: Dict[str, Any], original_cost: Decimal,
                  quality_score: float = 1.0, ttl_seconds: Optional[int] = None,
                  tags: Optional[Set[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store entry in Redis cache"""
        
        if not self.redis_client:
            return False
        
        try:
            # Create entry data
            entry_data = {
                "key": key,
                "response": response,
                "original_cost": float(original_cost),
                "quality_score": quality_score,
                "created_at": datetime.utcnow(),
                "last_accessed": datetime.utcnow(),
                "access_count": 1,
                "tags": list(tags) if tags else [],
                "metadata": metadata or {}
            }
            
            # Calculate TTL
            if ttl_seconds is None:
                ttl_seconds = self._calculate_dynamic_ttl(original_cost, quality_score)
            
            redis_key = self._make_redis_key(key)
            
            # Store entry
            await self._store_entry_data(redis_key, entry_data, ttl_seconds)
            
            logging.debug(f"Stored entry in Redis with key {redis_key}")
            return True
            
        except Exception as e:
            logging.error(f"Error storing in Redis cache: {e}")
            return False
    
    async def _store_entry_data(self, redis_key: str, entry_data: Dict[str, Any],
                               ttl_seconds: Optional[int] = None):
        """Store entry data in Redis"""
        # Serialize
        serialized_data = pickle.dumps(entry_data)
        
        # Compress if enabled
        if self.config.enable_compression:
            serialized_data = gzip.compress(serialized_data)
        
        # Store with TTL
        if ttl_seconds:
            await self.redis_client.setex(redis_key, ttl_seconds, serialized_data)
        else:
            await self.redis_client.set(redis_key, serialized_data)
    
    def _calculate_dynamic_ttl(self, cost: Decimal, quality_score: float) -> int:
        """Calculate TTL based on cost and quality (same logic as memory cache)"""
        base_ttl = self.config.default_ttl_seconds * 2  # Redis can store longer
        
        cost_multiplier = min(float(cost) * 1000, 10.0)  # Higher multiplier for Redis
        quality_multiplier = max(quality_score, 0.5)
        
        dynamic_ttl = int(base_ttl * cost_multiplier * quality_multiplier)
        
        return max(1800, min(dynamic_ttl, 604800))  # 30 minutes to 1 week
    
    async def evict(self, key: str) -> bool:
        """Evict entry from Redis cache"""
        if not self.redis_client:
            return False
        
        try:
            redis_key = self._make_redis_key(key)
            deleted = await self.redis_client.delete(redis_key)
            
            if deleted:
                self.stats.evictions += 1
                logging.debug(f"Evicted Redis entry {redis_key}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error evicting from Redis: {e}")
            return False
    
    async def clear_expired(self) -> int:
        """Clear expired entries (Redis handles this automatically)"""
        # Redis automatically handles TTL expiration
        # This method is for compatibility
        return 0
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get Redis cache information"""
        if not self.redis_client:
            return {}
        
        try:
            info = await self.redis_client.info("memory")
            keyspace = await self.redis_client.info("keyspace")
            
            return {
                "memory_usage": info.get("used_memory", 0),
                "memory_usage_human": info.get("used_memory_human", "0B"),
                "keyspace_info": keyspace
            }
            
        except Exception as e:
            logging.error(f"Error getting Redis info: {e}")
            return {}

# =============================================================================
# MULTI-LAYER INTELLIGENT CACHE MANAGER
# =============================================================================

class IntelligentCacheManager:
    """Comprehensive multi-layer cache manager with semantic matching"""
    
    def __init__(self, config: CacheConfig, redis_url: str = "redis://localhost:6379"):
        self.config = config
        
        # Initialize cache layers
        self.memory_cache = MemoryCache(config)
        self.redis_cache = RedisCache(config, redis_url)
        
        # Initialize semantic engine
        self.semantic_engine = SemanticSimilarityEngine()
        
        # Combined statistics
        self.global_stats = CacheStats()
        
        # Cache warming configuration
        self.warm_cache_patterns = []
        
    async def initialize(self):
        """Initialize all cache layers"""
        await self.redis_cache.initialize()
        logging.info("Intelligent cache manager initialized")
    
    async def cleanup(self):
        """Cleanup all cache layers"""
        await self.redis_cache.cleanup()
        logging.info("Cache manager cleaned up")
    
    async def get_response(self, prompt: str, model: str, temperature: float = 0.7,
                          additional_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response with intelligent fallback through cache layers
        """
        # Generate primary cache key
        cache_key = self.memory_cache.generate_key(prompt, model, temperature, additional_params)
        
        # Try memory cache first (fastest)
        response = self.memory_cache.get(cache_key)
        if response:
            logging.debug(f"Memory cache hit for {cache_key}")
            self._update_global_stats("memory", True)
            return response
        
        # Try Redis cache (distributed)
        response = await self.redis_cache.get(cache_key)
        if response:
            logging.debug(f"Redis cache hit for {cache_key}")
            self._update_global_stats("redis", True)
            
            # Promote to memory cache
            await self._promote_to_memory(cache_key, response)
            return response
        
        # If semantic matching is enabled, try to find similar cached responses
        if self.config.enable_semantic_matching:
            similar_response = await self._find_semantic_match(prompt, model, temperature)
            if similar_response:
                logging.debug(f"Semantic cache hit for similar prompt")
                self._update_global_stats("semantic", True)
                return similar_response
        
        # Cache miss across all layers
        logging.debug(f"Complete cache miss for {cache_key}")
        self._update_global_stats("all", False)
        return None
    
    async def store_response(self, prompt: str, model: str, response: Dict[str, Any],
                           original_cost: Decimal, temperature: float = 0.7,
                           quality_score: float = 1.0,
                           additional_params: Optional[Dict[str, Any]] = None,
                           tags: Optional[Set[str]] = None) -> bool:
        """
        Store response in appropriate cache layers based on cost and quality
        """
        cache_key = self.memory_cache.generate_key(prompt, model, temperature, additional_params)
        
        # Prepare metadata
        metadata = {
            "original_prompt": prompt,
            "model": model,
            "temperature": temperature,
            "timestamp": datetime.utcnow().isoformat()
        }
        if additional_params:
            metadata.update(additional_params)
        
        storage_success = True
        
        # Always try to store in memory cache for speed
        memory_stored = self.memory_cache.put(
            cache_key, response, original_cost, quality_score, 
            tags=tags, metadata=metadata
        )
        
        if not memory_stored:
            logging.warning(f"Failed to store in memory cache: {cache_key}")
            storage_success = False
        
        # Store in Redis for persistence and distribution
        # Only store high-value items in Redis to manage costs
        should_store_redis = (
            original_cost >= self.config.cost_threshold or
            quality_score >= self.config.quality_threshold
        )
        
        if should_store_redis:
            redis_stored = await self.redis_cache.put(
                cache_key, response, original_cost, quality_score,
                tags=tags, metadata=metadata
            )
            
            if not redis_stored:
                logging.warning(f"Failed to store in Redis cache: {cache_key}")
        
        return storage_success
    
    async def _find_semantic_match(self, prompt: str, model: str, 
                                  temperature: float) -> Optional[Dict[str, Any]]:
        """Find semantically similar cached response"""
        
        # Get entries from memory cache for semantic matching
        memory_entries = list(self.memory_cache.cache.values())
        
        # Find similar entries
        similar_entries = self.semantic_engine.find_similar_entries(
            prompt, memory_entries, self.config.similarity_threshold
        )
        
        if similar_entries:
            # Return the most similar entry that matches model and temperature
            for entry, similarity in similar_entries:
                entry_metadata = entry.metadata
                if (entry_metadata.get("model") == model and
                    abs(entry_metadata.get("temperature", 0.7) - temperature) < 0.1):
                    
                    # Update access statistics for the matched entry
                    entry.access_count += 1
                    entry.last_accessed = datetime.utcnow()
                    
                    logging.info(f"Semantic match found with similarity {similarity:.3f}")
                    return entry.response
        
        return None
    
    async def _promote_to_memory(self, cache_key: str, response: Dict[str, Any]):
        """Promote Redis cache hit to memory cache"""
        # This is a simplified promotion - in production you'd want to
        # retrieve the full entry metadata from Redis
        estimated_cost = Decimal("0.01")  # Default cost for promotion
        
        self.memory_cache.put(cache_key, response, estimated_cost, quality_score=0.8)
    
    def _update_global_stats(self, layer: str, hit: bool):
        """Update global cache statistics"""
        if hit:
            self.global_stats.hits += 1
        else:
            self.global_stats.misses += 1
        
        self.global_stats.update_hit_rate()
    
    async def precompute_responses(self, prompt_patterns: List[Dict[str, Any]]):
        """Precompute and cache responses for common patterns"""
        logging.info(f"Starting cache warming for {len(prompt_patterns)} patterns")
        
        for pattern in prompt_patterns:
            # This would integrate with your LLM client to precompute responses
            # For demonstration, we'll simulate this
            
            prompt_template = pattern.get("prompt_template", "")
            model = pattern.get("model", "gpt-3.5-turbo")
            variations = pattern.get("variations", [])
            
            for variation in variations[:5]:  # Limit to avoid overuse
                full_prompt = prompt_template.format(**variation)
                
                # Check if already cached
                response = await self.get_response(full_prompt, model)
                if not response:
                    # In production, you would call your LLM API here
                    simulated_response = {
                        "content": f"Precomputed response for: {full_prompt[:100]}...",
                        "model": model,
                        "cached_at": datetime.utcnow().isoformat()
                    }
                    
                    await self.store_response(
                        full_prompt, model, simulated_response,
                        Decimal("0.01"), quality_score=0.9,
                        tags={"precomputed", pattern.get("category", "general")}
                    )
                    
                    logging.debug(f"Precomputed response for pattern: {pattern.get('name', 'unnamed')}")
        
        logging.info("Cache warming completed")
    
    async def invalidate_by_tags(self, tags: Set[str]):
        """Invalidate cache entries by tags"""
        # Invalidate from memory cache
        memory_entries = self.memory_cache.find_by_tags(tags)
        for entry in memory_entries:
            self.memory_cache.evict(entry.key)
        
        # For Redis, we'd need to implement tag-based indexing
        # This is simplified for demonstration
        logging.info(f"Invalidated {len(memory_entries)} entries with tags: {tags}")
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics across all cache layers"""
        
        memory_stats = self.memory_cache.get_stats()
        redis_info = await self.redis_cache.get_cache_info()
        
        return {
            "global_stats": {
                "total_hits": self.global_stats.hits,
                "total_misses": self.global_stats.misses,
                "overall_hit_rate": self.global_stats.hit_rate,
                "total_cost_savings": float(self.global_stats.total_cost_savings)
            },
            "memory_cache": {
                "entries": len(self.memory_cache.cache),
                "hits": memory_stats.hits,
                "misses": memory_stats.misses,
                "hit_rate": memory_stats.hit_rate,
                "size_bytes": memory_stats.cache_size_bytes,
                "cost_savings": float(memory_stats.total_cost_savings)
            },
            "redis_cache": {
                "info": redis_info,
                "hits": self.redis_cache.stats.hits,
                "misses": self.redis_cache.stats.misses,
                "hit_rate": self.redis_cache.stats.hit_rate
            },
            "semantic_engine": {
                "embedding_cache_size": len(self.semantic_engine.embedding_cache),
                "similarity_threshold": self.config.similarity_threshold
            },
            "configuration": {
                "memory_max_size": self.config.memory_max_size,
                "default_ttl": self.config.default_ttl_seconds,
                "eviction_strategy": self.config.eviction_strategy.value,
                "semantic_matching_enabled": self.config.enable_semantic_matching,
                "compression_enabled": self.config.enable_compression
            }
        }
    
    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """Analyze and optimize cache performance"""
        
        optimization_report = {
            "analysis": {},
            "recommendations": [],
            "actions_taken": []
        }
        
        # Analyze hit rates
        memory_stats = self.memory_cache.get_stats()
        
        if memory_stats.hit_rate < 0.3:
            optimization_report["recommendations"].append({
                "type": "increase_memory_cache_size",
                "reason": "Low hit rate suggests cache size too small",
                "current_hit_rate": memory_stats.hit_rate,
                "suggested_action": "Increase memory cache size by 50%"
            })
        
        # Analyze cost effectiveness
        if memory_stats.total_cost_savings > Decimal("1.0"):
            optimization_report["analysis"]["cost_effective"] = True
            optimization_report["analysis"]["roi"] = "Positive - cache providing good value"
        else:
            optimization_report["recommendations"].append({
                "type": "review_caching_strategy",
                "reason": "Low cost savings suggest caching low-value requests",
                "suggested_action": "Increase cost threshold for caching"
            })
        
        # Clean up expired entries
        expired_cleaned = self.memory_cache.clear_expired()
        if expired_cleaned > 0:
            optimization_report["actions_taken"].append(f"Cleaned up {expired_cleaned} expired entries")
        
        return optimization_report

# =============================================================================
# DEMONSTRATION FUNCTION
# =============================================================================

async def demonstrate_intelligent_caching_system():
    """
    Comprehensive demonstration of the intelligent caching system
    in realistic enterprise scenarios.
    """
    
    print(f"=== {__doc__.split('.')[0]} ===\n")
    
    # Initialize cache configuration
    config = CacheConfig(
        memory_max_size=100,
        redis_max_size=1000,
        default_ttl_seconds=1800,  # 30 minutes
        eviction_strategy=CacheStrategy.ADAPTIVE,
        similarity_threshold=0.80,
        enable_semantic_matching=True,
        enable_compression=True
    )
    
    # Initialize cache manager
    cache_manager = IntelligentCacheManager(config)
    
    try:
        await cache_manager.initialize()
        print("✓ Cache manager initialized successfully")
        print()
        
        print("1. Basic Cache Operations")
        print("-" * 40)
        
        # Legal document analysis scenario (Lawstronaut)
        legal_prompt = "Analyze the liability clause in this contract: 'Party A shall be liable for direct damages only, excluding consequential or punitive damages.'"
        legal_response = {
            "analysis": "This is a limited liability clause that restricts damages to direct damages only...",
            "risk_level": "medium",
            "recommendations": ["Consider adding caps on liability amounts", "Define 'direct damages' clearly"]
        }
        
        # Test cache miss
        cached_response = await cache_manager.get_response(legal_prompt, "gpt-4o")
        print(f"Initial cache lookup (expected miss): {'Hit' if cached_response else 'Miss'}")
        
        # Store response
        stored = await cache_manager.store_response(
            legal_prompt, "gpt-4o", legal_response,
            Decimal("0.05"), quality_score=0.95,
            tags={"legal", "liability", "contract_analysis"}
        )
        print(f"Response stored: {stored}")
        
        # Test cache hit
        cached_response = await cache_manager.get_response(legal_prompt, "gpt-4o")
        print(f"Subsequent cache lookup (expected hit): {'Hit' if cached_response else 'Miss'}")
        print()
        
        print("2. Semantic Similarity Matching")
        print("-" * 40)
        
        # Similar but not identical prompt
        similar_prompt = "What are the risks in this liability clause: 'The first party is only responsible for direct damages and excludes consequential or punitive damages.'"
        
        similar_response = await cache_manager.get_response(similar_prompt, "gpt-4o")
        print(f"Semantic similarity match: {'Hit' if similar_response else 'Miss'}")
        
        if similar_response:
            print(f"Matched response type: {type(similar_response)}")
            print(f"Response keys: {list(similar_response.keys()) if isinstance(similar_response, dict) else 'N/A'}")
        print()
        
        print("3. Multi-Model Caching")
        print("-" * 40)
        
        # Customer service scenarios (Optimizely)
        customer_queries = [
            ("How do I set up A/B testing?", "gpt-3.5-turbo", Decimal("0.01")),
            ("What metrics should I track for optimization?", "gpt-4o", Decimal("0.03")),
            ("How to implement personalization rules?", "claude-3-5-sonnet-20241022", Decimal("0.02")),
            ("Why is my conversion rate dropping?", "gpt-3.5-turbo", Decimal("0.01")),
            ("How to configure audience targeting?", "gpt-4o", Decimal("0.04"))
        ]
        
        print(f"Caching {len(customer_queries)} customer service responses...")
        
        for query, model, cost in customer_queries:
            response = {
                "answer": f"Here's how to {query.lower()}...",
                "confidence": 0.9,
                "related_docs": ["user_guide.pdf", "api_reference.md"],
                "model_used": model
            }
            
            await cache_manager.store_response(
                query, model, response, cost, quality_score=0.85,
                tags={"customer_service", "optimization", "help"}
            )
        
        # Test retrieval
        test_query = customer_queries[0][0]  # First query
        test_model = customer_queries[0][1]
        retrieved = await cache_manager.get_response(test_query, test_model)
        print(f"Retrieved response for '{test_query[:30]}...': {'Success' if retrieved else 'Failed'}")
        print()
        
        print("4. Cache Warming with Precomputed Responses")
        print("-" * 40)
        
        # Define common prompt patterns for cache warming
        warm_patterns = [
            {
                "name": "contract_analysis",
                "category": "legal",
                "prompt_template": "Analyze this {contract_type} clause: '{clause_text}'",
                "model": "gpt-4o",
                "variations": [
                    {"contract_type": "liability", "clause_text": "Seller shall not be liable for indirect damages"},
                    {"contract_type": "termination", "clause_text": "Either party may terminate with 30 days notice"},
                    {"contract_type": "confidentiality", "clause_text": "All proprietary information must remain confidential"}
                ]
            },
            {
                "name": "optimization_help",
                "category": "customer_service",
                "prompt_template": "How do I {action} in {product}?",
                "model": "gpt-3.5-turbo",
                "variations": [
                    {"action": "set up conversion tracking", "product": "Optimizely"},
                    {"action": "create audience segments", "product": "the platform"},
                    {"action": "implement feature flags", "product": "my application"}
                ]
            }
        ]
        
        await cache_manager.precompute_responses(warm_patterns)
        print("Cache warming completed")
        print()
        
        print("5. Performance Analysis and Optimization")
        print("-" * 40)
        
        # Get comprehensive statistics
        stats = await cache_manager.get_comprehensive_stats()
        
        print("Cache Performance Summary:")
        global_stats = stats["global_stats"]
        print(f"  Overall hit rate: {global_stats['overall_hit_rate']:.1%}")
        print(f"  Total requests: {global_stats['total_hits'] + global_stats['total_misses']}")
        print(f"  Cost savings: ${global_stats['total_cost_savings']:.4f}")
        
        print("\nMemory Cache:")
        memory_stats = stats["memory_cache"]
        print(f"  Entries: {memory_stats['entries']}")
        print(f"  Hit rate: {memory_stats['hit_rate']:.1%}")
        print(f"  Size: {memory_stats['size_bytes']} bytes")
        print(f"  Cost savings: ${memory_stats['cost_savings']:.4f}")
        
        print("\nConfiguration:")
        config_info = stats["configuration"]
        print(f"  Max memory size: {config_info['memory_max_size']}")
        print(f"  Default TTL: {config_info['default_ttl']}s")
        print(f"  Eviction strategy: {config_info['eviction_strategy']}")
        print(f"  Semantic matching: {config_info['semantic_matching_enabled']}")
        print()
        
        print("6. Cache Optimization Analysis")
        print("-" * 40)
        
        optimization_report = await cache_manager.optimize_cache_performance()
        
        print("Optimization Analysis:")
        if "analysis" in optimization_report:
            for key, value in optimization_report["analysis"].items():
                print(f"  {key}: {value}")
        
        if optimization_report["recommendations"]:
            print("\nRecommendations:")
            for rec in optimization_report["recommendations"]:
                print(f"  • {rec['type']}: {rec['reason']}")
                print(f"    Action: {rec['suggested_action']}")
        
        if optimization_report["actions_taken"]:
            print("\nActions Taken:")
            for action in optimization_report["actions_taken"]:
                print(f"  • {action}")
        print()
        
        print("7. Tag-Based Cache Management")
        print("-" * 40)
        
        # Demonstrate tag-based invalidation
        print("Invalidating all legal-related cache entries...")
        await cache_manager.invalidate_by_tags({"legal"})
        
        # Test if legal query is still cached
        legal_cached_after_invalidation = await cache_manager.get_response(legal_prompt, "gpt-4o")
        print(f"Legal query after invalidation: {'Still cached' if legal_cached_after_invalidation else 'Invalidated'}")
        
        # Customer service queries should still be cached
        customer_cached_after_invalidation = await cache_manager.get_response(test_query, test_model)
        print(f"Customer query after invalidation: {'Still cached' if customer_cached_after_invalidation else 'Invalidated'}")
        print()
        
        print("8. Cache Layer Performance Comparison")
        print("-" * 40)
        
        # Time different cache operations
        import time
        
        # Memory cache performance
        start_time = time.time()
        for i in range(100):
            await cache_manager.get_response(f"Test query {i % 5}", "gpt-3.5-turbo")  # Should hit cache for repeated queries
        memory_time = time.time() - start_time
        
        print(f"100 memory cache operations: {memory_time:.3f}s ({memory_time*10:.1f}ms avg)")
        
        # Show cache efficiency
        final_stats = await cache_manager.get_comprehensive_stats()
        final_global = final_stats["global_stats"]
        print(f"Final hit rate: {final_global['overall_hit_rate']:.1%}")
        print(f"Total cost savings: ${final_global['total_cost_savings']:.4f}")
        
    except Exception as e:
        print(f"Error during cache demonstration: {e}")
        logging.error(f"Cache demonstration error: {e}")
    
    finally:
        # Cleanup
        await cache_manager.cleanup()
        print("\n=== Intelligent caching system demonstration completed ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    asyncio.run(demonstrate_intelligent_caching_system())
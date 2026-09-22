"""
Advanced Function Programming with functools for Enterprise Systems

This module demonstrates sophisticated caching, decorators, and function composition
patterns applied to realistic scenarios like those used at Lawstronaut (legal document
processing) and Optimizely (AI-powered platforms) for performance optimization.

Key concepts covered:
- Production-grade caching strategies with @lru_cache and custom cache implementations
- Decorator factories for cross-cutting concerns (auth, rate limiting, monitoring)
- Partial application and function composition for business logic
- Performance monitoring and metrics collection through decorators
- Memory-efficient memoization patterns for expensive computations

Real-world applications:
- Legal document NLP processing with intelligent caching
- A/B testing result analysis with cached statistical computations
- API rate limiting and authentication systems
- Performance monitoring and observability patterns

Author: Technical Interview Preparation Guide
"""

from functools import (
    lru_cache, cache, cached_property, partial, reduce, singledispatch,
    wraps, update_wrapper, WRAPPER_ASSIGNMENTS, WRAPPER_UPDATES
)
from typing import (
    Dict, Any, List, Optional, Callable, TypeVar, Union, Tuple, 
    Protocol, runtime_checkable
)
from dataclasses import dataclass, field
import time
import threading
import logging
import weakref
import hashlib
import json
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio
import inspect
from collections import OrderedDict, defaultdict
import heapq
import sys
from contextlib import contextmanager
import pickle

# =============================================================================
# PRODUCTION-GRADE CACHING STRATEGIES
# =============================================================================

F = TypeVar('F', bound=Callable[..., Any])

@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_calls: int = 0
    average_hit_time: float = 0.0
    average_miss_time: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        return (self.hits / self.total_calls * 100) if self.total_calls > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary for logging/monitoring."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'total_calls': self.total_calls,
            'hit_rate': self.hit_rate,
            'average_hit_time_ms': self.average_hit_time * 1000,
            'average_miss_time_ms': self.average_miss_time * 1000
        }

class TTLCache:
    """
    Time-To-Live cache implementation for enterprise systems.
    
    Provides automatic expiration, memory management, and performance
    monitoring for cached computations in production environments.
    """
    
    def __init__(self, maxsize: int = 1000, ttl_seconds: float = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
    
    def _is_expired(self, key: Any) -> bool:
        """Check if cache entry has expired."""
        if key not in self._timestamps:
            return True
        return time.time() - self._timestamps[key] > self.ttl_seconds
    
    def _evict_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                self._stats.evictions += 1
    
    def get(self, key: Any, default: Any = None) -> Any:
        """Get value from cache with TTL check."""
        with self._lock:
            if key in self._cache and not self._is_expired(key):
                # Move to end (LRU behavior)
                self._cache.move_to_end(key)
                return self._cache[key]
            
            return default
    
    def put(self, key: Any, value: Any):
        """Put value in cache with timestamp."""
        with self._lock:
            # Remove expired entries
            self._evict_expired()
            
            # Evict oldest if at capacity
            if len(self._cache) >= self.maxsize and key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                self._stats.evictions += 1
            
            # Add/update entry
            self._cache[key] = value
            self._timestamps[key] = time.time()
            
            # Move to end if updating existing key
            if key in self._cache:
                self._cache.move_to_end(key)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self._stats

def intelligent_cache(maxsize: int = 1000, ttl_seconds: float = 3600, 
                     typed: bool = False, stats: bool = True):
    """
    Intelligent caching decorator with TTL, statistics, and monitoring.
    
    Combines LRU eviction with time-based expiration for production systems
    that need both memory management and data freshness.
    """
    def decorator(func: F) -> F:
        cache_instance = TTLCache(maxsize, ttl_seconds)
        
        def _make_key(*args, **kwargs):
            """Create cache key from function arguments."""
            key_parts = [args]
            if kwargs:
                key_parts.append(tuple(sorted(kwargs.items())))
            if typed:
                key_parts.extend([type(arg) for arg in args])
                key_parts.extend([type(val) for val in kwargs.values()])
            
            # Use hash for large keys to avoid memory issues
            key_str = str(key_parts)
            if len(key_str) > 200:
                return hashlib.md5(key_str.encode()).hexdigest()
            return key_str
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(*args, **kwargs)
            
            # Check cache first
            start_time = time.perf_counter()
            cached_result = cache_instance.get(key)
            
            if cached_result is not None:
                if stats:
                    hit_time = time.perf_counter() - start_time
                    cache_instance._stats.hits += 1
                    cache_instance._stats.total_calls += 1
                    
                    # Update running average hit time
                    total_hit_time = (cache_instance._stats.average_hit_time * 
                                    (cache_instance._stats.hits - 1) + hit_time)
                    cache_instance._stats.average_hit_time = total_hit_time / cache_instance._stats.hits
                
                return cached_result
            
            # Cache miss - compute result
            result = func(*args, **kwargs)
            
            if stats:
                miss_time = time.perf_counter() - start_time
                cache_instance._stats.misses += 1
                cache_instance._stats.total_calls += 1
                
                # Update running average miss time
                total_miss_time = (cache_instance._stats.average_miss_time * 
                                 (cache_instance._stats.misses - 1) + miss_time)
                cache_instance._stats.average_miss_time = total_miss_time / cache_instance._stats.misses
            
            # Store in cache
            cache_instance.put(key, result)
            return result
        
        # Attach cache management methods
        wrapper.cache_info = lambda: cache_instance.get_stats()
        wrapper.cache_clear = cache_instance.clear
        wrapper.cache_get = cache_instance.get
        
        return wrapper
    
    return decorator

class LegalDocumentNLPProcessor:
    """
    Legal document NLP processing with intelligent caching.
    
    Demonstrates production-grade caching for expensive NLP computations
    commonly used in legal document analysis systems.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    @intelligent_cache(maxsize=5000, ttl_seconds=7200)  # 2 hour TTL
    def extract_legal_entities(self, document_text: str) -> Dict[str, List[str]]:
        """
        Extract legal entities from document text with caching.
        
        Expensive NLP operation that benefits from caching across user sessions.
        """
        # Simulate expensive NLP processing
        time.sleep(0.1)  # Simulate processing time
        
        # Simple entity extraction simulation
        entities = {
            'cases': [],
            'statutes': [], 
            'organizations': [],
            'dates': []
        }
        
        # Extract case citations (simplified pattern matching)
        import re
        case_pattern = r'\b\d+\s+U\.S\.\s+\d+\b'
        entities['cases'] = re.findall(case_pattern, document_text)
        
        # Extract statute references
        statute_pattern = r'\b\d+\s+U\.S\.C\.\s+§\s*\d+\b'
        entities['statutes'] = re.findall(statute_pattern, document_text)
        
        # Extract organizations (simplified)
        org_keywords = ['Court', 'Corporation', 'LLC', 'Inc', 'Ltd']
        words = document_text.split()
        for i, word in enumerate(words):
            if any(keyword in word for keyword in org_keywords):
                context = ' '.join(words[max(0, i-2):i+3])
                entities['organizations'].append(context.strip())
        
        # Extract dates (simplified)
        date_pattern = r'\b\d{1,2}/\d{1,2}/\d{4}\b|\b\w+\s+\d{1,2},\s+\d{4}\b'
        entities['dates'] = re.findall(date_pattern, document_text)
        
        return entities
    
    @lru_cache(maxsize=1000)
    def calculate_document_similarity(self, doc1_hash: str, doc2_hash: str) -> float:
        """
        Calculate document similarity with LRU caching.
        
        Uses built-in lru_cache for simple caching of similarity computations.
        """
        # Simulate expensive similarity computation
        time.sleep(0.05)
        
        # Simple hash-based similarity (in reality, would use embeddings)
        common_chars = sum(1 for a, b in zip(doc1_hash, doc2_hash) if a == b)
        return common_chars / max(len(doc1_hash), len(doc2_hash))
    
    @cached_property
    def legal_stopwords(self) -> set:
        """
        Cached property for legal-specific stopwords.
        
        Demonstrates cached_property for expensive initialization.
        """
        # Simulate loading from file or API
        time.sleep(0.2)
        
        return {
            'thereof', 'hereof', 'whereof', 'heretofore', 'hereafter',
            'whereas', 'whereby', 'heretofore', 'hereinafter', 'aforesaid',
            'aforementioned', 'pursuant', 'notwithstanding', 'provided'
        }
    
    def get_cache_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get caching performance statistics for monitoring."""
        stats = {}
        
        # Get intelligent cache stats
        if hasattr(self.extract_legal_entities, 'cache_info'):
            stats['entity_extraction'] = self.extract_legal_entities.cache_info().to_dict()
        
        # Get LRU cache stats
        similarity_info = self.calculate_document_similarity.cache_info()
        stats['similarity_calculation'] = {
            'hits': similarity_info.hits,
            'misses': similarity_info.misses,
            'maxsize': similarity_info.maxsize,
            'currsize': similarity_info.currsize,
            'hit_rate': (similarity_info.hits / (similarity_info.hits + similarity_info.misses) * 100) 
                       if (similarity_info.hits + similarity_info.misses) > 0 else 0.0
        }
        
        return stats

# =============================================================================
# DECORATOR FACTORIES FOR ENTERPRISE CONCERNS
# =============================================================================

def rate_limit(calls_per_second: float, burst_size: int = 10):
    """
    Rate limiting decorator for API endpoints and external service calls.
    
    Uses token bucket algorithm for smooth rate limiting with burst capacity.
    """
    def decorator(func: F) -> F:
        last_called = [0.0]
        tokens = [float(burst_size)]
        lock = threading.Lock()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                now = time.time()
                time_passed = now - last_called[0]
                last_called[0] = now
                
                # Add tokens based on time passed
                tokens[0] = min(burst_size, tokens[0] + time_passed * calls_per_second)
                
                # Check if we have tokens available
                if tokens[0] < 1.0:
                    sleep_time = (1.0 - tokens[0]) / calls_per_second
                    time.sleep(sleep_time)
                    tokens[0] = 0.0
                else:
                    tokens[0] -= 1.0
                
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def monitor_performance(metric_name: str, logger: logging.Logger = None):
    """
    Performance monitoring decorator with detailed metrics collection.
    
    Tracks execution time, memory usage, and call frequency for
    production monitoring and alerting.
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    def decorator(func: F) -> F:
        call_count = [0]
        total_time = [0.0]
        max_time = [0.0]
        min_time = [float('inf')]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            start_memory = sys.getsizeof(args) + sys.getsizeof(kwargs)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.perf_counter() - start_time
                
                # Update statistics
                call_count[0] += 1
                total_time[0] += execution_time
                max_time[0] = max(max_time[0], execution_time)
                min_time[0] = min(min_time[0], execution_time)
                
                # Log performance metrics
                avg_time = total_time[0] / call_count[0]
                
                if call_count[0] % 100 == 0:  # Log every 100 calls
                    logger.info(f"Performance [{metric_name}]: "
                              f"calls={call_count[0]}, "
                              f"avg_time={avg_time:.4f}s, "
                              f"max_time={max_time[0]:.4f}s, "
                              f"min_time={min_time[0]:.4f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.perf_counter() - start_time
                logger.error(f"Performance [{metric_name}] ERROR: "
                           f"failed after {execution_time:.4f}s: {e}")
                raise
        
        # Attach statistics access
        wrapper.get_stats = lambda: {
            'call_count': call_count[0],
            'total_time': total_time[0],
            'average_time': total_time[0] / call_count[0] if call_count[0] > 0 else 0,
            'max_time': max_time[0] if max_time[0] != 0 else 0,
            'min_time': min_time[0] if min_time[0] != float('inf') else 0
        }
        
        return wrapper
    return decorator

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, 
                      max_delay: float = 60.0, backoff_factor: float = 2.0,
                      exceptions: Tuple[type, ...] = (Exception,)):
    """
    Retry decorator with exponential backoff for resilient systems.
    
    Implements sophisticated retry logic for external service calls
    with configurable backoff strategy and exception handling.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed
                        logging.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    logging.warning(f"Function {func.__name__} attempt {attempt + 1} failed: {e}. "
                                  f"Retrying in {delay:.2f} seconds...")
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator

def authenticated(required_role: str = None):
    """
    Authentication decorator for API endpoints.
    
    Demonstrates security pattern implementation using decorators
    for role-based access control.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # In a real system, this would validate JWT tokens, check session, etc.
            # For demo purposes, we'll check a mock authentication context
            
            # Mock authentication check
            auth_context = kwargs.get('auth_context', {})
            user_role = auth_context.get('role')
            
            if not auth_context.get('authenticated', False):
                raise PermissionError("Authentication required")
            
            if required_role and user_role != required_role:
                raise PermissionError(f"Role '{required_role}' required, got '{user_role}'")
            
            # Authentication passed, execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# =============================================================================
# PARTIAL APPLICATION AND FUNCTION COMPOSITION
# =============================================================================

class ABTestingAnalytics:
    """
    A/B testing analytics using functional programming patterns.
    
    Demonstrates partial application and function composition for
    statistical computations in experiment analysis.
    """
    
    def __init__(self):
        # Pre-configured statistical functions using partial application
        self.confidence_intervals = {
            '90%': partial(self._calculate_confidence_interval, confidence=0.90),
            '95%': partial(self._calculate_confidence_interval, confidence=0.95), 
            '99%': partial(self._calculate_confidence_interval, confidence=0.99)
        }
        
        # Composed analysis pipelines
        self.standard_analysis = self._compose_analysis_pipeline([
            self._calculate_conversion_rate,
            self._calculate_statistical_significance,
            self.confidence_intervals['95%'],
            self._calculate_effect_size
        ])
    
    def _calculate_conversion_rate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate conversion rate for experiment variant."""
        conversions = data.get('conversions', 0)
        visitors = data.get('visitors', 0)
        
        rate = conversions / visitors if visitors > 0 else 0.0
        
        return {
            **data,
            'conversion_rate': rate,
            'conversion_percentage': rate * 100
        }
    
    def _calculate_statistical_significance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistical significance using z-test."""
        import math
        
        # Mock statistical significance calculation
        # In practice, would use proper statistical libraries
        control_rate = data.get('control_conversion_rate', 0.05)
        treatment_rate = data.get('conversion_rate', 0.05)
        sample_size = data.get('visitors', 1000)
        
        # Simplified z-test calculation
        pooled_rate = (control_rate + treatment_rate) / 2
        se = math.sqrt(2 * pooled_rate * (1 - pooled_rate) / sample_size)
        z_score = abs(treatment_rate - control_rate) / se if se > 0 else 0
        
        # Mock p-value calculation (simplified)
        p_value = max(0.001, 0.5 - abs(z_score) * 0.1)
        significant = p_value < 0.05
        
        return {
            **data,
            'z_score': z_score,
            'p_value': p_value,
            'statistically_significant': significant
        }
    
    def _calculate_confidence_interval(self, data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Calculate confidence interval for conversion rate."""
        import math
        
        rate = data.get('conversion_rate', 0)
        n = data.get('visitors', 0)
        
        if n == 0:
            return {**data, 'confidence_interval': (0, 0)}
        
        # Wilson score interval (more accurate than normal approximation)
        z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
        
        p = rate
        n_eff = n + z**2
        p_eff = (n * p + 0.5 * z**2) / n_eff
        margin = z * math.sqrt((p_eff * (1 - p_eff)) / n_eff)
        
        ci_lower = max(0, p_eff - margin)
        ci_upper = min(1, p_eff + margin)
        
        return {
            **data,
            'confidence_interval': (ci_lower, ci_upper),
            'confidence_level': confidence
        }
    
    def _calculate_effect_size(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate effect size (Cohen's h for proportions)."""
        import math
        
        control_rate = data.get('control_conversion_rate', 0.05)
        treatment_rate = data.get('conversion_rate', 0.05)
        
        # Cohen's h for difference between proportions
        h = 2 * (math.asin(math.sqrt(treatment_rate)) - math.asin(math.sqrt(control_rate)))
        
        # Effect size interpretation
        if abs(h) < 0.2:
            effect_magnitude = "small"
        elif abs(h) < 0.5:
            effect_magnitude = "medium" 
        else:
            effect_magnitude = "large"
        
        return {
            **data,
            'effect_size': h,
            'effect_magnitude': effect_magnitude
        }
    
    def _compose_analysis_pipeline(self, functions: List[Callable]) -> Callable:
        """Compose multiple analysis functions into a single pipeline."""
        def pipeline(data: Dict[str, Any]) -> Dict[str, Any]:
            result = data
            for func in functions:
                result = func(result)
            return result
        
        return pipeline
    
    @lru_cache(maxsize=1000)
    def analyze_experiment_cached(self, experiment_id: str, variant_data: str) -> Dict[str, Any]:
        """
        Cached experiment analysis with serialized input for hashability.
        
        Demonstrates combining caching with functional programming patterns.
        """
        # Deserialize data for processing
        data = json.loads(variant_data)
        
        # Run standard analysis pipeline
        return self.standard_analysis(data)
    
    def create_custom_analyzer(self, confidence_level: float, 
                             include_effect_size: bool = True) -> Callable:
        """
        Create custom analysis function using partial application.
        
        Demonstrates factory pattern with functional programming.
        """
        # Build custom pipeline based on requirements
        pipeline_functions = [
            self._calculate_conversion_rate,
            self._calculate_statistical_significance,
            partial(self._calculate_confidence_interval, confidence=confidence_level)
        ]
        
        if include_effect_size:
            pipeline_functions.append(self._calculate_effect_size)
        
        return self._compose_analysis_pipeline(pipeline_functions)

# =============================================================================
# ADVANCED DECORATOR PATTERNS
# =============================================================================

class DecoratorChain:
    """
    Utility class for chaining decorators with configuration.
    
    Enables dynamic decorator composition based on runtime configuration.
    """
    
    def __init__(self):
        self.decorators = []
    
    def add(self, decorator_func: Callable, *args, **kwargs):
        """Add decorator to chain with arguments."""
        if args or kwargs:
            # Decorator with arguments
            self.decorators.append(partial(decorator_func, *args, **kwargs))
        else:
            # Simple decorator
            self.decorators.append(decorator_func)
        return self
    
    def apply(self, func: F) -> F:
        """Apply all decorators in chain to function."""
        decorated = func
        # Apply decorators in reverse order (last added applied first)
        for decorator in reversed(self.decorators):
            decorated = decorator(decorated)
        return decorated

# Single dispatch for polymorphic behavior
@singledispatch 
def serialize_for_cache(obj) -> str:
    """Generic serialization for cache keys."""
    return str(obj)

@serialize_for_cache.register
def _(obj: dict) -> str:
    """Serialize dictionary objects."""
    return json.dumps(obj, sort_keys=True, default=str)

@serialize_for_cache.register  
def _(obj: list) -> str:
    """Serialize list objects."""
    return json.dumps(obj, default=str)

@serialize_for_cache.register
def _(obj: tuple) -> str:
    """Serialize tuple objects."""  
    return json.dumps(list(obj), default=str)

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

def demonstrate_functools_enterprise_patterns():
    """
    Comprehensive demonstration of functools enterprise patterns
    for production systems optimization.
    """
    
    print("=== Advanced Function Programming with functools for Enterprise Systems ===\n")
    
    # 1. Intelligent Caching for Legal Document Processing
    print("1. Intelligent Caching for Legal Document NLP Processing")
    
    nlp_processor = LegalDocumentNLPProcessor()
    
    # Sample legal document text
    sample_document = """
    In the case of Smith v. Jones, 123 U.S. 456 (2020), the Supreme Court
    ruled on the interpretation of 42 U.S.C. § 1983. The Corporation filed
    a motion on January 15, 2020, pursuant to the aforementioned statute.
    The Court noted that the plaintiff's claims were notwithstanding the
    defendant's arguments.
    """
    
    # Test caching performance
    print("Testing entity extraction with caching:")
    
    # First call (cache miss)
    start_time = time.perf_counter()
    entities_1 = nlp_processor.extract_legal_entities(sample_document)
    first_call_time = time.perf_counter() - start_time
    
    # Second call (cache hit)
    start_time = time.perf_counter()
    entities_2 = nlp_processor.extract_legal_entities(sample_document)
    second_call_time = time.perf_counter() - start_time
    
    print(f"First call (cache miss): {first_call_time:.4f}s")
    print(f"Second call (cache hit): {second_call_time:.4f}s")
    print(f"Cache speedup: {first_call_time / second_call_time:.1f}x faster")
    print(f"Extracted entities: {len(entities_1['cases'])} cases, "
          f"{len(entities_1['statutes'])} statutes")
    
    # Show cache performance
    cache_performance = nlp_processor.get_cache_performance()
    print(f"Cache performance: {cache_performance}")
    
    # 2. Decorator Factories for Cross-Cutting Concerns
    print("\n2. Production Decorator Factories")
    
    # Create decorated function with multiple concerns
    @rate_limit(calls_per_second=5.0, burst_size=10)
    @monitor_performance(metric_name="legal_search_api")
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    @authenticated(required_role="analyst")
    def search_legal_database(query: str, auth_context: Dict[str, Any]) -> Dict[str, Any]:
        """Mock legal database search with all enterprise concerns."""
        # Simulate some processing time
        time.sleep(0.05)
        
        # Simulate occasional failures for retry demo
        import random
        if random.random() < 0.1:  # 10% failure rate
            raise ConnectionError("Database connection failed")
        
        return {
            'query': query,
            'results_count': random.randint(10, 100),
            'processing_time': 0.05
        }
    
    # Test decorated function
    print("Testing decorated legal database search:")
    
    auth_context = {'authenticated': True, 'role': 'analyst'}
    success_count = 0
    
    for i in range(10):
        try:
            result = search_legal_database(f"search query {i}", auth_context=auth_context)
            success_count += 1
            if i % 3 == 0:  # Show some results
                print(f"  Query {i}: {result['results_count']} results found")
        except Exception as e:
            print(f"  Query {i}: Failed - {e}")
    
    print(f"Successful queries: {success_count}/10")
    
    # Show performance statistics
    if hasattr(search_legal_database, 'get_stats'):
        perf_stats = search_legal_database.get_stats()
        print(f"Performance stats: {perf_stats}")
    
    # 3. A/B Testing Analytics with Functional Programming
    print("\n3. A/B Testing Analytics with Functional Programming")
    
    ab_analytics = ABTestingAnalytics()
    
    # Sample experiment data
    control_data = {
        'variant': 'control',
        'visitors': 10000,
        'conversions': 500,
        'control_conversion_rate': 0.05
    }
    
    treatment_data = {
        'variant': 'treatment',
        'visitors': 10000, 
        'conversions': 580,
        'control_conversion_rate': 0.05
    }
    
    # Analyze experiments
    print("A/B Testing Analysis Results:")
    
    for data in [control_data, treatment_data]:
        analysis = ab_analytics.standard_analysis(data)
        
        print(f"\n{data['variant'].title()} Variant:")
        print(f"  Conversion rate: {analysis['conversion_percentage']:.2f}%")
        print(f"  Confidence interval: ({analysis['confidence_interval'][0]:.3f}, "
              f"{analysis['confidence_interval'][1]:.3f})")
        print(f"  Statistically significant: {analysis['statistically_significant']}")
        
        if 'effect_size' in analysis:
            print(f"  Effect size: {analysis['effect_size']:.3f} ({analysis['effect_magnitude']})")
    
    # Test cached analysis
    cached_result = ab_analytics.analyze_experiment_cached(
        'exp_001', json.dumps(treatment_data)
    )
    print(f"\nCached analysis result: {cached_result['conversion_percentage']:.2f}%")
    
    # Test custom analyzer
    custom_analyzer = ab_analytics.create_custom_analyzer(
        confidence_level=0.99, include_effect_size=False
    )
    custom_result = custom_analyzer(treatment_data)
    print(f"Custom 99% confidence analysis: {custom_result['confidence_interval']}")
    
    # 4. Decorator Chaining and Composition
    print("\n4. Dynamic Decorator Chaining")
    
    # Create decorator chain based on configuration
    config = {
        'enable_caching': True,
        'enable_monitoring': True,
        'enable_rate_limiting': True,
        'rate_limit': 10.0
    }
    
    decorator_chain = DecoratorChain()
    
    if config.get('enable_caching'):
        decorator_chain.add(lru_cache, maxsize=100)
    
    if config.get('enable_monitoring'):
        decorator_chain.add(monitor_performance, metric_name="dynamic_function")
    
    if config.get('enable_rate_limiting'):
        decorator_chain.add(rate_limit, calls_per_second=config['rate_limit'])
    
    # Apply chain to function
    @decorator_chain.apply
    def process_document(doc_id: str) -> Dict[str, Any]:
        """Process document with dynamically applied decorators."""
        time.sleep(0.01)  # Simulate processing
        return {'doc_id': doc_id, 'processed': True, 'timestamp': time.time()}
    
    # Test dynamic decoration
    print("Testing dynamically decorated function:")
    
    start_time = time.perf_counter()
    for i in range(20):
        result = process_document(f"doc_{i % 5}")  # Some cache hits
        if i % 5 == 0:
            print(f"  Processed: {result['doc_id']}")
    
    total_time = time.perf_counter() - start_time
    print(f"Total processing time: {total_time:.4f}s")
    
    # Show cache statistics
    cache_info = process_document.cache_info()
    print(f"Cache statistics: hits={cache_info.hits}, misses={cache_info.misses}, "
          f"hit_rate={cache_info.hits / (cache_info.hits + cache_info.misses) * 100:.1f}%")
    
    # 5. Performance Comparison
    print("\n5. Caching Performance Comparison")
    
    def expensive_computation(n: int) -> int:
        """Simulate expensive computation."""
        time.sleep(0.01)  # Simulate work
        return sum(i * i for i in range(n))
    
    # Test without caching
    start_time = time.perf_counter()
    for i in range(50):
        result = expensive_computation(i % 10)
    no_cache_time = time.perf_counter() - start_time
    
    # Test with LRU cache
    cached_computation = lru_cache(maxsize=128)(expensive_computation)
    
    start_time = time.perf_counter()
    for i in range(50):
        result = cached_computation(i % 10)
    lru_cache_time = time.perf_counter() - start_time
    
    print(f"Without caching: {no_cache_time:.4f}s")
    print(f"With LRU cache: {lru_cache_time:.4f}s")
    print(f"Performance improvement: {no_cache_time / lru_cache_time:.1f}x faster")
    
    cache_stats = cached_computation.cache_info()
    print(f"LRU cache hit rate: {cache_stats.hits / (cache_stats.hits + cache_stats.misses) * 100:.1f}%")
    
    print("\n=== All functools enterprise patterns successfully demonstrated ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    demonstrate_functools_enterprise_patterns()
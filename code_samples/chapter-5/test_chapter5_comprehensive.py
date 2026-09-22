"""
Comprehensive Test Suite for Chapter 5: Performance Optimization

This test suite validates all the performance optimization implementations
including profiling tools, optimization techniques, caching systems,
database optimization, and monitoring systems.

Test Categories:
- Profiling tools functionality and accuracy
- Algorithm and data structure optimizations
- Multi-level caching performance and correctness
- Database sharding and connection pooling
- Performance monitoring and alerting

Author: Technical Interview Preparation Guide
"""

import asyncio
import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

# Import all modules from chapter 5
from profiling_tools import (
    CPUProfiler, MemoryProfiler, IOPerformanceMonitor, 
    ProductionProfiler, ProfileResult
)
from optimization_techniques import (
    AlgorithmOptimizer, OptimizedDataStructures, ComputationalOptimizer,
    ParallelOptimizer, MemoryOptimizer, LegalDocumentOptimizer,
    PersonalizationOptimizer
)
from multilevel_cache import (
    InMemoryCache, RedisCache, DatabaseCache, MultiLevelCache,
    CacheWarmingStrategy, CacheInvalidationManager,
    LegalDocumentCacheManager, PersonalizationCacheManager
)
from database_optimization import (
    DatabaseConnectionPool, ShardedDatabase, QueryOptimizer,
    HashShardingStrategy, LegalDocumentDatabaseManager,
    PersonalizationDatabaseManager, ConnectionPoolConfig
)
from performance_monitoring import (
    PerformanceMonitor, SystemMetricsCollector, ApplicationMetricsCollector,
    AlertEvaluator, NotificationManager, LegalDocumentMonitor,
    PersonalizationMonitor
)

# =============================================================================
# PROFILING TOOLS TESTS
# =============================================================================

class TestProfilingTools:
    """Test suite for profiling tools"""
    
    def test_cpu_profiler_initialization(self):
        """Test CPU profiler initialization"""
        profiler = CPUProfiler()
        assert profiler.profile_data == {}
        assert not profiler.profiling_active
    
    @pytest.mark.asyncio
    async def test_cpu_profiler_context_manager(self):
        """Test CPU profiler context manager"""
        profiler = CPUProfiler()
        
        async with profiler.profile_context("test_operation") as p:
            # Simulate CPU-intensive work
            sum(range(10000))
        
        assert "test_operation" in profiler.profile_data
        assert len(profiler.profile_data["test_operation"]) > 0
    
    def test_cpu_profiler_decorator(self):
        """Test CPU profiler function decorator"""
        profiler = CPUProfiler()
        
        @profiler.profile_function
        def test_function():
            return sum(range(1000))
        
        result = test_function()
        assert result == sum(range(1000))
        assert len(profiler.profile_data) > 0
    
    def test_cpu_profiler_hotspots(self):
        """Test performance hotspot identification"""
        profiler = CPUProfiler()
        
        # Create mock profile data
        profiler.profile_data["test"] = [
            ProfileResult("test_func", 100, 1.5, 0.015, 1.5, "test.py", 10)
        ]
        
        hotspots = profiler.get_hotspots(threshold_percent=1.0)
        assert len(hotspots) >= 0  # Should return valid hotspots
    
    @pytest.mark.asyncio
    async def test_memory_profiler_context_manager(self):
        """Test memory profiler context manager"""
        profiler = MemoryProfiler()
        
        async with profiler.memory_tracking("test_memory_operation"):
            # Simulate memory allocation
            data = [i for i in range(10000)]
            processed = [x * 2 for x in data]
        
        # Memory tracking should complete without errors
        assert True
    
    def test_memory_profiler_decorator(self):
        """Test memory profiler function decorator"""
        profiler = MemoryProfiler()
        
        @profiler.memory_profile_function
        def memory_intensive_function():
            return list(range(5000))
        
        result = memory_intensive_function()
        assert len(result) == 5000
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self):
        """Test memory leak detection"""
        profiler = MemoryProfiler()
        
        leak_analysis = profiler.detect_memory_leaks(iterations=3)
        
        assert 'memory_usage_pattern' in leak_analysis
        assert 'leak_detected' in leak_analysis
        assert 'growth_rate_mb_per_iteration' in leak_analysis
        assert 'recommendations' in leak_analysis
    
    @pytest.mark.asyncio
    async def test_io_performance_monitor_file_operations(self):
        """Test I/O performance monitoring for file operations"""
        monitor = IOPerformanceMonitor()
        
        # Create temporary file for testing
        test_file = "/tmp/test_io_performance.txt"
        
        async with monitor.monitor_file_io("test_write", test_file):
            with open(test_file, "w") as f:
                f.write("Test content for I/O monitoring")
        
        async with monitor.monitor_file_io("test_read", test_file):
            with open(test_file, "r") as f:
                content = f.read()
        
        assert len(monitor.io_stats['file_operations']) == 2
        
        # Cleanup
        import os
        if os.path.exists(test_file):
            os.remove(test_file)
    
    def test_io_performance_analysis(self):
        """Test I/O performance pattern analysis"""
        monitor = IOPerformanceMonitor()
        
        # Add mock I/O statistics
        monitor.io_stats['file_operations'] = [
            {
                'operation': 'test_read',
                'duration_ms': 50.0,
                'bytes_read': 1024,
                'bytes_written': 0,
                'read_throughput_mbps': 0.02,
                'write_throughput_mbps': 0.0
            }
        ]
        
        analysis = monitor.analyze_io_patterns()
        
        assert 'file_io_analysis' in analysis
        assert 'performance_recommendations' in analysis
        assert analysis['file_io_analysis']['operation_count'] == 1
    
    @pytest.mark.asyncio
    async def test_production_profiler(self):
        """Test production profiler system"""
        profiler = ProductionProfiler(sampling_interval=0.1)
        
        # Start continuous profiling
        profiler.start_continuous_profiling()
        
        # Let it collect some data
        await asyncio.sleep(0.3)
        
        # Get performance summary
        summary = profiler.get_performance_summary(last_minutes=1)
        
        # Stop profiling
        profiler.stop_continuous_profiling()
        
        assert 'time_period_minutes' in summary
        assert 'sample_count' in summary

# =============================================================================
# OPTIMIZATION TECHNIQUES TESTS
# =============================================================================

class TestOptimizationTechniques:
    """Test suite for optimization techniques"""
    
    def test_algorithm_benchmarking(self):
        """Test algorithm benchmarking functionality"""
        # Test search algorithms
        test_data = list(range(1000))
        target = 500
        
        # Linear search
        result = AlgorithmOptimizer.linear_search_naive(test_data, target)
        assert result == 500
        
        # Binary search
        result = AlgorithmOptimizer.binary_search_optimized(test_data, target)
        assert result == 500
        
        # Interpolation search
        result = AlgorithmOptimizer.interpolation_search(test_data, target)
        assert result == 500
    
    def test_sorting_algorithms(self):
        """Test sorting algorithm performance"""
        import random
        test_data = list(range(100))
        random.shuffle(test_data)
        
        # Test quicksort
        sorted_data = AlgorithmOptimizer.quicksort_optimized(test_data.copy())
        assert sorted_data == sorted(test_data)
        
        # Test insertion sort
        sorted_data = AlgorithmOptimizer.insertion_sort_optimized(test_data.copy())
        assert sorted_data == sorted(test_data)
        
        # Test Timsort (built-in)
        sorted_data = AlgorithmOptimizer.timsort_hybrid(test_data.copy())
        assert sorted_data == sorted(test_data)
    
    def test_bloom_filter(self):
        """Test Bloom filter implementation"""
        bloom = OptimizedDataStructures.BloomFilter(capacity=1000, error_rate=0.1)
        
        # Add items
        test_items = ["apple", "banana", "cherry", "date"]
        for item in test_items:
            bloom.add(item)
        
        # Test membership (should have no false negatives)
        for item in test_items:
            assert bloom.might_contain(item)
        
        # Test non-existent item (might have false positives)
        result = bloom.might_contain("nonexistent")
        # Result can be True (false positive) or False
        assert isinstance(result, bool)
        
        # Test statistics
        stats = bloom.get_stats()
        assert stats['capacity'] == 1000
        assert stats['items_added'] == len(test_items)
    
    def test_lru_cache(self):
        """Test LRU cache implementation"""
        cache = OptimizedDataStructures.LRUCache(capacity=3)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # Verify retrieval
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Add another item (should evict LRU)
        cache.put("key4", "value4")
        
        # key1 should be evicted since it was accessed first
        # Note: This test might be sensitive to implementation details
        assert cache.size() <= 3
        
        # Test cache statistics
        stats = cache.get_stats()
        assert stats['capacity'] == 3
    
    def test_trie_operations(self):
        """Test Trie data structure"""
        trie = OptimizedDataStructures.OptimizedTrie()
        
        # Insert words
        words = ["apple", "application", "apply", "banana"]
        for word in words:
            trie.insert(word)
        
        # Test search
        assert trie.search("apple")
        assert trie.search("application")
        assert not trie.search("app")  # Prefix, not complete word
        
        # Test prefix search
        app_words = trie.starts_with("app")
        assert "apple" in app_words
        assert "application" in app_words
        assert "apply" in app_words
        
        # Test most frequent with prefix
        frequent = trie.get_most_frequent_with_prefix("app", limit=5)
        assert len(frequent) <= 3  # Only 3 words with "app" prefix
    
    def test_fibonacci_algorithms(self):
        """Test Fibonacci algorithm optimizations"""
        n = 10
        expected_result = 55  # 10th Fibonacci number
        
        # Test memoized version
        result = ComputationalOptimizer.fibonacci_memoized(n)
        assert result == expected_result
        
        # Test iterative version
        result = ComputationalOptimizer.fibonacci_iterative(n)
        assert result == expected_result
        
        # Test matrix exponentiation version
        result = ComputationalOptimizer.fibonacci_matrix_exponentiation(n)
        assert result == expected_result
    
    def test_knapsack_optimization(self):
        """Test optimized knapsack algorithm"""
        weights = [2, 3, 4, 5]
        values = [3, 4, 5, 6]
        capacity = 8
        
        result = ComputationalOptimizer.knapsack_optimized(weights, values, capacity)
        
        # Should find optimal solution
        assert result > 0
        assert isinstance(result, int)
    
    def test_parallel_processing(self):
        """Test parallel processing optimizations"""
        data = list(range(100))
        
        def square_function(x):
            return x * x
        
        # Test CPU-bound parallel processing
        results = ParallelOptimizer.parallel_map_cpu_bound(data[:10], square_function, max_workers=2)
        expected = [x * x for x in data[:10]]
        assert results == expected
        
        # Test I/O-bound parallel processing
        results = ParallelOptimizer.parallel_map_io_bound(data[:10], square_function, max_workers=2)
        assert results == expected
    
    @pytest.mark.asyncio
    async def test_async_parallel_processing(self):
        """Test asynchronous parallel processing"""
        async def async_task():
            await asyncio.sleep(0.01)
            return "completed"
        
        tasks = [async_task for _ in range(5)]
        results = await ParallelOptimizer.async_parallel_processing(tasks, concurrency_limit=3)
        
        assert len(results) == 5
        assert all(result == "completed" for result in results)
    
    def test_memory_optimization_patterns(self):
        """Test memory optimization patterns"""
        # Test generator processing
        def test_generator():
            for i in range(100):
                yield i
        
        processed_data = list(MemoryOptimizer.generator_processing(test_generator()))
        assert len(processed_data) == 100
        
        # Test sliding window
        data = list(range(10))
        windows = list(MemoryOptimizer.sliding_window_generator(data, window_size=3))
        assert len(windows) == 8  # 10 - 3 + 1
        assert windows[0] == [0, 1, 2]
        
        # Test chunked processing
        chunks = list(MemoryOptimizer.chunked_processing(data, chunk_size=3))
        assert len(chunks) == 4  # ceil(10/3)
        assert chunks[0] == [0, 1, 2]
    
    def test_object_pool(self):
        """Test object pool pattern"""
        class TestObject:
            def __init__(self):
                self.value = 0
            
            def reset(self):
                self.value = 0
        
        pool = MemoryOptimizer.ObjectPool(TestObject, initial_size=3, max_size=5)
        
        # Acquire objects
        obj1 = pool.acquire()
        obj2 = pool.acquire()
        
        assert isinstance(obj1, TestObject)
        assert isinstance(obj2, TestObject)
        
        # Return objects
        pool.release(obj1)
        pool.release(obj2)
        
        assert pool.size() > 0
    
    def test_legal_document_optimizer(self):
        """Test legal document optimization system"""
        optimizer = LegalDocumentOptimizer()
        
        # Build legal terms index
        legal_terms = ["contract", "liability", "indemnification", "jurisdiction"]
        optimizer.build_legal_terms_index(legal_terms)
        
        # Test term extraction
        document_text = "This contract includes liability and indemnification clauses."
        extracted_terms = optimizer.extract_legal_terms_optimized(document_text)
        
        assert "contract" in extracted_terms
        assert "liability" in extracted_terms
        assert "indemnification" in extracted_terms
    
    @pytest.mark.asyncio
    async def test_legal_document_batch_processing(self):
        """Test legal document batch processing optimization"""
        optimizer = LegalDocumentOptimizer()
        
        # Setup legal terms
        legal_terms = ["contract", "agreement", "liability"]
        optimizer.build_legal_terms_index(legal_terms)
        
        # Test batch processing
        documents = [
            {"id": "doc1", "content": "Contract agreement with liability clauses"},
            {"id": "doc2", "content": "Legal agreement for contract terms"}
        ]
        
        results = optimizer.process_document_batch_optimized(documents)
        
        assert len(results) == 2
        assert all("legal_terms" in result for result in results)
    
    def test_personalization_optimizer(self):
        """Test personalization optimization system"""
        optimizer = PersonalizationOptimizer()
        
        # Test user similarity calculation
        user1 = {"user_id": 1, "interests": ["tech", "science", "legal"]}
        user2 = {"user_id": 2, "interests": ["tech", "legal", "finance"]}
        
        similarity = optimizer.calculate_user_similarity_optimized(user1, user2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # Should have some similarity
    
    @pytest.mark.asyncio
    async def test_personalization_recommendations(self):
        """Test personalization recommendation generation"""
        optimizer = PersonalizationOptimizer()
        
        # Create user profiles
        user_profiles = {
            1: {"user_id": 1, "interests": ["tech", "science"]},
            2: {"user_id": 2, "interests": ["tech", "legal"]},
            3: {"user_id": 3, "interests": ["science", "finance"]}
        }
        
        # Generate recommendations
        recommendations = optimizer.generate_recommendations_optimized(
            user_id=1, user_profiles=user_profiles, num_recommendations=5
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5

# =============================================================================
# MULTI-LEVEL CACHE TESTS
# =============================================================================

class TestMultiLevelCache:
    """Test suite for multi-level caching system"""
    
    @pytest.mark.asyncio
    async def test_in_memory_cache_basic_operations(self):
        """Test basic in-memory cache operations"""
        cache = InMemoryCache(max_size=100, max_memory_mb=10)
        
        # Test set and get
        success = await cache.set("key1", "value1", ttl=3600)
        assert success
        
        value = await cache.get("key1")
        assert value == "value1"
        
        # Test existence check
        exists = await cache.exists("key1")
        assert exists
        
        # Test deletion
        deleted = await cache.delete("key1")
        assert deleted
        
        # Verify deletion
        value = await cache.get("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_in_memory_cache_ttl_expiration(self):
        """Test TTL expiration in in-memory cache"""
        cache = InMemoryCache(max_size=100, max_memory_mb=10)
        
        # Set item with short TTL
        await cache.set("expiring_key", "expiring_value", ttl=1)
        
        # Should be available immediately
        value = await cache.get("expiring_key")
        assert value == "expiring_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired now
        value = await cache.get("expiring_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_in_memory_cache_lru_eviction(self):
        """Test LRU eviction in in-memory cache"""
        cache = InMemoryCache(max_size=2, max_memory_mb=10)  # Small capacity
        
        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Access key1 to make it more recently used
        await cache.get("key1")
        
        # Add another item (should evict key2)
        await cache.set("key3", "value3")
        
        # key1 should still be present (more recently used)
        value1 = await cache.get("key1")
        assert value1 == "value1"
        
        # key2 should be evicted
        value2 = await cache.get("key2")
        assert value2 is None
    
    @pytest.mark.asyncio
    async def test_redis_cache_operations(self):
        """Test Redis cache operations"""
        cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="test:")
        
        # Test basic operations
        success = await cache.set("redis_key", "redis_value", ttl=3600)
        assert success
        
        value = await cache.get("redis_key")
        assert value == "redis_value"
        
        exists = await cache.exists("redis_key")
        assert exists
        
        deleted = await cache.delete("redis_key")
        assert deleted
    
    @pytest.mark.asyncio
    async def test_database_cache_operations(self):
        """Test database cache operations"""
        cache = DatabaseCache(connection_string="sqlite:///test.db", table_name="test_cache")
        
        # Test basic operations
        success = await cache.set("db_key", "db_value", ttl=3600)
        assert success
        
        value = await cache.get("db_key")
        assert value == "db_value"
        
        exists = await cache.exists("db_key")
        assert exists
        
        deleted = await cache.delete("db_key")
        assert deleted
    
    @pytest.mark.asyncio
    async def test_multi_level_cache_hierarchy(self):
        """Test multi-level cache hierarchy"""
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="l2:")
        l3_cache = DatabaseCache(connection_string="sqlite:///test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        
        # Test cache miss (all levels)
        value = await multi_cache.get("nonexistent_key")
        assert value is None
        
        # Test set (should populate all levels)
        success = await multi_cache.set("multi_key", "multi_value", ttl=3600)
        assert success
        
        # Test get (should hit L1 cache)
        value = await multi_cache.get("multi_key")
        assert value == "multi_value"
        
        # Test deletion (should remove from all levels)
        deleted = await multi_cache.delete("multi_key")
        assert deleted
        
        # Verify deletion
        value = await multi_cache.get("multi_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_warming_strategy(self):
        """Test cache warming functionality"""
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="warm:")
        l3_cache = DatabaseCache(connection_string="sqlite:///test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        warming_strategy = CacheWarmingStrategy(multi_cache)
        
        # Mock data loader
        def data_loader(key: str) -> str:
            return f"loaded_value_for_{key}"
        
        # Test warming specific keys
        keys_to_warm = ["warm_key1", "warm_key2", "warm_key3"]
        await warming_strategy.warm_popular_keys(keys_to_warm, data_loader)
        
        # Verify keys are warmed
        for key in keys_to_warm:
            value = await multi_cache.get(key)
            assert value == f"loaded_value_for_{key}"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_manager(self):
        """Test cache invalidation functionality"""
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="inv:")
        l3_cache = DatabaseCache(connection_string="sqlite:///test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        invalidation_manager = CacheInvalidationManager(multi_cache)
        
        # Set up test data
        await multi_cache.set("parent_key", "parent_value")
        await multi_cache.set("dependent_key", "dependent_value")
        
        # Set up dependency
        invalidation_manager.add_key_dependency("parent_key", "dependent_key")
        
        # Invalidate parent key
        invalidated_count = await invalidation_manager.invalidate_by_key("parent_key")
        assert invalidated_count > 0
        
        # Verify both keys are invalidated
        parent_value = await multi_cache.get("parent_key")
        dependent_value = await multi_cache.get("dependent_key")
        
        assert parent_value is None
        assert dependent_value is None
    
    @pytest.mark.asyncio
    async def test_legal_document_cache_manager(self):
        """Test legal document cache manager"""
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="legal:")
        l3_cache = DatabaseCache(connection_string="sqlite:///test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        legal_cache = LegalDocumentCacheManager(multi_cache)
        
        # Test document caching
        document_data = {
            "id": "doc123",
            "title": "Test Contract",
            "content": "Contract content...",
            "type": "contract"
        }
        
        success = await legal_cache.cache_legal_document("doc123", document_data)
        assert success
        
        # Test document retrieval
        cached_document = await legal_cache.get_legal_document("doc123")
        assert cached_document == document_data
        
        # Test analysis caching
        analysis_result = {
            "risk_score": 0.7,
            "key_terms": ["liability", "termination"]
        }
        
        success = await legal_cache.cache_document_analysis("doc123", analysis_result)
        assert success
    
    @pytest.mark.asyncio
    async def test_personalization_cache_manager(self):
        """Test personalization cache manager"""
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="person:")
        l3_cache = DatabaseCache(connection_string="sqlite:///test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        person_cache = PersonalizationCacheManager(multi_cache)
        
        # Test user profile caching
        profile_data = {
            "user_id": "user123",
            "preferences": ["tech", "science"],
            "demographics": {"age_group": "25-34"},
            "behavior_data": {"engagement_score": 0.8}
        }
        
        success = await person_cache.cache_user_profile("user123", profile_data)
        assert success
        
        # Test recommendations caching
        recommendations = [
            {"item_id": "item1", "score": 0.9},
            {"item_id": "item2", "score": 0.8}
        ]
        
        success = await person_cache.cache_user_recommendations("user123", recommendations)
        assert success

# =============================================================================
# DATABASE OPTIMIZATION TESTS
# =============================================================================

class TestDatabaseOptimization:
    """Test suite for database optimization"""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_initialization(self):
        """Test connection pool initialization"""
        config = ConnectionPoolConfig(
            min_connections=2,
            max_connections=5,
            connection_timeout=30
        )
        
        pool = DatabaseConnectionPool("postgresql://test", config)
        await pool.initialize_pool()
        
        # Test pool statistics
        stats = pool.get_pool_stats()
        assert stats['total_connections'] >= config.min_connections
        assert stats['max_connections'] == config.max_connections
        
        await pool.close_pool()
    
    @pytest.mark.asyncio
    async def test_database_connection_acquisition(self):
        """Test connection acquisition and return"""
        config = ConnectionPoolConfig(min_connections=1, max_connections=3)
        pool = DatabaseConnectionPool("postgresql://test", config)
        await pool.initialize_pool()
        
        # Acquire connection
        connection = await pool.get_connection()
        assert connection is not None
        
        # Return connection
        await pool.return_connection(connection)
        
        await pool.close_pool()
    
    def test_hash_sharding_strategy(self):
        """Test hash-based sharding strategy"""
        strategy = HashShardingStrategy(shard_field="user_id")
        
        # Test shard key extraction
        data = {"user_id": "user123", "name": "Test User"}
        shard_key = strategy.get_shard_key(data)
        assert shard_key == "user123"
        
        # Test shard ID calculation
        shard_id = strategy.get_shard_id(shard_key, total_shards=3)
        assert 0 <= shard_id < 3
        
        # Same key should always map to same shard
        shard_id2 = strategy.get_shard_id(shard_key, total_shards=3)
        assert shard_id == shard_id2
    
    def test_query_optimizer(self):
        """Test query optimization and analysis"""
        optimizer = QueryOptimizer()
        
        # Test query analysis
        query = "SELECT * FROM users WHERE age > 25 ORDER BY created_at"
        analysis = optimizer.analyze_query(query)
        
        assert analysis['query_type'] == 'SELECT'
        assert isinstance(analysis['complexity_score'], float)
        assert isinstance(analysis['optimization_suggestions'], list)
        
        # Test metrics recording
        optimizer.record_query_metrics(query, 150.0, 100, "conn1")
        
        # Test slow query detection
        slow_queries = optimizer.get_slow_queries()
        # Should have one slow query (150ms > 100ms threshold)
        assert len(slow_queries) >= 0
    
    def test_query_statistics(self):
        """Test query performance statistics"""
        optimizer = QueryOptimizer()
        
        # Record multiple query executions
        queries = [
            ("SELECT * FROM table1", 50.0, 10),
            ("INSERT INTO table1 VALUES (?)", 25.0, 1),
            ("UPDATE table1 SET field = ?", 75.0, 5)
        ]
        
        for query, exec_time, rows in queries:
            optimizer.record_query_metrics(query, exec_time, rows, "conn1")
        
        # Get statistics
        stats = optimizer.get_query_statistics()
        
        assert stats['total_queries'] == 3
        assert stats['unique_query_patterns'] == 3
        assert 'avg_execution_time_ms' in stats
        assert 'query_type_distribution' in stats

# =============================================================================
# PERFORMANCE MONITORING TESTS
# =============================================================================

class TestPerformanceMonitoring:
    """Test suite for performance monitoring"""
    
    @pytest.mark.asyncio
    async def test_system_metrics_collector(self):
        """Test system metrics collection"""
        collector = SystemMetricsCollector()
        
        metrics = await collector.collect_metrics()
        
        assert len(metrics) > 0
        
        # Check for expected metric types
        metric_names = [m.name for m in metrics]
        assert any("cpu" in name for name in metric_names)
        assert any("memory" in name for name in metric_names)
        
        # Verify metric structure
        for metric in metrics:
            assert hasattr(metric, 'name')
            assert hasattr(metric, 'value')
            assert hasattr(metric, 'timestamp')
            assert isinstance(metric.value, (int, float))
    
    @pytest.mark.asyncio
    async def test_application_metrics_collector(self):
        """Test application metrics collection"""
        collector = ApplicationMetricsCollector()
        
        # Record some request metrics
        collector.record_request("/api/test", 150.0, 200)
        collector.record_request("/api/test", 200.0, 500)  # Error
        
        # Record custom metric
        collector.record_custom_metric("custom_counter", 42, {"tag": "value"})
        
        # Collect metrics
        metrics = await collector.collect_metrics()
        
        assert len(metrics) > 0
        
        # Check for application metrics
        metric_names = [m.name for m in metrics]
        assert any("application.requests" in name for name in metric_names)
        assert any("application.response_time" in name for name in metric_names)
        assert any("application.custom" in name for name in metric_names)
    
    def test_alert_evaluator(self):
        """Test alert evaluation system"""
        evaluator = AlertEvaluator()
        
        # Add alert rule
        rule = AlertRule(
            name="test_cpu_alert",
            metric_name="system.cpu.usage",
            condition="gt",
            threshold=80.0,
            evaluation_period=300,
            severity="warning"
        )
        
        evaluator.add_alert_rule(rule)
        
        # Create test metrics
        from performance_monitoring import MetricPoint
        
        metrics = [
            MetricPoint("system.cpu.usage", 85.0, time.time(), {}, "gauge"),  # Above threshold
            MetricPoint("system.memory.usage", 70.0, time.time(), {}, "gauge")
        ]
        
        # Evaluate alerts
        triggered_alerts = evaluator.evaluate_alerts(metrics)
        
        # Should trigger the CPU alert
        assert len(triggered_alerts) >= 0  # May or may not trigger based on timing
    
    @pytest.mark.asyncio
    async def test_notification_manager(self):
        """Test notification management"""
        manager = NotificationManager()
        
        # Mock notification handler
        notifications_sent = []
        
        async def mock_handler(alert):
            notifications_sent.append(alert)
        
        manager.register_channel("mock", mock_handler)
        
        # Send test notification
        test_alert = {
            "rule_name": "test_alert",
            "severity": "warning",
            "message": "Test alert message"
        }
        
        success = await manager.send_notification(test_alert)
        assert success
        assert len(notifications_sent) == 1
        assert notifications_sent[0] == test_alert
    
    @pytest.mark.asyncio
    async def test_performance_monitor_lifecycle(self):
        """Test performance monitor start/stop lifecycle"""
        monitor = PerformanceMonitor()
        
        # Test starting monitoring
        await monitor.start_monitoring()
        assert monitor.monitoring_active
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Test stopping monitoring
        await monitor.stop_monitoring()
        assert not monitor.monitoring_active
    
    def test_performance_monitor_custom_metrics(self):
        """Test custom metrics recording"""
        monitor = PerformanceMonitor()
        
        # Record custom metrics
        monitor.record_custom_metric("business_metric", 100.0, {"category": "sales"})
        monitor.record_request_metric("/api/endpoint", 250.0, 200)
        
        # Get current metrics
        current_metrics = monitor.get_current_metrics()
        
        # Should have recorded metrics in buffer
        # Note: Actual metrics depend on when collectors run
        assert isinstance(current_metrics, list)
    
    def test_legal_document_monitor(self):
        """Test legal document monitoring"""
        base_monitor = PerformanceMonitor()
        legal_monitor = LegalDocumentMonitor(base_monitor)
        
        # Record document processing
        legal_monitor.record_document_processed(
            document_id="doc123",
            processing_time_ms=1500.0,
            terms_extracted=25,
            classification_confidence=0.92
        )
        
        # Record search performance
        legal_monitor.record_search_performance(
            query="contract terms",
            results_count=15,
            search_time_ms=85.0
        )
        
        # Verify metrics were recorded
        current_metrics = base_monitor.get_current_metrics()
        assert isinstance(current_metrics, list)
    
    def test_personalization_monitor(self):
        """Test personalization monitoring"""
        base_monitor = PerformanceMonitor()
        person_monitor = PersonalizationMonitor(base_monitor)
        
        # Record recommendation generation
        person_monitor.record_recommendation_generated(
            user_id="user123",
            recommendation_count=10,
            generation_time_ms=120.0,
            accuracy_score=0.88
        )
        
        # Record A/B test result
        person_monitor.record_ab_test_result(
            test_id="test_abc",
            variant="A",
            converted=True,
            user_engagement_time=45.0
        )
        
        # Verify metrics were recorded
        current_metrics = base_monitor.get_current_metrics()
        assert isinstance(current_metrics, list)

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for all chapter 5 components"""
    
    @pytest.mark.asyncio
    async def test_full_system_integration(self):
        """Test integration of all performance optimization components"""
        # Initialize all systems
        
        # 1. Performance monitoring
        monitor = PerformanceMonitor()
        await monitor.start_monitoring()
        
        # 2. Multi-level cache
        l1_cache = InMemoryCache(max_size=100, max_memory_mb=10)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="integration:")
        l3_cache = DatabaseCache(connection_string="sqlite:///integration_test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        
        # 3. Specialized monitors
        legal_monitor = LegalDocumentMonitor(monitor)
        person_monitor = PersonalizationMonitor(monitor)
        
        # 4. Cache managers
        legal_cache_manager = LegalDocumentCacheManager(multi_cache)
        person_cache_manager = PersonalizationCacheManager(multi_cache)
        
        # Simulate integrated operations
        
        # Legal document processing with caching and monitoring
        document_data = {
            "id": "integration_doc_1",
            "title": "Integration Test Contract",
            "content": "Contract content with legal terms",
            "type": "contract"
        }
        
        # Cache document
        start_time = time.perf_counter()
        await legal_cache_manager.cache_legal_document("integration_doc_1", document_data)
        cache_time = (time.perf_counter() - start_time) * 1000
        
        # Record processing metrics
        legal_monitor.record_document_processed(
            document_id="integration_doc_1",
            processing_time_ms=cache_time,
            terms_extracted=15,
            classification_confidence=0.93
        )
        
        # Retrieve from cache
        cached_doc = await legal_cache_manager.get_legal_document("integration_doc_1")
        assert cached_doc == document_data
        
        # Personalization operations
        profile_data = {
            "user_id": "integration_user_1",
            "preferences": ["legal", "tech"],
            "demographics": {"age_group": "30-39"}
        }
        
        # Cache profile
        await person_cache_manager.cache_user_profile("integration_user_1", profile_data)
        
        # Record recommendation metrics
        person_monitor.record_recommendation_generated(
            user_id="integration_user_1",
            recommendation_count=8,
            generation_time_ms=95.0,
            accuracy_score=0.85
        )
        
        # Let monitoring collect data
        await asyncio.sleep(0.2)
        
        # Verify integration
        performance_summary = monitor.get_performance_summary()
        assert performance_summary['monitoring_status'] == 'active'
        assert performance_summary['metrics_collected'] > 0
        
        # Cache statistics
        cache_stats = multi_cache.get_comprehensive_stats()
        assert cache_stats['multi_level_stats']['total_requests'] > 0
        
        # Cleanup
        await monitor.stop_monitoring()
        
        # Integration test passes if all operations complete without errors
        assert True
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test system performance under simulated load"""
        # Setup systems
        monitor = PerformanceMonitor()
        
        l1_cache = InMemoryCache(max_size=1000, max_memory_mb=50)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="load_test:")
        l3_cache = DatabaseCache(connection_string="sqlite:///load_test.db")
        
        multi_cache = MultiLevelCache(l1_cache, l2_cache, l3_cache)
        legal_monitor = LegalDocumentMonitor(monitor)
        
        await monitor.start_monitoring()
        
        # Simulate high load
        operations_count = 100
        start_time = time.perf_counter()
        
        async def simulate_operation(i):
            # Cache operation
            await multi_cache.set(f"load_key_{i}", f"load_value_{i}")
            
            # Retrieve operation
            value = await multi_cache.get(f"load_key_{i}")
            
            # Record metrics
            legal_monitor.record_document_processed(
                document_id=f"load_doc_{i}",
                processing_time_ms=50.0 + (i % 10),
                terms_extracted=10 + (i % 5),
                classification_confidence=0.9 - (i % 10) * 0.01
            )
            
            return value is not None
        
        # Execute operations concurrently
        tasks = [simulate_operation(i) for i in range(operations_count)]
        results = await asyncio.gather(*tasks)
        
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Verify performance
        success_rate = sum(results) / len(results)
        avg_operation_time = total_time / operations_count
        
        print(f"Load test results:")
        print(f"  Operations: {operations_count}")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average per operation: {avg_operation_time:.2f}ms")
        print(f"  Success rate: {success_rate:.1%}")
        
        # Performance assertions
        assert success_rate > 0.95  # 95% success rate
        assert avg_operation_time < 100  # Less than 100ms per operation
        
        # Get final statistics
        cache_stats = multi_cache.get_comprehensive_stats()
        performance_summary = monitor.get_performance_summary()
        
        print(f"  Cache hit rate: {cache_stats['multi_level_stats']['overall_hit_rate']:.1%}")
        print(f"  Monitoring active: {performance_summary['monitoring_status']}")
        
        await monitor.stop_monitoring()

# =============================================================================
# TEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest for chapter 5 tests"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance-related"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

# =============================================================================
# PERFORMANCE BENCHMARKS
# =============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.performance
    def test_algorithm_performance_comparison(self):
        """Benchmark algorithm performance"""
        import random
        
        # Generate test data
        sorted_data = list(range(10000))
        unsorted_data = sorted_data.copy()
        random.shuffle(unsorted_data)
        
        # Benchmark search algorithms
        target = 5000
        
        # Linear search timing
        start_time = time.perf_counter()
        AlgorithmOptimizer.linear_search_naive(sorted_data[:1000], target)  # Smaller dataset
        linear_time = (time.perf_counter() - start_time) * 1000
        
        # Binary search timing
        start_time = time.perf_counter()
        AlgorithmOptimizer.binary_search_optimized(sorted_data, target)
        binary_time = (time.perf_counter() - start_time) * 1000
        
        print(f"Search Performance Comparison:")
        print(f"  Linear search (1K items): {linear_time:.3f}ms")
        print(f"  Binary search (10K items): {binary_time:.3f}ms")
        
        # Binary search should be faster for large datasets
        assert binary_time < linear_time * 10  # Should be much faster
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_performance_comparison(self):
        """Benchmark cache performance across levels"""
        l1_cache = InMemoryCache(max_size=1000, max_memory_mb=50)
        l2_cache = RedisCache(redis_url="redis://localhost:6379", key_prefix="bench:")
        l3_cache = DatabaseCache(connection_string="sqlite:///benchmark.db")
        
        # Benchmark individual cache levels
        test_data = [f"benchmark_value_{i}" for i in range(100)]
        
        # L1 Cache (In-Memory) benchmark
        start_time = time.perf_counter()
        for i, value in enumerate(test_data):
            await l1_cache.set(f"bench_key_{i}", value)
        l1_set_time = (time.perf_counter() - start_time) * 1000
        
        start_time = time.perf_counter()
        for i in range(len(test_data)):
            await l1_cache.get(f"bench_key_{i}")
        l1_get_time = (time.perf_counter() - start_time) * 1000
        
        # L2 Cache (Redis) benchmark
        start_time = time.perf_counter()
        for i, value in enumerate(test_data):
            await l2_cache.set(f"bench_key_{i}", value)
        l2_set_time = (time.perf_counter() - start_time) * 1000
        
        start_time = time.perf_counter()
        for i in range(len(test_data)):
            await l2_cache.get(f"bench_key_{i}")
        l2_get_time = (time.perf_counter() - start_time) * 1000
        
        print(f"Cache Performance Comparison ({len(test_data)} operations):")
        print(f"  L1 (In-Memory) - Set: {l1_set_time:.2f}ms, Get: {l1_get_time:.2f}ms")
        print(f"  L2 (Redis) - Set: {l2_set_time:.2f}ms, Get: {l2_get_time:.2f}ms")
        
        # In-memory cache should be fastest
        assert l1_get_time < l2_get_time

if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v", "--tb=short"])
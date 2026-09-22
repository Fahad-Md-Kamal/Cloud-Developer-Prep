"""
Comprehensive Database Optimization and Sharding Implementation

This module demonstrates advanced database optimization techniques including
connection pooling, query optimization, database sharding, and performance
monitoring for enterprise applications handling millions of records.

Key features:
- Database connection pooling with health monitoring
- Query optimization and execution plan analysis
- Horizontal database sharding with automatic routing
- Database performance monitoring and alerting
- Production-ready database scaling patterns

Author: Technical Interview Preparation Guide
"""

import asyncio
import hashlib
import json
import logging
import time
import threading
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
import statistics
from concurrent.futures import ThreadPoolExecutor

# =============================================================================
# DATABASE ABSTRACTION LAYER
# =============================================================================

class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows"""
        pass
    
    @abstractmethod
    async def begin_transaction(self) -> 'TransactionContext':
        """Begin database transaction"""
        pass
    
    @abstractmethod
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pass

@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    execution_time_ms: float
    rows_affected: int
    query_type: str  # SELECT, INSERT, UPDATE, DELETE
    timestamp: float
    connection_id: str
    
class TransactionContext:
    """Database transaction context manager"""
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self.connection = None
        self.transaction_started = False
    
    async def __aenter__(self):
        self.connection = await self.connection_manager.get_connection()
        await self.connection.begin()
        self.transaction_started = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.transaction_started:
            if exc_type is None:
                await self.connection.commit()
            else:
                await self.connection.rollback()
        
        if self.connection:
            await self.connection_manager.return_connection(self.connection)

# =============================================================================
# CONNECTION POOL IMPLEMENTATION
# =============================================================================

@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration"""
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: int = 30
    idle_timeout: int = 300
    health_check_interval: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0

class DatabaseConnection:
    """Simulated database connection with health monitoring"""
    
    def __init__(self, connection_id: str, database_url: str):
        self.connection_id = connection_id
        self.database_url = database_url
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.query_count = 0
        self.is_healthy = True
        self.in_transaction = False
        self.transaction_start_time = None
    
    async def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        self.last_used_at = time.time()
        self.query_count += 1
        
        # Simulate query execution
        await asyncio.sleep(0.01)  # Simulate database latency
        
        # Return mock results based on query type
        if query.strip().upper().startswith('SELECT'):
            return [{'id': i, 'data': f'result_{i}'} for i in range(5)]
        return []
    
    async def execute_command(self, command: str, params: Optional[Tuple] = None) -> int:
        """Execute command and return affected rows"""
        self.last_used_at = time.time()
        self.query_count += 1
        
        # Simulate command execution
        await asyncio.sleep(0.005)  # Simulate database latency
        
        return 1  # Simulate 1 affected row
    
    async def begin(self):
        """Begin transaction"""
        self.in_transaction = True
        self.transaction_start_time = time.time()
    
    async def commit(self):
        """Commit transaction"""
        self.in_transaction = False
        self.transaction_start_time = None
    
    async def rollback(self):
        """Rollback transaction"""
        self.in_transaction = False
        self.transaction_start_time = None
    
    async def ping(self) -> bool:
        """Check connection health"""
        try:
            await asyncio.sleep(0.001)  # Simulate ping
            return True
        except:
            self.is_healthy = False
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'connection_id': self.connection_id,
            'created_at': self.created_at,
            'last_used_at': self.last_used_at,
            'query_count': self.query_count,
            'is_healthy': self.is_healthy,
            'in_transaction': self.in_transaction,
            'age_seconds': time.time() - self.created_at,
            'idle_seconds': time.time() - self.last_used_at
        }

class DatabaseConnectionPool:
    """High-performance database connection pool"""
    
    def __init__(self, database_url: str, config: ConnectionPoolConfig):
        self.database_url = database_url
        self.config = config
        
        self._available_connections: asyncio.Queue = asyncio.Queue(maxsize=config.max_connections)
        self._all_connections: Dict[str, DatabaseConnection] = {}
        self._connection_semaphore = asyncio.Semaphore(config.max_connections)
        
        self._stats = {
            'connections_created': 0,
            'connections_destroyed': 0,
            'connections_borrowed': 0,
            'connections_returned': 0,
            'health_checks_performed': 0,
            'failed_health_checks': 0
        }
        
        self._health_check_task = None
        self._pool_initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize_pool(self):
        """Initialize connection pool with minimum connections"""
        if self._pool_initialized:
            return
        
        async with self._lock:
            if self._pool_initialized:
                return
            
            # Create minimum connections
            for i in range(self.config.min_connections):
                connection = await self._create_connection()
                await self._available_connections.put(connection)
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_worker())
            
            self._pool_initialized = True
            logging.info(f"Connection pool initialized with {self.config.min_connections} connections")
    
    async def close_pool(self):
        """Close all connections and stop background tasks"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        while not self._available_connections.empty():
            try:
                connection = self._available_connections.get_nowait()
                await self._destroy_connection(connection)
            except asyncio.QueueEmpty:
                break
        
        self._pool_initialized = False
        logging.info("Connection pool closed")
    
    async def get_connection(self) -> DatabaseConnection:
        """Get connection from pool"""
        if not self._pool_initialized:
            await self.initialize_pool()
        
        await self._connection_semaphore.acquire()
        self._stats['connections_borrowed'] += 1
        
        try:
            # Try to get available connection
            connection = await asyncio.wait_for(
                self._available_connections.get(),
                timeout=self.config.connection_timeout
            )
            
            # Validate connection health
            if not await connection.ping():
                await self._destroy_connection(connection)
                connection = await self._create_connection()
            
            return connection
            
        except asyncio.TimeoutError:
            # Create new connection if pool is not at max capacity
            if len(self._all_connections) < self.config.max_connections:
                connection = await self._create_connection()
                return connection
            else:
                self._connection_semaphore.release()
                raise Exception("Connection pool exhausted")
    
    async def return_connection(self, connection: DatabaseConnection):
        """Return connection to pool"""
        self._stats['connections_returned'] += 1
        
        try:
            # Check if connection is still healthy
            if connection.is_healthy and await connection.ping():
                # Reset connection state
                if connection.in_transaction:
                    await connection.rollback()
                
                await self._available_connections.put(connection)
            else:
                # Destroy unhealthy connection
                await self._destroy_connection(connection)
        finally:
            self._connection_semaphore.release()
    
    async def _create_connection(self) -> DatabaseConnection:
        """Create new database connection"""
        connection_id = f"conn_{len(self._all_connections)}_{int(time.time())}"
        connection = DatabaseConnection(connection_id, self.database_url)
        
        self._all_connections[connection_id] = connection
        self._stats['connections_created'] += 1
        
        return connection
    
    async def _destroy_connection(self, connection: DatabaseConnection):
        """Destroy database connection"""
        if connection.connection_id in self._all_connections:
            del self._all_connections[connection.connection_id]
            self._stats['connections_destroyed'] += 1
    
    async def _health_check_worker(self):
        """Background worker for connection health checks"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in connection health check: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on idle connections"""
        current_time = time.time()
        connections_to_check = []
        
        # Identify connections that need health checking
        for connection in self._all_connections.values():
            idle_time = current_time - connection.last_used_at
            if idle_time > self.config.idle_timeout / 2:  # Check connections idle for half the timeout
                connections_to_check.append(connection)
        
        for connection in connections_to_check:
            self._stats['health_checks_performed'] += 1
            
            if not await connection.ping():
                self._stats['failed_health_checks'] += 1
                await self._destroy_connection(connection)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        available_count = self._available_connections.qsize()
        total_connections = len(self._all_connections)
        
        return {
            'total_connections': total_connections,
            'available_connections': available_count,
            'active_connections': total_connections - available_count,
            'max_connections': self.config.max_connections,
            'min_connections': self.config.min_connections,
            'utilization': (total_connections - available_count) / self.config.max_connections,
            'stats': self._stats.copy(),
            'health': {
                'healthy_connections': sum(1 for c in self._all_connections.values() if c.is_healthy),
                'unhealthy_connections': sum(1 for c in self._all_connections.values() if not c.is_healthy),
                'connections_in_transaction': sum(1 for c in self._all_connections.values() if c.in_transaction)
            }
        }

# =============================================================================
# DATABASE SHARDING IMPLEMENTATION
# =============================================================================

class ShardingStrategy(ABC):
    """Abstract sharding strategy"""
    
    @abstractmethod
    def get_shard_key(self, data: Dict[str, Any]) -> str:
        """Determine shard key from data"""
        pass
    
    @abstractmethod
    def get_shard_id(self, shard_key: str, total_shards: int) -> int:
        """Determine shard ID from shard key"""
        pass

class HashShardingStrategy(ShardingStrategy):
    """Hash-based sharding strategy"""
    
    def __init__(self, shard_field: str = 'id'):
        self.shard_field = shard_field
    
    def get_shard_key(self, data: Dict[str, Any]) -> str:
        """Get shard key from data"""
        return str(data.get(self.shard_field, ''))
    
    def get_shard_id(self, shard_key: str, total_shards: int) -> int:
        """Calculate shard ID using consistent hashing"""
        hash_value = int(hashlib.md5(shard_key.encode()).hexdigest(), 16)
        return hash_value % total_shards

class RangeShardingStrategy(ShardingStrategy):
    """Range-based sharding strategy"""
    
    def __init__(self, shard_field: str = 'id', ranges: List[Tuple[Any, Any]] = None):
        self.shard_field = shard_field
        self.ranges = ranges or []
    
    def get_shard_key(self, data: Dict[str, Any]) -> str:
        """Get shard key from data"""
        return str(data.get(self.shard_field, ''))
    
    def get_shard_id(self, shard_key: str, total_shards: int) -> int:
        """Determine shard ID based on ranges"""
        try:
            value = int(shard_key)
            for i, (start, end) in enumerate(self.ranges):
                if start <= value < end:
                    return i
        except ValueError:
            pass
        
        # Fallback to hash-based sharding
        hash_value = int(hashlib.md5(shard_key.encode()).hexdigest(), 16)
        return hash_value % total_shards

@dataclass
class ShardConfig:
    """Configuration for a database shard"""
    shard_id: int
    database_url: str
    weight: float = 1.0  # For weighted sharding
    is_active: bool = True
    is_read_replica: bool = False

class ShardedDatabase(DatabaseInterface):
    """Sharded database implementation with automatic routing"""
    
    def __init__(self, shards: List[ShardConfig], sharding_strategy: ShardingStrategy,
                 pool_config: ConnectionPoolConfig):
        self.shards = {shard.shard_id: shard for shard in shards}
        self.sharding_strategy = sharding_strategy
        self.pool_config = pool_config
        
        # Connection pools for each shard
        self.connection_pools: Dict[int, DatabaseConnectionPool] = {}
        
        # Query routing statistics
        self._routing_stats = {
            'queries_routed': 0,
            'shard_distribution': {shard.shard_id: 0 for shard in shards},
            'cross_shard_queries': 0,
            'failed_routes': 0
        }
    
    async def initialize(self):
        """Initialize connection pools for all shards"""
        for shard_id, shard_config in self.shards.items():
            if shard_config.is_active:
                pool = DatabaseConnectionPool(shard_config.database_url, self.pool_config)
                await pool.initialize_pool()
                self.connection_pools[shard_id] = pool
        
        logging.info(f"Initialized sharded database with {len(self.connection_pools)} active shards")
    
    async def close(self):
        """Close all connection pools"""
        for pool in self.connection_pools.values():
            await pool.close_pool()
        
        self.connection_pools.clear()
    
    async def execute_query(self, query: str, params: Optional[Tuple] = None, 
                          shard_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute query on appropriate shard"""
        if shard_key:
            # Direct shard routing
            shard_id = self.sharding_strategy.get_shard_id(shard_key, len(self.shards))
            return await self._execute_on_shard(shard_id, 'query', query, params)
        else:
            # Cross-shard query (aggregate results from all shards)
            return await self._execute_cross_shard_query(query, params)
    
    async def execute_command(self, command: str, params: Optional[Tuple] = None,
                            data: Optional[Dict[str, Any]] = None) -> int:
        """Execute command on appropriate shard"""
        if data:
            # Route based on data content
            shard_key = self.sharding_strategy.get_shard_key(data)
            shard_id = self.sharding_strategy.get_shard_id(shard_key, len(self.shards))
            return await self._execute_on_shard(shard_id, 'command', command, params)
        else:
            # Execute on all shards and sum results
            total_affected = 0
            for shard_id in self.connection_pools.keys():
                affected = await self._execute_on_shard(shard_id, 'command', command, params)
                total_affected += affected
            return total_affected
    
    async def begin_transaction(self, shard_key: str) -> TransactionContext:
        """Begin transaction on specific shard"""
        shard_id = self.sharding_strategy.get_shard_id(shard_key, len(self.shards))
        pool = self.connection_pools.get(shard_id)
        
        if not pool:
            raise Exception(f"Shard {shard_id} not available")
        
        return TransactionContext(pool)
    
    async def _execute_on_shard(self, shard_id: int, operation_type: str, 
                               query_or_command: str, params: Optional[Tuple] = None):
        """Execute operation on specific shard"""
        pool = self.connection_pools.get(shard_id)
        
        if not pool:
            self._routing_stats['failed_routes'] += 1
            raise Exception(f"Shard {shard_id} not available")
        
        self._routing_stats['queries_routed'] += 1
        self._routing_stats['shard_distribution'][shard_id] += 1
        
        connection = await pool.get_connection()
        try:
            if operation_type == 'query':
                return await connection.execute_query(query_or_command, params)
            else:
                return await connection.execute_command(query_or_command, params)
        finally:
            await pool.return_connection(connection)
    
    async def _execute_cross_shard_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute query across all shards and aggregate results"""
        self._routing_stats['cross_shard_queries'] += 1
        
        tasks = []
        for shard_id in self.connection_pools.keys():
            task = asyncio.create_task(
                self._execute_on_shard(shard_id, 'query', query, params)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        aggregated_results = []
        for result in results:
            if isinstance(result, list):
                aggregated_results.extend(result)
            elif isinstance(result, Exception):
                logging.error(f"Cross-shard query failed: {result}")
        
        return aggregated_results
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics for all shards"""
        shard_stats = {}
        
        for shard_id, pool in self.connection_pools.items():
            shard_stats[f"shard_{shard_id}"] = pool.get_pool_stats()
        
        return {
            'sharding_strategy': type(self.sharding_strategy).__name__,
            'total_shards': len(self.shards),
            'active_shards': len(self.connection_pools),
            'routing_stats': self._routing_stats.copy(),
            'shard_stats': shard_stats
        }

# =============================================================================
# QUERY OPTIMIZATION AND MONITORING
# =============================================================================

class QueryOptimizer:
    """Query optimization and performance monitoring"""
    
    def __init__(self):
        self.query_metrics: Dict[str, List[QueryMetrics]] = {}
        self.slow_query_threshold_ms = 100
        self._metrics_lock = threading.RLock()
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query for optimization opportunities"""
        query_lower = query.lower().strip()
        
        analysis = {
            'query_type': self._determine_query_type(query_lower),
            'complexity_score': self._calculate_complexity_score(query_lower),
            'optimization_suggestions': self._get_optimization_suggestions(query_lower),
            'estimated_cost': self._estimate_query_cost(query_lower)
        }
        
        return analysis
    
    def record_query_metrics(self, query: str, execution_time_ms: float, 
                           rows_affected: int, connection_id: str):
        """Record query execution metrics"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
        
        metrics = QueryMetrics(
            query_hash=query_hash,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            query_type=self._determine_query_type(query.lower()),
            timestamp=time.time(),
            connection_id=connection_id
        )
        
        with self._metrics_lock:
            if query_hash not in self.query_metrics:
                self.query_metrics[query_hash] = []
            
            self.query_metrics[query_hash].append(metrics)
            
            # Keep only recent metrics (last 1000 executions per query)
            if len(self.query_metrics[query_hash]) > 1000:
                self.query_metrics[query_hash] = self.query_metrics[query_hash][-1000:]
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries by average execution time"""
        query_performance = []
        
        with self._metrics_lock:
            for query_hash, metrics_list in self.query_metrics.items():
                if not metrics_list:
                    continue
                
                execution_times = [m.execution_time_ms for m in metrics_list]
                avg_execution_time = statistics.mean(execution_times)
                
                if avg_execution_time >= self.slow_query_threshold_ms:
                    query_performance.append({
                        'query_hash': query_hash,
                        'avg_execution_time_ms': avg_execution_time,
                        'max_execution_time_ms': max(execution_times),
                        'min_execution_time_ms': min(execution_times),
                        'execution_count': len(metrics_list),
                        'total_time_ms': sum(execution_times),
                        'query_type': metrics_list[0].query_type,
                        'last_executed': max(m.timestamp for m in metrics_list)
                    })
        
        # Sort by average execution time
        query_performance.sort(key=lambda x: x['avg_execution_time_ms'], reverse=True)
        
        return query_performance[:limit]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        with self._metrics_lock:
            total_queries = sum(len(metrics) for metrics in self.query_metrics.values())
            
            if total_queries == 0:
                return {'total_queries': 0}
            
            all_execution_times = []
            query_type_counts = {}
            
            for metrics_list in self.query_metrics.values():
                for metric in metrics_list:
                    all_execution_times.append(metric.execution_time_ms)
                    query_type = metric.query_type
                    query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
            
            return {
                'total_queries': total_queries,
                'unique_query_patterns': len(self.query_metrics),
                'avg_execution_time_ms': statistics.mean(all_execution_times),
                'median_execution_time_ms': statistics.median(all_execution_times),
                'p95_execution_time_ms': self._percentile(all_execution_times, 95),
                'p99_execution_time_ms': self._percentile(all_execution_times, 99),
                'slow_queries_count': len(self.get_slow_queries()),
                'query_type_distribution': query_type_counts
            }
    
    def _determine_query_type(self, query: str) -> str:
        """Determine the type of SQL query"""
        query = query.strip().lower()
        
        if query.startswith('select'):
            return 'SELECT'
        elif query.startswith('insert'):
            return 'INSERT'
        elif query.startswith('update'):
            return 'UPDATE'
        elif query.startswith('delete'):
            return 'DELETE'
        elif query.startswith('create'):
            return 'CREATE'
        elif query.startswith('alter'):
            return 'ALTER'
        elif query.startswith('drop'):
            return 'DROP'
        else:
            return 'OTHER'
    
    def _calculate_complexity_score(self, query: str) -> float:
        """Calculate query complexity score"""
        score = 0.0
        
        # Basic complexity factors
        if 'join' in query:
            score += query.count('join') * 2.0
        if 'where' in query:
            score += 1.0
        if 'group by' in query:
            score += 1.5
        if 'order by' in query:
            score += 1.0
        if 'having' in query:
            score += 2.0
        if 'union' in query:
            score += query.count('union') * 3.0
        if 'subquery' in query or '(' in query:
            score += query.count('(') * 1.5
        
        return min(score, 10.0)  # Cap at 10.0
    
    def _get_optimization_suggestions(self, query: str) -> List[str]:
        """Get query optimization suggestions"""
        suggestions = []
        
        if 'select *' in query:
            suggestions.append("Avoid SELECT * - specify only needed columns")
        
        if query.count('join') > 3:
            suggestions.append("Consider breaking complex joins into simpler queries")
        
        if 'where' not in query and 'select' in query:
            suggestions.append("Add WHERE clause to filter results")
        
        if 'order by' in query and 'limit' not in query:
            suggestions.append("Consider adding LIMIT to ORDER BY queries")
        
        if query.count('union') > 0:
            suggestions.append("Consider using UNION ALL instead of UNION if duplicates are acceptable")
        
        return suggestions
    
    def _estimate_query_cost(self, query: str) -> float:
        """Estimate relative query cost"""
        base_cost = 1.0
        
        # Adjust cost based on operations
        if 'join' in query:
            base_cost *= (1 + query.count('join') * 0.5)
        if 'group by' in query:
            base_cost *= 1.3
        if 'order by' in query:
            base_cost *= 1.2
        if 'union' in query:
            base_cost *= (1 + query.count('union') * 0.8)
        
        return base_cost
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index >= len(sorted_data):
                return sorted_data[lower_index]
            
            return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight

# =============================================================================
# ENTERPRISE DATABASE MANAGERS
# =============================================================================

class LegalDocumentDatabaseManager:
    """Database manager for legal document system (Lawstronaut)"""
    
    def __init__(self, sharded_db: ShardedDatabase):
        self.db = sharded_db
        self.query_optimizer = QueryOptimizer()
        
    async def store_legal_document(self, document: Dict[str, Any]) -> int:
        """Store legal document with optimized sharding"""
        command = """
            INSERT INTO legal_documents (id, title, content, document_type, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        params = (
            document['id'],
            document['title'],
            document['content'],
            document['type'],
            datetime.now().isoformat()
        )
        
        start_time = time.perf_counter()
        
        try:
            result = await self.db.execute_command(command, params, data=document)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            self.query_optimizer.record_query_metrics(
                command, execution_time, result, "legal_db"
            )
            
            return result
            
        except Exception as e:
            logging.error(f"Error storing legal document: {e}")
            raise
    
    async def search_legal_documents(self, search_criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search legal documents with optimization"""
        # Build optimized query based on criteria
        where_clauses = []
        params = []
        
        if 'document_type' in search_criteria:
            where_clauses.append("document_type = %s")
            params.append(search_criteria['document_type'])
        
        if 'title_contains' in search_criteria:
            where_clauses.append("title ILIKE %s")
            params.append(f"%{search_criteria['title_contains']}%")
        
        if 'created_after' in search_criteria:
            where_clauses.append("created_at >= %s")
            params.append(search_criteria['created_after'])
        
        # Construct query
        query = "SELECT id, title, document_type, created_at FROM legal_documents"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY created_at DESC LIMIT 100"
        
        start_time = time.perf_counter()
        
        try:
            results = await self.db.execute_query(query, tuple(params) if params else None)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            self.query_optimizer.record_query_metrics(
                query, execution_time, len(results), "legal_db"
            )
            
            return results
            
        except Exception as e:
            logging.error(f"Error searching legal documents: {e}")
            raise
    
    async def get_document_analytics(self) -> Dict[str, Any]:
        """Get document analytics with cross-shard aggregation"""
        analytics_queries = [
            "SELECT document_type, COUNT(*) as count FROM legal_documents GROUP BY document_type",
            "SELECT DATE(created_at) as date, COUNT(*) as count FROM legal_documents GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30"
        ]
        
        analytics_results = {}
        
        for query in analytics_queries:
            start_time = time.perf_counter()
            
            try:
                results = await self.db.execute_query(query)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                self.query_optimizer.record_query_metrics(
                    query, execution_time, len(results), "legal_db"
                )
                
                if "document_type" in query:
                    analytics_results['by_type'] = results
                elif "DATE(created_at)" in query:
                    analytics_results['by_date'] = results
                    
            except Exception as e:
                logging.error(f"Error in analytics query: {e}")
        
        return analytics_results

class PersonalizationDatabaseManager:
    """Database manager for personalization system (Optimizely)"""
    
    def __init__(self, sharded_db: ShardedDatabase):
        self.db = sharded_db
        self.query_optimizer = QueryOptimizer()
    
    async def store_user_profile(self, profile: Dict[str, Any]) -> int:
        """Store user profile with user-based sharding"""
        command = """
            INSERT INTO user_profiles (user_id, preferences, demographics, behavior_data, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            preferences = EXCLUDED.preferences,
            demographics = EXCLUDED.demographics,
            behavior_data = EXCLUDED.behavior_data,
            updated_at = EXCLUDED.updated_at
        """
        
        params = (
            profile['user_id'],
            json.dumps(profile.get('preferences', [])),
            json.dumps(profile.get('demographics', {})),
            json.dumps(profile.get('behavior_data', {})),
            datetime.now().isoformat()
        )
        
        start_time = time.perf_counter()
        
        try:
            result = await self.db.execute_command(command, params, data=profile)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            self.query_optimizer.record_query_metrics(
                command, execution_time, result, "personalization_db"
            )
            
            return result
            
        except Exception as e:
            logging.error(f"Error storing user profile: {e}")
            raise
    
    async def get_user_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get personalized recommendations for user"""
        query = """
            SELECT r.item_id, r.score, r.recommendation_type, i.title, i.category
            FROM user_recommendations r
            JOIN items i ON r.item_id = i.id
            WHERE r.user_id = %s AND r.is_active = true
            ORDER BY r.score DESC, r.created_at DESC
            LIMIT %s
        """
        
        params = (user_id, limit)
        shard_key = user_id
        
        start_time = time.perf_counter()
        
        try:
            results = await self.db.execute_query(query, params, shard_key=shard_key)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            self.query_optimizer.record_query_metrics(
                query, execution_time, len(results), "personalization_db"
            )
            
            return results
            
        except Exception as e:
            logging.error(f"Error getting user recommendations: {e}")
            raise
    
    async def batch_update_recommendation_scores(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update recommendation scores for performance"""
        total_updated = 0
        
        # Group updates by shard
        shard_groups = {}
        for update in updates:
            user_id = update['user_id']
            shard_key = user_id
            shard_id = self.db.sharding_strategy.get_shard_id(shard_key, len(self.db.shards))
            
            if shard_id not in shard_groups:
                shard_groups[shard_id] = []
            shard_groups[shard_id].append(update)
        
        # Execute batch updates per shard
        for shard_id, shard_updates in shard_groups.items():
            if len(shard_updates) == 1:
                # Single update
                update = shard_updates[0]
                command = """
                    UPDATE user_recommendations 
                    SET score = %s, updated_at = %s
                    WHERE user_id = %s AND item_id = %s
                """
                params = (update['score'], datetime.now().isoformat(), 
                         update['user_id'], update['item_id'])
                
                result = await self.db.execute_command(command, params, data={'user_id': update['user_id']})
                total_updated += result
            else:
                # Batch update using CASE statement
                case_statements = []
                user_item_pairs = []
                
                for update in shard_updates:
                    case_statements.append("WHEN (user_id = %s AND item_id = %s) THEN %s")
                    user_item_pairs.extend([update['user_id'], update['item_id'], update['score']])
                
                command = f"""
                    UPDATE user_recommendations 
                    SET score = CASE 
                        {' '.join(case_statements)}
                        ELSE score 
                    END,
                    updated_at = %s
                    WHERE (user_id, item_id) IN ({', '.join(['(%s, %s)'] * len(shard_updates))})
                """
                
                # Build parameters
                params = user_item_pairs + [datetime.now().isoformat()]
                for update in shard_updates:
                    params.extend([update['user_id'], update['item_id']])
                
                result = await self.db.execute_command(command, tuple(params), 
                                                     data={'user_id': shard_updates[0]['user_id']})
                total_updated += result
        
        return total_updated

# =============================================================================
# DEMONSTRATION
# =============================================================================

async def demonstrate_database_optimization():
    """Comprehensive demonstration of database optimization techniques"""
    
    print("=== Database Optimization and Sharding Demo ===\n")
    
    # Setup sharded database configuration
    shards = [
        ShardConfig(shard_id=0, database_url="postgresql://localhost/shard_0"),
        ShardConfig(shard_id=1, database_url="postgresql://localhost/shard_1"),
        ShardConfig(shard_id=2, database_url="postgresql://localhost/shard_2")
    ]
    
    sharding_strategy = HashShardingStrategy(shard_field='user_id')
    pool_config = ConnectionPoolConfig(
        min_connections=3,
        max_connections=10,
        connection_timeout=30
    )
    
    # Initialize sharded database
    sharded_db = ShardedDatabase(shards, sharding_strategy, pool_config)
    await sharded_db.initialize()
    
    print("1. Database Sharding Setup")
    print("-" * 50)
    print(f"Initialized database with {len(shards)} shards")
    print(f"Sharding strategy: {type(sharding_strategy).__name__}")
    
    # Connection pool statistics
    conn_stats = sharded_db.get_connection_stats()
    print(f"Active shards: {conn_stats['active_shards']}")
    
    print("\n2. Legal Document Database Operations")
    print("-" * 50)
    
    legal_db_manager = LegalDocumentDatabaseManager(sharded_db)
    
    # Store legal documents
    legal_documents = [
        {
            'id': f'legal_doc_{i}',
            'title': f'Contract Agreement {i}',
            'content': f'Legal document content for contract {i}',
            'type': 'contract',
            'user_id': f'user_{i % 100}'  # For sharding
        }
        for i in range(100)
    ]
    
    start_time = time.perf_counter()
    
    storage_tasks = [
        legal_db_manager.store_legal_document(doc) for doc in legal_documents[:10]
    ]
    storage_results = await asyncio.gather(*storage_tasks)
    
    storage_time = (time.perf_counter() - start_time) * 1000
    
    print(f"Stored {len(storage_results)} legal documents in {storage_time:.2f}ms")
    print(f"Average storage time per document: {storage_time / len(storage_results):.2f}ms")
    
    # Search operations
    search_criteria = {'document_type': 'contract', 'title_contains': 'Agreement'}
    search_results = await legal_db_manager.search_legal_documents(search_criteria)
    
    print(f"Search returned {len(search_results)} matching documents")
    
    print("\n3. Personalization Database Operations")
    print("-" * 50)
    
    personalization_manager = PersonalizationDatabaseManager(sharded_db)
    
    # Store user profiles
    user_profiles = [
        {
            'user_id': f'user_{i}',
            'preferences': ['tech', 'science', 'legal'],
            'demographics': {'age_group': '25-34', 'location': 'US'},
            'behavior_data': {'engagement_score': 0.8, 'activity_level': 'high'}
        }
        for i in range(50)
    ]
    
    start_time = time.perf_counter()
    
    profile_tasks = [
        personalization_manager.store_user_profile(profile) for profile in user_profiles[:10]
    ]
    profile_results = await asyncio.gather(*profile_tasks)
    
    profile_time = (time.perf_counter() - start_time) * 1000
    
    print(f"Stored {len(profile_results)} user profiles in {profile_time:.2f}ms")
    
    # Get recommendations
    recommendations = await personalization_manager.get_user_recommendations('user_1', limit=5)
    print(f"Generated {len(recommendations)} recommendations for user_1")
    
    print("\n4. Query Optimization Analysis")
    print("-" * 50)
    
    query_optimizer = legal_db_manager.query_optimizer
    
    # Analyze query performance
    query_stats = query_optimizer.get_query_statistics()
    
    print("Query Performance Statistics:")
    print(f"  Total queries executed: {query_stats.get('total_queries', 0)}")
    print(f"  Unique query patterns: {query_stats.get('unique_query_patterns', 0)}")
    print(f"  Average execution time: {query_stats.get('avg_execution_time_ms', 0):.2f}ms")
    print(f"  95th percentile time: {query_stats.get('p95_execution_time_ms', 0):.2f}ms")
    
    # Show slow queries
    slow_queries = query_optimizer.get_slow_queries(limit=3)
    if slow_queries:
        print(f"\nTop {len(slow_queries)} slowest queries:")
        for i, query_info in enumerate(slow_queries, 1):
            print(f"  {i}. Query {query_info['query_hash']}: {query_info['avg_execution_time_ms']:.2f}ms avg")
    
    print("\n5. Database Connection Pool Analysis")
    print("-" * 50)
    
    final_conn_stats = sharded_db.get_connection_stats()
    
    print("Connection Pool Statistics:")
    for shard_name, stats in final_conn_stats['shard_stats'].items():
        print(f"\n  {shard_name.upper()}:")
        print(f"    Total connections: {stats['total_connections']}")
        print(f"    Active connections: {stats['active_connections']}")
        print(f"    Pool utilization: {stats['utilization']:.1%}")
        print(f"    Health status: {stats['health']['healthy_connections']}/{stats['total_connections']} healthy")
    
    print(f"\nRouting Statistics:")
    routing_stats = final_conn_stats['routing_stats']
    print(f"  Queries routed: {routing_stats['queries_routed']}")
    print(f"  Cross-shard queries: {routing_stats['cross_shard_queries']}")
    print(f"  Failed routes: {routing_stats['failed_routes']}")
    
    # Shard distribution
    if routing_stats['shard_distribution']:
        print(f"\nShard Distribution:")
        for shard_id, query_count in routing_stats['shard_distribution'].items():
            percentage = (query_count / routing_stats['queries_routed'] * 100) if routing_stats['queries_routed'] > 0 else 0
            print(f"    Shard {shard_id}: {query_count} queries ({percentage:.1f}%)")
    
    print("\n6. Performance Load Testing")
    print("-" * 50)
    
    # Simulate concurrent load
    concurrent_operations = 100
    
    async def simulate_user_operation(user_id: int):
        """Simulate typical user operations"""
        # Store profile
        profile = {
            'user_id': f'load_test_user_{user_id}',
            'preferences': ['tech', 'science'],
            'demographics': {'age_group': '25-34'},
            'behavior_data': {'score': 0.8}
        }
        await personalization_manager.store_user_profile(profile)
        
        # Get recommendations
        await personalization_manager.get_user_recommendations(profile['user_id'])
        
        return user_id
    
    start_time = time.perf_counter()
    
    load_test_tasks = [
        simulate_user_operation(i) for i in range(concurrent_operations)
    ]
    load_test_results = await asyncio.gather(*load_test_tasks)
    
    load_test_time = (time.perf_counter() - start_time) * 1000
    
    print(f"Completed {len(load_test_results)} concurrent operations in {load_test_time:.2f}ms")
    print(f"Average operation time: {load_test_time / len(load_test_results):.2f}ms")
    print(f"Operations per second: {len(load_test_results) / (load_test_time / 1000):.1f}")
    
    # Clean up
    await sharded_db.close()
    
    print("\n=== Database Optimization Demo Completed ===")
    
    print("\nKey Database Optimization Insights:")
    print("- Connection pooling significantly improves performance under load")
    print("- Database sharding enables horizontal scaling across multiple servers")
    print("- Query optimization and monitoring help identify performance bottlenecks")
    print("- Proper shard key selection ensures even data distribution")
    print("- Enterprise database managers provide domain-specific optimizations")
    print("- Batch operations and prepared statements improve throughput")

if __name__ == "__main__":
    # Run the comprehensive database optimization demonstration
    asyncio.run(demonstrate_database_optimization())
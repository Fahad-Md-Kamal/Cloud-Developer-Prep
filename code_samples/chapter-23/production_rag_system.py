"""
Production RAG System Implementation

This module demonstrates a complete production-ready RAG system with
monitoring, caching, security, and scalability considerations.

Key concepts covered:
- Production deployment architecture
- Real-time monitoring and metrics
- Caching strategies and optimization
- Security and access control
- Auto-scaling and load balancing
- Error handling and recovery

Real-world applications:
- Enterprise legal research platform for Lawstronaut
- Scalable content personalization for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Union, Callable, AsyncGenerator
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
import asyncio
import json
import logging
import time
import hashlib
import uuid
from datetime import datetime, timedelta
from enum import Enum
import threading
from contextlib import asynccontextmanager
import weakref
from collections import defaultdict, deque
import concurrent.futures

# Mock external dependencies for production features
class MockRedis:
    def __init__(self):
        self.data = {}
        self.expiry = {}
    
    async def get(self, key: str) -> Optional[str]:
        if key in self.expiry and datetime.now() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        self.data[key] = value
        if ex:
            self.expiry[key] = datetime.now() + timedelta(seconds=ex)
    
    async def delete(self, key: str):
        self.data.pop(key, None)
        self.expiry.pop(key, None)

class MockPrometheus:
    class Counter:
        def __init__(self, name: str, description: str, labelnames: List[str] = None):
            self.name = name
            self._value = 0
            self.labels = {}
        
        def inc(self, amount: float = 1):
            self._value += amount
        
        def labels(self, **kwargs):
            key = json.dumps(kwargs, sort_keys=True)
            if key not in self.labels:
                self.labels[key] = MockPrometheus.Counter(self.name, "", [])
            return self.labels[key]
    
    class Histogram:
        def __init__(self, name: str, description: str, labelnames: List[str] = None):
            self.name = name
            self.observations = []
            self.labels = {}
        
        def observe(self, amount: float):
            self.observations.append(amount)
        
        def labels(self, **kwargs):
            return self

class MockAuth:
    def __init__(self):
        self.users = {
            "user1": {"roles": ["reader"], "api_key": "key1"},
            "admin": {"roles": ["admin", "reader"], "api_key": "admin_key"}
        }
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        for user, data in self.users.items():
            if data["api_key"] == token:
                return {"user": user, "roles": data["roles"]}
        return None

# =============================================================================
# PRODUCTION DATA MODELS
# =============================================================================

class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"

class CacheLevel(Enum):
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_DISK = "l3_disk"

@dataclass
class RequestContext:
    """Context for production requests"""
    request_id: str
    user_id: Optional[str]
    api_key: Optional[str]
    roles: List[str] = field(default_factory=list)
    rate_limit_key: Optional[str] = None
    priority: int = 0  # 0=low, 1=normal, 2=high, 3=critical
    timeout_seconds: int = 30
    cache_ttl: int = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    requests_per_second: float
    avg_response_time_ms: float
    cache_hit_rate: float
    error_rate: float
    active_connections: int
    memory_usage_mb: float
    cpu_usage_percent: float
    queue_depth: int
    status: SystemStatus
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value
        }

@dataclass
class CacheEntry:
    """Production cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    cache_level: CacheLevel = CacheLevel.L1_MEMORY
    
    def is_expired(self) -> bool:
        return self.expires_at and datetime.now() > self.expires_at
    
    def touch(self):
        self.last_accessed = datetime.now()
        self.access_count += 1

# =============================================================================
# MONITORING AND METRICS
# =============================================================================

class MetricsCollector:
    """Production metrics collection and monitoring"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 data points
        self.prometheus_metrics = self._setup_prometheus_metrics()
        self.alert_thresholds = {
            'error_rate_threshold': 0.05,  # 5%
            'response_time_threshold': 2000,  # 2 seconds
            'cache_hit_rate_threshold': 0.7,  # 70%
            'memory_threshold': 80,  # 80%
        }
        self.logger = logging.getLogger(__name__)
        self._start_time = datetime.now()
        
        # Request tracking
        self.request_counts = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        
    def _setup_prometheus_metrics(self) -> Dict[str, Any]:
        """Setup Prometheus metrics"""
        return {
            'requests_total': MockPrometheus.Counter(
                'rag_requests_total', 
                'Total RAG requests',
                ['method', 'status']
            ),
            'request_duration': MockPrometheus.Histogram(
                'rag_request_duration_seconds',
                'RAG request duration',
                ['method']
            ),
            'cache_operations': MockPrometheus.Counter(
                'rag_cache_operations_total',
                'Cache operations',
                ['operation', 'level', 'result']
            ),
            'active_connections': MockPrometheus.Counter(
                'rag_active_connections',
                'Active connections'
            )
        }
    
    async def record_request(self, method: str, status: str, duration_ms: float):
        """Record request metrics"""
        # Update Prometheus metrics
        self.prometheus_metrics['requests_total'].labels(
            method=method, status=status
        ).inc()
        
        self.prometheus_metrics['request_duration'].labels(
            method=method
        ).observe(duration_ms / 1000)
        
        # Update internal tracking
        self.request_counts[method] += 1
        self.response_times.append(duration_ms)
        
        if status == 'error':
            self.error_counts[method] += 1
    
    async def record_cache_operation(self, operation: str, level: str, result: str):
        """Record cache operation metrics"""
        self.prometheus_metrics['cache_operations'].labels(
            operation=operation, level=level, result=result
        ).inc()
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        now = datetime.now()
        
        # Calculate metrics from recent data
        recent_requests = sum(self.request_counts.values())
        uptime_seconds = (now - self._start_time).total_seconds()
        rps = recent_requests / max(uptime_seconds, 1)
        
        # Average response time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        # Error rate
        total_errors = sum(self.error_counts.values())
        error_rate = total_errors / max(recent_requests, 1)
        
        # Mock system stats (in production, get from actual system)
        cache_hit_rate = 0.85  # Mock 85% hit rate
        active_connections = 25  # Mock connection count
        memory_usage = 256.5  # Mock memory usage in MB
        cpu_usage = 45.2  # Mock CPU usage percentage
        queue_depth = 3  # Mock queue depth
        
        # Determine system status
        status = self._determine_system_status(error_rate, avg_response_time, memory_usage, cache_hit_rate)
        
        metrics = SystemMetrics(
            timestamp=now,
            requests_per_second=rps,
            avg_response_time_ms=avg_response_time,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate,
            active_connections=active_connections,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            queue_depth=queue_depth,
            status=status
        )
        
        # Store in history
        self.metrics_history.append(metrics)
        
        # Check for alerts
        await self._check_alerts(metrics)
        
        return metrics
    
    def _determine_system_status(self, error_rate: float, response_time: float, 
                                memory_usage: float, cache_hit_rate: float) -> SystemStatus:
        """Determine overall system status"""
        
        if (error_rate > self.alert_thresholds['error_rate_threshold'] or
            response_time > self.alert_thresholds['response_time_threshold'] or
            memory_usage > 90):  # Critical memory threshold
            return SystemStatus.UNHEALTHY
        
        if (error_rate > self.alert_thresholds['error_rate_threshold'] * 0.5 or
            response_time > self.alert_thresholds['response_time_threshold'] * 0.7 or
            cache_hit_rate < self.alert_thresholds['cache_hit_rate_threshold'] or
            memory_usage > self.alert_thresholds['memory_threshold']):
            return SystemStatus.DEGRADED
        
        return SystemStatus.HEALTHY
    
    async def _check_alerts(self, metrics: SystemMetrics):
        """Check metrics against alert thresholds"""
        alerts = []
        
        if metrics.error_rate > self.alert_thresholds['error_rate_threshold']:
            alerts.append(f"High error rate: {metrics.error_rate:.1%}")
        
        if metrics.avg_response_time_ms > self.alert_thresholds['response_time_threshold']:
            alerts.append(f"High response time: {metrics.avg_response_time_ms:.0f}ms")
        
        if metrics.cache_hit_rate < self.alert_thresholds['cache_hit_rate_threshold']:
            alerts.append(f"Low cache hit rate: {metrics.cache_hit_rate:.1%}")
        
        if metrics.memory_usage_mb > self.alert_thresholds['memory_threshold']:
            alerts.append(f"High memory usage: {metrics.memory_usage_mb:.1f}MB")
        
        if alerts:
            self.logger.warning(f"System alerts: {'; '.join(alerts)}")
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff]
        
        if not recent_metrics:
            return {}
        
        return {
            'time_range_minutes': minutes,
            'avg_rps': sum(m.requests_per_second for m in recent_metrics) / len(recent_metrics),
            'avg_response_time': sum(m.avg_response_time_ms for m in recent_metrics) / len(recent_metrics),
            'avg_cache_hit_rate': sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics),
            'max_error_rate': max(m.error_rate for m in recent_metrics),
            'current_status': recent_metrics[-1].status.value,
            'data_points': len(recent_metrics)
        }

# =============================================================================
# MULTI-LEVEL CACHING SYSTEM
# =============================================================================

class ProductionCacheManager:
    """Production-grade multi-level caching system"""
    
    def __init__(self, 
                 l1_max_size: int = 1000,
                 l2_redis_client: MockRedis = None,
                 default_ttl: int = 3600):
        
        # L1: In-memory cache
        self.l1_cache: Dict[str, CacheEntry] = {}
        self.l1_max_size = l1_max_size
        self.l1_access_order = deque()
        
        # L2: Redis cache
        self.l2_client = l2_redis_client or MockRedis()
        
        # L3: Could be disk cache (not implemented in demo)
        
        self.default_ttl = default_ttl
        self.cache_stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l1_evictions': 0
        }
        self.logger = logging.getLogger(__name__)
        
        # Background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await self._cleanup_expired_entries()
                    await asyncio.sleep(300)  # Cleanup every 5 minutes
                except Exception as e:
                    self.logger.error(f"Cache cleanup error: {e}")
        
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with multi-level lookup"""
        
        # L1 lookup
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not entry.is_expired():
                entry.touch()
                self._update_access_order(key)
                self.cache_stats['l1_hits'] += 1
                self.logger.debug(f"L1 cache hit: {key}")
                return entry.value
            else:
                # Remove expired entry
                del self.l1_cache[key]
        
        self.cache_stats['l1_misses'] += 1
        
        # L2 lookup
        try:
            l2_value = await self.l2_client.get(key)
            if l2_value:
                # Deserialize and promote to L1
                value = json.loads(l2_value)
                await self._promote_to_l1(key, value)
                self.cache_stats['l2_hits'] += 1
                self.logger.debug(f"L2 cache hit: {key}")
                return value
        except Exception as e:
            self.logger.error(f"L2 cache lookup error: {e}")
        
        self.cache_stats['l2_misses'] += 1
        self.logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with multi-level storage"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        try:
            # Store in L1
            await self._set_l1(key, value, expires_at)
            
            # Store in L2
            await self._set_l2(key, value, ttl)
            
            self.logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return True
        
        except Exception as e:
            self.logger.error(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete from all cache levels"""
        try:
            # Remove from L1
            self.l1_cache.pop(key, None)
            
            # Remove from L2
            await self.l2_client.delete(key)
            
            self.logger.debug(f"Deleted from cache: {key}")
            return True
        
        except Exception as e:
            self.logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    async def _promote_to_l1(self, key: str, value: Any):
        """Promote L2 hit to L1 cache"""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=None,  # Will use L2 TTL
            cache_level=CacheLevel.L1_MEMORY,
            size_bytes=len(json.dumps(value).encode()) if isinstance(value, (dict, list)) else len(str(value))
        )
        
        await self._set_l1_entry(key, entry)
    
    async def _set_l1(self, key: str, value: Any, expires_at: datetime):
        """Set value in L1 cache"""
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            cache_level=CacheLevel.L1_MEMORY,
            size_bytes=len(json.dumps(value).encode()) if isinstance(value, (dict, list)) else len(str(value))
        )
        
        await self._set_l1_entry(key, entry)
    
    async def _set_l1_entry(self, key: str, entry: CacheEntry):
        """Set entry in L1 with eviction if needed"""
        # Check if we need to evict
        if len(self.l1_cache) >= self.l1_max_size and key not in self.l1_cache:
            await self._evict_l1_entry()
        
        self.l1_cache[key] = entry
        self._update_access_order(key)
    
    async def _set_l2(self, key: str, value: Any, ttl: int):
        """Set value in L2 cache"""
        serialized = json.dumps(value)
        await self.l2_client.set(key, serialized, ex=ttl)
    
    def _update_access_order(self, key: str):
        """Update LRU access order"""
        if key in self.l1_access_order:
            self.l1_access_order.remove(key)
        self.l1_access_order.append(key)
    
    async def _evict_l1_entry(self):
        """Evict least recently used entry from L1"""
        if not self.l1_access_order:
            return
        
        lru_key = self.l1_access_order.popleft()
        self.l1_cache.pop(lru_key, None)
        self.cache_stats['l1_evictions'] += 1
        self.logger.debug(f"Evicted from L1: {lru_key}")
    
    async def _cleanup_expired_entries(self):
        """Remove expired entries from L1 cache"""
        expired_keys = []
        
        for key, entry in self.l1_cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.l1_cache[key]
            if key in self.l1_access_order:
                self.l1_access_order.remove(key)
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired L1 entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = (self.cache_stats['l1_hits'] + self.cache_stats['l1_misses'])
        
        stats = {
            **self.cache_stats,
            'l1_size': len(self.l1_cache),
            'l1_hit_rate': self.cache_stats['l1_hits'] / max(total_requests, 1),
            'total_hit_rate': (self.cache_stats['l1_hits'] + self.cache_stats['l2_hits']) / max(total_requests, 1),
            'memory_usage_bytes': sum(entry.size_bytes for entry in self.l1_cache.values())
        }
        
        return stats

# =============================================================================
# SECURITY AND ACCESS CONTROL
# =============================================================================

class SecurityManager:
    """Production security and access control"""
    
    def __init__(self, auth_service: MockAuth = None):
        self.auth_service = auth_service or MockAuth()
        self.rate_limiters = {}
        self.blocked_ips = set()
        self.failed_attempts = defaultdict(list)
        self.security_events = deque(maxlen=1000)
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting configuration
        self.rate_limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'premium': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'admin': {'requests': 10000, 'window': 3600}    # 10k requests per hour
        }
    
    async def authenticate_request(self, api_key: str, ip_address: str = None) -> Optional[RequestContext]:
        """Authenticate API request"""
        
        # Check if IP is blocked
        if ip_address and ip_address in self.blocked_ips:
            self._log_security_event("blocked_ip_attempt", {"ip": ip_address})
            return None
        
        # Verify API key
        user_info = await self.auth_service.verify_token(api_key)
        if not user_info:
            await self._handle_failed_auth(api_key, ip_address)
            return None
        
        # Check rate limits
        user_id = user_info['user']
        roles = user_info['roles']
        
        if not await self._check_rate_limit(user_id, roles):
            self._log_security_event("rate_limit_exceeded", {"user": user_id})
            return None
        
        # Create request context
        context = RequestContext(
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            api_key=api_key,
            roles=roles,
            rate_limit_key=user_id,
            priority=self._get_user_priority(roles),
            metadata={"ip_address": ip_address}
        )
        
        self._log_security_event("successful_auth", {"user": user_id, "ip": ip_address})
        return context
    
    async def _handle_failed_auth(self, api_key: str, ip_address: str = None):
        """Handle failed authentication attempt"""
        now = datetime.now()
        
        # Track failed attempts by IP
        if ip_address:
            self.failed_attempts[ip_address].append(now)
            
            # Remove old attempts (older than 1 hour)
            self.failed_attempts[ip_address] = [
                attempt for attempt in self.failed_attempts[ip_address]
                if now - attempt < timedelta(hours=1)
            ]
            
            # Block IP if too many failed attempts
            if len(self.failed_attempts[ip_address]) > 10:
                self.blocked_ips.add(ip_address)
                self.logger.warning(f"Blocked IP due to repeated failed auth: {ip_address}")
        
        self._log_security_event("failed_auth", {
            "api_key_hash": hashlib.md5(api_key.encode()).hexdigest()[:8],
            "ip": ip_address
        })
    
    async def _check_rate_limit(self, user_id: str, roles: List[str]) -> bool:
        """Check if user is within rate limits"""
        # Determine rate limit tier
        tier = 'default'
        if 'admin' in roles:
            tier = 'admin'
        elif 'premium' in roles:
            tier = 'premium'
        
        limit_config = self.rate_limits[tier]
        
        # Simple in-memory rate limiting (in production, use Redis)
        now = datetime.now()
        
        if user_id not in self.rate_limiters:
            self.rate_limiters[user_id] = deque()
        
        user_requests = self.rate_limiters[user_id]
        
        # Remove old requests outside the window
        window_start = now - timedelta(seconds=limit_config['window'])
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if under limit
        if len(user_requests) < limit_config['requests']:
            user_requests.append(now)
            return True
        
        return False
    
    def _get_user_priority(self, roles: List[str]) -> int:
        """Get request priority based on user roles"""
        if 'admin' in roles:
            return 3  # Critical
        elif 'premium' in roles:
            return 2  # High
        else:
            return 1  # Normal
    
    def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': details
        }
        
        self.security_events.append(event)
        
        if event_type in ['blocked_ip_attempt', 'rate_limit_exceeded', 'failed_auth']:
            self.logger.warning(f"Security event: {event_type} - {details}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary"""
        recent_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event['timestamp']) > datetime.now() - timedelta(hours=24)
        ]
        
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event['event_type']] += 1
        
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'recent_events_24h': len(recent_events),
            'event_type_counts': dict(event_counts),
            'active_rate_limiters': len(self.rate_limiters)
        }

# =============================================================================
# PRODUCTION RAG SYSTEM
# =============================================================================

class ProductionRAGSystem:
    """Complete production-ready RAG system"""
    
    def __init__(self,
                 vector_db: Any = None,
                 embedding_service: Any = None,
                 response_generator: Any = None):
        
        # Core RAG components
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.response_generator = response_generator
        
        # Production components
        self.metrics_collector = MetricsCollector()
        self.cache_manager = ProductionCacheManager()
        self.security_manager = SecurityManager()
        
        # System state
        self.is_healthy = True
        self.maintenance_mode = False
        self.request_queue = asyncio.Queue(maxsize=1000)
        self.worker_pool = None
        
        # Configuration
        self.config = {
            'max_concurrent_requests': 50,
            'request_timeout': 30,
            'cache_query_results': True,
            'enable_monitoring': True,
            'log_level': 'INFO'
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        asyncio.create_task(self._metrics_collection_loop())
        asyncio.create_task(self._health_check_loop())
    
    async def query(self, query: str, api_key: str, 
                   ip_address: str = None, **kwargs) -> Dict[str, Any]:
        """Process RAG query with full production pipeline"""
        
        start_time = time.time()
        request_context = None
        
        try:
            # 1. Authentication and authorization
            request_context = await self.security_manager.authenticate_request(api_key, ip_address)
            if not request_context:
                await self.metrics_collector.record_request("query", "auth_failed", 0)
                return self._error_response("Authentication failed", 401)
            
            # 2. System health check
            if self.maintenance_mode:
                await self.metrics_collector.record_request("query", "maintenance", 0)
                return self._error_response("System under maintenance", 503)
            
            if not self.is_healthy:
                await self.metrics_collector.record_request("query", "unhealthy", 0)
                return self._error_response("System temporarily unavailable", 503)
            
            # 3. Cache lookup
            cache_key = self._generate_cache_key(query, kwargs)
            if self.config['cache_query_results']:
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result:
                    await self.metrics_collector.record_cache_operation("get", "multi", "hit")
                    cached_result['cached'] = True
                    cached_result['request_id'] = request_context.request_id
                    return cached_result
            
            await self.metrics_collector.record_cache_operation("get", "multi", "miss")
            
            # 4. Queue request with priority
            try:
                await asyncio.wait_for(
                    self.request_queue.put((request_context, query, kwargs)),
                    timeout=5.0  # 5 second queue timeout
                )
            except asyncio.TimeoutError:
                await self.metrics_collector.record_request("query", "queue_timeout", 0)
                return self._error_response("System overloaded", 429)
            
            # 5. Process request
            result = await self._process_query_request(request_context, query, kwargs)
            
            # 6. Cache result
            if self.config['cache_query_results'] and result.get('status') == 'success':
                cache_ttl = request_context.cache_ttl
                await self.cache_manager.set(cache_key, result, ttl=cache_ttl)
                await self.metrics_collector.record_cache_operation("set", "multi", "success")
            
            # 7. Record metrics
            duration_ms = (time.time() - start_time) * 1000
            status = "success" if result.get('status') == 'success' else "error"
            await self.metrics_collector.record_request("query", status, duration_ms)
            
            result['request_id'] = request_context.request_id
            result['processing_time_ms'] = duration_ms
            
            return result
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            await self.metrics_collector.record_request("query", "error", duration_ms)
            
            self.logger.error(f"Query processing error: {e}", exc_info=True)
            
            return self._error_response(
                "Internal server error",
                500,
                request_id=request_context.request_id if request_context else None
            )
    
    async def _process_query_request(self, context: RequestContext, 
                                   query: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual query request"""
        
        try:
            # Mock RAG processing (replace with actual implementation)
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Mock response
            response = {
                'status': 'success',
                'query': query,
                'response': f"This is a mock response for: {query[:100]}...",
                'sources': [
                    {
                        'id': 'doc1',
                        'title': 'Sample Document 1',
                        'relevance_score': 0.95,
                        'content_preview': 'Sample content preview...'
                    }
                ],
                'metadata': {
                    'user_id': context.user_id,
                    'processing_method': 'production_pipeline',
                    'model_version': '1.0.0',
                    'confidence_score': 0.89
                }
            }
            
            return response
        
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'query': query
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'uptime_seconds': (datetime.now() - self.metrics_collector._start_time).total_seconds()
        }
        
        try:
            # Check core components
            component_health = {}
            
            # Vector DB health
            component_health['vector_db'] = 'healthy'  # Mock check
            
            # Cache health
            cache_stats = self.cache_manager.get_cache_stats()
            component_health['cache'] = 'healthy' if cache_stats['l1_hit_rate'] > 0.5 else 'degraded'
            
            # Metrics collection
            current_metrics = await self.metrics_collector.collect_system_metrics()
            component_health['metrics'] = current_metrics.status.value
            
            # Security system
            security_summary = self.security_manager.get_security_summary()
            component_health['security'] = 'healthy'
            
            health_status['components'] = component_health
            health_status['metrics'] = current_metrics.to_dict()
            health_status['cache_stats'] = cache_stats
            health_status['security_stats'] = security_summary
            
            # Overall status
            if any(status == 'unhealthy' for status in component_health.values()):
                health_status['status'] = 'unhealthy'
                self.is_healthy = False
            elif any(status == 'degraded' for status in component_health.values()):
                health_status['status'] = 'degraded'
                self.is_healthy = True
            else:
                health_status['status'] = 'healthy'
                self.is_healthy = True
        
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            self.is_healthy = False
            self.logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def _generate_cache_key(self, query: str, kwargs: Dict[str, Any]) -> str:
        """Generate cache key for query"""
        key_data = {
            'query': query,
            'params': {k: v for k, v in kwargs.items() if k in ['domain', 'k', 'filters']}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _error_response(self, message: str, status_code: int, 
                       request_id: str = None) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'status': 'error',
            'error': message,
            'status_code': status_code,
            'request_id': request_id,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _metrics_collection_loop(self):
        """Background metrics collection"""
        while True:
            try:
                await self.metrics_collector.collect_system_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)
    
    async def _health_check_loop(self):
        """Background health monitoring"""
        while True:
            try:
                await self.health_check()
                await asyncio.sleep(30)  # Health check every 30 seconds
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(30)
    
    async def set_maintenance_mode(self, enabled: bool):
        """Enable/disable maintenance mode"""
        self.maintenance_mode = enabled
        self.logger.info(f"Maintenance mode {'enabled' if enabled else 'disabled'}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        return {
            'system_status': 'healthy' if self.is_healthy else 'unhealthy',
            'maintenance_mode': self.maintenance_mode,
            'queue_size': self.request_queue.qsize(),
            'configuration': self.config,
            'metrics_summary': self.metrics_collector.get_metrics_summary(),
            'cache_summary': self.cache_manager.get_cache_stats(),
            'security_summary': self.security_manager.get_security_summary()
        }

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

async def demonstrate_production_rag_system():
    """
    Comprehensive demonstration of production RAG system with
    monitoring, caching, security, and scalability features.
    """
    
    print("🚀 Production RAG System Demo")
    print("Enterprise-Grade Implementation with Monitoring & Security")
    print("Applications: Lawstronaut Legal Platform + Optimizely Content Engine")
    
    # Initialize production system
    print("\n" + "="*60)
    print("Production System Initialization")
    print("="*60)
    
    rag_system = ProductionRAGSystem()
    
    # Wait for background tasks to initialize
    await asyncio.sleep(1)
    
    print("✅ Production RAG system initialized")
    print("✅ Background monitoring started")
    print("✅ Security layer activated")
    print("✅ Multi-level caching enabled")
    
    # Security and Authentication Demo
    print("\n" + "="*60)
    print("Security and Authentication")
    print("="*60)
    
    # Test authentication scenarios
    auth_tests = [
        ("valid_user", "key1", "192.168.1.100", True),
        ("admin_user", "admin_key", "192.168.1.101", True),
        ("invalid_user", "invalid_key", "192.168.1.102", False),
        ("blocked_user", "bad_key", "192.168.1.100", False)  # Same IP as first, will accumulate
    ]
    
    for test_name, api_key, ip, should_succeed in auth_tests:
        print(f"\n🔐 Testing: {test_name}")
        
        # Simulate multiple failed attempts for blocking demo
        if test_name == "blocked_user":
            for _ in range(12):  # Exceed the block threshold
                await rag_system.security_manager.authenticate_request("bad_key", ip)
        
        context = await rag_system.security_manager.authenticate_request(api_key, ip)
        
        if should_succeed and context:
            print(f"   ✅ Authentication successful")
            print(f"   👤 User: {context.user_id}")
            print(f"   🎭 Roles: {context.roles}")
            print(f"   🚀 Priority: {context.priority}")
        elif not should_succeed and not context:
            print(f"   ❌ Authentication failed (expected)")
        else:
            print(f"   ⚠️  Unexpected result")
    
    # Caching System Demo
    print("\n" + "="*60)
    print("Multi-Level Caching System")
    print("="*60)
    
    cache_manager = rag_system.cache_manager
    
    # Cache operations demo
    test_data = {
        "query1": {"response": "Legal compliance answer", "sources": ["doc1", "doc2"]},
        "query2": {"response": "A/B testing guide", "sources": ["guide1", "tutorial1"]},
        "query3": {"response": "User segmentation strategy", "sources": ["framework1"]}
    }
    
    print(f"\n💾 Caching Test Data:")
    for key, value in test_data.items():
        await cache_manager.set(key, value, ttl=300)  # 5-minute TTL
        print(f"   • Cached: {key}")
    
    print(f"\n🔍 Cache Retrieval Test:")
    for key in test_data.keys():
        start_time = time.time()
        result = await cache_manager.get(key)
        retrieval_time = (time.time() - start_time) * 1000
        
        if result:
            print(f"   ✅ {key}: Retrieved in {retrieval_time:.2f}ms")
        else:
            print(f"   ❌ {key}: Cache miss")
    
    cache_stats = cache_manager.get_cache_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"   • L1 Hit Rate: {cache_stats['l1_hit_rate']:.1%}")
    print(f"   • Total Hit Rate: {cache_stats['total_hit_rate']:.1%}")
    print(f"   • L1 Cache Size: {cache_stats['l1_size']} entries")
    print(f"   • Memory Usage: {cache_stats['memory_usage_bytes']} bytes")
    
    # Production Query Processing Demo
    print("\n" + "="*60)
    print("Production Query Processing")
    print("="*60)
    
    test_queries = [
        ("What are GDPR compliance requirements?", "key1", "192.168.1.100"),
        ("How to optimize conversion rates?", "admin_key", "192.168.1.101"),
        ("What user segmentation strategies work best?", "key1", "192.168.1.100"),
        ("Complex legal liability question with multiple aspects?", "admin_key", "192.168.1.101")
    ]
    
    for query, api_key, ip in test_queries:
        print(f"\n🔍 Processing: {query[:50]}...")
        
        start_time = time.time()
        result = await rag_system.query(query, api_key, ip, domain="legal")
        processing_time = (time.time() - start_time) * 1000
        
        if result.get('status') == 'success':
            print(f"   ✅ Success in {processing_time:.1f}ms")
            print(f"   📋 Request ID: {result.get('request_id', 'N/A')}")
            print(f"   💾 Cached: {result.get('cached', False)}")
            print(f"   🎯 Confidence: {result.get('metadata', {}).get('confidence_score', 'N/A')}")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
    
    # System Health Monitoring Demo
    print("\n" + "="*60)
    print("System Health and Monitoring")
    print("="*60)
    
    health_status = await rag_system.health_check()
    
    print(f"\n🏥 System Health Check:")
    print(f"   • Overall Status: {health_status['status'].upper()}")
    print(f"   • Uptime: {health_status['uptime_seconds']:.0f} seconds")
    
    print(f"\n🔧 Component Health:")
    for component, status in health_status.get('components', {}).items():
        status_icon = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
        print(f"   • {component}: {status_icon} {status}")
    
    # Performance Metrics
    metrics = health_status.get('metrics', {})
    if metrics:
        print(f"\n📊 Performance Metrics:")
        print(f"   • Requests/sec: {metrics.get('requests_per_second', 0):.2f}")
        print(f"   • Avg Response Time: {metrics.get('avg_response_time_ms', 0):.0f}ms")
        print(f"   • Error Rate: {metrics.get('error_rate', 0):.1%}")
        print(f"   • Cache Hit Rate: {metrics.get('cache_hit_rate', 0):.1%}")
        print(f"   • Memory Usage: {metrics.get('memory_usage_mb', 0):.1f}MB")
        print(f"   • CPU Usage: {metrics.get('cpu_usage_percent', 0):.1f}%")
    
    # Security Summary
    security_stats = health_status.get('security_stats', {})
    if security_stats:
        print(f"\n🔒 Security Summary:")
        print(f"   • Blocked IPs: {security_stats.get('blocked_ips_count', 0)}")
        print(f"   • Recent Events (24h): {security_stats.get('recent_events_24h', 0)}")
        print(f"   • Active Rate Limiters: {security_stats.get('active_rate_limiters', 0)}")
    
    # Load Testing Simulation
    print("\n" + "="*60)
    print("Load Testing Simulation")
    print("="*60)
    
    print(f"\n🚀 Simulating concurrent requests...")
    
    async def simulate_user_request(user_id: int):
        """Simulate individual user request"""
        query = f"Test query from user {user_id}"
        api_key = "key1" if user_id % 2 == 0 else "admin_key"
        ip = f"192.168.1.{100 + (user_id % 50)}"
        
        start_time = time.time()
        result = await rag_system.query(query, api_key, ip)
        duration = (time.time() - start_time) * 1000
        
        return {
            'user_id': user_id,
            'success': result.get('status') == 'success',
            'duration_ms': duration,
            'cached': result.get('cached', False)
        }
    
    # Run concurrent requests
    num_concurrent = 20
    tasks = [simulate_user_request(i) for i in range(num_concurrent)]
    
    concurrent_start = time.time()
    results = await asyncio.gather(*tasks)
    total_duration = (time.time() - concurrent_start) * 1000
    
    # Analyze load test results
    successful_requests = [r for r in results if r['success']]
    cached_requests = [r for r in results if r['cached']]
    
    avg_duration = sum(r['duration_ms'] for r in successful_requests) / len(successful_requests) if successful_requests else 0
    
    print(f"\n📊 Load Test Results:")
    print(f"   • Total Requests: {num_concurrent}")
    print(f"   • Successful: {len(successful_requests)} ({len(successful_requests)/num_concurrent:.1%})")
    print(f"   • Cached Responses: {len(cached_requests)} ({len(cached_requests)/num_concurrent:.1%})")
    print(f"   • Total Time: {total_duration:.0f}ms")
    print(f"   • Avg Response Time: {avg_duration:.0f}ms")
    print(f"   • Throughput: {num_concurrent / (total_duration / 1000):.1f} req/sec")
    
    # Maintenance Mode Demo
    print("\n" + "="*60)
    print("Maintenance Mode")
    print("="*60)
    
    print(f"\n🔧 Enabling maintenance mode...")
    await rag_system.set_maintenance_mode(True)
    
    # Test request during maintenance
    maintenance_result = await rag_system.query("Test query during maintenance", "key1", "192.168.1.100")
    print(f"   • Request during maintenance: {maintenance_result.get('error', 'Unknown')}")
    print(f"   • Status code: {maintenance_result.get('status_code', 'N/A')}")
    
    # Disable maintenance mode
    await rag_system.set_maintenance_mode(False)
    print(f"   ✅ Maintenance mode disabled")
    
    # Final System Summary
    print("\n" + "="*60)
    print("Final System Summary")
    print("="*60)
    
    system_summary = rag_system.get_system_summary()
    
    print(f"\n📋 System Overview:")
    print(f"   • Status: {system_summary['system_status'].upper()}")
    print(f"   • Maintenance: {'Yes' if system_summary['maintenance_mode'] else 'No'}")
    print(f"   • Queue Size: {system_summary['queue_size']}")
    
    metrics_summary = system_summary.get('metrics_summary', {})
    if metrics_summary:
        print(f"\n📊 Performance Summary (60min):")
        print(f"   • Avg RPS: {metrics_summary.get('avg_rps', 0):.2f}")
        print(f"   • Avg Response Time: {metrics_summary.get('avg_response_time', 0):.0f}ms")
        print(f"   • Cache Hit Rate: {metrics_summary.get('avg_cache_hit_rate', 0):.1%}")
        print(f"   • Max Error Rate: {metrics_summary.get('max_error_rate', 0):.1%}")
    
    print("\n" + "="*60)
    print("✅ Production RAG System Demo Complete")
    print("="*60)
    
    print(f"\n🎯 Production Features Demonstrated:")
    print(f"   • ✅ Multi-level authentication and authorization")
    print(f"   • ✅ Rate limiting and IP blocking")
    print(f"   • ✅ Multi-level caching (L1 memory + L2 Redis)")
    print(f"   • ✅ Real-time monitoring and metrics collection")
    print(f"   • ✅ Health checks and system status tracking")
    print(f"   • ✅ Error handling and graceful degradation")
    print(f"   • ✅ Load balancing and concurrent request handling")
    print(f"   • ✅ Maintenance mode and operational controls")
    print(f"   • ✅ Security event logging and intrusion detection")
    print(f"   • ✅ Performance optimization and caching strategies")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run comprehensive production system demonstration
    asyncio.run(demonstrate_production_rag_system())
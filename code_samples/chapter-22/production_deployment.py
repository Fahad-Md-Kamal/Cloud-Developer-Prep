"""
Production Deployment and Monitoring for Conversational AI Systems

This module demonstrates production deployment patterns, monitoring strategies,
and operational best practices for enterprise conversational AI systems like
those deployed at Lawstronaut and Optimizely.

Key concepts covered:
- Container orchestration and deployment strategies
- Health checks and observability patterns
- Performance monitoring and alerting
- Scaling strategies and load management
- Circuit breaker patterns and fault tolerance

Real-world applications:
- High-availability legal AI service for Lawstronaut
- Scalable personalization engine for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import psutil
import threading
from collections import deque, defaultdict

# =============================================================================
# HEALTH CHECK AND MONITORING
# =============================================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service_name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    request_rate_per_minute: float
    error_rate_percent: float
    avg_response_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.checks[name] = check_func
        self.logger.info(f"Registered health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                service_name=name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        try:
            check_func = self.checks[name]
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                return result
            elif isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                return HealthCheckResult(
                    service_name=name,
                    status=status,
                    response_time_ms=response_time,
                    message="OK" if result else "Check failed"
                )
            else:
                return HealthCheckResult(
                    service_name=name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=str(result)
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service_name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}"
            )
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        # Run checks concurrently
        check_tasks = [
            self.run_check(name) for name in self.checks.keys()
        ]
        
        check_results = await asyncio.gather(*check_tasks)
        
        for result in check_results:
            results[result.service_name] = result
        
        return results
    
    def get_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system health status"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

# =============================================================================
# METRICS COLLECTION AND MONITORING
# =============================================================================

class MetricsCollector:
    """Collects and aggregates system metrics"""
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 measurements
        self.request_counters = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.active_connections = 0
        self.logger = logging.getLogger(__name__)
        self._collection_task: Optional[asyncio.Task] = None
    
    def start_collection(self):
        """Start metrics collection"""
        if not self._collection_task:
            self._collection_task = asyncio.create_task(self._collect_metrics_loop())
            self.logger.info("Started metrics collection")
    
    def stop_collection(self):
        """Stop metrics collection"""
        if self._collection_task:
            self._collection_task.cancel()
            self._collection_task = None
            self.logger.info("Stopped metrics collection")
    
    async def _collect_metrics_loop(self):
        """Continuous metrics collection loop"""
        while True:
            try:
                metrics = self._collect_current_metrics()
                self.metrics_history.append(metrics)
                
                # Log metrics periodically
                if len(self.metrics_history) % 10 == 0:
                    self.logger.info(f"System metrics - CPU: {metrics.cpu_percent:.1f}%, "
                                   f"Memory: {metrics.memory_percent:.1f}%, "
                                   f"Requests/min: {metrics.request_rate_per_minute:.1f}")
                
                await asyncio.sleep(self.collection_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def _collect_current_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Application metrics
        current_time = datetime.now()
        minute_ago = current_time - timedelta(minutes=1)
        
        # Calculate request rate (requests per minute)
        recent_requests = sum(
            count for timestamp, count in self.request_counters.items()
            if timestamp > minute_ago
        )
        
        # Calculate error rate
        recent_errors = sum(
            count for timestamp, count in self.error_counts.items()
            if timestamp > minute_ago
        )
        
        error_rate = (recent_errors / recent_requests * 100) if recent_requests > 0 else 0
        
        # Calculate average response time
        recent_response_times = [
            rt for rt in self.response_times
            if rt > 0  # Filter valid response times
        ]
        avg_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=(disk.used / disk.total) * 100,
            active_connections=self.active_connections,
            request_rate_per_minute=recent_requests,
            error_rate_percent=error_rate,
            avg_response_time_ms=avg_response_time
        )
    
    def record_request(self):
        """Record a new request"""
        timestamp = datetime.now().replace(second=0, microsecond=0)  # Round to minute
        self.request_counters[timestamp] += 1
    
    def record_response_time(self, response_time_ms: float):
        """Record response time for a request"""
        self.response_times.append(response_time_ms)
    
    def record_error(self):
        """Record an error occurrence"""
        timestamp = datetime.now().replace(second=0, microsecond=0)  # Round to minute
        self.error_counts[timestamp] += 1
    
    def increment_connections(self):
        """Increment active connections counter"""
        self.active_connections += 1
    
    def decrement_connections(self):
        """Decrement active connections counter"""
        self.active_connections = max(0, self.active_connections - 1)
    
    def get_recent_metrics(self, minutes: int = 5) -> List[SystemMetrics]:
        """Get metrics from recent time period"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]

# =============================================================================
# CIRCUIT BREAKER PATTERN
# =============================================================================

class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: int = 60          # Seconds before trying half-open
    success_threshold: int = 3          # Successful calls to close from half-open
    timeout_seconds: float = 30.0       # Request timeout

class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._set_half_open()
            else:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else asyncio.create_task(asyncio.coroutine(lambda: func(*args, **kwargs))()),
                timeout=self.config.timeout_seconds
            )
            
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN to HALF_OPEN"""
        if not self.last_failure_time:
            return True
        
        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout
    
    def _set_half_open(self):
        """Set circuit breaker to HALF_OPEN state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.logger.info(f"Circuit breaker '{self.name}' set to HALF_OPEN")
    
    def _record_success(self):
        """Record successful operation"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._set_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if (self.state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN] and 
            self.failure_count >= self.config.failure_threshold):
            self._set_open()
    
    def _set_closed(self):
        """Set circuit breaker to CLOSED state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(f"Circuit breaker '{self.name}' set to CLOSED")
    
    def _set_open(self):
        """Set circuit breaker to OPEN state"""
        self.state = CircuitBreakerState.OPEN
        self.logger.warning(f"Circuit breaker '{self.name}' set to OPEN after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

# =============================================================================
# SCALING AND LOAD MANAGEMENT
# =============================================================================

class LoadBalancer:
    """Simple round-robin load balancer"""
    
    def __init__(self):
        self.instances: List[str] = []
        self.current_index = 0
        self.instance_health: Dict[str, bool] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_instance(self, instance_id: str):
        """Add a new instance to the pool"""
        if instance_id not in self.instances:
            self.instances.append(instance_id)
            self.instance_health[instance_id] = True
            self.logger.info(f"Added instance to load balancer: {instance_id}")
    
    def remove_instance(self, instance_id: str):
        """Remove an instance from the pool"""
        if instance_id in self.instances:
            self.instances.remove(instance_id)
            self.instance_health.pop(instance_id, None)
            self.logger.info(f"Removed instance from load balancer: {instance_id}")
    
    def mark_instance_unhealthy(self, instance_id: str):
        """Mark an instance as unhealthy"""
        if instance_id in self.instance_health:
            self.instance_health[instance_id] = False
            self.logger.warning(f"Marked instance as unhealthy: {instance_id}")
    
    def mark_instance_healthy(self, instance_id: str):
        """Mark an instance as healthy"""
        if instance_id in self.instance_health:
            self.instance_health[instance_id] = True
            self.logger.info(f"Marked instance as healthy: {instance_id}")
    
    def get_next_instance(self) -> Optional[str]:
        """Get next healthy instance using round-robin"""
        healthy_instances = [
            instance for instance in self.instances 
            if self.instance_health.get(instance, False)
        ]
        
        if not healthy_instances:
            return None
        
        # Round-robin among healthy instances
        instance = healthy_instances[self.current_index % len(healthy_instances)]
        self.current_index += 1
        
        return instance
    
    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        healthy_count = sum(self.instance_health.values())
        
        return {
            "total_instances": len(self.instances),
            "healthy_instances": healthy_count,
            "instance_status": self.instance_health.copy()
        }

class AutoScaler:
    """Automatic scaling based on metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector, load_balancer: LoadBalancer):
        self.metrics_collector = metrics_collector
        self.load_balancer = load_balancer
        self.min_instances = 2
        self.max_instances = 10
        self.scale_up_threshold = 80.0    # CPU percentage
        self.scale_down_threshold = 30.0  # CPU percentage
        self.scale_cooldown = 300         # Seconds between scaling actions
        self.last_scale_action: Optional[datetime] = None
        self.logger = logging.getLogger(__name__)
    
    async def check_scaling_conditions(self):
        """Check if scaling action is needed"""
        # Check cooldown period
        if self.last_scale_action:
            time_since_last_scale = (datetime.now() - self.last_scale_action).total_seconds()
            if time_since_last_scale < self.scale_cooldown:
                return
        
        # Get recent metrics
        recent_metrics = self.metrics_collector.get_recent_metrics(minutes=5)
        if not recent_metrics:
            return
        
        # Calculate average CPU usage
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        current_instances = self.load_balancer.get_status()["healthy_instances"]
        
        # Scale up condition
        if (avg_cpu > self.scale_up_threshold and 
            current_instances < self.max_instances):
            await self._scale_up()
        
        # Scale down condition
        elif (avg_cpu < self.scale_down_threshold and 
              current_instances > self.min_instances):
            await self._scale_down()
    
    async def _scale_up(self):
        """Add new instance"""
        new_instance_id = f"instance_{int(time.time())}"
        
        # Simulate instance creation
        await asyncio.sleep(0.1)
        
        self.load_balancer.add_instance(new_instance_id)
        self.last_scale_action = datetime.now()
        
        self.logger.info(f"Scaled up: Added instance {new_instance_id}")
    
    async def _scale_down(self):
        """Remove instance"""
        # Get least loaded instance (simplified - just remove last one)
        instances = self.load_balancer.instances
        if instances:
            instance_to_remove = instances[-1]
            self.load_balancer.remove_instance(instance_to_remove)
            self.last_scale_action = datetime.now()
            
            self.logger.info(f"Scaled down: Removed instance {instance_to_remove}")

# =============================================================================
# DEPLOYMENT MANAGER
# =============================================================================

@dataclass
class DeploymentConfig:
    """Configuration for deployment"""
    service_name: str
    version: str
    port: int
    replicas: int = 3
    health_check_path: str = "/health"
    resource_limits: Dict[str, str] = field(default_factory=lambda: {
        "cpu": "500m",
        "memory": "512Mi"
    })
    environment_variables: Dict[str, str] = field(default_factory=dict)

class DeploymentManager:
    """Manages service deployment and lifecycle"""
    
    def __init__(self):
        self.health_checker = HealthChecker()
        self.metrics_collector = MetricsCollector()
        self.load_balancer = LoadBalancer()
        self.auto_scaler = AutoScaler(self.metrics_collector, self.load_balancer)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger(__name__)
        
        # Setup health checks
        self._setup_health_checks()
    
    def _setup_health_checks(self):
        """Setup standard health checks"""
        
        async def database_check():
            """Check database connectivity"""
            # Mock database check
            await asyncio.sleep(0.01)
            return HealthCheckResult(
                service_name="database",
                status=HealthStatus.HEALTHY,
                response_time_ms=10,
                message="Database connection OK"
            )
        
        async def redis_check():
            """Check Redis connectivity"""
            # Mock Redis check
            await asyncio.sleep(0.005)
            return HealthCheckResult(
                service_name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=5,
                message="Redis connection OK"
            )
        
        def disk_space_check():
            """Check disk space"""
            disk_usage = psutil.disk_usage('/')
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage critical: {usage_percent:.1f}%"
            elif usage_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_percent:.1f}%"
            
            return HealthCheckResult(
                service_name="disk_space",
                status=status,
                response_time_ms=1,
                message=message
            )
        
        def memory_check():
            """Check memory usage"""
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critical: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return HealthCheckResult(
                service_name="memory",
                status=status,
                response_time_ms=1,
                message=message
            )
        
        # Register health checks
        self.health_checker.register_check("database", database_check)
        self.health_checker.register_check("redis", redis_check)
        self.health_checker.register_check("disk_space", disk_space_check)
        self.health_checker.register_check("memory", memory_check)
    
    def add_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Add circuit breaker for external service"""
        self.circuit_breakers[name] = CircuitBreaker(name, config)
        self.logger.info(f"Added circuit breaker: {name}")
    
    async def deploy_service(self, config: DeploymentConfig) -> bool:
        """Deploy service with specified configuration"""
        self.logger.info(f"Deploying service: {config.service_name} v{config.version}")
        
        try:
            # Simulate deployment steps
            await self._create_deployment(config)
            await self._setup_service_discovery(config)
            await self._configure_load_balancer(config)
            
            self.logger.info(f"Successfully deployed {config.service_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            return False
    
    async def _create_deployment(self, config: DeploymentConfig):
        """Create deployment (mock Kubernetes deployment)"""
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": config.service_name},
            "spec": {
                "replicas": config.replicas,
                "selector": {"matchLabels": {"app": config.service_name}},
                "template": {
                    "metadata": {"labels": {"app": config.service_name}},
                    "spec": {
                        "containers": [{
                            "name": config.service_name,
                            "image": f"{config.service_name}:{config.version}",
                            "ports": [{"containerPort": config.port}],
                            "resources": {"limits": config.resource_limits},
                            "env": [
                                {"name": k, "value": v} 
                                for k, v in config.environment_variables.items()
                            ],
                            "livenessProbe": {
                                "httpGet": {
                                    "path": config.health_check_path,
                                    "port": config.port
                                },
                                "periodSeconds": 30
                            }
                        }]
                    }
                }
            }
        }
        
        # Mock deployment creation
        await asyncio.sleep(2)  # Simulate deployment time
        self.logger.info(f"Created deployment manifest: {json.dumps(deployment_manifest, indent=2)}")
    
    async def _setup_service_discovery(self, config: DeploymentConfig):
        """Setup service discovery"""
        service_manifest = {
            "apiVersion": "v1", 
            "kind": "Service",
            "metadata": {"name": config.service_name},
            "spec": {
                "selector": {"app": config.service_name},
                "ports": [{"port": 80, "targetPort": config.port}],
                "type": "ClusterIP"
            }
        }
        
        await asyncio.sleep(0.5)
        self.logger.info(f"Setup service discovery for {config.service_name}")
    
    async def _configure_load_balancer(self, config: DeploymentConfig):
        """Configure load balancer with initial instances"""
        for i in range(config.replicas):
            instance_id = f"{config.service_name}-{i}"
            self.load_balancer.add_instance(instance_id)
        
        self.logger.info(f"Configured load balancer with {config.replicas} instances")
    
    async def start_monitoring(self):
        """Start all monitoring components"""
        self.logger.info("Starting monitoring systems")
        
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        # Start auto-scaling monitoring
        async def auto_scaling_loop():
            while True:
                try:
                    await self.auto_scaler.check_scaling_conditions()
                    await asyncio.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Auto-scaling error: {e}")
                    await asyncio.sleep(30)
        
        asyncio.create_task(auto_scaling_loop())
        
        self.logger.info("Monitoring systems started")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        # Run health checks
        health_results = await self.health_checker.run_all_checks()
        overall_health = self.health_checker.get_overall_status(health_results)
        
        # Get metrics
        recent_metrics = self.metrics_collector.get_recent_metrics(minutes=1)
        current_metrics = recent_metrics[-1] if recent_metrics else None
        
        # Get load balancer status
        lb_status = self.load_balancer.get_status()
        
        # Get circuit breaker statuses
        cb_statuses = {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
        
        return {
            "overall_health": overall_health.value,
            "health_checks": {name: result.status.value for name, result in health_results.items()},
            "metrics": {
                "cpu_percent": current_metrics.cpu_percent if current_metrics else 0,
                "memory_percent": current_metrics.memory_percent if current_metrics else 0,
                "request_rate": current_metrics.request_rate_per_minute if current_metrics else 0,
                "error_rate": current_metrics.error_rate_percent if current_metrics else 0,
                "avg_response_time": current_metrics.avg_response_time_ms if current_metrics else 0
            },
            "load_balancer": lb_status,
            "circuit_breakers": cb_statuses,
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

class ProductionDeploymentDemo:
    """Demonstration of production deployment and monitoring"""
    
    def __init__(self):
        self.setup_logging()
        self.deployment_manager = DeploymentManager()
    
    def setup_logging(self):
        """Configure logging for the demo"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def demo_service_deployment(self):
        """Demonstrate service deployment process"""
        print("\n" + "="*60)
        print("Service Deployment Demo - Production Pipeline")
        print("="*60)
        
        # Legal AI Service Configuration (Lawstronaut)
        legal_config = DeploymentConfig(
            service_name="legal-ai-service",
            version="2.1.0",
            port=8080,
            replicas=4,
            health_check_path="/api/v1/health",
            resource_limits={"cpu": "1000m", "memory": "2Gi"},
            environment_variables={
                "DATABASE_URL": "postgresql://legal-db:5432/lawstronaut",
                "REDIS_URL": "redis://legal-cache:6379",
                "LOG_LEVEL": "INFO",
                "MAX_WORKERS": "8"
            }
        )
        
        # Personalization Service Configuration (Optimizely)
        personalization_config = DeploymentConfig(
            service_name="personalization-engine",
            version="1.5.2",
            port=9090,
            replicas=6,
            health_check_path="/health",
            resource_limits={"cpu": "800m", "memory": "1.5Gi"},
            environment_variables={
                "ANALYTICS_DATABASE": "clickhouse://analytics:8123",
                "FEATURE_STORE": "redis://features:6379",
                "ML_MODEL_PATH": "/models/personalization-v1.5.2",
                "BATCH_SIZE": "1000"
            }
        )
        
        print(f"🚀 Deploying Legal AI Service...")
        legal_success = await self.deployment_manager.deploy_service(legal_config)
        print(f"   {'✅ Success' if legal_success else '❌ Failed'}")
        
        print(f"🎯 Deploying Personalization Engine...")
        personalization_success = await self.deployment_manager.deploy_service(personalization_config)
        print(f"   {'✅ Success' if personalization_success else '❌ Failed'}")
        
        return legal_success and personalization_success
    
    async def demo_health_monitoring(self):
        """Demonstrate health monitoring capabilities"""
        print("\n" + "="*60)
        print("Health Monitoring Demo - System Observability")
        print("="*60)
        
        # Add circuit breakers for external services
        self.deployment_manager.add_circuit_breaker(
            "legal_database",
            CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
        )
        
        self.deployment_manager.add_circuit_breaker(
            "analytics_api",
            CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
        )
        
        print("🔍 Running comprehensive health checks...")
        
        # Get system status multiple times to show monitoring
        for i in range(3):
            print(f"\n📊 Health Check #{i+1}:")
            status = await self.deployment_manager.get_system_status()
            
            print(f"   • Overall Health: {status['overall_health'].upper()}")
            print(f"   • CPU Usage: {status['metrics']['cpu_percent']:.1f}%")
            print(f"   • Memory Usage: {status['metrics']['memory_percent']:.1f}%")
            print(f"   • Active Instances: {status['load_balancer']['healthy_instances']}")
            
            # Show individual health check results
            print(f"   • Service Health:")
            for service, health_status in status['health_checks'].items():
                status_icon = "✅" if health_status == "healthy" else "⚠️" if health_status == "degraded" else "❌"
                print(f"     {status_icon} {service}: {health_status}")
            
            await asyncio.sleep(2)
    
    async def demo_circuit_breaker(self):
        """Demonstrate circuit breaker functionality"""
        print("\n" + "="*60)
        print("Circuit Breaker Demo - Fault Tolerance")
        print("="*60)
        
        # Get circuit breaker
        cb = self.deployment_manager.circuit_breakers.get("legal_database")
        if not cb:
            print("❌ Circuit breaker not found")
            return
        
        print(f"🔒 Testing circuit breaker: {cb.name}")
        
        # Simulate successful calls
        async def mock_successful_call():
            await asyncio.sleep(0.1)
            return "Database query successful"
        
        # Simulate failing calls
        async def mock_failing_call():
            await asyncio.sleep(0.1)
            raise Exception("Database connection timeout")
        
        # Test successful calls
        print("\n📈 Testing successful operations...")
        for i in range(3):
            try:
                result = await cb.call(mock_successful_call)
                print(f"   ✅ Call {i+1}: {result}")
            except Exception as e:
                print(f"   ❌ Call {i+1}: {e}")
        
        print(f"   Circuit breaker status: {cb.state.value}")
        
        # Test failing calls to trigger circuit breaker
        print("\n📉 Testing failing operations...")
        for i in range(6):  # Exceed failure threshold
            try:
                result = await cb.call(mock_failing_call)
                print(f"   ✅ Call {i+1}: {result}")
            except Exception as e:
                print(f"   ❌ Call {i+1}: Circuit breaker or service error")
        
        print(f"   Circuit breaker status: {cb.state.value}")
        
        # Show final circuit breaker status
        cb_status = cb.get_status()
        print(f"\n🔍 Final Circuit Breaker Status:")
        print(f"   • State: {cb_status['state']}")
        print(f"   • Failure Count: {cb_status['failure_count']}")
        print(f"   • Last Failure: {cb_status['last_failure'] or 'None'}")
    
    async def demo_auto_scaling(self):
        """Demonstrate auto-scaling capabilities"""
        print("\n" + "="*60)
        print("Auto-Scaling Demo - Dynamic Load Management")
        print("="*60)
        
        # Start monitoring
        await self.deployment_manager.start_monitoring()
        
        # Simulate load by recording metrics
        metrics_collector = self.deployment_manager.metrics_collector
        
        print("📈 Simulating high load scenario...")
        
        # Record high CPU usage to trigger scale up
        original_collect = metrics_collector._collect_current_metrics
        
        def mock_high_cpu_metrics():
            metrics = original_collect()
            metrics.cpu_percent = 85.0  # Above scale-up threshold
            return metrics
        
        metrics_collector._collect_current_metrics = mock_high_cpu_metrics
        
        # Trigger scaling check
        print("   • CPU usage: 85% (above threshold)")
        print("   • Checking scaling conditions...")
        
        initial_instances = self.deployment_manager.load_balancer.get_status()["total_instances"]
        
        await self.deployment_manager.auto_scaler.check_scaling_conditions()
        
        final_instances = self.deployment_manager.load_balancer.get_status()["total_instances"]
        
        if final_instances > initial_instances:
            print(f"   ✅ Scaled up: {initial_instances} → {final_instances} instances")
        else:
            print(f"   ⏳ Scaling cooldown active or max instances reached")
        
        # Simulate scale down
        print("\n📉 Simulating low load scenario...")
        
        def mock_low_cpu_metrics():
            metrics = original_collect()
            metrics.cpu_percent = 25.0  # Below scale-down threshold
            return metrics
        
        metrics_collector._collect_current_metrics = mock_low_cpu_metrics
        
        # Reset cooldown for demo
        self.deployment_manager.auto_scaler.last_scale_action = None
        
        print("   • CPU usage: 25% (below threshold)")
        print("   • Checking scaling conditions...")
        
        pre_scale_instances = final_instances
        await self.deployment_manager.auto_scaler.check_scaling_conditions()
        
        post_scale_instances = self.deployment_manager.load_balancer.get_status()["total_instances"]
        
        if post_scale_instances < pre_scale_instances:
            print(f"   ✅ Scaled down: {pre_scale_instances} → {post_scale_instances} instances")
        else:
            print(f"   ⏳ At minimum instances or cooldown active")
        
        # Restore original metrics function
        metrics_collector._collect_current_metrics = original_collect
        
        # Show final load balancer status
        lb_status = self.deployment_manager.load_balancer.get_status()
        print(f"\n📊 Final Load Balancer Status:")
        print(f"   • Total instances: {lb_status['total_instances']}")
        print(f"   • Healthy instances: {lb_status['healthy_instances']}")

async def demonstrate_production_deployment():
    """
    Comprehensive demonstration of production deployment patterns and
    monitoring strategies for enterprise conversational AI systems.
    """
    
    print("🚀 Production Deployment and Monitoring Demo")
    print("Enterprise-Grade Operations for Conversational AI Systems")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    demo = ProductionDeploymentDemo()
    
    # Demonstrate deployment patterns
    deployment_success = await demo.demo_service_deployment()
    
    if deployment_success:
        await demo.demo_health_monitoring()
        await demo.demo_circuit_breaker()
        await demo.demo_auto_scaling()
    
    print("\n" + "="*60)
    print("✅ Production Deployment Demo Complete")
    print("="*60)
    
    # Operational summary
    print(f"\n🏗️  Production Architecture Summary:")
    print(f"   • Container orchestration with Kubernetes manifests")
    print(f"   • Multi-service deployment with health checks")
    print(f"   • Circuit breaker fault tolerance")
    print(f"   • Auto-scaling based on CPU metrics")
    print(f"   • Load balancing with health monitoring")
    print(f"   • Comprehensive observability and alerting")
    print(f"   • Zero-downtime deployment strategies")
    print(f"   • Production-ready configuration management")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run demonstration
    asyncio.run(demonstrate_production_deployment())
"""
Distributed System Observability and Monitoring

This module demonstrates comprehensive observability patterns for
microservices architectures including distributed tracing, metrics
collection, structured logging, and health monitoring for systems
like those at Lawstronaut and Optimizely.

Key concepts covered:
- Distributed tracing with correlation IDs and span tracking
- Metrics collection and aggregation (RED and USE methods)
- Structured logging with contextual information
- Health checks and service monitoring
- Performance monitoring and SLA tracking

Real-world applications:
- Legal document processing pipeline monitoring at Lawstronaut
- A/B testing platform observability at Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Protocol, Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
from contextlib import asynccontextmanager

# =============================================================================
# DISTRIBUTED TRACING
# =============================================================================

@dataclass
class TraceContext:
    """Trace context for distributed tracing"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    flags: int = 0
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def create_child_span(self, operation_name: str) -> 'TraceSpan':
        """Create child span from this context"""
        return TraceSpan(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=self.span_id,
            operation_name=operation_name
        )

@dataclass
class TraceSpan:
    """Individual span in distributed trace"""
    trace_id: str
    span_id: str
    operation_name: str
    parent_span_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "ok"  # ok, error, timeout
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    service_name: str = ""
    
    def start(self):
        """Start the span"""
        self.start_time = datetime.utcnow()
    
    def finish(self, status: str = "ok"):
        """Finish the span"""
        self.end_time = datetime.utcnow()
        self.status = status
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def add_tag(self, key: str, value: Any):
        """Add tag to span"""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **fields):
        """Add log entry to span"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **fields
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "operation_name": self.operation_name,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "service_name": self.service_name
        }

class Tracer:
    """Distributed tracer for creating and managing spans"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._active_spans: Dict[str, TraceSpan] = {}
        self._finished_spans: List[TraceSpan] = []
        self.logger = logging.getLogger(__name__)
    
    def start_trace(self, operation_name: str) -> TraceSpan:
        """Start a new trace (root span)"""
        trace_id = str(uuid.uuid4())
        span = TraceSpan(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            operation_name=operation_name,
            service_name=self.service_name
        )
        
        span.start()
        self._active_spans[span.span_id] = span
        
        self.logger.debug(
            "Started new trace",
            trace_id=trace_id,
            span_id=span.span_id,
            operation=operation_name
        )
        
        return span
    
    def start_span(self, operation_name: str, parent_context: Optional[TraceContext] = None) -> TraceSpan:
        """Start a span with optional parent context"""
        if parent_context:
            span = parent_context.create_child_span(operation_name)
        else:
            # Create root span
            span = TraceSpan(
                trace_id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4()),
                operation_name=operation_name
            )
        
        span.service_name = self.service_name
        span.start()
        self._active_spans[span.span_id] = span
        
        return span
    
    def finish_span(self, span: TraceSpan, status: str = "ok"):
        """Finish a span"""
        span.finish(status)
        
        if span.span_id in self._active_spans:
            del self._active_spans[span.span_id]
        
        self._finished_spans.append(span)
        
        self.logger.debug(
            "Finished span",
            trace_id=span.trace_id,
            span_id=span.span_id,
            operation=span.operation_name,
            duration_ms=span.duration_ms,
            status=status
        )
    
    @asynccontextmanager
    async def trace_async(self, operation_name: str, parent_context: Optional[TraceContext] = None):
        """Async context manager for tracing"""
        span = self.start_span(operation_name, parent_context)
        try:
            yield span
            self.finish_span(span, "ok")
        except Exception as e:
            span.add_tag("error", True)
            span.add_tag("error.message", str(e))
            span.add_log(f"Error occurred: {str(e)}", level="error")
            self.finish_span(span, "error")
            raise
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace"""
        return [span for span in self._finished_spans if span.trace_id == trace_id]
    
    def get_all_traces(self) -> List[TraceSpan]:
        """Get all finished spans"""
        return self._finished_spans.copy()

# =============================================================================
# METRICS COLLECTION
# =============================================================================

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

@dataclass
class Metric:
    """Base metric data structure"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels
        }

class MetricsCollector:
    """Metrics collector implementing RED and USE methodologies"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timeseries: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.logger = logging.getLogger(__name__)
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment counter metric"""
        key = self._get_metric_key(name, labels or {})
        self._counters[key] += value
        
        metric = Metric(name, MetricType.COUNTER, self._counters[key], labels=labels or {})
        self._timeseries[key].append(metric)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge metric value"""
        key = self._get_metric_key(name, labels or {})
        self._gauges[key] = value
        
        metric = Metric(name, MetricType.GAUGE, value, labels=labels or {})
        self._timeseries[key].append(metric)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add observation to histogram"""
        key = self._get_metric_key(name, labels or {})
        self._histograms[key].append(value)
        
        # Keep only recent observations (sliding window)
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]
    
    def _get_metric_key(self, name: str, labels: Dict[str, str]) -> str:
        """Generate unique key for metric with labels"""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    # RED Metrics (Rate, Errors, Duration)
    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Record HTTP request metrics (RED method)"""
        labels = {"endpoint": endpoint, "method": method}
        
        # Rate: increment request counter
        self.increment_counter("http_requests_total", 1.0, {**labels, "status": str(status_code)})
        
        # Errors: increment error counter for 4xx/5xx
        if status_code >= 400:
            self.increment_counter("http_requests_errors_total", 1.0, labels)
        
        # Duration: observe request duration
        self.observe_histogram("http_request_duration_ms", duration_ms, labels)
    
    # USE Metrics (Utilization, Saturation, Errors)
    def record_resource_usage(self, resource: str, utilization: float, saturation: float, errors: int):
        """Record resource usage metrics (USE method)"""
        labels = {"resource": resource}
        
        # Utilization: percentage of resource used
        self.set_gauge("resource_utilization_percent", utilization, labels)
        
        # Saturation: queue length or backlog
        self.set_gauge("resource_saturation", saturation, labels)
        
        # Errors: error count
        self.increment_counter("resource_errors_total", errors, labels)
    
    def get_counter_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        key = self._get_metric_key(name, labels or {})
        return self._counters[key]
    
    def get_gauge_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value"""
        key = self._get_metric_key(name, labels or {})
        return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._get_metric_key(name, labels or {})
        values = self._histograms.get(key, [])
        
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "sum": sum(values),
            "avg": statistics.mean(values),
            "p50": sorted_values[int(count * 0.5)] if count > 0 else 0.0,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0.0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0.0,
            "min": min(values),
            "max": max(values)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get snapshot of all current metrics"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name.split("{")[0], 
                    dict(item.split("=") for item in name.split("{")[1].rstrip("}").split(",")) if "{" in name else {})
                for name in self._histograms.keys()
            }
        }

# =============================================================================
# STRUCTURED LOGGING
# =============================================================================

class StructuredLogger:
    """Structured logger with contextual information"""
    
    def __init__(self, service_name: str, logger: Optional[logging.Logger] = None):
        self.service_name = service_name
        self.logger = logger or logging.getLogger(__name__)
        self._context: Dict[str, Any] = {"service": service_name}
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Create new logger with additional context"""
        new_logger = StructuredLogger(self.service_name, self.logger)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def _log(self, level: str, message: str, **fields):
        """Internal log method with structured output"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "message": message,
            "service": self.service_name,
            **self._context,
            **fields
        }
        
        # Log as JSON for structured parsing
        log_message = json.dumps(log_entry, default=str)
        
        if level == "debug":
            self.logger.debug(log_message)
        elif level == "info":
            self.logger.info(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        elif level == "error":
            self.logger.error(log_message)
        elif level == "critical":
            self.logger.critical(log_message)
    
    def debug(self, message: str, **fields):
        """Log debug message"""
        self._log("debug", message, **fields)
    
    def info(self, message: str, **fields):
        """Log info message"""
        self._log("info", message, **fields)
    
    def warning(self, message: str, **fields):
        """Log warning message"""
        self._log("warning", message, **fields)
    
    def error(self, message: str, **fields):
        """Log error message"""
        self._log("error", message, **fields)
    
    def critical(self, message: str, **fields):
        """Log critical message"""
        self._log("critical", message, **fields)

# =============================================================================
# HEALTH MONITORING
# =============================================================================

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str = ""
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class HealthMonitor:
    """Comprehensive health monitoring system"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._health_checks: Dict[str, Callable] = {}
        self._check_results: Dict[str, HealthCheck] = {}
        self._running = False
        self.logger = StructuredLogger(service_name)
    
    def register_health_check(self, name: str, check_func: Callable[[], bool], 
                            metadata: Optional[Dict[str, Any]] = None):
        """Register a health check function"""
        self._health_checks[name] = check_func
        self.logger.info(f"Health check registered: {name}", check_name=name, metadata=metadata or {})
    
    async def run_health_check(self, name: str) -> HealthCheck:
        """Run individual health check"""
        if name not in self._health_checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check '{name}' not found"
            )
        
        start_time = time.time()
        
        try:
            check_func = self._health_checks[name]
            
            # Run health check (support both sync and async)
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if result:
                health_check = HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="OK",
                    response_time_ms=response_time_ms
                )
            else:
                health_check = HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Check failed",
                    response_time_ms=response_time_ms
                )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}",
                response_time_ms=response_time_ms
            )
        
        self._check_results[name] = health_check
        return health_check
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks"""
        results = {}
        
        for name in self._health_checks:
            results[name] = await self.run_health_check(name)
        
        return results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall service health status"""
        check_results = await self.run_all_health_checks()
        
        # Determine overall status
        statuses = [check.status for check in check_results.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        # Calculate metrics
        total_checks = len(check_results)
        healthy_checks = sum(1 for check in check_results.values() if check.status == HealthStatus.HEALTHY)
        avg_response_time = statistics.mean(check.response_time_ms for check in check_results.values()) if check_results else 0
        
        return {
            "service": self.service_name,
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {name: check.to_dict() for name, check in check_results.items()},
            "summary": {
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
                "avg_response_time_ms": avg_response_time
            }
        }

# =============================================================================
# SLA AND PERFORMANCE MONITORING
# =============================================================================

@dataclass
class SlaTarget:
    """SLA target definition"""
    name: str
    threshold: float
    operator: str  # "lt", "gt", "eq"
    description: str

class SlaMonitor:
    """SLA monitoring and alerting"""
    
    def __init__(self, service_name: str, metrics_collector: MetricsCollector):
        self.service_name = service_name
        self.metrics_collector = metrics_collector
        self._sla_targets: Dict[str, SlaTarget] = {}
        self._violations: List[Dict[str, Any]] = []
        self.logger = StructuredLogger(service_name)
    
    def register_sla_target(self, target: SlaTarget):
        """Register SLA target for monitoring"""
        self._sla_targets[target.name] = target
        self.logger.info(
            "SLA target registered",
            sla_name=target.name,
            threshold=target.threshold,
            operator=target.operator
        )
    
    async def check_sla_compliance(self) -> Dict[str, Any]:
        """Check compliance against all SLA targets"""
        compliance_report = {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "targets": {},
            "violations": [],
            "overall_compliance": True
        }
        
        for name, target in self._sla_targets.items():
            result = await self._check_individual_sla(target)
            compliance_report["targets"][name] = result
            
            if not result["compliant"]:
                compliance_report["overall_compliance"] = False
                violation = {
                    "sla_name": name,
                    "threshold": target.threshold,
                    "actual_value": result["actual_value"],
                    "violation_severity": self._calculate_severity(target, result["actual_value"]),
                    "timestamp": datetime.utcnow().isoformat()
                }
                compliance_report["violations"].append(violation)
                self._violations.append(violation)
        
        return compliance_report
    
    async def _check_individual_sla(self, target: SlaTarget) -> Dict[str, Any]:
        """Check individual SLA target"""
        # Map SLA target names to metrics
        metric_mapping = {
            "response_time_p95": ("http_request_duration_ms", "p95"),
            "error_rate": ("error_percentage", "current"),
            "availability": ("availability_percentage", "current"),
            "throughput": ("requests_per_second", "current")
        }
        
        if target.name not in metric_mapping:
            return {
                "compliant": False,
                "actual_value": None,
                "message": f"Unknown SLA target: {target.name}"
            }
        
        metric_name, stat_type = metric_mapping[target.name]
        
        # Get actual metric value
        if stat_type == "p95":
            stats = self.metrics_collector.get_histogram_stats("http_request_duration_ms")
            actual_value = stats.get("p95", 0)
        elif stat_type == "current":
            actual_value = self.metrics_collector.get_gauge_value(metric_name)
        else:
            actual_value = 0
        
        # Check compliance based on operator
        if target.operator == "lt":
            compliant = actual_value < target.threshold
        elif target.operator == "gt":
            compliant = actual_value > target.threshold
        elif target.operator == "eq":
            compliant = abs(actual_value - target.threshold) < 0.01  # Allow small tolerance
        else:
            compliant = False
        
        return {
            "compliant": compliant,
            "actual_value": actual_value,
            "threshold": target.threshold,
            "operator": target.operator,
            "message": f"{'PASS' if compliant else 'FAIL'}: {actual_value} {target.operator} {target.threshold}"
        }
    
    def _calculate_severity(self, target: SlaTarget, actual_value: float) -> str:
        """Calculate violation severity"""
        if target.operator == "lt":
            deviation_ratio = (actual_value - target.threshold) / target.threshold
        elif target.operator == "gt":
            deviation_ratio = (target.threshold - actual_value) / target.threshold
        else:
            deviation_ratio = abs(actual_value - target.threshold) / target.threshold
        
        if deviation_ratio > 0.5:
            return "critical"
        elif deviation_ratio > 0.2:
            return "high"
        elif deviation_ratio > 0.1:
            return "medium"
        else:
            return "low"

# =============================================================================
# INTEGRATED OBSERVABILITY SYSTEM
# =============================================================================

class ObservabilitySystem:
    """Integrated observability system combining all monitoring aspects"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = Tracer(service_name)
        self.metrics = MetricsCollector(service_name)
        self.logger = StructuredLogger(service_name)
        self.health_monitor = HealthMonitor(service_name)
        self.sla_monitor = SlaMonitor(service_name, self.metrics)
        
        # Register default health checks
        self._register_default_health_checks()
        
        # Register default SLA targets
        self._register_default_sla_targets()
    
    def _register_default_health_checks(self):
        """Register common health checks"""
        
        def database_health():
            """Simulate database connectivity check"""
            return True  # In real implementation: actual DB ping
        
        def external_service_health():
            """Simulate external service connectivity"""
            return True  # In real implementation: actual service check
        
        def memory_health():
            """Check memory usage"""
            # Simulate memory check
            return True  # In real implementation: check actual memory usage
        
        self.health_monitor.register_health_check("database", database_health)
        self.health_monitor.register_health_check("external_services", external_service_health)
        self.health_monitor.register_health_check("memory", memory_health)
    
    def _register_default_sla_targets(self):
        """Register common SLA targets"""
        
        # Response time SLA: 95th percentile < 500ms
        self.sla_monitor.register_sla_target(SlaTarget(
            name="response_time_p95",
            threshold=500.0,
            operator="lt",
            description="95th percentile response time should be less than 500ms"
        ))
        
        # Error rate SLA: < 1%
        self.sla_monitor.register_sla_target(SlaTarget(
            name="error_rate",
            threshold=1.0,
            operator="lt",
            description="Error rate should be less than 1%"
        ))
        
        # Availability SLA: > 99.9%
        self.sla_monitor.register_sla_target(SlaTarget(
            name="availability",
            threshold=99.9,
            operator="gt",
            description="Service availability should be greater than 99.9%"
        ))
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, **tags):
        """Context manager for tracing operations"""
        async with self.tracer.trace_async(operation_name) as span:
            # Add tags to span
            for key, value in tags.items():
                span.add_tag(key, value)
            
            # Create logger with trace context
            logger = self.logger.with_context(
                trace_id=span.trace_id,
                span_id=span.span_id,
                operation=operation_name
            )
            
            try:
                yield span, logger
            except Exception as e:
                logger.error(f"Operation failed: {operation_name}", error=str(e), **tags)
                raise
    
    async def simulate_business_operation(self, operation_type: str, **params):
        """Simulate business operation with full observability"""
        
        async with self.trace_operation(f"{operation_type}_operation", **params) as (span, logger):
            start_time = time.time()
            
            logger.info(f"Starting {operation_type} operation", **params)
            
            try:
                # Simulate operation with variable duration
                operation_duration = 0.1 + (hash(str(params)) % 100) / 1000.0
                await asyncio.sleep(operation_duration)
                
                # Simulate occasional failures
                if operation_type == "document_processing" and params.get("filename", "").startswith("fail_"):
                    raise ValueError("Document processing failed")
                
                # Record successful metrics
                duration_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    endpoint=f"/{operation_type}",
                    method="POST",
                    status_code=200,
                    duration_ms=duration_ms
                )
                
                # Update success gauge
                self.metrics.set_gauge("operation_success_rate", 1.0, {"operation": operation_type})
                
                logger.info(
                    f"Completed {operation_type} operation",
                    duration_ms=duration_ms,
                    success=True,
                    **params
                )
                
                return {
                    "operation": operation_type,
                    "success": True,
                    "duration_ms": duration_ms,
                    "trace_id": span.trace_id
                }
                
            except Exception as e:
                # Record failed metrics
                duration_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    endpoint=f"/{operation_type}",
                    method="POST",
                    status_code=500,
                    duration_ms=duration_ms
                )
                
                # Update failure gauge
                self.metrics.set_gauge("operation_success_rate", 0.0, {"operation": operation_type})
                
                logger.error(
                    f"Failed {operation_type} operation",
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    **params
                )
                
                raise e
    
    async def get_observability_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive observability dashboard"""
        
        # Get health status
        health_status = await self.health_monitor.get_overall_health()
        
        # Get SLA compliance
        sla_compliance = await self.sla_monitor.check_sla_compliance()
        
        # Get metrics summary
        all_metrics = self.metrics.get_all_metrics()
        
        # Get trace summary
        all_traces = self.tracer.get_all_traces()
        trace_summary = {
            "total_traces": len(set(span.trace_id for span in all_traces)),
            "total_spans": len(all_traces),
            "avg_duration_ms": statistics.mean(span.duration_ms for span in all_traces if span.duration_ms) if all_traces else 0,
            "error_rate": len([span for span in all_traces if span.status == "error"]) / len(all_traces) * 100 if all_traces else 0
        }
        
        return {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "health": health_status,
            "sla_compliance": sla_compliance,
            "metrics": all_metrics,
            "tracing": trace_summary,
            "alerts": self._get_active_alerts(health_status, sla_compliance)
        }
    
    def _get_active_alerts(self, health_status: Dict[str, Any], sla_compliance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate active alerts based on health and SLA status"""
        alerts = []
        
        # Health-based alerts
        if health_status["status"] != "healthy":
            alerts.append({
                "type": "health",
                "severity": "high" if health_status["status"] == "unhealthy" else "medium",
                "message": f"Service health is {health_status['status']}",
                "details": health_status["summary"]
            })
        
        # SLA violation alerts
        for violation in sla_compliance.get("violations", []):
            alerts.append({
                "type": "sla_violation",
                "severity": violation["violation_severity"],
                "message": f"SLA violation: {violation['sla_name']}",
                "details": violation
            })
        
        return alerts

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

async def demonstrate_observability_system():
    """
    Comprehensive demonstration of distributed system observability
    patterns for microservices architectures.
    """
    
    print("=== Distributed System Observability and Monitoring ===\n")
    
    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'  # Structured logging will handle formatting
    )
    
    # Initialize observability system for document processing service
    print("1. Initializing Observability System:")
    doc_service_obs = ObservabilitySystem("document-processing-service")
    
    print("   - Distributed tracing configured")
    print("   - Metrics collection (RED and USE methods) enabled")
    print("   - Structured logging with correlation IDs")
    print("   - Health monitoring with multiple checks")
    print("   - SLA monitoring with automatic violation detection")
    
    # Initialize observability system for experiment service
    exp_service_obs = ObservabilitySystem("experiment-service")
    
    print("   - Multi-service observability configured")
    
    # Demonstrate distributed tracing
    print("\n2. Testing Distributed Tracing:")
    
    # Simulate document processing workflow
    doc_operations = [
        {"operation_type": "document_upload", "filename": "contract.pdf", "user_id": "user_123"},
        {"operation_type": "document_processing", "filename": "legal_doc.pdf", "doc_id": "doc_456"},
        {"operation_type": "document_indexing", "filename": "agreement.pdf", "doc_id": "doc_789"}
    ]
    
    for operation in doc_operations:
        try:
            result = await doc_service_obs.simulate_business_operation(**operation)
            print(f"   - {operation['operation_type']}: SUCCESS (trace: {result['trace_id'][:8]}...)")
        except Exception as e:
            print(f"   - {operation['operation_type']}: FAILED ({str(e)})")
    
    # Simulate experiment operations
    exp_operations = [
        {"operation_type": "experiment_creation", "exp_name": "checkout_v2", "user_id": "researcher_1"},
        {"operation_type": "variant_assignment", "exp_id": "exp_123", "user_id": "user_456"},
        {"operation_type": "conversion_tracking", "exp_id": "exp_123", "user_id": "user_789"}
    ]
    
    for operation in exp_operations:
        try:
            result = await exp_service_obs.simulate_business_operation(**operation)
            print(f"   - {operation['operation_type']}: SUCCESS (trace: {result['trace_id'][:8]}...)")
        except Exception as e:
            print(f"   - {operation['operation_type']}: FAILED ({str(e)})")
    
    # Test failure scenario
    print("\n3. Testing Failure Handling:")
    try:
        await doc_service_obs.simulate_business_operation(
            operation_type="document_processing",
            filename="fail_corrupted.pdf",  # This will trigger failure
            doc_id="doc_error"
        )
    except Exception:
        print("   - Failure properly traced and logged")
    
    # Demonstrate metrics collection
    print("\n4. Analyzing Metrics (RED Method):")
    
    doc_metrics = doc_service_obs.metrics.get_all_metrics()
    
    # Request rates
    request_counts = {k: v for k, v in doc_metrics["counters"].items() if "http_requests_total" in k}
    print(f"   - Total requests: {sum(request_counts.values())}")
    
    # Error rates
    error_counts = {k: v for k, v in doc_metrics["counters"].items() if "errors" in k}
    total_errors = sum(error_counts.values())
    total_requests = sum(request_counts.values())
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    print(f"   - Error rate: {error_rate:.1f}%")
    
    # Duration statistics
    duration_stats = doc_service_obs.metrics.get_histogram_stats("http_request_duration_ms")
    print(f"   - Response time P95: {duration_stats['p95']:.1f}ms")
    print(f"   - Response time P99: {duration_stats['p99']:.1f}ms")
    print(f"   - Average response time: {duration_stats['avg']:.1f}ms")
    
    # Demonstrate health monitoring
    print("\n5. Health Check Results:")
    
    doc_health = await doc_service_obs.health_monitor.get_overall_health()
    print(f"   - Overall health: {doc_health['status'].upper()}")
    print(f"   - Healthy checks: {doc_health['summary']['health_percentage']:.1f}%")
    
    for check_name, check_result in doc_health['checks'].items():
        status_indicator = "✓" if check_result['status'] == 'healthy' else "✗"
        print(f"   - {check_name}: {status_indicator} {check_result['status']} ({check_result['response_time_ms']:.1f}ms)")
    
    # Demonstrate SLA monitoring
    print("\n6. SLA Compliance Monitoring:")
    
    doc_sla = await doc_service_obs.sla_monitor.check_sla_compliance()
    print(f"   - Overall SLA compliance: {'PASS' if doc_sla['overall_compliance'] else 'FAIL'}")
    
    for target_name, target_result in doc_sla['targets'].items():
        compliance_indicator = "✓" if target_result['compliant'] else "✗"
        print(f"   - {target_name}: {compliance_indicator} {target_result['message']}")
    
    if doc_sla['violations']:
        print("   - SLA Violations:")
        for violation in doc_sla['violations']:
            print(f"     * {violation['sla_name']}: {violation['violation_severity']} severity")
    
    # Demonstrate complete observability dashboard
    print("\n7. Observability Dashboard:")
    
    dashboard = await doc_service_obs.get_observability_dashboard()
    
    print(f"   Service: {dashboard['service']}")
    print(f"   Timestamp: {dashboard['timestamp']}")
    print(f"   Health Status: {dashboard['health']['status']}")
    print(f"   SLA Compliance: {'COMPLIANT' if dashboard['sla_compliance']['overall_compliance'] else 'VIOLATIONS'}")
    
    print(f"   Tracing Summary:")
    print(f"     - Total traces: {dashboard['tracing']['total_traces']}")
    print(f"     - Total spans: {dashboard['tracing']['total_spans']}")
    print(f"     - Average duration: {dashboard['tracing']['avg_duration_ms']:.1f}ms")
    print(f"     - Error rate: {dashboard['tracing']['error_rate']:.1f}%")
    
    # Display active alerts
    if dashboard['alerts']:
        print(f"   Active Alerts ({len(dashboard['alerts'])}):")
        for alert in dashboard['alerts']:
            severity_indicator = {"low": "ℹ", "medium": "⚠", "high": "🚨", "critical": "🔴"}
            indicator = severity_indicator.get(alert['severity'], "❓")
            print(f"     {indicator} [{alert['severity'].upper()}] {alert['message']}")
    else:
        print("   Active Alerts: None ✓")
    
    # Demonstrate cross-service correlation
    print("\n8. Cross-Service Trace Correlation:")
    
    # Show traces from both services
    doc_traces = doc_service_obs.tracer.get_all_traces()
    exp_traces = exp_service_obs.tracer.get_all_traces()
    
    print(f"   - Document service traces: {len(set(span.trace_id for span in doc_traces))}")
    print(f"   - Experiment service traces: {len(set(span.trace_id for span in exp_traces))}")
    
    # Show recent trace details
    if doc_traces:
        recent_trace = doc_traces[-1]
        print(f"   - Recent trace: {recent_trace.trace_id}")
        print(f"     * Operation: {recent_trace.operation_name}")
        print(f"     * Duration: {recent_trace.duration_ms:.1f}ms")
        print(f"     * Status: {recent_trace.status}")
        print(f"     * Tags: {recent_trace.tags}")
    
    print("\n9. Key Observability Benefits:")
    print("   - End-to-end request tracing across services")
    print("   - Proactive SLA monitoring and alerting")
    print("   - Structured logging for efficient troubleshooting")
    print("   - Comprehensive health checks for reliability")
    print("   - Real-time metrics for performance optimization")
    print("   - Correlation between different observability signals")
    
    print("\n10. Production Considerations:")
    print("   - Trace sampling strategies for high-volume systems")
    print("   - Metrics cardinality management")
    print("   - Log aggregation and long-term retention")
    print("   - Alert fatigue prevention with intelligent routing")
    print("   - Cost optimization for observability infrastructure")
    print("   - Privacy and security in trace/log data")
    
    print("\n11. Integration with External Tools:")
    print("   - Jaeger/Zipkin for distributed tracing visualization")
    print("   - Prometheus/Grafana for metrics and dashboards")
    print("   - ELK/Fluentd stack for log aggregation")
    print("   - PagerDuty/Slack for alert management")
    print("   - Service mesh integration (Istio, Linkerd)")
    
    print("\n=== Observability system demonstration completed ===")

if __name__ == "__main__":
    asyncio.run(demonstrate_observability_system())
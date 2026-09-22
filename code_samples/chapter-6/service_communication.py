"""
Service Communication Patterns for Microservices

This module demonstrates comprehensive service communication patterns
used in distributed microservices architectures like those at 
Lawstronaut (legal document processing) and Optimizely (experimentation).

Key concepts covered:
- Synchronous communication with REST APIs and circuit breakers
- Asynchronous communication with event-driven messaging
- Service discovery and load balancing strategies
- API versioning and backward compatibility
- Retry mechanisms and timeout handling

Real-world applications:
- Inter-service communication in legal document workflows
- Experiment service coordination at Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Protocol, Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import json
import uuid
import time
import random
from datetime import datetime, timedelta
import logging
import hashlib
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# =============================================================================
# SERVICE DISCOVERY AND REGISTRY
# =============================================================================

@dataclass
class ServiceInstance:
    """Service instance registration information"""
    service_id: str
    service_name: str
    host: str
    port: int
    protocol: str = "http"
    health_check_url: str = "/health"
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def base_url(self) -> str:
        """Get base URL for service instance"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if instance is considered healthy based on heartbeat"""
        heartbeat_timeout = timedelta(seconds=30)
        return datetime.utcnow() - self.last_heartbeat < heartbeat_timeout

class ServiceRegistry(Protocol):
    """Service registry interface for service discovery"""
    
    async def register_service(self, instance: ServiceInstance) -> None:
        """Register service instance"""
        ...
    
    async def deregister_service(self, service_id: str) -> None:
        """Deregister service instance"""
        ...
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover healthy instances of a service"""
        ...
    
    async def heartbeat(self, service_id: str) -> None:
        """Send heartbeat to keep service registration alive"""
        ...

class InMemoryServiceRegistry:
    """In-memory service registry implementation"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInstance] = {}
        self._service_names: Dict[str, List[str]] = {}  # service_name -> [service_ids]
        self.logger = logging.getLogger(__name__)
    
    async def register_service(self, instance: ServiceInstance) -> None:
        """Register service instance"""
        self._services[instance.service_id] = instance
        
        if instance.service_name not in self._service_names:
            self._service_names[instance.service_name] = []
        
        if instance.service_id not in self._service_names[instance.service_name]:
            self._service_names[instance.service_name].append(instance.service_id)
        
        self.logger.info(
            "Service registered",
            service_id=instance.service_id,
            service_name=instance.service_name,
            base_url=instance.base_url
        )
    
    async def deregister_service(self, service_id: str) -> None:
        """Deregister service instance"""
        if service_id in self._services:
            instance = self._services.pop(service_id)
            
            if instance.service_name in self._service_names:
                self._service_names[instance.service_name] = [
                    sid for sid in self._service_names[instance.service_name]
                    if sid != service_id
                ]
            
            self.logger.info(
                "Service deregistered",
                service_id=service_id,
                service_name=instance.service_name
            )
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover healthy instances of a service"""
        service_ids = self._service_names.get(service_name, [])
        instances = []
        
        for service_id in service_ids:
            if service_id in self._services:
                instance = self._services[service_id]
                if instance.is_healthy:
                    instances.append(instance)
                else:
                    # Remove unhealthy instances
                    await self.deregister_service(service_id)
        
        return instances
    
    async def heartbeat(self, service_id: str) -> None:
        """Update heartbeat timestamp"""
        if service_id in self._services:
            self._services[service_id].last_heartbeat = datetime.utcnow()

# =============================================================================
# LOAD BALANCING STRATEGIES
# =============================================================================

class LoadBalancer(ABC):
    """Abstract load balancer for distributing requests"""
    
    @abstractmethod
    async def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select instance for request routing"""
        ...

class RoundRobinLoadBalancer:
    """Round-robin load balancing strategy"""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
    
    async def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select next instance in round-robin fashion"""
        if not instances:
            return None
        
        # Use service name as key for counter
        service_name = instances[0].service_name
        counter = self._counters.get(service_name, 0)
        
        selected = instances[counter % len(instances)]
        self._counters[service_name] = counter + 1
        
        return selected

class WeightedRandomLoadBalancer:
    """Weighted random load balancing with health consideration"""
    
    async def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select instance using weighted random selection"""
        if not instances:
            return None
        
        # Weight based on inverse of response time (simulated)
        weights = []
        for instance in instances:
            # Simulate response time based on metadata
            response_time = instance.metadata.get("avg_response_time", 100)
            weight = max(1, 1000 // response_time)  # Lower response time = higher weight
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        random_value = random.randint(1, total_weight)
        
        cumulative_weight = 0
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return instances[i]
        
        return instances[0]  # Fallback

class LeastConnectionsLoadBalancer:
    """Load balancer that routes to instance with fewest active connections"""
    
    def __init__(self):
        self._active_connections: Dict[str, int] = {}
    
    async def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select instance with least connections"""
        if not instances:
            return None
        
        min_connections = float('inf')
        selected_instance = None
        
        for instance in instances:
            connections = self._active_connections.get(instance.service_id, 0)
            if connections < min_connections:
                min_connections = connections
                selected_instance = instance
        
        return selected_instance
    
    def increment_connections(self, service_id: str):
        """Increment connection count for service instance"""
        self._active_connections[service_id] = self._active_connections.get(service_id, 0) + 1
    
    def decrement_connections(self, service_id: str):
        """Decrement connection count for service instance"""
        if service_id in self._active_connections:
            self._active_connections[service_id] = max(0, self._active_connections[service_id] - 1)

# =============================================================================
# CIRCUIT BREAKER PATTERN
# =============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60
    request_volume_threshold: int = 10

class CircuitBreaker:
    """Circuit breaker for resilient service communication"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.request_count = 0
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker transitioning to half-open", name=self.name)
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"Circuit breaker {self.name} is OPEN"
                )
        
        try:
            self.request_count += 1
            
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure()
            raise e
    
    async def _on_success(self):
        """Handle successful request"""
        self.failure_count = 0
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0
                self.logger.info("Circuit breaker closed after successful recovery", name=self.name)
    
    async def _on_failure(self):
        """Handle failed request"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning("Circuit breaker opened from half-open state", name=self.name)
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.request_count >= self.config.request_volume_threshold and
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                "Circuit breaker opened due to failure threshold",
                name=self.name,
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if not self.last_failure_time:
            return True
        
        timeout_exceeded = (
            datetime.utcnow() - self.last_failure_time >
            timedelta(seconds=self.config.timeout_seconds)
        )
        
        return timeout_exceeded
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "request_count": self.request_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

# =============================================================================
# RESILIENT HTTP CLIENT
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

class ResilientHttpClient:
    """HTTP client with circuit breaker, retry, and load balancing"""
    
    def __init__(self, service_registry: ServiceRegistry, 
                 load_balancer: LoadBalancer, timeout: float = 10.0):
        self.service_registry = service_registry
        self.load_balancer = load_balancer
        self.timeout = timeout
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self.logger = logging.getLogger(__name__)
    
    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self._circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=60
            )
            self._circuit_breakers[service_name] = CircuitBreaker(
                name=f"cb_{service_name}",
                config=config
            )
        return self._circuit_breakers[service_name]
    
    async def request(self, service_name: str, method: str, path: str,
                     data: Optional[Dict[str, Any]] = None,
                     retry_config: Optional[RetryConfig] = None) -> Dict[str, Any]:
        """Make resilient HTTP request to service"""
        if retry_config is None:
            retry_config = RetryConfig()
        
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                # Discover service instances
                instances = await self.service_registry.discover_services(service_name)
                if not instances:
                    raise HTTPException(
                        status_code=503,
                        detail=f"No healthy instances found for service: {service_name}"
                    )
                
                # Select instance using load balancer
                instance = await self.load_balancer.select_instance(instances)
                if not instance:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Load balancer failed to select instance for: {service_name}"
                    )
                
                # Make request with circuit breaker protection
                circuit_breaker = self._get_circuit_breaker(service_name)
                
                response = await circuit_breaker.call(
                    self._make_http_request,
                    instance,
                    method,
                    path,
                    data
                )
                
                self.logger.info(
                    "Service request successful",
                    service_name=service_name,
                    instance_id=instance.service_id,
                    method=method,
                    path=path,
                    attempt=attempt + 1
                )
                
                return response
                
            except Exception as e:
                last_exception = e
                
                # Don't retry on client errors (4xx)
                if hasattr(e, 'status_code') and 400 <= e.status_code < 500:
                    raise e
                
                if attempt < retry_config.max_retries:
                    # Calculate retry delay with exponential backoff
                    delay = min(
                        retry_config.base_delay * (retry_config.exponential_base ** attempt),
                        retry_config.max_delay
                    )
                    
                    self.logger.warning(
                        "Service request failed, retrying",
                        service_name=service_name,
                        method=method,
                        path=path,
                        attempt=attempt + 1,
                        delay_seconds=delay,
                        error=str(e)
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        "Service request failed after all retries",
                        service_name=service_name,
                        method=method,
                        path=path,
                        max_retries=retry_config.max_retries,
                        error=str(e)
                    )
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            raise HTTPException(status_code=503, detail="Service request failed")
    
    async def _make_http_request(self, instance: ServiceInstance, method: str,
                               path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make actual HTTP request to service instance"""
        url = urljoin(instance.base_url, path)
        
        request_kwargs = {
            "method": method,
            "url": url,
            "headers": {"Content-Type": "application/json"}
        }
        
        if data:
            request_kwargs["json"] = data
        
        # Simulate HTTP request
        start_time = time.time()
        
        # Simulate network latency and occasional failures
        await asyncio.sleep(0.05 + random.random() * 0.1)  # 50-150ms latency
        
        # Simulate service failures (5% chance)
        if random.random() < 0.05:
            raise httpx.RequestError("Simulated network error")
        
        # Simulate HTTP errors (3% chance)
        if random.random() < 0.03:
            raise HTTPException(status_code=500, detail="Internal service error")
        
        response_time = (time.time() - start_time) * 1000
        
        # Update instance metadata with response time
        instance.metadata["avg_response_time"] = (
            instance.metadata.get("avg_response_time", response_time) * 0.8 +
            response_time * 0.2  # Exponential moving average
        )
        
        # Simulate successful response
        return {
            "status": "success",
            "data": {"message": f"Response from {instance.service_id}"},
            "response_time_ms": response_time,
            "instance_id": instance.service_id
        }
    
    async def get(self, service_name: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return await self.request(service_name, "GET", path, **kwargs)
    
    async def post(self, service_name: str, path: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        return await self.request(service_name, "POST", path, data, **kwargs)
    
    async def put(self, service_name: str, path: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make PUT request"""
        return await self.request(service_name, "PUT", path, data, **kwargs)
    
    async def delete(self, service_name: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self.request(service_name, "DELETE", path, **kwargs)
    
    def get_circuit_breaker_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        return {
            name: cb.get_metrics()
            for name, cb in self._circuit_breakers.items()
        }
    
    async def close(self):
        """Close HTTP client"""
        await self._http_client.aclose()

# =============================================================================
# API VERSIONING AND COMPATIBILITY
# =============================================================================

class ApiVersion(str, Enum):
    """API version enumeration"""
    V1 = "v1"
    V2 = "v2"
    V3 = "v3"

@dataclass
class ApiEndpoint:
    """API endpoint definition with versioning"""
    path: str
    method: str
    version: ApiVersion
    deprecated: bool = False
    sunset_date: Optional[datetime] = None
    
    def get_versioned_path(self) -> str:
        """Get path with version prefix"""
        return f"/{self.version.value}{self.path}"

class VersionedApiClient:
    """HTTP client with API versioning support"""
    
    def __init__(self, http_client: ResilientHttpClient, 
                 preferred_version: ApiVersion = ApiVersion.V2):
        self.http_client = http_client
        self.preferred_version = preferred_version
        self.logger = logging.getLogger(__name__)
    
    async def call_api(self, service_name: str, endpoint: ApiEndpoint,
                      data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call API endpoint with version handling"""
        
        # Check for deprecation warnings
        if endpoint.deprecated:
            self.logger.warning(
                "Using deprecated API endpoint",
                service=service_name,
                endpoint=endpoint.path,
                version=endpoint.version.value,
                sunset_date=endpoint.sunset_date.isoformat() if endpoint.sunset_date else None
            )
        
        # Add version to request headers
        versioned_path = endpoint.get_versioned_path()
        
        try:
            response = await self.http_client.request(
                service_name=service_name,
                method=endpoint.method,
                path=versioned_path,
                data=data
            )
            
            return response
            
        except HTTPException as e:
            if e.status_code == 404 and endpoint.version != ApiVersion.V1:
                # Try fallback to previous version
                self.logger.warning(
                    "API version not found, trying fallback",
                    service=service_name,
                    requested_version=endpoint.version.value,
                    fallback_version=ApiVersion.V1.value
                )
                
                fallback_endpoint = ApiEndpoint(
                    path=endpoint.path,
                    method=endpoint.method,
                    version=ApiVersion.V1
                )
                
                return await self.call_api(service_name, fallback_endpoint, data)
            
            raise e

# =============================================================================
# EVENT-DRIVEN SERVICE COMMUNICATION
# =============================================================================

@dataclass
class ServiceEvent:
    """Event for inter-service communication"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source_service: str = ""
    target_service: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_service": self.source_service,
            "target_service": self.target_service,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "payload": self.payload
        }

class EventBus:
    """Simple event bus for service communication"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_log: List[ServiceEvent] = []
        self.logger = logging.getLogger(__name__)
    
    async def publish(self, event: ServiceEvent) -> None:
        """Publish event to subscribers"""
        self._event_log.append(event)
        
        # Notify subscribers
        subscribers = self._subscribers.get(event.event_type, [])
        
        for subscriber in subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                self.logger.error(
                    "Event subscriber failed",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    subscriber=subscriber.__name__,
                    error=str(e)
                )
        
        self.logger.info(
            "Event published",
            event_id=event.event_id,
            event_type=event.event_type,
            source_service=event.source_service,
            subscriber_count=len(subscribers)
        )
    
    def subscribe(self, event_type: str, handler: Callable[[ServiceEvent], None]) -> None:
        """Subscribe to event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        
        self.logger.info(
            "Subscribed to event type",
            event_type=event_type,
            handler=handler.__name__
        )
    
    def get_event_log(self, event_type: Optional[str] = None) -> List[ServiceEvent]:
        """Get event log, optionally filtered by type"""
        if event_type:
            return [e for e in self._event_log if e.event_type == event_type]
        return self._event_log.copy()

# =============================================================================
# BUSINESS SERVICE IMPLEMENTATIONS
# =============================================================================

class DocumentProcessingService:
    """Document processing service (Lawstronaut scenario)"""
    
    def __init__(self, service_id: str, http_client: ResilientHttpClient,
                 event_bus: EventBus):
        self.service_id = service_id
        self.http_client = http_client
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
    
    async def process_document(self, document_id: str, filename: str) -> Dict[str, Any]:
        """Process document with dependent service calls"""
        correlation_id = str(uuid.uuid4())
        
        try:
            # Step 1: Validate document format (synchronous call)
            validation_result = await self.http_client.post(
                "validation-service",
                "/validate",
                {
                    "document_id": document_id,
                    "filename": filename
                }
            )
            
            if not validation_result["data"]["valid"]:
                raise ValueError("Document validation failed")
            
            # Step 2: Extract text content (synchronous call)
            extraction_result = await self.http_client.post(
                "extraction-service",
                "/extract",
                {
                    "document_id": document_id,
                    "format": "pdf"
                }
            )
            
            extracted_text = extraction_result["data"]["text"]
            
            # Step 3: Classify document (synchronous call)
            classification_result = await self.http_client.post(
                "classification-service",
                "/classify",
                {
                    "text": extracted_text,
                    "context": "legal"
                }
            )
            
            classification = classification_result["data"]["classification"]
            
            # Step 4: Publish processing completed event (asynchronous)
            event = ServiceEvent(
                event_type="document_processed",
                source_service=self.service_id,
                correlation_id=correlation_id,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "classification": classification,
                    "text_length": len(extracted_text)
                }
            )
            
            await self.event_bus.publish(event)
            
            return {
                "document_id": document_id,
                "status": "processed",
                "classification": classification,
                "text_length": len(extracted_text),
                "correlation_id": correlation_id
            }
            
        except Exception as e:
            # Publish failure event
            error_event = ServiceEvent(
                event_type="document_processing_failed",
                source_service=self.service_id,
                correlation_id=correlation_id,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "error": str(e)
                }
            )
            
            await self.event_bus.publish(error_event)
            raise e

class ExperimentService:
    """Experiment management service (Optimizely scenario)"""
    
    def __init__(self, service_id: str, http_client: ResilientHttpClient,
                 event_bus: EventBus):
        self.service_id = service_id
        self.http_client = http_client
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
    
    async def assign_variant(self, experiment_id: str, user_id: str) -> Dict[str, Any]:
        """Assign user to experiment variant"""
        correlation_id = str(uuid.uuid4())
        
        try:
            # Get experiment configuration
            experiment_result = await self.http_client.get(
                "config-service",
                f"/experiments/{experiment_id}"
            )
            
            experiment_config = experiment_result["data"]
            
            # Get user profile for targeting
            user_result = await self.http_client.get(
                "user-service",
                f"/users/{user_id}/profile"
            )
            
            user_profile = user_result["data"]
            
            # Assign variant based on traffic allocation
            variant = self._assign_variant_logic(experiment_config, user_profile)
            
            # Record assignment (synchronous call)
            assignment_result = await self.http_client.post(
                "analytics-service",
                "/assignments",
                {
                    "experiment_id": experiment_id,
                    "user_id": user_id,
                    "variant": variant,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Publish assignment event (asynchronous)
            event = ServiceEvent(
                event_type="variant_assigned",
                source_service=self.service_id,
                correlation_id=correlation_id,
                payload={
                    "experiment_id": experiment_id,
                    "user_id": user_id,
                    "variant": variant,
                    "assignment_id": assignment_result["data"]["assignment_id"]
                }
            )
            
            await self.event_bus.publish(event)
            
            return {
                "experiment_id": experiment_id,
                "user_id": user_id,
                "variant": variant,
                "correlation_id": correlation_id
            }
            
        except Exception as e:
            self.logger.error(
                "Variant assignment failed",
                experiment_id=experiment_id,
                user_id=user_id,
                error=str(e)
            )
            raise e
    
    def _assign_variant_logic(self, experiment_config: Dict[str, Any], 
                            user_profile: Dict[str, Any]) -> str:
        """Simple variant assignment logic"""
        variants = experiment_config.get("variants", ["control", "treatment"])
        traffic_allocation = experiment_config.get("traffic_allocation", {"control": 0.5, "treatment": 0.5})
        
        # Simple hash-based assignment for consistency
        user_hash = int(hashlib.md5(user_profile["user_id"].encode()).hexdigest(), 16)
        assignment_ratio = (user_hash % 100) / 100.0
        
        cumulative_allocation = 0.0
        for variant, allocation in traffic_allocation.items():
            cumulative_allocation += allocation
            if assignment_ratio <= cumulative_allocation:
                return variant
        
        return variants[0]  # Fallback

# =============================================================================
# INTEGRATION AND DEMONSTRATION
# =============================================================================

async def demonstrate_service_communication():
    """
    Comprehensive demonstration of service communication patterns
    including synchronous and asynchronous communication strategies.
    """
    
    print("=== Service Communication Patterns for Microservices ===\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize service registry
    print("1. Initializing Service Registry:")
    service_registry = InMemoryServiceRegistry()
    
    # Register mock service instances
    services = [
        ServiceInstance("validation-1", "validation-service", "localhost", 8001),
        ServiceInstance("validation-2", "validation-service", "localhost", 8002),
        ServiceInstance("extraction-1", "extraction-service", "localhost", 8003),
        ServiceInstance("classification-1", "classification-service", "localhost", 8004),
        ServiceInstance("config-1", "config-service", "localhost", 8005),
        ServiceInstance("user-1", "user-service", "localhost", 8006),
        ServiceInstance("analytics-1", "analytics-service", "localhost", 8007)
    ]
    
    for service in services:
        await service_registry.register_service(service)
        print(f"   - Registered: {service.service_name} at {service.base_url}")
    
    # Initialize load balancer and HTTP client
    print("\n2. Setting up Communication Infrastructure:")
    load_balancer = RoundRobinLoadBalancer()
    http_client = ResilientHttpClient(service_registry, load_balancer)
    
    print("   - Round-robin load balancer configured")
    print("   - Resilient HTTP client with circuit breakers")
    print("   - Retry mechanisms with exponential backoff")
    
    # Initialize event bus
    event_bus = EventBus()
    
    # Set up event handlers
    processed_events = []
    
    async def document_event_handler(event: ServiceEvent):
        processed_events.append(event)
        print(f"   - Processed event: {event.event_type} for {event.payload.get('document_id', 'N/A')}")
    
    async def experiment_event_handler(event: ServiceEvent):
        processed_events.append(event)
        print(f"   - Processed event: {event.event_type} for experiment {event.payload.get('experiment_id', 'N/A')}")
    
    event_bus.subscribe("document_processed", document_event_handler)
    event_bus.subscribe("document_processing_failed", document_event_handler)
    event_bus.subscribe("variant_assigned", experiment_event_handler)
    
    print("   - Event bus configured with subscribers")
    
    # Create business services
    print("\n3. Initializing Business Services:")
    
    document_service = DocumentProcessingService(
        "document-processor-1",
        http_client,
        event_bus
    )
    
    experiment_service = ExperimentService(
        "experiment-manager-1", 
        http_client,
        event_bus
    )
    
    print("   - Document processing service initialized")
    print("   - Experiment management service initialized")
    
    # Demonstrate synchronous communication with circuit breaker
    print("\n4. Testing Synchronous Service Communication:")
    
    try:
        result = await document_service.process_document(
            "legal_doc_123",
            "contract_agreement.pdf"
        )
        
        print(f"   - Document processed: {result['document_id']}")
        print(f"   - Classification: {result['classification']}")
        print(f"   - Correlation ID: {result['correlation_id']}")
        
    except Exception as e:
        print(f"   - Document processing failed: {str(e)}")
    
    # Demonstrate experiment service communication
    print("\n5. Testing Experiment Service Communication:")
    
    try:
        assignment = await experiment_service.assign_variant(
            "checkout_optimization_v2",
            "user_12345"
        )
        
        print(f"   - User assigned to variant: {assignment['variant']}")
        print(f"   - Experiment: {assignment['experiment_id']}")
        print(f"   - Correlation ID: {assignment['correlation_id']}")
        
    except Exception as e:
        print(f"   - Variant assignment failed: {str(e)}")
    
    # Test load balancing
    print("\n6. Testing Load Balancing:")
    
    validation_instances = await service_registry.discover_services("validation-service")
    print(f"   - Found {len(validation_instances)} validation service instances")
    
    selected_instances = []
    for i in range(6):  # Test round-robin over multiple requests
        instance = await load_balancer.select_instance(validation_instances)
        selected_instances.append(instance.service_id)
    
    print(f"   - Round-robin selection: {selected_instances}")
    
    # Test circuit breaker behavior
    print("\n7. Testing Circuit Breaker:")
    
    circuit_breaker_metrics = http_client.get_circuit_breaker_metrics()
    for service_name, metrics in circuit_breaker_metrics.items():
        print(f"   - {service_name}: state={metrics['state']}, requests={metrics['request_count']}")
    
    # Demonstrate API versioning
    print("\n8. Testing API Versioning:")
    
    versioned_client = VersionedApiClient(http_client, ApiVersion.V2)
    
    # Test current version endpoint
    endpoint_v2 = ApiEndpoint("/documents", "POST", ApiVersion.V2)
    
    try:
        response = await versioned_client.call_api(
            "validation-service",
            endpoint_v2,
            {"document_id": "test_doc", "format": "pdf"}
        )
        print(f"   - API v2 call successful: {response['status']}")
    except Exception as e:
        print(f"   - API v2 call failed: {str(e)}")
    
    # Test deprecated endpoint
    deprecated_endpoint = ApiEndpoint(
        "/legacy/validate", 
        "POST", 
        ApiVersion.V1, 
        deprecated=True,
        sunset_date=datetime.utcnow() + timedelta(days=90)
    )
    
    try:
        response = await versioned_client.call_api(
            "validation-service",
            deprecated_endpoint,
            {"document": "test"}
        )
        print(f"   - Deprecated API call successful: {response['status']}")
    except Exception as e:
        print(f"   - Deprecated API call failed: {str(e)}")
    
    # Analyze event processing
    print("\n9. Event Processing Results:")
    
    event_log = event_bus.get_event_log()
    print(f"   - Total events published: {len(event_log)}")
    print(f"   - Events processed by handlers: {len(processed_events)}")
    
    event_types = {}
    for event in event_log:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
    
    print("   - Event type breakdown:")
    for event_type, count in event_types.items():
        print(f"     * {event_type}: {count}")
    
    # Performance metrics
    print("\n10. Performance Metrics:")
    
    # Service discovery stats
    all_services = {}
    for service_name in ["validation-service", "extraction-service", "classification-service"]:
        instances = await service_registry.discover_services(service_name)
        all_services[service_name] = len(instances)
    
    print("   Service Discovery:")
    for service_name, count in all_services.items():
        print(f"     - {service_name}: {count} healthy instances")
    
    # Circuit breaker states
    print("   Circuit Breakers:")
    for service_name, metrics in circuit_breaker_metrics.items():
        print(f"     - {service_name}: {metrics['state']} ({metrics['failure_count']} failures)")
    
    print("\n11. Key Benefits Demonstrated:")
    print("   - Service discovery enables dynamic service location")
    print("   - Load balancing distributes requests across instances")
    print("   - Circuit breakers prevent cascade failures")
    print("   - Retry mechanisms handle transient failures")
    print("   - Event-driven communication enables loose coupling")
    print("   - API versioning supports backward compatibility")
    
    print("\n12. Production Considerations:")
    print("   - Service mesh for advanced traffic management")
    print("   - Distributed tracing for request correlation")
    print("   - Rate limiting and throttling")
    print("   - Authentication and authorization")
    print("   - Monitoring and alerting for service health")
    print("   - Graceful degradation strategies")
    
    # Cleanup
    await http_client.close()
    
    print("\n=== Service communication demonstration completed ===")

if __name__ == "__main__":
    asyncio.run(demonstrate_service_communication())
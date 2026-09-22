"""
FastAPI Microservice Template for Enterprise Systems

This module demonstrates a production-ready FastAPI microservice template
with comprehensive patterns used in enterprise environments like those
at Lawstronaut (legal document processing) and Optimizely (personalization).

Key concepts covered:
- Hexagonal architecture with clean separation of concerns
- Comprehensive health checks and observability
- Configuration management and dependency injection
- Error handling and circuit breaker patterns
- Structured logging and distributed tracing

Real-world applications:
- Document processing microservice at Lawstronaut
- Experiment management service at Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Protocol, Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import logging
import time
import json
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware  
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

# =============================================================================
# DOMAIN MODELS AND INTERFACES
# =============================================================================

class ServiceHealth(str, Enum):
    """Service health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    """Health check result data model"""
    service: str
    status: ServiceHealth
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: List['HealthCheck'] = field(default_factory=list)

class DatabaseRepository(Protocol):
    """Database repository interface"""
    async def health_check(self) -> bool:
        """Check database connectivity"""
        ...
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        ...
    
    async def store_document(self, document: Dict[str, Any]) -> str:
        """Store document and return ID"""
        ...

class MessageBroker(Protocol):
    """Message broker interface"""
    async def health_check(self) -> bool:
        """Check message broker connectivity"""
        ...
    
    async def publish_event(self, topic: str, event: Dict[str, Any]) -> bool:
        """Publish event to topic"""
        ...
    
    async def subscribe_to_topic(self, topic: str, handler: Any) -> None:
        """Subscribe to topic with message handler"""
        ...

class ExternalService(Protocol):
    """External service client interface"""
    async def health_check(self) -> bool:
        """Check external service availability"""
        ...
    
    async def process_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process external request"""
        ...

# =============================================================================
# INFRASTRUCTURE IMPLEMENTATIONS
# =============================================================================

class PostgreSQLRepository:
    """PostgreSQL implementation of database repository"""
    
    def __init__(self, connection_string: str, pool_size: int = 10):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self._pool: Optional[Any] = None
        self.logger = structlog.get_logger()
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            # Simulate connection pool initialization
            await asyncio.sleep(0.1)
            self._pool = {"active": True, "connections": self.pool_size}
            self.logger.info("Database connection pool initialized", pool_size=self.pool_size)
        except Exception as e:
            self.logger.error("Failed to initialize database pool", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            if not self._pool or not self._pool.get("active"):
                return False
            
            # Simulate database ping
            await asyncio.sleep(0.05)
            return True
        except Exception as e:
            self.logger.warning("Database health check failed", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        if not await self.health_check():
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Simulate document retrieval for Lawstronaut legal documents
        await asyncio.sleep(0.02)
        return {
            "id": document_id,
            "title": f"Legal Document {document_id}",
            "type": "contract",
            "jurisdiction": "US",
            "status": "processed",
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def store_document(self, document: Dict[str, Any]) -> str:
        """Store document and return ID"""
        if not await self.health_check():
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        document_id = str(uuid.uuid4())
        document["id"] = document_id
        document["stored_at"] = datetime.utcnow().isoformat()
        
        # Simulate document storage
        await asyncio.sleep(0.03)
        self.logger.info("Document stored", document_id=document_id, type=document.get("type"))
        return document_id
    
    async def close(self):
        """Close database connections"""
        if self._pool:
            self._pool["active"] = False
            self.logger.info("Database connections closed")

class KafkaMessageBroker:
    """Kafka implementation of message broker"""
    
    def __init__(self, bootstrap_servers: List[str], client_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer: Optional[Any] = None
        self._consumer: Optional[Any] = None
        self.logger = structlog.get_logger()
    
    async def initialize(self):
        """Initialize Kafka producer and consumer"""
        try:
            # Simulate Kafka client initialization
            await asyncio.sleep(0.1)
            self._producer = {"active": True, "client_id": self.client_id}
            self._consumer = {"active": True, "client_id": self.client_id}
            self.logger.info("Kafka clients initialized", servers=self.bootstrap_servers)
        except Exception as e:
            self.logger.error("Failed to initialize Kafka clients", error=str(e))
            raise
    
    async def health_check(self) -> bool:
        """Check Kafka broker connectivity"""
        try:
            if not self._producer or not self._producer.get("active"):
                return False
            
            # Simulate Kafka cluster metadata request
            await asyncio.sleep(0.02)
            return True
        except Exception as e:
            self.logger.warning("Kafka health check failed", error=str(e))
            return False
    
    async def publish_event(self, topic: str, event: Dict[str, Any]) -> bool:
        """Publish event to Kafka topic"""
        if not await self.health_check():
            raise HTTPException(status_code=503, detail="Message broker unavailable")
        
        event_with_metadata = {
            **event,
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": self.client_id
        }
        
        # Simulate event publishing
        await asyncio.sleep(0.01)
        self.logger.info("Event published", topic=topic, event_id=event_with_metadata["event_id"])
        return True
    
    async def subscribe_to_topic(self, topic: str, handler: Any) -> None:
        """Subscribe to Kafka topic with message handler"""
        if not await self.health_check():
            raise RuntimeError("Kafka broker unavailable")
        
        self.logger.info("Subscribed to topic", topic=topic)
        # In real implementation, this would start consuming messages
        
    async def close(self):
        """Close Kafka connections"""
        if self._producer:
            self._producer["active"] = False
        if self._consumer:
            self._consumer["active"] = False
        self.logger.info("Kafka connections closed")

class OptimizelyExperimentService:
    """External service client for Optimizely experiments"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = structlog.get_logger()
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=30,
            expected_exception=httpx.RequestError
        )
    
    async def initialize(self):
        """Initialize HTTP client"""
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(connect=5.0, read=10.0)
        )
        self.logger.info("Optimizely client initialized", api_url=self.api_url)
    
    async def health_check(self) -> bool:
        """Check Optimizely API availability"""
        if not self._client:
            return False
        
        try:
            async with self._circuit_breaker:
                # Simulate health check request
                await asyncio.sleep(0.05)
                return True
        except Exception as e:
            self.logger.warning("Optimizely health check failed", error=str(e))
            return False
    
    async def process_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process experiment request"""
        if not self._client:
            raise HTTPException(status_code=503, detail="External service unavailable")
        
        async with self._circuit_breaker:
            # Simulate experiment processing for personalization
            await asyncio.sleep(0.1)
            return {
                "experiment_id": "exp_123",
                "variant": "treatment",
                "user_id": payload.get("user_id"),
                "decision_time": datetime.utcnow().isoformat(),
                "confidence": 0.85
            }
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self.logger.info("Optimizely client closed")

# =============================================================================
# RESILIENCE PATTERNS
# =============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation for resilient service calls"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = CircuitBreakerState.CLOSED
        self.logger = structlog.get_logger()
    
    async def __aenter__(self):
        if self._state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to half-open")
            else:
                raise HTTPException(
                    status_code=503, 
                    detail="Service temporarily unavailable (circuit breaker open)"
                )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.expected_exception):
            await self._record_failure()
        else:
            await self._record_success()
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if not self._last_failure_time:
            return True
        return datetime.utcnow() - self._last_failure_time > timedelta(seconds=self.timeout)
    
    async def _record_failure(self):
        """Record failure and update circuit breaker state"""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN
            self.logger.warning(
                "Circuit breaker opened", 
                failure_count=self._failure_count,
                threshold=self.failure_threshold
            )
        elif self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.OPEN
            self.logger.warning("Circuit breaker failed in half-open, returning to open")
    
    async def _record_success(self):
        """Record success and reset circuit breaker if needed"""
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self.logger.info("Circuit breaker closed after successful request")

# =============================================================================
# APPLICATION LAYER
# =============================================================================

@dataclass
class ServiceConfig:
    """Service configuration data model"""
    service_name: str
    version: str
    environment: str
    log_level: str = "INFO"
    
    # Database configuration
    database_url: str = "postgresql://localhost:5432/lawstronaut"
    database_pool_size: int = 10
    
    # Message broker configuration
    kafka_bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    kafka_client_id: str = "document-service"
    
    # External service configuration
    optimizely_api_url: str = "https://api.optimizely.com"
    optimizely_api_key: str = "your-api-key"
    
    # Monitoring configuration
    enable_metrics: bool = True
    enable_tracing: bool = True
    health_check_interval: int = 30

class DocumentService:
    """Core business logic service for document processing"""
    
    def __init__(self, db_repo: DatabaseRepository, message_broker: MessageBroker,
                 external_service: ExternalService):
        self.db_repo = db_repo
        self.message_broker = message_broker
        self.external_service = external_service
        self.logger = structlog.get_logger()
    
    async def process_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process document with event publishing"""
        start_time = time.time()
        
        try:
            # Store document in database
            document_id = await self.db_repo.store_document(document_data)
            
            # Publish document processing event
            event = {
                "event_type": "document_processed",
                "document_id": document_id,
                "document_type": document_data.get("type", "unknown"),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
            await self.message_broker.publish_event("document_events", event)
            
            # For Optimizely integration: analyze document for personalization insights
            if document_data.get("type") == "user_behavior":
                await self.external_service.process_request({
                    "user_id": document_data.get("user_id"),
                    "action": "document_processed",
                    "document_id": document_id
                })
            
            self.logger.info(
                "Document processed successfully",
                document_id=document_id,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
            return {
                "document_id": document_id,
                "status": "processed",
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            self.logger.error(
                "Document processing failed",
                error=str(e),
                document_type=document_data.get("type")
            )
            raise HTTPException(status_code=500, detail="Document processing failed")
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve document by ID"""
        document = await self.db_repo.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

class HealthCheckService:
    """Comprehensive health check service"""
    
    def __init__(self, db_repo: DatabaseRepository, message_broker: MessageBroker,
                 external_service: ExternalService, config: ServiceConfig):
        self.db_repo = db_repo
        self.message_broker = message_broker
        self.external_service = external_service
        self.config = config
        self.logger = structlog.get_logger()
    
    async def check_health(self) -> HealthCheck:
        """Perform comprehensive health check"""
        start_time = time.time()
        
        # Check all dependencies
        db_healthy = await self.db_repo.health_check()
        broker_healthy = await self.message_broker.health_check()
        external_healthy = await self.external_service.health_check()
        
        # Determine overall health status
        all_healthy = db_healthy and broker_healthy and external_healthy
        some_healthy = db_healthy or broker_healthy or external_healthy
        
        if all_healthy:
            status = ServiceHealth.HEALTHY
        elif some_healthy:
            status = ServiceHealth.DEGRADED
        else:
            status = ServiceHealth.UNHEALTHY
        
        response_time = (time.time() - start_time) * 1000
        
        health_check = HealthCheck(
            service=self.config.service_name,
            status=status,
            timestamp=datetime.utcnow(),
            response_time_ms=response_time,
            details={
                "version": self.config.version,
                "environment": self.config.environment,
                "database": "healthy" if db_healthy else "unhealthy",
                "message_broker": "healthy" if broker_healthy else "unhealthy",
                "external_service": "healthy" if external_healthy else "unhealthy"
            }
        )
        
        self.logger.info(
            "Health check completed",
            status=status.value,
            response_time_ms=response_time,
            database_healthy=db_healthy,
            broker_healthy=broker_healthy,
            external_healthy=external_healthy
        )
        
        return health_check

# =============================================================================
# PRESENTATION LAYER (FASTAPI)
# =============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and timing"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to context
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        logger = structlog.get_logger()
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                error=str(e),
                duration_ms=duration_ms
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()

# Pydantic models for API schemas
class DocumentInput(BaseModel):
    """Input schema for document processing"""
    title: str = Field(..., description="Document title")
    type: str = Field(..., description="Document type (contract, policy, etc.)")
    content: str = Field(..., description="Document content")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Software License Agreement",
                "type": "contract",
                "content": "This agreement governs the use of...",
                "jurisdiction": "US",
                "user_id": "user_123"
            }
        }
    )

class DocumentOutput(BaseModel):
    """Output schema for document processing"""
    document_id: str = Field(..., description="Generated document ID")
    status: str = Field(..., description="Processing status")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

class HealthResponse(BaseModel):
    """Health check response schema"""
    service: str
    status: str
    timestamp: str
    response_time_ms: float
    details: Dict[str, Any]

# Dependency injection functions
async def get_document_service(request: Request) -> DocumentService:
    """Get document service dependency"""
    return request.app.state.document_service

async def get_health_service(request: Request) -> HealthCheckService:
    """Get health check service dependency"""
    return request.app.state.health_service

# FastAPI application factory
def create_app(config: ServiceConfig) -> FastAPI:
    """Create FastAPI application with all dependencies configured"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan management"""
        logger = structlog.get_logger()
        logger.info("Starting application", service=config.service_name, version=config.version)
        
        # Initialize dependencies
        db_repo = PostgreSQLRepository(config.database_url, config.database_pool_size)
        message_broker = KafkaMessageBroker(config.kafka_bootstrap_servers, config.kafka_client_id)
        external_service = OptimizelyExperimentService(config.optimizely_api_url, config.optimizely_api_key)
        
        await db_repo.initialize()
        await message_broker.initialize()
        await external_service.initialize()
        
        # Create services
        document_service = DocumentService(db_repo, message_broker, external_service)
        health_service = HealthCheckService(db_repo, message_broker, external_service, config)
        
        # Store in app state
        app.state.document_service = document_service
        app.state.health_service = health_service
        app.state.db_repo = db_repo
        app.state.message_broker = message_broker
        app.state.external_service = external_service
        
        logger.info("Application started successfully")
        
        yield
        
        # Cleanup
        logger.info("Shutting down application")
        await db_repo.close()
        await message_broker.close()
        await external_service.close()
        logger.info("Application shutdown complete")
    
    # Create FastAPI app
    app = FastAPI(
        title=config.service_name,
        version=config.version,
        description="Production-ready microservice template for enterprise systems",
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.environment == "development" else ["https://lawstronaut.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
    # Health check endpoints
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check(health_service: HealthCheckService = Depends(get_health_service)):
        """Comprehensive health check endpoint"""
        health = await health_service.check_health()
        
        status_code = 200
        if health.status == ServiceHealth.DEGRADED:
            status_code = 200  # Still accepting requests
        elif health.status == ServiceHealth.UNHEALTHY:
            status_code = 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "service": health.service,
                "status": health.status.value,
                "timestamp": health.timestamp.isoformat(),
                "response_time_ms": health.response_time_ms,
                "details": health.details
            }
        )
    
    @app.get("/health/live", tags=["Health"])
    async def liveness_check():
        """Liveness probe for Kubernetes"""
        return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
    
    @app.get("/health/ready", tags=["Health"])
    async def readiness_check(health_service: HealthCheckService = Depends(get_health_service)):
        """Readiness probe for Kubernetes"""
        health = await health_service.check_health()
        
        if health.status == ServiceHealth.UNHEALTHY:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    
    # Business endpoints
    @app.post("/documents", response_model=DocumentOutput, tags=["Documents"])
    async def create_document(
        document: DocumentInput,
        background_tasks: BackgroundTasks,
        document_service: DocumentService = Depends(get_document_service)
    ):
        """Process and store a new document"""
        result = await document_service.process_document(document.model_dump())
        
        # Add background task for additional processing
        background_tasks.add_task(
            _process_document_analytics,
            result["document_id"],
            document.type
        )
        
        return DocumentOutput(**result)
    
    @app.get("/documents/{document_id}", tags=["Documents"])
    async def get_document(
        document_id: str,
        document_service: DocumentService = Depends(get_document_service)
    ):
        """Retrieve document by ID"""
        return await document_service.get_document(document_id)
    
    @app.get("/metrics", tags=["Monitoring"])
    async def get_metrics():
        """Basic metrics endpoint for monitoring"""
        return {
            "service": config.service_name,
            "version": config.version,
            "environment": config.environment,
            "uptime_seconds": time.time(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return app

async def _process_document_analytics(document_id: str, document_type: str):
    """Background task for document analytics processing"""
    logger = structlog.get_logger()
    logger.info("Processing document analytics", document_id=document_id, type=document_type)
    
    # Simulate analytics processing
    await asyncio.sleep(2.0)
    
    logger.info("Document analytics completed", document_id=document_id)

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

async def demonstrate_microservice_template():
    """
    Comprehensive demonstration of production-ready FastAPI microservice
    template with enterprise patterns and practices.
    """
    
    print("=== FastAPI Microservice Template for Enterprise Systems ===\n")
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Create service configuration
    config = ServiceConfig(
        service_name="lawstronaut-document-service",
        version="1.0.0",
        environment="development"
    )
    
    print("1. Service Configuration:")
    print(f"   - Service: {config.service_name}")
    print(f"   - Version: {config.version}")
    print(f"   - Environment: {config.environment}")
    print(f"   - Database: {config.database_url}")
    print(f"   - Kafka: {config.kafka_bootstrap_servers}")
    
    # Create FastAPI application
    app = create_app(config)
    
    print("\n2. Application Features:")
    print("   - Hexagonal architecture with clean separation")
    print("   - Comprehensive health checks (liveness/readiness)")
    print("   - Circuit breaker pattern for resilience")
    print("   - Structured logging with correlation IDs")
    print("   - Background task processing")
    print("   - Dependency injection")
    
    print("\n3. Available Endpoints:")
    print("   - POST /documents - Process new documents")
    print("   - GET /documents/{id} - Retrieve documents")
    print("   - GET /health - Comprehensive health check")
    print("   - GET /health/live - Liveness probe")
    print("   - GET /health/ready - Readiness probe")
    print("   - GET /metrics - Service metrics")
    
    print("\n4. Enterprise Patterns Demonstrated:")
    print("   - Domain-driven service boundaries")
    print("   - Repository pattern for data access")
    print("   - Event-driven communication")
    print("   - Circuit breaker for external services")
    print("   - Request correlation and tracing")
    print("   - Graceful startup and shutdown")
    
    print("\n5. Production Considerations:")
    print("   - Connection pooling for databases")
    print("   - Retry logic and circuit breakers")
    print("   - Comprehensive error handling")
    print("   - Security middleware (CORS, trusted hosts)")
    print("   - Observability and monitoring")
    print("   - Configuration management")
    
    print("\n6. Scalability Features:")
    print("   - Async/await for high concurrency")
    print("   - Background task processing")
    print("   - Stateless design for horizontal scaling")
    print("   - Health checks for load balancer integration")
    print("   - Graceful degradation when dependencies fail")
    
    # Demonstrate key components
    print("\n7. Component Demonstration:")
    
    # Initialize components manually for demonstration
    db_repo = PostgreSQLRepository(config.database_url)
    message_broker = KafkaMessageBroker(config.kafka_bootstrap_servers, config.kafka_client_id)
    external_service = OptimizelyExperimentService(config.optimizely_api_url, config.optimizely_api_key)
    
    await db_repo.initialize()
    await message_broker.initialize()  
    await external_service.initialize()
    
    # Create services
    document_service = DocumentService(db_repo, message_broker, external_service)
    health_service = HealthCheckService(db_repo, message_broker, external_service, config)
    
    # Test document processing
    test_document = {
        "title": "Test Legal Contract",
        "type": "contract", 
        "content": "This is a test legal document for demonstration purposes.",
        "jurisdiction": "US",
        "user_id": "demo_user_123"
    }
    
    print("   - Processing test document...")
    result = await document_service.process_document(test_document)
    print(f"   - Document processed: {result['document_id']}")
    print(f"   - Processing time: {result['processing_time_ms']:.2f}ms")
    
    # Test health check
    print("   - Performing health check...")
    health = await health_service.check_health()
    print(f"   - Service health: {health.status.value}")
    print(f"   - Health check time: {health.response_time_ms:.2f}ms")
    
    # Cleanup
    await db_repo.close()
    await message_broker.close()
    await external_service.close()
    
    print("\n=== Microservice template demonstration completed successfully ===")
    print("\nTo run this service in production:")
    print("1. Configure environment variables for database/Kafka connections")
    print("2. Set up proper logging infrastructure")
    print("3. Configure load balancer health check endpoints")
    print("4. Deploy with container orchestration (Kubernetes)")
    print("5. Set up monitoring and alerting")

if __name__ == "__main__":
    asyncio.run(demonstrate_microservice_template())
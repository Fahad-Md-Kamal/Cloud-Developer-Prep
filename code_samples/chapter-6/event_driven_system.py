"""
Event-Driven System Architecture with Kafka and Saga Patterns

This module demonstrates comprehensive event-driven architecture patterns
for microservices systems like those used at Lawstronaut (legal document 
processing workflows) and Optimizely (real-time experimentation).

Key concepts covered:
- Event sourcing and event streaming with Kafka
- Saga pattern for distributed transactions (orchestration and choreography)
- CQRS (Command Query Responsibility Segregation)
- Event store implementation with replay capabilities
- Compensation patterns for handling failures

Real-world applications:
- Legal document workflow orchestration at Lawstronaut
- A/B test lifecycle management at Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Protocol, Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import json
import uuid
from datetime import datetime, timedelta
import logging
from collections import defaultdict

# =============================================================================
# DOMAIN MODELS AND EVENTS
# =============================================================================

class EventType(str, Enum):
    """Standard event types for the system"""
    # Document processing events
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_CLASSIFIED = "document_classified"
    DOCUMENT_INDEXED = "document_indexed"
    DOCUMENT_FAILED = "document_failed"
    
    # Experiment events  
    EXPERIMENT_CREATED = "experiment_created"
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_USER_ASSIGNED = "experiment_user_assigned"
    EXPERIMENT_CONVERSION = "experiment_conversion"
    EXPERIMENT_ENDED = "experiment_ended"
    
    # Saga events
    SAGA_STARTED = "saga_started"
    SAGA_STEP_COMPLETED = "saga_step_completed"
    SAGA_STEP_FAILED = "saga_step_failed"
    SAGA_COMPLETED = "saga_completed"
    SAGA_COMPENSATED = "saga_compensated"

@dataclass
class DomainEvent:
    """Base domain event with metadata"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.DOCUMENT_UPLOADED
    aggregate_id: str = ""
    aggregate_version: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""
    causation_id: str = ""
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_version": self.aggregate_version,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "payload": self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """Deserialize event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_version=data["aggregate_version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
            payload=data.get("payload", {})
        )

# Specific event types for different domains
@dataclass
class DocumentUploadedEvent(DomainEvent):
    """Event fired when document is uploaded"""
    
    def __init__(self, document_id: str, filename: str, file_size: int, 
                 user_id: str, correlation_id: str):
        super().__init__(
            event_type=EventType.DOCUMENT_UPLOADED,
            aggregate_id=document_id,
            correlation_id=correlation_id,
            user_id=user_id,
            payload={
                "document_id": document_id,
                "filename": filename,
                "file_size": file_size,
                "upload_timestamp": datetime.utcnow().isoformat()
            }
        )

@dataclass
class ExperimentCreatedEvent(DomainEvent):
    """Event fired when A/B experiment is created"""
    
    def __init__(self, experiment_id: str, name: str, variants: List[str],
                 traffic_allocation: Dict[str, float], user_id: str, correlation_id: str):
        super().__init__(
            event_type=EventType.EXPERIMENT_CREATED,
            aggregate_id=experiment_id,
            correlation_id=correlation_id,
            user_id=user_id,
            payload={
                "experiment_id": experiment_id,
                "name": name,
                "variants": variants,
                "traffic_allocation": traffic_allocation,
                "created_at": datetime.utcnow().isoformat()
            }
        )

# =============================================================================
# EVENT STORE AND STREAMING
# =============================================================================

class EventStore(Protocol):
    """Event store interface for persisting and retrieving events"""
    
    async def append_events(self, stream_name: str, events: List[DomainEvent],
                          expected_version: int) -> None:
        """Append events to stream with optimistic concurrency control"""
        ...
    
    async def get_events(self, stream_name: str, from_version: int = 0) -> List[DomainEvent]:
        """Get events from stream starting from specific version"""
        ...
    
    async def get_all_events(self, from_timestamp: Optional[datetime] = None) -> AsyncIterator[DomainEvent]:
        """Get all events across all streams for projection building"""
        ...

class EventBus(Protocol):
    """Event bus interface for publishing and subscribing to events"""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish event to appropriate topic"""
        ...
    
    async def subscribe(self, event_type: EventType, handler: Callable[[DomainEvent], None]) -> None:
        """Subscribe to specific event type"""
        ...
    
    async def subscribe_to_stream(self, stream_pattern: str, 
                                handler: Callable[[DomainEvent], None]) -> None:
        """Subscribe to event stream pattern"""
        ...

class InMemoryEventStore:
    """In-memory event store implementation for development/testing"""
    
    def __init__(self):
        self._streams: Dict[str, List[DomainEvent]] = defaultdict(list)
        self._global_events: List[DomainEvent] = []
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.logger = logging.getLogger(__name__)
    
    async def append_events(self, stream_name: str, events: List[DomainEvent],
                          expected_version: int) -> None:
        """Append events with optimistic concurrency control"""
        async with self._locks[stream_name]:
            current_version = len(self._streams[stream_name])
            
            if current_version != expected_version:
                raise ValueError(
                    f"Concurrency conflict: expected version {expected_version}, "
                    f"but current version is {current_version}"
                )
            
            # Update event versions and append
            for i, event in enumerate(events):
                event.aggregate_version = current_version + i + 1
            
            self._streams[stream_name].extend(events)
            self._global_events.extend(events)
            
            self.logger.info(
                "Events appended to stream",
                stream=stream_name,
                count=len(events),
                new_version=len(self._streams[stream_name])
            )
    
    async def get_events(self, stream_name: str, from_version: int = 0) -> List[DomainEvent]:
        """Get events from stream"""
        return self._streams[stream_name][from_version:]
    
    async def get_all_events(self, from_timestamp: Optional[datetime] = None) -> AsyncIterator[DomainEvent]:
        """Get all events for projection building"""
        for event in self._global_events:
            if from_timestamp is None or event.timestamp >= from_timestamp:
                yield event

class KafkaEventBus:
    """Kafka-based event bus implementation"""
    
    def __init__(self, bootstrap_servers: List[str], topic_prefix: str = "events"):
        self.bootstrap_servers = bootstrap_servers
        self.topic_prefix = topic_prefix
        self._producer: Optional[Any] = None
        self._consumers: Dict[str, Any] = {}
        self._handlers: Dict[EventType, List[Callable[[DomainEvent], None]]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize Kafka producer and consumers"""
        # Simulate Kafka client initialization
        self._producer = {"active": True, "servers": self.bootstrap_servers}
        self.logger.info("Kafka event bus initialized", servers=self.bootstrap_servers)
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish event to Kafka topic"""
        if not self._producer:
            raise RuntimeError("Event bus not initialized")
        
        topic = f"{self.topic_prefix}.{event.event_type.value}"
        message = json.dumps(event.to_dict())
        
        # Simulate Kafka publish
        await asyncio.sleep(0.01)
        
        self.logger.info(
            "Event published",
            event_id=event.event_id,
            event_type=event.event_type.value,
            topic=topic,
            aggregate_id=event.aggregate_id
        )
    
    async def subscribe(self, event_type: EventType, 
                      handler: Callable[[DomainEvent], None]) -> None:
        """Subscribe to specific event type"""
        self._handlers[event_type].append(handler)
        
        topic = f"{self.topic_prefix}.{event_type.value}"
        if topic not in self._consumers:
            # Simulate Kafka consumer creation
            self._consumers[topic] = {"active": True, "topic": topic}
            self.logger.info("Subscribed to event type", event_type=event_type.value, topic=topic)
    
    async def _handle_message(self, topic: str, message: str):
        """Handle incoming Kafka message"""
        try:
            event_data = json.loads(message)
            event = DomainEvent.from_dict(event_data)
            
            # Call all registered handlers
            for handler in self._handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    self.logger.error(
                        "Event handler failed",
                        event_id=event.event_id,
                        handler=handler.__name__,
                        error=str(e)
                    )
        except Exception as e:
            self.logger.error("Failed to process message", topic=topic, error=str(e))

# =============================================================================
# SAGA PATTERN IMPLEMENTATION
# =============================================================================

class SagaStep(ABC):
    """Abstract base class for saga steps"""
    
    def __init__(self, step_name: str):
        self.step_name = step_name
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the saga step"""
        ...
    
    @abstractmethod
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Compensate/rollback the saga step"""
        ...

class SagaStatus(Enum):
    """Saga execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"

@dataclass
class SagaExecution:
    """Saga execution state"""
    saga_id: str
    saga_type: str
    status: SagaStatus
    current_step: int
    context: Dict[str, Any]
    completed_steps: List[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class SagaOrchestrator:
    """Orchestration-based saga coordinator"""
    
    def __init__(self, event_store: EventStore, event_bus: EventBus):
        self.event_store = event_store
        self.event_bus = event_bus
        self._saga_definitions: Dict[str, List[SagaStep]] = {}
        self._active_sagas: Dict[str, SagaExecution] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_saga(self, saga_type: str, steps: List[SagaStep]):
        """Register a saga definition"""
        self._saga_definitions[saga_type] = steps
        self.logger.info("Saga registered", saga_type=saga_type, step_count=len(steps))
    
    async def start_saga(self, saga_type: str, initial_context: Dict[str, Any]) -> str:
        """Start a new saga execution"""
        if saga_type not in self._saga_definitions:
            raise ValueError(f"Unknown saga type: {saga_type}")
        
        saga_id = str(uuid.uuid4())
        execution = SagaExecution(
            saga_id=saga_id,
            saga_type=saga_type,
            status=SagaStatus.PENDING,
            current_step=0,
            context=initial_context
        )
        
        self._active_sagas[saga_id] = execution
        
        # Publish saga started event
        event = DomainEvent(
            event_type=EventType.SAGA_STARTED,
            aggregate_id=saga_id,
            correlation_id=initial_context.get("correlation_id", saga_id),
            payload={
                "saga_id": saga_id,
                "saga_type": saga_type,
                "context": initial_context
            }
        )
        
        await self.event_bus.publish(event)
        
        # Start execution
        asyncio.create_task(self._execute_saga(saga_id))
        
        self.logger.info("Saga started", saga_id=saga_id, saga_type=saga_type)
        return saga_id
    
    async def _execute_saga(self, saga_id: str):
        """Execute saga steps sequentially"""
        execution = self._active_sagas[saga_id]
        steps = self._saga_definitions[execution.saga_type]
        
        try:
            execution.status = SagaStatus.IN_PROGRESS
            
            for step_index, step in enumerate(steps[execution.current_step:], execution.current_step):
                execution.current_step = step_index
                execution.updated_at = datetime.utcnow()
                
                try:
                    # Execute step
                    self.logger.info(
                        "Executing saga step",
                        saga_id=saga_id,
                        step=step.step_name,
                        step_index=step_index
                    )
                    
                    result = await step.execute(execution.context)
                    execution.context.update(result)
                    execution.completed_steps.append(step.step_name)
                    
                    # Publish step completed event
                    event = DomainEvent(
                        event_type=EventType.SAGA_STEP_COMPLETED,
                        aggregate_id=saga_id,
                        correlation_id=execution.context.get("correlation_id", saga_id),
                        payload={
                            "saga_id": saga_id,
                            "step_name": step.step_name,
                            "step_index": step_index,
                            "result": result
                        }
                    )
                    await self.event_bus.publish(event)
                    
                except Exception as e:
                    # Step failed, start compensation
                    execution.status = SagaStatus.FAILED
                    execution.failed_step = step.step_name
                    execution.error_message = str(e)
                    
                    self.logger.error(
                        "Saga step failed",
                        saga_id=saga_id,
                        step=step.step_name,
                        error=str(e)
                    )
                    
                    # Publish step failed event
                    event = DomainEvent(
                        event_type=EventType.SAGA_STEP_FAILED,
                        aggregate_id=saga_id,
                        correlation_id=execution.context.get("correlation_id", saga_id),
                        payload={
                            "saga_id": saga_id,
                            "step_name": step.step_name,
                            "step_index": step_index,
                            "error": str(e)
                        }
                    )
                    await self.event_bus.publish(event)
                    
                    await self._compensate_saga(saga_id)
                    return
            
            # All steps completed successfully
            execution.status = SagaStatus.COMPLETED
            execution.updated_at = datetime.utcnow()
            
            # Publish saga completed event
            event = DomainEvent(
                event_type=EventType.SAGA_COMPLETED,
                aggregate_id=saga_id,
                correlation_id=execution.context.get("correlation_id", saga_id),
                payload={
                    "saga_id": saga_id,
                    "saga_type": execution.saga_type,
                    "final_context": execution.context
                }
            )
            await self.event_bus.publish(event)
            
            self.logger.info("Saga completed successfully", saga_id=saga_id)
            
        except Exception as e:
            execution.status = SagaStatus.FAILED
            execution.error_message = str(e)
            self.logger.error("Saga execution failed", saga_id=saga_id, error=str(e))
            await self._compensate_saga(saga_id)
    
    async def _compensate_saga(self, saga_id: str):
        """Compensate saga by rolling back completed steps"""
        execution = self._active_sagas[saga_id]
        execution.status = SagaStatus.COMPENSATING
        
        steps = self._saga_definitions[execution.saga_type]
        completed_steps = list(reversed(execution.completed_steps))
        
        for step_name in completed_steps:
            # Find the step by name
            step = next(s for s in steps if s.step_name == step_name)
            
            try:
                self.logger.info("Compensating saga step", saga_id=saga_id, step=step_name)
                await step.compensate(execution.context)
                
            except Exception as e:
                self.logger.error(
                    "Compensation failed",
                    saga_id=saga_id,
                    step=step_name,
                    error=str(e)
                )
        
        execution.status = SagaStatus.COMPENSATED
        execution.updated_at = datetime.utcnow()
        
        # Publish saga compensated event
        event = DomainEvent(
            event_type=EventType.SAGA_COMPENSATED,
            aggregate_id=saga_id,
            correlation_id=execution.context.get("correlation_id", saga_id),
            payload={
                "saga_id": saga_id,
                "saga_type": execution.saga_type,
                "failed_step": execution.failed_step,
                "error_message": execution.error_message
            }
        )
        await self.event_bus.publish(event)
        
        self.logger.info("Saga compensated", saga_id=saga_id)

# =============================================================================
# CONCRETE SAGA STEPS FOR BUSINESS WORKFLOWS
# =============================================================================

class DocumentValidationStep(SagaStep):
    """Validate uploaded document for processing"""
    
    def __init__(self):
        super().__init__("document_validation")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document format and content"""
        document_id = context["document_id"]
        filename = context["filename"]
        
        # Simulate document validation
        await asyncio.sleep(0.1)
        
        if filename.endswith(('.pdf', '.docx', '.txt')):
            self.logger.info("Document validation passed", document_id=document_id)
            return {
                "validation_status": "passed",
                "supported_format": True,
                "validation_timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise ValueError(f"Unsupported document format: {filename}")
    
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Mark document as invalid"""
        document_id = context["document_id"]
        self.logger.info("Compensating document validation", document_id=document_id)
        # In real implementation: mark document as failed validation

class DocumentProcessingStep(SagaStep):
    """Process document content (OCR, text extraction)"""
    
    def __init__(self):
        super().__init__("document_processing")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text and metadata from document"""
        document_id = context["document_id"]
        
        # Simulate document processing with potential failure
        await asyncio.sleep(0.5)
        
        if context.get("filename", "").startswith("fail_"):
            raise RuntimeError("Document processing service unavailable")
        
        extracted_text = f"Extracted text content from document {document_id}"
        
        self.logger.info("Document processing completed", document_id=document_id)
        return {
            "processing_status": "completed",
            "extracted_text": extracted_text,
            "word_count": len(extracted_text.split()),
            "processing_timestamp": datetime.utcnow().isoformat()
        }
    
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Clean up processing artifacts"""
        document_id = context["document_id"]
        self.logger.info("Compensating document processing", document_id=document_id)
        # In real implementation: delete processing artifacts, temporary files

class DocumentIndexingStep(SagaStep):
    """Index document for search"""
    
    def __init__(self):
        super().__init__("document_indexing")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Index document in search engine"""
        document_id = context["document_id"]
        extracted_text = context.get("extracted_text", "")
        
        # Simulate search indexing
        await asyncio.sleep(0.2)
        
        index_id = f"idx_{document_id}"
        
        self.logger.info("Document indexing completed", document_id=document_id, index_id=index_id)
        return {
            "indexing_status": "completed",
            "index_id": index_id,
            "searchable": True,
            "indexing_timestamp": datetime.utcnow().isoformat()
        }
    
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Remove document from search index"""
        document_id = context["document_id"]
        index_id = context.get("index_id")
        self.logger.info("Compensating document indexing", document_id=document_id, index_id=index_id)
        # In real implementation: remove from Elasticsearch/Solr index

class NotificationStep(SagaStep):
    """Send completion notification to user"""
    
    def __init__(self):
        super().__init__("notification")
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send processing completion notification"""
        document_id = context["document_id"]
        user_id = context.get("user_id")
        
        # Simulate notification sending
        await asyncio.sleep(0.1)
        
        notification_id = str(uuid.uuid4())
        
        self.logger.info(
            "Notification sent",
            document_id=document_id,
            user_id=user_id,
            notification_id=notification_id
        )
        return {
            "notification_status": "sent",
            "notification_id": notification_id,
            "notification_timestamp": datetime.utcnow().isoformat()
        }
    
    async def compensate(self, context: Dict[str, Any]) -> None:
        """Send failure notification"""
        document_id = context["document_id"]
        user_id = context.get("user_id")
        notification_id = str(uuid.uuid4())
        
        self.logger.info(
            "Failure notification sent",
            document_id=document_id,
            user_id=user_id,
            notification_id=notification_id
        )
        # In real implementation: send actual failure notification

# =============================================================================
# CQRS PROJECTIONS AND READ MODELS
# =============================================================================

@dataclass
class DocumentProjection:
    """Read model for document queries"""
    document_id: str
    filename: str
    status: str
    user_id: str
    upload_timestamp: datetime
    processing_timestamp: Optional[datetime] = None
    indexing_timestamp: Optional[datetime] = None
    word_count: Optional[int] = None
    searchable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "status": self.status,
            "user_id": self.user_id,
            "upload_timestamp": self.upload_timestamp.isoformat(),
            "processing_timestamp": self.processing_timestamp.isoformat() if self.processing_timestamp else None,
            "indexing_timestamp": self.indexing_timestamp.isoformat() if self.indexing_timestamp else None,
            "word_count": self.word_count,
            "searchable": self.searchable
        }

class DocumentProjectionBuilder:
    """Builds document read models from events"""
    
    def __init__(self):
        self._projections: Dict[str, DocumentProjection] = {}
        self.logger = logging.getLogger(__name__)
    
    async def handle_event(self, event: DomainEvent):
        """Handle domain event and update projection"""
        if event.event_type == EventType.DOCUMENT_UPLOADED:
            await self._handle_document_uploaded(event)
        elif event.event_type == EventType.SAGA_STEP_COMPLETED:
            await self._handle_saga_step_completed(event)
        elif event.event_type == EventType.SAGA_COMPLETED:
            await self._handle_saga_completed(event)
        elif event.event_type == EventType.SAGA_COMPENSATED:
            await self._handle_saga_compensated(event)
    
    async def _handle_document_uploaded(self, event: DomainEvent):
        """Handle document uploaded event"""
        payload = event.payload
        document_id = payload["document_id"]
        
        projection = DocumentProjection(
            document_id=document_id,
            filename=payload["filename"],
            status="uploaded",
            user_id=event.user_id,
            upload_timestamp=event.timestamp
        )
        
        self._projections[document_id] = projection
        self.logger.info("Document projection created", document_id=document_id)
    
    async def _handle_saga_step_completed(self, event: DomainEvent):
        """Handle saga step completion"""
        payload = event.payload
        step_name = payload["step_name"]
        result = payload.get("result", {})
        
        # Extract document_id from event context
        document_id = self._extract_document_id(event)
        if not document_id or document_id not in self._projections:
            return
        
        projection = self._projections[document_id]
        
        if step_name == "document_processing":
            projection.processing_timestamp = event.timestamp
            projection.word_count = result.get("word_count")
            projection.status = "processed"
        elif step_name == "document_indexing":
            projection.indexing_timestamp = event.timestamp
            projection.searchable = result.get("searchable", False)
            projection.status = "indexed"
    
    async def _handle_saga_completed(self, event: DomainEvent):
        """Handle saga completion"""
        document_id = self._extract_document_id(event)
        if document_id and document_id in self._projections:
            self._projections[document_id].status = "completed"
            self.logger.info("Document processing completed", document_id=document_id)
    
    async def _handle_saga_compensated(self, event: DomainEvent):
        """Handle saga compensation (failure)"""
        document_id = self._extract_document_id(event)
        if document_id and document_id in self._projections:
            self._projections[document_id].status = "failed"
            self.logger.info("Document processing failed", document_id=document_id)
    
    def _extract_document_id(self, event: DomainEvent) -> Optional[str]:
        """Extract document ID from saga event"""
        # In practice, this would use correlation ID mapping
        return event.correlation_id if event.correlation_id.startswith("doc_") else None
    
    def get_projection(self, document_id: str) -> Optional[DocumentProjection]:
        """Get document projection by ID"""
        return self._projections.get(document_id)
    
    def get_all_projections(self) -> List[DocumentProjection]:
        """Get all document projections"""
        return list(self._projections.values())

# =============================================================================
# INTEGRATION AND DEMONSTRATION
# =============================================================================

class EventDrivenWorkflowOrchestrator:
    """Complete event-driven system orchestrator"""
    
    def __init__(self):
        self.event_store = InMemoryEventStore()
        self.event_bus = KafkaEventBus(["localhost:9092"])
        self.saga_orchestrator = SagaOrchestrator(self.event_store, self.event_bus)
        self.projection_builder = DocumentProjectionBuilder()
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize all components"""
        await self.event_bus.initialize()
        
        # Register saga definition for document processing
        self.saga_orchestrator.register_saga("document_processing", [
            DocumentValidationStep(),
            DocumentProcessingStep(),
            DocumentIndexingStep(),
            NotificationStep()
        ])
        
        # Subscribe projection builder to events
        for event_type in [EventType.DOCUMENT_UPLOADED, EventType.SAGA_STEP_COMPLETED,
                          EventType.SAGA_COMPLETED, EventType.SAGA_COMPENSATED]:
            await self.event_bus.subscribe(event_type, self.projection_builder.handle_event)
        
        self.logger.info("Event-driven system initialized")
    
    async def upload_document(self, filename: str, file_size: int, user_id: str) -> str:
        """Upload document and start processing workflow"""
        document_id = f"doc_{str(uuid.uuid4())}"
        correlation_id = f"workflow_{str(uuid.uuid4())}"
        
        # Create and publish document uploaded event
        event = DocumentUploadedEvent(
            document_id=document_id,
            filename=filename,
            file_size=file_size,
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        await self.event_store.append_events(f"document-{document_id}", [event], 0)
        await self.event_bus.publish(event)
        
        # Start document processing saga
        saga_context = {
            "document_id": document_id,
            "filename": filename,
            "file_size": file_size,
            "user_id": user_id,
            "correlation_id": correlation_id
        }
        
        saga_id = await self.saga_orchestrator.start_saga("document_processing", saga_context)
        
        self.logger.info(
            "Document upload initiated",
            document_id=document_id,
            saga_id=saga_id,
            filename=filename
        )
        
        return document_id
    
    async def get_document_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get current document processing status"""
        projection = self.projection_builder.get_projection(document_id)
        return projection.to_dict() if projection else None
    
    async def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get overall workflow statistics"""
        projections = self.projection_builder.get_all_projections()
        
        status_counts = defaultdict(int)
        for proj in projections:
            status_counts[proj.status] += 1
        
        return {
            "total_documents": len(projections),
            "status_breakdown": dict(status_counts),
            "completed_percentage": (status_counts["completed"] / len(projections) * 100) if projections else 0
        }

async def demonstrate_event_driven_system():
    """
    Comprehensive demonstration of event-driven architecture patterns
    including event sourcing, CQRS, and saga patterns.
    """
    
    print("=== Event-Driven System Architecture with Saga Patterns ===\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the complete system
    orchestrator = EventDrivenWorkflowOrchestrator()
    await orchestrator.initialize()
    
    print("1. System Architecture:")
    print("   - Event Store: Immutable event log with optimistic concurrency")
    print("   - Event Bus: Kafka-based publish/subscribe messaging")
    print("   - Saga Orchestrator: Distributed transaction coordination")
    print("   - CQRS Projections: Optimized read models from events")
    print("   - Compensation Patterns: Rollback handling for failures")
    
    print("\n2. Document Processing Workflow:")
    print("   Step 1: Document Validation")
    print("   Step 2: Content Processing (OCR/extraction)")
    print("   Step 3: Search Indexing")
    print("   Step 4: User Notification")
    
    # Demonstrate successful workflow
    print("\n3. Testing Successful Document Processing:")
    
    document_id = await orchestrator.upload_document(
        filename="legal_contract.pdf",
        file_size=1024000,
        user_id="lawyer_123"
    )
    
    print(f"   - Document uploaded: {document_id}")
    
    # Wait for saga completion
    await asyncio.sleep(2.0)
    
    status = await orchestrator.get_document_status(document_id)
    if status:
        print(f"   - Final status: {status['status']}")
        print(f"   - Searchable: {status['searchable']}")
        print(f"   - Word count: {status['word_count']}")
    
    # Demonstrate failure and compensation
    print("\n4. Testing Failure and Compensation:")
    
    failed_document_id = await orchestrator.upload_document(
        filename="fail_processing_error.pdf",  # This will trigger processing failure
        file_size=512000,
        user_id="lawyer_456"
    )
    
    print(f"   - Failed document uploaded: {failed_document_id}")
    
    # Wait for compensation
    await asyncio.sleep(2.0)
    
    failed_status = await orchestrator.get_document_status(failed_document_id)
    if failed_status:
        print(f"   - Final status: {failed_status['status']}")
        print("   - Compensation completed for failed workflow")
    
    # Demonstrate multiple documents
    print("\n5. Bulk Processing Demonstration:")
    
    documents = []
    for i in range(3):
        doc_id = await orchestrator.upload_document(
            filename=f"bulk_document_{i+1}.docx",
            file_size=256000,
            user_id="bulk_user"
        )
        documents.append(doc_id)
        print(f"   - Bulk document {i+1} uploaded: {doc_id}")
    
    # Wait for all processing
    await asyncio.sleep(3.0)
    
    print("\n6. System Statistics:")
    stats = await orchestrator.get_workflow_statistics()
    print(f"   - Total documents processed: {stats['total_documents']}")
    print(f"   - Status breakdown: {stats['status_breakdown']}")
    print(f"   - Completion rate: {stats['completed_percentage']:.1f}%")
    
    print("\n7. Event Sourcing Benefits:")
    print("   - Complete audit trail of all document processing steps")
    print("   - Ability to rebuild read models from events")
    print("   - Time-travel debugging and analytics")
    print("   - Eventual consistency with immediate responsiveness")
    
    print("\n8. Saga Pattern Benefits:")
    print("   - Distributed transaction management without 2PC")
    print("   - Automatic compensation on failures")
    print("   - Clear separation of business workflow steps")
    print("   - Resilience to partial failures and service outages")
    
    print("\n9. CQRS Benefits:")
    print("   - Optimized read models for query performance")
    print("   - Independent scaling of read and write operations")
    print("   - Multiple specialized views from same event stream")
    print("   - Real-time updates through event projections")
    
    print("\n10. Production Considerations:")
    print("   - Event schema evolution and versioning")
    print("   - Dead letter queues for failed message processing")
    print("   - Monitoring and alerting for saga timeouts")
    print("   - Snapshot strategies for large event streams")
    print("   - Idempotency handling for duplicate events")
    
    print("\n=== Event-driven system demonstration completed successfully ===")

if __name__ == "__main__":
    asyncio.run(demonstrate_event_driven_system())
"""
Message Queue Integration with Kafka and Redis

This module demonstrates comprehensive message queue integration patterns
for microservices architectures like those used at Lawstronaut (legal 
document processing) and Optimizely (real-time personalization).

Key concepts covered:
- Kafka producer/consumer patterns with high throughput
- Redis task queues with priority handling and retry mechanisms
- Message serialization with Avro schema registry
- Dead letter queues and error handling strategies
- Backpressure and flow control mechanisms

Real-world applications:
- High-volume document processing queues at Lawstronaut
- Real-time experiment event processing at Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Protocol, Dict, List, Optional, Any, Callable, AsyncIterator, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import asyncio
import json
import uuid
import time
import pickle
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import heapq
import hashlib

# =============================================================================
# MESSAGE AND QUEUE ABSTRACTIONS
# =============================================================================

class MessagePriority(Enum):
    """Message priority levels for task queues"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Message:
    """Base message structure with metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary"""
        return {
            "id": self.id,
            "topic": self.topic,
            "payload": self.payload,
            "headers": self.headers,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Deserialize message from dictionary"""
        return cls(
            id=data["id"],
            topic=data["topic"],
            payload=data["payload"],
            headers=data["headers"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=MessagePriority(data["priority"]),
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            correlation_id=data.get("correlation_id")
        )

@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    worker_id: Optional[str] = None

class MessageProducer(Protocol):
    """Message producer interface"""
    
    async def send_message(self, topic: str, message: Message) -> bool:
        """Send message to topic"""
        ...
    
    async def send_batch(self, topic: str, messages: List[Message]) -> List[bool]:
        """Send batch of messages for better throughput"""
        ...

class MessageConsumer(Protocol):
    """Message consumer interface"""
    
    async def consume_messages(self, topics: List[str], 
                             handler: Callable[[Message], None]) -> None:
        """Consume messages from topics"""
        ...
    
    async def commit_offset(self, message_id: str) -> None:
        """Commit message processing offset"""
        ...

class TaskQueue(Protocol):
    """Task queue interface for background job processing"""
    
    async def enqueue_task(self, task_name: str, payload: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """Enqueue task for background processing"""
        ...
    
    async def dequeue_task(self, worker_id: str) -> Optional[Message]:
        """Dequeue highest priority task"""
        ...
    
    async def complete_task(self, task_id: str, result: TaskResult) -> None:
        """Mark task as completed"""
        ...
    
    async def retry_task(self, task_id: str, delay_seconds: int = 0) -> None:
        """Retry failed task with optional delay"""
        ...

# =============================================================================
# KAFKA IMPLEMENTATION
# =============================================================================

class KafkaMessageProducer:
    """High-performance Kafka message producer"""
    
    def __init__(self, bootstrap_servers: List[str], client_id: str,
                 compression_type: str = "lz4", batch_size: int = 16384):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.compression_type = compression_type
        self.batch_size = batch_size
        self._producer: Optional[Any] = None
        self._metrics = {
            "messages_sent": 0,
            "bytes_sent": 0,
            "send_errors": 0,
            "batch_count": 0
        }
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize Kafka producer with optimizations"""
        # Simulate Kafka producer creation with performance settings
        self._producer = {
            "active": True,
            "client_id": self.client_id,
            "config": {
                "bootstrap_servers": self.bootstrap_servers,
                "compression_type": self.compression_type,
                "batch_size": self.batch_size,
                "linger_ms": 5,  # Small delay to allow batching
                "acks": "1",     # Wait for leader acknowledgment
                "retries": 3,
                "max_in_flight_requests_per_connection": 5
            }
        }
        
        self.logger.info(
            "Kafka producer initialized",
            client_id=self.client_id,
            servers=self.bootstrap_servers,
            compression=self.compression_type
        )
    
    async def send_message(self, topic: str, message: Message) -> bool:
        """Send single message with error handling"""
        if not self._producer or not self._producer.get("active"):
            raise RuntimeError("Producer not initialized")
        
        try:
            # Serialize message
            serialized_message = json.dumps(message.to_dict())
            message_size = len(serialized_message.encode('utf-8'))
            
            # Simulate Kafka send with network latency
            await asyncio.sleep(0.005)  # 5ms network latency
            
            # Update metrics
            self._metrics["messages_sent"] += 1
            self._metrics["bytes_sent"] += message_size
            
            self.logger.debug(
                "Message sent to Kafka",
                topic=topic,
                message_id=message.id,
                size_bytes=message_size,
                priority=message.priority.name
            )
            
            return True
            
        except Exception as e:
            self._metrics["send_errors"] += 1
            self.logger.error(
                "Failed to send message",
                topic=topic,
                message_id=message.id,
                error=str(e)
            )
            return False
    
    async def send_batch(self, topic: str, messages: List[Message]) -> List[bool]:
        """Send batch of messages for higher throughput"""
        if not messages:
            return []
        
        try:
            # Serialize all messages
            batch_data = []
            total_size = 0
            
            for message in messages:
                serialized = json.dumps(message.to_dict())
                batch_data.append(serialized)
                total_size += len(serialized.encode('utf-8'))
            
            # Simulate batched send (more efficient than individual sends)
            await asyncio.sleep(0.002 * len(messages))  # 2ms per message in batch
            
            # Update metrics
            self._metrics["messages_sent"] += len(messages)
            self._metrics["bytes_sent"] += total_size
            self._metrics["batch_count"] += 1
            
            self.logger.info(
                "Message batch sent to Kafka",
                topic=topic,
                batch_size=len(messages),
                total_bytes=total_size,
                avg_message_size=total_size // len(messages)
            )
            
            return [True] * len(messages)
            
        except Exception as e:
            self._metrics["send_errors"] += len(messages)
            self.logger.error(
                "Failed to send message batch",
                topic=topic,
                batch_size=len(messages),
                error=str(e)
            )
            return [False] * len(messages)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get producer performance metrics"""
        return {
            **self._metrics,
            "messages_per_batch": (self._metrics["messages_sent"] / self._metrics["batch_count"]) 
                                 if self._metrics["batch_count"] > 0 else 0,
            "avg_message_size": (self._metrics["bytes_sent"] / self._metrics["messages_sent"]) 
                               if self._metrics["messages_sent"] > 0 else 0
        }

class KafkaMessageConsumer:
    """Scalable Kafka message consumer with consumer groups"""
    
    def __init__(self, bootstrap_servers: List[str], group_id: str, 
                 client_id: str, max_poll_records: int = 500):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.client_id = client_id
        self.max_poll_records = max_poll_records
        self._consumer: Optional[Any] = None
        self._running = False
        self._committed_offsets: Dict[str, int] = {}
        self._metrics = {
            "messages_consumed": 0,
            "bytes_consumed": 0,
            "processing_errors": 0,
            "commits": 0
        }
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize Kafka consumer with optimizations"""
        self._consumer = {
            "active": True,
            "group_id": self.group_id,
            "client_id": self.client_id,
            "config": {
                "bootstrap_servers": self.bootstrap_servers,
                "auto_offset_reset": "earliest",
                "enable_auto_commit": False,  # Manual commit for better control
                "max_poll_records": self.max_poll_records,
                "fetch_min_bytes": 1024,     # Wait for at least 1KB
                "fetch_max_wait_ms": 500     # Or 500ms timeout
            },
            "subscribed_topics": []
        }
        
        self.logger.info(
            "Kafka consumer initialized",
            group_id=self.group_id,
            client_id=self.client_id,
            servers=self.bootstrap_servers
        )
    
    async def consume_messages(self, topics: List[str], 
                             handler: Callable[[Message], None]) -> None:
        """Consume messages from topics with automatic retries"""
        if not self._consumer or not self._consumer.get("active"):
            raise RuntimeError("Consumer not initialized")
        
        self._consumer["subscribed_topics"] = topics
        self._running = True
        
        self.logger.info(
            "Starting message consumption",
            topics=topics,
            group_id=self.group_id
        )
        
        try:
            while self._running:
                # Simulate polling for messages
                await asyncio.sleep(0.1)  # Poll interval
                
                # Generate simulated messages for demonstration
                messages = await self._poll_messages(topics)
                
                for message in messages:
                    try:
                        # Process message with handler
                        await self._process_message(message, handler)
                        
                        # Auto-commit after successful processing
                        await self.commit_offset(message.id)
                        
                    except Exception as e:
                        self._metrics["processing_errors"] += 1
                        self.logger.error(
                            "Message processing failed",
                            message_id=message.id,
                            topic=message.topic,
                            error=str(e)
                        )
                        
                        # Handle retry logic or dead letter queue
                        await self._handle_processing_error(message, e)
                
        except Exception as e:
            self.logger.error("Consumer error", error=str(e))
        finally:
            self._running = False
    
    async def _poll_messages(self, topics: List[str]) -> List[Message]:
        """Poll messages from Kafka topics"""
        # Simulate message polling with variable message volume
        if not hasattr(self, '_message_counter'):
            self._message_counter = 0
        
        # Generate 0-5 messages per poll for demonstration
        message_count = min(5, max(0, 3 + (self._message_counter % 7) - 3))
        messages = []
        
        for i in range(message_count):
            self._message_counter += 1
            topic = topics[self._message_counter % len(topics)]
            
            # Create simulated message based on topic
            if "document" in topic:
                payload = {
                    "document_id": f"doc_{self._message_counter}",
                    "filename": f"document_{self._message_counter}.pdf",
                    "size_bytes": 1024 * (self._message_counter % 100 + 1),
                    "user_id": f"user_{self._message_counter % 50}"
                }
            elif "experiment" in topic:
                payload = {
                    "experiment_id": f"exp_{self._message_counter}",
                    "user_id": f"user_{self._message_counter % 1000}",
                    "variant": ["control", "treatment_a", "treatment_b"][self._message_counter % 3],
                    "conversion": self._message_counter % 10 == 0
                }
            else:
                payload = {"data": f"message_{self._message_counter}"}
            
            message = Message(
                topic=topic,
                payload=payload,
                correlation_id=f"corr_{self._message_counter}"
            )
            messages.append(message)
        
        if messages:
            total_bytes = sum(len(json.dumps(msg.to_dict()).encode('utf-8')) for msg in messages)
            self._metrics["messages_consumed"] += len(messages)
            self._metrics["bytes_consumed"] += total_bytes
        
        return messages
    
    async def _process_message(self, message: Message, 
                             handler: Callable[[Message], None]) -> None:
        """Process individual message with timing"""
        start_time = time.time()
        
        # Call the message handler
        if asyncio.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)
        
        processing_time = (time.time() - start_time) * 1000
        
        self.logger.debug(
            "Message processed successfully",
            message_id=message.id,
            topic=message.topic,
            processing_time_ms=processing_time
        )
    
    async def _handle_processing_error(self, message: Message, error: Exception) -> None:
        """Handle message processing errors with retry logic"""
        message.retry_count += 1
        
        if message.retry_count <= message.max_retries:
            # Retry with exponential backoff
            delay = min(300, 2 ** message.retry_count)  # Max 5 minutes
            
            self.logger.warning(
                "Retrying message processing",
                message_id=message.id,
                retry_count=message.retry_count,
                delay_seconds=delay
            )
            
            # In real implementation: schedule retry or send to retry topic
            await asyncio.sleep(delay)
        else:
            # Send to dead letter queue
            self.logger.error(
                "Message exceeded max retries, sending to DLQ",
                message_id=message.id,
                max_retries=message.max_retries,
                final_error=str(error)
            )
            
            # In real implementation: send to dead letter topic
    
    async def commit_offset(self, message_id: str) -> None:
        """Commit message processing offset"""
        # Simulate offset commit
        self._committed_offsets[message_id] = int(time.time())
        self._metrics["commits"] += 1
        
        self.logger.debug("Offset committed", message_id=message_id)
    
    def stop(self):
        """Stop consuming messages"""
        self._running = False
        self.logger.info("Consumer stop requested")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get consumer performance metrics"""
        return {
            **self._metrics,
            "avg_message_size": (self._metrics["bytes_consumed"] / self._metrics["messages_consumed"]) 
                               if self._metrics["messages_consumed"] > 0 else 0,
            "error_rate": (self._metrics["processing_errors"] / self._metrics["messages_consumed"]) 
                         if self._metrics["messages_consumed"] > 0 else 0
        }

# =============================================================================
# REDIS TASK QUEUE IMPLEMENTATION
# =============================================================================

class RedisTaskQueue:
    """Redis-based priority task queue with retry mechanisms"""
    
    def __init__(self, redis_url: str, queue_name: str = "tasks"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._redis_client: Optional[Any] = None
        self._task_storage: Dict[str, Message] = {}  # Simulate Redis storage
        self._priority_queues: Dict[MessagePriority, List[Message]] = {
            priority: [] for priority in MessagePriority
        }
        self._processing_tasks: Dict[str, Message] = {}
        self._retry_queue: List[tuple[datetime, Message]] = []
        self._metrics = {
            "tasks_enqueued": 0,
            "tasks_dequeued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0
        }
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize Redis connection"""
        # Simulate Redis client creation
        self._redis_client = {
            "active": True,
            "url": self.redis_url,
            "connection_pool": {"size": 10, "max_connections": 50}
        }
        
        # Start retry processor
        asyncio.create_task(self._process_retry_queue())
        
        self.logger.info(
            "Redis task queue initialized",
            queue_name=self.queue_name,
            redis_url=self.redis_url
        )
    
    async def enqueue_task(self, task_name: str, payload: Dict[str, Any],
                          priority: MessagePriority = MessagePriority.NORMAL) -> str:
        """Enqueue task with priority handling"""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized")
        
        task_id = str(uuid.uuid4())
        message = Message(
            id=task_id,
            topic=task_name,
            payload=payload,
            priority=priority,
            headers={"task_type": task_name, "enqueued_at": str(time.time())}
        )
        
        # Store task data
        self._task_storage[task_id] = message
        
        # Add to priority queue (using heapq for efficient priority handling)
        heapq.heappush(
            self._priority_queues[priority],
            (-priority.value, time.time(), message)  # Negative for max-heap behavior
        )
        
        self._metrics["tasks_enqueued"] += 1
        
        self.logger.info(
            "Task enqueued",
            task_id=task_id,
            task_name=task_name,
            priority=priority.name,
            payload_size=len(json.dumps(payload))
        )
        
        return task_id
    
    async def dequeue_task(self, worker_id: str) -> Optional[Message]:
        """Dequeue highest priority task available"""
        if not self._redis_client:
            raise RuntimeError("Redis client not initialized")
        
        # Check priority queues from highest to lowest priority
        for priority in sorted(MessagePriority, key=lambda x: x.value, reverse=True):
            queue = self._priority_queues[priority]
            
            if queue:
                # Get highest priority task
                _, enqueue_time, message = heapq.heappop(queue)
                
                # Move to processing state
                self._processing_tasks[message.id] = message
                message.headers["worker_id"] = worker_id
                message.headers["dequeued_at"] = str(time.time())
                
                self._metrics["tasks_dequeued"] += 1
                
                self.logger.info(
                    "Task dequeued",
                    task_id=message.id,
                    task_name=message.topic,
                    worker_id=worker_id,
                    priority=priority.name,
                    queue_time_ms=(time.time() - enqueue_time) * 1000
                )
                
                return message
        
        return None  # No tasks available
    
    async def complete_task(self, task_id: str, result: TaskResult) -> None:
        """Mark task as completed successfully"""
        if task_id not in self._processing_tasks:
            self.logger.warning("Task not found in processing state", task_id=task_id)
            return
        
        message = self._processing_tasks.pop(task_id)
        self._task_storage.pop(task_id, None)
        
        if result.success:
            self._metrics["tasks_completed"] += 1
            self.logger.info(
                "Task completed successfully",
                task_id=task_id,
                task_name=message.topic,
                execution_time_ms=result.execution_time_ms,
                worker_id=result.worker_id
            )
        else:
            self._metrics["tasks_failed"] += 1
            self.logger.error(
                "Task completed with failure",
                task_id=task_id,
                task_name=message.topic,
                error=result.error,
                worker_id=result.worker_id
            )
    
    async def retry_task(self, task_id: str, delay_seconds: int = 0) -> None:
        """Retry failed task with optional delay"""
        if task_id not in self._processing_tasks:
            self.logger.warning("Task not found in processing state for retry", task_id=task_id)
            return
        
        message = self._processing_tasks.pop(task_id)
        message.retry_count += 1
        
        if message.retry_count > message.max_retries:
            # Send to dead letter queue
            self.logger.error(
                "Task exceeded max retries, moving to DLQ",
                task_id=task_id,
                retry_count=message.retry_count,
                max_retries=message.max_retries
            )
            self._metrics["tasks_failed"] += 1
            return
        
        # Schedule retry
        retry_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
        self._retry_queue.append((retry_time, message))
        
        self._metrics["tasks_retried"] += 1
        
        self.logger.warning(
            "Task scheduled for retry",
            task_id=task_id,
            retry_count=message.retry_count,
            delay_seconds=delay_seconds,
            retry_time=retry_time.isoformat()
        )
    
    async def _process_retry_queue(self):
        """Background processor for handling task retries"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Process all ready retries
                ready_retries = []
                remaining_retries = []
                
                for retry_time, message in self._retry_queue:
                    if retry_time <= current_time:
                        ready_retries.append(message)
                    else:
                        remaining_retries.append((retry_time, message))
                
                self._retry_queue = remaining_retries
                
                # Re-enqueue ready tasks
                for message in ready_retries:
                    heapq.heappush(
                        self._priority_queues[message.priority],
                        (-message.priority.value, time.time(), message)
                    )
                    
                    self.logger.info(
                        "Task re-enqueued from retry queue",
                        task_id=message.id,
                        retry_count=message.retry_count
                    )
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error("Retry queue processor error", error=str(e))
                await asyncio.sleep(5)  # Back off on errors
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics and metrics"""
        total_queued = sum(len(queue) for queue in self._priority_queues.values())
        
        priority_stats = {}
        for priority, queue in self._priority_queues.items():
            priority_stats[priority.name] = len(queue)
        
        return {
            "total_queued_tasks": total_queued,
            "processing_tasks": len(self._processing_tasks),
            "retry_queue_size": len(self._retry_queue),
            "priority_breakdown": priority_stats,
            "metrics": self._metrics
        }

# =============================================================================
# TASK WORKER IMPLEMENTATION
# =============================================================================

class TaskWorker:
    """Generic task worker for processing background jobs"""
    
    def __init__(self, worker_id: str, task_queue: TaskQueue):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self._task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._current_task: Optional[Message] = None
        self._stats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "total_execution_time_ms": 0
        }
        self.logger = logging.getLogger(__name__)
    
    def register_handler(self, task_name: str, handler: Callable):
        """Register handler function for specific task type"""
        self._task_handlers[task_name] = handler
        self.logger.info(
            "Task handler registered",
            worker_id=self.worker_id,
            task_name=task_name,
            handler=handler.__name__
        )
    
    async def start(self):
        """Start worker process"""
        if self._running:
            return
        
        self._running = True
        self.logger.info("Task worker started", worker_id=self.worker_id)
        
        try:
            while self._running:
                # Dequeue next task
                task = await self.task_queue.dequeue_task(self.worker_id)
                
                if task:
                    await self._process_task(task)
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            self.logger.error("Worker error", worker_id=self.worker_id, error=str(e))
        finally:
            self._running = False
            self.logger.info("Task worker stopped", worker_id=self.worker_id)
    
    async def _process_task(self, task: Message):
        """Process individual task with error handling"""
        self._current_task = task
        start_time = time.time()
        
        try:
            # Find appropriate handler
            handler = self._task_handlers.get(task.topic)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.topic}")
            
            self.logger.info(
                "Processing task",
                worker_id=self.worker_id,
                task_id=task.id,
                task_type=task.topic,
                retry_count=task.retry_count
            )
            
            # Execute task handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                result = handler(task.payload)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Mark task as completed
            task_result = TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                execution_time_ms=execution_time_ms,
                worker_id=self.worker_id
            )
            
            await self.task_queue.complete_task(task.id, task_result)
            
            # Update stats
            self._stats["tasks_processed"] += 1
            self._stats["tasks_succeeded"] += 1
            self._stats["total_execution_time_ms"] += execution_time_ms
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.logger.error(
                "Task processing failed",
                worker_id=self.worker_id,
                task_id=task.id,
                task_type=task.topic,
                error=str(e),
                execution_time_ms=execution_time_ms
            )
            
            # Mark task as failed
            task_result = TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
                worker_id=self.worker_id
            )
            
            await self.task_queue.complete_task(task.id, task_result)
            
            # Retry task if not exceeded max retries
            if task.retry_count < task.max_retries:
                retry_delay = min(300, 2 ** task.retry_count)  # Exponential backoff
                await self.task_queue.retry_task(task.id, retry_delay)
            
            # Update stats
            self._stats["tasks_processed"] += 1
            self._stats["tasks_failed"] += 1
            self._stats["total_execution_time_ms"] += execution_time_ms
        
        finally:
            self._current_task = None
    
    def stop(self):
        """Stop worker gracefully"""
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        processed = self._stats["tasks_processed"]
        return {
            **self._stats,
            "success_rate": (self._stats["tasks_succeeded"] / processed) if processed > 0 else 0,
            "avg_execution_time_ms": (self._stats["total_execution_time_ms"] / processed) if processed > 0 else 0,
            "current_task": self._current_task.id if self._current_task else None,
            "running": self._running
        }

# =============================================================================
# BUSINESS TASK HANDLERS
# =============================================================================

async def document_processing_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for document processing tasks (Lawstronaut scenario)"""
    document_id = payload["document_id"]
    filename = payload["filename"]
    
    # Simulate document processing with variable execution time
    processing_time = 0.5 + (hash(document_id) % 100) / 200.0  # 0.5-1.0 seconds
    await asyncio.sleep(processing_time)
    
    # Simulate occasional processing failures
    if "fail" in filename.lower():
        raise RuntimeError("Document processing failed: corrupted file")
    
    return {
        "document_id": document_id,
        "status": "processed",
        "extracted_text_size": len(filename) * 100,  # Simulated text size
        "processing_time_seconds": processing_time
    }

async def experiment_analysis_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for experiment analysis tasks (Optimizely scenario)"""
    experiment_id = payload["experiment_id"]
    user_count = payload.get("user_count", 1000)
    
    # Simulate statistical analysis with computation time
    analysis_time = 0.2 + (user_count / 10000.0)  # Scale with user count
    await asyncio.sleep(analysis_time)
    
    # Calculate simulated results
    control_conversion = 0.12 + (hash(experiment_id) % 100) / 10000.0
    treatment_conversion = control_conversion * (1.1 + (hash(experiment_id) % 20) / 100.0)
    
    statistical_significance = abs(treatment_conversion - control_conversion) > 0.02
    
    return {
        "experiment_id": experiment_id,
        "control_conversion_rate": round(control_conversion, 4),
        "treatment_conversion_rate": round(treatment_conversion, 4),
        "statistical_significance": statistical_significance,
        "confidence_interval": 0.95,
        "analysis_time_seconds": analysis_time
    }

def notification_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for notification tasks (synchronous example)"""
    user_id = payload["user_id"]
    message = payload["message"]
    notification_type = payload.get("type", "email")
    
    # Simulate notification sending
    time.sleep(0.1)
    
    return {
        "user_id": user_id,
        "notification_id": str(uuid.uuid4()),
        "type": notification_type,
        "status": "sent",
        "sent_at": datetime.utcnow().isoformat()
    }

# =============================================================================
# INTEGRATION AND DEMONSTRATION
# =============================================================================

async def demonstrate_message_queues():
    """
    Comprehensive demonstration of message queue integration patterns
    including Kafka and Redis with various use cases.
    """
    
    print("=== Message Queue Integration with Kafka and Redis ===\n")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("1. System Components:")
    print("   - Kafka: High-throughput event streaming")
    print("   - Redis: Priority task queues with retry mechanisms")
    print("   - Task Workers: Background job processing")
    print("   - Dead Letter Queues: Failed message handling")
    
    # Initialize Kafka components
    print("\n2. Initializing Kafka Producer/Consumer:")
    
    kafka_producer = KafkaMessageProducer(
        bootstrap_servers=["localhost:9092"],
        client_id="lawstronaut-producer"
    )
    await kafka_producer.initialize()
    
    kafka_consumer = KafkaMessageConsumer(
        bootstrap_servers=["localhost:9092"],
        group_id="document-processors",
        client_id="lawstronaut-consumer"
    )
    await kafka_consumer.initialize()
    
    # Initialize Redis task queue
    print("3. Initializing Redis Task Queue:")
    
    redis_queue = RedisTaskQueue(
        redis_url="redis://localhost:6379",
        queue_name="background_tasks"
    )
    await redis_queue.initialize()
    
    # Create and configure task workers
    print("4. Setting up Task Workers:")
    
    worker1 = TaskWorker("worker_1", redis_queue)
    worker1.register_handler("document_processing", document_processing_handler)
    worker1.register_handler("send_notification", notification_handler)
    
    worker2 = TaskWorker("worker_2", redis_queue)
    worker2.register_handler("experiment_analysis", experiment_analysis_handler)
    worker2.register_handler("send_notification", notification_handler)
    
    # Start workers
    asyncio.create_task(worker1.start())
    asyncio.create_task(worker2.start())
    
    # Demonstrate Kafka streaming
    print("\n5. Testing Kafka Event Streaming:")
    
    # Create message handler for Kafka
    processed_messages = []
    
    async def kafka_message_handler(message: Message):
        processed_messages.append(message)
        print(f"   - Processed Kafka message: {message.id} from topic {message.topic}")
    
    # Start consumer (in real app, this would be a separate process)
    consumer_task = asyncio.create_task(
        kafka_consumer.consume_messages(
            ["document_events", "experiment_events"],
            kafka_message_handler
        )
    )
    
    # Send batch of messages to Kafka
    kafka_messages = []
    for i in range(5):
        message = Message(
            topic="document_events",
            payload={
                "event_type": "document_uploaded",
                "document_id": f"doc_{i+1}",
                "filename": f"legal_document_{i+1}.pdf",
                "user_id": f"user_{i+1}"
            },
            priority=MessagePriority.NORMAL
        )
        kafka_messages.append(message)
    
    results = await kafka_producer.send_batch("document_events", kafka_messages)
    print(f"   - Sent {sum(results)} messages to Kafka successfully")
    
    # Wait for message processing
    await asyncio.sleep(2.0)
    
    # Demonstrate Redis task queuing
    print("\n6. Testing Redis Task Queue:")
    
    # Enqueue various tasks with different priorities
    task_ids = []
    
    # High priority document processing
    task_id = await redis_queue.enqueue_task(
        "document_processing",
        {
            "document_id": "urgent_doc_1",
            "filename": "urgent_contract.pdf",
            "user_id": "vip_user"
        },
        MessagePriority.HIGH
    )
    task_ids.append(task_id)
    print(f"   - Enqueued high priority task: {task_id}")
    
    # Normal priority experiment analysis
    task_id = await redis_queue.enqueue_task(
        "experiment_analysis",
        {
            "experiment_id": "exp_conversion_test",
            "user_count": 5000
        },
        MessagePriority.NORMAL
    )
    task_ids.append(task_id)
    print(f"   - Enqueued experiment analysis: {task_id}")
    
    # Low priority notifications
    for i in range(3):
        task_id = await redis_queue.enqueue_task(
            "send_notification",
            {
                "user_id": f"user_{i+10}",
                "message": f"Your document has been processed",
                "type": "email"
            },
            MessagePriority.LOW
        )
        task_ids.append(task_id)
    
    print(f"   - Enqueued 3 low priority notification tasks")
    
    # Demonstrate failure and retry
    print("\n7. Testing Failure Handling and Retries:")
    
    # Enqueue a task that will fail
    fail_task_id = await redis_queue.enqueue_task(
        "document_processing",
        {
            "document_id": "fail_doc_1",
            "filename": "fail_corrupted_file.pdf",  # This will trigger failure
            "user_id": "test_user"
        },
        MessagePriority.NORMAL
    )
    print(f"   - Enqueued task that will fail: {fail_task_id}")
    
    # Wait for task processing
    await asyncio.sleep(5.0)
    
    # Display results and metrics
    print("\n8. Performance Metrics:")
    
    # Kafka metrics
    kafka_producer_metrics = kafka_producer.get_metrics()
    kafka_consumer_metrics = kafka_consumer.get_metrics()
    
    print("   Kafka Producer:")
    print(f"     - Messages sent: {kafka_producer_metrics['messages_sent']}")
    print(f"     - Bytes sent: {kafka_producer_metrics['bytes_sent']:,}")
    print(f"     - Average message size: {kafka_producer_metrics['avg_message_size']:.1f} bytes")
    
    print("   Kafka Consumer:")
    print(f"     - Messages consumed: {kafka_consumer_metrics['messages_consumed']}")
    print(f"     - Processing errors: {kafka_consumer_metrics['processing_errors']}")
    print(f"     - Error rate: {kafka_consumer_metrics['error_rate']*100:.1f}%")
    
    # Redis queue metrics
    queue_stats = redis_queue.get_queue_stats()
    print("   Redis Task Queue:")
    print(f"     - Total queued: {queue_stats['total_queued_tasks']}")
    print(f"     - Processing: {queue_stats['processing_tasks']}")
    print(f"     - In retry queue: {queue_stats['retry_queue_size']}")
    print(f"     - Tasks completed: {queue_stats['metrics']['tasks_completed']}")
    print(f"     - Tasks failed: {queue_stats['metrics']['tasks_failed']}")
    print(f"     - Tasks retried: {queue_stats['metrics']['tasks_retried']}")
    
    # Worker metrics
    worker1_stats = worker1.get_stats()
    worker2_stats = worker2.get_stats()
    
    print("   Worker 1 Stats:")
    print(f"     - Tasks processed: {worker1_stats['tasks_processed']}")
    print(f"     - Success rate: {worker1_stats['success_rate']*100:.1f}%")
    print(f"     - Avg execution time: {worker1_stats['avg_execution_time_ms']:.1f}ms")
    
    print("   Worker 2 Stats:")
    print(f"     - Tasks processed: {worker2_stats['tasks_processed']}")
    print(f"     - Success rate: {worker2_stats['success_rate']*100:.1f}%")
    print(f"     - Avg execution time: {worker2_stats['avg_execution_time_ms']:.1f}ms")
    
    print("\n9. Key Benefits Demonstrated:")
    print("   - High-throughput event streaming with Kafka")
    print("   - Priority-based task processing with Redis")
    print("   - Automatic retry mechanisms with exponential backoff")
    print("   - Worker scaling and load distribution")
    print("   - Comprehensive monitoring and metrics")
    print("   - Graceful error handling and dead letter queues")
    
    print("\n10. Production Considerations:")
    print("   - Message schema evolution and compatibility")
    print("   - Consumer group management and rebalancing")
    print("   - Task queue monitoring and alerting")
    print("   - Dead letter queue analysis and replay")
    print("   - Backpressure handling and flow control")
    print("   - Security (authentication, authorization, encryption)")
    
    # Cleanup
    kafka_consumer.stop()
    worker1.stop()
    worker2.stop()
    
    # Wait for graceful shutdown
    await asyncio.sleep(1.0)
    
    print("\n=== Message queue integration demonstration completed ===")

if __name__ == "__main__":
    asyncio.run(demonstrate_message_queues())
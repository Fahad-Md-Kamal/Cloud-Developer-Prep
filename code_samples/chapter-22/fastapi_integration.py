"""
FastAPI Production Integration for Conversational AI Systems

This module demonstrates FastAPI integration patterns for conversational AI
systems in production environments like those at Lawstronaut and Optimizely.

Key concepts covered:
- WebSocket connections for real-time conversations
- Streaming response handling for long-form content
- Authentication and session management
- Rate limiting and performance optimization
- Error handling and monitoring integration

Real-world applications:
- Legal consultation API for Lawstronaut
- Real-time personalization API for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
import time
import logging
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# FastAPI and related imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
import uvicorn

# Mock external dependencies (in real implementation, use actual libraries)
class RedisPool:
    async def get(self, key: str) -> Optional[str]:
        return f"cached_value_for_{key}"
    
    async def set(self, key: str, value: str, expire: int = 3600):
        pass

class DatabasePool:
    async def execute(self, query: str, params: List[Any] = None) -> List[Dict]:
        return [{"id": 1, "result": "mock_data"}]

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationMessage(BaseModel):
    """Model for individual conversation messages"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationRequest(BaseModel):
    """Request model for conversation API"""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "message": "What are the key GDPR compliance requirements?",
                "session_id": "session_123",
                "context": {"domain": "legal", "jurisdiction": "EU"},
                "stream": True
            }
        }

class ConversationResponse(BaseModel):
    """Response model for conversation API"""
    message: str
    session_id: str
    response_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "message": "GDPR requires explicit consent for data processing...",
                "session_id": "session_123",
                "response_time_ms": 1500,
                "metadata": {"confidence": 0.95, "sources": ["GDPR Article 6"]}
            }
        }

class StreamChunk(BaseModel):
    """Model for streaming response chunks"""
    chunk: str
    chunk_id: int
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@dataclass
class ConversationSession:
    """Manages conversation state and context"""
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    messages: List[ConversationMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict] = None):
        """Add a message to the session"""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_context_window(self, max_messages: int = 10) -> List[ConversationMessage]:
        """Get recent conversation context"""
        return self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session has expired"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

class SessionManager:
    """Manages conversation sessions with Redis backend"""
    
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
        self.sessions: Dict[str, ConversationSession] = {}  # In-memory fallback
        self.logger = logging.getLogger(__name__)
    
    async def create_session(self, user_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        await self._store_session(session)
        self.logger.info(f"Created session: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve conversation session"""
        # Try in-memory cache first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if not session.is_expired():
                return session
        
        # Try Redis if not in memory or expired
        session_data = await self.redis_pool.get(f"session:{session_id}")
        if session_data:
            try:
                # In real implementation, deserialize from JSON
                # session = ConversationSession.from_dict(json.loads(session_data))
                # For demo, create a mock session
                session = ConversationSession(
                    session_id=session_id,
                    user_id="demo_user",
                    created_at=datetime.now() - timedelta(minutes=30),
                    last_activity=datetime.now() - timedelta(minutes=5)
                )
                self.sessions[session_id] = session
                return session
            except (json.JSONDecodeError, ValidationError):
                self.logger.error(f"Failed to deserialize session: {session_id}")
        
        return None
    
    async def _store_session(self, session: ConversationSession):
        """Store session in Redis and memory"""
        self.sessions[session.session_id] = session
        # In real implementation: await self.redis_pool.set(f"session:{session.session_id}", session.to_json())
        await self.redis_pool.set(f"session:{session.session_id}", "session_data")
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            self.logger.info(f"Cleaned up expired session: {session_id}")

# =============================================================================
# RATE LIMITING AND SECURITY
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, redis_pool: RedisPool):
        self.redis_pool = redis_pool
        self.requests: Dict[str, List[datetime]] = {}  # In-memory fallback
    
    async def is_allowed(self, client_id: str, max_requests: int = 60, window_minutes: int = 1) -> bool:
        """Check if request is allowed within rate limits"""
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > window_start
            ]
        else:
            self.requests[client_id] = []
        
        # Check rate limit
        if len(self.requests[client_id]) >= max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True

security = HTTPBearer()

async def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Authenticate user from JWT token"""
    # In real implementation, validate JWT token
    token = credentials.credentials
    
    # Mock authentication
    if token.startswith("demo_"):
        return token.replace("demo_", "user_")
    
    raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_client_ip(request: Request) -> str:
    """Extract client IP for rate limiting"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host

# =============================================================================
# CONVERSATIONAL AI SERVICE
# =============================================================================

class ConversationalAIService:
    """Service for handling conversational AI interactions"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_message(self, request: ConversationRequest, user_id: str) -> ConversationResponse:
        """Process a conversation message"""
        start_time = time.time()
        
        # Get or create session
        session = None
        if request.session_id:
            session = await self.session_manager.get_session(request.session_id)
        
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        # Add user message to session
        session.add_message(MessageRole.USER, request.message)
        
        # Process with mock AI (in real implementation, integrate with LangChain agent)
        response_content = await self._generate_response(request.message, session)
        
        # Add assistant response to session
        session.add_message(MessageRole.ASSISTANT, response_content)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return ConversationResponse(
            message=response_content,
            session_id=session.session_id,
            response_time_ms=response_time_ms,
            metadata={
                "message_count": len(session.messages),
                "user_id": user_id
            }
        )
    
    async def _generate_response(self, message: str, session: ConversationSession) -> str:
        """Generate AI response (mock implementation)"""
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        message_lower = message.lower()
        
        # Legal domain responses (Lawstronaut scenario)
        if any(term in message_lower for term in ["legal", "gdpr", "compliance", "contract"]):
            legal_responses = [
                "Based on current EU regulations, GDPR compliance requires explicit user consent for data processing. Key requirements include data minimization, purpose limitation, and the right to erasure.",
                "Contract liability in EU jurisdictions requires careful attention to unfair terms regulations. Standard contract clauses must be clearly readable and not create significant imbalance.",
                "For legal compliance, I recommend reviewing Articles 6 and 7 of GDPR for lawful basis of processing, and implementing proper consent management systems."
            ]
            return legal_responses[len(session.messages) % len(legal_responses)]
        
        # Personalization domain responses (Optimizely scenario)
        elif any(term in message_lower for term in ["personalization", "user", "behavior", "analytics"]):
            personalization_responses = [
                "For effective personalization, focus on behavioral signals like page engagement time, content interaction patterns, and conversion funnel progression. A/B testing is crucial for validating personalization strategies.",
                "User behavior analysis shows that personalized content increases engagement by 35% on average. Key metrics to track include click-through rates, session duration, and conversion rates by user segment.",
                "Implementing real-time personalization requires robust data pipelines and low-latency decision engines. Consider using feature stores for consistent feature engineering across batch and streaming workflows."
            ]
            return personalization_responses[len(session.messages) % len(personalization_responses)]
        
        # General responses
        return f"I understand you're asking about '{message}'. Based on our conversation history, I can provide more specific guidance if you let me know whether this relates to legal compliance, user personalization, or another specific domain."
    
    async def stream_response(self, request: ConversationRequest, user_id: str) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming response for long-form content"""
        # Get or create session
        session = None
        if request.session_id:
            session = await self.session_manager.get_session(request.session_id)
        
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        # Add user message
        session.add_message(MessageRole.USER, request.message)
        
        # Generate streaming response
        response_parts = [
            "Let me provide you with a comprehensive response.",
            "First, I'll analyze your query for key requirements.",
            "Based on your question, I can see this relates to enterprise-level concerns.",
            "Here are the specific recommendations I have for your situation:",
            "1. Consider the regulatory compliance aspects",
            "2. Evaluate the technical implementation requirements", 
            "3. Plan for scalability and performance optimization",
            "4. Implement proper monitoring and observability",
            "This approach ensures both immediate needs and long-term success."
        ]
        
        full_response = []
        
        for i, part in enumerate(response_parts):
            # Simulate processing delay
            await asyncio.sleep(0.3)
            
            chunk = StreamChunk(
                chunk=part + " ",
                chunk_id=i,
                is_final=(i == len(response_parts) - 1)
            )
            
            full_response.append(part)
            yield chunk
        
        # Add complete response to session
        session.add_message(MessageRole.ASSISTANT, " ".join(full_response))

# =============================================================================
# WEBSOCKET HANDLERS
# =============================================================================

class WebSocketManager:
    """Manages WebSocket connections for real-time chat"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.active_connections: Dict[str, WebSocket] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            self.logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific WebSocket"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to send WebSocket message: {e}")
                self.disconnect(session_id)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to broadcast to {session_id}: {e}")

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

# Global dependencies
redis_pool = RedisPool()
session_manager = SessionManager(redis_pool)
rate_limiter = RateLimiter(redis_pool)
ai_service = ConversationalAIService(session_manager)
websocket_manager = WebSocketManager(session_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logging.info("Starting Conversational AI API")
    
    # Setup background tasks for session cleanup
    async def cleanup_task():
        while True:
            await asyncio.sleep(300)  # Run every 5 minutes
            await session_manager.cleanup_expired_sessions()
    
    cleanup_task_handle = asyncio.create_task(cleanup_task())
    
    yield
    
    # Shutdown
    cleanup_task_handle.cancel()
    logging.info("Shutting down Conversational AI API")

# Create FastAPI application
app = FastAPI(
    title="Conversational AI API",
    description="Production-ready conversational AI system for enterprise applications",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.lawstronaut.com", "https://app.optimizely.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.lawstronaut.com", "api.optimizely.com", "localhost", "127.0.0.1"]
)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for load balancers"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        services={
            "redis": "connected",
            "database": "connected",
            "ai_service": "ready"
        }
    )

@app.post("/conversation", response_model=ConversationResponse)
async def conversation_endpoint(
    request: ConversationRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(authenticate_user),
    client_ip: str = Depends(get_client_ip)
):
    """
    Process conversation message and return AI response
    
    - **message**: The user's message (required)
    - **session_id**: Optional session ID for conversation continuity
    - **context**: Optional context dictionary for domain-specific processing
    - **stream**: Whether to use streaming response (use /conversation/stream for streaming)
    """
    
    # Rate limiting
    if not await rate_limiter.is_allowed(client_ip, max_requests=30):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        response = await ai_service.process_message(request, user_id)
        
        # Background task for analytics
        background_tasks.add_task(log_conversation_analytics, user_id, request, response)
        
        return response
    
    except Exception as e:
        logging.error(f"Conversation processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/conversation/stream")
async def conversation_stream_endpoint(
    request: ConversationRequest,
    user_id: str = Depends(authenticate_user),
    client_ip: str = Depends(get_client_ip)
):
    """
    Process conversation message with streaming response
    
    Returns Server-Sent Events (SSE) stream for real-time response generation
    """
    
    # Rate limiting
    if not await rate_limiter.is_allowed(client_ip, max_requests=10):
        raise HTTPException(status_code=429, detail="Rate limit exceeded") 
    
    async def generate_stream():
        try:
            async for chunk in ai_service.stream_response(request, user_id):
                yield f"data: {chunk.json()}\n\n"
        except Exception as e:
            logging.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': 'Stream processing failed'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time conversation
    
    Enables bidirectional real-time communication for interactive chat experiences
    """
    
    await websocket_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process conversation request
            request = ConversationRequest(**data)
            
            # Mock user authentication for WebSocket (in real implementation, validate session)
            user_id = f"ws_user_{session_id}"
            
            # Send typing indicator
            await websocket_manager.send_message(session_id, {
                "type": "typing",
                "message": "AI is thinking..."
            })
            
            # Process message
            response = await ai_service.process_message(request, user_id)
            
            # Send response
            await websocket_manager.send_message(session_id, {
                "type": "message",
                "content": response.dict()
            })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(session_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(session_id)

@app.get("/sessions/{session_id}")
async def get_session_endpoint(
    session_id: str,
    user_id: str = Depends(authenticate_user)
):
    """
    Retrieve conversation session information
    """
    
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Authorization check (in real implementation, verify user ownership)
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "last_activity": session.last_activity,
        "message_count": len(session.messages),
        "context": session.context
    }

# =============================================================================
# BACKGROUND TASKS AND MONITORING
# =============================================================================

async def log_conversation_analytics(user_id: str, request: ConversationRequest, response: ConversationResponse):
    """Background task for logging conversation analytics"""
    analytics_data = {
        "user_id": user_id,
        "session_id": response.session_id,
        "message_length": len(request.message),
        "response_time_ms": response.response_time_ms,
        "timestamp": datetime.now().isoformat()
    }
    
    # In real implementation, send to analytics service
    logging.info(f"Analytics: {analytics_data}")

# =============================================================================
# DEMONSTRATION FUNCTION
# =============================================================================

async def demonstrate_fastapi_integration():
    """
    Demonstration of FastAPI integration with conversational AI
    for production enterprise systems.
    """
    
    print("🚀 FastAPI Conversational AI Integration Demo")
    print("Production-Ready API for Enterprise Systems")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    # Test conversation processing
    print("\n" + "="*60)
    print("Testing Conversation Processing")
    print("="*60)
    
    # Mock requests
    test_requests = [
        ConversationRequest(
            message="What are the key GDPR compliance requirements?",
            context={"domain": "legal", "jurisdiction": "EU"}
        ),
        ConversationRequest(
            message="How can I improve user personalization on my platform?",
            context={"domain": "personalization", "platform": "web"}
        )
    ]
    
    for i, request in enumerate(test_requests):
        print(f"\n🔍 Test {i+1}: {request.message}")
        print("-" * 50)
        
        start_time = time.time()
        response = await ai_service.process_message(request, f"demo_user_{i}")
        end_time = time.time()
        
        print(f"📋 Response: {response.message[:200]}...")
        print(f"⏱️  Processing time: {end_time - start_time:.2f}s")
        print(f"🔗 Session ID: {response.session_id}")
    
    # Test streaming
    print("\n" + "="*60)
    print("Testing Streaming Responses")
    print("="*60)
    
    stream_request = ConversationRequest(
        message="Give me a comprehensive guide to API security best practices",
        stream=True
    )
    
    print(f"\n🌊 Streaming: {stream_request.message}")
    print("-" * 50)
    
    chunk_count = 0
    async for chunk in ai_service.stream_response(stream_request, "demo_stream_user"):
        print(f"Chunk {chunk.chunk_id}: {chunk.chunk[:50]}...")
        chunk_count += 1
        if chunk.is_final:
            break
    
    print(f"✅ Streamed {chunk_count} chunks successfully")
    
    print("\n" + "="*60)
    print("✅ FastAPI Integration Demo Complete")
    print("="*60)
    
    # Configuration summary
    print(f"\n📊 Production Configuration Summary:")
    print(f"   • CORS enabled for production domains")
    print(f"   • Rate limiting: 30 requests/minute")
    print(f"   • Session management with Redis backend")
    print(f"   • WebSocket support for real-time chat")
    print(f"   • Streaming responses for long content")
    print(f"   • Authentication with JWT tokens")
    print(f"   • Background analytics processing")
    print(f"   • Health checks for load balancers")

if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_fastapi_integration())
    
    # In production, use: uvicorn fastapi_integration:app --host 0.0.0.0 --port 8000 --workers 4
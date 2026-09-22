"""
FastAPI LLM Server with Multi-Provider Support

This module demonstrates a production-ready FastAPI server for LLM services
with comprehensive features for enterprise deployments like those used at
Lawstronaut (legal document processing) and Optimizely (AI-powered customer interactions).

Key concepts covered:
- FastAPI application structure with dependency injection
- Multi-provider LLM integration with failover
- Authentication and rate limiting middleware
- Request/response validation and serialization
- Async request handling and streaming responses
- Comprehensive monitoring and logging

Real-world applications:
- Legal document analysis API service
- Customer service chatbot backend
- Content generation service with usage tracking

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from datetime import datetime, timedelta
from decimal import Decimal
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Pydantic models
from pydantic import BaseModel, Field, validator
from enum import Enum

# Custom imports (these would be your actual modules)
# from multi_provider_llm_client import MultiProviderLLMClient, LLMRequest, LLMResponse, RoutingStrategy
# from cost_optimization_system import CostOptimizationSystem
# from intelligent_caching import IntelligentCacheManager

# =============================================================================
# PYDANTIC MODELS FOR API
# =============================================================================

class LLMProviderEnum(str, Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    VERTEX_AI = "vertex_ai"
    AZURE_OPENAI = "azure_openai"

class RequestPriorityEnum(str, Enum):
    """Request priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class RoutingStrategyEnum(str, Enum):
    """Routing strategies"""
    ROUND_ROBIN = "round_robin"
    LOWEST_LATENCY = "lowest_latency"
    LOWEST_COST = "lowest_cost"
    HIGHEST_SUCCESS_RATE = "highest_success_rate"
    INTELLIGENT_HYBRID = "intelligent_hybrid"

class CompletionRequest(BaseModel):
    """Request model for text completion"""
    prompt: str = Field(..., description="Input prompt for completion", min_length=1, max_length=50000)
    model: str = Field(default="gpt-3.5-turbo", description="Model to use for completion")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate", ge=1, le=8192)
    temperature: float = Field(default=0.7, description="Sampling temperature", ge=0.0, le=2.0)
    stream: bool = Field(default=False, description="Stream response tokens")
    priority: RequestPriorityEnum = Field(default=RequestPriorityEnum.NORMAL, description="Request priority")
    routing_strategy: RoutingStrategyEnum = Field(
        default=RoutingStrategyEnum.INTELLIGENT_HYBRID, 
        description="Provider selection strategy"
    )
    user_id: Optional[str] = Field(default=None, description="User identifier for analytics")
    application: str = Field(default="api", description="Application identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()

class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['user', 'assistant', 'system']:
            raise ValueError('Role must be user, assistant, or system')
        return v

class ChatCompletionRequest(BaseModel):
    """Request model for chat completion"""
    messages: List[ChatMessage] = Field(..., description="List of chat messages", min_items=1)
    model: str = Field(default="gpt-3.5-turbo", description="Model to use for chat completion")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate", ge=1, le=8192)
    temperature: float = Field(default=0.7, description="Sampling temperature", ge=0.0, le=2.0)
    stream: bool = Field(default=False, description="Stream response tokens")
    priority: RequestPriorityEnum = Field(default=RequestPriorityEnum.NORMAL)
    routing_strategy: RoutingStrategyEnum = Field(default=RoutingStrategyEnum.INTELLIGENT_HYBRID)
    user_id: Optional[str] = Field(default=None)
    application: str = Field(default="chat")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('Messages list cannot be empty')
        
        # Ensure at least one user message
        user_messages = [msg for msg in v if msg.role == 'user']
        if not user_messages:
            raise ValueError('At least one user message is required')
        
        return v

class CompletionResponse(BaseModel):
    """Response model for completions"""
    id: str = Field(..., description="Unique response identifier")
    content: str = Field(..., description="Generated content")
    model: str = Field(..., description="Model used for generation")
    provider: str = Field(..., description="Provider used")
    usage: Dict[str, int] = Field(..., description="Token usage information")
    cost: float = Field(..., description="Request cost in USD")
    latency_ms: float = Field(..., description="Response latency in milliseconds")
    quality_score: float = Field(default=1.0, description="Response quality score")
    cached: bool = Field(default=False, description="Whether response was cached")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BatchCompletionRequest(BaseModel):
    """Request model for batch completions"""
    requests: List[CompletionRequest] = Field(..., min_items=1, max_items=100)
    max_concurrent: int = Field(default=10, description="Maximum concurrent requests", ge=1, le=50)
    
class BatchCompletionResponse(BaseModel):
    """Response model for batch completions"""
    responses: List[CompletionResponse]
    summary: Dict[str, Any]

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    providers: Dict[str, bool] = Field(..., description="Provider availability")
    uptime_seconds: float = Field(..., description="Service uptime")
    
class UsageStatsResponse(BaseModel):
    """Usage statistics response"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_cost: float
    average_latency_ms: float
    cache_hit_rate: float
    provider_distribution: Dict[str, int]
    model_distribution: Dict[str, int]
    cost_by_model: Dict[str, float]
    period_start: datetime
    period_end: datetime

# =============================================================================
# AUTHENTICATION AND MIDDLEWARE
# =============================================================================

class APIKeyAuth:
    """API key authentication"""
    
    def __init__(self):
        # In production, store API keys in secure storage
        self.valid_keys = {
            "llm_api_key_demo": {
                "user_id": "demo_user",
                "permissions": ["read", "write"],
                "rate_limit": 1000,  # requests per hour
                "applications": ["legal_analysis", "customer_service", "content_generation"]
            },
            "enterprise_key_123": {
                "user_id": "enterprise_user",
                "permissions": ["read", "write", "admin"],
                "rate_limit": 10000,
                "applications": ["*"]
            }
        }
        self.usage_tracking = {}
    
    def verify_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return user info"""
        return self.valid_keys.get(api_key)
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check if API key is within rate limits"""
        if api_key not in self.valid_keys:
            return False
        
        current_hour = datetime.utcnow().hour
        usage_key = f"{api_key}:{current_hour}"
        
        current_usage = self.usage_tracking.get(usage_key, 0)
        rate_limit = self.valid_keys[api_key]["rate_limit"]
        
        return current_usage < rate_limit
    
    def record_usage(self, api_key: str):
        """Record API usage"""
        current_hour = datetime.utcnow().hour
        usage_key = f"{api_key}:{current_hour}"
        
        self.usage_tracking[usage_key] = self.usage_tracking.get(usage_key, 0) + 1

# Global authentication instance
auth_manager = APIKeyAuth()
security = HTTPBearer()

async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to extract and validate API key"""
    api_key = credentials.credentials
    
    user_info = auth_manager.verify_key(api_key)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not auth_manager.check_rate_limit(api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    auth_manager.record_usage(api_key)
    
    return {
        "api_key": api_key,
        "user_id": user_info["user_id"],
        "permissions": user_info["permissions"],
        "applications": user_info["applications"]
    }

# =============================================================================
# SERVICE LAYER (SIMPLIFIED IMPLEMENTATIONS)
# =============================================================================

class MockLLMProvider:
    """Mock LLM provider for demonstration"""
    
    def __init__(self, name: str):
        self.name = name
        self.available = True
        self.latency_ms = 1000 + hash(name) % 2000  # Simulate different latencies
        
    async def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """Mock completion generation"""
        # Simulate API latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Generate mock response
        content = f"Mock response from {self.name} for prompt: {request.prompt[:50]}..."
        
        return CompletionResponse(
            id=f"mock_{int(time.time())}_{hash(request.prompt) % 10000}",
            content=content,
            model=request.model,
            provider=self.name,
            usage={
                "prompt_tokens": len(request.prompt.split()) * 1.3,
                "completion_tokens": len(content.split()),
                "total_tokens": len(request.prompt.split()) * 1.3 + len(content.split())
            },
            cost=0.01,  # Mock cost
            latency_ms=self.latency_ms,
            quality_score=0.9,
            cached=False
        )
    
    async def stream_completion(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        """Mock streaming completion"""
        content = f"Mock streaming response from {self.name} for: {request.prompt[:30]}..."
        words = content.split()
        
        for word in words:
            await asyncio.sleep(0.1)  # Simulate streaming delay
            yield word + " "

class MockLLMService:
    """Mock LLM service that simulates multi-provider functionality"""
    
    def __init__(self):
        self.providers = {
            "openai": MockLLMProvider("openai"),
            "anthropic": MockLLMProvider("anthropic"),
            "vertex_ai": MockLLMProvider("vertex_ai")
        }
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "total_latency": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = datetime.utcnow()
    
    async def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using mock providers"""
        self.stats["total_requests"] += 1
        
        try:
            # Simple provider selection (normally would use intelligent routing)
            provider = self.providers["openai"]  # Default to OpenAI
            
            response = await provider.generate_completion(request)
            
            # Update statistics
            self.stats["successful_requests"] += 1
            self.stats["total_cost"] += response.cost
            self.stats["total_latency"] += response.latency_ms
            
            return response
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            logging.error(f"Error generating completion: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def stream_completion(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        """Stream completion using mock providers"""
        provider = self.providers["openai"]
        async for chunk in provider.stream_completion(request):
            yield chunk
    
    async def batch_completion(self, requests: List[CompletionRequest], 
                             max_concurrent: int = 10) -> BatchCompletionResponse:
        """Process batch of completion requests"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(req: CompletionRequest) -> CompletionResponse:
            async with semaphore:
                return await self.generate_completion(req)
        
        # Process all requests
        tasks = [process_single(req) for req in requests]
        responses = []
        
        for task in asyncio.as_completed(tasks):
            try:
                response = await task
                responses.append(response)
            except Exception as e:
                logging.error(f"Batch request failed: {e}")
                # Continue processing other requests
        
        # Calculate summary statistics
        total_cost = sum(r.cost for r in responses)
        avg_latency = sum(r.latency_ms for r in responses) / len(responses) if responses else 0
        
        summary = {
            "total_requests": len(requests),
            "successful_responses": len(responses),
            "failed_responses": len(requests) - len(responses),
            "total_cost": total_cost,
            "average_latency_ms": avg_latency
        }
        
        return BatchCompletionResponse(responses=responses, summary=summary)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "providers": {name: provider.available for name, provider in self.providers.items()},
            "stats": self.stats.copy()
        }
    
    def get_usage_stats(self, hours: int = 24) -> UsageStatsResponse:
        """Get usage statistics"""
        # Mock statistics for demonstration
        total_requests = self.stats["total_requests"]
        
        return UsageStatsResponse(
            total_requests=total_requests,
            successful_requests=self.stats["successful_requests"],
            failed_requests=self.stats["failed_requests"],
            total_cost=self.stats["total_cost"],
            average_latency_ms=self.stats["total_latency"] / max(total_requests, 1),
            cache_hit_rate=0.7,  # Mock cache hit rate
            provider_distribution={"openai": 70, "anthropic": 20, "vertex_ai": 10},
            model_distribution={"gpt-3.5-turbo": 60, "gpt-4o": 25, "claude-3-sonnet": 15},
            cost_by_model={"gpt-3.5-turbo": 50.0, "gpt-4o": 150.0, "claude-3-sonnet": 80.0},
            period_start=datetime.utcnow() - timedelta(hours=hours),
            period_end=datetime.utcnow()
        )

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

# Global service instance
llm_service = MockLLMService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logging.info("LLM API Server starting up...")
    
    # Initialize services (in production, initialize real services)
    # await llm_service.initialize()
    
    logging.info("LLM API Server ready to serve requests")
    
    yield
    
    # Shutdown
    logging.info("LLM API Server shutting down...")
    
    # Cleanup services
    # await llm_service.cleanup()
    
    logging.info("LLM API Server shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Enterprise LLM API Server",
    description="Production-ready LLM API with multi-provider support, caching, and cost optimization",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    health_data = llm_service.get_health_status()
    
    return HealthCheckResponse(
        status=health_data["status"],
        providers=health_data["providers"],
        uptime_seconds=health_data["uptime_seconds"]
    )

@app.post("/v1/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    auth: Dict[str, Any] = Depends(get_api_key),
    background_tasks: BackgroundTasks = None
):
    """
    Generate text completion
    
    This endpoint provides text completion functionality similar to OpenAI's API
    but with multi-provider support, intelligent routing, and cost optimization.
    """
    try:
        # Add user context to request
        request.user_id = request.user_id or auth["user_id"]
        
        # Check application permissions
        if (auth["applications"] != ["*"] and 
            request.application not in auth["applications"]):
            raise HTTPException(
                status_code=403, 
                detail=f"Application '{request.application}' not permitted for this API key"
            )
        
        # Generate completion
        response = await llm_service.generate_completion(request)
        
        # Add background tasks for analytics (in production)
        if background_tasks:
            background_tasks.add_task(
                log_request_analytics,
                request=request,
                response=response,
                user_id=auth["user_id"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Completion generation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/chat/completions", response_model=CompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    auth: Dict[str, Any] = Depends(get_api_key),
    background_tasks: BackgroundTasks = None
):
    """
    Generate chat completion
    
    Provides chat-based completions with conversation context management
    and multi-turn conversation support.
    """
    try:
        # Convert chat request to completion request
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
        
        completion_request = CompletionRequest(
            prompt=prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            priority=request.priority,
            routing_strategy=request.routing_strategy,
            user_id=request.user_id or auth["user_id"],
            application=request.application
        )
        
        response = await llm_service.generate_completion(completion_request)
        
        if background_tasks:
            background_tasks.add_task(
                log_request_analytics,
                request=completion_request,
                response=response,
                user_id=auth["user_id"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/completions/stream")
async def create_streaming_completion(
    request: CompletionRequest,
    auth: Dict[str, Any] = Depends(get_api_key)
):
    """
    Generate streaming text completion
    
    Returns completion tokens as they are generated for real-time applications
    like chat interfaces and live content generation.
    """
    try:
        request.user_id = request.user_id or auth["user_id"]
        request.stream = True
        
        async def generate_stream():
            """Generator for streaming response"""
            try:
                async for chunk in llm_service.stream_completion(request):
                    # Format as server-sent events
                    data = json.dumps({"choices": [{"delta": {"content": chunk}}]})
                    yield f"data: {data}\n\n"
                
                # Send completion marker
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                error_data = json.dumps({"error": {"message": str(e)}})
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Streaming completion failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/completions/batch", response_model=BatchCompletionResponse)
async def create_batch_completion(
    request: BatchCompletionRequest,
    auth: Dict[str, Any] = Depends(get_api_key),
    background_tasks: BackgroundTasks = None
):
    """
    Generate batch completions
    
    Process multiple completion requests efficiently with controlled concurrency.
    Ideal for bulk content generation and batch processing workflows.
    """
    try:
        # Validate batch size based on user permissions
        max_batch_size = 100 if "admin" in auth["permissions"] else 50
        
        if len(request.requests) > max_batch_size:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size {len(request.requests)} exceeds limit of {max_batch_size}"
            )
        
        # Add user context to all requests
        for req in request.requests:
            req.user_id = req.user_id or auth["user_id"]
        
        response = await llm_service.batch_completion(request.requests, request.max_concurrent)
        
        if background_tasks:
            background_tasks.add_task(
                log_batch_analytics,
                requests=request.requests,
                response=response,
                user_id=auth["user_id"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Batch completion failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/usage", response_model=UsageStatsResponse)
async def get_usage_statistics(
    hours: int = 24,
    auth: Dict[str, Any] = Depends(get_api_key)
):
    """
    Get usage statistics
    
    Provides comprehensive usage analytics including cost breakdown,
    model usage patterns, and performance metrics.
    """
    try:
        if "admin" not in auth["permissions"]:
            # Non-admin users get limited stats
            hours = min(hours, 24)
        
        stats = llm_service.get_usage_stats(hours)
        return stats
        
    except Exception as e:
        logging.error(f"Failed to get usage statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/models")
async def list_models(auth: Dict[str, Any] = Depends(get_api_key)):
    """
    List available models
    
    Returns information about available models across all providers
    with capabilities and pricing information.
    """
    models = {
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "provider": "openai",
                "capabilities": ["text"],
                "context_length": 16385,
                "cost_per_1k_tokens": {"input": 0.0015, "output": 0.002}
            },
            {
                "id": "gpt-4o",
                "provider": "openai", 
                "capabilities": ["text", "vision"],
                "context_length": 128000,
                "cost_per_1k_tokens": {"input": 0.005, "output": 0.015}
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "provider": "anthropic",
                "capabilities": ["text", "vision"],
                "context_length": 200000,
                "cost_per_1k_tokens": {"input": 0.003, "output": 0.015}
            }
        ]
    }
    
    return models

@app.post("/v1/optimize")
async def optimize_request(
    request: CompletionRequest,
    auth: Dict[str, Any] = Depends(get_api_key)
):
    """
    Optimize request for cost and performance
    
    Analyzes the request and suggests optimizations for better cost-effectiveness
    and performance without executing the actual completion.
    """
    try:
        # Mock optimization analysis
        optimization_result = {
            "original_request": request.dict(),
            "optimizations": [
                {
                    "type": "model_suggestion",
                    "description": "Consider using gpt-3.5-turbo for cost savings",
                    "estimated_savings": 0.75,
                    "quality_impact": "minimal"
                },
                {
                    "type": "prompt_optimization", 
                    "description": "Prompt could be shortened by 20% without losing meaning",
                    "estimated_savings": 0.20,
                    "quality_impact": "none"
                }
            ],
            "estimated_cost": {
                "original": 0.05,
                "optimized": 0.03,
                "savings_percentage": 40.0
            },
            "quality_score": 0.95
        }
        
        return optimization_result
        
    except Exception as e:
        logging.error(f"Request optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# BACKGROUND TASKS AND ANALYTICS
# =============================================================================

async def log_request_analytics(request: CompletionRequest, response: CompletionResponse, user_id: str):
    """Log request analytics for monitoring and optimization"""
    analytics_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "request_id": response.id,
        "application": request.application,
        "model": request.model,
        "provider": response.provider,
        "prompt_length": len(request.prompt),
        "response_length": len(response.content),
        "cost": response.cost,
        "latency_ms": response.latency_ms,
        "cached": response.cached,
        "tags": request.tags
    }
    
    # In production, send to analytics service
    logging.info(f"Analytics: {json.dumps(analytics_data)}")

async def log_batch_analytics(requests: List[CompletionRequest], 
                            response: BatchCompletionResponse, user_id: str):
    """Log batch request analytics"""
    batch_analytics = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "batch_size": len(requests),
        "successful_responses": len(response.responses),
        "total_cost": response.summary["total_cost"],
        "average_latency": response.summary["average_latency_ms"]
    }
    
    logging.info(f"Batch Analytics: {json.dumps(batch_analytics)}")

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return {
        "error": {
            "message": exc.detail,
            "type": "http_error",
            "status_code": exc.status_code
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logging.error(f"Unhandled exception: {exc}")
    
    return {
        "error": {
            "message": "Internal server error",
            "type": "server_error",
            "status_code": 500
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('llm_api_server.log')
        ]
    )
    
    # Run the application
    uvicorn.run(
        "fastapi_llm_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

# =============================================================================
# USAGE EXAMPLES AND CLIENT CODE
# =============================================================================

"""
Example client usage:

import httpx
import asyncio
import json

async def test_llm_api():
    base_url = "http://localhost:8000"
    headers = {
        "Authorization": "Bearer llm_api_key_demo",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Test completion
        completion_request = {
            "prompt": "Analyze the following contract clause for legal risks:",
            "model": "gpt-4o",
            "max_tokens": 500,
            "temperature": 0.7,
            "application": "legal_analysis"
        }
        
        response = await client.post(
            f"{base_url}/v1/completions",
            json=completion_request,
            headers=headers
        )
        
        print("Completion Response:")
        print(json.dumps(response.json(), indent=2))
        
        # Test chat completion
        chat_request = {
            "messages": [
                {"role": "user", "content": "How do I set up A/B testing?"}
            ],
            "model": "gpt-3.5-turbo",
            "application": "customer_service"
        }
        
        response = await client.post(
            f"{base_url}/v1/chat/completions", 
            json=chat_request,
            headers=headers
        )
        
        print("Chat Response:")
        print(json.dumps(response.json(), indent=2))
        
        # Test streaming
        stream_request = {
            "prompt": "Write a brief explanation of microservices",
            "model": "gpt-3.5-turbo",
            "stream": True
        }
        
        async with client.stream(
            "POST",
            f"{base_url}/v1/completions/stream",
            json=stream_request,
            headers=headers
        ) as stream:
            print("Streaming Response:")
            async for chunk in stream.aiter_text():
                if chunk.startswith("data: "):
                    data = chunk[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(data)
                        if "choices" in parsed:
                            content = parsed["choices"][0]["delta"].get("content", "")
                            print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        continue
            print()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_llm_api())
"""
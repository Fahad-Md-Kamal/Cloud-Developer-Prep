"""
Multi-Provider LLM Client for Enterprise AI Applications

This module demonstrates a production-ready multi-provider LLM client system
designed for enterprise applications like those used at Lawstronaut (legal document
analysis) and Optimizely (conversational AI systems).

Key concepts covered:
- Provider abstraction and interface design
- Intelligent failover and load balancing
- Rate limiting and quota management
- Cost optimization across providers
- Async request handling and connection pooling

Real-world applications:
- Legal document processing with provider fallbacks
- Customer service chatbots with cost optimization
- Content generation with quality-based routing

Author: Technical Interview Preparation Guide
"""

import asyncio
import aiohttp
import json
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, AsyncGenerator, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import deque, defaultdict
import random

# =============================================================================
# CORE DATA MODELS AND TYPES
# =============================================================================

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    VERTEX_AI = "vertex_ai"
    AZURE_OPENAI = "azure_openai"

class RequestPriority(Enum):
    """Request priority levels for routing decisions"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class LLMRequest:
    """Standardized LLM request format"""
    prompt: str
    model: str = "gpt-3.5-turbo"
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    stream: bool = False
    priority: RequestPriority = RequestPriority.NORMAL
    user_id: Optional[str] = None
    application: str = "default"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        self.request_id = hashlib.md5(
            f"{self.prompt}{time.time()}{random.randint(0, 1000)}".encode()
        ).hexdigest()[:12]

@dataclass
class LLMResponse:
    """Standardized LLM response format"""
    content: str
    provider: LLMProvider
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency: float
    request_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ProviderMetrics:
    """Real-time provider performance metrics"""
    success_rate: float = 1.0
    average_latency: float = 0.0
    current_load: int = 0
    cost_per_token: float = 0.0
    availability: bool = True
    last_error: Optional[str] = None
    consecutive_failures: int = 0

# =============================================================================
# PROVIDER ABSTRACTION LAYER
# =============================================================================

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, provider_type: LLMProvider, config: Dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.metrics = ProviderMetrics()
        self.session: Optional[aiohttp.ClientSession] = None
        
    @abstractmethod
    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate completion for the given request"""
        pass
    
    @abstractmethod
    async def stream_completion(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion tokens as they are generated"""
        pass
    
    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about specific model capabilities"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health and availability"""
        pass
    
    async def initialize(self):
        """Initialize provider resources"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Max connections per host
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,
            sock_connect=10,
            sock_read=20
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._get_default_headers()
        )
    
    async def cleanup(self):
        """Cleanup provider resources"""
        if self.session:
            await self.session.close()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests"""
        return {
            "Content-Type": "application/json",
            "User-Agent": "Enterprise-LLM-Client/1.0"
        }
    
    def update_metrics(self, success: bool, latency: float, cost: float):
        """Update provider performance metrics"""
        # Simple exponential moving average for metrics
        alpha = 0.1
        
        if success:
            self.metrics.consecutive_failures = 0
            self.metrics.success_rate = (
                alpha * 1.0 + (1 - alpha) * self.metrics.success_rate
            )
        else:
            self.metrics.consecutive_failures += 1
            self.metrics.success_rate = (
                alpha * 0.0 + (1 - alpha) * self.metrics.success_rate
            )
        
        self.metrics.average_latency = (
            alpha * latency + (1 - alpha) * self.metrics.average_latency
        )
        
        # Update availability based on recent performance
        self.metrics.availability = (
            self.metrics.success_rate > 0.5 and 
            self.metrics.consecutive_failures < 5
        )

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(LLMProvider.OPENAI, config)
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.organization_id = config.get("organization_id")
        
        # Model pricing (per 1K tokens)
        self.model_pricing = {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
        }
    
    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        headers["Authorization"] = f"Bearer {self.api_key}"
        if self.organization_id:
            headers["OpenAI-Organization"] = self.organization_id
        return headers
    
    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using OpenAI API"""
        start_time = time.time()
        
        try:
            payload = {
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "stream": False
            }
            
            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens
            
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Extract response data
                choice = data["choices"][0]
                usage = data["usage"]
                
                # Calculate cost
                input_tokens = usage["prompt_tokens"]
                output_tokens = usage["completion_tokens"]
                cost = self._calculate_cost(request.model, input_tokens, output_tokens)
                
                latency = time.time() - start_time
                
                # Update metrics
                self.update_metrics(True, latency, cost)
                
                return LLMResponse(
                    content=choice["message"]["content"],
                    provider=self.provider_type,
                    model=request.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    latency=latency,
                    request_id=request.request_id,
                    timestamp=datetime.utcnow(),
                    metadata={"finish_reason": choice["finish_reason"]}
                )
                
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(False, latency, 0.0)
            self.metrics.last_error = str(e)
            raise
    
    async def stream_completion(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion tokens from OpenAI"""
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "stream": True
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        
        async with self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for OpenAI request"""
        pricing = self.model_pricing.get(model, {"input": 0.001, "output": 0.002})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get OpenAI model information"""
        model_info = {
            "gpt-4o": {
                "context_length": 128000,
                "output_tokens": 4096,
                "capabilities": ["text", "vision"],
                "strengths": ["reasoning", "analysis", "code"]
            },
            "gpt-4-turbo": {
                "context_length": 128000,
                "output_tokens": 4096,
                "capabilities": ["text", "vision"],
                "strengths": ["reasoning", "analysis", "creative"]
            },
            "gpt-3.5-turbo": {
                "context_length": 16385,
                "output_tokens": 4096,
                "capabilities": ["text"],
                "strengths": ["speed", "cost-efficiency"]
            }
        }
        
        return model_info.get(model, {})
    
    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                return response.status == 200
        except Exception:
            return False

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(LLMProvider.ANTHROPIC, config)
        self.api_key = config["api_key"]
        self.base_url = config.get("base_url", "https://api.anthropic.com/v1")
        
        # Model pricing (per 1K tokens)
        self.model_pricing = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125}
        }
    
    def _get_default_headers(self) -> Dict[str, str]:
        headers = super()._get_default_headers()
        headers["x-api-key"] = self.api_key
        headers["anthropic-version"] = "2023-06-01"
        return headers
    
    async def generate_completion(self, request: LLMRequest) -> LLMResponse:
        """Generate completion using Anthropic Claude API"""
        start_time = time.time()
        
        try:
            payload = {
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 4096
            }
            
            async with self.session.post(
                f"{self.base_url}/messages",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Extract response data
                content = data["content"][0]["text"]
                usage = data["usage"]
                
                # Calculate cost
                input_tokens = usage["input_tokens"]
                output_tokens = usage["output_tokens"]
                cost = self._calculate_cost(request.model, input_tokens, output_tokens)
                
                latency = time.time() - start_time
                
                # Update metrics
                self.update_metrics(True, latency, cost)
                
                return LLMResponse(
                    content=content,
                    provider=self.provider_type,
                    model=request.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    latency=latency,
                    request_id=request.request_id,
                    timestamp=datetime.utcnow(),
                    metadata={"stop_reason": data.get("stop_reason")}
                )
                
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(False, latency, 0.0)
            self.metrics.last_error = str(e)
            raise
    
    async def stream_completion(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream completion from Anthropic (simplified implementation)"""
        # Note: This is a simplified streaming implementation
        # In production, you would implement proper SSE parsing
        response = await self.generate_completion(request)
        
        # Simulate streaming by yielding chunks
        words = response.content.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)  # Simulate streaming delay
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Anthropic request"""
        pricing = self.model_pricing.get(model, {"input": 0.003, "output": 0.015})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get Anthropic model information"""
        model_info = {
            "claude-3-5-sonnet-20241022": {
                "context_length": 200000,
                "output_tokens": 8192,
                "capabilities": ["text", "vision"],
                "strengths": ["analysis", "reasoning", "safety"]
            },
            "claude-3-opus-20240229": {
                "context_length": 200000,
                "output_tokens": 4096,
                "capabilities": ["text", "vision"],
                "strengths": ["complex reasoning", "creative writing"]
            },
            "claude-3-haiku-20240307": {
                "context_length": 200000,
                "output_tokens": 4096,
                "capabilities": ["text", "vision"],
                "strengths": ["speed", "cost-efficiency"]
            }
        }
        
        return model_info.get(model, {})
    
    async def health_check(self) -> bool:
        """Check Anthropic API health"""
        try:
            # Simple health check - you might need to adjust based on API
            async with self.session.get(f"{self.base_url}/models") as response:
                return response.status in [200, 404]  # 404 might be expected
        except Exception:
            return False

# =============================================================================
# ADVANCED RATE LIMITING
# =============================================================================

class AdaptiveRateLimiter:
    """Advanced rate limiter with adaptive behavior"""
    
    def __init__(self, base_rate: int, burst_allowance: int = 10):
        self.base_rate = base_rate
        self.burst_allowance = burst_allowance
        self.request_times = deque()
        self.current_rate = base_rate
        self.lock = asyncio.Lock()
        
        # Performance tracking
        self.success_count = 0
        self.total_requests = 0
        
    async def acquire_permit(self) -> bool:
        """Acquire permission to make request"""
        async with self.lock:
            now = time.time()
            
            # Remove requests outside current window (1 minute)
            while self.request_times and now - self.request_times[0] > 60:
                self.request_times.popleft()
            
            # Check if we can make request
            if len(self.request_times) < self.current_rate:
                self.request_times.append(now)
                return True
            
            return False
    
    async def wait_for_permit(self, timeout: float = 30.0) -> bool:
        """Wait for permit with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.acquire_permit():
                return True
            await asyncio.sleep(0.1)
        
        return False
    
    def record_result(self, success: bool):
        """Record request result for rate adaptation"""
        self.total_requests += 1
        if success:
            self.success_count += 1
        
        # Adjust rate every 100 requests
        if self.total_requests % 100 == 0:
            success_rate = self.success_count / self.total_requests
            self.adjust_rate(success_rate)
    
    def adjust_rate(self, success_rate: float):
        """Adjust rate based on success rate"""
        if success_rate > 0.95:
            # Increase rate if we're successful
            self.current_rate = min(
                self.current_rate + 5,
                self.base_rate + self.burst_allowance
            )
        elif success_rate < 0.85:
            # Decrease rate if we're failing
            self.current_rate = max(
                self.current_rate - 10,
                self.base_rate // 2
            )

# =============================================================================
# INTELLIGENT REQUEST ROUTER
# =============================================================================

class RoutingStrategy(Enum):
    """Available routing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LOWEST_LATENCY = "lowest_latency"
    LOWEST_COST = "lowest_cost"
    HIGHEST_SUCCESS_RATE = "highest_success_rate"
    INTELLIGENT_HYBRID = "intelligent_hybrid"

class IntelligentRouter:
    """Advanced request router with multiple strategies"""
    
    def __init__(self, providers: List[BaseLLMProvider]):
        self.providers = {p.provider_type: p for p in providers}
        self.current_index = 0
        
        # Model capability mapping
        self.model_provider_map = {
            # OpenAI models
            "gpt-4o": [LLMProvider.OPENAI],
            "gpt-4-turbo": [LLMProvider.OPENAI],
            "gpt-3.5-turbo": [LLMProvider.OPENAI],
            
            # Anthropic models
            "claude-3-5-sonnet-20241022": [LLMProvider.ANTHROPIC],
            "claude-3-opus-20240229": [LLMProvider.ANTHROPIC],
            "claude-3-haiku-20240307": [LLMProvider.ANTHROPIC],
        }
    
    async def select_provider(self, request: LLMRequest, 
                            strategy: RoutingStrategy = RoutingStrategy.INTELLIGENT_HYBRID) -> BaseLLMProvider:
        """Select optimal provider for request"""
        
        # Filter providers that support the requested model
        compatible_providers = []
        supported_providers = self.model_provider_map.get(request.model, list(self.providers.keys()))
        
        for provider_type in supported_providers:
            provider = self.providers.get(provider_type)
            if provider and provider.metrics.availability:
                compatible_providers.append(provider)
        
        if not compatible_providers:
            raise RuntimeError(f"No available providers for model {request.model}")
        
        # Apply routing strategy
        if strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(compatible_providers)
        elif strategy == RoutingStrategy.LOWEST_LATENCY:
            return self._lowest_latency_selection(compatible_providers)
        elif strategy == RoutingStrategy.LOWEST_COST:
            return self._lowest_cost_selection(compatible_providers, request)
        elif strategy == RoutingStrategy.HIGHEST_SUCCESS_RATE:
            return self._highest_success_rate_selection(compatible_providers)
        elif strategy == RoutingStrategy.INTELLIGENT_HYBRID:
            return await self._intelligent_hybrid_selection(compatible_providers, request)
        else:
            return random.choice(compatible_providers)
    
    def _round_robin_selection(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """Round-robin provider selection"""
        provider = providers[self.current_index % len(providers)]
        self.current_index += 1
        return provider
    
    def _lowest_latency_selection(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """Select provider with lowest average latency"""
        return min(providers, key=lambda p: p.metrics.average_latency)
    
    def _lowest_cost_selection(self, providers: List[BaseLLMProvider], 
                             request: LLMRequest) -> BaseLLMProvider:
        """Select provider with lowest cost for request"""
        def estimate_cost(provider: BaseLLMProvider) -> float:
            # Rough cost estimation based on prompt length
            estimated_tokens = len(request.prompt.split()) * 1.3  # Rough token estimation
            return provider.metrics.cost_per_token * estimated_tokens
        
        return min(providers, key=estimate_cost)
    
    def _highest_success_rate_selection(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """Select provider with highest success rate"""
        return max(providers, key=lambda p: p.metrics.success_rate)
    
    async def _intelligent_hybrid_selection(self, providers: List[BaseLLMProvider], 
                                          request: LLMRequest) -> BaseLLMProvider:
        """Intelligent selection based on multiple factors"""
        
        def calculate_score(provider: BaseLLMProvider) -> float:
            """Calculate weighted score for provider selection"""
            
            # Base scores (0-1 scale)
            success_score = provider.metrics.success_rate
            latency_score = max(0, 1 - (provider.metrics.average_latency / 10))  # Assume 10s is max acceptable
            cost_score = max(0, 1 - (provider.metrics.cost_per_token * 1000))  # Normalize cost
            
            # Priority-based weighting
            if request.priority == RequestPriority.CRITICAL:
                # For critical requests, prioritize success and latency
                return 0.5 * success_score + 0.4 * latency_score + 0.1 * cost_score
            elif request.priority == RequestPriority.HIGH:
                return 0.4 * success_score + 0.3 * latency_score + 0.3 * cost_score
            else:
                # For normal/low priority, balance all factors
                return 0.3 * success_score + 0.3 * latency_score + 0.4 * cost_score
        
        # Calculate scores and select best provider
        scored_providers = [(p, calculate_score(p)) for p in providers]
        best_provider = max(scored_providers, key=lambda x: x[1])
        
        return best_provider[0]

# =============================================================================
# MULTI-PROVIDER LLM CLIENT
# =============================================================================

class MultiProviderLLMClient:
    """Production-ready multi-provider LLM client"""
    
    def __init__(self, config: Dict[str, Dict[str, Any]]):
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.rate_limiters: Dict[LLMProvider, AdaptiveRateLimiter] = {}
        self.router = None
        
        # Initialize providers
        self._initialize_providers(config)
        
        # Request tracking
        self.active_requests = 0
        self.total_requests = 0
        self.total_cost = 0.0
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60
        
        # Metrics collection
        self.metrics_history = defaultdict(list)
        
    def _initialize_providers(self, config: Dict[str, Dict[str, Any]]):
        """Initialize all configured providers"""
        provider_classes = {
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.ANTHROPIC: AnthropicProvider,
            # Add other providers as needed
        }
        
        for provider_type_str, provider_config in config.items():
            try:
                provider_type = LLMProvider(provider_type_str)
                provider_class = provider_classes.get(provider_type)
                
                if provider_class:
                    provider = provider_class(provider_config)
                    self.providers[provider_type] = provider
                    
                    # Initialize rate limiter
                    rate_limit = provider_config.get("rate_limit", 60)
                    self.rate_limiters[provider_type] = AdaptiveRateLimiter(rate_limit)
                    
                    logging.info(f"Initialized {provider_type} provider")
                else:
                    logging.warning(f"No implementation for provider: {provider_type}")
                    
            except ValueError:
                logging.error(f"Unknown provider type: {provider_type_str}")
        
        # Initialize router
        if self.providers:
            self.router = IntelligentRouter(list(self.providers.values()))
    
    async def initialize(self):
        """Initialize all providers"""
        for provider in self.providers.values():
            try:
                await provider.initialize()
                logging.info(f"Initialized {provider.provider_type} provider")
            except Exception as e:
                logging.error(f"Failed to initialize {provider.provider_type}: {e}")
    
    async def cleanup(self):
        """Cleanup all provider resources"""
        for provider in self.providers.values():
            try:
                await provider.cleanup()
            except Exception as e:
                logging.error(f"Error cleaning up {provider.provider_type}: {e}")
    
    async def generate_completion(self, request: LLMRequest, 
                                strategy: RoutingStrategy = RoutingStrategy.INTELLIGENT_HYBRID,
                                max_retries: int = 3) -> LLMResponse:
        """Generate completion with intelligent provider selection"""
        
        if not self.router:
            raise RuntimeError("No providers available")
        
        self.total_requests += 1
        self.active_requests += 1
        
        last_exception = None
        
        try:
            for attempt in range(max_retries):
                try:
                    # Select provider
                    provider = await self.router.select_provider(request, strategy)
                    
                    # Check rate limits
                    rate_limiter = self.rate_limiters[provider.provider_type]
                    if not await rate_limiter.wait_for_permit():
                        logging.warning(f"Rate limit exceeded for {provider.provider_type}")
                        continue
                    
                    # Make request
                    response = await provider.generate_completion(request)
                    
                    # Record success
                    rate_limiter.record_result(True)
                    self.total_cost += response.cost
                    
                    # Update metrics
                    self._update_metrics(provider.provider_type, response)
                    
                    return response
                    
                except Exception as e:
                    last_exception = e
                    logging.warning(f"Request failed on {provider.provider_type}: {e}")
                    
                    # Record failure
                    if 'provider' in locals():
                        rate_limiter = self.rate_limiters[provider.provider_type]
                        rate_limiter.record_result(False)
                    
                    # Exponential backoff
                    if attempt < max_retries - 1:
                        delay = min(2 ** attempt, 10)
                        await asyncio.sleep(delay)
            
            # All retries exhausted
            raise RuntimeError(f"All providers failed after {max_retries} attempts. Last error: {last_exception}")
            
        finally:
            self.active_requests -= 1
    
    async def stream_completion(self, request: LLMRequest,
                              strategy: RoutingStrategy = RoutingStrategy.INTELLIGENT_HYBRID) -> AsyncGenerator[str, None]:
        """Stream completion with provider selection"""
        
        provider = await self.router.select_provider(request, strategy)
        rate_limiter = self.rate_limiters[provider.provider_type]
        
        if not await rate_limiter.wait_for_permit():
            raise RuntimeError(f"Rate limit exceeded for {provider.provider_type}")
        
        self.active_requests += 1
        
        try:
            async for chunk in provider.stream_completion(request):
                yield chunk
                
            rate_limiter.record_result(True)
            
        except Exception as e:
            rate_limiter.record_result(False)
            raise
        finally:
            self.active_requests -= 1
    
    async def batch_generate(self, requests: List[LLMRequest], 
                           max_concurrent: int = 10) -> List[LLMResponse]:
        """Process multiple requests with controlled concurrency"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_request(req: LLMRequest) -> LLMResponse:
            async with semaphore:
                return await self.generate_completion(req)
        
        # Create tasks for all requests
        tasks = [process_single_request(req) for req in requests]
        
        # Execute with progress tracking
        responses = []
        completed = 0
        
        for task in asyncio.as_completed(tasks):
            try:
                response = await task
                responses.append(response)
                completed += 1
                logging.info(f"Completed {completed}/{len(requests)} requests")
            except Exception as e:
                logging.error(f"Request failed: {e}")
                responses.append(None)  # Placeholder for failed request
        
        return responses
    
    def _update_metrics(self, provider_type: LLMProvider, response: LLMResponse):
        """Update internal metrics"""
        self.metrics_history[provider_type].append({
            "timestamp": response.timestamp,
            "latency": response.latency,
            "cost": response.cost,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "success": True
        })
        
        # Keep only recent metrics (last 1000 requests per provider)
        if len(self.metrics_history[provider_type]) > 1000:
            self.metrics_history[provider_type] = self.metrics_history[provider_type][-1000:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        summary = {
            "total_requests": self.total_requests,
            "active_requests": self.active_requests,
            "total_cost": self.total_cost,
            "providers": {}
        }
        
        for provider_type, provider in self.providers.items():
            provider_metrics = {
                "success_rate": provider.metrics.success_rate,
                "average_latency": provider.metrics.average_latency,
                "current_load": provider.metrics.current_load,
                "availability": provider.metrics.availability,
                "consecutive_failures": provider.metrics.consecutive_failures
            }
            
            # Add historical metrics if available
            if provider_type in self.metrics_history:
                recent_metrics = self.metrics_history[provider_type][-100:]  # Last 100 requests
                if recent_metrics:
                    provider_metrics.update({
                        "recent_average_cost": sum(m["cost"] for m in recent_metrics) / len(recent_metrics),
                        "recent_average_latency": sum(m["latency"] for m in recent_metrics) / len(recent_metrics),
                        "recent_request_count": len(recent_metrics)
                    })
            
            summary["providers"][provider_type.value] = provider_metrics
        
        return summary
    
    async def health_check(self) -> Dict[LLMProvider, bool]:
        """Check health of all providers"""
        health_status = {}
        
        for provider_type, provider in self.providers.items():
            try:
                is_healthy = await provider.health_check()
                health_status[provider_type] = is_healthy
                
                # Update availability in metrics
                provider.metrics.availability = is_healthy
                
            except Exception as e:
                logging.error(f"Health check failed for {provider_type}: {e}")
                health_status[provider_type] = False
                provider.metrics.availability = False
        
        return health_status

# =============================================================================
# DEMONSTRATION FUNCTION
# =============================================================================

async def demonstrate_multi_provider_llm_client():
    """
    Comprehensive demonstration of the multi-provider LLM client
    in realistic enterprise scenarios.
    """
    
    print(f"=== {__doc__.split('.')[0]} ===\n")
    
    # Configuration for multiple providers
    config = {
        "openai": {
            "api_key": "your-openai-api-key",  # Replace with actual key
            "rate_limit": 60
        },
        "anthropic": {
            "api_key": "your-anthropic-api-key",  # Replace with actual key
            "rate_limit": 50
        }
    }
    
    # Initialize client
    client = MultiProviderLLMClient(config)
    await client.initialize()
    
    try:
        print("1. Health Check")
        print("-" * 40)
        health_status = await client.health_check()
        for provider, status in health_status.items():
            print(f"{provider.value}: {'✓ Healthy' if status else '✗ Unhealthy'}")
        print()
        
        print("2. Single Request Generation")
        print("-" * 40)
        
        # Legal document analysis scenario (Lawstronaut)
        legal_request = LLMRequest(
            prompt="Analyze the following contract clause for potential risks: 'The party shall be liable for any damages whatsoever arising from breach of this agreement.'",
            model="gpt-4o",
            priority=RequestPriority.HIGH,
            application="legal_analysis"
        )
        
        try:
            start_time = time.time()
            response = await client.generate_completion(legal_request)
            end_time = time.time()
            
            print(f"Request ID: {response.request_id}")
            print(f"Provider: {response.provider.value}")
            print(f"Model: {response.model}")
            print(f"Response: {response.content[:200]}...")
            print(f"Tokens: {response.input_tokens} input, {response.output_tokens} output")
            print(f"Cost: ${response.cost:.4f}")
            print(f"Latency: {response.latency:.2f}s")
            print()
        except Exception as e:
            print(f"Request failed: {e}")
            print()
        
        print("3. Batch Processing")
        print("-" * 40)
        
        # Multiple customer service queries (Optimizely scenario)
        batch_requests = [
            LLMRequest(
                prompt=f"Provide a helpful response to this customer query: 'How do I configure A/B testing for my website?'",
                model="gpt-3.5-turbo",
                priority=RequestPriority.NORMAL,
                application="customer_service"
            ),
            LLMRequest(
                prompt=f"Explain the benefits of personalization in e-commerce",
                model="gpt-3.5-turbo",
                priority=RequestPriority.NORMAL,
                application="content_generation"
            ),
            LLMRequest(
                prompt=f"Analyze user engagement metrics for optimization recommendations",
                model="gpt-4o",
                priority=RequestPriority.HIGH,
                application="analytics"
            )
        ]
        
        try:
            print(f"Processing {len(batch_requests)} requests...")
            batch_start = time.time()
            responses = await client.batch_generate(batch_requests, max_concurrent=3)
            batch_end = time.time()
            
            successful_responses = [r for r in responses if r is not None]
            print(f"Completed: {len(successful_responses)}/{len(batch_requests)}")
            print(f"Total time: {batch_end - batch_start:.2f}s")
            print(f"Total cost: ${sum(r.cost for r in successful_responses):.4f}")
            print()
        except Exception as e:
            print(f"Batch processing failed: {e}")
            print()
        
        print("4. Different Routing Strategies")
        print("-" * 40)
        
        test_request = LLMRequest(
            prompt="What are the key principles of effective API design?",
            model="gpt-3.5-turbo",
            application="technical_content"
        )
        
        strategies = [
            RoutingStrategy.INTELLIGENT_HYBRID,
            RoutingStrategy.LOWEST_LATENCY,
            RoutingStrategy.HIGHEST_SUCCESS_RATE
        ]
        
        for strategy in strategies:
            try:
                start = time.time()
                response = await client.generate_completion(test_request, strategy=strategy)
                end = time.time()
                
                print(f"Strategy: {strategy.value}")
                print(f"Provider: {response.provider.value}")
                print(f"Latency: {end - start:.2f}s")
                print(f"Cost: ${response.cost:.4f}")
                print()
            except Exception as e:
                print(f"Strategy {strategy.value} failed: {e}")
                print()
        
        print("5. Streaming Response")
        print("-" * 40)
        
        stream_request = LLMRequest(
            prompt="Write a brief explanation of microservices architecture",
            model="gpt-3.5-turbo",
            stream=True
        )
        
        try:
            print("Streaming response:")
            async for chunk in client.stream_completion(stream_request):
                print(chunk, end='', flush=True)
            print("\n")
        except Exception as e:
            print(f"Streaming failed: {e}")
            print()
        
        print("6. Metrics and Performance Summary")
        print("-" * 40)
        
        metrics = client.get_metrics_summary()
        print(f"Total requests processed: {metrics['total_requests']}")
        print(f"Currently active requests: {metrics['active_requests']}")
        print(f"Total cost: ${metrics['total_cost']:.4f}")
        print()
        
        print("Provider Performance:")
        for provider_name, provider_metrics in metrics["providers"].items():
            print(f"\n{provider_name.upper()}:")
            print(f"  Success rate: {provider_metrics['success_rate']:.1%}")
            print(f"  Average latency: {provider_metrics['average_latency']:.2f}s")
            print(f"  Available: {'Yes' if provider_metrics['availability'] else 'No'}")
            if 'recent_average_cost' in provider_metrics:
                print(f"  Recent avg cost: ${provider_metrics['recent_average_cost']:.4f}")
        
    finally:
        # Cleanup resources
        await client.cleanup()
        print("\n=== Multi-provider LLM client demonstration completed ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    asyncio.run(demonstrate_multi_provider_llm_client())
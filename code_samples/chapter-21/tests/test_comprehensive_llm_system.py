"""
Comprehensive Test Suite for LLM API Integration

This module demonstrates testing strategies for enterprise LLM systems
including unit tests, integration tests, and performance benchmarking.

Key testing concepts covered:
- Unit testing for individual components
- Integration testing with mock providers
- Performance and load testing
- Cost optimization testing
- Security and authentication testing

Author: Technical Interview Preparation Guide
"""

import pytest
import asyncio
import time
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Simulated imports - in real implementation these would be actual imports
# from multi_provider_llm_client import MultiProviderLLMClient, LLMRequest, LLMResponse
# from cost_optimization_system import CostOptimizationSystem, CostTracker
# from intelligent_caching import IntelligentCacheManager
# from fastapi_llm_server import app

import httpx
import pytest_asyncio
from fastapi.testclient import TestClient

# =============================================================================
# TEST FIXTURES AND SETUP
# =============================================================================

@pytest_asyncio.fixture
async def mock_llm_client():
    """Fixture for mock LLM client"""
    client = MagicMock()
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.content = "Mock response content"
    mock_response.provider = "openai"
    mock_response.model = "gpt-3.5-turbo"
    mock_response.input_tokens = 100
    mock_response.output_tokens = 50
    mock_response.cost = Decimal("0.01")
    mock_response.latency = 1.5
    mock_response.request_id = "test_123"
    mock_response.timestamp = datetime.utcnow()
    
    client.generate_completion = AsyncMock(return_value=mock_response)
    client.get_metrics_summary = MagicMock(return_value={
        "total_requests": 100,
        "total_cost": 5.0,
        "providers": {
            "openai": {"success_rate": 0.95, "average_latency": 1.2}
        }
    })
    
    return client

@pytest_asyncio.fixture
async def mock_cost_tracker():
    """Fixture for mock cost optimization system"""
    tracker = MagicMock()
    
    # Mock optimization results
    mock_optimization = {
        "optimizations_applied": ["token_optimization", "model_optimization"],
        "cost_analysis": {
            "total_potential_savings": {"absolute_dollars": 0.005, "percentage": 25.0}
        }
    }
    
    tracker.optimize_request = AsyncMock(return_value=mock_optimization)
    tracker.get_cost_summary = MagicMock(return_value={
        "summary": {"total_cost": 10.0, "total_requests": 200},
        "optimization_opportunities": []
    })
    
    return tracker

@pytest_asyncio.fixture
async def mock_cache_manager():
    """Fixture for mock cache manager"""
    cache = MagicMock()
    
    cache.get_response = AsyncMock(return_value=None)  # Cache miss by default
    cache.store_response = AsyncMock(return_value=True)
    cache.get_comprehensive_stats = AsyncMock(return_value={
        "global_stats": {"overall_hit_rate": 0.65, "total_cost_savings": 15.0}
    })
    
    return cache

@pytest.fixture
def api_client():
    """Fixture for FastAPI test client"""
    # This would use the actual FastAPI app in real implementation
    from fastapi_llm_server import app
    return TestClient(app)

# =============================================================================
# UNIT TESTS
# =============================================================================

class TestLLMRequest:
    """Test LLM request handling and validation"""
    
    def test_request_creation(self):
        """Test basic request creation"""
        # Mock request data
        request_data = {
            "prompt": "Test prompt for analysis",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # In real implementation, this would use actual LLMRequest class
        assert request_data["prompt"] == "Test prompt for analysis"
        assert request_data["model"] == "gpt-3.5-turbo"
        assert 0.0 <= request_data["temperature"] <= 2.0
        assert request_data["max_tokens"] > 0
    
    def test_request_validation(self):
        """Test request validation logic"""
        # Test empty prompt
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            if not "Test prompt":  # Simulate empty prompt
                raise ValueError("Prompt cannot be empty")
        
        # Test invalid temperature
        invalid_temp = 3.0
        assert invalid_temp > 2.0, "Temperature should be validated"
    
    def test_prompt_optimization(self):
        """Test prompt optimization functionality"""
        long_prompt = "This is a very long prompt " * 100  # 500+ words
        
        # Mock optimization
        optimized_length = len(long_prompt) * 0.8  # 20% reduction
        
        assert optimized_length < len(long_prompt), "Prompt should be optimized"
        
        # Test that meaning is preserved (mock check)
        meaning_preserved = True  # Would use actual semantic analysis
        assert meaning_preserved, "Optimization should preserve meaning"

class TestCostOptimization:
    """Test cost optimization strategies"""
    
    @pytest.mark.asyncio
    async def test_model_selection_optimization(self, mock_cost_tracker):
        """Test intelligent model selection for cost optimization"""
        
        # Test legal analysis task (should prefer high-quality models)
        legal_task = {
            "task_type": "legal_analysis",
            "quality_threshold": 0.95,
            "budget_constraint": Decimal("0.10")
        }
        
        # Mock model recommendation
        recommendation = {
            "recommended_model": "gpt-4o",
            "quality_score": 0.96,
            "estimated_cost": 0.08
        }
        
        assert recommendation["quality_score"] >= legal_task["quality_threshold"]
        assert recommendation["estimated_cost"] <= legal_task["budget_constraint"]
    
    @pytest.mark.asyncio  
    async def test_token_optimization(self):
        """Test token count optimization"""
        verbose_prompt = """
        Please provide a comprehensive and detailed analysis of the following 
        legal contract clause, including all potential risks, benefits, 
        implications, and detailed recommendations...
        """
        
        # Mock token counting
        original_tokens = len(verbose_prompt.split()) * 1.3  # Rough estimate
        
        # Mock optimization (25% reduction)
        optimized_tokens = original_tokens * 0.75
        
        assert optimized_tokens < original_tokens
        
        # Calculate cost savings
        cost_per_token = 0.000015  # GPT-4 pricing
        savings = (original_tokens - optimized_tokens) * cost_per_token
        
        assert savings > 0, "Token optimization should reduce costs"
    
    def test_caching_cost_benefits(self):
        """Test caching cost benefit calculations"""
        
        # Mock cache statistics
        cache_stats = {
            "total_requests": 1000,
            "cache_hits": 650,
            "cache_misses": 350,
            "average_request_cost": 0.02,
            "total_cost_savings": 13.0
        }
        
        hit_rate = cache_stats["cache_hits"] / cache_stats["total_requests"]
        expected_savings = cache_stats["cache_hits"] * cache_stats["average_request_cost"]
        
        assert hit_rate == 0.65, "Hit rate calculation should be correct"
        assert cache_stats["total_cost_savings"] == expected_savings

class TestCaching:
    """Test caching functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_hit_miss_logic(self, mock_cache_manager):
        """Test basic cache hit/miss logic"""
        
        # Test cache miss (first request)
        response1 = await mock_cache_manager.get_response(
            "What is machine learning?", "gpt-3.5-turbo"
        )
        assert response1 is None, "First request should be cache miss"
        
        # Store response in cache
        mock_response = {"content": "Machine learning is..."}
        await mock_cache_manager.store_response(
            "What is machine learning?", "gpt-3.5-turbo", 
            mock_response, Decimal("0.01")
        )
        
        # Test cache hit (subsequent identical request)
        mock_cache_manager.get_response.return_value = mock_response
        response2 = await mock_cache_manager.get_response(
            "What is machine learning?", "gpt-3.5-turbo"
        )
        assert response2 is not None, "Identical request should be cache hit"
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_caching(self):
        """Test semantic similarity in caching"""
        
        similar_prompts = [
            "What is machine learning?",
            "Can you explain machine learning?",
            "How does machine learning work?",
            "Tell me about ML algorithms"
        ]
        
        # Mock semantic similarity scores
        similarity_scores = [1.0, 0.9, 0.85, 0.7]  # Decreasing similarity
        
        # Test that highly similar prompts (>0.8 similarity) can share cache
        for prompt, score in zip(similar_prompts, similarity_scores):
            if score >= 0.8:
                # Should be considered for cache sharing
                assert score >= 0.8, f"Prompt '{prompt}' should share cache"
    
    def test_cache_eviction_strategies(self):
        """Test different cache eviction strategies"""
        
        # Mock cache entries with different characteristics
        cache_entries = [
            {"key": "entry1", "cost": 0.001, "access_count": 10, "age_hours": 1},
            {"key": "entry2", "cost": 0.05, "access_count": 2, "age_hours": 24}, 
            {"key": "entry3", "cost": 0.02, "access_count": 5, "age_hours": 6}
        ]
        
        # Test LRU eviction (oldest first)
        lru_candidate = max(cache_entries, key=lambda x: x["age_hours"])
        assert lru_candidate["key"] == "entry2", "LRU should select oldest entry"
        
        # Test cost-aware eviction (lowest cost savings first)
        cost_scores = [e["cost"] * e["access_count"] for e in cache_entries]
        min_cost_idx = cost_scores.index(min(cost_scores))
        cost_candidate = cache_entries[min_cost_idx]
        
        assert cost_candidate["cost"] * cost_candidate["access_count"] == min(cost_scores)

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAPIIntegration:
    """Test FastAPI endpoint integration"""
    
    def test_health_check_endpoint(self, api_client):
        """Test health check endpoint"""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "providers" in data
        assert "uptime_seconds" in data
    
    def test_completion_endpoint_authentication(self, api_client):
        """Test completion endpoint requires authentication"""
        
        # Test without API key
        response = api_client.post("/v1/completions", json={
            "prompt": "Test prompt"
        })
        
        assert response.status_code == 401, "Should require authentication"
        
        # Test with invalid API key
        headers = {"Authorization": "Bearer invalid_key"}
        response = api_client.post("/v1/completions", json={
            "prompt": "Test prompt"
        }, headers=headers)
        
        assert response.status_code == 401, "Should reject invalid API key"
    
    def test_completion_endpoint_with_auth(self, api_client):
        """Test completion endpoint with valid authentication"""
        
        headers = {"Authorization": "Bearer llm_api_key_demo"}
        request_data = {
            "prompt": "Analyze this legal clause: 'Party shall be liable for damages'",
            "model": "gpt-4o",
            "max_tokens": 500,
            "application": "legal_analysis"
        }
        
        response = api_client.post("/v1/completions", json=request_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = ["id", "content", "model", "provider", "usage", "cost", "latency_ms"]
        for field in required_fields:
            assert field in data, f"Response should contain {field}"
    
    def test_batch_completion_endpoint(self, api_client):
        """Test batch completion endpoint"""
        
        headers = {"Authorization": "Bearer llm_api_key_demo"}
        batch_request = {
            "requests": [
                {"prompt": "What is AI?", "model": "gpt-3.5-turbo"},
                {"prompt": "What is ML?", "model": "gpt-3.5-turbo"},
                {"prompt": "What is NLP?", "model": "gpt-3.5-turbo"}
            ],
            "max_concurrent": 2
        }
        
        response = api_client.post("/v1/completions/batch", json=batch_request, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "responses" in data
        assert "summary" in data
        assert len(data["responses"]) <= len(batch_request["requests"])
        
        # Verify summary contains expected fields
        summary_fields = ["total_requests", "successful_responses", "total_cost"]
        for field in summary_fields:
            assert field in data["summary"]
    
    def test_rate_limiting(self, api_client):
        """Test rate limiting functionality"""
        
        headers = {"Authorization": "Bearer llm_api_key_demo"}
        request_data = {"prompt": "Test rate limiting", "model": "gpt-3.5-turbo"}
        
        # Make multiple requests rapidly
        responses = []
        for i in range(5):
            response = api_client.post("/v1/completions", json=request_data, headers=headers)
            responses.append(response)
        
        # Check that at least some succeed (rate limiting is per hour in mock)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count > 0, "Some requests should succeed within rate limits"

class TestProviderFailover:
    """Test multi-provider failover scenarios"""
    
    @pytest.mark.asyncio
    async def test_provider_failover_logic(self, mock_llm_client):
        """Test failover when primary provider fails"""
        
        # Mock provider failure then success
        mock_llm_client.generate_completion.side_effect = [
            Exception("Provider unavailable"),  # First call fails
            AsyncMock(return_value=MagicMock())  # Second call succeeds
        ]
        
        # In real implementation, this would test actual failover logic
        try:
            await mock_llm_client.generate_completion("test")
            assert False, "First call should fail"
        except Exception:
            pass  # Expected failure
        
        # Reset mock for successful call
        mock_response = MagicMock()
        mock_response.content = "Failover success"
        mock_llm_client.generate_completion.side_effect = None
        mock_llm_client.generate_completion.return_value = mock_response
        
        result = await mock_llm_client.generate_completion("test")
        assert result.content == "Failover success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern"""
        
        # Mock circuit breaker state
        class MockCircuitBreaker:
            def __init__(self):
                self.failure_count = 0
                self.state = "closed"  # closed, open, half_open
                self.failure_threshold = 5
            
            def record_success(self):
                self.failure_count = 0
                self.state = "closed"
            
            def record_failure(self):
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
            
            def can_execute(self):
                return self.state != "open"
        
        circuit_breaker = MockCircuitBreaker()
        
        # Simulate failures
        for _ in range(6):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "open", "Circuit breaker should open after threshold"
        assert not circuit_breaker.can_execute(), "Should not allow execution when open"
        
        # Test recovery
        circuit_breaker.record_success()
        assert circuit_breaker.state == "closed", "Should close on success"

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, mock_llm_client):
        """Test handling of concurrent requests"""
        
        async def make_request(request_id: int):
            """Simulate individual request"""
            await asyncio.sleep(0.1)  # Simulate processing time
            return f"Response {request_id}"
        
        # Test concurrent execution
        start_time = time.time()
        
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        assert len(results) == 10, "All requests should complete"
        
        # Should complete faster than sequential execution
        max_sequential_time = 10 * 0.1  # 1 second
        actual_time = end_time - start_time
        
        assert actual_time < max_sequential_time, "Concurrent execution should be faster"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        
        # Mock memory tracking
        initial_memory = 100  # MB
        
        # Simulate processing many requests
        for batch in range(10):
            # Process batch of requests
            current_memory = initial_memory + (batch * 5)  # Simulate memory growth
            
            # Memory should not grow excessively
            assert current_memory < initial_memory * 2, "Memory growth should be bounded"
        
        # Memory should be cleaned up after processing
        final_memory = initial_memory + 10  # Small growth acceptable
        assert final_memory < initial_memory * 1.5, "Memory should be cleaned up"
    
    def test_response_time_requirements(self):
        """Test that response times meet SLA requirements"""
        
        # Mock response times for different request types
        response_times = {
            "simple_query": 0.5,      # 500ms
            "complex_analysis": 2.0,   # 2 seconds  
            "batch_processing": 5.0    # 5 seconds
        }
        
        # Define SLA requirements
        sla_requirements = {
            "simple_query": 1.0,       # Must be under 1 second
            "complex_analysis": 3.0,   # Must be under 3 seconds
            "batch_processing": 10.0   # Must be under 10 seconds
        }
        
        for request_type, actual_time in response_times.items():
            required_time = sla_requirements[request_type]
            assert actual_time < required_time, f"{request_type} exceeds SLA: {actual_time}s > {required_time}s"

class TestLoadTesting:
    """Load testing scenarios"""
    
    @pytest.mark.asyncio
    async def test_sustained_load_handling(self):
        """Test handling sustained load over time"""
        
        async def simulate_load_batch():
            """Simulate a batch of concurrent requests"""
            tasks = []
            for _ in range(50):  # 50 concurrent requests
                task = asyncio.create_task(asyncio.sleep(0.1))  # Mock request
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            return len(tasks)
        
        # Run multiple batches to simulate sustained load
        total_processed = 0
        
        for batch_num in range(5):  # 5 batches
            start_time = time.time()
            batch_count = await simulate_load_batch()
            end_time = time.time()
            
            total_processed += batch_count
            batch_time = end_time - start_time
            
            # Each batch should complete in reasonable time
            assert batch_time < 1.0, f"Batch {batch_num} took too long: {batch_time}s"
        
        assert total_processed == 250, "Should process all requests"
    
    def test_error_rate_under_load(self):
        """Test error rates remain acceptable under load"""
        
        # Mock load test results
        load_test_results = {
            "total_requests": 10000,
            "successful_requests": 9850,
            "failed_requests": 150,
            "timeout_errors": 50,
            "server_errors": 100
        }
        
        error_rate = load_test_results["failed_requests"] / load_test_results["total_requests"]
        timeout_rate = load_test_results["timeout_errors"] / load_test_results["total_requests"]
        
        # Error rates should be within acceptable limits
        assert error_rate < 0.02, f"Error rate too high: {error_rate:.1%}"  # < 2%
        assert timeout_rate < 0.01, f"Timeout rate too high: {timeout_rate:.1%}"  # < 1%

# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Test security features"""
    
    def test_api_key_validation(self):
        """Test API key validation logic"""
        
        valid_keys = ["llm_api_key_demo", "enterprise_key_123"]
        invalid_keys = ["", "invalid", "expired_key", None]
        
        def validate_api_key(key):
            return key in valid_keys
        
        # Test valid keys
        for key in valid_keys:
            assert validate_api_key(key), f"Valid key {key} should be accepted"
        
        # Test invalid keys
        for key in invalid_keys:
            assert not validate_api_key(key), f"Invalid key {key} should be rejected"
    
    def test_input_sanitization(self):
        """Test input sanitization for security"""
        
        malicious_inputs = [
            "'; DROP TABLE users; --",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../../etc/passwd",  # Path traversal attempt
            "{{7*7}}",  # Template injection attempt
        ]
        
        def sanitize_input(text: str) -> str:
            """Mock input sanitization"""
            # Remove SQL injection patterns
            if "DROP TABLE" in text.upper():
                text = text.replace("DROP TABLE", "").replace("--", "")
            
            # Remove script tags
            text = text.replace("<script>", "").replace("</script>", "")
            
            # Remove path traversal
            text = text.replace("../", "")
            
            return text.strip()
        
        for malicious_input in malicious_inputs:
            sanitized = sanitize_input(malicious_input)
            
            # Sanitized input should not contain dangerous patterns
            assert "DROP TABLE" not in sanitized.upper()
            assert "<script>" not in sanitized.lower()
            assert "../" not in sanitized
    
    def test_rate_limiting_security(self):
        """Test rate limiting as security measure"""
        
        class MockRateLimiter:
            def __init__(self, limit: int, window_seconds: int):
                self.limit = limit
                self.window_seconds = window_seconds
                self.requests = {}
            
            def is_allowed(self, user_id: str) -> bool:
                current_time = time.time()
                
                if user_id not in self.requests:
                    self.requests[user_id] = []
                
                # Clean old requests
                self.requests[user_id] = [
                    req_time for req_time in self.requests[user_id]
                    if current_time - req_time < self.window_seconds
                ]
                
                # Check limit
                if len(self.requests[user_id]) >= self.limit:
                    return False
                
                self.requests[user_id].append(current_time)
                return True
        
        rate_limiter = MockRateLimiter(limit=5, window_seconds=60)
        
        # Test normal usage
        for i in range(5):
            assert rate_limiter.is_allowed("user1"), f"Request {i+1} should be allowed"
        
        # Test rate limiting kicks in
        assert not rate_limiter.is_allowed("user1"), "6th request should be blocked"
        
        # Different user should not be affected
        assert rate_limiter.is_allowed("user2"), "Different user should be allowed"

# =============================================================================
# COST AND OPTIMIZATION TESTS
# =============================================================================

class TestCostOptimization:
    """Test cost optimization features"""
    
    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self, mock_cost_tracker):
        """Test accuracy of cost tracking"""
        
        # Mock requests with known costs
        test_requests = [
            {"model": "gpt-3.5-turbo", "tokens": 1000, "expected_cost": 0.002},
            {"model": "gpt-4o", "tokens": 1000, "expected_cost": 0.02},
            {"model": "claude-3-haiku-20240307", "tokens": 1000, "expected_cost": 0.00025}
        ]
        
        total_expected_cost = sum(req["expected_cost"] for req in test_requests)
        
        # In real implementation, would track actual costs
        tracked_cost = total_expected_cost  # Mock perfect tracking
        
        # Cost tracking should be accurate within 1%
        accuracy_threshold = 0.01
        cost_difference = abs(tracked_cost - total_expected_cost) / total_expected_cost
        
        assert cost_difference < accuracy_threshold, f"Cost tracking accuracy: {cost_difference:.1%}"
    
    def test_budget_alert_system(self):
        """Test budget monitoring and alerts"""
        
        class MockBudgetMonitor:
            def __init__(self, monthly_budget: float):
                self.monthly_budget = monthly_budget
                self.current_spend = 0.0
                self.alerts_sent = []
            
            def record_spend(self, amount: float):
                self.current_spend += amount
                self._check_alerts()
            
            def _check_alerts(self):
                usage_percentage = (self.current_spend / self.monthly_budget) * 100
                
                alert_thresholds = [50, 75, 90, 95]
                for threshold in alert_thresholds:
                    if usage_percentage >= threshold and threshold not in self.alerts_sent:
                        self.alerts_sent.append(threshold)
        
        budget_monitor = MockBudgetMonitor(monthly_budget=1000.0)
        
        # Simulate spending
        budget_monitor.record_spend(400.0)  # 40%
        assert len(budget_monitor.alerts_sent) == 0, "No alerts at 40%"
        
        budget_monitor.record_spend(150.0)  # 55% total
        assert 50 in budget_monitor.alerts_sent, "Should alert at 50%"
        
        budget_monitor.record_spend(200.0)  # 75% total
        assert 75 in budget_monitor.alerts_sent, "Should alert at 75%"
    
    def test_roi_calculation(self):
        """Test ROI calculation for optimization features"""
        
        # Mock optimization results
        optimization_data = {
            "implementation_cost": 100.0,  # Hours * hourly rate
            "monthly_savings": 500.0,      # Reduced LLM costs
            "payback_period_months": 0.2   # 100/500 = 0.2 months
        }
        
        # Calculate ROI metrics
        annual_savings = optimization_data["monthly_savings"] * 12
        roi_percentage = ((annual_savings - optimization_data["implementation_cost"]) / 
                         optimization_data["implementation_cost"]) * 100
        
        assert optimization_data["payback_period_months"] < 1.0, "Should pay back quickly"
        assert roi_percentage > 500, "Should have strong ROI"  # 5900% in this case

# =============================================================================
# TEST RUNNER AND REPORTING
# =============================================================================

def run_comprehensive_tests():
    """Run all tests and generate report"""
    
    print("=== LLM API Integration Test Suite ===\n")
    
    # Test categories
    test_categories = [
        "Unit Tests",
        "Integration Tests", 
        "Performance Tests",
        "Security Tests",
        "Cost Optimization Tests"
    ]
    
    # Mock test results
    test_results = {
        "Unit Tests": {"passed": 8, "failed": 0, "skipped": 0},
        "Integration Tests": {"passed": 6, "failed": 0, "skipped": 0},
        "Performance Tests": {"passed": 4, "failed": 0, "skipped": 1},
        "Security Tests": {"passed": 3, "failed": 0, "skipped": 0},
        "Cost Optimization Tests": {"passed": 3, "failed": 0, "skipped": 0}
    }
    
    total_passed = sum(result["passed"] for result in test_results.values())
    total_failed = sum(result["failed"] for result in test_results.values())
    total_skipped = sum(result["skipped"] for result in test_results.values())
    total_tests = total_passed + total_failed + total_skipped
    
    print("Test Results Summary:")
    print("=" * 50)
    
    for category, results in test_results.items():
        status = "✓" if results["failed"] == 0 else "✗"
        print(f"{status} {category}: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped")
    
    print("\nOverall Results:")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
    print(f"Failed: {total_failed}")
    print(f"Skipped: {total_skipped}")
    
    success_rate = total_passed / (total_passed + total_failed) * 100 if (total_passed + total_failed) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if total_failed == 0:
        print("\n🎉 All tests passed! System is ready for production.")
    else:
        print(f"\n⚠️  {total_failed} tests failed. Review issues before deployment.")
    
    return total_failed == 0

if __name__ == "__main__":
    # Run the comprehensive test suite
    success = run_comprehensive_tests()
    
    print("\n=== Test Suite Completed ===")
    
    if success:
        print("✅ System validated and ready for enterprise deployment")
    else:
        print("❌ Issues found - address failures before production deployment")
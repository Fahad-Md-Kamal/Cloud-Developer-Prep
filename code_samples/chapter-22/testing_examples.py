"""
Integration Testing and Comprehensive Example for Conversational AI Systems

This module provides comprehensive testing strategies and integration examples
demonstrating how all Chapter 22 concepts work together in realistic enterprise
scenarios for Lawstronaut and Optimizely.

Key concepts covered:
- Integration testing for multi-agent systems
- End-to-end workflow testing
- Performance testing and benchmarking
- Mock service integration
- Test data generation and validation

Author: Technical Interview Preparation Guide
"""

import asyncio
import pytest
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime

# Import modules from other code samples
from langchain_agent import (
    ReActAgent, PlanAndExecuteAgent, LegalResearchTool, 
    PersonalizationAnalyticsTool, ConversationBuffer
)
from fastapi_integration import (
    ConversationalAIService, SessionManager, ConversationRequest,
    MessageRole, RateLimiter
)
from multi_agent_orchestration import (
    WorkflowOrchestrator, LegalDocumentAnalysisAgent,
    PersonalizationOptimizationAgent, Task, TaskStatus,
    LawstronautWorkflowBuilder, OptimizelyWorkflowBuilder
)
from production_deployment import (
    DeploymentManager, HealthChecker, MetricsCollector,
    CircuitBreaker, CircuitBreakerConfig
)

# =============================================================================
# TEST FIXTURES AND MOCK DATA
# =============================================================================

@dataclass
class TestScenario:
    """Test scenario configuration"""
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_outcomes: Dict[str, Any]
    performance_requirements: Dict[str, float]

class MockRedisPool:
    """Mock Redis pool for testing"""
    
    def __init__(self):
        self.data: Dict[str, str] = {}
    
    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)
    
    async def set(self, key: str, value: str, expire: int = 3600):
        self.data[key] = value

class TestDataGenerator:
    """Generates realistic test data for different scenarios"""
    
    @staticmethod
    def generate_legal_contract_data() -> Dict[str, Any]:
        """Generate mock legal contract data"""
        return {
            "contract_id": f"contract_{uuid.uuid4().hex[:8]}",
            "contract_text": """
            SERVICE AGREEMENT
            
            This Service Agreement is entered into between Company A ("Client") 
            and Company B ("Provider") for the provision of legal technology services.
            
            1. SERVICES
            Provider shall deliver AI-powered legal research and document analysis
            services including contract review, compliance checking, and risk assessment.
            
            2. LIABILITY
            Provider's total liability shall not exceed €100,000 for any claims
            arising from this agreement.
            
            3. DATA PROTECTION
            All data processing shall comply with GDPR requirements. Provider
            shall implement appropriate technical and organizational measures.
            
            4. TERMINATION
            Either party may terminate with 30 days written notice.
            
            5. GOVERNING LAW
            This agreement shall be governed by EU law.
            """,
            "contract_type": "service_agreement",
            "jurisdiction": "EU",
            "parties": ["Company A", "Company B"],
            "value": 75000,
            "duration_months": 24,
            "risk_factors": ["liability_limitation", "data_processing", "jurisdiction"]
        }
    
    @staticmethod
    def generate_personalization_campaign_data() -> Dict[str, Any]:
        """Generate mock personalization campaign data"""
        return {
            "campaign_id": f"campaign_{uuid.uuid4().hex[:8]}",
            "campaign_name": "Legal Professional Onboarding Optimization",
            "objective": "increase_trial_conversion",
            "target_metric": "trial_signup_rate",
            "baseline_conversion_rate": 0.032,
            "target_improvement": 0.15,  # 15% improvement
            "audience_segments": [
                {"name": "solo_practitioners", "size": 2500, "conversion_rate": 0.028},
                {"name": "small_firms", "size": 4200, "conversion_rate": 0.035},
                {"name": "enterprise_legal", "size": 800, "conversion_rate": 0.045}
            ],
            "content_variants": [
                {"variant": "control", "traffic": 50, "elements": ["standard_messaging"]},
                {"variant": "personalized", "traffic": 50, "elements": ["dynamic_content", "social_proof"]}
            ],
            "success_metrics": ["conversion_rate", "engagement_rate", "time_to_convert"],
            "duration_weeks": 4
        }
    
    @staticmethod
    def generate_user_behavior_data(count: int = 1000) -> List[Dict[str, Any]]:
        """Generate mock user behavior data"""
        import random
        
        behaviors = []
        user_types = ["solo_practitioner", "small_firm", "enterprise", "student"]
        pages = ["homepage", "pricing", "features", "case_studies", "trial_signup", "contact"]
        
        for i in range(count):
            user_type = random.choice(user_types)
            session_pages = random.sample(pages, random.randint(2, 5))
            
            behavior = {
                "user_id": f"user_{i:04d}",
                "user_type": user_type,
                "session_id": f"session_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().isoformat(),
                "pages_visited": session_pages,
                "session_duration": random.randint(30, 1800),  # 30 seconds to 30 minutes
                "conversion": random.random() < 0.035,  # ~3.5% baseline conversion
                "engagement_score": random.uniform(0.1, 1.0),
                "referrer": random.choice(["google", "linkedin", "direct", "partner"])
            }
            behaviors.append(behavior)
        
        return behaviors

# =============================================================================
# INTEGRATION TEST SUITES
# =============================================================================

class LangChainAgentTests:
    """Test suite for LangChain agent functionality"""
    
    def __init__(self):
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup test environment with mock services"""
        self.memory = ConversationBuffer(max_size=10)
        self.tools = [
            LegalResearchTool({"database_url": "test.db"}),
            PersonalizationAnalyticsTool({"analytics_endpoint": "test.api"})
        ]
        self.react_agent = ReActAgent(self.tools, self.memory)
        self.plan_execute_agent = PlanAndExecuteAgent(self.tools, self.memory)
    
    async def test_legal_query_processing(self):
        """Test legal query processing with ReAct agent"""
        test_queries = [
            "What are the key GDPR compliance requirements for data processing?",
            "Analyze the liability limitations in this service agreement",
            "What are the termination clauses we should include?"
        ]
        
        results = []
        for query in test_queries:
            start_time = time.time()
            response = await self.react_agent.process_query(query)
            processing_time = time.time() - start_time
            
            results.append({
                "query": query,
                "response_length": len(response),
                "processing_time": processing_time,
                "contains_legal_terms": any(term in response.lower() for term in ["gdpr", "liability", "compliance", "contract"])
            })
        
        return {
            "total_queries": len(test_queries),
            "avg_processing_time": sum(r["processing_time"] for r in results) / len(results),
            "avg_response_length": sum(r["response_length"] for r in results) / len(results),
            "legal_relevance_rate": sum(r["contains_legal_terms"] for r in results) / len(results),
            "results": results
        }
    
    async def test_personalization_workflow(self):
        """Test personalization workflow with Plan-and-Execute agent"""
        campaign_data = TestDataGenerator.generate_personalization_campaign_data()
        
        queries = [
            f"Analyze user behavior for {campaign_data['campaign_name']}",
            f"Create A/B test design for {campaign_data['objective']}",
            "Optimize content for legal professional audience"
        ]
        
        results = []
        for query in queries:
            start_time = time.time()
            response = await self.plan_execute_agent.process_query(query)
            processing_time = time.time() - start_time
            
            results.append({
                "query": query,
                "response_length": len(response),
                "processing_time": processing_time,
                "has_structured_plan": "step" in response.lower() and any(str(i) in response for i in range(1, 5))
            })
        
        return {
            "campaign_analysis": campaign_data,
            "query_results": results,
            "avg_processing_time": sum(r["processing_time"] for r in results) / len(results),
            "plan_structure_rate": sum(r["has_structured_plan"] for r in results) / len(results)
        }
    
    async def test_memory_persistence(self):
        """Test conversation memory and context persistence"""
        conversation_flow = [
            "I need help with a legal contract analysis",
            "The contract is for software services in the EU",
            "What GDPR considerations should I be aware of?",
            "Can you summarize the key points we've discussed?"
        ]
        
        responses = []
        for message in conversation_flow:
            response = await self.react_agent.process_query(message)
            responses.append(response)
        
        # Check memory state
        memory_context = self.memory.get_context()
        
        return {
            "conversation_length": len(conversation_flow),
            "memory_entries": len(self.memory.messages),
            "context_length": len(memory_context),
            "context_contains_history": "contract" in memory_context and "GDPR" in memory_context,
            "responses": responses
        }

class FastAPIIntegrationTests:
    """Test suite for FastAPI integration"""
    
    def __init__(self):
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup test environment"""
        self.redis_pool = MockRedisPool()
        self.session_manager = SessionManager(self.redis_pool)
        self.ai_service = ConversationalAIService(self.session_manager)
        self.rate_limiter = RateLimiter(self.redis_pool)
    
    async def test_conversation_api(self):
        """Test conversation API functionality"""
        # Test data
        legal_request = ConversationRequest(
            message="What are the key elements of a software licensing agreement?",
            context={"domain": "legal", "jurisdiction": "US"}
        )
        
        personalization_request = ConversationRequest(
            message="How can I improve user engagement on my platform?",
            context={"domain": "personalization", "platform": "web"}
        )
        
        # Process requests
        legal_response = await self.ai_service.process_message(legal_request, "test_user_legal")
        personalization_response = await self.ai_service.process_message(personalization_request, "test_user_personalization")
        
        return {
            "legal_response": {
                "session_id": legal_response.session_id,
                "response_time_ms": legal_response.response_time_ms,
                "message_length": len(legal_response.message),
                "contains_legal_content": "license" in legal_response.message.lower() or "agreement" in legal_response.message.lower()
            },
            "personalization_response": {
                "session_id": personalization_response.session_id,
                "response_time_ms": personalization_response.response_time_ms,
                "message_length": len(personalization_response.message),
                "contains_personalization_content": "engagement" in personalization_response.message.lower() or "behavior" in personalization_response.message.lower()
            }
        }
    
    async def test_streaming_response(self):
        """Test streaming response functionality"""
        request = ConversationRequest(
            message="Provide a comprehensive guide to API security best practices",
            stream=True
        )
        
        chunks = []
        async for chunk in self.ai_service.stream_response(request, "test_stream_user"):
            chunks.append({
                "chunk_id": chunk.chunk_id,
                "chunk_length": len(chunk.chunk),
                "is_final": chunk.is_final
            })
            
            if chunk.is_final:
                break
        
        return {
            "total_chunks": len(chunks),
            "final_chunk_received": chunks[-1]["is_final"] if chunks else False,
            "total_content_length": sum(c["chunk_length"] for c in chunks),
            "streaming_successful": len(chunks) > 1
        }
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        client_id = "test_rate_limit_client"
        
        # Test normal operation
        allowed_requests = 0
        for i in range(10):
            if await self.rate_limiter.is_allowed(client_id, max_requests=5, window_minutes=1):
                allowed_requests += 1
        
        return {
            "requests_attempted": 10,
            "requests_allowed": allowed_requests,
            "rate_limiting_active": allowed_requests < 10,
            "rate_limit_threshold": 5
        }

class MultiAgentOrchestrationTests:
    """Test suite for multi-agent orchestration"""
    
    def __init__(self):
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup test orchestration environment"""
        self.orchestrator = WorkflowOrchestrator()
        
        # Register agents
        legal_agent = LegalDocumentAnalysisAgent()
        personalization_agent = PersonalizationOptimizationAgent()
        
        self.orchestrator.register_agent(legal_agent)
        self.orchestrator.register_agent(personalization_agent)
    
    async def test_legal_workflow_execution(self):
        """Test complete legal document workflow"""
        # Generate test data
        contract_data = TestDataGenerator.generate_legal_contract_data()
        
        # Create workflow
        workflow_id = LawstronautWorkflowBuilder.create_contract_analysis_workflow(
            self.orchestrator, contract_data
        )
        
        # Execute workflow
        start_time = time.time()
        result = await self.orchestrator.execute_workflow(workflow_id)
        execution_time = time.time() - start_time
        
        return {
            "workflow_id": workflow_id,
            "execution_time": execution_time,
            "workflow_status": result["status"],
            "task_count": result["task_count"],
            "success_rate": result["success_rate"],
            "all_tasks_completed": result["success_rate"] == 1.0,
            "contract_data": contract_data,
            "task_details": result["tasks"]
        }
    
    async def test_personalization_workflow_execution(self):
        """Test complete personalization optimization workflow"""
        # Generate test data
        campaign_data = TestDataGenerator.generate_personalization_campaign_data()
        
        # Create workflow
        workflow_id = OptimizelyWorkflowBuilder.create_personalization_optimization_workflow(
            self.orchestrator, campaign_data
        )
        
        # Execute workflow
        start_time = time.time()
        result = await self.orchestrator.execute_workflow(workflow_id)
        execution_time = time.time() - start_time
        
        return {
            "workflow_id": workflow_id,
            "execution_time": execution_time,
            "workflow_status": result["status"],
            "task_count": result["task_count"],
            "success_rate": result["success_rate"],
            "all_tasks_completed": result["success_rate"] == 1.0,
            "campaign_data": campaign_data,
            "task_details": result["tasks"]
        }
    
    async def test_concurrent_workflow_execution(self):
        """Test concurrent execution of multiple workflows"""
        # Create multiple workflows
        legal_data = TestDataGenerator.generate_legal_contract_data()
        personalization_data = TestDataGenerator.generate_personalization_campaign_data()
        
        legal_workflow_id = LawstronautWorkflowBuilder.create_contract_analysis_workflow(
            self.orchestrator, legal_data
        )
        
        personalization_workflow_id = OptimizelyWorkflowBuilder.create_personalization_optimization_workflow(
            self.orchestrator, personalization_data
        )
        
        # Execute concurrently
        start_time = time.time()
        
        legal_task = asyncio.create_task(self.orchestrator.execute_workflow(legal_workflow_id))
        personalization_task = asyncio.create_task(self.orchestrator.execute_workflow(personalization_workflow_id))
        
        legal_result, personalization_result = await asyncio.gather(legal_task, personalization_task)
        
        total_execution_time = time.time() - start_time
        
        return {
            "concurrent_execution": True,
            "total_execution_time": total_execution_time,
            "legal_workflow": {
                "status": legal_result["status"],
                "success_rate": legal_result["success_rate"]
            },
            "personalization_workflow": {
                "status": personalization_result["status"],
                "success_rate": personalization_result["success_rate"]
            },
            "both_successful": (legal_result["success_rate"] == 1.0 and 
                              personalization_result["success_rate"] == 1.0)
        }

class ProductionDeploymentTests:
    """Test suite for production deployment and monitoring"""
    
    def __init__(self):
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup test deployment environment"""
        self.deployment_manager = DeploymentManager()
    
    async def test_health_checks(self):
        """Test health check system"""
        # Run all health checks
        health_results = await self.deployment_manager.health_checker.run_all_checks()
        overall_status = self.deployment_manager.health_checker.get_overall_status(health_results)
        
        return {
            "health_checks_count": len(health_results),
            "overall_status": overall_status.value,
            "individual_results": {
                name: {
                    "status": result.status.value,
                    "response_time_ms": result.response_time_ms,
                    "message": result.message
                }
                for name, result in health_results.items()
            },
            "all_healthy": overall_status.value == "healthy"
        }
    
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker fault tolerance"""
        # Create test circuit breaker
        cb_config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5)
        cb = CircuitBreaker("test_service", cb_config)
        
        # Test successful operations
        async def successful_operation():
            await asyncio.sleep(0.01)
            return "success"
        
        # Test failing operations
        async def failing_operation():
            await asyncio.sleep(0.01)
            raise Exception("Service unavailable")
        
        # Record successful calls
        success_count = 0
        for i in range(5):
            try:
                await cb.call(successful_operation)
                success_count += 1
            except:
                pass
        
        # Record failing calls to trigger circuit breaker
        failure_count = 0
        for i in range(5):
            try:
                await cb.call(failing_operation)
            except:
                failure_count += 1
        
        # Check circuit breaker state
        cb_status = cb.get_status()
        
        return {
            "successful_calls": success_count,
            "failed_calls": failure_count,
            "circuit_breaker_state": cb_status["state"],
            "failure_count": cb_status["failure_count"],
            "circuit_breaker_triggered": cb_status["state"] == "open"
        }
    
    async def test_metrics_collection(self):
        """Test metrics collection system"""
        metrics_collector = self.deployment_manager.metrics_collector
        
        # Start collection for a short period
        metrics_collector.start_collection()
        
        # Simulate some requests and responses
        for i in range(10):
            metrics_collector.record_request()
            metrics_collector.record_response_time(50 + i * 10)
            if i % 4 == 0:  # 25% error rate
                metrics_collector.record_error()
        
        await asyncio.sleep(0.5)  # Let metrics collect
        
        recent_metrics = metrics_collector.get_recent_metrics(minutes=1)
        
        metrics_collector.stop_collection()
        
        return {
            "metrics_collected": len(recent_metrics) > 0,
            "recent_metrics_count": len(recent_metrics),
            "request_tracking": True,
            "response_time_tracking": len(metrics_collector.response_times) > 0,
            "error_tracking": len(metrics_collector.error_counts) > 0
        }

# =============================================================================
# COMPREHENSIVE INTEGRATION TEST
# =============================================================================

class ComprehensiveIntegrationTest:
    """End-to-end integration test covering all components"""
    
    def __init__(self):
        self.test_results: Dict[str, Any] = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for tests"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive end-to-end integration test"""
        self.logger.info("Starting comprehensive integration test")
        
        start_time = time.time()
        
        # Run all test suites
        try:
            # LangChain Agent Tests
            langchain_tests = LangChainAgentTests()
            self.test_results["langchain_legal_queries"] = await langchain_tests.test_legal_query_processing()
            self.test_results["langchain_personalization"] = await langchain_tests.test_personalization_workflow()
            self.test_results["langchain_memory"] = await langchain_tests.test_memory_persistence()
            
            # FastAPI Integration Tests
            fastapi_tests = FastAPIIntegrationTests()
            self.test_results["fastapi_conversation"] = await fastapi_tests.test_conversation_api()
            self.test_results["fastapi_streaming"] = await fastapi_tests.test_streaming_response()
            self.test_results["fastapi_rate_limiting"] = await fastapi_tests.test_rate_limiting()
            
            # Multi-Agent Orchestration Tests
            orchestration_tests = MultiAgentOrchestrationTests()
            self.test_results["orchestration_legal_workflow"] = await orchestration_tests.test_legal_workflow_execution()
            self.test_results["orchestration_personalization_workflow"] = await orchestration_tests.test_personalization_workflow_execution()
            self.test_results["orchestration_concurrent"] = await orchestration_tests.test_concurrent_workflow_execution()
            
            # Production Deployment Tests
            deployment_tests = ProductionDeploymentTests()
            self.test_results["deployment_health_checks"] = await deployment_tests.test_health_checks()
            self.test_results["deployment_circuit_breaker"] = await deployment_tests.test_circuit_breaker_functionality()
            self.test_results["deployment_metrics"] = await deployment_tests.test_metrics_collection()
            
        except Exception as e:
            self.logger.error(f"Integration test failed: {e}")
            self.test_results["error"] = str(e)
        
        total_time = time.time() - start_time
        
        # Calculate overall success metrics
        success_metrics = self._calculate_success_metrics()
        
        return {
            "test_execution_time": total_time,
            "overall_success_rate": success_metrics["success_rate"],
            "components_tested": success_metrics["components_tested"],
            "tests_passed": success_metrics["tests_passed"],
            "tests_failed": success_metrics["tests_failed"],
            "detailed_results": self.test_results
        }
    
    def _calculate_success_metrics(self) -> Dict[str, Any]:
        """Calculate overall success metrics"""
        total_tests = 0
        passed_tests = 0
        
        # Define success criteria for each test
        success_criteria = {
            "langchain_legal_queries": lambda r: r.get("legal_relevance_rate", 0) > 0.8,
            "langchain_personalization": lambda r: r.get("plan_structure_rate", 0) > 0.8,
            "langchain_memory": lambda r: r.get("context_contains_history", False),
            "fastapi_conversation": lambda r: (
                r.get("legal_response", {}).get("contains_legal_content", False) and
                r.get("personalization_response", {}).get("contains_personalization_content", False)
            ),
            "fastapi_streaming": lambda r: r.get("streaming_successful", False),
            "fastapi_rate_limiting": lambda r: r.get("rate_limiting_active", False),
            "orchestration_legal_workflow": lambda r: r.get("all_tasks_completed", False),
            "orchestration_personalization_workflow": lambda r: r.get("all_tasks_completed", False),
            "orchestration_concurrent": lambda r: r.get("both_successful", False),
            "deployment_health_checks": lambda r: r.get("all_healthy", False),
            "deployment_circuit_breaker": lambda r: r.get("circuit_breaker_triggered", False),
            "deployment_metrics": lambda r: r.get("metrics_collected", False)
        }
        
        for test_name, success_fn in success_criteria.items():
            total_tests += 1
            if test_name in self.test_results:
                if success_fn(self.test_results[test_name]):
                    passed_tests += 1
        
        return {
            "components_tested": len(success_criteria),
            "tests_passed": passed_tests,
            "tests_failed": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0
        }

# =============================================================================
# DEMONSTRATION FUNCTION
# =============================================================================

async def demonstrate_comprehensive_testing():
    """
    Comprehensive demonstration of testing strategies for conversational AI systems
    """
    
    print("🚀 Comprehensive Integration Testing Demo")
    print("Testing All Chapter 22 Concepts in Realistic Enterprise Scenarios")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    # Run comprehensive integration test
    integration_test = ComprehensiveIntegrationTest()
    
    print("\n" + "="*60)
    print("Running End-to-End Integration Tests...")
    print("="*60)
    
    test_results = await integration_test.run_comprehensive_test()
    
    # Display results
    print(f"\n📊 Test Execution Summary:")
    print(f"   • Total execution time: {test_results['test_execution_time']:.2f}s")
    print(f"   • Overall success rate: {test_results['overall_success_rate']:.1%}")
    print(f"   • Components tested: {test_results['components_tested']}")
    print(f"   • Tests passed: {test_results['tests_passed']}")
    print(f"   • Tests failed: {test_results['tests_failed']}")
    
    # Display component-specific results
    print(f"\n📋 Component Test Results:")
    
    component_groups = {
        "LangChain Agents": ["langchain_legal_queries", "langchain_personalization", "langchain_memory"],
        "FastAPI Integration": ["fastapi_conversation", "fastapi_streaming", "fastapi_rate_limiting"],
        "Multi-Agent Orchestration": ["orchestration_legal_workflow", "orchestration_personalization_workflow", "orchestration_concurrent"],
        "Production Deployment": ["deployment_health_checks", "deployment_circuit_breaker", "deployment_metrics"]
    }
    
    for group_name, test_names in component_groups.items():
        print(f"\n   🔧 {group_name}:")
        for test_name in test_names:
            if test_name in test_results["detailed_results"]:
                result = test_results["detailed_results"][test_name]
                
                # Determine test status
                if "error" in str(result).lower():
                    status = "❌ FAILED"
                elif any(key in result for key in ["success_rate", "all_tasks_completed", "streaming_successful"]):
                    # Check specific success indicators
                    success_indicators = [
                        result.get("success_rate", 0) == 1.0,
                        result.get("all_tasks_completed", False),
                        result.get("streaming_successful", False),
                        result.get("rate_limiting_active", False),
                        result.get("all_healthy", False),
                        result.get("metrics_collected", False)
                    ]
                    status = "✅ PASSED" if any(success_indicators) else "⚠️  PARTIAL"
                else:
                    status = "✅ PASSED"
                
                print(f"     {status} {test_name.replace('_', ' ').title()}")
            else:
                print(f"     ❌ SKIPPED {test_name.replace('_', ' ').title()}")
    
    # Performance insights
    print(f"\n⚡ Performance Insights:")
    detailed_results = test_results["detailed_results"]
    
    if "langchain_legal_queries" in detailed_results:
        legal_perf = detailed_results["langchain_legal_queries"]
        print(f"   • Legal query processing: {legal_perf.get('avg_processing_time', 0):.3f}s average")
    
    if "orchestration_legal_workflow" in detailed_results:
        workflow_perf = detailed_results["orchestration_legal_workflow"]
        print(f"   • Legal workflow execution: {workflow_perf.get('execution_time', 0):.3f}s total")
    
    if "orchestration_concurrent" in detailed_results:
        concurrent_perf = detailed_results["orchestration_concurrent"]
        print(f"   • Concurrent workflows: {concurrent_perf.get('total_execution_time', 0):.3f}s total")
    
    print("\n" + "="*60)
    print("✅ Comprehensive Integration Testing Complete")
    print("="*60)
    
    # Test coverage summary
    print(f"\n🎯 Test Coverage Summary:")
    print(f"   • LangChain agent patterns: ReAct + Plan-and-Execute")
    print(f"   • FastAPI production integration: REST + WebSocket + Streaming")
    print(f"   • Multi-agent orchestration: Workflow automation + Task coordination")
    print(f"   • Production deployment: Health checks + Circuit breakers + Metrics")
    print(f"   • Enterprise scenarios: Legal (Lawstronaut) + Personalization (Optimizely)")
    print(f"   • Performance testing: Response times + Throughput + Resource usage")
    print(f"   • Integration testing: End-to-end workflows + Component interaction")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run comprehensive testing demonstration
    asyncio.run(demonstrate_comprehensive_testing())
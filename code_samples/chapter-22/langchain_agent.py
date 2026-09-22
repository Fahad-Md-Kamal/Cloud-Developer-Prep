"""
LangChain Agent Architecture Implementation for Enterprise Systems

This module demonstrates LangChain agent architectures applied to realistic
scenarios like those used at Lawstronaut and Optimizely.

Key concepts covered:
- ReAct and Plan-and-Execute agent patterns
- Custom tool creation and integration
- Memory systems for conversation persistence
- Chain composition and orchestration

Real-world applications:
- Legal research assistant for Lawstronaut
- Personalization agent for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import logging
import time
import json
from datetime import datetime
from enum import Enum

# Mock LangChain imports (in real implementation, use actual LangChain)
class BaseTool(ABC):
    @abstractmethod
    def run(self, input_data: str) -> str:
        pass

class BaseMemory(ABC):
    @abstractmethod
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        pass
    
    @abstractmethod
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        pass

class BaseChain(ABC):
    @abstractmethod
    async def arun(self, **kwargs) -> str:
        pass

# =============================================================================
# AGENT TYPES AND EXECUTION PATTERNS
# =============================================================================

class AgentType(Enum):
    REACT = "react"
    PLAN_AND_EXECUTE = "plan_and_execute"
    CONVERSATIONAL = "conversational"

@dataclass
class AgentAction:
    """Represents an action taken by an agent"""
    tool: str
    tool_input: str
    log: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AgentObservation:
    """Represents the result of an agent action"""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class LegalResearchTool(BaseTool):
    """Tool for searching legal databases - Lawstronaut scenario"""
    
    def __init__(self, database_config: Dict[str, Any]):
        self.database_config = database_config
        self.logger = logging.getLogger(__name__)
    
    def run(self, query: str) -> str:
        """
        Search legal database for relevant regulations and case law
        
        Args:
            query: Search query for legal documents
            
        Returns:
            JSON string containing search results
        """
        self.logger.info(f"Searching legal database for: {query}")
        
        # Simulate legal database search
        mock_results = {
            "query": query,
            "results": [
                {
                    "title": "Contract Liability Regulations",
                    "jurisdiction": "EU",
                    "relevance_score": 0.95,
                    "summary": "Key regulations for contract liability in EU jurisdictions"
                },
                {
                    "title": "Data Protection Compliance",
                    "jurisdiction": "GDPR",
                    "relevance_score": 0.87,
                    "summary": "GDPR compliance requirements for data processing"
                }
            ],
            "search_time_ms": 150
        }
        
        return json.dumps(mock_results, indent=2)

class PersonalizationAnalyticsTool(BaseTool):
    """Tool for customer behavior analysis - Optimizely scenario"""
    
    def __init__(self, analytics_config: Dict[str, Any]):
        self.analytics_config = analytics_config
        self.logger = logging.getLogger(__name__)
    
    def run(self, user_data: str) -> str:
        """
        Analyze customer behavior for personalization
        
        Args:
            user_data: JSON string containing user behavior data
            
        Returns:
            JSON string containing analysis results
        """
        self.logger.info(f"Analyzing user behavior for personalization")
        
        try:
            user_info = json.loads(user_data)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON input"})
        
        # Simulate behavior analysis
        mock_analysis = {
            "user_id": user_info.get("user_id", "unknown"),
            "behavior_score": 0.78,
            "preferences": ["technology", "legal-compliance", "automation"],
            "recommended_content": [
                "AI-powered legal research tools",
                "Compliance automation guides",
                "Technology integration best practices"
            ],
            "confidence": 0.85
        }
        
        return json.dumps(mock_analysis, indent=2)

# =============================================================================
# MEMORY SYSTEMS FOR CONVERSATION PERSISTENCE
# =============================================================================

class ConversationBuffer:
    """Buffer for storing recent conversation history"""
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.messages: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation buffer"""
        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        # Keep only the most recent messages
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size:]
    
    def get_context(self) -> str:
        """Get formatted conversation context"""
        context_parts = []
        for msg in self.messages:
            context_parts.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(context_parts)

class EntityMemory:
    """Memory system for tracking entities across conversations"""
    
    def __init__(self):
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text (simplified implementation)"""
        # In real implementation, use spaCy or similar NLP library
        entities = []
        
        # Simple keyword-based entity extraction for demo
        legal_terms = ["contract", "liability", "compliance", "GDPR", "jurisdiction"]
        tech_terms = ["API", "database", "personalization", "analytics"]
        
        text_lower = text.lower()
        
        for term in legal_terms:
            if term.lower() in text_lower:
                entities.append({
                    "text": term,
                    "label": "LEGAL_TERM",
                    "confidence": 0.9
                })
        
        for term in tech_terms:
            if term.lower() in text_lower:
                entities.append({
                    "text": term,
                    "label": "TECH_TERM", 
                    "confidence": 0.85
                })
        
        return entities
    
    def update_entities(self, entities: List[Dict[str, Any]]):
        """Update entity knowledge base"""
        for entity in entities:
            entity_key = f"{entity['label']}:{entity['text']}"
            
            if entity_key not in self.entities:
                self.entities[entity_key] = {
                    "text": entity["text"],
                    "label": entity["label"],
                    "mentions": 0,
                    "first_seen": datetime.now().isoformat(),
                    "contexts": []
                }
            
            self.entities[entity_key]["mentions"] += 1
            self.entities[entity_key]["last_seen"] = datetime.now().isoformat()
    
    def get_relevant_entities(self, query: str) -> List[Dict[str, Any]]:
        """Get entities relevant to the current query"""
        relevant = []
        query_lower = query.lower()
        
        for entity_key, entity_data in self.entities.items():
            if entity_data["text"].lower() in query_lower:
                relevant.append(entity_data)
        
        return sorted(relevant, key=lambda x: x["mentions"], reverse=True)

# =============================================================================
# REACT AGENT IMPLEMENTATION
# =============================================================================

class ReActAgent:
    """ReAct (Reasoning + Acting) Agent implementation"""
    
    def __init__(self, tools: List[BaseTool], memory: ConversationBuffer):
        self.tools = {tool.__class__.__name__: tool for tool in tools}
        self.memory = memory
        self.entity_memory = EntityMemory()
        self.logger = logging.getLogger(__name__)
    
    async def think(self, query: str, context: str) -> str:
        """Generate reasoning about the query"""
        thoughts = []
        
        # Analyze the query
        if "legal" in query.lower() or "compliance" in query.lower():
            thoughts.append("This appears to be a legal research query.")
            thoughts.append("I should use the LegalResearchTool to find relevant regulations.")
        
        if "personalization" in query.lower() or "behavior" in query.lower():
            thoughts.append("This seems to be about user personalization.")
            thoughts.append("I should use the PersonalizationAnalyticsTool to analyze user data.")
        
        # Consider context from memory
        if context:
            thoughts.append(f"Previous context: {context[:100]}...")
        
        return " ".join(thoughts)
    
    async def act(self, action_plan: str) -> AgentObservation:
        """Execute an action based on the reasoning"""
        action_plan_lower = action_plan.lower()
        
        if "legalresearchtool" in action_plan_lower:
            tool = self.tools.get("LegalResearchTool")
            if tool:
                result = tool.run("compliance regulations contract liability")
                return AgentObservation(
                    content=result,
                    metadata={"tool_used": "LegalResearchTool"}
                )
        
        if "personalizationanalyticstool" in action_plan_lower:
            tool = self.tools.get("PersonalizationAnalyticsTool")
            if tool:
                mock_user_data = json.dumps({
                    "user_id": "user_123",
                    "page_views": ["legal-compliance", "ai-tools", "automation"],
                    "session_duration": 1200
                })
                result = tool.run(mock_user_data)
                return AgentObservation(
                    content=result,
                    metadata={"tool_used": "PersonalizationAnalyticsTool"}
                )
        
        return AgentObservation(
            content="I need more specific guidance on which tool to use.",
            metadata={"action": "request_clarification"}
        )
    
    async def process_query(self, query: str) -> str:
        """Process a query using the ReAct pattern"""
        self.logger.info(f"Processing query: {query}")
        
        # Get conversation context
        context = self.memory.get_context()
        
        # Extract and update entities
        entities = self.entity_memory.extract_entities(query)
        self.entity_memory.update_entities(entities)
        
        # Step 1: Think (Reasoning)
        thoughts = await self.think(query, context)
        self.logger.info(f"Thoughts: {thoughts}")
        
        # Step 2: Act (Action)
        observation = await self.act(thoughts)
        self.logger.info(f"Action result: {observation.content[:100]}...")
        
        # Step 3: Generate final answer
        final_answer = self._generate_final_answer(query, thoughts, observation)
        
        # Update memory
        self.memory.add_message("user", query)
        self.memory.add_message("assistant", final_answer)
        
        return final_answer
    
    def _generate_final_answer(self, query: str, thoughts: str, observation: AgentObservation) -> str:
        """Generate the final answer based on reasoning and observations"""
        try:
            # Try to parse tool results
            tool_result = json.loads(observation.content)
            
            if observation.metadata.get("tool_used") == "LegalResearchTool":
                results = tool_result.get("results", [])
                answer_parts = [
                    "Based on my legal research, I found the following relevant information:",
                    ""
                ]
                
                for result in results[:2]:  # Show top 2 results
                    answer_parts.append(
                        f"• {result['title']} ({result['jurisdiction']}) - "
                        f"{result['summary']} (Relevance: {result['relevance_score']:.1%})"
                    )
                
                return "\n".join(answer_parts)
            
            elif observation.metadata.get("tool_used") == "PersonalizationAnalyticsTool":
                answer_parts = [
                    "Based on user behavior analysis, here are the personalization insights:",
                    f"• User preferences: {', '.join(tool_result.get('preferences', []))}",
                    f"• Behavior score: {tool_result.get('behavior_score', 0):.1%}",
                    f"• Confidence level: {tool_result.get('confidence', 0):.1%}",
                    "",
                    "Recommended content:"
                ]
                
                for content in tool_result.get("recommended_content", []):
                    answer_parts.append(f"• {content}")
                
                return "\n".join(answer_parts)
        
        except (json.JSONDecodeError, KeyError):
            pass
        
        return f"I analyzed your query about '{query}' and gathered relevant information, but I need more specific details to provide a complete answer."

# =============================================================================
# PLAN-AND-EXECUTE AGENT IMPLEMENTATION
# =============================================================================

@dataclass
class ExecutionPlan:
    """Represents a structured execution plan"""
    steps: List[str]
    estimated_duration: int  # seconds
    required_tools: List[str]
    success_criteria: List[str]

class PlanAndExecuteAgent:
    """Plan-and-Execute Agent implementation"""
    
    def __init__(self, tools: List[BaseTool], memory: ConversationBuffer):
        self.tools = {tool.__class__.__name__: tool for tool in tools}
        self.memory = memory
        self.logger = logging.getLogger(__name__)
    
    async def create_plan(self, query: str) -> ExecutionPlan:
        """Create a structured execution plan for the query"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["legal", "compliance", "contract"]):
            return ExecutionPlan(
                steps=[
                    "Analyze the legal query requirements",
                    "Search legal database for relevant regulations",
                    "Cross-reference findings with jurisdiction requirements",
                    "Compile comprehensive legal summary"
                ],
                estimated_duration=30,
                required_tools=["LegalResearchTool"],
                success_criteria=[
                    "Found relevant legal regulations",
                    "Identified applicable jurisdictions",
                    "Provided actionable compliance guidance"
                ]
            )
        
        elif any(term in query_lower for term in ["personalization", "user", "behavior"]):
            return ExecutionPlan(
                steps=[
                    "Extract user behavior parameters",
                    "Analyze behavioral patterns and preferences",
                    "Generate personalization recommendations",
                    "Validate recommendations against success metrics"
                ],
                estimated_duration=20,
                required_tools=["PersonalizationAnalyticsTool"],
                success_criteria=[
                    "Identified user preferences",
                    "Generated relevant recommendations",
                    "Achieved high confidence score"
                ]
            )
        
        # Default plan for general queries
        return ExecutionPlan(
            steps=[
                "Analyze query requirements",
                "Determine appropriate tools and resources",
                "Execute information gathering",
                "Synthesize and present results"
            ],
            estimated_duration=15,
            required_tools=["LegalResearchTool", "PersonalizationAnalyticsTool"],
            success_criteria=[
                "Understood query intent",
                "Gathered relevant information",
                "Provided helpful response"
            ]
        )
    
    async def execute_plan(self, plan: ExecutionPlan, query: str) -> List[AgentObservation]:
        """Execute the structured plan"""
        observations = []
        
        for i, step in enumerate(plan.steps):
            self.logger.info(f"Executing step {i+1}: {step}")
            
            # Simulate step execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            if i == 1 and "LegalResearchTool" in plan.required_tools:
                # Execute legal research
                tool = self.tools.get("LegalResearchTool")
                if tool:
                    result = tool.run(query)
                    observations.append(AgentObservation(
                        content=result,
                        metadata={"step": i+1, "tool_used": "LegalResearchTool"}
                    ))
            
            elif i == 1 and "PersonalizationAnalyticsTool" in plan.required_tools:
                # Execute personalization analysis
                tool = self.tools.get("PersonalizationAnalyticsTool")
                if tool:
                    mock_data = json.dumps({"user_id": "plan_exec_user", "query": query})
                    result = tool.run(mock_data)
                    observations.append(AgentObservation(
                        content=result,
                        metadata={"step": i+1, "tool_used": "PersonalizationAnalyticsTool"}
                    ))
            
            else:
                # Generic step execution
                observations.append(AgentObservation(
                    content=f"Completed: {step}",
                    metadata={"step": i+1, "action": "step_completion"}
                ))
        
        return observations
    
    async def process_query(self, query: str) -> str:
        """Process query using plan-and-execute pattern"""
        self.logger.info(f"Creating execution plan for: {query}")
        
        # Step 1: Create Plan
        plan = await self.create_plan(query)
        self.logger.info(f"Created plan with {len(plan.steps)} steps")
        
        # Step 2: Execute Plan
        observations = await self.execute_plan(plan, query)
        
        # Step 3: Synthesize Results
        final_answer = self._synthesize_results(query, plan, observations)
        
        # Update memory
        self.memory.add_message("user", query)
        self.memory.add_message("assistant", final_answer)
        
        return final_answer
    
    def _synthesize_results(self, query: str, plan: ExecutionPlan, observations: List[AgentObservation]) -> str:
        """Synthesize execution results into final answer"""
        answer_parts = [
            f"I executed a {len(plan.steps)}-step plan to address your query:",
            ""
        ]
        
        # Add plan summary
        for i, step in enumerate(plan.steps):
            answer_parts.append(f"{i+1}. {step}")
        
        answer_parts.append("")
        
        # Add key findings from observations
        key_findings = []
        for obs in observations:
            if obs.metadata.get("tool_used") == "LegalResearchTool":
                try:
                    result = json.loads(obs.content)
                    key_findings.append("Legal Research Results:")
                    for legal_result in result.get("results", [])[:2]:
                        key_findings.append(f"  • {legal_result['title']}: {legal_result['summary']}")
                except json.JSONDecodeError:
                    key_findings.append("Legal research completed successfully")
            
            elif obs.metadata.get("tool_used") == "PersonalizationAnalyticsTool":
                try:
                    result = json.loads(obs.content)
                    key_findings.append("Personalization Analysis:")
                    key_findings.append(f"  • Behavior Score: {result.get('behavior_score', 0):.1%}")
                    key_findings.append(f"  • Confidence: {result.get('confidence', 0):.1%}")
                    prefs = result.get('preferences', [])
                    if prefs:
                        key_findings.append(f"  • Key Preferences: {', '.join(prefs)}")
                except json.JSONDecodeError:
                    key_findings.append("Personalization analysis completed successfully")
        
        if key_findings:
            answer_parts.extend(["Key Findings:"] + key_findings)
        
        # Check success criteria
        answer_parts.extend([
            "",
            "Success Criteria Met:",
            *[f"✓ {criteria}" for criteria in plan.success_criteria]
        ])
        
        return "\n".join(answer_parts)

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

class ConversationalAIDemo:
    """Demonstration of conversational AI agent patterns"""
    
    def __init__(self):
        self.setup_logging()
        self.memory = ConversationBuffer(max_size=20)
        
        # Initialize tools
        self.tools = [
            LegalResearchTool({"database_url": "legal.db", "api_key": "demo"}),
            PersonalizationAnalyticsTool({"analytics_endpoint": "analytics.api", "credentials": "demo"})
        ]
        
        # Initialize agents
        self.react_agent = ReActAgent(self.tools, self.memory)
        self.plan_execute_agent = PlanAndExecuteAgent(self.tools, self.memory)
    
    def setup_logging(self):
        """Configure logging for the demo"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def demo_react_agent(self):
        """Demonstrate ReAct agent with legal research scenario"""
        print("\n" + "="*60)
        print("ReAct Agent Demo - Legal Research (Lawstronaut Scenario)")
        print("="*60)
        
        legal_queries = [
            "What are the key compliance requirements for GDPR in contract processing?",
            "Find regulations about data liability in EU jurisdictions",
            "I need information about contract termination clauses"
        ]
        
        for query in legal_queries:
            print(f"\n🔍 Query: {query}")
            print("-" * 50)
            
            start_time = time.time()
            response = await self.react_agent.process_query(query)
            end_time = time.time()
            
            print(f"📋 Response:\n{response}")
            print(f"⏱️  Processing time: {end_time - start_time:.2f}s")
            
            await asyncio.sleep(0.5)  # Brief pause between queries
    
    async def demo_plan_execute_agent(self):
        """Demonstrate Plan-and-Execute agent with personalization scenario"""
        print("\n" + "="*60)
        print("Plan-and-Execute Agent Demo - Personalization (Optimizely Scenario)")
        print("="*60)
        
        personalization_queries = [
            "Analyze user behavior for personalized content recommendations",
            "Create a personalization strategy for legal tech professionals",
            "Optimize user engagement based on behavioral patterns"
        ]
        
        for query in personalization_queries:
            print(f"\n🎯 Query: {query}")
            print("-" * 50)
            
            start_time = time.time()
            response = await self.plan_execute_agent.process_query(query)
            end_time = time.time()
            
            print(f"📊 Response:\n{response}")
            print(f"⏱️  Processing time: {end_time - start_time:.2f}s")
            
            await asyncio.sleep(0.5)  # Brief pause between queries
    
    async def demo_memory_persistence(self):
        """Demonstrate conversation memory and context"""
        print("\n" + "="*60)
        print("Memory Persistence Demo - Context Awareness")
        print("="*60)
        
        # Multi-turn conversation
        conversation = [
            "I'm working on a legal compliance project",
            "What GDPR regulations should I consider?",
            "How does this apply to user personalization?",
            "Can you summarize our discussion so far?"
        ]
        
        for i, message in enumerate(conversation):
            print(f"\n💬 Turn {i+1}: {message}")
            print("-" * 40)
            
            if i < 2:
                response = await self.react_agent.process_query(message)
            else:
                response = await self.plan_execute_agent.process_query(message)
            
            print(f"🤖 Agent: {response}")
            
            # Show memory context
            if i == len(conversation) - 1:
                print(f"\n📚 Conversation Context:")
                print(self.memory.get_context())

async def demonstrate_langchain_agents():
    """
    Comprehensive demonstration of LangChain agent patterns
    for enterprise conversational AI systems.
    """
    
    print("🚀 LangChain Agent Architecture Demo")
    print("Building Conversational AI for Enterprise Systems")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    demo = ConversationalAIDemo()
    
    # Demonstrate different agent patterns
    await demo.demo_react_agent()
    await demo.demo_plan_execute_agent()
    await demo.demo_memory_persistence()
    
    print("\n" + "="*60)
    print("✅ Demo Complete - All LangChain Agent Patterns Demonstrated")
    print("="*60)
    
    # Performance summary
    total_tools = len(demo.tools)
    memory_size = len(demo.memory.messages)
    
    print(f"\n📈 Performance Summary:")
    print(f"   • Tools integrated: {total_tools}")
    print(f"   • Conversation turns: {memory_size}")
    print(f"   • Agent patterns: ReAct + Plan-and-Execute")
    print(f"   • Memory persistence: ✓ Active")
    print(f"   • Enterprise scenarios: ✓ Legal + Personalization")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run demonstration
    asyncio.run(demonstrate_langchain_agents())
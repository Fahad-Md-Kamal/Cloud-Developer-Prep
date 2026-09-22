"""
Factory and Strategy Design Patterns for Enterprise Systems

This module demonstrates Factory and Strategy patterns applied to:
1. AI model selection and management (Optimizely scenario)
2. Document processing strategies (Lawstronaut scenario)

These patterns enable flexible, extensible systems that can adapt to
different requirements without modifying existing code.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import logging
import time


# =============================================================================
# FACTORY PATTERN IMPLEMENTATION
# =============================================================================

class ModelProvider(Enum):
    """Supported AI model providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"
    AZURE = "azure"


@dataclass
class ConversationRequest:
    """Request for AI conversation"""
    prompt: str
    context: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    user_id: Optional[str] = None


@dataclass
class ConversationResponse:
    """Response from AI conversation"""
    content: str
    model_used: str
    tokens_used: int
    response_time: float
    confidence: float


class ConversationModel(Protocol):
    """Protocol defining interface for conversation models"""
    
    async def generate_response(self, request: ConversationRequest) -> ConversationResponse:
        """Generate response to conversation request"""
        ...
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        ...
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for given number of tokens"""
        ...


class OpenAIModel:
    """OpenAI GPT model implementation"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        self.cost_per_token = 0.00003  # Example cost
    
    async def generate_response(self, request: ConversationRequest) -> ConversationResponse:
        """Generate response using OpenAI API"""
        start_time = time.time()
        
        # Simulate API call
        await asyncio.sleep(0.5)  # Simulate network latency
        
        # Simulate response generation
        response_content = f"OpenAI {self.model_name} response to: {request.prompt[:50]}..."
        tokens_used = len(request.prompt.split()) + len(response_content.split())
        
        return ConversationResponse(
            content=response_content,
            model_used=f"openai/{self.model_name}",
            tokens_used=tokens_used,
            response_time=time.time() - start_time,
            confidence=0.95
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "OpenAI",
            "model": self.model_name,
            "max_tokens": 4096,
            "supports_streaming": True,
            "cost_per_token": self.cost_per_token
        }
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for OpenAI model"""
        return tokens * self.cost_per_token


class ClaudeModel:
    """Anthropic Claude model implementation"""
    
    def __init__(self, api_key: str, model_version: str = "claude-3"):
        self.api_key = api_key
        self.model_version = model_version
        self.cost_per_token = 0.000015  # Generally cheaper than GPT-4
    
    async def generate_response(self, request: ConversationRequest) -> ConversationResponse:
        """Generate response using Claude API"""
        start_time = time.time()
        
        # Simulate API call
        await asyncio.sleep(0.4)  # Slightly faster than OpenAI
        
        response_content = f"Claude {self.model_version} thoughtful response to: {request.prompt[:50]}..."
        tokens_used = len(request.prompt.split()) + len(response_content.split())
        
        return ConversationResponse(
            content=response_content,
            model_used=f"claude/{self.model_version}",
            tokens_used=tokens_used,
            response_time=time.time() - start_time,
            confidence=0.92
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Claude model information"""
        return {
            "provider": "Anthropic",
            "model": self.model_version,
            "max_tokens": 8192,
            "supports_streaming": True,
            "cost_per_token": self.cost_per_token
        }
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for Claude model"""
        return tokens * self.cost_per_token


class LocalModel:
    """Local model implementation (e.g., Ollama, local LLaMA)"""
    
    def __init__(self, model_path: str, model_name: str = "llama2"):
        self.model_path = model_path
        self.model_name = model_name
        self.cost_per_token = 0.0  # No API costs for local models
    
    async def generate_response(self, request: ConversationRequest) -> ConversationResponse:
        """Generate response using local model"""
        start_time = time.time()
        
        # Simulate local model inference (slower but free)
        await asyncio.sleep(2.0)  # Local models are typically slower
        
        response_content = f"Local {self.model_name} response to: {request.prompt[:50]}..."
        tokens_used = len(request.prompt.split()) + len(response_content.split())
        
        return ConversationResponse(
            content=response_content,
            model_used=f"local/{self.model_name}",
            tokens_used=tokens_used,
            response_time=time.time() - start_time,
            confidence=0.85  # Local models might be less confident
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get local model information"""
        return {
            "provider": "Local",
            "model": self.model_name,
            "max_tokens": 2048,
            "supports_streaming": False,
            "cost_per_token": 0.0
        }
    
    def estimate_cost(self, tokens: int) -> float:
        """Local models have no per-token cost"""
        return 0.0


class AzureOpenAIModel:
    """Azure OpenAI model implementation"""
    
    def __init__(self, endpoint: str, api_key: str, deployment_name: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.cost_per_token = 0.000025  # Azure pricing
    
    async def generate_response(self, request: ConversationRequest) -> ConversationResponse:
        """Generate response using Azure OpenAI"""
        start_time = time.time()
        
        # Simulate Azure API call
        await asyncio.sleep(0.3)  # Azure might be faster due to regional deployment
        
        response_content = f"Azure OpenAI ({self.deployment_name}) response to: {request.prompt[:50]}..."
        tokens_used = len(request.prompt.split()) + len(response_content.split())
        
        return ConversationResponse(
            content=response_content,
            model_used=f"azure/{self.deployment_name}",
            tokens_used=tokens_used,
            response_time=time.time() - start_time,
            confidence=0.94
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Azure OpenAI model information"""
        return {
            "provider": "Azure OpenAI",
            "model": self.deployment_name,
            "max_tokens": 4096,
            "supports_streaming": True,
            "cost_per_token": self.cost_per_token
        }
    
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for Azure OpenAI"""
        return tokens * self.cost_per_token


# FACTORY IMPLEMENTATION
class ModelFactory:
    """Factory for creating AI conversation models"""
    
    @staticmethod
    def create_model(provider: ModelProvider, **config) -> ConversationModel:
        """
        Create model instance based on provider and configuration.
        
        This is the core Factory pattern - centralized object creation
        that can be extended without modifying existing code.
        """
        
        if provider == ModelProvider.OPENAI:
            return OpenAIModel(
                api_key=config["api_key"],
                model_name=config.get("model_name", "gpt-4")
            )
        
        elif provider == ModelProvider.CLAUDE:
            return ClaudeModel(
                api_key=config["api_key"],
                model_version=config.get("model_version", "claude-3")
            )
        
        elif provider == ModelProvider.LOCAL:
            return LocalModel(
                model_path=config["model_path"],
                model_name=config.get("model_name", "llama2")
            )
        
        elif provider == ModelProvider.AZURE:
            return AzureOpenAIModel(
                endpoint=config["endpoint"],
                api_key=config["api_key"],
                deployment_name=config["deployment_name"]
            )
        
        else:
            raise ValueError(f"Unknown model provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> List[ModelProvider]:
        """Get list of available providers"""
        return list(ModelProvider)
    
    @staticmethod
    def create_best_model_for_use_case(use_case: str, budget: float) -> ConversationModel:
        """
        Factory method that selects best model based on use case and budget.
        This demonstrates intelligent factory logic.
        """
        
        if use_case == "customer_support" and budget > 0.01:
            # Customer support needs fast, reliable responses
            return ModelFactory.create_model(
                ModelProvider.OPENAI,
                api_key="demo-key",
                model_name="gpt-4"
            )
        
        elif use_case == "creative_writing" and budget > 0.005:
            # Creative tasks benefit from Claude's thoughtful responses
            return ModelFactory.create_model(
                ModelProvider.CLAUDE,
                api_key="demo-key",
                model_version="claude-3"
            )
        
        elif use_case == "internal_tools" or budget <= 0.001:
            # Internal tools can use local models to save costs
            return ModelFactory.create_model(
                ModelProvider.LOCAL,
                model_path="/models/llama2",
                model_name="llama2"
            )
        
        else:
            # Default to Azure for enterprise scenarios
            return ModelFactory.create_model(
                ModelProvider.AZURE,
                endpoint="https://demo.openai.azure.com/",
                api_key="demo-key",
                deployment_name="gpt-4"
            )


# =============================================================================
# STRATEGY PATTERN IMPLEMENTATION
# =============================================================================

@dataclass
class DocumentContent:
    """Document content with metadata"""
    raw_content: str
    content_type: str
    source_url: str
    jurisdiction: Optional[str] = None


@dataclass
class ProcessedDocument:
    """Result of document processing"""
    title: str
    structured_content: Dict[str, Any]
    extracted_entities: List[str]
    confidence_score: float
    processing_method: str
    processing_time: float


class DocumentProcessingStrategy(ABC):
    """Abstract strategy for document processing"""
    
    @abstractmethod
    async def process(self, content: DocumentContent) -> ProcessedDocument:
        """Process document content"""
        pass
    
    @abstractmethod
    def can_handle(self, content: DocumentContent) -> bool:
        """Check if this strategy can handle the content"""
        pass
    
    @abstractmethod
    def get_processing_info(self) -> Dict[str, Any]:
        """Get information about this processing strategy"""
        pass


class PDFProcessingStrategy(DocumentProcessingStrategy):
    """Strategy for processing PDF documents"""
    
    async def process(self, content: DocumentContent) -> ProcessedDocument:
        """Process PDF document"""
        start_time = time.time()
        
        # Simulate PDF processing
        await asyncio.sleep(0.8)  # PDF processing is typically slower
        
        # Extract text and structure from PDF
        text_content = f"Extracted PDF text from {content.source_url}"
        
        # Simulate PDF-specific processing
        entities = ["Section 1", "Article 2", "Paragraph 3.1"]
        structured_content = {
            "pages": 10,
            "sections": entities,
            "text": text_content,
            "metadata": {
                "pdf_version": "1.4",
                "creation_date": "2024-01-01"
            }
        }
        
        return ProcessedDocument(
            title="PDF Legal Document",
            structured_content=structured_content,
            extracted_entities=entities,
            confidence_score=0.88,
            processing_method="PDF extraction",
            processing_time=time.time() - start_time
        )
    
    def can_handle(self, content: DocumentContent) -> bool:
        """Check if content is PDF"""
        return (content.content_type == "application/pdf" or 
                content.source_url.endswith(".pdf"))
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get PDF processing strategy info"""
        return {
            "strategy": "PDF Processing",
            "supported_formats": ["application/pdf"],
            "features": ["text_extraction", "structure_analysis", "metadata_extraction"],
            "typical_processing_time": "0.5-2.0 seconds"
        }


class HTMLProcessingStrategy(DocumentProcessingStrategy):
    """Strategy for processing HTML documents"""
    
    async def process(self, content: DocumentContent) -> ProcessedDocument:
        """Process HTML document"""
        start_time = time.time()
        
        # Simulate HTML processing
        await asyncio.sleep(0.3)  # HTML processing is faster
        
        # Parse HTML structure
        text_content = content.raw_content.replace("<", "").replace(">", "")
        
        # Extract HTML-specific elements
        entities = ["Title", "Header 1", "Header 2", "Navigation"]
        structured_content = {
            "html_structure": {
                "title": "HTML Legal Document",
                "headers": ["Introduction", "Legal Framework", "Conclusion"],
                "links": ["https://example.com/ref1", "https://example.com/ref2"]
            },
            "clean_text": text_content,
            "word_count": len(text_content.split())
        }
        
        return ProcessedDocument(
            title="HTML Legal Document",
            structured_content=structured_content,
            extracted_entities=entities,
            confidence_score=0.92,
            processing_method="HTML parsing",
            processing_time=time.time() - start_time
        )
    
    def can_handle(self, content: DocumentContent) -> bool:
        """Check if content is HTML"""
        return (content.content_type == "text/html" or 
                "<html>" in content.raw_content.lower())
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get HTML processing strategy info"""
        return {
            "strategy": "HTML Processing",
            "supported_formats": ["text/html"],
            "features": ["dom_parsing", "link_extraction", "clean_text"],
            "typical_processing_time": "0.1-0.5 seconds"
        }


class XMLProcessingStrategy(DocumentProcessingStrategy):
    """Strategy for processing XML documents"""
    
    async def process(self, content: DocumentContent) -> ProcessedDocument:
        """Process XML document"""
        start_time = time.time()
        
        # Simulate XML processing
        await asyncio.sleep(0.4)
        
        # Parse XML structure
        text_content = content.raw_content.replace("<", "").replace(">", "")
        
        # Extract XML-specific elements
        entities = ["Root Element", "Child Node 1", "Child Node 2"]
        structured_content = {
            "xml_structure": {
                "root": "legal_document",
                "namespaces": ["http://legal.gov/schema"],
                "elements": entities
            },
            "text_content": text_content,
            "schema_version": "1.0"
        }
        
        return ProcessedDocument(
            title="XML Legal Document",
            structured_content=structured_content,
            extracted_entities=entities,
            confidence_score=0.90,
            processing_method="XML parsing",
            processing_time=time.time() - start_time
        )
    
    def can_handle(self, content: DocumentContent) -> bool:
        """Check if content is XML"""
        return (content.content_type == "application/xml" or 
                content.content_type == "text/xml" or
                "<?xml" in content.raw_content)
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get XML processing strategy info"""
        return {
            "strategy": "XML Processing",
            "supported_formats": ["application/xml", "text/xml"],
            "features": ["schema_validation", "xpath_queries", "namespace_handling"],
            "typical_processing_time": "0.2-0.6 seconds"
        }


class JSONProcessingStrategy(DocumentProcessingStrategy):
    """Strategy for processing JSON API responses"""
    
    async def process(self, content: DocumentContent) -> ProcessedDocument:
        """Process JSON document"""
        start_time = time.time()
        
        # Simulate JSON processing
        await asyncio.sleep(0.1)  # JSON is fastest to process
        
        try:
            # Parse JSON content
            json_data = json.loads(content.raw_content)
            
            # Extract JSON-specific information
            entities = list(json_data.keys())[:5] if isinstance(json_data, dict) else []
            structured_content = {
                "json_data": json_data,
                "data_type": type(json_data).__name__,
                "key_count": len(json_data) if isinstance(json_data, dict) else 0
            }
            
            return ProcessedDocument(
                title="JSON API Response",
                structured_content=structured_content,
                extracted_entities=entities,
                confidence_score=0.95,
                processing_method="JSON parsing",
                processing_time=time.time() - start_time
            )
        
        except json.JSONDecodeError:
            # Handle invalid JSON
            return ProcessedDocument(
                title="Invalid JSON Document",
                structured_content={"error": "Invalid JSON format"},
                extracted_entities=[],
                confidence_score=0.0,
                processing_method="JSON parsing (failed)",
                processing_time=time.time() - start_time
            )
    
    def can_handle(self, content: DocumentContent) -> bool:
        """Check if content is JSON"""
        return (content.content_type == "application/json" or
                content.raw_content.strip().startswith(("{", "[")))
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get JSON processing strategy info"""
        return {
            "strategy": "JSON Processing",
            "supported_formats": ["application/json"],
            "features": ["fast_parsing", "schema_validation", "nested_object_handling"],
            "typical_processing_time": "0.05-0.2 seconds"
        }


# STRATEGY CONTEXT
class DocumentProcessor:
    """Context class that uses document processing strategies"""
    
    def __init__(self):
        self.strategies: List[DocumentProcessingStrategy] = [
            PDFProcessingStrategy(),
            HTMLProcessingStrategy(),
            XMLProcessingStrategy(),
            JSONProcessingStrategy()
        ]
        self.default_strategy = HTMLProcessingStrategy()
    
    async def process_document(self, content: DocumentContent) -> ProcessedDocument:
        """
        Process document using appropriate strategy.
        This demonstrates the Strategy pattern in action.
        """
        
        # Find appropriate strategy
        for strategy in self.strategies:
            if strategy.can_handle(content):
                logging.info(f"Using {strategy.__class__.__name__} for processing")
                return await strategy.process(content)
        
        # Fall back to default strategy
        logging.warning(f"No specific strategy found, using default: {self.default_strategy.__class__.__name__}")
        return await self.default_strategy.process(content)
    
    def add_strategy(self, strategy: DocumentProcessingStrategy):
        """Add new processing strategy"""
        self.strategies.append(strategy)
    
    def get_supported_formats(self) -> List[str]:
        """Get all supported formats"""
        formats = []
        for strategy in self.strategies:
            info = strategy.get_processing_info()
            formats.extend(info.get("supported_formats", []))
        return list(set(formats))


# =============================================================================
# ADVANCED PATTERN USAGE: COMBINING FACTORY AND STRATEGY
# =============================================================================

class DocumentProcessingService:
    """
    Service that combines Factory and Strategy patterns for
    intelligent document processing with AI enhancement.
    """
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.model_factory = ModelFactory()
    
    async def intelligent_document_processing(
        self, 
        content: DocumentContent,
        ai_enhancement: bool = True,
        budget_limit: float = 0.01
    ) -> Dict[str, Any]:
        """
        Process document and optionally enhance with AI analysis.
        Demonstrates combining Factory and Strategy patterns.
        """
        
        # Step 1: Use Strategy pattern for document processing
        processed_doc = await self.document_processor.process_document(content)
        
        result = {
            "processed_document": processed_doc,
            "ai_analysis": None,
            "total_cost": 0.0
        }
        
        if ai_enhancement:
            # Step 2: Use Factory pattern to create appropriate AI model
            ai_model = self.model_factory.create_best_model_for_use_case(
                use_case="document_analysis",
                budget=budget_limit
            )
            
            # Step 3: Enhance processing with AI analysis
            ai_request = ConversationRequest(
                prompt=f"Analyze this legal document: {processed_doc.title}. "
                      f"Content summary: {str(processed_doc.structured_content)[:200]}...",
                max_tokens=500
            )
            
            ai_response = await ai_model.generate_response(ai_request)
            
            result["ai_analysis"] = {
                "summary": ai_response.content,
                "model_used": ai_response.model_used,
                "confidence": ai_response.confidence
            }
            
            result["total_cost"] = ai_model.estimate_cost(ai_response.tokens_used)
        
        return result


# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

async def demonstrate_factory_pattern():
    """Demonstrate Factory pattern with AI models"""
    
    print("=== Factory Pattern Demonstration ===\n")
    
    # Configuration for different environments
    configurations = [
        {
            "name": "Production OpenAI",
            "provider": ModelProvider.OPENAI,
            "config": {"api_key": "sk-prod-key", "model_name": "gpt-4"}
        },
        {
            "name": "Development Claude",
            "provider": ModelProvider.CLAUDE,
            "config": {"api_key": "claude-dev-key", "model_version": "claude-3"}
        },
        {
            "name": "Local Testing",
            "provider": ModelProvider.LOCAL,
            "config": {"model_path": "/models/llama2", "model_name": "llama2-7b"}
        },
        {
            "name": "Enterprise Azure",
            "provider": ModelProvider.AZURE,
            "config": {
                "endpoint": "https://enterprise.openai.azure.com/",
                "api_key": "azure-key",
                "deployment_name": "gpt-4-enterprise"
            }
        }
    ]
    
    test_request = ConversationRequest(
        prompt="Explain the key principles of contract law in simple terms.",
        max_tokens=150
    )
    
    for config in configurations:
        print(f"Testing {config['name']}:")
        
        # Factory creates appropriate model
        model = ModelFactory.create_model(config["provider"], **config["config"])
        
        # Get model info
        info = model.get_model_info()
        print(f"  Provider: {info['provider']}")
        print(f"  Model: {info['model']}")
        print(f"  Cost per token: ${info['cost_per_token']:.6f}")
        
        # Generate response
        response = await model.generate_response(test_request)
        print(f"  Response: {response.content[:80]}...")
        print(f"  Response time: {response.response_time:.2f}s")
        print(f"  Estimated cost: ${model.estimate_cost(response.tokens_used):.4f}")
        print()


async def demonstrate_strategy_pattern():
    """Demonstrate Strategy pattern with document processing"""
    
    print("=== Strategy Pattern Demonstration ===\n")
    
    # Different document types
    test_documents = [
        DocumentContent(
            raw_content="<html><head><title>Legal Document</title></head><body><h1>Contract Law</h1><p>This document explains...</p></body></html>",
            content_type="text/html",
            source_url="https://legal.gov/contract-law.html"
        ),
        DocumentContent(
            raw_content='{"title": "API Response", "legal_code": "USC-123", "sections": ["1.1", "1.2"]}',
            content_type="application/json",
            source_url="https://api.legal.gov/statutes/123"
        ),
        DocumentContent(
            raw_content="<?xml version='1.0'?><legal_doc><title>Regulation</title><section>1</section></legal_doc>",
            content_type="application/xml",
            source_url="https://regulations.gov/doc.xml"
        ),
        DocumentContent(
            raw_content="Binary PDF content would be here...",
            content_type="application/pdf",
            source_url="https://court.gov/ruling.pdf"
        )
    ]
    
    processor = DocumentProcessor()
    
    print(f"Supported formats: {processor.get_supported_formats()}")
    print()
    
    for i, doc in enumerate(test_documents, 1):
        print(f"Processing Document {i} ({doc.content_type}):")
        
        # Strategy pattern automatically selects appropriate processor
        result = await processor.process_document(doc)
        
        print(f"  Title: {result.title}")
        print(f"  Method: {result.processing_method}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Processing time: {result.processing_time:.3f}s")
        print(f"  Entities found: {len(result.extracted_entities)}")
        print()


async def demonstrate_combined_patterns():
    """Demonstrate Factory and Strategy patterns working together"""
    
    print("=== Combined Factory + Strategy Patterns ===\n")
    
    service = DocumentProcessingService()
    
    # Test document
    test_doc = DocumentContent(
        raw_content="<html><head><title>Employment Contract</title></head><body>"
                   "<h1>Employment Agreement</h1>"
                   "<p>This agreement is between Employer and Employee...</p>"
                   "<h2>Terms and Conditions</h2>"
                   "<p>1. Duration of employment...</p>"
                   "</body></html>",
        content_type="text/html",
        source_url="https://legal.company.com/employment-contract.html",
        jurisdiction="US"
    )
    
    # Process with and without AI enhancement
    scenarios = [
        {"ai_enhancement": False, "budget_limit": 0.0},
        {"ai_enhancement": True, "budget_limit": 0.005},
        {"ai_enhancement": True, "budget_limit": 0.02}
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: AI Enhancement = {scenario['ai_enhancement']}, "
              f"Budget = ${scenario['budget_limit']}")
        
        result = await service.intelligent_document_processing(
            test_doc, **scenario
        )
        
        doc_result = result["processed_document"]
        print(f"  Document processed: {doc_result.title}")
        print(f"  Processing method: {doc_result.processing_method}")
        print(f"  Confidence: {doc_result.confidence_score:.2f}")
        
        if result["ai_analysis"]:
            ai_analysis = result["ai_analysis"]
            print(f"  AI Model used: {ai_analysis['model_used']}")
            print(f"  AI Summary: {ai_analysis['summary'][:80]}...")
            print(f"  Total cost: ${result['total_cost']:.4f}")
        else:
            print("  No AI enhancement requested")
        
        print()


async def main():
    """Run all demonstrations"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Factory and Strategy Patterns Demonstration")
    print("=" * 50)
    print()
    
    # Run demonstrations
    await demonstrate_factory_pattern()
    await demonstrate_strategy_pattern()
    await demonstrate_combined_patterns()
    
    print("All pattern demonstrations completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

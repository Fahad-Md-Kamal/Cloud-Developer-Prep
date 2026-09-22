"""
Complete RAG Pipeline Implementation for Enterprise Systems

This module demonstrates a comprehensive RAG (Retrieval-Augmented Generation) pipeline
applied to realistic scenarios like those used at Lawstronaut and Optimizely.

Key concepts covered:
- Query processing and embedding generation
- Vector similarity search and retrieval
- Context assembly and response generation
- Pipeline optimization and caching
- Multi-provider vector database support

Real-world applications:
- Legal research assistant for Lawstronaut
- Content personalization engine for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Union, Tuple, AsyncGenerator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import json
import logging
import time
import numpy as np
from datetime import datetime, timedelta
import hashlib
import uuid
from enum import Enum

# Mock external dependencies (in real implementation, use actual libraries)
class SentenceTransformer:
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def encode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        # Mock embedding generation (384-dimensional vectors)
        return np.random.random((len(texts), 384)).astype(np.float32)

class OpenAI:
    class AsyncOpenAI:
        async def chat_completions_create(self, model: str, messages: List[Dict], **kwargs) -> Dict:
            # Mock OpenAI response
            return {
                "choices": [{
                    "message": {
                        "content": f"Based on the provided context, I can help answer your question about: {messages[-1]['content'][:100]}..."
                    }
                }]
            }

# =============================================================================
# CORE DATA MODELS
# =============================================================================

class DocumentType(Enum):
    LEGAL = "legal"
    TECHNICAL = "technical"
    MARKETING = "marketing"
    POLICY = "policy"

@dataclass
class Document:
    """Represents a document in the knowledge base"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    relevance_score: Optional[float] = None
    doc_type: DocumentType = DocumentType.TECHNICAL
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # Ensure metadata has required fields
        if "source" not in self.metadata:
            self.metadata["source"] = "unknown"
        if "created_at" not in self.metadata:
            self.metadata["created_at"] = datetime.now().isoformat()

@dataclass
class QueryContext:
    """Context information for queries"""
    user_id: Optional[str] = None
    domain: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10
    include_metadata: bool = True

@dataclass
class RetrievalResult:
    """Result of retrieval operation"""
    query: str
    documents: List[Document]
    retrieval_time_ms: int
    total_candidates: int
    reranked: bool = False
    context_metadata: Dict[str, Any] = field(default_factory=dict)

# =============================================================================
# EMBEDDING AND QUERY PROCESSING
# =============================================================================

class EmbeddingService:
    """Service for generating embeddings with multiple model support"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name)
        self.embedding_cache = {}
        self.logger = logging.getLogger(__name__)
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query"""
        cache_key = hashlib.md5(query.encode()).hexdigest()
        
        if cache_key in self.embedding_cache:
            self.logger.debug(f"Cache hit for query embedding: {query[:50]}...")
            return self.embedding_cache[cache_key]
        
        # Generate embedding
        embedding = self.model.encode([query])[0]
        
        # Cache the result
        self.embedding_cache[cache_key] = embedding
        
        return embedding
    
    async def embed_documents(self, documents: List[Document]) -> List[Document]:
        """Generate embeddings for multiple documents"""
        texts = [doc.content for doc in documents]
        
        # Process in batches
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(batch_texts, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
        
        # Assign embeddings to documents
        for doc, embedding in zip(documents, embeddings):
            doc.embedding = embedding
        
        self.logger.info(f"Generated embeddings for {len(documents)} documents")
        return documents
    
    def clear_cache(self):
        """Clear embedding cache"""
        self.embedding_cache.clear()
        self.logger.info("Embedding cache cleared")

class QueryProcessor:
    """Advanced query processing with expansion and optimization"""
    
    def __init__(self, domain_vocabulary: Dict[str, List[str]] = None):
        self.domain_vocabulary = domain_vocabulary or {}
        self.logger = logging.getLogger(__name__)
    
    async def process_query(self, query: str, context: QueryContext) -> Tuple[str, List[str]]:
        """Process query with expansion and optimization"""
        # Clean and normalize query
        processed_query = self._clean_query(query)
        
        # Generate query expansions
        expansions = await self._expand_query(processed_query, context.domain)
        
        self.logger.info(f"Processed query: '{query}' -> '{processed_query}' with {len(expansions)} expansions")
        
        return processed_query, expansions
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query text"""
        # Remove extra whitespace
        cleaned = " ".join(query.split())
        
        # Basic normalization
        cleaned = cleaned.strip()
        
        return cleaned
    
    async def _expand_query(self, query: str, domain: Optional[str] = None) -> List[str]:
        """Expand query with synonyms and related terms"""
        expansions = [query]  # Original query
        
        query_lower = query.lower()
        
        # Domain-specific expansion
        if domain == "legal":
            legal_expansions = {
                "gdpr": ["general data protection regulation", "data protection", "privacy regulation"],
                "contract": ["agreement", "legal document", "terms and conditions"],
                "liability": ["legal responsibility", "accountability", "legal obligation"],
                "compliance": ["regulatory compliance", "legal compliance", "adherence"]
            }
            
            for term, synonyms in legal_expansions.items():
                if term in query_lower:
                    expansions.extend(synonyms)
        
        elif domain == "personalization":
            personalization_expansions = {
                "engagement": ["user engagement", "interaction", "user activity"],
                "conversion": ["conversion rate", "conversion optimization", "funnel optimization"],
                "segmentation": ["user segmentation", "audience targeting", "user groups"],
                "ab test": ["a/b testing", "split testing", "multivariate testing"]
            }
            
            for term, synonyms in personalization_expansions.items():
                if term in query_lower:
                    expansions.extend(synonyms)
        
        # Generic vocabulary expansion
        if self.domain_vocabulary:
            for term, synonyms in self.domain_vocabulary.items():
                if term in query_lower:
                    expansions.extend(synonyms)
        
        return list(set(expansions))  # Remove duplicates

# =============================================================================
# VECTOR DATABASE ABSTRACTION
# =============================================================================

class VectorDatabase(ABC):
    """Abstract base class for vector database implementations"""
    
    @abstractmethod
    async def upsert_documents(self, documents: List[Document]) -> bool:
        """Insert or update documents in the vector database"""
        pass
    
    @abstractmethod
    async def similarity_search(self, query_embedding: np.ndarray, k: int = 10, filters: Dict = None) -> List[Document]:
        """Perform similarity search"""
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass

class InMemoryVectorDB(VectorDatabase):
    """In-memory vector database for development and testing"""
    
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata_index: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def upsert_documents(self, documents: List[Document]) -> bool:
        """Insert or update documents"""
        try:
            for doc in documents:
                self.documents[doc.id] = doc
                if doc.embedding is not None:
                    self.embeddings[doc.id] = doc.embedding
                
                # Update metadata index
                for key, value in doc.metadata.items():
                    if key not in self.metadata_index:
                        self.metadata_index[key] = []
                    if doc.id not in self.metadata_index[key]:
                        self.metadata_index[key].append(doc.id)
            
            self.logger.info(f"Upserted {len(documents)} documents")
            return True
        
        except Exception as e:
            self.logger.error(f"Error upserting documents: {e}")
            return False
    
    async def similarity_search(self, query_embedding: np.ndarray, k: int = 10, filters: Dict = None) -> List[Document]:
        """Perform cosine similarity search"""
        if not self.embeddings:
            return []
        
        # Apply metadata filters
        candidate_ids = set(self.documents.keys())
        if filters:
            candidate_ids = self._apply_filters(candidate_ids, filters)
        
        # Calculate similarities
        similarities = []
        for doc_id in candidate_ids:
            if doc_id in self.embeddings:
                embedding = self.embeddings[doc_id]
                similarity = self._cosine_similarity(query_embedding, embedding)
                similarities.append((doc_id, similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:k]
        
        # Create result documents with relevance scores
        results = []
        for doc_id, similarity in top_results:
            doc = self.documents[doc_id]
            doc.relevance_score = float(similarity)
            results.append(doc)
        
        self.logger.info(f"Found {len(results)} similar documents out of {len(candidate_ids)} candidates")
        return results
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        try:
            for doc_id in document_ids:
                if doc_id in self.documents:
                    del self.documents[doc_id]
                if doc_id in self.embeddings:
                    del self.embeddings[doc_id]
                
                # Clean metadata index
                for key, ids in self.metadata_index.items():
                    if doc_id in ids:
                        ids.remove(doc_id)
            
            self.logger.info(f"Deleted {len(document_ids)} documents")
            return True
        
        except Exception as e:
            self.logger.error(f"Error deleting documents: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            "total_documents": len(self.documents),
            "total_embeddings": len(self.embeddings),
            "metadata_keys": list(self.metadata_index.keys()),
            "avg_embedding_dimension": len(list(self.embeddings.values())[0]) if self.embeddings else 0
        }
    
    def _apply_filters(self, candidate_ids: set, filters: Dict) -> set:
        """Apply metadata filters to candidate document IDs"""
        filtered_ids = candidate_ids.copy()
        
        for key, value in filters.items():
            if key in self.metadata_index:
                # Find documents matching the filter
                matching_docs = []
                for doc_id in self.metadata_index[key]:
                    if doc_id in self.documents:
                        doc_value = self.documents[doc_id].metadata.get(key)
                        if doc_value == value:
                            matching_docs.append(doc_id)
                
                # Intersect with current candidates
                filtered_ids &= set(matching_docs)
        
        return filtered_ids
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)

# =============================================================================
# CONTEXT ASSEMBLY AND GENERATION
# =============================================================================

class ContextAssembler:
    """Assembles retrieved documents into coherent context for generation"""
    
    def __init__(self, max_context_tokens: int = 4000):
        self.max_context_tokens = max_context_tokens
        self.logger = logging.getLogger(__name__)
    
    async def assemble_context(self, query: str, documents: List[Document], strategy: str = "relevance") -> str:
        """Assemble context from retrieved documents"""
        if not documents:
            return ""
        
        if strategy == "relevance":
            return self._assemble_by_relevance(documents)
        elif strategy == "temporal":
            return self._assemble_by_time(documents)
        elif strategy == "hierarchical":
            return self._assemble_by_hierarchy(documents)
        else:
            return self._assemble_by_relevance(documents)
    
    def _assemble_by_relevance(self, documents: List[Document]) -> str:
        """Assemble context ordered by relevance score"""
        # Sort by relevance score (descending)
        sorted_docs = sorted(documents, key=lambda d: d.relevance_score or 0, reverse=True)
        
        context_parts = []
        current_tokens = 0
        
        for doc in sorted_docs:
            # Estimate tokens (rough approximation: 4 chars per token)
            doc_tokens = len(doc.content) // 4
            
            if current_tokens + doc_tokens <= self.max_context_tokens:
                # Add document with source attribution
                doc_part = f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                if doc.metadata.get('title'):
                    doc_part += f"Title: {doc.metadata['title']}\n"
                doc_part += f"Content: {doc.content}\n"
                
                context_parts.append(doc_part)
                current_tokens += doc_tokens + 50  # Add overhead for metadata
            else:
                # Truncate if needed
                remaining_tokens = self.max_context_tokens - current_tokens
                if remaining_tokens > 100:  # Only add if meaningful content can fit
                    truncated_content = doc.content[:remaining_tokens*4]
                    doc_part = f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                    doc_part += f"Content: {truncated_content}...\n"
                    context_parts.append(doc_part)
                break
        
        return "\n---\n".join(context_parts)
    
    def _assemble_by_time(self, documents: List[Document]) -> str:
        """Assemble context ordered by document timestamps"""
        # Sort by creation time (most recent first)
        sorted_docs = sorted(
            documents, 
            key=lambda d: d.metadata.get('created_at', ''), 
            reverse=True
        )
        return self._assemble_by_relevance(sorted_docs)
    
    def _assemble_by_hierarchy(self, documents: List[Document]) -> str:
        """Assemble context preserving document hierarchy"""
        # Group by parent document or section
        hierarchical_groups = {}
        
        for doc in documents:
            parent = doc.metadata.get('parent_section', 'root')
            if parent not in hierarchical_groups:
                hierarchical_groups[parent] = []
            hierarchical_groups[parent].append(doc)
        
        # Assemble hierarchically
        context_parts = []
        for parent, group_docs in hierarchical_groups.items():
            if parent != 'root':
                context_parts.append(f"Section: {parent}")
            
            # Sort group by relevance
            group_docs.sort(key=lambda d: d.relevance_score or 0, reverse=True)
            for doc in group_docs:
                context_parts.append(f"- {doc.content}")
        
        return "\n\n".join(context_parts)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return len(text) // 4  # Rough approximation

class ResponseGenerator:
    """Generates responses using language models"""
    
    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.7):
        self.model_name = model_name
        self.temperature = temperature
        self.client = OpenAI.AsyncOpenAI()  # Mock client
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(self, query: str, context: str, domain: str = None) -> str:
        """Generate response using retrieved context"""
        # Create domain-specific system prompt
        system_prompt = self._get_system_prompt(domain)
        
        # Create user prompt with context
        user_prompt = self._create_user_prompt(query, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.client.chat_completions_create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=1000
            )
            
            generated_text = response["choices"][0]["message"]["content"]
            self.logger.info(f"Generated response for query: {query[:50]}...")
            
            return generated_text
        
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return f"I apologize, but I encountered an error while generating a response to your query: {query}"
    
    def _get_system_prompt(self, domain: str) -> str:
        """Get domain-specific system prompt"""
        base_prompt = "You are a helpful AI assistant that provides accurate, well-sourced answers based on the provided context."
        
        if domain == "legal":
            return f"{base_prompt} You specialize in legal research and provide precise, citation-backed legal analysis. Always mention when information should be verified with current legal counsel."
        
        elif domain == "personalization":
            return f"{base_prompt} You specialize in digital marketing, user experience optimization, and personalization strategies. Focus on actionable insights and data-driven recommendations."
        
        else:
            return f"{base_prompt} Provide clear, factual responses and cite your sources when possible."
    
    def _create_user_prompt(self, query: str, context: str) -> str:
        """Create user prompt combining query and context"""
        if not context.strip():
            return f"Question: {query}\n\nI don't have specific context documents to reference for this question. Please provide a general response based on your knowledge."
        
        return f"""Based on the following context documents, please answer the question.

Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context provided. If the context doesn't fully address the question, mention what additional information might be needed."""

# =============================================================================
# COMPLETE RAG PIPELINE
# =============================================================================

class RAGPipeline:
    """Complete RAG pipeline implementation"""
    
    def __init__(self, 
                 vector_db: VectorDatabase,
                 embedding_service: EmbeddingService,
                 response_generator: ResponseGenerator):
        self.vector_db = vector_db
        self.embedding_service = embedding_service
        self.response_generator = response_generator
        self.query_processor = QueryProcessor()
        self.context_assembler = ContextAssembler()
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.performance_stats = {
            "queries_processed": 0,
            "total_retrieval_time": 0,
            "total_generation_time": 0,
            "cache_hits": 0
        }
        
        # Simple result cache
        self.result_cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    async def query(self, query: str, context: QueryContext) -> Dict[str, Any]:
        """Process complete RAG query"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(query, context)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.performance_stats["cache_hits"] += 1
            return cached_result
        
        try:
            # Step 1: Process query
            processed_query, expansions = await self.query_processor.process_query(query, context)
            
            # Step 2: Generate embeddings
            query_embedding = await self.embedding_service.embed_query(processed_query)
            
            # Step 3: Retrieve documents
            retrieval_start = time.time()
            documents = await self.vector_db.similarity_search(
                query_embedding, 
                k=context.max_results,
                filters=context.filters
            )
            retrieval_time = (time.time() - retrieval_start) * 1000
            
            # Step 4: Assemble context
            assembled_context = await self.context_assembler.assemble_context(
                processed_query, 
                documents, 
                strategy="relevance"
            )
            
            # Step 5: Generate response
            generation_start = time.time()
            response = await self.response_generator.generate_response(
                processed_query,
                assembled_context,
                context.domain
            )
            generation_time = (time.time() - generation_start) * 1000
            
            # Create result
            result = {
                "query": query,
                "processed_query": processed_query,
                "response": response,
                "sources": [
                    {
                        "id": doc.id,
                        "title": doc.metadata.get("title", ""),
                        "source": doc.metadata.get("source", ""),
                        "relevance_score": doc.relevance_score,
                        "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                    }
                    for doc in documents
                ],
                "metadata": {
                    "retrieval_time_ms": retrieval_time,
                    "generation_time_ms": generation_time,
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "documents_retrieved": len(documents),
                    "context_tokens": self.context_assembler.estimate_tokens(assembled_context),
                    "expansions_used": len(expansions)
                }
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            # Update performance stats
            self.performance_stats["queries_processed"] += 1
            self.performance_stats["total_retrieval_time"] += retrieval_time
            self.performance_stats["total_generation_time"] += generation_time
            
            self.logger.info(f"RAG query completed in {result['metadata']['total_time_ms']:.2f}ms")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error processing RAG query: {e}")
            return {
                "query": query,
                "error": str(e),
                "response": "I encountered an error while processing your query. Please try again.",
                "sources": [],
                "metadata": {
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "error": True
                }
            }
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the knowledge base"""
        # Generate embeddings for new documents
        documents_with_embeddings = await self.embedding_service.embed_documents(documents)
        
        # Store in vector database
        success = await self.vector_db.upsert_documents(documents_with_embeddings)
        
        if success:
            # Clear cache to ensure fresh results
            self._clear_cache()
            self.logger.info(f"Added {len(documents)} documents to knowledge base")
        
        return success
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get pipeline performance statistics"""
        stats = self.performance_stats.copy()
        
        if stats["queries_processed"] > 0:
            stats["avg_retrieval_time_ms"] = stats["total_retrieval_time"] / stats["queries_processed"]
            stats["avg_generation_time_ms"] = stats["total_generation_time"] / stats["queries_processed"]
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["queries_processed"]
        
        return stats
    
    def _get_cache_key(self, query: str, context: QueryContext) -> str:
        """Generate cache key for query"""
        context_str = f"{context.domain}_{context.max_results}_{json.dumps(context.filters, sort_keys=True)}"
        return hashlib.md5(f"{query}_{context_str}".encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Get cached result if still valid"""
        if cache_key in self.result_cache:
            cached_data = self.result_cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["result"]
            else:
                del self.result_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict):
        """Cache query result"""
        self.result_cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }
    
    def _clear_cache(self):
        """Clear result cache"""
        self.result_cache.clear()

# =============================================================================
# ENTERPRISE RAG SCENARIOS
# =============================================================================

class LegalRAGSystem:
    """RAG system specialized for legal research - Lawstronaut scenario"""
    
    def __init__(self):
        # Initialize components
        self.vector_db = InMemoryVectorDB()
        self.embedding_service = EmbeddingService("all-MiniLM-L6-v2")
        self.response_generator = ResponseGenerator("gpt-4", temperature=0.3)  # Lower temperature for legal accuracy
        self.rag_pipeline = RAGPipeline(self.vector_db, self.embedding_service, self.response_generator)
        
        # Legal-specific setup
        self.setup_legal_knowledge_base()
    
    def setup_legal_knowledge_base(self):
        """Initialize legal knowledge base with sample documents"""
        legal_documents = [
            Document(
                id="gdpr_art_6",
                content="Article 6 GDPR - Lawfulness of processing: Processing shall be lawful only if and to the extent that at least one of the following applies: (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes...",
                metadata={
                    "title": "GDPR Article 6 - Lawfulness of Processing",
                    "source": "EU General Data Protection Regulation",
                    "jurisdiction": "EU",
                    "document_type": "regulation",
                    "article_number": "6",
                    "created_at": "2018-05-25T00:00:00Z"
                },
                doc_type=DocumentType.LEGAL
            ),
            Document(
                id="contract_liability_example",
                content="Limitation of liability clauses in software licensing agreements must be reasonable and not exclude liability for fundamental breaches. Courts have consistently held that attempts to exclude all liability may be deemed unfair under consumer protection legislation...",
                metadata={
                    "title": "Software Contract Liability Principles",
                    "source": "Commercial Law Review",
                    "jurisdiction": "UK",
                    "document_type": "legal_commentary",
                    "practice_area": "contract_law",
                    "created_at": "2023-03-15T00:00:00Z"
                },
                doc_type=DocumentType.LEGAL
            ),
            Document(
                id="ai_ethics_guidelines",
                content="AI Ethics Guidelines for Legal Practice: AI systems used in legal research and document analysis must ensure transparency, accountability, and fairness. Legal professionals must maintain oversight and verification of AI-generated analysis...",
                metadata={
                    "title": "AI Ethics in Legal Practice",
                    "source": "Legal Ethics Committee",
                    "jurisdiction": "International",
                    "document_type": "guidelines",
                    "practice_area": "legal_technology",
                    "created_at": "2024-01-10T00:00:00Z"
                },
                doc_type=DocumentType.POLICY
            )
        ]
        
        # Add documents asynchronously
        asyncio.create_task(self.rag_pipeline.add_documents(legal_documents))
    
    async def legal_research_query(self, query: str, jurisdiction: str = None, practice_area: str = None) -> Dict[str, Any]:
        """Perform legal research query with specialized filters"""
        context = QueryContext(
            domain="legal",
            filters={
                **({"jurisdiction": jurisdiction} if jurisdiction else {}),
                **({"practice_area": practice_area} if practice_area else {})
            },
            max_results=15  # More results for comprehensive legal research
        )
        
        result = await self.rag_pipeline.query(query, context)
        
        # Add legal-specific metadata
        result["legal_metadata"] = {
            "jurisdictions_covered": list(set([
                source.get("jurisdiction", "Unknown") 
                for source in result["sources"]
            ])),
            "document_types": list(set([
                source.get("document_type", "Unknown")
                for source in result["sources"]
            ])),
            "legal_disclaimer": "This analysis is for informational purposes only and does not constitute legal advice. Consult qualified legal counsel for specific situations."
        }
        
        return result

class PersonalizationRAGSystem:
    """RAG system for content personalization - Optimizely scenario"""
    
    def __init__(self):
        # Initialize components
        self.vector_db = InMemoryVectorDB()
        self.embedding_service = EmbeddingService("all-MiniLM-L6-v2")
        self.response_generator = ResponseGenerator("gpt-4", temperature=0.8)  # Higher temperature for creative content
        self.rag_pipeline = RAGPipeline(self.vector_db, self.embedding_service, self.response_generator)
        
        # Personalization-specific setup
        self.setup_content_knowledge_base()
    
    def setup_content_knowledge_base(self):
        """Initialize content knowledge base with sample documents"""
        content_documents = [
            Document(
                id="ab_testing_guide",
                content="A/B Testing Best Practices: Effective A/B tests require sufficient sample sizes, proper randomization, and clear success metrics. Test duration should account for weekly patterns and seasonal variations. Statistical significance should reach 95% confidence before making decisions...",
                metadata={
                    "title": "A/B Testing Best Practices",
                    "source": "Digital Marketing Institute",
                    "content_type": "guide",
                    "audience": "marketers",
                    "topics": ["ab_testing", "conversion_optimization", "statistics"],
                    "created_at": "2024-02-01T00:00:00Z"
                },
                doc_type=DocumentType.MARKETING
            ),
            Document(
                id="personalization_strategies",
                content="Personalization Strategies for E-commerce: Behavioral targeting based on browsing history, purchase patterns, and demographic data can increase conversion rates by 15-25%. Dynamic content personalization should balance relevance with privacy considerations...",
                metadata={
                    "title": "E-commerce Personalization Strategies",
                    "source": "E-commerce Today",
                    "content_type": "case_study",
                    "audience": "product_managers",
                    "topics": ["personalization", "ecommerce", "behavioral_targeting"],
                    "created_at": "2024-01-20T00:00:00Z"
                },
                doc_type=DocumentType.TECHNICAL
            ),
            Document(
                id="user_segmentation_framework",
                content="Advanced User Segmentation Framework: Combine demographic, behavioral, and psychographic data for multi-dimensional user segments. RFM analysis (Recency, Frequency, Monetary) provides foundation for value-based segmentation...",
                metadata={
                    "title": "Advanced User Segmentation Framework",
                    "source": "Analytics Weekly",
                    "content_type": "framework",
                    "audience": "data_analysts",
                    "topics": ["segmentation", "user_analytics", "rfm_analysis"],
                    "created_at": "2023-12-15T00:00:00Z"
                },
                doc_type=DocumentType.TECHNICAL
            )
        ]
        
        # Add documents asynchronously
        asyncio.create_task(self.rag_pipeline.add_documents(content_documents))
    
    async def personalization_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform personalization-focused query"""
        filters = {}
        
        # Add user context filters
        if user_context:
            if user_context.get("role"):
                filters["audience"] = user_context["role"]
            if user_context.get("industry"):
                filters["industry"] = user_context["industry"]
        
        context = QueryContext(
            domain="personalization",
            filters=filters,
            max_results=10
        )
        
        result = await self.rag_pipeline.query(query, context)
        
        # Add personalization-specific metadata
        result["personalization_metadata"] = {
            "user_context": user_context or {},
            "content_types": list(set([
                source.get("content_type", "Unknown")
                for source in result["sources"]
            ])),
            "target_audiences": list(set([
                source.get("audience", "General")
                for source in result["sources"]
            ])),
            "personalization_score": self._calculate_personalization_score(result["sources"], user_context)
        }
        
        return result
    
    def _calculate_personalization_score(self, sources: List[Dict], user_context: Dict) -> float:
        """Calculate how well the results match user context"""
        if not user_context or not sources:
            return 0.5
        
        score = 0.0
        total_sources = len(sources)
        
        for source in sources:
            source_score = 0.0
            
            # Role matching
            if user_context.get("role") and source.get("audience"):
                if user_context["role"] in source.get("audience", ""):
                    source_score += 0.5
            
            # Topic relevance (simplified)
            if user_context.get("interests"):
                topics = source.get("topics", [])
                if any(interest in topics for interest in user_context["interests"]):
                    source_score += 0.3
            
            # Recency bonus for newer content
            created_at = source.get("created_at", "")
            if "2024" in created_at:
                source_score += 0.2
            
            score += min(source_score, 1.0)
        
        return min(score / total_sources, 1.0)

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

async def demonstrate_rag_pipeline():
    """
    Comprehensive demonstration of RAG pipeline implementation
    for enterprise knowledge systems.
    """
    
    print("🚀 RAG Pipeline Implementation Demo")
    print("Enterprise Knowledge Systems for Legal Research and Content Personalization")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    # Legal RAG System Demo
    print("\n" + "="*60)
    print("Legal Research System Demo - Lawstronaut Scenario")
    print("="*60)
    
    legal_system = LegalRAGSystem()
    
    # Wait for knowledge base setup
    await asyncio.sleep(0.1)
    
    legal_queries = [
        "What are the key requirements for GDPR compliance in data processing?",
        "How should liability be limited in software licensing agreements?",
        "What ethical considerations apply to AI use in legal practice?"
    ]
    
    for query in legal_queries:
        print(f"\n📚 Legal Query: {query}")
        print("-" * 50)
        
        result = await legal_system.legal_research_query(query, jurisdiction="EU")
        
        print(f"🔍 Response: {result['response'][:300]}...")
        print(f"📊 Sources found: {result['metadata']['documents_retrieved']}")
        print(f"⚖️  Jurisdictions: {', '.join(result['legal_metadata']['jurisdictions_covered'])}")
        print(f"📋 Document types: {', '.join(result['legal_metadata']['document_types'])}")
        print(f"⏱️  Query time: {result['metadata']['total_time_ms']:.1f}ms")
    
    # Personalization RAG System Demo
    print("\n" + "="*60)
    print("Content Personalization System Demo - Optimizely Scenario")
    print("="*60)
    
    personalization_system = PersonalizationRAGSystem()
    
    # Wait for knowledge base setup
    await asyncio.sleep(0.1)
    
    personalization_queries = [
        ("How can I improve conversion rates through A/B testing?", {"role": "product_manager", "interests": ["conversion_optimization"]}),
        ("What are effective user segmentation strategies?", {"role": "data_analyst", "interests": ["analytics", "segmentation"]}),
        ("How do I implement personalization for e-commerce?", {"role": "marketer", "interests": ["personalization", "ecommerce"]})
    ]
    
    for query, user_context in personalization_queries:
        print(f"\n🎯 Personalization Query: {query}")
        print(f"👤 User Context: {user_context}")
        print("-" * 50)
        
        result = await personalization_system.personalization_query(query, user_context)
        
        print(f"💡 Response: {result['response'][:300]}...")
        print(f"📊 Sources found: {result['metadata']['documents_retrieved']}")
        print(f"🎭 Target audiences: {', '.join(result['personalization_metadata']['target_audiences'])}")
        print(f"📈 Personalization score: {result['personalization_metadata']['personalization_score']:.2f}")
        print(f"⏱️  Query time: {result['metadata']['total_time_ms']:.1f}ms")
    
    # Performance Analysis
    print("\n" + "="*60)
    print("Performance Analysis")
    print("="*60)
    
    legal_stats = legal_system.rag_pipeline.get_performance_stats()
    personalization_stats = personalization_system.rag_pipeline.get_performance_stats()
    
    print(f"\n📈 Legal System Performance:")
    print(f"   • Queries processed: {legal_stats['queries_processed']}")
    print(f"   • Avg retrieval time: {legal_stats.get('avg_retrieval_time_ms', 0):.1f}ms")
    print(f"   • Avg generation time: {legal_stats.get('avg_generation_time_ms', 0):.1f}ms")
    print(f"   • Cache hit rate: {legal_stats.get('cache_hit_rate', 0):.1%}")
    
    print(f"\n🎯 Personalization System Performance:")
    print(f"   • Queries processed: {personalization_stats['queries_processed']}")
    print(f"   • Avg retrieval time: {personalization_stats.get('avg_retrieval_time_ms', 0):.1f}ms")
    print(f"   • Avg generation time: {personalization_stats.get('avg_generation_time_ms', 0):.1f}ms")
    print(f"   • Cache hit rate: {personalization_stats.get('cache_hit_rate', 0):.1%}")
    
    # Vector Database Statistics
    legal_db_stats = await legal_system.vector_db.get_stats()
    personalization_db_stats = await personalization_system.vector_db.get_stats()
    
    print(f"\n🗄️  Database Statistics:")
    print(f"   Legal Knowledge Base:")
    print(f"     • Total documents: {legal_db_stats['total_documents']}")
    print(f"     • Embedding dimension: {legal_db_stats['avg_embedding_dimension']}")
    print(f"   Personalization Knowledge Base:")
    print(f"     • Total documents: {personalization_db_stats['total_documents']}")
    print(f"     • Embedding dimension: {personalization_db_stats['avg_embedding_dimension']}")
    
    print("\n" + "="*60)
    print("✅ RAG Pipeline Demo Complete")
    print("="*60)
    
    print(f"\n🎯 Key Achievements:")
    print(f"   • Demonstrated complete RAG pipeline with retrieval and generation")
    print(f"   • Implemented domain-specific systems for legal and personalization use cases")
    print(f"   • Showcased vector similarity search with metadata filtering")
    print(f"   • Provided context assembly and response generation")
    print(f"   • Included performance monitoring and caching strategies")
    print(f"   • Delivered enterprise-grade error handling and logging")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run comprehensive RAG demonstration
    asyncio.run(demonstrate_rag_pipeline())
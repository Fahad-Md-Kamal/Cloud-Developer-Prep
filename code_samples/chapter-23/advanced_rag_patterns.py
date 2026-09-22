"""
Advanced RAG Patterns and Multi-Step Retrieval

This module demonstrates advanced RAG patterns including multi-step retrieval,
query expansion, document relationships, and hybrid search strategies.

Key concepts covered:
- Multi-step retrieval with query refinement
- Contextual query expansion and reranking
- Document relationship modeling
- Hybrid dense-sparse search
- Query routing and specialized retrievers
- Real-time knowledge base updates

Real-world applications:
- Complex legal research for Lawstronaut
- Advanced content recommendations for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Set
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
from collections import defaultdict, Counter
import math

# Mock external dependencies
class MockSentenceTransformer:
    def __init__(self, model_name: str):
        self.model_name = model_name
    
    def encode(self, texts: List[str]) -> np.ndarray:
        # Return mock embeddings
        return np.random.random((len(texts), 384)).astype(np.float32)

class MockBM25:
    def __init__(self, corpus: List[str]):
        self.corpus = corpus
        self.vocab = set()
        for doc in corpus:
            self.vocab.update(doc.split())
    
    def get_scores(self, query: str) -> List[float]:
        # Mock BM25 scores
        return [np.random.random() for _ in self.corpus]

# =============================================================================
# CORE DATA MODELS FOR ADVANCED RAG
# =============================================================================

class QueryType(Enum):
    FACTUAL = "factual"
    ANALYTICAL = "analytical" 
    COMPARATIVE = "comparative"
    PROCEDURAL = "procedural"
    EXPLORATORY = "exploratory"

class RetrievalStrategy(Enum):
    DENSE_ONLY = "dense_only"
    SPARSE_ONLY = "sparse_only"
    HYBRID = "hybrid"
    MULTI_STEP = "multi_step"
    CONTEXTUAL = "contextual"

@dataclass
class QueryIntent:
    """Analyzed query intent and requirements"""
    query_type: QueryType
    confidence: float
    entities: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    requires_multi_step: bool = False
    domain_specific: bool = False

@dataclass
class DocumentRelationship:
    """Relationship between documents"""
    source_id: str
    target_id: str
    relationship_type: str  # "references", "cites", "follows", "contradicts", etc.
    strength: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalStep:
    """Individual step in multi-step retrieval"""
    step_id: str
    query: str
    strategy: RetrievalStrategy
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0

@dataclass
class MultiStepRetrievalResult:
    """Result of multi-step retrieval process"""
    original_query: str
    final_query: str
    steps: List[RetrievalStep]
    combined_results: List[Dict[str, Any]]
    query_intent: QueryIntent
    total_time_ms: float
    confidence_score: float

# =============================================================================
# QUERY ANALYSIS AND INTENT DETECTION
# =============================================================================

class QueryAnalyzer:
    """Advanced query analysis for intent detection and expansion"""
    
    def __init__(self, domain_ontologies: Dict[str, Dict] = None):
        self.domain_ontologies = domain_ontologies or {}
        self.logger = logging.getLogger(__name__)
    
    async def analyze_query(self, query: str, domain: str = None) -> QueryIntent:
        """Analyze query to determine intent and requirements"""
        
        # Extract entities and topics
        entities = self._extract_entities(query)
        topics = self._extract_topics(query, domain)
        
        # Determine query type
        query_type = self._classify_query_type(query)
        
        # Calculate complexity
        complexity = self._calculate_complexity(query, entities, topics)
        
        # Determine if multi-step retrieval is needed
        requires_multi_step = self._requires_multi_step_retrieval(query, complexity)
        
        # Check domain specificity
        domain_specific = self._is_domain_specific(query, domain)
        
        intent = QueryIntent(
            query_type=query_type,
            confidence=0.85,  # Mock confidence
            entities=entities,
            topics=topics,
            complexity_score=complexity,
            requires_multi_step=requires_multi_step,
            domain_specific=domain_specific
        )
        
        self.logger.info(f"Query analysis complete: type={query_type.value}, complexity={complexity:.2f}")
        return intent
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query"""
        # Simplified entity extraction (in production, use spaCy or similar)
        entities = []
        
        # Look for capitalized words (potential proper nouns)
        import re
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        entities.extend(capitalized)
        
        # Look for dates
        dates = re.findall(r'\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b', query)
        entities.extend(dates)
        
        # Look for legal/technical terms
        legal_terms = ['GDPR', 'API', 'URL', 'HTTP', 'SQL', 'JSON']
        for term in legal_terms:
            if term in query:
                entities.append(term)
        
        return list(set(entities))
    
    def _extract_topics(self, query: str, domain: str = None) -> List[str]:
        """Extract topics from query"""
        topics = []
        
        # Domain-specific topic extraction
        if domain == "legal":
            legal_topics = {
                'data protection': ['gdpr', 'privacy', 'data protection', 'personal data'],
                'contracts': ['contract', 'agreement', 'terms', 'liability'],
                'compliance': ['compliance', 'regulation', 'audit', 'violation'],
                'intellectual property': ['patent', 'trademark', 'copyright', 'ip']
            }
            
            query_lower = query.lower()
            for topic, keywords in legal_topics.items():
                if any(keyword in query_lower for keyword in keywords):
                    topics.append(topic)
        
        elif domain == "personalization":
            personalization_topics = {
                'optimization': ['optimization', 'improve', 'increase', 'boost'],
                'testing': ['test', 'experiment', 'ab test', 'multivariate'],
                'analytics': ['analytics', 'metrics', 'measurement', 'tracking'],
                'segmentation': ['segment', 'audience', 'target', 'persona']
            }
            
            query_lower = query.lower()
            for topic, keywords in personalization_topics.items():
                if any(keyword in query_lower for keyword in keywords):
                    topics.append(topic)
        
        return topics
    
    def _classify_query_type(self, query: str) -> QueryType:
        """Classify query into different types"""
        query_lower = query.lower()
        
        # Comparative queries
        comparative_indicators = ['compare', 'difference', 'versus', 'vs', 'better', 'worse']
        if any(indicator in query_lower for indicator in comparative_indicators):
            return QueryType.COMPARATIVE
        
        # Procedural queries
        procedural_indicators = ['how to', 'steps to', 'process', 'procedure', 'implement']
        if any(indicator in query_lower for indicator in procedural_indicators):
            return QueryType.PROCEDURAL
        
        # Analytical queries
        analytical_indicators = ['why', 'analyze', 'impact', 'effect', 'consequence']
        if any(indicator in query_lower for indicator in analytical_indicators):
            return QueryType.ANALYTICAL
        
        # Exploratory queries
        exploratory_indicators = ['explore', 'overview', 'summary', 'introduction', 'what is']
        if any(indicator in query_lower for indicator in exploratory_indicators):
            return QueryType.EXPLORATORY
        
        # Default to factual
        return QueryType.FACTUAL
    
    def _calculate_complexity(self, query: str, entities: List[str], topics: List[str]) -> float:
        """Calculate query complexity score"""
        complexity = 0.0
        
        # Base complexity from query length
        word_count = len(query.split())
        complexity += min(word_count / 20.0, 1.0) * 0.3
        
        # Complexity from entities
        complexity += len(entities) / 10.0 * 0.3
        
        # Complexity from topics
        complexity += len(topics) / 5.0 * 0.2
        
        # Complexity from question words
        question_words = ['what', 'how', 'why', 'when', 'where', 'which']
        question_count = sum(1 for word in question_words if word in query.lower())
        complexity += question_count / 3.0 * 0.2
        
        return min(complexity, 1.0)
    
    def _requires_multi_step_retrieval(self, query: str, complexity: float) -> bool:
        """Determine if query requires multi-step retrieval"""
        # High complexity queries likely need multi-step
        if complexity > 0.7:
            return True
        
        # Queries with multiple questions
        if query.count('?') > 1:
            return True
        
        # Queries with conjunctions suggesting multiple aspects
        multi_aspect_indicators = [' and ', ' or ', 'also', 'additionally', 'furthermore']
        if any(indicator in query.lower() for indicator in multi_aspect_indicators):
            return True
        
        return False
    
    def _is_domain_specific(self, query: str, domain: str = None) -> bool:
        """Check if query is domain-specific"""
        if not domain:
            return False
        
        domain_vocabularies = {
            "legal": ['law', 'legal', 'regulation', 'statute', 'court', 'judge', 'liability'],
            "personalization": ['conversion', 'engagement', 'funnel', 'segment', 'campaign']
        }
        
        vocabulary = domain_vocabularies.get(domain, [])
        query_lower = query.lower()
        
        domain_term_count = sum(1 for term in vocabulary if term in query_lower)
        
        # Consider domain-specific if 2+ domain terms present
        return domain_term_count >= 2

# =============================================================================
# QUERY EXPANSION AND REFINEMENT
# =============================================================================

class QueryExpander:
    """Advanced query expansion with contextual understanding"""
    
    def __init__(self, embedding_model: MockSentenceTransformer = None):
        self.embedding_model = embedding_model or MockSentenceTransformer("all-MiniLM-L6-v2")
        self.expansion_cache = {}
        self.logger = logging.getLogger(__name__)
    
    async def expand_query(self, query: str, intent: QueryIntent, 
                          context: List[str] = None) -> List[str]:
        """Expand query based on intent and context"""
        
        cache_key = hashlib.md5(f"{query}_{intent.query_type.value}".encode()).hexdigest()
        if cache_key in self.expansion_cache:
            return self.expansion_cache[cache_key]
        
        expansions = [query]  # Original query
        
        # Intent-based expansion
        if intent.query_type == QueryType.COMPARATIVE:
            expansions.extend(self._expand_comparative(query, intent))
        elif intent.query_type == QueryType.PROCEDURAL:
            expansions.extend(self._expand_procedural(query, intent))
        elif intent.query_type == QueryType.ANALYTICAL:
            expansions.extend(self._expand_analytical(query, intent))
        
        # Entity-based expansion
        expansions.extend(self._expand_with_entities(query, intent.entities))
        
        # Topic-based expansion
        expansions.extend(self._expand_with_topics(query, intent.topics))
        
        # Contextual expansion
        if context:
            expansions.extend(self._expand_with_context(query, context))
        
        # Remove duplicates and filter
        unique_expansions = list(set(expansions))
        
        # Rank expansions by relevance
        ranked_expansions = await self._rank_expansions(query, unique_expansions)
        
        # Cache and return top expansions
        top_expansions = ranked_expansions[:10]  # Limit to top 10
        self.expansion_cache[cache_key] = top_expansions
        
        self.logger.info(f"Query expanded from 1 to {len(top_expansions)} variants")
        return top_expansions
    
    def _expand_comparative(self, query: str, intent: QueryIntent) -> List[str]:
        """Expand comparative queries"""
        expansions = []
        
        base_query = query.replace('compare', '').replace('vs', '').strip()
        
        # Add alternative phrasings
        expansions.extend([
            f"difference between {base_query}",
            f"advantages and disadvantages of {base_query}",
            f"pros and cons of {base_query}",
            f"{base_query} comparison"
        ])
        
        return expansions
    
    def _expand_procedural(self, query: str, intent: QueryIntent) -> List[str]:
        """Expand procedural queries"""
        expansions = []
        
        # Extract the main action/process
        action_words = ['implement', 'setup', 'configure', 'create', 'build']
        
        for entity in intent.entities:
            expansions.extend([
                f"step by step guide for {entity}",
                f"best practices for {entity}",
                f"implementation guide {entity}",
                f"tutorial {entity}"
            ])
        
        return expansions
    
    def _expand_analytical(self, query: str, intent: QueryIntent) -> List[str]:
        """Expand analytical queries"""
        expansions = []
        
        for topic in intent.topics:
            expansions.extend([
                f"analysis of {topic}",
                f"impact of {topic}",
                f"effects of {topic}",
                f"consequences of {topic}",
                f"factors affecting {topic}"
            ])
        
        return expansions
    
    def _expand_with_entities(self, query: str, entities: List[str]) -> List[str]:
        """Expand query using extracted entities"""
        expansions = []
        
        for entity in entities:
            # Add entity-focused queries
            expansions.extend([
                f"{entity} overview",
                f"{entity} details",
                f"information about {entity}",
                f"{entity} explanation"
            ])
        
        return expansions
    
    def _expand_with_topics(self, query: str, topics: List[str]) -> List[str]:
        """Expand query using identified topics"""
        expansions = []
        
        for topic in topics:
            expansions.extend([
                f"{topic} fundamentals",
                f"{topic} principles",
                f"{topic} best practices",
                f"{topic} guidelines"
            ])
        
        return expansions
    
    def _expand_with_context(self, query: str, context: List[str]) -> List[str]:
        """Expand query using contextual information"""
        expansions = []
        
        # Extract key terms from context
        context_terms = set()
        for ctx in context[:3]:  # Use top 3 context pieces
            words = ctx.split()
            # Add significant terms (length > 3, not common words)
            significant_terms = [w for w in words if len(w) > 3 and w.lower() not in 
                               {'this', 'that', 'with', 'from', 'they', 'were', 'been'}]
            context_terms.update(significant_terms[:5])  # Top 5 terms per context
        
        # Create contextual expansions
        for term in list(context_terms)[:5]:  # Limit to 5 terms
            expansions.append(f"{query} {term}")
        
        return expansions
    
    async def _rank_expansions(self, original_query: str, expansions: List[str]) -> List[str]:
        """Rank query expansions by relevance to original query"""
        
        # Generate embeddings for original query and expansions
        all_queries = [original_query] + expansions
        embeddings = self.embedding_model.encode(all_queries)
        
        original_embedding = embeddings[0]
        expansion_embeddings = embeddings[1:]
        
        # Calculate similarities
        similarities = []
        for i, exp_embedding in enumerate(expansion_embeddings):
            # Cosine similarity
            similarity = np.dot(original_embedding, exp_embedding) / (
                np.linalg.norm(original_embedding) * np.linalg.norm(exp_embedding)
            )
            similarities.append((similarity, expansions[i]))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return [exp for _, exp in similarities]

# =============================================================================
# MULTI-STEP RETRIEVAL ENGINE
# =============================================================================

class MultiStepRetriever:
    """Advanced multi-step retrieval with query refinement"""
    
    def __init__(self, 
                 dense_retriever: Any = None,
                 sparse_retriever: Any = None,
                 query_analyzer: QueryAnalyzer = None,
                 query_expander: QueryExpander = None):
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.query_expander = query_expander or QueryExpander()
        self.logger = logging.getLogger(__name__)
    
    async def multi_step_retrieve(self, query: str, k: int = 10, 
                                 max_steps: int = 3,
                                 domain: str = None) -> MultiStepRetrievalResult:
        """Execute multi-step retrieval process"""
        
        start_time = time.time()
        steps = []
        
        # Step 1: Analyze query intent
        intent = await self.query_analyzer.analyze_query(query, domain)
        
        # Step 2: Initial retrieval
        initial_step = await self._execute_retrieval_step(
            step_id="initial",
            query=query,
            strategy=RetrievalStrategy.HYBRID,
            k=k * 2  # Get more results initially
        )
        steps.append(initial_step)
        
        current_results = initial_step.results
        refined_query = query
        
        # Additional steps if needed
        if intent.requires_multi_step and len(steps) < max_steps:
            
            # Step 3: Query refinement based on initial results
            context = [result.get('content', '') for result in current_results[:5]]
            expanded_queries = await self.query_expander.expand_query(query, intent, context)
            
            if expanded_queries and len(expanded_queries) > 1:
                refined_query = expanded_queries[1]  # Use best expansion
                
                refinement_step = await self._execute_retrieval_step(
                    step_id="refinement",
                    query=refined_query,
                    strategy=RetrievalStrategy.DENSE_ONLY,
                    k=k
                )
                steps.append(refinement_step)
                current_results.extend(refinement_step.results)
        
        # Step 4: Contextual expansion (if very complex)
        if intent.complexity_score > 0.8 and len(steps) < max_steps:
            
            # Extract key concepts from current results
            key_concepts = self._extract_key_concepts(current_results[:10])
            
            if key_concepts:
                concept_query = f"{query} {' '.join(key_concepts[:3])}"
                
                contextual_step = await self._execute_retrieval_step(
                    step_id="contextual",
                    query=concept_query,
                    strategy=RetrievalStrategy.SPARSE_ONLY,
                    k=k // 2
                )
                steps.append(contextual_step)
                current_results.extend(contextual_step.results)
        
        # Combine and rerank results
        combined_results = await self._combine_and_rerank_results(
            current_results, query, intent, k
        )
        
        # Calculate confidence score
        confidence = self._calculate_retrieval_confidence(steps, combined_results)
        
        total_time = (time.time() - start_time) * 1000
        
        result = MultiStepRetrievalResult(
            original_query=query,
            final_query=refined_query,
            steps=steps,
            combined_results=combined_results,
            query_intent=intent,
            total_time_ms=total_time,
            confidence_score=confidence
        )
        
        self.logger.info(f"Multi-step retrieval completed in {len(steps)} steps, {total_time:.1f}ms")
        return result
    
    async def _execute_retrieval_step(self, step_id: str, query: str, 
                                    strategy: RetrievalStrategy, k: int) -> RetrievalStep:
        """Execute a single retrieval step"""
        
        start_time = time.time()
        
        # Mock retrieval results (in real implementation, use actual retrievers)
        if strategy == RetrievalStrategy.DENSE_ONLY:
            results = self._mock_dense_retrieval(query, k)
        elif strategy == RetrievalStrategy.SPARSE_ONLY:
            results = self._mock_sparse_retrieval(query, k)
        else:  # HYBRID
            dense_results = self._mock_dense_retrieval(query, k // 2)
            sparse_results = self._mock_sparse_retrieval(query, k // 2)
            results = dense_results + sparse_results
        
        execution_time = (time.time() - start_time) * 1000
        
        step = RetrievalStep(
            step_id=step_id,
            query=query,
            strategy=strategy,
            results=results,
            execution_time_ms=execution_time,
            metadata={
                "results_count": len(results),
                "strategy": strategy.value,
                "avg_score": np.mean([r.get('score', 0) for r in results]) if results else 0
            }
        )
        
        return step
    
    def _mock_dense_retrieval(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Mock dense retrieval results"""
        results = []
        
        for i in range(k):
            result = {
                "id": f"dense_doc_{i}",
                "content": f"Dense retrieval result {i+1} for query: {query[:50]}...",
                "score": 0.9 - (i * 0.05),  # Decreasing scores
                "source": f"dense_source_{i}",
                "metadata": {
                    "retrieval_method": "dense",
                    "embedding_similarity": 0.9 - (i * 0.05)
                }
            }
            results.append(result)
        
        return results
    
    def _mock_sparse_retrieval(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Mock sparse retrieval results"""
        results = []
        
        for i in range(k):
            result = {
                "id": f"sparse_doc_{i}",
                "content": f"Sparse retrieval result {i+1} with keyword matches for: {query[:50]}...",
                "score": 0.8 - (i * 0.04),  # Decreasing scores
                "source": f"sparse_source_{i}",
                "metadata": {
                    "retrieval_method": "sparse",
                    "bm25_score": 0.8 - (i * 0.04),
                    "keyword_matches": max(1, 5 - i)
                }
            }
            results.append(result)
        
        return results
    
    def _extract_key_concepts(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract key concepts from retrieval results"""
        all_content = " ".join([result.get('content', '') for result in results])
        
        # Simple keyword extraction (in production, use TF-IDF or similar)
        words = all_content.lower().split()
        
        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        significant_words = [w for w in words if len(w) > 4 and w not in stop_words]
        
        # Count frequency and return top concepts
        word_counts = Counter(significant_words)
        top_concepts = [word for word, count in word_counts.most_common(10)]
        
        return top_concepts
    
    async def _combine_and_rerank_results(self, results: List[Dict[str, Any]], 
                                        query: str, intent: QueryIntent, k: int) -> List[Dict[str, Any]]:
        """Combine results from multiple steps and rerank"""
        
        # Remove duplicates based on content similarity
        unique_results = self._deduplicate_results(results)
        
        # Rerank based on multiple factors
        reranked_results = self._rerank_results(unique_results, query, intent)
        
        # Return top k results
        return reranked_results[:k]
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results based on content similarity"""
        unique_results = []
        seen_content = set()
        
        for result in results:
            content = result.get('content', '')
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _rerank_results(self, results: List[Dict[str, Any]], 
                       query: str, intent: QueryIntent) -> List[Dict[str, Any]]:
        """Rerank results based on multiple relevance factors"""
        
        for result in results:
            # Base score from retrieval
            base_score = result.get('score', 0.0)
            
            # Intent-based score adjustment
            intent_boost = self._calculate_intent_boost(result, intent)
            
            # Freshness boost (mock)
            freshness_boost = 0.1  # Mock freshness
            
            # Authority boost based on source
            authority_boost = self._calculate_authority_boost(result)
            
            # Calculate final score
            final_score = base_score + intent_boost + freshness_boost + authority_boost
            result['final_score'] = min(final_score, 1.0)
        
        # Sort by final score
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        return results
    
    def _calculate_intent_boost(self, result: Dict[str, Any], intent: QueryIntent) -> float:
        """Calculate score boost based on query intent"""
        content = result.get('content', '').lower()
        boost = 0.0
        
        # Boost for entity matches
        for entity in intent.entities:
            if entity.lower() in content:
                boost += 0.05
        
        # Boost for topic matches
        for topic in intent.topics:
            if topic.lower() in content:
                boost += 0.03
        
        # Intent-specific boosts
        if intent.query_type == QueryType.PROCEDURAL:
            if any(word in content for word in ['step', 'process', 'procedure', 'guide']):
                boost += 0.02
        
        return min(boost, 0.2)  # Cap boost at 0.2
    
    def _calculate_authority_boost(self, result: Dict[str, Any]) -> float:
        """Calculate authority-based score boost"""
        source = result.get('source', '').lower()
        
        # Mock authority scoring
        authority_sources = ['regulation', 'statute', 'official', 'documentation']
        
        for auth_source in authority_sources:
            if auth_source in source:
                return 0.05
        
        return 0.0
    
    def _calculate_retrieval_confidence(self, steps: List[RetrievalStep], 
                                      results: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in retrieval results"""
        
        if not results:
            return 0.0
        
        # Base confidence from top result scores
        top_scores = [r.get('final_score', r.get('score', 0)) for r in results[:5]]
        score_confidence = np.mean(top_scores) if top_scores else 0.0
        
        # Confidence from result diversity
        diversity_score = min(len(set(r.get('source', '') for r in results[:10])) / 10.0, 1.0)
        
        # Confidence from multi-step consistency
        step_confidence = 1.0 if len(steps) > 1 else 0.8
        
        # Combined confidence
        overall_confidence = (score_confidence * 0.5 + diversity_score * 0.3 + step_confidence * 0.2)
        
        return min(overall_confidence, 1.0)

# =============================================================================
# DOCUMENT RELATIONSHIP MODELING
# =============================================================================

class DocumentRelationshipManager:
    """Manages relationships between documents for enhanced retrieval"""
    
    def __init__(self):
        self.relationships: Dict[str, List[DocumentRelationship]] = defaultdict(list)
        self.relationship_cache = {}
        self.logger = logging.getLogger(__name__)
    
    async def add_relationship(self, relationship: DocumentRelationship):
        """Add a document relationship"""
        self.relationships[relationship.source_id].append(relationship)
        
        # Also add reverse relationship for bidirectional lookup
        reverse_rel = DocumentRelationship(
            source_id=relationship.target_id,
            target_id=relationship.source_id,
            relationship_type=f"reverse_{relationship.relationship_type}",
            strength=relationship.strength,
            metadata=relationship.metadata
        )
        self.relationships[relationship.target_id].append(reverse_rel)
        
        self.logger.debug(f"Added relationship: {relationship.source_id} -> {relationship.target_id}")
    
    async def find_related_documents(self, document_id: str, 
                                   relationship_types: List[str] = None,
                                   max_depth: int = 2,
                                   min_strength: float = 0.1) -> List[Tuple[str, float, str]]:
        """Find related documents using graph traversal"""
        
        cache_key = f"{document_id}_{relationship_types}_{max_depth}_{min_strength}"
        if cache_key in self.relationship_cache:
            return self.relationship_cache[cache_key]
        
        related = []
        visited = set()
        queue = [(document_id, 1.0, 0)]  # (doc_id, strength, depth)
        
        while queue:
            current_id, current_strength, depth = queue.pop(0)
            
            if current_id in visited or depth >= max_depth:
                continue
            
            visited.add(current_id)
            
            # Get relationships for current document
            for rel in self.relationships.get(current_id, []):
                if relationship_types and rel.relationship_type not in relationship_types:
                    continue
                
                combined_strength = current_strength * rel.strength
                
                if combined_strength >= min_strength:
                    related.append((rel.target_id, combined_strength, rel.relationship_type))
                    
                    # Add to queue for further exploration
                    if depth + 1 < max_depth:
                        queue.append((rel.target_id, combined_strength, depth + 1))
        
        # Sort by strength and remove duplicates
        unique_related = {}
        for doc_id, strength, rel_type in related:
            if doc_id != document_id:  # Exclude self
                if doc_id not in unique_related or unique_related[doc_id][0] < strength:
                    unique_related[doc_id] = (strength, rel_type)
        
        final_related = [(doc_id, strength, rel_type) for doc_id, (strength, rel_type) in unique_related.items()]
        final_related.sort(key=lambda x: x[1], reverse=True)
        
        self.relationship_cache[cache_key] = final_related
        return final_related
    
    def build_citation_relationships(self, documents: List[Dict[str, Any]]):
        """Build citation relationships between documents"""
        
        for doc in documents:
            doc_id = doc.get('id', '')
            content = doc.get('content', '')
            
            # Find citations in content (simplified pattern)
            citations = self._extract_citations(content)
            
            for citation in citations:
                # Find matching documents
                for other_doc in documents:
                    if other_doc.get('id') != doc_id:
                        other_title = other_doc.get('metadata', {}).get('title', '')
                        
                        if citation.lower() in other_title.lower() or other_title.lower() in citation.lower():
                            relationship = DocumentRelationship(
                                source_id=doc_id,
                                target_id=other_doc.get('id', ''),
                                relationship_type="cites",
                                strength=0.8,
                                metadata={"citation_text": citation}
                            )
                            
                            asyncio.create_task(self.add_relationship(relationship))
    
    def _extract_citations(self, content: str) -> List[str]:
        """Extract citations from document content"""
        import re
        
        citations = []
        
        # Legal citation patterns
        legal_patterns = [
            r'\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+\b',  # Case citations
            r'\b\d+\s+U\.S\.C\.\s+§\s+\d+\b',        # USC citations
            r'\bArticle\s+\d+\b',                     # Article references
        ]
        
        for pattern in legal_patterns:
            matches = re.findall(pattern, content)
            citations.extend(matches)
        
        return citations

# =============================================================================
# HYBRID SEARCH IMPLEMENTATION
# =============================================================================

class HybridSearchEngine:
    """Hybrid dense-sparse search with intelligent fusion"""
    
    def __init__(self, 
                 dense_weight: float = 0.6,
                 sparse_weight: float = 0.4,
                 fusion_method: str = "rrf"):  # "rrf" or "linear"
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.fusion_method = fusion_method
        self.logger = logging.getLogger(__name__)
        
        # Mock retrievers
        self.dense_retriever = MockSentenceTransformer("all-MiniLM-L6-v2")
        self.sparse_retriever = None  # Will be initialized with corpus
        
        # Performance tracking
        self.search_stats = defaultdict(list)
    
    async def hybrid_search(self, query: str, documents: List[Dict[str, Any]], 
                           k: int = 10, adaptive_weights: bool = True) -> List[Dict[str, Any]]:
        """Execute hybrid dense-sparse search"""
        
        start_time = time.time()
        
        # Initialize sparse retriever with current corpus
        corpus = [doc.get('content', '') for doc in documents]
        self.sparse_retriever = MockBM25(corpus)
        
        # Execute dense search
        dense_start = time.time()
        dense_results = await self._dense_search(query, documents, k * 2)
        dense_time = (time.time() - dense_start) * 1000
        
        # Execute sparse search
        sparse_start = time.time()
        sparse_results = await self._sparse_search(query, documents, k * 2)
        sparse_time = (time.time() - sparse_start) * 1000
        
        # Adapt weights based on query characteristics if enabled
        if adaptive_weights:
            self.dense_weight, self.sparse_weight = self._calculate_adaptive_weights(
                query, dense_results, sparse_results
            )
        
        # Fuse results
        fusion_start = time.time()
        fused_results = self._fuse_results(dense_results, sparse_results, k)
        fusion_time = (time.time() - fusion_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        # Track performance
        self.search_stats['total_time'].append(total_time)
        self.search_stats['dense_time'].append(dense_time)
        self.search_stats['sparse_time'].append(sparse_time)
        self.search_stats['fusion_time'].append(fusion_time)
        
        self.logger.info(f"Hybrid search completed in {total_time:.1f}ms "
                        f"(dense: {self.dense_weight:.2f}, sparse: {self.sparse_weight:.2f})")
        
        return fused_results
    
    async def _dense_search(self, query: str, documents: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Execute dense vector search"""
        
        # Generate query embedding
        query_embedding = self.dense_retriever.encode([query])[0]
        
        # Generate document embeddings (in practice, these would be pre-computed)
        doc_texts = [doc.get('content', '') for doc in documents]
        doc_embeddings = self.dense_retriever.encode(doc_texts)
        
        # Calculate similarities
        similarities = []
        for i, doc_embedding in enumerate(doc_embeddings):
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            similarities.append((similarity, i))
        
        # Sort and select top k
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for similarity, idx in similarities[:k]:
            result = documents[idx].copy()
            result['dense_score'] = float(similarity)
            results.append(result)
        
        return results
    
    async def _sparse_search(self, query: str, documents: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Execute sparse BM25 search"""
        
        # Get BM25 scores
        scores = self.sparse_retriever.get_scores(query)
        
        # Create scored results
        scored_docs = []
        for i, score in enumerate(scores):
            if i < len(documents):
                scored_docs.append((score, i))
        
        # Sort and select top k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, idx in scored_docs[:k]:
            result = documents[idx].copy()
            result['sparse_score'] = float(score)
            results.append(result)
        
        return results
    
    def _calculate_adaptive_weights(self, query: str, 
                                  dense_results: List[Dict[str, Any]], 
                                  sparse_results: List[Dict[str, Any]]) -> Tuple[float, float]:
        """Calculate adaptive weights based on query and result characteristics"""
        
        # Default weights
        dense_w, sparse_w = self.dense_weight, self.sparse_weight
        
        # Adjust based on query length (longer queries often benefit from dense search)
        query_words = len(query.split())
        if query_words > 10:
            dense_w += 0.1
            sparse_w -= 0.1
        elif query_words < 5:
            dense_w -= 0.1
            sparse_w += 0.1
        
        # Adjust based on result quality
        if dense_results:
            avg_dense_score = np.mean([r.get('dense_score', 0) for r in dense_results[:5]])
            if avg_dense_score > 0.8:
                dense_w += 0.05
        
        if sparse_results:
            avg_sparse_score = np.mean([r.get('sparse_score', 0) for r in sparse_results[:5]])
            if avg_sparse_score > 0.8:
                sparse_w += 0.05
        
        # Normalize weights
        total_weight = dense_w + sparse_w
        dense_w /= total_weight
        sparse_w /= total_weight
        
        return dense_w, sparse_w
    
    def _fuse_results(self, dense_results: List[Dict[str, Any]], 
                     sparse_results: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Fuse dense and sparse results"""
        
        if self.fusion_method == "rrf":
            return self._reciprocal_rank_fusion(dense_results, sparse_results, k)
        else:
            return self._linear_fusion(dense_results, sparse_results, k)
    
    def _reciprocal_rank_fusion(self, dense_results: List[Dict[str, Any]], 
                               sparse_results: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion (RRF) for combining results"""
        
        rrf_constant = 60  # Common RRF constant
        doc_scores = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results):
            doc_id = result.get('id', f"doc_{rank}")
            rrf_score = self.dense_weight / (rrf_constant + rank + 1)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': result, 'score': 0}
            doc_scores[doc_id]['score'] += rrf_score
        
        # Process sparse results
        for rank, result in enumerate(sparse_results):
            doc_id = result.get('id', f"doc_{rank}")
            rrf_score = self.sparse_weight / (rrf_constant + rank + 1)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': result, 'score': 0}
            doc_scores[doc_id]['score'] += rrf_score
        
        # Sort by RRF score
        sorted_results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        
        # Return top k with fusion scores
        final_results = []
        for item in sorted_results[:k]:
            result = item['doc'].copy()
            result['fusion_score'] = item['score']
            final_results.append(result)
        
        return final_results
    
    def _linear_fusion(self, dense_results: List[Dict[str, Any]], 
                      sparse_results: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
        """Linear combination fusion"""
        
        doc_scores = {}
        
        # Normalize and combine scores
        max_dense_score = max([r.get('dense_score', 0) for r in dense_results], default=1.0)
        max_sparse_score = max([r.get('sparse_score', 0) for r in sparse_results], default=1.0)
        
        # Process dense results
        for result in dense_results:
            doc_id = result.get('id', '')
            normalized_score = result.get('dense_score', 0) / max_dense_score
            weighted_score = normalized_score * self.dense_weight
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': result, 'score': 0}
            doc_scores[doc_id]['score'] += weighted_score
        
        # Process sparse results
        for result in sparse_results:
            doc_id = result.get('id', '')
            normalized_score = result.get('sparse_score', 0) / max_sparse_score
            weighted_score = normalized_score * self.sparse_weight
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'doc': result, 'score': 0}
            doc_scores[doc_id]['score'] += weighted_score
        
        # Sort and return top k
        sorted_results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        
        final_results = []
        for item in sorted_results[:k]:
            result = item['doc'].copy()
            result['fusion_score'] = item['score']
            final_results.append(result)
        
        return final_results
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        stats = {}
        
        for metric, values in self.search_stats.items():
            if values:
                stats[f"avg_{metric}"] = np.mean(values)
                stats[f"max_{metric}"] = np.max(values)
                stats[f"min_{metric}"] = np.min(values)
        
        return stats

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

async def demonstrate_advanced_rag_patterns():
    """
    Comprehensive demonstration of advanced RAG patterns including
    multi-step retrieval, query expansion, and hybrid search.
    """
    
    print("🚀 Advanced RAG Patterns Demo")
    print("Multi-Step Retrieval, Query Expansion & Hybrid Search")
    print("Enterprise Applications: Legal Research + Content Personalization")
    
    # Sample document corpus
    sample_documents = [
        {
            "id": "legal_doc_1",
            "content": "GDPR Article 6 defines the legal basis for processing personal data. Processing shall be lawful only if consent is given, contract performance is necessary, legal obligation compliance is required, vital interests protection is needed, public task performance is necessary, or legitimate interests are pursued.",
            "metadata": {"title": "GDPR Article 6", "source": "EU Regulation", "domain": "legal"}
        },
        {
            "id": "legal_doc_2", 
            "content": "Contract liability limitations must be reasonable and cannot exclude fundamental breaches. Courts consistently hold that attempts to exclude all liability may be deemed unfair under consumer protection legislation.",
            "metadata": {"title": "Contract Liability", "source": "Case Law", "domain": "legal"}
        },
        {
            "id": "content_doc_1",
            "content": "A/B testing best practices include establishing clear hypotheses, ensuring sufficient sample sizes, and accounting for statistical significance. Test duration should consider weekly patterns and seasonal variations.",
            "metadata": {"title": "A/B Testing Guide", "source": "Marketing Handbook", "domain": "personalization"}
        },
        {
            "id": "content_doc_2",
            "content": "Personalization strategies for e-commerce include behavioral targeting, demographic segmentation, and dynamic content adaptation. Machine learning models can predict user preferences and optimize conversion rates.",
            "metadata": {"title": "Personalization Strategies", "source": "Tech Blog", "domain": "personalization"}
        },
        {
            "id": "content_doc_3",
            "content": "User segmentation frameworks combine demographic, behavioral, and psychographic data. RFM analysis (Recency, Frequency, Monetary) provides foundation for value-based customer segments.",
            "metadata": {"title": "User Segmentation", "source": "Analytics Guide", "domain": "personalization"}
        }
    ]
    
    # Query Analysis Demo
    print("\n" + "="*60)
    print("Query Analysis and Intent Detection")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_queries = [
        ("What are the GDPR compliance requirements for data processing?", "legal"),
        ("How to implement effective A/B testing for conversion optimization?", "personalization"),
        ("Compare different user segmentation strategies and their benefits", "personalization"),
        ("What contract liability limitations are legally enforceable and why do courts reject certain exclusions?", "legal")
    ]
    
    for query, domain in test_queries:
        print(f"\n🔍 Query: {query}")
        print(f"📋 Domain: {domain}")
        print("-" * 50)
        
        intent = await analyzer.analyze_query(query, domain)
        
        print(f"   • Type: {intent.query_type.value}")
        print(f"   • Complexity: {intent.complexity_score:.2f}")
        print(f"   • Entities: {intent.entities}")
        print(f"   • Topics: {intent.topics}")
        print(f"   • Multi-step needed: {intent.requires_multi_step}")
        print(f"   • Domain-specific: {intent.domain_specific}")
    
    # Query Expansion Demo
    print("\n" + "="*60)
    print("Query Expansion and Refinement")
    print("="*60)
    
    expander = QueryExpander()
    
    for query, domain in test_queries[:2]:  # Test first 2 queries
        print(f"\n🔄 Expanding: {query}")
        print("-" * 40)
        
        intent = await analyzer.analyze_query(query, domain)
        expansions = await expander.expand_query(query, intent)
        
        print(f"   Original: {query}")
        for i, expansion in enumerate(expansions[1:6], 1):  # Show top 5 expansions
            print(f"   Expansion {i}: {expansion}")
    
    # Multi-Step Retrieval Demo
    print("\n" + "="*60)
    print("Multi-Step Retrieval Process")
    print("="*60)
    
    retriever = MultiStepRetriever()
    
    complex_query = "What contract liability limitations are legally enforceable and why do courts reject certain exclusions?"
    
    print(f"\n🎯 Complex Query: {complex_query}")
    print("-" * 50)
    
    multi_result = await retriever.multi_step_retrieve(complex_query, k=5, domain="legal")
    
    print(f"\n📊 Multi-Step Results:")
    print(f"   • Original query: {multi_result.original_query}")
    print(f"   • Final query: {multi_result.final_query}")
    print(f"   • Steps executed: {len(multi_result.steps)}")
    print(f"   • Total time: {multi_result.total_time_ms:.1f}ms")
    print(f"   • Confidence: {multi_result.confidence_score:.3f}")
    
    print(f"\n📋 Step Details:")
    for step in multi_result.steps:
        print(f"   Step '{step.step_id}':")
        print(f"     • Query: {step.query}")
        print(f"     • Strategy: {step.strategy.value}")
        print(f"     • Results: {len(step.results)}")
        print(f"     • Time: {step.execution_time_ms:.1f}ms")
        print(f"     • Avg Score: {step.metadata.get('avg_score', 0):.3f}")
    
    print(f"\n🎯 Final Results:")
    for i, result in enumerate(multi_result.combined_results, 1):
        print(f"   {i}. Score: {result.get('final_score', result.get('score', 0)):.3f}")
        print(f"      Content: {result.get('content', '')[:100]}...")
    
    # Hybrid Search Demo
    print("\n" + "="*60)
    print("Hybrid Dense-Sparse Search")
    print("="*60)
    
    hybrid_engine = HybridSearchEngine()
    
    search_queries = [
        "GDPR data processing legal basis",
        "A/B testing conversion optimization",
        "user segmentation behavioral targeting"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Hybrid Search: {query}")
        print("-" * 40)
        
        results = await hybrid_engine.hybrid_search(query, sample_documents, k=3)
        
        print(f"   Results (Dense weight: {hybrid_engine.dense_weight:.2f}, Sparse weight: {hybrid_engine.sparse_weight:.2f}):")
        
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result.get('metadata', {}).get('title', 'Unknown')}")
            print(f"      Fusion Score: {result.get('fusion_score', 0):.3f}")
            print(f"      Dense Score: {result.get('dense_score', 'N/A')}")
            print(f"      Sparse Score: {result.get('sparse_score', 'N/A')}")
    
    # Document Relationship Demo
    print("\n" + "="*60)
    print("Document Relationship Modeling")
    print("="*60)
    
    rel_manager = DocumentRelationshipManager()
    
    # Build sample relationships
    relationships = [
        DocumentRelationship("legal_doc_1", "legal_doc_2", "references", 0.8),
        DocumentRelationship("content_doc_1", "content_doc_2", "complements", 0.7),
        DocumentRelationship("content_doc_2", "content_doc_3", "follows", 0.6)
    ]
    
    for rel in relationships:
        await rel_manager.add_relationship(rel)
    
    # Find related documents
    for doc_id in ["legal_doc_1", "content_doc_1"]:
        print(f"\n🔗 Related to {doc_id}:")
        
        related = await rel_manager.find_related_documents(doc_id, max_depth=2)
        
        for related_id, strength, rel_type in related[:3]:
            print(f"   • {related_id} (strength: {strength:.2f}, type: {rel_type})")
    
    # Performance Analysis
    print("\n" + "="*60)
    print("Performance Analysis")
    print("="*60)
    
    hybrid_stats = hybrid_engine.get_performance_stats()
    
    print(f"\n📈 Hybrid Search Performance:")
    for metric, value in hybrid_stats.items():
        print(f"   • {metric}: {value:.2f}ms" if 'time' in metric else f"   • {metric}: {value:.3f}")
    
    # Advanced Pattern Comparison
    print("\n" + "="*60)
    print("Pattern Effectiveness Comparison")
    print("="*60)
    
    comparison_query = "How to implement GDPR-compliant user segmentation?"
    
    print(f"\n🎯 Comparison Query: {comparison_query}")
    print("-" * 50)
    
    # Simple retrieval
    simple_results = await hybrid_engine.hybrid_search(comparison_query, sample_documents, k=3)
    
    # Multi-step retrieval
    multi_step_results = await retriever.multi_step_retrieve(comparison_query, k=3, domain="legal")
    
    print(f"\n📊 Results Comparison:")
    print(f"\n   Simple Hybrid Search:")
    for i, result in enumerate(simple_results[:2], 1):
        print(f"     {i}. {result.get('metadata', {}).get('title', 'Unknown')} (score: {result.get('fusion_score', 0):.3f})")
    
    print(f"\n   Multi-Step Retrieval:")
    for i, result in enumerate(multi_step_results.combined_results[:2], 1):
        print(f"     {i}. Mock result {i} (score: {result.get('final_score', result.get('score', 0)):.3f})")
    
    print(f"\n   Performance Comparison:")
    print(f"     • Simple search: ~{np.mean(hybrid_stats.get('avg_total_time', [50])):.1f}ms")
    print(f"     • Multi-step search: {multi_step_results.total_time_ms:.1f}ms")
    print(f"     • Multi-step confidence: {multi_step_results.confidence_score:.3f}")
    
    # Best Practices Summary
    print("\n" + "="*60)
    print("Advanced RAG Best Practices")
    print("="*60)
    
    print(f"\n🎯 Pattern Selection Guidelines:")
    print(f"\nSimple Queries (Low Complexity):")
    print(f"   • Use hybrid search with balanced weights")
    print(f"   • Single-step retrieval sufficient")
    print(f"   • Focus on relevance ranking")
    
    print(f"\nComplex Queries (High Complexity):")
    print(f"   • Use multi-step retrieval with query refinement")
    print(f"   • Apply contextual expansion")
    print(f"   • Consider document relationships")
    
    print(f"\nDomain-Specific Queries:")
    print(f"   • Adjust weights based on domain characteristics")
    print(f"   • Use specialized intent detection")
    print(f"   • Apply domain vocabulary expansion")
    
    print(f"\nPerformance Optimization:")
    print(f"   • Cache query expansions and embeddings")
    print(f"   • Use adaptive weights based on query type")
    print(f"   • Implement result deduplication")
    print(f"   • Monitor and adjust fusion methods")
    
    print("\n" + "="*60)
    print("✅ Advanced RAG Patterns Demo Complete")
    print("="*60)
    
    print(f"\n🎯 Key Achievements:")
    print(f"   • Demonstrated intelligent query analysis and intent detection")
    print(f"   • Implemented multi-step retrieval with query refinement")
    print(f"   • Showcased hybrid dense-sparse search with adaptive weights")
    print(f"   • Built document relationship modeling and graph traversal")
    print(f"   • Provided contextual query expansion strategies")
    print(f"   • Delivered performance optimization and best practices")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Import numpy for calculations
    import numpy as np
    
    # Run comprehensive advanced RAG demonstration
    asyncio.run(demonstrate_advanced_rag_patterns())
"""
Vector Database Implementation and Optimization

This module demonstrates comprehensive vector database implementations
with support for multiple providers and production optimizations.

Key concepts covered:
- Vector database abstraction layer
- Pinecone, Qdrant, and Weaviate implementations
- Index optimization and scaling strategies
- Metadata filtering and hybrid search
- Performance monitoring and benchmarking

Real-world applications:
- Legal document search for Lawstronaut
- Content recommendation for Optimizely

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import json
import logging
import time
import numpy as np
from datetime import datetime, timedelta
import uuid
import hashlib
from enum import Enum
import concurrent.futures
from contextlib import asynccontextmanager

# Mock external dependencies (replace with actual libraries in production)
class MockPinecone:
    class Index:
        def __init__(self, name: str):
            self.name = name
            self._vectors = {}
            self._metadata = {}
        
        async def upsert(self, vectors: List[Dict], **kwargs):
            for vector in vectors:
                self._vectors[vector['id']] = vector['values']
                if 'metadata' in vector:
                    self._metadata[vector['id']] = vector['metadata']
        
        async def query(self, vector: List[float], top_k: int = 10, filter: Dict = None, **kwargs):
            # Simple mock similarity computation
            similarities = []
            for vec_id, vec_values in self._vectors.items():
                if filter:
                    metadata = self._metadata.get(vec_id, {})
                    if not all(metadata.get(k) == v for k, v in filter.items()):
                        continue
                
                # Mock cosine similarity
                similarity = np.random.random()
                similarities.append({
                    'id': vec_id,
                    'score': similarity,
                    'metadata': self._metadata.get(vec_id, {})
                })
            
            # Sort by score and return top_k
            similarities.sort(key=lambda x: x['score'], reverse=True)
            return {'matches': similarities[:top_k]}

class MockQdrant:
    class QdrantClient:
        def __init__(self, **kwargs):
            self.collections = {}
        
        async def upsert(self, collection_name: str, points: List[Dict]):
            if collection_name not in self.collections:
                self.collections[collection_name] = {}
            
            for point in points:
                self.collections[collection_name][point['id']] = {
                    'vector': point['vector'],
                    'payload': point.get('payload', {})
                }
        
        async def search(self, collection_name: str, query_vector: List[float], 
                        limit: int = 10, query_filter: Dict = None):
            if collection_name not in self.collections:
                return []
            
            collection = self.collections[collection_name]
            results = []
            
            for point_id, data in collection.items():
                if query_filter:
                    payload = data.get('payload', {})
                    if not all(payload.get(k) == v for k, v in query_filter.items()):
                        continue
                
                # Mock similarity score
                score = np.random.random()
                results.append({
                    'id': point_id,
                    'score': score,
                    'payload': data.get('payload', {})
                })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]

class MockWeaviate:
    class Client:
        def __init__(self, **kwargs):
            self.objects = {}
            self.classes = {}
        
        def schema_create_class(self, class_obj: Dict):
            self.classes[class_obj['class']] = class_obj
        
        async def data_object_create(self, data_object: Dict, class_name: str, uuid_val: str = None):
            if uuid_val is None:
                uuid_val = str(uuid.uuid4())
            
            self.objects[uuid_val] = {
                'class': class_name,
                'properties': data_object,
                'vector': np.random.random(384).tolist()  # Mock vector
            }
            return uuid_val
        
        async def query_near_vector(self, class_name: str, vector: List[float], 
                                   limit: int = 10, where: Dict = None):
            results = []
            
            for obj_id, obj_data in self.objects.items():
                if obj_data['class'] != class_name:
                    continue
                
                if where:
                    properties = obj_data.get('properties', {})
                    # Simplified where filtering
                    path = where.get('path', [])
                    operator = where.get('operator')
                    value = where.get('valueString') or where.get('valueInt')
                    
                    if path and len(path) > 0:
                        prop_value = properties.get(path[0])
                        if operator == 'Equal' and prop_value != value:
                            continue
                
                # Mock similarity score
                score = np.random.random()
                results.append({
                    'id': obj_id,
                    'score': score,
                    'properties': obj_data.get('properties', {})
                })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]

# =============================================================================
# CORE VECTOR DATABASE INTERFACES
# =============================================================================

class VectorSearchResult:
    """Standardized vector search result"""
    
    def __init__(self, id: str, score: float, metadata: Dict[str, Any] = None):
        self.id = id
        self.score = score
        self.metadata = metadata or {}

class VectorDatabaseConfig:
    """Configuration for vector database connections"""
    
    def __init__(self, 
                 provider: str,
                 connection_params: Dict[str, Any] = None,
                 index_config: Dict[str, Any] = None):
        self.provider = provider
        self.connection_params = connection_params or {}
        self.index_config = index_config or {}

class VectorDatabase(ABC):
    """Enhanced abstract base class for vector databases"""
    
    @abstractmethod
    async def initialize(self, config: VectorDatabaseConfig) -> bool:
        """Initialize database connection and configuration"""
        pass
    
    @abstractmethod
    async def create_index(self, index_name: str, dimension: int, 
                          metric: str = "cosine", **kwargs) -> bool:
        """Create a new vector index"""
        pass
    
    @abstractmethod
    async def upsert_vectors(self, index_name: str, vectors: List[Dict[str, Any]]) -> bool:
        """Insert or update vectors with metadata"""
        pass
    
    @abstractmethod
    async def search_vectors(self, index_name: str, query_vector: List[float], 
                            k: int = 10, filters: Dict = None, **kwargs) -> List[VectorSearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete_vectors(self, index_name: str, vector_ids: List[str]) -> bool:
        """Delete vectors by IDs"""
        pass
    
    @abstractmethod
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get index statistics and metadata"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close database connection"""
        pass

# =============================================================================
# PINECONE IMPLEMENTATION
# =============================================================================

class PineconeVectorDB(VectorDatabase):
    """Pinecone vector database implementation"""
    
    def __init__(self):
        self.client = None
        self.indexes = {}
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self, config: VectorDatabaseConfig) -> bool:
        """Initialize Pinecone connection"""
        try:
            # In real implementation: pinecone.init()
            self.client = MockPinecone()
            
            self.logger.info("Pinecone client initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Pinecone: {e}")
            return False
    
    async def create_index(self, index_name: str, dimension: int, 
                          metric: str = "cosine", **kwargs) -> bool:
        """Create Pinecone index"""
        try:
            # In real implementation: pinecone.create_index()
            index = MockPinecone.Index(index_name)
            self.indexes[index_name] = index
            
            self.logger.info(f"Created Pinecone index: {index_name} (dimension: {dimension})")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to create Pinecone index {index_name}: {e}")
            return False
    
    async def upsert_vectors(self, index_name: str, vectors: List[Dict[str, Any]]) -> bool:
        """Upsert vectors to Pinecone index"""
        try:
            if index_name not in self.indexes:
                raise ValueError(f"Index {index_name} not found")
            
            index = self.indexes[index_name]
            
            # Format vectors for Pinecone
            pinecone_vectors = []
            for vector in vectors:
                pinecone_vector = {
                    'id': vector['id'],
                    'values': vector['values'],
                }
                if 'metadata' in vector:
                    pinecone_vector['metadata'] = vector['metadata']
                
                pinecone_vectors.append(pinecone_vector)
            
            # Batch upsert (Pinecone supports up to 100 vectors per request)
            batch_size = 100
            for i in range(0, len(pinecone_vectors), batch_size):
                batch = pinecone_vectors[i:i + batch_size]
                await index.upsert(vectors=batch)
            
            self.logger.info(f"Upserted {len(vectors)} vectors to Pinecone index {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to upsert vectors to Pinecone: {e}")
            return False
    
    async def search_vectors(self, index_name: str, query_vector: List[float], 
                            k: int = 10, filters: Dict = None, **kwargs) -> List[VectorSearchResult]:
        """Search vectors in Pinecone index"""
        try:
            if index_name not in self.indexes:
                raise ValueError(f"Index {index_name} not found")
            
            index = self.indexes[index_name]
            
            # Prepare query parameters
            query_params = {
                'vector': query_vector,
                'top_k': k,
                'include_metadata': True,
                'include_values': False
            }
            
            if filters:
                query_params['filter'] = filters
            
            # Execute search
            response = await index.query(**query_params)
            
            # Convert to standardized results
            results = []
            for match in response['matches']:
                result = VectorSearchResult(
                    id=match['id'],
                    score=match['score'],
                    metadata=match.get('metadata', {})
                )
                results.append(result)
            
            self.logger.info(f"Found {len(results)} results in Pinecone search")
            return results
        
        except Exception as e:
            self.logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def delete_vectors(self, index_name: str, vector_ids: List[str]) -> bool:
        """Delete vectors from Pinecone index"""
        try:
            if index_name not in self.indexes:
                raise ValueError(f"Index {index_name} not found")
            
            # In real implementation: index.delete(ids=vector_ids)
            self.logger.info(f"Deleted {len(vector_ids)} vectors from Pinecone index {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to delete vectors from Pinecone: {e}")
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        if index_name not in self.indexes:
            return {}
        
        return {
            "provider": "pinecone",
            "index_name": index_name,
            "total_vectors": len(self.indexes[index_name]._vectors),
            "dimension": 384,  # Mock dimension
            "metric": "cosine"
        }
    
    async def close(self):
        """Close Pinecone connection"""
        self.indexes.clear()
        self.client = None
        self.logger.info("Pinecone connection closed")

# =============================================================================
# QDRANT IMPLEMENTATION
# =============================================================================

class QdrantVectorDB(VectorDatabase):
    """Qdrant vector database implementation"""
    
    def __init__(self):
        self.client = None
        self.collections = set()
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self, config: VectorDatabaseConfig) -> bool:
        """Initialize Qdrant connection"""
        try:
            # In real implementation: QdrantClient(host=..., port=...)
            self.client = MockQdrant.QdrantClient()
            
            self.logger.info("Qdrant client initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {e}")
            return False
    
    async def create_index(self, index_name: str, dimension: int, 
                          metric: str = "cosine", **kwargs) -> bool:
        """Create Qdrant collection (equivalent to index)"""
        try:
            # In real implementation: client.recreate_collection()
            self.collections.add(index_name)
            
            self.logger.info(f"Created Qdrant collection: {index_name} (dimension: {dimension})")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to create Qdrant collection {index_name}: {e}")
            return False
    
    async def upsert_vectors(self, index_name: str, vectors: List[Dict[str, Any]]) -> bool:
        """Upsert vectors to Qdrant collection"""
        try:
            if index_name not in self.collections:
                raise ValueError(f"Collection {index_name} not found")
            
            # Format vectors for Qdrant
            qdrant_points = []
            for vector in vectors:
                point = {
                    'id': vector['id'],
                    'vector': vector['values'],
                }
                if 'metadata' in vector:
                    point['payload'] = vector['metadata']
                
                qdrant_points.append(point)
            
            # Batch upsert
            await self.client.upsert(
                collection_name=index_name,
                points=qdrant_points
            )
            
            self.logger.info(f"Upserted {len(vectors)} vectors to Qdrant collection {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to upsert vectors to Qdrant: {e}")
            return False
    
    async def search_vectors(self, index_name: str, query_vector: List[float], 
                            k: int = 10, filters: Dict = None, **kwargs) -> List[VectorSearchResult]:
        """Search vectors in Qdrant collection"""
        try:
            if index_name not in self.collections:
                raise ValueError(f"Collection {index_name} not found")
            
            # Prepare query filter
            query_filter = None
            if filters:
                # Convert filters to Qdrant format
                query_filter = filters  # Simplified - real implementation needs proper format
            
            # Execute search
            search_result = await self.client.search(
                collection_name=index_name,
                query_vector=query_vector,
                limit=k,
                query_filter=query_filter
            )
            
            # Convert to standardized results
            results = []
            for hit in search_result:
                result = VectorSearchResult(
                    id=hit['id'],
                    score=hit['score'],
                    metadata=hit.get('payload', {})
                )
                results.append(result)
            
            self.logger.info(f"Found {len(results)} results in Qdrant search")
            return results
        
        except Exception as e:
            self.logger.error(f"Qdrant search failed: {e}")
            return []
    
    async def delete_vectors(self, index_name: str, vector_ids: List[str]) -> bool:
        """Delete vectors from Qdrant collection"""
        try:
            if index_name not in self.collections:
                raise ValueError(f"Collection {index_name} not found")
            
            # In real implementation: client.delete()
            self.logger.info(f"Deleted {len(vector_ids)} vectors from Qdrant collection {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to delete vectors from Qdrant: {e}")
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get Qdrant collection statistics"""
        if index_name not in self.collections:
            return {}
        
        return {
            "provider": "qdrant",
            "collection_name": index_name,
            "total_vectors": 1000,  # Mock count
            "dimension": 384,
            "metric": "cosine"
        }
    
    async def close(self):
        """Close Qdrant connection"""
        self.collections.clear()
        self.client = None
        self.logger.info("Qdrant connection closed")

# =============================================================================
# WEAVIATE IMPLEMENTATION
# =============================================================================

class WeaviateVectorDB(VectorDatabase):
    """Weaviate vector database implementation"""
    
    def __init__(self):
        self.client = None
        self.classes = set()
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self, config: VectorDatabaseConfig) -> bool:
        """Initialize Weaviate connection"""
        try:
            # In real implementation: weaviate.Client()
            self.client = MockWeaviate.Client()
            
            self.logger.info("Weaviate client initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to initialize Weaviate: {e}")
            return False
    
    async def create_index(self, index_name: str, dimension: int, 
                          metric: str = "cosine", **kwargs) -> bool:
        """Create Weaviate class (equivalent to index)"""
        try:
            # Define class schema
            class_obj = {
                "class": index_name,
                "description": f"Vector index for {index_name}",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Content text"
                    },
                    {
                        "name": "source",
                        "dataType": ["string"],
                        "description": "Source document"
                    }
                ],
                "vectorizer": "none",  # We provide our own vectors
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "distance": metric,
                    "efConstruction": 128,
                    "maxConnections": 64
                }
            }
            
            self.client.schema_create_class(class_obj)
            self.classes.add(index_name)
            
            self.logger.info(f"Created Weaviate class: {index_name} (dimension: {dimension})")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to create Weaviate class {index_name}: {e}")
            return False
    
    async def upsert_vectors(self, index_name: str, vectors: List[Dict[str, Any]]) -> bool:
        """Upsert vectors to Weaviate class"""
        try:
            if index_name not in self.classes:
                raise ValueError(f"Class {index_name} not found")
            
            # Insert objects with vectors
            for vector in vectors:
                data_object = vector.get('metadata', {})
                
                await self.client.data_object_create(
                    data_object=data_object,
                    class_name=index_name,
                    uuid_val=vector['id']
                )
            
            self.logger.info(f"Upserted {len(vectors)} vectors to Weaviate class {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to upsert vectors to Weaviate: {e}")
            return False
    
    async def search_vectors(self, index_name: str, query_vector: List[float], 
                            k: int = 10, filters: Dict = None, **kwargs) -> List[VectorSearchResult]:
        """Search vectors in Weaviate class"""
        try:
            if index_name not in self.classes:
                raise ValueError(f"Class {index_name} not found")
            
            # Prepare where filter
            where_filter = None
            if filters:
                # Convert to Weaviate where format (simplified)
                filter_key = list(filters.keys())[0]
                filter_value = filters[filter_key]
                
                where_filter = {
                    "path": [filter_key],
                    "operator": "Equal",
                    "valueString": filter_value if isinstance(filter_value, str) else None,
                    "valueInt": filter_value if isinstance(filter_value, int) else None
                }
            
            # Execute near vector search
            results = await self.client.query_near_vector(
                class_name=index_name,
                vector=query_vector,
                limit=k,
                where=where_filter
            )
            
            # Convert to standardized results
            search_results = []
            for result in results:
                search_result = VectorSearchResult(
                    id=result['id'],
                    score=result['score'],
                    metadata=result.get('properties', {})
                )
                search_results.append(search_result)
            
            self.logger.info(f"Found {len(search_results)} results in Weaviate search")
            return search_results
        
        except Exception as e:
            self.logger.error(f"Weaviate search failed: {e}")
            return []
    
    async def delete_vectors(self, index_name: str, vector_ids: List[str]) -> bool:
        """Delete vectors from Weaviate class"""
        try:
            if index_name not in self.classes:
                raise ValueError(f"Class {index_name} not found")
            
            # In real implementation: client.data_object.delete()
            self.logger.info(f"Deleted {len(vector_ids)} vectors from Weaviate class {index_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to delete vectors from Weaviate: {e}")
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get Weaviate class statistics"""
        if index_name not in self.classes:
            return {}
        
        return {
            "provider": "weaviate",
            "class_name": index_name,
            "total_objects": 500,  # Mock count
            "dimension": 384,
            "metric": "cosine"
        }
    
    async def close(self):
        """Close Weaviate connection"""
        self.classes.clear()
        self.client = None
        self.logger.info("Weaviate connection closed")

# =============================================================================
# VECTOR DATABASE MANAGER
# =============================================================================

class VectorDatabaseManager:
    """Manager for multiple vector database providers"""
    
    def __init__(self):
        self.databases: Dict[str, VectorDatabase] = {}
        self.active_database: Optional[str] = None
        self.logger = logging.getLogger(__name__)
    
    async def add_database(self, name: str, database: VectorDatabase, 
                          config: VectorDatabaseConfig) -> bool:
        """Add and initialize a vector database"""
        try:
            success = await database.initialize(config)
            if success:
                self.databases[name] = database
                if self.active_database is None:
                    self.active_database = name
                
                self.logger.info(f"Added vector database: {name} (provider: {config.provider})")
                return True
            else:
                self.logger.error(f"Failed to initialize database: {name}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error adding database {name}: {e}")
            return False
    
    def set_active_database(self, name: str) -> bool:
        """Set the active database for operations"""
        if name in self.databases:
            self.active_database = name
            self.logger.info(f"Switched to database: {name}")
            return True
        else:
            self.logger.error(f"Database {name} not found")
            return False
    
    async def create_index(self, index_name: str, dimension: int, 
                          metric: str = "cosine", database_name: str = None, **kwargs) -> bool:
        """Create index in specified or active database"""
        db_name = database_name or self.active_database
        
        if db_name not in self.databases:
            self.logger.error(f"Database {db_name} not found")
            return False
        
        return await self.databases[db_name].create_index(index_name, dimension, metric, **kwargs)
    
    async def upsert_vectors(self, index_name: str, vectors: List[Dict[str, Any]], 
                            database_name: str = None) -> bool:
        """Upsert vectors to specified or active database"""
        db_name = database_name or self.active_database
        
        if db_name not in self.databases:
            self.logger.error(f"Database {db_name} not found")
            return False
        
        return await self.databases[db_name].upsert_vectors(index_name, vectors)
    
    async def search_vectors(self, index_name: str, query_vector: List[float], 
                            k: int = 10, filters: Dict = None, database_name: str = None, 
                            **kwargs) -> List[VectorSearchResult]:
        """Search vectors in specified or active database"""
        db_name = database_name or self.active_database
        
        if db_name not in self.databases:
            self.logger.error(f"Database {db_name} not found")
            return []
        
        return await self.databases[db_name].search_vectors(index_name, query_vector, k, filters, **kwargs)
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all databases"""
        all_stats = {}
        
        for db_name, database in self.databases.items():
            try:
                # Get index stats for each database (simplified)
                stats = {
                    "provider": "unknown",
                    "status": "connected",
                    "indexes": []
                }
                all_stats[db_name] = stats
            
            except Exception as e:
                all_stats[db_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return all_stats
    
    async def close_all(self):
        """Close all database connections"""
        for name, database in self.databases.items():
            try:
                await database.close()
                self.logger.info(f"Closed database: {name}")
            except Exception as e:
                self.logger.error(f"Error closing database {name}: {e}")
        
        self.databases.clear()
        self.active_database = None

# =============================================================================
# PERFORMANCE BENCHMARKING
# =============================================================================

class VectorDatabaseBenchmark:
    """Benchmark different vector database implementations"""
    
    def __init__(self, manager: VectorDatabaseManager):
        self.manager = manager
        self.logger = logging.getLogger(__name__)
    
    async def run_benchmark(self, 
                           databases: List[str],
                           index_name: str,
                           dimension: int = 384,
                           num_vectors: int = 1000,
                           num_queries: int = 100) -> Dict[str, Dict[str, float]]:
        """Run comprehensive benchmark across databases"""
        
        results = {}
        
        # Generate test data
        test_vectors = self._generate_test_vectors(num_vectors, dimension)
        test_queries = self._generate_test_vectors(num_queries, dimension)
        
        for db_name in databases:
            if db_name not in self.manager.databases:
                self.logger.warning(f"Database {db_name} not found, skipping")
                continue
            
            self.logger.info(f"Benchmarking database: {db_name}")
            
            try:
                # Set active database
                self.manager.set_active_database(db_name)
                
                # Create index
                await self.manager.create_index(index_name, dimension)
                
                # Benchmark upsert performance
                upsert_time = await self._benchmark_upsert(index_name, test_vectors)
                
                # Benchmark search performance
                search_time = await self._benchmark_search(index_name, test_queries)
                
                results[db_name] = {
                    "upsert_time_ms": upsert_time,
                    "search_time_ms": search_time,
                    "vectors_per_sec_upsert": (num_vectors / upsert_time) * 1000,
                    "queries_per_sec": (num_queries / search_time) * 1000
                }
                
                self.logger.info(f"Benchmark complete for {db_name}")
            
            except Exception as e:
                self.logger.error(f"Benchmark failed for {db_name}: {e}")
                results[db_name] = {"error": str(e)}
        
        return results
    
    def _generate_test_vectors(self, num_vectors: int, dimension: int) -> List[Dict[str, Any]]:
        """Generate test vectors for benchmarking"""
        vectors = []
        
        for i in range(num_vectors):
            vector = {
                "id": f"test_vector_{i}",
                "values": np.random.random(dimension).tolist(),
                "metadata": {
                    "content": f"Test document {i}",
                    "source": f"test_source_{i % 10}",
                    "category": f"category_{i % 5}"
                }
            }
            vectors.append(vector)
        
        return vectors
    
    async def _benchmark_upsert(self, index_name: str, vectors: List[Dict[str, Any]]) -> float:
        """Benchmark vector upsert performance"""
        start_time = time.time()
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            await self.manager.upsert_vectors(index_name, batch)
        
        end_time = time.time()
        return (end_time - start_time) * 1000  # Return milliseconds
    
    async def _benchmark_search(self, index_name: str, query_vectors: List[Dict[str, Any]]) -> float:
        """Benchmark vector search performance"""
        start_time = time.time()
        
        for query_data in query_vectors:
            query_vector = query_data["values"]
            results = await self.manager.search_vectors(index_name, query_vector, k=10)
        
        end_time = time.time()
        return (end_time - start_time) * 1000  # Return milliseconds

# =============================================================================
# ENTERPRISE SCENARIOS
# =============================================================================

class LegalDocumentVectorSystem:
    """Specialized vector system for legal document search - Lawstronaut scenario"""
    
    def __init__(self, manager: VectorDatabaseManager):
        self.manager = manager
        self.index_name = "legal_documents"
        self.logger = logging.getLogger(__name__)
    
    async def setup_legal_index(self, database_name: str = None):
        """Setup optimized index for legal documents"""
        
        # Create index with legal-specific optimizations
        success = await self.manager.create_index(
            index_name=self.index_name,
            dimension=384,
            metric="cosine",
            database_name=database_name
        )
        
        if success:
            # Add sample legal documents
            await self._populate_legal_documents()
            self.logger.info("Legal document index setup complete")
        
        return success
    
    async def _populate_legal_documents(self):
        """Populate with sample legal documents"""
        
        legal_docs = [
            {
                "id": "gdpr_art_5",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "GDPR Article 5 - Principles of Processing",
                    "content": "Personal data shall be processed lawfully, fairly and in a transparent manner...",
                    "jurisdiction": "EU",
                    "document_type": "regulation",
                    "practice_area": "data_protection",
                    "language": "en",
                    "confidence_score": 0.95
                }
            },
            {
                "id": "contract_formation_principles",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "Contract Formation Principles",
                    "content": "A contract is formed when there is offer, acceptance, and consideration...",
                    "jurisdiction": "UK",
                    "document_type": "case_law",
                    "practice_area": "contract_law",
                    "language": "en",
                    "confidence_score": 0.88
                }
            },
            {
                "id": "intellectual_property_basics",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "Intellectual Property Protection",
                    "content": "Intellectual property rights include patents, trademarks, copyrights...",
                    "jurisdiction": "US",
                    "document_type": "statute",
                    "practice_area": "ip_law",
                    "language": "en",
                    "confidence_score": 0.92
                }
            }
        ]
        
        await self.manager.upsert_vectors(self.index_name, legal_docs)
    
    async def search_legal_documents(self, query_vector: List[float], 
                                   jurisdiction: str = None,
                                   practice_area: str = None,
                                   document_type: str = None,
                                   k: int = 10) -> List[VectorSearchResult]:
        """Search legal documents with specialized filters"""
        
        # Build filters
        filters = {}
        if jurisdiction:
            filters["jurisdiction"] = jurisdiction
        if practice_area:
            filters["practice_area"] = practice_area
        if document_type:
            filters["document_type"] = document_type
        
        # Perform search
        results = await self.manager.search_vectors(
            index_name=self.index_name,
            query_vector=query_vector,
            k=k,
            filters=filters
        )
        
        # Enhance results with legal-specific scoring
        enhanced_results = []
        for result in results:
            # Apply legal-specific relevance adjustments
            adjusted_score = self._adjust_legal_relevance_score(result)
            result.score = adjusted_score
            enhanced_results.append(result)
        
        # Re-sort by adjusted scores
        enhanced_results.sort(key=lambda x: x.score, reverse=True)
        
        return enhanced_results
    
    def _adjust_legal_relevance_score(self, result: VectorSearchResult) -> float:
        """Adjust relevance score based on legal-specific factors"""
        base_score = result.score
        metadata = result.metadata
        
        # Boost for high confidence legal documents
        confidence_boost = metadata.get("confidence_score", 0.5) * 0.1
        
        # Boost for authoritative sources
        authority_sources = ["regulation", "statute", "case_law"]
        authority_boost = 0.05 if metadata.get("document_type") in authority_sources else 0
        
        # Boost for recent documents (simplified)
        recency_boost = 0.02  # Mock recency calculation
        
        adjusted_score = base_score + confidence_boost + authority_boost + recency_boost
        
        return min(adjusted_score, 1.0)  # Cap at 1.0

class ContentPersonalizationVectorSystem:
    """Specialized vector system for content personalization - Optimizely scenario"""
    
    def __init__(self, manager: VectorDatabaseManager):
        self.manager = manager
        self.index_name = "content_library"
        self.user_embeddings_index = "user_profiles"
        self.logger = logging.getLogger(__name__)
    
    async def setup_personalization_indexes(self, database_name: str = None):
        """Setup indexes for content personalization"""
        
        # Create content library index
        content_success = await self.manager.create_index(
            index_name=self.index_name,
            dimension=384,
            metric="cosine",
            database_name=database_name
        )
        
        # Create user profiles index
        user_success = await self.manager.create_index(
            index_name=self.user_embeddings_index,
            dimension=384,
            metric="cosine",
            database_name=database_name
        )
        
        if content_success and user_success:
            # Populate with sample data
            await self._populate_content_library()
            await self._populate_user_profiles()
            self.logger.info("Personalization indexes setup complete")
        
        return content_success and user_success
    
    async def _populate_content_library(self):
        """Populate with sample content"""
        
        content_items = [
            {
                "id": "ab_testing_guide",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "Complete A/B Testing Guide",
                    "content_type": "article",
                    "category": "optimization",
                    "tags": ["ab_testing", "conversion", "statistics"],
                    "difficulty": "intermediate",
                    "engagement_score": 8.5,
                    "conversion_impact": "high"
                }
            },
            {
                "id": "personalization_strategies",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "Advanced Personalization Strategies",
                    "content_type": "whitepaper",
                    "category": "personalization",
                    "tags": ["personalization", "machine_learning", "user_experience"],
                    "difficulty": "advanced",
                    "engagement_score": 9.2,
                    "conversion_impact": "very_high"
                }
            },
            {
                "id": "beginner_analytics",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "title": "Analytics for Beginners",
                    "content_type": "tutorial",
                    "category": "analytics",
                    "tags": ["analytics", "basics", "getting_started"],
                    "difficulty": "beginner",
                    "engagement_score": 7.8,
                    "conversion_impact": "medium"
                }
            }
        ]
        
        await self.manager.upsert_vectors(self.index_name, content_items)
    
    async def _populate_user_profiles(self):
        """Populate with sample user profiles"""
        
        user_profiles = [
            {
                "id": "user_pm_001",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "role": "product_manager",
                    "experience_level": "senior",
                    "interests": ["conversion_optimization", "user_experience"],
                    "preferred_difficulty": "intermediate",
                    "engagement_history": ["ab_testing", "analytics"]
                }
            },
            {
                "id": "user_analyst_002",
                "values": np.random.random(384).tolist(),
                "metadata": {
                    "role": "data_analyst",
                    "experience_level": "junior",
                    "interests": ["analytics", "statistics", "data_visualization"],
                    "preferred_difficulty": "beginner",
                    "engagement_history": ["basics", "tutorials"]
                }
            }
        ]
        
        await self.manager.upsert_vectors(self.user_embeddings_index, user_profiles)
    
    async def get_personalized_content(self, user_id: str, 
                                     content_preferences: Dict[str, Any] = None,
                                     k: int = 5) -> List[VectorSearchResult]:
        """Get personalized content recommendations"""
        
        # Get user profile embedding
        user_results = await self.manager.search_vectors(
            index_name=self.user_embeddings_index,
            query_vector=np.random.random(384).tolist(),  # Mock user query
            k=1,
            filters={"user_id": user_id} if user_id else None
        )
        
        if not user_results:
            # Fallback to general recommendations
            return await self._get_general_recommendations(k)
        
        user_profile = user_results[0]
        user_embedding = np.random.random(384).tolist()  # Mock user embedding
        
        # Build content filters based on user profile and preferences
        filters = {}
        
        # Apply user preference filters
        if content_preferences:
            if content_preferences.get("category"):
                filters["category"] = content_preferences["category"]
            if content_preferences.get("difficulty"):
                filters["difficulty"] = content_preferences["difficulty"]
        else:
            # Use profile-based filters
            metadata = user_profile.metadata
            if metadata.get("preferred_difficulty"):
                filters["difficulty"] = metadata["preferred_difficulty"]
        
        # Search for personalized content
        content_results = await self.manager.search_vectors(
            index_name=self.index_name,
            query_vector=user_embedding,
            k=k * 2,  # Get more results to allow for diversification
            filters=filters
        )
        
        # Apply personalization scoring and diversification
        personalized_results = self._apply_personalization_scoring(
            content_results, 
            user_profile.metadata,
            content_preferences
        )
        
        # Return top k results
        return personalized_results[:k]
    
    async def _get_general_recommendations(self, k: int) -> List[VectorSearchResult]:
        """Get general content recommendations for unknown users"""
        
        # Use a general query embedding
        general_query = np.random.random(384).tolist()
        
        results = await self.manager.search_vectors(
            index_name=self.index_name,
            query_vector=general_query,
            k=k,
            filters={"engagement_score": 8.0}  # High engagement content
        )
        
        return results
    
    def _apply_personalization_scoring(self, 
                                     content_results: List[VectorSearchResult],
                                     user_profile: Dict[str, Any],
                                     preferences: Dict[str, Any] = None) -> List[VectorSearchResult]:
        """Apply personalization scoring to content results"""
        
        for result in content_results:
            metadata = result.metadata
            personalization_score = 0.0
            
            # Interest matching
            user_interests = user_profile.get("interests", [])
            content_tags = metadata.get("tags", [])
            interest_overlap = len(set(user_interests) & set(content_tags))
            personalization_score += interest_overlap * 0.2
            
            # Experience level matching
            user_level = user_profile.get("experience_level", "")
            content_difficulty = metadata.get("difficulty", "")
            
            if user_level == "senior" and content_difficulty in ["intermediate", "advanced"]:
                personalization_score += 0.15
            elif user_level == "junior" and content_difficulty == "beginner":
                personalization_score += 0.15
            
            # Engagement score boost
            engagement_score = metadata.get("engagement_score", 0)
            personalization_score += (engagement_score / 10) * 0.1
            
            # Conversion impact boost
            conversion_impact = metadata.get("conversion_impact", "")
            impact_scores = {"low": 0, "medium": 0.05, "high": 0.1, "very_high": 0.15}
            personalization_score += impact_scores.get(conversion_impact, 0)
            
            # Apply personalization score
            result.score = (result.score * 0.7) + (personalization_score * 0.3)
        
        # Sort by personalized scores
        content_results.sort(key=lambda x: x.score, reverse=True)
        
        return content_results

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

async def demonstrate_vector_databases():
    """
    Comprehensive demonstration of vector database implementations
    with multiple providers and enterprise scenarios.
    """
    
    print("🚀 Vector Database Implementation Demo")
    print("Multi-Provider Support with Enterprise Optimization")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Personalization)")
    
    # Initialize database manager
    manager = VectorDatabaseManager()
    
    # Setup different vector databases
    print("\n" + "="*60)
    print("Database Initialization")
    print("="*60)
    
    # Add Pinecone
    pinecone_db = PineconeVectorDB()
    pinecone_config = VectorDatabaseConfig("pinecone")
    await manager.add_database("pinecone", pinecone_db, pinecone_config)
    
    # Add Qdrant
    qdrant_db = QdrantVectorDB()
    qdrant_config = VectorDatabaseConfig("qdrant")
    await manager.add_database("qdrant", qdrant_db, qdrant_config)
    
    # Add Weaviate
    weaviate_db = WeaviateVectorDB()
    weaviate_config = VectorDatabaseConfig("weaviate")
    await manager.add_database("weaviate", weaviate_db, weaviate_config)
    
    print(f"✅ Initialized {len(manager.databases)} vector databases")
    
    # Performance Benchmarking
    print("\n" + "="*60)
    print("Performance Benchmarking")
    print("="*60)
    
    benchmark = VectorDatabaseBenchmark(manager)
    
    # Run benchmarks
    benchmark_results = await benchmark.run_benchmark(
        databases=["pinecone", "qdrant", "weaviate"],
        index_name="benchmark_test",
        dimension=384,
        num_vectors=100,  # Reduced for demo
        num_queries=20    # Reduced for demo
    )
    
    print("\n📊 Benchmark Results:")
    for db_name, results in benchmark_results.items():
        if "error" not in results:
            print(f"\n{db_name.upper()}:")
            print(f"  • Upsert time: {results['upsert_time_ms']:.1f}ms")
            print(f"  • Search time: {results['search_time_ms']:.1f}ms")
            print(f"  • Upsert rate: {results['vectors_per_sec_upsert']:.1f} vectors/sec")
            print(f"  • Query rate: {results['queries_per_sec']:.1f} queries/sec")
        else:
            print(f"\n{db_name.upper()}: ERROR - {results['error']}")
    
    # Legal Document Search Demo
    print("\n" + "="*60)
    print("Legal Document Search System - Lawstronaut Scenario")
    print("="*60)
    
    # Setup legal system with Pinecone
    manager.set_active_database("pinecone")
    legal_system = LegalDocumentVectorSystem(manager)
    
    await legal_system.setup_legal_index()
    
    # Perform legal searches
    legal_queries = [
        ("GDPR compliance requirements", {"jurisdiction": "EU", "practice_area": "data_protection"}),
        ("Contract liability principles", {"jurisdiction": "UK", "practice_area": "contract_law"}),
        ("Intellectual property protection", {"document_type": "statute"})
    ]
    
    for query_desc, search_params in legal_queries:
        print(f"\n⚖️  Legal Query: {query_desc}")
        print(f"🔍 Filters: {search_params}")
        print("-" * 40)
        
        # Generate mock query vector
        query_vector = np.random.random(384).tolist()
        
        results = await legal_system.search_legal_documents(
            query_vector=query_vector,
            **search_params,
            k=3
        )
        
        for i, result in enumerate(results, 1):
            metadata = result.metadata
            print(f"{i}. {metadata.get('title', 'Unknown')}")
            print(f"   Jurisdiction: {metadata.get('jurisdiction', 'N/A')}")
            print(f"   Type: {metadata.get('document_type', 'N/A')}")
            print(f"   Relevance: {result.score:.3f}")
    
    # Content Personalization Demo
    print("\n" + "="*60)
    print("Content Personalization System - Optimizely Scenario")
    print("="*60)
    
    # Setup personalization system with Qdrant
    manager.set_active_database("qdrant")
    personalization_system = ContentPersonalizationVectorSystem(manager)
    
    await personalization_system.setup_personalization_indexes()
    
    # Perform personalized searches
    user_scenarios = [
        ("Senior Product Manager", {"role": "product_manager", "experience_level": "senior"}),
        ("Junior Data Analyst", {"role": "data_analyst", "experience_level": "junior"}),
        ("Unknown User", None)
    ]
    
    for user_desc, user_context in user_scenarios:
        print(f"\n👤 User Profile: {user_desc}")
        if user_context:
            print(f"📋 Context: {user_context}")
        print("-" * 40)
        
        results = await personalization_system.get_personalized_content(
            user_id=f"user_{user_desc.lower().replace(' ', '_')}",
            content_preferences=user_context,
            k=3
        )
        
        for i, result in enumerate(results, 1):
            metadata = result.metadata
            print(f"{i}. {metadata.get('title', 'Unknown')}")
            print(f"   Category: {metadata.get('category', 'N/A')}")
            print(f"   Difficulty: {metadata.get('difficulty', 'N/A')}")
            print(f"   Engagement: {metadata.get('engagement_score', 'N/A')}")
            print(f"   Personalization Score: {result.score:.3f}")
    
    # Multi-Database Statistics
    print("\n" + "="*60)
    print("Multi-Database Statistics")
    print("="*60)
    
    all_stats = await manager.get_all_stats()
    
    for db_name, stats in all_stats.items():
        print(f"\n📊 {db_name.upper()} Statistics:")
        if stats.get("status") == "connected":
            print(f"   • Status: ✅ Connected")
            print(f"   • Provider: {stats.get('provider', 'Unknown')}")
            print(f"   • Indexes: {len(stats.get('indexes', []))}")
        else:
            print(f"   • Status: ❌ {stats.get('error', 'Unknown error')}")
    
    # Cleanup
    print("\n" + "="*60)
    print("Cleanup")
    print("="*60)
    
    await manager.close_all()
    print("✅ All database connections closed")
    
    print("\n" + "="*60)
    print("✅ Vector Database Demo Complete")
    print("="*60)
    
    print(f"\n🎯 Key Achievements:")
    print(f"   • Implemented multi-provider vector database abstraction")
    print(f"   • Demonstrated Pinecone, Qdrant, and Weaviate integrations")
    print(f"   • Showcased performance benchmarking across providers")
    print(f"   • Built specialized legal document search system")
    print(f"   • Created content personalization with user profiling")
    print(f"   • Provided enterprise-grade error handling and monitoring")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run comprehensive vector database demonstration
    asyncio.run(demonstrate_vector_databases())
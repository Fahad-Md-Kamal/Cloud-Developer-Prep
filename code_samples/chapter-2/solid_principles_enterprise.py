"""
SOLID Principles in Enterprise Legal Document Processing System

This module demonstrates all five SOLID principles applied to a realistic
legal document processing system like those used at Lawstronaut.

Author: Technical Interview Preparation Guide
"""

from abc import ABC, abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json
import logging


# =============================================================================
# 1. SINGLE RESPONSIBILITY PRINCIPLE (SRP)
# Each class has one reason to change
# =============================================================================

@dataclass
class Document:
    """Represents a legal document with metadata"""
    id: str
    content: str
    title: str
    jurisdiction: str
    document_type: str
    source_url: str
    created_at: datetime


class DocumentParser:
    """Responsible ONLY for parsing document content"""
    
    def parse_pdf_content(self, pdf_data: bytes) -> str:
        """Extract text from PDF document"""
        # In real implementation, would use PyPDF2 or similar
        return f"Parsed PDF content: {len(pdf_data)} bytes"
    
    def parse_html_content(self, html_content: str) -> str:
        """Extract text from HTML document"""
        # In real implementation, would use BeautifulSoup
        return html_content.replace('<', '').replace('>', '')
    
    def extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract metadata from document content"""
        return {
            'title': content.split('\n')[0][:100] if content else 'Unknown',
            'word_count': str(len(content.split())),
            'language': 'en'  # Simplified
        }


class DocumentValidator:
    """Responsible ONLY for document validation"""
    
    def validate_structure(self, document: Document) -> bool:
        """Validate document has required structure"""
        if not document.content or len(document.content) < 10:
            return False
        if not document.title or len(document.title) < 3:
            return False
        return True
    
    def validate_legal_format(self, document: Document) -> bool:
        """Validate document follows legal formatting standards"""
        legal_indicators = ['section', 'article', 'whereas', 'hereby']
        content_lower = document.content.lower()
        return any(indicator in content_lower for indicator in legal_indicators)
    
    def get_validation_errors(self, document: Document) -> List[str]:
        """Get detailed validation errors"""
        errors = []
        if not self.validate_structure(document):
            errors.append("Document structure is invalid")
        if not self.validate_legal_format(document):
            errors.append("Document does not appear to be legal content")
        return errors


class DocumentStorage:
    """Responsible ONLY for document persistence"""
    
    def __init__(self):
        self._documents: Dict[str, Document] = {}
    
    async def save_document(self, document: Document) -> str:
        """Save document and return ID"""
        self._documents[document.id] = document
        logging.info(f"Document {document.id} saved successfully")
        return document.id
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve document by ID"""
        return self._documents.get(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document by ID"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False


# =============================================================================
# 2. OPEN/CLOSED PRINCIPLE (OCP)
# Open for extension, closed for modification
# =============================================================================

class CrawlerStrategy(ABC):
    """Abstract base for crawler strategies - open for extension"""
    
    @abstractmethod
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl content from URL"""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this strategy can handle the URL"""
        pass


class WebPageCrawler(CrawlerStrategy):
    """Strategy for crawling standard web pages"""
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl web page content"""
        # Simulate web crawling
        await asyncio.sleep(0.1)
        return {
            'url': url,
            'content': f'Web page content from {url}',
            'content_type': 'text/html'
        }
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is a standard web page"""
        return url.startswith('http') and not url.endswith('.pdf')


class PDFCrawler(CrawlerStrategy):
    """Strategy for crawling PDF documents"""
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl PDF document"""
        await asyncio.sleep(0.2)
        return {
            'url': url,
            'content': f'PDF content from {url}',
            'content_type': 'application/pdf'
        }
    
    def can_handle(self, url: str) -> bool:
        """Check if URL points to PDF"""
        return url.endswith('.pdf')


class APICrawler(CrawlerStrategy):
    """Strategy for crawling API endpoints - NEW EXTENSION"""
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl API endpoint"""
        await asyncio.sleep(0.05)
        return {
            'url': url,
            'content': f'API response from {url}',
            'content_type': 'application/json'
        }
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is API endpoint"""
        return '/api/' in url


class CrawlerContext:
    """Context that uses crawler strategies - closed for modification"""
    
    def __init__(self):
        self.strategies: List[CrawlerStrategy] = [
            WebPageCrawler(),
            PDFCrawler(),
            APICrawler()  # Can add new strategies without modifying this class
        ]
    
    async def crawl_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl URL using appropriate strategy"""
        for strategy in self.strategies:
            if strategy.can_handle(url):
                return await strategy.crawl(url)
        
        logging.warning(f"No strategy found for URL: {url}")
        return None


# =============================================================================
# 3. LISKOV SUBSTITUTION PRINCIPLE (LSP)
# Derived classes must be substitutable for base classes
# =============================================================================

class DocumentProcessor(ABC):
    """Base document processor - defines contract"""
    
    @abstractmethod
    async def process(self, content: str, metadata: Dict[str, str]) -> Document:
        """
        Process document content and return Document object.
        
        Contract:
        - Must return a valid Document object
        - Must not raise unexpected exceptions
        - Processing time should be reasonable (< 30 seconds)
        """
        pass
    
    def validate_preconditions(self, content: str) -> bool:
        """Validate input preconditions"""
        return content is not None and len(content.strip()) > 0


class LegalDocumentProcessor(DocumentProcessor):
    """Processes legal documents - maintains LSP contract"""
    
    async def process(self, content: str, metadata: Dict[str, str]) -> Document:
        """Process legal document - maintains base class contract"""
        if not self.validate_preconditions(content):
            raise ValueError("Invalid document content")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        return Document(
            id=f"legal_{hash(content) % 10000}",
            content=content,
            title=metadata.get('title', 'Legal Document'),
            jurisdiction=metadata.get('jurisdiction', 'Unknown'),
            document_type='legal',
            source_url=metadata.get('source_url', ''),
            created_at=datetime.now()
        )


class RegulationProcessor(DocumentProcessor):
    """Processes regulations - maintains LSP contract"""
    
    async def process(self, content: str, metadata: Dict[str, str]) -> Document:
        """Process regulation - maintains base class contract"""
        if not self.validate_preconditions(content):
            raise ValueError("Invalid document content")
        
        await asyncio.sleep(0.15)
        
        return Document(
            id=f"reg_{hash(content) % 10000}",
            content=content,
            title=metadata.get('title', 'Regulation Document'),
            jurisdiction=metadata.get('jurisdiction', 'Unknown'),
            document_type='regulation',
            source_url=metadata.get('source_url', ''),
            created_at=datetime.now()
        )


# Client code that depends on DocumentProcessor abstraction
class DocumentProcessingService:
    """Service that works with any DocumentProcessor implementation"""
    
    def __init__(self, processor: DocumentProcessor):
        self.processor = processor
    
    async def process_batch(self, documents: List[Dict[str, str]]) -> List[Document]:
        """Process multiple documents using the same processor"""
        results = []
        for doc_data in documents:
            try:
                # This works with ANY DocumentProcessor implementation
                # thanks to LSP compliance
                processed_doc = await self.processor.process(
                    doc_data['content'], 
                    doc_data.get('metadata', {})
                )
                results.append(processed_doc)
            except Exception as e:
                logging.error(f"Processing failed: {e}")
        
        return results


# =============================================================================
# 4. INTERFACE SEGREGATION PRINCIPLE (ISP)
# Clients should not depend on interfaces they don't use
# =============================================================================

class Readable(Protocol):
    """Interface for reading operations only"""
    async def read(self, doc_id: str) -> Optional[Document]: ...


class Writable(Protocol):
    """Interface for writing operations only"""
    async def write(self, document: Document) -> str: ...


class Searchable(Protocol):
    """Interface for search operations only"""
    async def search(self, query: str) -> List[Document]: ...


class Deletable(Protocol):
    """Interface for deletion operations only"""
    async def delete(self, doc_id: str) -> bool: ...


# Clients depend only on interfaces they need

class DocumentReader:
    """Client that only needs read access"""
    
    def __init__(self, storage: Readable):
        self.storage = storage  # Only depends on Readable
    
    async def get_document_summary(self, doc_id: str) -> Optional[str]:
        """Get document summary"""
        doc = await self.storage.read(doc_id)
        if doc:
            return f"{doc.title} ({doc.jurisdiction})"
        return None


class DocumentIndexer:
    """Client that only needs write access"""
    
    def __init__(self, storage: Writable):
        self.storage = storage  # Only depends on Writable
    
    async def index_document(self, content: str, metadata: Dict[str, str]) -> str:
        """Index a new document"""
        doc = Document(
            id=f"idx_{hash(content) % 10000}",
            content=content,
            title=metadata.get('title', 'Unknown'),
            jurisdiction=metadata.get('jurisdiction', 'Unknown'),
            document_type=metadata.get('type', 'unknown'),
            source_url=metadata.get('url', ''),
            created_at=datetime.now()
        )
        return await self.storage.write(doc)


class DocumentSearchEngine:
    """Client that only needs search access"""
    
    def __init__(self, storage: Searchable):
        self.storage = storage  # Only depends on Searchable
    
    async def find_similar_documents(self, query: str) -> List[str]:
        """Find documents similar to query"""
        docs = await self.storage.search(query)
        return [doc.title for doc in docs[:5]]


# =============================================================================
# 5. DEPENDENCY INVERSION PRINCIPLE (DIP)
# Depend on abstractions, not concretions
# =============================================================================

class DocumentRepository(Protocol):
    """High-level abstraction for document storage"""
    async def save(self, document: Document) -> str: ...
    async def find_by_id(self, doc_id: str) -> Optional[Document]: ...
    async def search(self, query: str) -> List[Document]: ...
    async def delete(self, doc_id: str) -> bool: ...


class PostgreSQLDocumentRepository:
    """Low-level implementation for PostgreSQL"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._documents: Dict[str, Document] = {}  # Simulate database
    
    async def save(self, document: Document) -> str:
        """Save to PostgreSQL"""
        self._documents[document.id] = document
        logging.info(f"Saved document {document.id} to PostgreSQL")
        return document.id
    
    async def find_by_id(self, doc_id: str) -> Optional[Document]:
        """Find in PostgreSQL"""
        return self._documents.get(doc_id)
    
    async def search(self, query: str) -> List[Document]:
        """Search in PostgreSQL"""
        results = []
        for doc in self._documents.values():
            if query.lower() in doc.content.lower() or query.lower() in doc.title.lower():
                results.append(doc)
        return results
    
    async def delete(self, doc_id: str) -> bool:
        """Delete from PostgreSQL"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False


class ElasticsearchDocumentRepository:
    """Low-level implementation for Elasticsearch"""
    
    def __init__(self, host: str, index: str):
        self.host = host
        self.index = index
        self._documents: Dict[str, Document] = {}  # Simulate Elasticsearch
    
    async def save(self, document: Document) -> str:
        """Save to Elasticsearch"""
        self._documents[document.id] = document
        logging.info(f"Indexed document {document.id} in Elasticsearch")
        return document.id
    
    async def find_by_id(self, doc_id: str) -> Optional[Document]:
        """Find in Elasticsearch"""
        return self._documents.get(doc_id)
    
    async def search(self, query: str) -> List[Document]:
        """Full-text search in Elasticsearch"""
        # Simulate better search capabilities
        results = []
        for doc in self._documents.values():
            # Elasticsearch would provide more sophisticated matching
            if query.lower() in doc.content.lower():
                results.append(doc)
        return results
    
    async def delete(self, doc_id: str) -> bool:
        """Delete from Elasticsearch"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False


# High-level module depends on abstraction
class LegalDocumentService:
    """High-level service that depends on abstraction, not implementation"""
    
    def __init__(self, repository: DocumentRepository):
        # Depends on abstraction (DocumentRepository)
        # Not on concrete implementation (PostgreSQLDocumentRepository)
        self.repository = repository
        self.parser = DocumentParser()
        self.validator = DocumentValidator()
    
    async def process_and_store_document(
        self, 
        content: str, 
        metadata: Dict[str, str]
    ) -> str:
        """Process and store document using injected repository"""
        
        # Parse content
        parsed_content = self.parser.parse_html_content(content)
        extracted_metadata = self.parser.extract_metadata(parsed_content)
        
        # Create document
        document = Document(
            id=f"doc_{hash(content) % 10000}",
            content=parsed_content,
            title=extracted_metadata['title'],
            jurisdiction=metadata.get('jurisdiction', 'Unknown'),
            document_type=metadata.get('type', 'legal'),
            source_url=metadata.get('url', ''),
            created_at=datetime.now()
        )
        
        # Validate
        if not self.validator.validate_structure(document):
            raise ValueError("Document validation failed")
        
        # Store using injected repository
        return await self.repository.save(document)
    
    async def search_documents(self, query: str) -> List[str]:
        """Search documents using injected repository"""
        documents = await self.repository.search(query)
        return [f"{doc.title} ({doc.jurisdiction})" for doc in documents]


# Dependency injection configuration
class ServiceConfiguration:
    """Configure services with appropriate implementations"""
    
    @staticmethod
    def create_production_service() -> LegalDocumentService:
        """Create service with PostgreSQL for production"""
        repository = PostgreSQLDocumentRepository("postgresql://prod-db:5432/legal")
        return LegalDocumentService(repository)
    
    @staticmethod
    def create_search_optimized_service() -> LegalDocumentService:
        """Create service with Elasticsearch for search-heavy workloads"""
        repository = ElasticsearchDocumentRepository("elasticsearch:9200", "legal_docs")
        return LegalDocumentService(repository)
    
    @staticmethod
    def create_test_service() -> LegalDocumentService:
        """Create service with in-memory repository for testing"""
        # Could create MockDocumentRepository for testing
        repository = PostgreSQLDocumentRepository(":memory:")
        return LegalDocumentService(repository)


# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

async def demonstrate_solid_principles():
    """Demonstrate all SOLID principles working together"""
    
    print("=== SOLID Principles Demonstration ===\n")
    
    # 1. SRP: Each class has single responsibility
    print("1. Single Responsibility Principle:")
    parser = DocumentParser()
    validator = DocumentValidator()
    storage = DocumentStorage()
    
    content = "Article 1: This is a legal document with proper structure."
    metadata = parser.extract_metadata(content)
    print(f"   Parser extracted metadata: {metadata}")
    
    doc = Document(
        id="demo_001",
        content=content,
        title="Demo Legal Document",
        jurisdiction="US",
        document_type="statute",
        source_url="https://example.com/law1",
        created_at=datetime.now()
    )
    
    is_valid = validator.validate_structure(doc)
    print(f"   Validator result: {is_valid}")
    
    doc_id = await storage.save_document(doc)
    print(f"   Storage saved document: {doc_id}\n")
    
    # 2. OCP: Adding new crawler without modifying existing code
    print("2. Open/Closed Principle:")
    crawler = CrawlerContext()
    
    urls = [
        "https://legislation.gov.uk/act.html",
        "https://example.com/law.pdf",
        "https://api.legal.com/api/v1/statute/123"
    ]
    
    for url in urls:
        result = await crawler.crawl_url(url)
        if result:
            print(f"   Crawled {url}: {result['content_type']}")
    print()
    
    # 3. LSP: Different processors are substitutable
    print("3. Liskov Substitution Principle:")
    
    processors = [
        ("Legal", LegalDocumentProcessor()),
        ("Regulation", RegulationProcessor())
    ]
    
    test_data = [
        {
            'content': 'Legal document content with proper structure',
            'metadata': {'title': 'Test Legal Doc', 'jurisdiction': 'US'}
        }
    ]
    
    for name, processor in processors:
        service = DocumentProcessingService(processor)
        results = await service.process_batch(test_data)
        print(f"   {name} processor handled: {len(results)} documents")
    print()
    
    # 4. ISP: Clients use only needed interfaces
    print("4. Interface Segregation Principle:")
    
    # Create repository that implements all interfaces
    full_repo = PostgreSQLDocumentRepository("test://db")
    await full_repo.save(doc)
    
    # Different clients use only what they need
    reader = DocumentReader(full_repo)  # Only needs Readable
    indexer = DocumentIndexer(full_repo)  # Only needs Writable
    searcher = DocumentSearchEngine(full_repo)  # Only needs Searchable
    
    summary = await reader.get_document_summary("demo_001")
    print(f"   Reader got summary: {summary}")
    
    new_doc_id = await indexer.index_document("New indexed content", 
                                             {"title": "Indexed Doc"})
    print(f"   Indexer created: {new_doc_id}")
    
    search_results = await searcher.find_similar_documents("legal")
    print(f"   Searcher found {len(search_results)} results")
    print()
    
    # 5. DIP: High-level service works with different implementations
    print("5. Dependency Inversion Principle:")
    
    # Same service works with different repository implementations
    implementations = [
        ("PostgreSQL", PostgreSQLDocumentRepository("postgresql://localhost/legal")),
        ("Elasticsearch", ElasticsearchDocumentRepository("localhost:9200", "legal"))
    ]
    
    for name, repo in implementations:
        service = LegalDocumentService(repo)
        doc_id = await service.process_and_store_document(
            "Sample legal content for testing DIP",
            {"jurisdiction": "US", "type": "statute", "url": "https://example.com"}
        )
        print(f"   Service with {name} created document: {doc_id}")
    
    print("\n=== All SOLID Principles Successfully Demonstrated ===")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run demonstration
    asyncio.run(demonstrate_solid_principles())

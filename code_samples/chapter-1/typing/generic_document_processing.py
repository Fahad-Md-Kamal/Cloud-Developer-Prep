from typing import TypeVar, Generic, List, Dict, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio

# Generic type variables
T = TypeVar('T')
DocType = TypeVar('DocType', bound='BaseDocument')

# Protocol for document processing
class DocumentProcessor(Protocol[T]):
    async def process(self, document: T) -> Dict[str, any]:
        ...
    
    def validate(self, document: T) -> bool:
        ...

# Base document with generic content type
@dataclass
class BaseDocument(Generic[T]):
    id: str
    content: T
    metadata: Dict[str, str]
    source_url: str
    
    def extract_text(self) -> str:
        """Extract text content regardless of document type"""
        if isinstance(self.content, str):
            return self.content
        elif hasattr(self.content, 'text'):
            return self.content.text
        return str(self.content)

# Specific document types
@dataclass
class LegalText:
    text: str
    jurisdiction: str
    law_type: str

@dataclass
class StructuredLaw:
    sections: List[Dict[str, str]]
    references: List[str]
    effective_date: str

# Typed document classes
class LegalDocument(BaseDocument[LegalText]):
    pass

class StructuredDocument(BaseDocument[StructuredLaw]):
    pass

# Generic repository pattern
class DocumentRepository(Generic[DocType]):
    def __init__(self):
        self._documents: Dict[str, DocType] = {}
    
    async def save(self, document: DocType) -> None:
        self._documents[document.id] = document
    
    async def find_by_id(self, doc_id: str) -> Optional[DocType]:
        return self._documents.get(doc_id)
    
    async def find_by_jurisdiction(self, jurisdiction: str) -> List[DocType]:
        results = []
        for doc in self._documents.values():
            if hasattr(doc.content, 'jurisdiction'):
                if doc.content.jurisdiction == jurisdiction:
                    results.append(doc)
        return results

# Usage with full type safety
async def process_legal_documents():
    # Repository is typed to specific document type
    legal_repo: DocumentRepository[LegalDocument] = DocumentRepository()
    
    # Create typed documents
    legal_doc = LegalDocument(
        id="law_001",
        content=LegalText(
            text="Article 1: Rights and obligations...",
            jurisdiction="US",
            law_type="constitutional"
        ),
        metadata={"source": "congress", "year": "2023"},
        source_url="https://example.com/law_001"
    )
    
    await legal_repo.save(legal_doc)
    
    # Type checker ensures correct return type
    found_doc: Optional[LegalDocument] = await legal_repo.find_by_id("law_001")
    
    if found_doc:
        print(f"Document content: {found_doc.extract_text()}")

if __name__ == "__main__":
    asyncio.run(process_legal_documents())

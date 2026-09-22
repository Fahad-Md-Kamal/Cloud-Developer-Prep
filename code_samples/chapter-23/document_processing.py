"""
Document Processing and Chunking Strategies

This module demonstrates comprehensive document processing pipelines
with intelligent chunking strategies for RAG systems.

Key concepts covered:
- Multi-format document parsing (PDF, DOC, HTML, Markdown)
- Semantic chunking strategies
- Overlap optimization and boundary detection
- Metadata extraction and enrichment
- Preprocessing pipelines for different content types

Real-world applications:
- Legal document processing for Lawstronaut
- Content ingestion for Optimizely personalization

Author: Technical Interview Preparation Guide
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Iterator, Generator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
import re
import json
import logging
import hashlib
import asyncio
from datetime import datetime
from enum import Enum
import mimetypes

# Mock external dependencies (replace with actual libraries in production)
class MockPyPDF2:
    class PdfReader:
        def __init__(self, file_path: str):
            self.pages = [
                MockPage(f"Content from page {i+1} of PDF document. This is sample text content.") 
                for i in range(3)
            ]
        
        def __len__(self):
            return len(self.pages)

class MockPage:
    def __init__(self, text: str):
        self.text = text
    
    def extract_text(self):
        return self.text

class MockDocx:
    class Document:
        def __init__(self, file_path: str):
            self.paragraphs = [
                MockParagraph("Sample paragraph 1 from DOCX document."),
                MockParagraph("Sample paragraph 2 with more content."),
                MockParagraph("Sample paragraph 3 for demonstration.")
            ]

class MockParagraph:
    def __init__(self, text: str):
        self.text = text

class MockBeautifulSoup:
    def __init__(self, content: str, parser: str):
        self.text = "Sample HTML content extracted from the document."
    
    def get_text(self, separator: str = " "):
        return self.text

# =============================================================================
# CORE DATA MODELS
# =============================================================================

class DocumentFormat(Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "markdown"
    TXT = "txt"
    JSON = "json"

class ChunkingStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SLIDING_WINDOW = "sliding_window"
    RECURSIVE = "recursive"

@dataclass
class DocumentChunk:
    """Represents a processed document chunk"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    chunk_index: int = 0
    source_document_id: str = ""
    
    def __post_init__(self):
        if not self.id:
            # Generate ID based on content hash
            content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
            self.id = f"{self.source_document_id}_{self.chunk_index}_{content_hash}"
    
    @property
    def word_count(self) -> int:
        """Get word count of the chunk"""
        return len(self.content.split())
    
    @property
    def char_count(self) -> int:
        """Get character count of the chunk"""
        return len(self.content)

@dataclass
class ProcessedDocument:
    """Represents a fully processed document"""
    id: str
    original_path: str
    format: DocumentFormat
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(str(self.original_path).encode()).hexdigest()[:12]
    
    @property
    def total_chunks(self) -> int:
        """Get total number of chunks"""
        return len(self.chunks)
    
    @property
    def total_words(self) -> int:
        """Get total word count across all chunks"""
        return sum(chunk.word_count for chunk in self.chunks)

# =============================================================================
# DOCUMENT PARSERS
# =============================================================================

class DocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    @abstractmethod
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse document and return content with metadata"""
        pass
    
    @abstractmethod
    def supports_format(self, file_format: DocumentFormat) -> bool:
        """Check if parser supports the given format"""
        pass

class PDFParser(DocumentParser):
    """PDF document parser"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse PDF document"""
        try:
            # In real implementation: use PyPDF2, pdfplumber, or pymupdf
            reader = MockPyPDF2.PdfReader(file_path)
            
            text_content = []
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text_content.append(page_text)
            
            full_text = "\n\n".join(text_content)
            
            metadata = {
                "format": "pdf",
                "pages": len(reader.pages),
                "parsed_at": datetime.now().isoformat(),
                "parser": "pdf_parser",
                "file_size": len(full_text),  # Mock file size
                "extraction_method": "text_layer"
            }
            
            self.logger.info(f"Parsed PDF: {file_path} ({len(reader.pages)} pages)")
            return full_text, metadata
        
        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {e}")
            raise
    
    def supports_format(self, file_format: DocumentFormat) -> bool:
        return file_format == DocumentFormat.PDF

class DOCXParser(DocumentParser):
    """DOCX document parser"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse DOCX document"""
        try:
            # In real implementation: use python-docx
            doc = MockDocx.Document(file_path)
            
            text_content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())
            
            full_text = "\n\n".join(text_content)
            
            metadata = {
                "format": "docx",
                "paragraphs": len(text_content),
                "parsed_at": datetime.now().isoformat(),
                "parser": "docx_parser",
                "file_size": len(full_text)
            }
            
            self.logger.info(f"Parsed DOCX: {file_path} ({len(text_content)} paragraphs)")
            return full_text, metadata
        
        except Exception as e:
            self.logger.error(f"Error parsing DOCX {file_path}: {e}")
            raise
    
    def supports_format(self, file_format: DocumentFormat) -> bool:
        return file_format == DocumentFormat.DOCX

class HTMLParser(DocumentParser):
    """HTML document parser"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse HTML document"""
        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            # In real implementation: use BeautifulSoup
            soup = MockBeautifulSoup(html_content, 'html.parser')
            
            # Extract text content
            text_content = soup.get_text(separator=' ')
            
            # Clean up whitespace
            cleaned_text = re.sub(r'\s+', ' ', text_content).strip()
            
            metadata = {
                "format": "html",
                "parsed_at": datetime.now().isoformat(),
                "parser": "html_parser",
                "file_size": len(cleaned_text),
                "original_html_size": len(html_content)
            }
            
            self.logger.info(f"Parsed HTML: {file_path}")
            return cleaned_text, metadata
        
        except Exception as e:
            self.logger.error(f"Error parsing HTML {file_path}: {e}")
            raise
    
    def supports_format(self, file_format: DocumentFormat) -> bool:
        return file_format == DocumentFormat.HTML

class MarkdownParser(DocumentParser):
    """Markdown document parser"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse Markdown document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                markdown_content = file.read()
            
            # Extract headers for structure
            headers = re.findall(r'^#{1,6}\s+(.+)$', markdown_content, re.MULTILINE)
            
            # Remove markdown syntax for plain text
            # In real implementation: use markdown library
            text_content = self._clean_markdown(markdown_content)
            
            metadata = {
                "format": "markdown",
                "headers": headers,
                "header_count": len(headers),
                "parsed_at": datetime.now().isoformat(),
                "parser": "markdown_parser",
                "file_size": len(text_content)
            }
            
            self.logger.info(f"Parsed Markdown: {file_path} ({len(headers)} headers)")
            return text_content, metadata
        
        except Exception as e:
            self.logger.error(f"Error parsing Markdown {file_path}: {e}")
            raise
    
    def _clean_markdown(self, content: str) -> str:
        """Clean markdown syntax to get plain text"""
        # Remove headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic
        content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
        content = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', content)
        
        # Remove links
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def supports_format(self, file_format: DocumentFormat) -> bool:
        return file_format == DocumentFormat.MARKDOWN

class TextParser(DocumentParser):
    """Plain text document parser"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def parse(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Parse text document"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
            
            # Count lines and paragraphs
            lines = text_content.count('\n') + 1
            paragraphs = len([p for p in text_content.split('\n\n') if p.strip()])
            
            metadata = {
                "format": "txt",
                "lines": lines,
                "paragraphs": paragraphs,
                "parsed_at": datetime.now().isoformat(),
                "parser": "text_parser",
                "file_size": len(text_content)
            }
            
            self.logger.info(f"Parsed text: {file_path} ({lines} lines)")
            return text_content, metadata
        
        except Exception as e:
            self.logger.error(f"Error parsing text {file_path}: {e}")
            raise
    
    def supports_format(self, file_format: DocumentFormat) -> bool:
        return file_format == DocumentFormat.TXT

# =============================================================================
# CHUNKING STRATEGIES
# =============================================================================

class ChunkingEngine(ABC):
    """Abstract base class for chunking strategies"""
    
    @abstractmethod
    async def chunk_document(self, content: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Chunk document content into smaller pieces"""
        pass

class FixedSizeChunker(ChunkingEngine):
    """Fixed-size chunking with overlap"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.logger = logging.getLogger(__name__)
    
    async def chunk_document(self, content: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Create fixed-size chunks with overlap"""
        chunks = []
        
        # Handle empty content
        if not content.strip():
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            # Calculate end position
            end = min(start + self.chunk_size, len(content))
            
            # Adjust to word boundaries to avoid splitting words
            if end < len(content):
                # Find the last space before the end position
                while end > start and content[end] not in [' ', '\n', '\t']:
                    end -= 1
                
                # If no space found, use original end position
                if end == start:
                    end = min(start + self.chunk_size, len(content))
            
            # Extract chunk content
            chunk_content = content[start:end].strip()
            
            if chunk_content:
                chunk = DocumentChunk(
                    id="",  # Will be generated in __post_init__
                    content=chunk_content,
                    metadata=metadata.copy() if metadata else {},
                    start_char=start,
                    end_char=end,
                    chunk_index=chunk_index,
                    source_document_id=metadata.get("document_id", "") if metadata else ""
                )
                
                # Add chunk-specific metadata
                chunk.metadata.update({
                    "chunking_strategy": "fixed_size",
                    "chunk_size": self.chunk_size,
                    "overlap": self.overlap,
                    "word_count": chunk.word_count,
                    "char_count": chunk.char_count
                })
                
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            start = max(end - self.overlap, start + 1)
            
            # Prevent infinite loop
            if end >= len(content):
                break
        
        self.logger.info(f"Fixed-size chunking created {len(chunks)} chunks")
        return chunks

class SemanticChunker(ChunkingEngine):
    """Semantic chunking based on content meaning"""
    
    def __init__(self, max_chunk_size: int = 1500, min_chunk_size: int = 300):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.logger = logging.getLogger(__name__)
    
    async def chunk_document(self, content: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Create semantic chunks based on content structure"""
        chunks = []
        
        # Split into paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = ""
        chunk_index = 0
        start_char = 0
        
        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed max size
            potential_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph
            
            if len(potential_chunk) <= self.max_chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunk = self._create_semantic_chunk(
                        current_chunk, chunk_index, start_char, metadata
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    start_char += len(current_chunk) + 2  # +2 for \n\n
                
                # Start new chunk with current paragraph
                current_chunk = paragraph
        
        # Add final chunk if it exists
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = self._create_semantic_chunk(
                current_chunk, chunk_index, start_char, metadata
            )
            chunks.append(chunk)
        elif current_chunk and chunks:
            # Merge small final chunk with last chunk
            chunks[-1].content += "\n\n" + current_chunk
            chunks[-1].metadata["word_count"] = chunks[-1].word_count
            chunks[-1].metadata["char_count"] = chunks[-1].char_count
        
        self.logger.info(f"Semantic chunking created {len(chunks)} chunks")
        return chunks
    
    def _create_semantic_chunk(self, content: str, chunk_index: int, start_char: int, metadata: Dict[str, Any] = None) -> DocumentChunk:
        """Create a semantic chunk with metadata"""
        chunk = DocumentChunk(
            id="",
            content=content,
            metadata=metadata.copy() if metadata else {},
            start_char=start_char,
            end_char=start_char + len(content),
            chunk_index=chunk_index,
            source_document_id=metadata.get("document_id", "") if metadata else ""
        )
        
        # Add semantic analysis metadata
        chunk.metadata.update({
            "chunking_strategy": "semantic",
            "paragraph_count": content.count('\n\n') + 1,
            "word_count": chunk.word_count,
            "char_count": chunk.char_count,
            "semantic_coherence": self._calculate_coherence_score(content)
        })
        
        return chunk
    
    def _calculate_coherence_score(self, content: str) -> float:
        """Calculate a simple coherence score for the chunk"""
        # Simple heuristic: ratio of sentences to total length
        sentence_count = len(re.findall(r'[.!?]+', content))
        word_count = len(content.split())
        
        if word_count == 0:
            return 0.0
        
        # Normalize score between 0 and 1
        coherence = min(1.0, sentence_count / (word_count / 20))  # ~20 words per sentence is good
        return round(coherence, 3)

class SentenceChunker(ChunkingEngine):
    """Sentence-based chunking"""
    
    def __init__(self, sentences_per_chunk: int = 5, overlap_sentences: int = 1):
        self.sentences_per_chunk = sentences_per_chunk
        self.overlap_sentences = overlap_sentences
        self.logger = logging.getLogger(__name__)
    
    async def chunk_document(self, content: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Create chunks based on sentence boundaries"""
        chunks = []
        
        # Split into sentences
        sentences = self._split_sentences(content)
        
        if not sentences:
            return chunks
        
        chunk_index = 0
        start_idx = 0
        
        while start_idx < len(sentences):
            end_idx = min(start_idx + self.sentences_per_chunk, len(sentences))
            
            # Get sentences for this chunk
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_content = ' '.join(chunk_sentences)
            
            # Calculate character positions (approximate)
            start_char = sum(len(s) + 1 for s in sentences[:start_idx])  # +1 for space
            end_char = start_char + len(chunk_content)
            
            chunk = DocumentChunk(
                id="",
                content=chunk_content,
                metadata=metadata.copy() if metadata else {},
                start_char=start_char,
                end_char=end_char,
                chunk_index=chunk_index,
                source_document_id=metadata.get("document_id", "") if metadata else ""
            )
            
            chunk.metadata.update({
                "chunking_strategy": "sentence",
                "sentence_count": len(chunk_sentences),
                "sentences_per_chunk": self.sentences_per_chunk,
                "overlap_sentences": self.overlap_sentences,
                "word_count": chunk.word_count,
                "char_count": chunk.char_count
            })
            
            chunks.append(chunk)
            chunk_index += 1
            
            # Move start position with overlap
            start_idx = max(end_idx - self.overlap_sentences, start_idx + 1)
            
            if end_idx >= len(sentences):
                break
        
        self.logger.info(f"Sentence chunking created {len(chunks)} chunks")
        return chunks
    
    def _split_sentences(self, content: str) -> List[str]:
        """Split content into sentences"""
        # Simple sentence splitting (in production, use NLTK or spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Filter very short sentences
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences

class RecursiveChunker(ChunkingEngine):
    """Recursive chunking with hierarchical structure preservation"""
    
    def __init__(self, chunk_size: int = 1000, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.separators = separators or ["\n\n", "\n", " ", ""]
        self.logger = logging.getLogger(__name__)
    
    async def chunk_document(self, content: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Create chunks using recursive splitting"""
        chunks = []
        
        if not content.strip():
            return chunks
        
        # Start recursive chunking
        initial_chunks = self._recursive_split(content, 0)
        
        # Convert to DocumentChunk objects
        for i, chunk_content in enumerate(initial_chunks):
            chunk = DocumentChunk(
                id="",
                content=chunk_content,
                metadata=metadata.copy() if metadata else {},
                chunk_index=i,
                source_document_id=metadata.get("document_id", "") if metadata else ""
            )
            
            chunk.metadata.update({
                "chunking_strategy": "recursive",
                "chunk_size": self.chunk_size,
                "separators_used": self.separators,
                "word_count": chunk.word_count,
                "char_count": chunk.char_count
            })
            
            chunks.append(chunk)
        
        self.logger.info(f"Recursive chunking created {len(chunks)} chunks")
        return chunks
    
    def _recursive_split(self, text: str, separator_index: int) -> List[str]:
        """Recursively split text using hierarchical separators"""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        if separator_index >= len(self.separators):
            # No more separators, force split
            return [text[:self.chunk_size], text[self.chunk_size:]]
        
        separator = self.separators[separator_index]
        
        if separator == "":
            # Character-level split (last resort)
            chunks = []
            for i in range(0, len(text), self.chunk_size):
                chunks.append(text[i:i + self.chunk_size])
            return chunks
        
        # Split by current separator
        parts = text.split(separator)
        
        if len(parts) == 1:
            # Separator not found, try next separator
            return self._recursive_split(text, separator_index + 1)
        
        # Recombine parts to form chunks of appropriate size
        chunks = []
        current_chunk = ""
        
        for part in parts:
            potential_chunk = current_chunk + (separator if current_chunk else "") + part
            
            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If single part is too large, recursively split it
                if len(part) > self.chunk_size:
                    chunks.extend(self._recursive_split(part, separator_index + 1))
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

# =============================================================================
# DOCUMENT PROCESSING PIPELINE
# =============================================================================

class DocumentProcessor:
    """Main document processing pipeline"""
    
    def __init__(self):
        # Initialize parsers
        self.parsers = {
            DocumentFormat.PDF: PDFParser(),
            DocumentFormat.DOCX: DOCXParser(),
            DocumentFormat.HTML: HTMLParser(),
            DocumentFormat.MARKDOWN: MarkdownParser(),
            DocumentFormat.TXT: TextParser()
        }
        
        # Initialize chunkers
        self.chunkers = {
            ChunkingStrategy.FIXED_SIZE: FixedSizeChunker(),
            ChunkingStrategy.SEMANTIC: SemanticChunker(),
            ChunkingStrategy.SENTENCE: SentenceChunker(),
            ChunkingStrategy.RECURSIVE: RecursiveChunker()
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def process_document(self, 
                              file_path: str,
                              chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
                              **chunker_params) -> ProcessedDocument:
        """Process a single document through the complete pipeline"""
        
        start_time = datetime.now()
        
        try:
            # Detect document format
            doc_format = self._detect_format(file_path)
            
            # Parse document
            content, parse_metadata = await self._parse_document(file_path, doc_format)
            
            # Preprocess content
            preprocessed_content = self._preprocess_content(content, doc_format)
            
            # Create chunker with custom parameters
            chunker = self._create_chunker(chunking_strategy, **chunker_params)
            
            # Add document ID to metadata
            doc_id = hashlib.md5(str(file_path).encode()).hexdigest()[:12]
            parse_metadata["document_id"] = doc_id
            
            # Chunk document
            chunks = await chunker.chunk_document(preprocessed_content, parse_metadata)
            
            # Create processed document
            processed_doc = ProcessedDocument(
                id=doc_id,
                original_path=str(file_path),
                format=doc_format,
                chunks=chunks,
                metadata=parse_metadata,
                processing_stats={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "original_size": len(content),
                    "preprocessed_size": len(preprocessed_content),
                    "chunking_strategy": chunking_strategy.value,
                    "total_chunks": len(chunks),
                    "avg_chunk_size": sum(chunk.char_count for chunk in chunks) / len(chunks) if chunks else 0
                }
            )
            
            self.logger.info(f"Processed document {file_path}: {len(chunks)} chunks created")
            return processed_doc
        
        except Exception as e:
            self.logger.error(f"Error processing document {file_path}: {e}")
            raise
    
    async def process_batch(self, 
                           file_paths: List[str],
                           chunking_strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
                           max_concurrent: int = 5,
                           **chunker_params) -> List[ProcessedDocument]:
        """Process multiple documents concurrently"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(file_path: str) -> ProcessedDocument:
            async with semaphore:
                return await self.process_document(file_path, chunking_strategy, **chunker_params)
        
        # Process all documents concurrently
        tasks = [process_single(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        processed_docs = []
        for result in results:
            if isinstance(result, ProcessedDocument):
                processed_docs.append(result)
            else:
                self.logger.error(f"Processing failed: {result}")
        
        self.logger.info(f"Batch processing complete: {len(processed_docs)}/{len(file_paths)} successful")
        return processed_docs
    
    def _detect_format(self, file_path: str) -> DocumentFormat:
        """Detect document format from file extension"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        format_mapping = {
            '.pdf': DocumentFormat.PDF,
            '.docx': DocumentFormat.DOCX,
            '.doc': DocumentFormat.DOCX,  # Treat as DOCX for simplicity
            '.html': DocumentFormat.HTML,
            '.htm': DocumentFormat.HTML,
            '.md': DocumentFormat.MARKDOWN,
            '.markdown': DocumentFormat.MARKDOWN,
            '.txt': DocumentFormat.TXT
        }
        
        return format_mapping.get(extension, DocumentFormat.TXT)
    
    async def _parse_document(self, file_path: str, doc_format: DocumentFormat) -> Tuple[str, Dict[str, Any]]:
        """Parse document using appropriate parser"""
        parser = self.parsers.get(doc_format)
        
        if not parser:
            raise ValueError(f"No parser available for format: {doc_format}")
        
        return await parser.parse(file_path)
    
    def _preprocess_content(self, content: str, doc_format: DocumentFormat) -> str:
        """Preprocess content for better chunking"""
        
        # Basic cleanup
        content = content.strip()
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Restore paragraph breaks for better semantic chunking
        content = re.sub(r'\. ([A-Z])', r'.\n\n\1', content)
        
        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Format-specific preprocessing
        if doc_format == DocumentFormat.PDF:
            # Handle PDF-specific issues like line breaks in middle of sentences
            content = re.sub(r'(\w)-\n(\w)', r'\1\2', content)  # Join hyphenated words
        
        elif doc_format == DocumentFormat.HTML:
            # Additional HTML cleanup might be needed
            content = re.sub(r'<[^>]+>', '', content)  # Remove any remaining HTML tags
        
        return content
    
    def _create_chunker(self, strategy: ChunkingStrategy, **params) -> ChunkingEngine:
        """Create chunker with custom parameters"""
        
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return FixedSizeChunker(
                chunk_size=params.get('chunk_size', 1000),
                overlap=params.get('overlap', 200)
            )
        
        elif strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(
                max_chunk_size=params.get('max_chunk_size', 1500),
                min_chunk_size=params.get('min_chunk_size', 300)
            )
        
        elif strategy == ChunkingStrategy.SENTENCE:
            return SentenceChunker(
                sentences_per_chunk=params.get('sentences_per_chunk', 5),
                overlap_sentences=params.get('overlap_sentences', 1)
            )
        
        elif strategy == ChunkingStrategy.RECURSIVE:
            return RecursiveChunker(
                chunk_size=params.get('chunk_size', 1000),
                separators=params.get('separators', ["\n\n", "\n", " ", ""])
            )
        
        else:
            return self.chunkers[strategy]

# =============================================================================
# ENTERPRISE SCENARIOS
# =============================================================================

class LegalDocumentProcessor:
    """Specialized processor for legal documents - Lawstronaut scenario"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.logger = logging.getLogger(__name__)
    
    async def process_legal_document(self, file_path: str) -> ProcessedDocument:
        """Process legal document with specialized settings"""
        
        # Use semantic chunking with legal-optimized parameters
        processed_doc = await self.processor.process_document(
            file_path=file_path,
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            max_chunk_size=2000,  # Larger chunks for legal context
            min_chunk_size=500    # Ensure meaningful legal content
        )
        
        # Add legal-specific metadata to chunks
        for chunk in processed_doc.chunks:
            chunk.metadata.update({
                "document_domain": "legal",
                "requires_legal_review": True,
                "citation_extractable": self._has_legal_citations(chunk.content),
                "legal_confidence": self._calculate_legal_confidence(chunk.content)
            })
        
        return processed_doc
    
    def _has_legal_citations(self, content: str) -> bool:
        """Check if content contains legal citations"""
        citation_patterns = [
            r'\d+\s+U\.S\.C\.\s+§\s+\d+',  # US Code
            r'\d+\s+F\.\s*\d+d?\s+\d+',    # Federal Reporter
            r'Art\.?\s+\d+',               # Article references
            r'§\s*\d+',                    # Section references
        ]
        
        for pattern in citation_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_legal_confidence(self, content: str) -> float:
        """Calculate confidence score for legal content"""
        legal_terms = [
            'pursuant', 'whereas', 'notwithstanding', 'heretofore',
            'liability', 'contract', 'agreement', 'statute',
            'regulation', 'compliance', 'jurisdiction'
        ]
        
        term_count = sum(1 for term in legal_terms if term.lower() in content.lower())
        
        # Normalize based on content length and term frequency
        word_count = len(content.split())
        confidence = min(1.0, (term_count / max(word_count / 100, 1)) * 2)
        
        return round(confidence, 3)

class ContentLibraryProcessor:
    """Specialized processor for content library - Optimizely scenario"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.logger = logging.getLogger(__name__)
    
    async def process_content_library(self, file_paths: List[str]) -> List[ProcessedDocument]:
        """Process content library with optimization for personalization"""
        
        # Process documents with sentence-based chunking for better content matching
        processed_docs = await self.processor.process_batch(
            file_paths=file_paths,
            chunking_strategy=ChunkingStrategy.SENTENCE,
            sentences_per_chunk=3,  # Smaller chunks for granular matching
            overlap_sentences=1,
            max_concurrent=10
        )
        
        # Add content-specific metadata
        for doc in processed_docs:
            for chunk in doc.chunks:
                chunk.metadata.update({
                    "document_domain": "content",
                    "personalization_ready": True,
                    "engagement_potential": self._calculate_engagement_potential(chunk.content),
                    "content_category": self._categorize_content(chunk.content),
                    "reading_level": self._estimate_reading_level(chunk.content)
                })
        
        return processed_docs
    
    def _calculate_engagement_potential(self, content: str) -> float:
        """Calculate potential engagement score for content"""
        engagement_indicators = [
            'how to', 'guide', 'tips', 'best practices', 'strategy',
            'optimize', 'improve', 'increase', 'boost', 'enhance',
            'step-by-step', 'tutorial', 'example'
        ]
        
        indicator_count = sum(1 for indicator in engagement_indicators 
                            if indicator.lower() in content.lower())
        
        # Normalize score
        potential = min(1.0, indicator_count / 5.0)
        
        return round(potential, 3)
    
    def _categorize_content(self, content: str) -> str:
        """Categorize content based on keywords"""
        categories = {
            'analytics': ['analytics', 'data', 'metrics', 'measurement'],
            'optimization': ['optimization', 'testing', 'conversion', 'ab test'],
            'personalization': ['personalization', 'targeting', 'segmentation'],
            'strategy': ['strategy', 'planning', 'roadmap', 'framework'],
            'technical': ['implementation', 'code', 'API', 'integration']
        }
        
        content_lower = content.lower()
        category_scores = {}
        
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            category_scores[category] = score
        
        # Return category with highest score, or 'general' if no clear winner
        if category_scores:
            max_category = max(category_scores, key=category_scores.get)
            if category_scores[max_category] > 0:
                return max_category
        
        return 'general'
    
    def _estimate_reading_level(self, content: str) -> str:
        """Estimate reading difficulty level"""
        sentences = len(re.findall(r'[.!?]+', content))
        words = len(content.split())
        
        if words == 0:
            return 'unknown'
        
        avg_sentence_length = words / max(sentences, 1)
        
        # Simple heuristic based on sentence length
        if avg_sentence_length < 15:
            return 'easy'
        elif avg_sentence_length < 25:
            return 'medium'
        else:
            return 'advanced'

# =============================================================================
# DEMONSTRATION FUNCTIONS
# =============================================================================

async def demonstrate_document_processing():
    """
    Comprehensive demonstration of document processing and chunking strategies
    for enterprise RAG systems.
    """
    
    print("🚀 Document Processing & Chunking Demo")
    print("Advanced Pipeline for Legal and Content Processing")
    print("Target Applications: Lawstronaut (Legal) + Optimizely (Content)")
    
    # Create sample documents for demonstration
    print("\n" + "="*60)
    print("Sample Document Creation")
    print("="*60)
    
    # Create sample legal document
    legal_content = """
    ARTICLE 6 - LAWFULNESS OF PROCESSING

    1. Processing shall be lawful only if and to the extent that at least one of the following applies:

    (a) the data subject has given consent to the processing of his or her personal data for one or more specific purposes;

    (b) processing is necessary for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract;

    (c) processing is necessary for compliance with a legal obligation to which the controller is subject;

    (d) processing is necessary in order to protect the vital interests of the data subject or of another natural person.

    2. Member States may maintain or introduce more specific provisions to adapt the application of the rules of this Regulation with regard to processing for compliance with points (c) and (e) of paragraph 1.

    This regulation establishes the fundamental principles for lawful processing of personal data pursuant to the General Data Protection Regulation (GDPR). Organizations must ensure compliance with at least one of the specified legal bases before processing any personal data.
    """
    
    # Create sample content document
    content_document = """
    A/B Testing Best Practices for Conversion Optimization

    Introduction

    A/B testing is a fundamental methodology for optimizing digital experiences. This guide provides comprehensive strategies for implementing effective tests.

    Planning Your Test

    Before launching any A/B test, establish clear objectives. Define what you want to measure and ensure you have sufficient traffic to reach statistical significance.

    Key principles include:
    - Identify a single variable to test
    - Establish a clear hypothesis
    - Determine required sample size
    - Set test duration parameters

    Implementation Guidelines

    When implementing your test, ensure proper randomization and avoid contamination between variants. Use reliable testing platforms and maintain consistent user experiences.

    Statistical Analysis

    Wait for statistical significance before making decisions. Consider factors like seasonality and external events that might impact results. Document findings for future reference.
    """
    
    # Create temporary files
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        legal_file = os.path.join(temp_dir, "gdpr_article.txt")
        content_file = os.path.join(temp_dir, "ab_testing_guide.txt")
        
        with open(legal_file, 'w') as f:
            f.write(legal_content)
        
        with open(content_file, 'w') as f:
            f.write(content_document)
        
        # Document Processing Demonstrations
        print("\n" + "="*60)
        print("Chunking Strategy Comparison")
        print("="*60)
        
        processor = DocumentProcessor()
        
        # Test different chunking strategies on legal document
        strategies = [
            (ChunkingStrategy.FIXED_SIZE, {"chunk_size": 500, "overlap": 100}),
            (ChunkingStrategy.SEMANTIC, {"max_chunk_size": 800, "min_chunk_size": 200}),
            (ChunkingStrategy.SENTENCE, {"sentences_per_chunk": 3, "overlap_sentences": 1}),
            (ChunkingStrategy.RECURSIVE, {"chunk_size": 600})
        ]
        
        for strategy, params in strategies:
            print(f"\n📄 Testing {strategy.value.title()} Chunking:")
            print("-" * 40)
            
            processed_doc = await processor.process_document(
                legal_file, strategy, **params
            )
            
            print(f"   • Total chunks: {processed_doc.total_chunks}")
            print(f"   • Average chunk size: {processed_doc.processing_stats['avg_chunk_size']:.0f} chars")
            print(f"   • Processing time: {processed_doc.processing_stats['processing_time_ms']:.1f}ms")
            
            # Show first chunk as example
            if processed_doc.chunks:
                first_chunk = processed_doc.chunks[0]
                print(f"   • First chunk preview: {first_chunk.content[:100]}...")
                print(f"   • Chunk metadata: {list(first_chunk.metadata.keys())}")
        
        # Legal Document Processing Demo
        print("\n" + "="*60)
        print("Legal Document Processing - Lawstronaut Scenario")
        print("="*60)
        
        legal_processor = LegalDocumentProcessor()
        legal_doc = await legal_processor.process_legal_document(legal_file)
        
        print(f"\n⚖️  Legal Document Analysis:")
        print(f"   • Document ID: {legal_doc.id}")
        print(f"   • Total chunks: {legal_doc.total_chunks}")
        print(f"   • Total words: {legal_doc.total_words}")
        
        print(f"\n📋 Legal-Specific Analysis:")
        for i, chunk in enumerate(legal_doc.chunks[:3]):  # Show first 3 chunks
            print(f"\nChunk {i+1}:")
            print(f"   • Has citations: {chunk.metadata.get('citation_extractable', False)}")
            print(f"   • Legal confidence: {chunk.metadata.get('legal_confidence', 0)}")
            print(f"   • Content preview: {chunk.content[:150]}...")
        
        # Content Library Processing Demo
        print("\n" + "="*60)
        print("Content Library Processing - Optimizely Scenario")
        print("="*60)
        
        content_processor = ContentLibraryProcessor()
        content_docs = await content_processor.process_content_library([content_file])
        
        if content_docs:
            content_doc = content_docs[0]
            
            print(f"\n🎯 Content Document Analysis:")
            print(f"   • Document ID: {content_doc.id}")
            print(f"   • Total chunks: {content_doc.total_chunks}")
            print(f"   • Processing strategy: {content_doc.processing_stats['chunking_strategy']}")
            
            print(f"\n📊 Content-Specific Analysis:")
            for i, chunk in enumerate(content_doc.chunks[:4]):  # Show first 4 chunks
                print(f"\nChunk {i+1}:")
                print(f"   • Category: {chunk.metadata.get('content_category', 'unknown')}")
                print(f"   • Reading level: {chunk.metadata.get('reading_level', 'unknown')}")
                print(f"   • Engagement potential: {chunk.metadata.get('engagement_potential', 0)}")
                print(f"   • Content: {chunk.content[:120]}...")
        
        # Batch Processing Demo
        print("\n" + "="*60)
        print("Batch Processing Performance")
        print("="*60)
        
        # Process multiple files
        all_docs = await processor.process_batch(
            [legal_file, content_file],
            chunking_strategy=ChunkingStrategy.SEMANTIC,
            max_concurrent=2
        )
        
        print(f"\n📈 Batch Processing Results:")
        print(f"   • Documents processed: {len(all_docs)}")
        
        total_chunks = sum(doc.total_chunks for doc in all_docs)
        total_processing_time = sum(doc.processing_stats['processing_time_ms'] for doc in all_docs)
        
        print(f"   • Total chunks created: {total_chunks}")
        print(f"   • Total processing time: {total_processing_time:.1f}ms")
        print(f"   • Average chunks per document: {total_chunks / len(all_docs):.1f}")
        
        # Chunking Strategy Analysis
        print("\n" + "="*60)
        print("Chunking Strategy Performance Analysis")
        print("="*60)
        
        strategy_comparison = {}
        
        for strategy, params in strategies:
            processed_doc = await processor.process_document(
                content_file, strategy, **params
            )
            
            strategy_comparison[strategy.value] = {
                "chunks": processed_doc.total_chunks,
                "avg_size": processed_doc.processing_stats['avg_chunk_size'],
                "processing_time": processed_doc.processing_stats['processing_time_ms'],
                "size_variance": np.std([chunk.char_count for chunk in processed_doc.chunks])
            }
        
        print(f"\n📊 Strategy Comparison:")
        print(f"{'Strategy':<15} {'Chunks':<8} {'Avg Size':<10} {'Time (ms)':<10} {'Variance':<10}")
        print("-" * 65)
        
        for strategy, stats in strategy_comparison.items():
            print(f"{strategy:<15} {stats['chunks']:<8} {stats['avg_size']:<10.0f} "
                  f"{stats['processing_time']:<10.1f} {stats['size_variance']:<10.1f}")
        
        # Best Practices Summary
        print("\n" + "="*60)
        print("Processing Best Practices Summary")
        print("="*60)
        
        print("\n🎯 Recommendations by Use Case:")
        print("\nLegal Documents (Lawstronaut):")
        print("   • Use Semantic chunking for context preservation")
        print("   • Larger chunk sizes (1500-2000 chars) for legal context")
        print("   • Enable citation detection and legal confidence scoring")
        print("   • Preserve document hierarchy and cross-references")
        
        print("\nContent Library (Optimizely):")
        print("   • Use Sentence chunking for granular personalization")
        print("   • Smaller chunks (300-800 chars) for precise matching")
        print("   • Include engagement potential and reading level analysis")
        print("   • Enable content categorization and audience targeting")
        
        print("\nGeneral Guidelines:")
        print("   • Choose chunking strategy based on content type and use case")
        print("   • Balance chunk size with context preservation needs")
        print("   • Include relevant metadata for enhanced retrieval")
        print("   • Monitor processing performance and optimize accordingly")
    
    print("\n" + "="*60)
    print("✅ Document Processing Demo Complete")
    print("="*60)
    
    print(f"\n🎯 Key Achievements:")
    print(f"   • Demonstrated multiple document parsing formats")
    print(f"   • Implemented 4 different chunking strategies")
    print(f"   • Showcased legal document specialized processing")
    print(f"   • Created content library optimization pipeline")
    print(f"   • Provided performance analysis and best practices")
    print(f"   • Delivered enterprise-grade batch processing capabilities")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Import numpy for statistics
    import numpy as np
    
    # Run comprehensive document processing demonstration
    asyncio.run(demonstrate_document_processing())
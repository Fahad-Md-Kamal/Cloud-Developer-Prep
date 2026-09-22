"""
Integrated Standard Library System for Enterprise Legal Document Processing

This module demonstrates how all Python standard library concepts work together
in a realistic enterprise scenario combining file operations, data processing,
configuration management, caching, and text processing for a legal document
analysis system similar to those used at Lawstronaut.

Key integration patterns:
- pathlib for cross-platform document management
- collections and itertools for memory-efficient processing  
- configparser and argparse for enterprise configuration
- functools for performance optimization with caching
- re for legal document pattern extraction
- Real-time analytics and monitoring integration

Real-world application:
- Complete legal document processing pipeline
- Multi-jurisdiction crawler management system
- Performance monitoring and optimization
- Production deployment patterns

Author: Technical Interview Preparation Guide
"""

import asyncio
import json
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator, Tuple
import configparser
import argparse
import sys
import re
import hashlib
import tempfile
import shutil
from dataclasses import dataclass, field
from collections import Counter, defaultdict, deque
from itertools import islice, groupby, chain
from functools import lru_cache, partial, wraps

# Import components from our other modules (in a real system, these would be separate packages)
from pathlib_enterprise_patterns import (
    LegalDocumentPathManager, DocumentDiscoveryEngine, 
    AtomicFileOperations, DocumentMetadata
)
from data_processing_optimization import (
    LegalCitationAnalyzer, RealTimeAnalyticsEngine, StreamingDataProcessor,
    FunctionalDataPipeline, LegalCitation, UserEvent
)
from enterprise_configuration import LegalCrawlerConfiguration
from functools_enterprise_patterns import (
    intelligent_cache, rate_limit, monitor_performance, retry_with_backoff,
    LegalDocumentNLPProcessor
)

# =============================================================================
# INTEGRATED LEGAL DOCUMENT PROCESSING SYSTEM
# =============================================================================

@dataclass
class ProcessingJob:
    """Represents a document processing job with metadata."""
    job_id: str
    jurisdiction: str
    document_paths: List[Path]
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    results: Dict[str, Any] = field(default_factory=dict)

class LegalDocumentProcessingSystem:
    """
    Integrated legal document processing system demonstrating all
    standard library patterns working together in production.
    
    Combines file management, data processing, configuration,
    caching, and text analysis for a complete enterprise solution.
    """
    
    def __init__(self, config_dir: Path = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration management
        self.config_manager = LegalCrawlerConfiguration(config_dir or Path("config"))
        self.config = {}
        
        # Initialize file management
        self.path_manager = None
        self.discovery_engine = None
        
        # Initialize data processing components
        self.citation_analyzer = LegalCitationAnalyzer()
        self.analytics_engine = None
        self.streaming_processor = StreamingDataProcessor(batch_size=500)
        self.nlp_processor = LegalDocumentNLPProcessor()
        
        # Processing queues and statistics
        self.job_queue = deque()
        self.processing_stats = Counter()
        self.active_jobs = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance monitoring
        self.performance_metrics = defaultdict(list)
        self.last_metrics_reset = time.time()
    
    def initialize(self, environment: str = "development") -> Dict[str, Any]:
        """
        Initialize the processing system with configuration.
        
        Demonstrates integrated startup sequence with all components.
        """
        self.logger.info(f"Initializing legal document processing system for {environment}")
        
        try:
            # 1. Load configuration with environment-specific settings
            self.config = self.config_manager.load_configuration(environment)
            self.logger.info("Configuration loaded successfully")
            
            # 2. Initialize file management with configured paths
            storage_config = self.config.get('storage', {})
            base_path = Path(storage_config.get('base_path', './legal_docs'))
            
            jurisdiction_mapping = {
                'United States': 'us',
                'European Union': 'eu', 
                'United Kingdom': 'uk',
                'Canada': 'ca'
            }
            
            self.path_manager = LegalDocumentPathManager(base_path, jurisdiction_mapping)
            
            # 3. Initialize document discovery
            discovery_paths = [
                base_path / "jurisdictions",
                Path(storage_config.get('archive_path', './archive'))
            ]
            discovery_paths = [p for p in discovery_paths if p.exists() or p == base_path / "jurisdictions"]
            
            max_workers = self.config.get('crawler', {}).get('concurrent_workers', 4)
            self.discovery_engine = DocumentDiscoveryEngine(discovery_paths, max_workers)
            
            # 4. Initialize analytics engine
            window_size = self.config.get('analytics', {}).get('window_size', 5000)
            self.analytics_engine = RealTimeAnalyticsEngine(window_size=window_size)
            
            # 5. Create necessary directories
            self._ensure_directory_structure()
            
            # 6. Load cached data if available
            self._load_cached_state()
            
            initialization_summary = {
                'environment': environment,
                'config_sections': list(self.config.keys()),
                'base_path': str(base_path),
                'discovery_paths': [str(p) for p in discovery_paths],
                'max_workers': max_workers,
                'window_size': window_size,
                'status': 'initialized'
            }
            
            self.logger.info(f"System initialization completed: {initialization_summary}")
            return initialization_summary
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            raise
    
    def _ensure_directory_structure(self):
        """Create necessary directory structure for the system."""
        storage_config = self.config.get('storage', {})
        required_dirs = [
            Path(storage_config.get('base_path', './legal_docs')),
            Path(storage_config.get('temp_path', './temp')),
            Path(storage_config.get('archive_path', './archive')),
            Path('./logs'),
            Path('./cache')
        ]
        
        for directory in required_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
    
    def _load_cached_state(self):
        """Load cached processing state from previous runs."""
        cache_file = Path('./cache/processing_state.json')
        if cache_file.exists():
            try:
                with cache_file.open('r') as f:
                    cached_state = json.load(f)
                
                # Restore statistics
                self.processing_stats.update(cached_state.get('processing_stats', {}))
                
                # Restore performance metrics (last 100 entries)
                for metric_name, values in cached_state.get('performance_metrics', {}).items():
                    self.performance_metrics[metric_name] = deque(values[-100:], maxlen=100)
                
                self.logger.info("Loaded cached processing state")
                
            except Exception as e:
                self.logger.warning(f"Failed to load cached state: {e}")
    
    def _save_cached_state(self):
        """Save current processing state to cache."""
        cache_file = Path('./cache/processing_state.json')
        
        try:
            cached_state = {
                'processing_stats': dict(self.processing_stats),
                'performance_metrics': {
                    name: list(values) for name, values in self.performance_metrics.items()
                },
                'last_saved': datetime.now().isoformat()
            }
            
            atomic_ops = AtomicFileOperations()
            atomic_ops.atomic_json_write(cached_state, cache_file)
            
        except Exception as e:
            self.logger.warning(f"Failed to save cached state: {e}")
    
    @monitor_performance("document_discovery")
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def discover_documents(self, 
                          jurisdictions: List[str] = None,
                          modified_since: Optional[datetime] = None,
                          max_documents: Optional[int] = None) -> Iterator[DocumentMetadata]:
        """
        Discover legal documents with integrated error handling and monitoring.
        
        Combines document discovery with real-time analytics and performance tracking.
        """
        if not self.discovery_engine:
            raise RuntimeError("System not initialized")
        
        jurisdictions = jurisdictions or ['US', 'EU', 'UK', 'Canada']
        patterns = self._get_document_patterns(jurisdictions)
        
        self.logger.info(f"Starting document discovery for jurisdictions: {jurisdictions}")
        
        discovered_count = 0
        start_time = time.time()
        
        try:
            for doc_metadata in self.discovery_engine.discover_documents(
                patterns=patterns,
                modified_since=modified_since,
                max_size_mb=self.config.get('crawler', {}).get('max_file_size_mb', 50)
            ):
                # Track discovery in analytics
                discovery_event = UserEvent(
                    user_id='system',
                    event_type='document_discovered',
                    timestamp=datetime.now(),
                    properties={
                        'jurisdiction': doc_metadata.jurisdiction,
                        'document_type': doc_metadata.document_type,
                        'size_bytes': doc_metadata.size_bytes
                    }
                )
                self.analytics_engine.process_event(discovery_event)
                
                discovered_count += 1
                self.processing_stats['documents_discovered'] += 1
                
                # Update performance metrics
                elapsed_time = time.time() - start_time
                if elapsed_time > 0:
                    discovery_rate = discovered_count / elapsed_time
                    self.performance_metrics['discovery_rate'].append(discovery_rate)
                
                yield doc_metadata
                
                # Respect max documents limit
                if max_documents and discovered_count >= max_documents:
                    break
                
                # Log progress periodically
                if discovered_count % 1000 == 0:
                    self.logger.info(f"Discovered {discovered_count} documents so far")
        
        except Exception as e:
            self.logger.error(f"Document discovery failed: {e}")
            self.processing_stats['discovery_errors'] += 1
            raise
        
        finally:
            total_time = time.time() - start_time
            self.logger.info(f"Document discovery completed: {discovered_count} documents in {total_time:.2f}s")
    
    def _get_document_patterns(self, jurisdictions: List[str]) -> List[str]:
        """Get file patterns for document discovery based on jurisdictions."""
        jurisdiction_patterns = {
            'US': ['**/us/**/*.pdf', '**/united_states/**/*.txt', '**/federal/**/*.docx'],
            'EU': ['**/eu/**/*.pdf', '**/europe/**/*.txt'],
            'UK': ['**/uk/**/*.pdf', '**/britain/**/*.txt'],
            'Canada': ['**/ca/**/*.pdf', '**/canada/**/*.txt']
        }
        
        patterns = []
        for jurisdiction in jurisdictions:
            patterns.extend(jurisdiction_patterns.get(jurisdiction, ['**/*.pdf']))
        
        # Add general patterns
        patterns.extend(['**/*.pdf', '**/*.txt', '**/*.docx'])
        
        return list(set(patterns))  # Remove duplicates
    
    @intelligent_cache(maxsize=5000, ttl_seconds=3600)  # 1 hour TTL
    @monitor_performance("document_processing")
    @rate_limit(calls_per_second=10.0, burst_size=20)
    def process_single_document(self, doc_metadata: DocumentMetadata) -> Dict[str, Any]:
        """
        Process a single legal document with integrated NLP and caching.
        
        Demonstrates all standard library patterns working together for
        complex document processing pipeline.
        """
        self.logger.debug(f"Processing document: {doc_metadata.file_path}")
        
        start_time = time.time()
        processing_result = {
            'document_id': doc_metadata.content_hash,
            'file_path': str(doc_metadata.file_path),
            'jurisdiction': doc_metadata.jurisdiction,
            'document_type': doc_metadata.document_type,
            'processing_timestamp': datetime.now().isoformat(),
            'status': 'processing'
        }
        
        try:
            # 1. Read document content safely
            if not doc_metadata.file_path.exists():
                raise FileNotFoundError(f"Document not found: {doc_metadata.file_path}")
            
            content = self._read_document_safely(doc_metadata.file_path)
            processing_result['content_length'] = len(content)
            
            # 2. Extract legal entities using cached NLP processing
            entities = self.nlp_processor.extract_legal_entities(content)
            processing_result['entities'] = entities
            processing_result['entity_counts'] = {
                entity_type: len(entity_list) 
                for entity_type, entity_list in entities.items()
            }
            
            # 3. Process citations with high-performance collections
            citations = self._extract_citations_from_entities(entities, doc_metadata)
            if citations:
                citation_stats = self.citation_analyzer.process_citation_batch(citations)
                processing_result['citation_processing'] = citation_stats
            
            # 4. Extract document patterns with regex
            patterns = self._extract_document_patterns(content)
            processing_result['patterns'] = patterns
            
            # 5. Calculate document metrics
            metrics = self._calculate_document_metrics(content, entities)
            processing_result['metrics'] = metrics
            
            # 6. Store processing results atomically
            self._store_processing_results(processing_result)
            
            processing_result['status'] = 'completed'
            processing_time = time.time() - start_time
            processing_result['processing_time_seconds'] = processing_time
            
            # Update statistics
            self.processing_stats['documents_processed'] += 1
            self.performance_metrics['processing_time'].append(processing_time)
            
            self.logger.debug(f"Document processed successfully in {processing_time:.3f}s")
            
            return processing_result
            
        except Exception as e:
            processing_result['status'] = 'failed'
            processing_result['error'] = str(e)
            processing_result['processing_time_seconds'] = time.time() - start_time
            
            self.processing_stats['processing_errors'] += 1
            self.logger.error(f"Document processing failed: {e}")
            
            return processing_result
    
    def _read_document_safely(self, file_path: Path) -> str:
        """Safely read document content with encoding detection."""
        try:
            # Try UTF-8 first
            with file_path.open('r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to other encodings
            for encoding in ['latin-1', 'cp1252', 'utf-16']:
                try:
                    with file_path.open('r', encoding=encoding) as f:
                        content = f.read()
                        self.logger.warning(f"Used fallback encoding {encoding} for {file_path}")
                        return content
                except UnicodeDecodeError:
                    continue
            
            # If all else fails, read as binary and decode with error handling
            with file_path.open('rb') as f:
                raw_content = f.read()
                return raw_content.decode('utf-8', errors='replace')
    
    def _extract_citations_from_entities(self, entities: Dict[str, List[str]], 
                                      doc_metadata: DocumentMetadata) -> List[LegalCitation]:
        """Convert extracted entities to LegalCitation objects."""
        citations = []
        
        for case in entities.get('cases', []):
            # Parse case citation (simplified)
            match = re.search(r'(\d+)\s+U\.S\.\s+(\d+)', case)
            if match:
                citation = LegalCitation(
                    case_name=case,
                    year=2000 + int(match.group(1)) % 100,  # Simplified year extraction
                    court="Supreme Court",
                    citation_id=f"US-{match.group(1)}-{match.group(2)}",
                    jurisdiction=doc_metadata.jurisdiction,
                    relevance_score=0.8
                )
                citations.append(citation)
        
        return citations
    
    def _extract_document_patterns(self, content: str) -> Dict[str, List[str]]:
        """Extract common legal document patterns using regex."""
        patterns = {
            'dates': [],
            'monetary_amounts': [],
            'section_references': [],
            'party_names': []
        }
        
        # Compile regex patterns for performance
        date_pattern = re.compile(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b|'
            r'\b\d{1,2}/\d{1,2}/\d{4}\b'
        )
        
        money_pattern = re.compile(r'\$[\d,]+(?:\.\d{2})?')
        section_pattern = re.compile(r'§\s*\d+(?:\.\d+)*|\bSection\s+\d+(?:\.\d+)*', re.IGNORECASE)
        
        # Extract patterns
        patterns['dates'] = date_pattern.findall(content)
        patterns['monetary_amounts'] = money_pattern.findall(content)
        patterns['section_references'] = section_pattern.findall(content)
        
        # Extract potential party names (simplified heuristic)
        party_pattern = re.compile(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:v\.|vs\.|versus)\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*')
        patterns['party_names'] = party_pattern.findall(content)
        
        return patterns
    
    def _calculate_document_metrics(self, content: str, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate various document metrics for analysis."""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = content.split('\n\n')
        
        # Legal-specific metrics
        legal_terms = [
            'pursuant', 'whereas', 'heretofore', 'hereafter', 'notwithstanding',
            'plaintiff', 'defendant', 'court', 'statute', 'regulation'
        ]
        
        legal_term_count = sum(1 for word in words if word.lower() in legal_terms)
        
        return {
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len([p for p in paragraphs if p.strip()]),
            'average_words_per_sentence': len(words) / max(1, len(sentences)),
            'legal_term_density': legal_term_count / max(1, len(words)),
            'total_entities': sum(len(entity_list) for entity_list in entities.values()),
            'entity_density': sum(len(entity_list) for entity_list in entities.values()) / max(1, len(words))
        }
    
    def _store_processing_results(self, result: Dict[str, Any]):
        """Store processing results with atomic operations."""
        results_dir = Path('./cache/processing_results')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        result_file = results_dir / f"{result['document_id']}.json"
        
        atomic_ops = AtomicFileOperations()
        atomic_ops.atomic_json_write(result, result_file)
    
    def batch_process_documents(self, documents: List[DocumentMetadata], 
                              max_workers: int = None) -> Iterator[Dict[str, Any]]:
        """
        Process documents in parallel batches using ThreadPoolExecutor.
        
        Demonstrates integration of concurrent processing with all
        standard library patterns for maximum throughput.
        """
        if not documents:
            return
        
        max_workers = max_workers or self.config.get('crawler', {}).get('concurrent_workers', 4)
        batch_size = self.config.get('processing', {}).get('batch_size', 100)
        
        self.logger.info(f"Starting batch processing of {len(documents)} documents "
                        f"with {max_workers} workers")
        
        # Process documents in batches to manage memory
        for batch_start in range(0, len(documents), batch_size):
            batch = documents[batch_start:batch_start + batch_size]
            batch_number = batch_start // batch_size + 1
            
            self.logger.info(f"Processing batch {batch_number}: {len(batch)} documents")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all documents in batch for processing
                future_to_doc = {
                    executor.submit(self.process_single_document, doc): doc 
                    for doc in batch
                }
                
                # Process completed futures as they finish
                for future in as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    
                    try:
                        result = future.result()
                        yield result
                        
                        # Update batch progress
                        if result['status'] == 'completed':
                            self.processing_stats['batch_successes'] += 1
                        else:
                            self.processing_stats['batch_failures'] += 1
                            
                    except Exception as e:
                        self.logger.error(f"Batch processing error for {doc.file_path}: {e}")
                        self.processing_stats['batch_errors'] += 1
                        
                        yield {
                            'document_id': doc.content_hash,
                            'status': 'batch_error',
                            'error': str(e),
                            'file_path': str(doc.file_path)
                        }
            
            # Periodic statistics logging
            self.logger.info(f"Completed batch {batch_number}")
            
            # Save state periodically
            if batch_number % 5 == 0:
                self._save_cached_state()
    
    def generate_processing_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive processing report with all metrics.
        
        Demonstrates data aggregation using collections and statistics
        computation with functools patterns.
        """
        current_time = datetime.now()
        uptime_seconds = time.time() - self.last_metrics_reset
        
        # Basic statistics
        report = {
            'timestamp': current_time.isoformat(),
            'uptime_seconds': uptime_seconds,
            'processing_statistics': dict(self.processing_stats),
            'system_status': 'running'
        }
        
        # Performance metrics analysis
        if self.performance_metrics:
            perf_analysis = {}
            
            for metric_name, values in self.performance_metrics.items():
                if values:
                    perf_analysis[metric_name] = {
                        'count': len(values),
                        'average': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'recent_average': sum(list(values)[-10:]) / min(10, len(values))
                    }
            
            report['performance_metrics'] = perf_analysis
        
        # Analytics engine statistics
        if self.analytics_engine:
            analytics_stats = self.analytics_engine._get_current_stats()
            report['analytics'] = analytics_stats
        
        # Cache performance from NLP processor
        if self.nlp_processor:
            cache_performance = self.nlp_processor.get_cache_performance()
            report['cache_performance'] = cache_performance
        
        # Citation analysis summary
        if self.citation_analyzer:
            top_citations = self.citation_analyzer.get_top_citations(10)
            jurisdiction_summary = self.citation_analyzer.get_jurisdiction_summary()
            
            report['citation_analysis'] = {
                'top_citations': top_citations,
                'jurisdiction_summary': jurisdiction_summary
            }
        
        # Calculate derived metrics
        total_documents = self.processing_stats.get('documents_processed', 0)
        total_errors = self.processing_stats.get('processing_errors', 0)
        
        if total_documents > 0:
            report['success_rate'] = ((total_documents - total_errors) / total_documents) * 100
            report['average_processing_rate'] = total_documents / max(1, uptime_seconds)
        
        return report
    
    def shutdown(self):
        """Gracefully shutdown the processing system."""
        self.logger.info("Shutting down legal document processing system")
        
        try:
            # Save final state
            self._save_cached_state()
            
            # Clear caches
            if self.nlp_processor:
                # Clear function caches
                if hasattr(self.nlp_processor.extract_legal_entities, 'cache_clear'):
                    self.nlp_processor.extract_legal_entities.cache_clear()
                
                if hasattr(self.nlp_processor.calculate_document_similarity, 'cache_clear'):
                    self.nlp_processor.calculate_document_similarity.cache_clear()
            
            # Generate final report
            final_report = self.generate_processing_report()
            report_file = Path('./logs/final_processing_report.json')
            
            atomic_ops = AtomicFileOperations()
            atomic_ops.atomic_json_write(final_report, report_file)
            
            self.logger.info("System shutdown completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

# =============================================================================
# COMMAND-LINE INTERFACE INTEGRATION
# =============================================================================

def create_integrated_cli():
    """Create comprehensive CLI for the integrated system."""
    parser = argparse.ArgumentParser(
        prog="legal-document-processor",
        description="Integrated Legal Document Processing System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--environment", default="development")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process legal documents")
    process_parser.add_argument("--jurisdictions", nargs="+", default=["US", "EU", "UK"])
    process_parser.add_argument("--max-documents", type=int, help="Maximum documents to process")
    process_parser.add_argument("--max-workers", type=int, help="Maximum worker threads")
    process_parser.add_argument("--batch-size", type=int, default=100)
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover legal documents")
    discover_parser.add_argument("--jurisdictions", nargs="+", default=["US", "EU", "UK"])
    discover_parser.add_argument("--since-days", type=int, help="Only documents modified in last N days")
    discover_parser.add_argument("--max-documents", type=int)
    discover_parser.add_argument("--output-format", choices=["json", "csv", "table"], default="table")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate processing report")
    report_parser.add_argument("--format", choices=["json", "summary"], default="summary")
    report_parser.add_argument("--output-file", type=Path, help="Save report to file")
    
    return parser

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

def setup_demo_environment():
    """Set up demonstration environment with sample data."""
    # Create sample documents
    sample_docs_dir = Path("./demo_legal_docs")
    jurisdictions = ["us", "eu", "uk"]
    
    for jurisdiction in jurisdictions:
        jurisdiction_dir = sample_docs_dir / "jurisdictions" / jurisdiction / "cases"
        jurisdiction_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample legal documents
        for i in range(5):
            doc_content = f"""
            Legal Document {i+1} for {jurisdiction.upper()}
            
            Case: Sample Case {i+1} v. Example Corp
            Citation: {100+i} U.S. {200+i} (2024)
            
            This document discusses the legal principles established in previous cases,
            including references to 42 U.S.C. § {1980+i} and related statutes.
            
            The court found that pursuant to the regulations established on January {i+10}, 2024,
            the plaintiff's claim for ${(i+1)*10000} in damages was justified.
            
            Notwithstanding the defendant's arguments, the court ruled in favor of
            the plaintiff based on precedent established in landmark cases.
            """
            
            doc_file = jurisdiction_dir / f"case_{i+1:03d}.txt"
            doc_file.write_text(doc_content)
    
    # Create sample configuration
    config_dir = Path("./demo_config")
    config_dir.mkdir(exist_ok=True)
    
    demo_config = """
[crawler]
rate_limit = 5
concurrent_workers = 2
max_file_size_mb = 10

[storage]
base_path = ./demo_legal_docs
temp_path = ./demo_temp
archive_path = ./demo_archive

[analytics]
window_size = 1000

[processing]
batch_size = 50

[logging]
level = INFO
"""
    
    (config_dir / "default.ini").write_text(demo_config)
    
    return sample_docs_dir, config_dir

def demonstrate_integrated_stdlib_system():
    """
    Comprehensive demonstration of all standard library concepts
    working together in an integrated enterprise system.
    """
    
    print("=== Integrated Standard Library System for Enterprise Legal Document Processing ===\n")
    
    # Setup demonstration environment
    print("1. Setting up demonstration environment...")
    demo_docs_dir, demo_config_dir = setup_demo_environment()
    print(f"Created demo documents in: {demo_docs_dir}")
    print(f"Created demo config in: {demo_config_dir}")
    
    try:
        # 2. Initialize integrated system
        print("\n2. Initializing integrated processing system...")
        
        processing_system = LegalDocumentProcessingSystem(demo_config_dir)
        init_summary = processing_system.initialize("development")
        
        print(f"System initialized successfully:")
        for key, value in init_summary.items():
            print(f"  {key}: {value}")
        
        # 3. Document discovery with all components
        print("\n3. Discovering legal documents...")
        
        discovered_documents = list(processing_system.discover_documents(
            jurisdictions=["US", "EU", "UK"],
            max_documents=20
        ))
        
        print(f"Discovered {len(discovered_documents)} documents:")
        for doc in discovered_documents[:3]:  # Show first 3
            print(f"  - {doc.file_path} ({doc.jurisdiction}, {doc.document_type})")
        
        # 4. Batch document processing
        print("\n4. Processing documents with integrated pipeline...")
        
        start_time = time.time()
        processed_results = list(processing_system.batch_process_documents(
            discovered_documents, max_workers=2
        ))
        processing_time = time.time() - start_time
        
        print(f"Processed {len(processed_results)} documents in {processing_time:.2f}s")
        
        # Show processing results summary
        successful = sum(1 for r in processed_results if r['status'] == 'completed')
        failed = len(processed_results) - successful
        
        print(f"Processing summary: {successful} successful, {failed} failed")
        
        # Show sample processing result
        if processed_results:
            sample_result = processed_results[0]
            if sample_result['status'] == 'completed':
                print(f"\nSample processing result:")
                print(f"  Document: {sample_result['file_path']}")
                print(f"  Entities found: {sample_result['entity_counts']}")
                print(f"  Processing time: {sample_result['processing_time_seconds']:.3f}s")
                if 'metrics' in sample_result:
                    print(f"  Word count: {sample_result['metrics']['word_count']}")
                    print(f"  Legal term density: {sample_result['metrics']['legal_term_density']:.3f}")
        
        # 5. Performance and analytics reporting
        print("\n5. Generating comprehensive system report...")
        
        report = processing_system.generate_processing_report()
        
        print("System Performance Report:")
        print(f"  Uptime: {report['uptime_seconds']:.1f} seconds")
        print(f"  Documents processed: {report['processing_statistics'].get('documents_processed', 0)}")
        print(f"  Success rate: {report.get('success_rate', 0):.1f}%")
        
        if 'performance_metrics' in report:
            for metric_name, metrics in report['performance_metrics'].items():
                print(f"  {metric_name}: avg={metrics['average']:.3f}s, "
                      f"min={metrics['min']:.3f}s, max={metrics['max']:.3f}s")
        
        if 'cache_performance' in report:
            cache_perf = report['cache_performance']
            for cache_name, stats in cache_perf.items():
                hit_rate = stats.get('hit_rate', 0)
                print(f"  {cache_name} cache hit rate: {hit_rate:.1f}%")
        
        # 6. Citation analysis results
        if 'citation_analysis' in report:
            citation_data = report['citation_analysis']
            print(f"\nCitation Analysis:")
            
            if citation_data['top_citations']:
                print("  Top citations:")
                for citation, count in citation_data['top_citations'][:3]:
                    print(f"    {citation}: {count} occurrences")
            
            if citation_data['jurisdiction_summary']:
                print("  Citations by jurisdiction:")
                for jurisdiction, courts in citation_data['jurisdiction_summary'].items():
                    total = sum(courts.values())
                    print(f"    {jurisdiction}: {total} total citations")
        
        # 7. Test CLI integration
        print("\n6. Testing CLI integration...")
        
        cli = create_integrated_cli()
        
        # Show help
        print("CLI Help Output:")
        try:
            cli.parse_args(["--help"])
        except SystemExit:
            pass  # Help output causes SystemExit
        
        # 8. Performance comparison demonstration
        print("\n7. Standard Library Performance Demonstration:")
        
        # Compare different processing approaches
        sample_docs = discovered_documents[:5]
        
        # Sequential processing
        start_time = time.time()
        for doc in sample_docs:
            _ = processing_system.process_single_document(doc)
        sequential_time = time.time() - start_time
        
        # Clear cache for fair comparison
        processing_system.nlp_processor.extract_legal_entities.cache_clear()
        
        # Parallel processing
        start_time = time.time()
        _ = list(processing_system.batch_process_documents(sample_docs, max_workers=2))
        parallel_time = time.time() - start_time
        
        print(f"Processing {len(sample_docs)} documents:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Parallel: {parallel_time:.3f}s")
        print(f"  Speedup: {sequential_time / parallel_time:.1f}x")
        
        # Final system report
        final_report = processing_system.generate_processing_report()
        print(f"\nFinal system statistics:")
        print(f"  Total function calls: {final_report['processing_statistics'].get('total_calls', 'N/A')}")
        print(f"  Cache efficiency: {final_report.get('cache_performance', {}).get('entity_extraction', {}).get('hit_rate', 'N/A')}%")
        
        # 9. Graceful shutdown
        print("\n8. Graceful system shutdown...")
        processing_system.shutdown()
        print("System shutdown completed")
        
    finally:
        # Cleanup demonstration files
        print("\n9. Cleaning up demonstration environment...")
        cleanup_paths = [demo_docs_dir, demo_config_dir, Path("./demo_temp"), 
                        Path("./demo_archive"), Path("./cache"), Path("./logs")]
        
        for path in cleanup_paths:
            if path.exists():
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
                print(f"Cleaned up: {path}")
    
    print("\n=== All integrated standard library patterns successfully demonstrated ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Run comprehensive demonstration
    demonstrate_integrated_stdlib_system()
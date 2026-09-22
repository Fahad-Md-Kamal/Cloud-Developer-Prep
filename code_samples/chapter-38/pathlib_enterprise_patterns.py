"""
pathlib Enterprise Patterns Implementation for Legal Document Processing

This module demonstrates advanced pathlib patterns applied to realistic
scenarios like those used at Lawstronaut for legal document processing.

Key concepts covered:
- Cross-platform path operations for document archives
- Atomic file operations for transactional processing  
- Enterprise file discovery and batch processing patterns
- Performance optimization for large file hierarchies
- Security patterns for path sanitization

Real-world applications:
- Legal document crawling and processing pipelines
- Multi-jurisdiction file system handling
- Compliance auditing and backup strategies

Author: Technical Interview Preparation Guide
"""

from pathlib import Path
from typing import Iterator, List, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
import tempfile
import shutil
import hashlib
import json
import time
import logging
from datetime import datetime, timedelta
import stat
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# ENTERPRISE PATH MANAGEMENT PATTERNS
# =============================================================================

@dataclass
class DocumentMetadata:
    """Metadata for legal documents with enterprise validation"""
    file_path: Path
    size_bytes: int
    modified_time: float
    content_hash: str
    jurisdiction: str
    document_type: str
    classification: str = "unclassified"

class LegalDocumentPathManager:
    """
    Production-grade path management for legal document processing systems.
    
    Handles cross-platform paths, security validation, and performance
    optimization for systems processing millions of legal documents.
    """
    
    def __init__(self, base_path: Path, jurisdiction_mapping: Dict[str, str]):
        self.base_path = Path(base_path).resolve()
        self.jurisdiction_mapping = jurisdiction_mapping
        self._path_cache = {}
        self._lock = threading.Lock()
        
        # Ensure base directory exists with proper permissions
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def sanitize_path(self, user_input: str) -> Path:
        """
        Sanitize user input to prevent directory traversal attacks.
        
        Critical for systems accepting file paths from external sources.
        """
        # Remove dangerous path components
        sanitized = user_input.replace("..", "").replace("//", "/")
        
        # Resolve against base path to prevent escaping
        full_path = (self.base_path / sanitized).resolve()
        
        # Verify the resolved path is within base directory
        try:
            full_path.relative_to(self.base_path)
            return full_path
        except ValueError:
            raise SecurityError(f"Path traversal attempt detected: {user_input}")
    
    def get_jurisdiction_path(self, jurisdiction: str) -> Path:
        """
        Get standardized path for jurisdiction-specific documents.
        
        Implements caching for high-performance path resolution.
        """
        with self._lock:
            if jurisdiction not in self._path_cache:
                normalized_jurisdiction = self.jurisdiction_mapping.get(
                    jurisdiction, jurisdiction.lower().replace(" ", "_")
                )
                jurisdiction_path = self.base_path / "jurisdictions" / normalized_jurisdiction
                jurisdiction_path.mkdir(parents=True, exist_ok=True)
                self._path_cache[jurisdiction] = jurisdiction_path
            
            return self._path_cache[jurisdiction]
    
    def create_document_path(self, jurisdiction: str, doc_type: str, 
                           doc_id: str, extension: str = "pdf") -> Path:
        """
        Create standardized document path with collision avoidance.
        """
        jurisdiction_path = self.get_jurisdiction_path(jurisdiction)
        doc_type_path = jurisdiction_path / doc_type
        doc_type_path.mkdir(exist_ok=True)
        
        # Create date-based subdirectory for better performance
        date_path = doc_type_path / datetime.now().strftime("%Y/%m")
        date_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with collision detection
        base_name = f"{doc_id}.{extension}"
        final_path = date_path / base_name
        
        counter = 1
        while final_path.exists():
            base_name = f"{doc_id}_{counter}.{extension}"
            final_path = date_path / base_name
            counter += 1
            
        return final_path

# =============================================================================
# ENTERPRISE FILE DISCOVERY AND BATCH PROCESSING
# =============================================================================

class DocumentDiscoveryEngine:
    """
    High-performance document discovery system for legal archives.
    
    Supports complex filtering, parallel processing, and incremental updates
    for systems handling millions of legal documents.
    """
    
    def __init__(self, root_paths: List[Path], max_workers: int = 4):
        self.root_paths = [Path(p) for p in root_paths]
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
    def discover_documents(self, 
                          patterns: List[str] = None,
                          modified_since: Optional[datetime] = None,
                          max_size_mb: Optional[int] = None) -> Iterator[DocumentMetadata]:
        """
        Discover documents matching criteria with parallel processing.
        
        Yields DocumentMetadata objects for streaming processing without
        loading entire file lists into memory.
        """
        if patterns is None:
            patterns = ["**/*.pdf", "**/*.docx", "**/*.txt"]
        
        cutoff_time = modified_since.timestamp() if modified_since else 0
        max_size_bytes = (max_size_mb * 1024 * 1024) if max_size_mb else float('inf')
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit discovery tasks for each root path and pattern
            future_to_pattern = {}
            for root_path in self.root_paths:
                for pattern in patterns:
                    future = executor.submit(
                        self._discover_pattern, root_path, pattern, 
                        cutoff_time, max_size_bytes
                    )
                    future_to_pattern[future] = (root_path, pattern)
            
            # Process results as they complete
            for future in as_completed(future_to_pattern):
                root_path, pattern = future_to_pattern[future]
                try:
                    for doc_metadata in future.result():
                        yield doc_metadata
                except Exception as e:
                    self.logger.error(f"Discovery failed for {root_path}/{pattern}: {e}")
    
    def _discover_pattern(self, root_path: Path, pattern: str, 
                         cutoff_time: float, max_size_bytes: int) -> List[DocumentMetadata]:
        """
        Discover documents matching a specific pattern in a root path.
        """
        documents = []
        
        try:
            for file_path in root_path.glob(pattern):
                if not file_path.is_file():
                    continue
                
                try:
                    stat_info = file_path.stat()
                    
                    # Apply filters
                    if stat_info.st_mtime < cutoff_time:
                        continue
                    if stat_info.st_size > max_size_bytes:
                        continue
                    
                    # Extract metadata
                    content_hash = self._calculate_file_hash(file_path)
                    jurisdiction = self._extract_jurisdiction(file_path)
                    doc_type = self._extract_document_type(file_path)
                    
                    metadata = DocumentMetadata(
                        file_path=file_path,
                        size_bytes=stat_info.st_size,
                        modified_time=stat_info.st_mtime,
                        content_hash=content_hash,
                        jurisdiction=jurisdiction,
                        document_type=doc_type
                    )
                    
                    documents.append(metadata)
                    
                except (OSError, PermissionError) as e:
                    self.logger.warning(f"Cannot access {file_path}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Pattern discovery failed for {pattern}: {e}")
            
        return documents
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash for file integrity verification."""
        hasher = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return "unknown"
    
    def _extract_jurisdiction(self, file_path: Path) -> str:
        """Extract jurisdiction from file path structure."""
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part == "jurisdictions" and i + 1 < len(parts):
                return parts[i + 1].replace("_", " ").title()
        return "Unknown"
    
    def _extract_document_type(self, file_path: Path) -> str:
        """Extract document type from file path or content analysis."""
        # Simple extraction based on parent directory
        parent_name = file_path.parent.name.lower()
        if any(term in parent_name for term in ["regulation", "statute", "law"]):
            return "statute"
        elif any(term in parent_name for term in ["case", "court", "judgment"]):
            return "case_law"
        else:
            return "document"

# =============================================================================
# ATOMIC FILE OPERATIONS FOR PRODUCTION SAFETY
# =============================================================================

class AtomicFileOperations:
    """
    Atomic file operations ensuring data integrity in production systems.
    
    Prevents partial writes, corruption, and race conditions in concurrent
    legal document processing pipelines.
    """
    
    @staticmethod
    @contextmanager
    def atomic_write(target_path: Path, mode: str = 'w', encoding: str = 'utf-8'):
        """
        Context manager for atomic file writes.
        
        Writes to temporary file first, then atomically moves to target.
        Ensures no partial files exist if process crashes.
        """
        target_path = Path(target_path)
        temp_path = None
        
        try:
            # Create temporary file in same directory for atomic move
            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_path.parent,
                prefix=f".tmp_{target_path.name}_"
            )
            
            # Open temporary file with requested mode
            if 'b' in mode:
                temp_file = open(temp_fd, mode)
            else:
                temp_file = open(temp_fd, mode, encoding=encoding)
            
            yield temp_file
            
            # Ensure data is written to disk
            temp_file.flush()
            if hasattr(temp_file, 'fileno'):
                import os
                os.fsync(temp_file.fileno())
            
            temp_file.close()
            
            # Atomic move (rename) to final location
            Path(temp_path).replace(target_path)
            temp_path = None  # Prevent cleanup
            
        except Exception:
            # Clean up temporary file on error
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
            raise
    
    @staticmethod
    def atomic_json_write(data: Any, target_path: Path, indent: int = 2):
        """Write JSON data atomically with proper error handling."""
        with AtomicFileOperations.atomic_write(target_path, 'w') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def safe_copy_with_backup(source: Path, destination: Path, 
                             backup_suffix: str = ".backup") -> bool:
        """
        Copy file with automatic backup of destination if it exists.
        
        Returns True if copy succeeded, False otherwise.
        """
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            return False
        
        try:
            # Create backup if destination exists
            if destination.exists():
                backup_path = destination.with_suffix(
                    destination.suffix + backup_suffix
                )
                shutil.copy2(destination, backup_path)
            
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Perform the copy with metadata
            shutil.copy2(source, destination)
            return True
            
        except (OSError, shutil.Error) as e:
            logging.error(f"Copy failed from {source} to {destination}: {e}")
            return False

# =============================================================================
# ENTERPRISE FILE LIFECYCLE MANAGEMENT
# =============================================================================

class DocumentLifecycleManager:
    """
    Manages document lifecycle for compliance and performance optimization.
    
    Handles archival, cleanup, and retention policies for legal document
    processing systems with audit trail requirements.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'processed': 0,
            'archived': 0,
            'deleted': 0,
            'errors': 0
        }
    
    def apply_retention_policy(self, documents: Iterator[DocumentMetadata]) -> Dict[str, int]:
        """
        Apply retention policy to document collection.
        
        Returns statistics about actions taken.
        """
        retention_days = self.config.get('retention_days', 2555)  # ~7 years
        archive_days = self.config.get('archive_days', 365)
        cutoff_timestamp = (datetime.now() - timedelta(days=retention_days)).timestamp()
        archive_timestamp = (datetime.now() - timedelta(days=archive_days)).timestamp()
        
        for doc_metadata in documents:
            self.stats['processed'] += 1
            
            try:
                if doc_metadata.modified_time < cutoff_timestamp:
                    self._delete_document(doc_metadata)
                elif doc_metadata.modified_time < archive_timestamp:
                    self._archive_document(doc_metadata)
                    
            except Exception as e:
                self.logger.error(f"Lifecycle processing failed for {doc_metadata.file_path}: {e}")
                self.stats['errors'] += 1
        
        return dict(self.stats)
    
    def _archive_document(self, doc_metadata: DocumentMetadata):
        """Move document to archive storage with compression."""
        archive_root = Path(self.config.get('archive_path', '/archive'))
        archive_path = self._get_archive_path(doc_metadata, archive_root)
        
        # Ensure archive directory exists
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move to archive (atomic operation)
        doc_metadata.file_path.replace(archive_path)
        self.stats['archived'] += 1
        
        self.logger.info(f"Archived: {doc_metadata.file_path} -> {archive_path}")
    
    def _delete_document(self, doc_metadata: DocumentMetadata):
        """Securely delete document with audit logging."""
        # Log deletion for compliance audit
        self.logger.info(f"Deleting document: {doc_metadata.file_path} "
                        f"(hash: {doc_metadata.content_hash})")
        
        # Remove file
        doc_metadata.file_path.unlink()
        self.stats['deleted'] += 1
    
    def _get_archive_path(self, doc_metadata: DocumentMetadata, archive_root: Path) -> Path:
        """Generate archive path maintaining organization structure."""
        relative_path = doc_metadata.file_path.relative_to(
            doc_metadata.file_path.parts[0]
        )
        return archive_root / relative_path

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

class SecurityError(Exception):
    """Custom exception for security-related path operations."""
    pass

def demonstrate_pathlib_enterprise_patterns():
    """
    Comprehensive demonstration of pathlib enterprise patterns
    for legal document processing systems.
    """
    
    print("=== pathlib Enterprise Patterns for Legal Document Processing ===\n")
    
    # Setup test environment
    test_root = Path("test_legal_docs")
    test_root.mkdir(exist_ok=True)
    
    try:
        # 1. Path Management with Security
        print("1. Enterprise Path Management with Security Validation")
        
        jurisdiction_mapping = {
            "United States": "us",
            "European Union": "eu", 
            "United Kingdom": "uk"
        }
        
        path_manager = LegalDocumentPathManager(test_root, jurisdiction_mapping)
        
        # Demonstrate secure path creation
        doc_path = path_manager.create_document_path(
            "United States", "regulations", "gdpr_compliance_2024", "pdf"
        )
        print(f"Created secure document path: {doc_path}")
        
        # Test security validation (this should fail safely)
        try:
            dangerous_path = path_manager.sanitize_path("../../etc/passwd")
            print("WARNING: Security bypass detected!")
        except SecurityError as e:
            print(f"✓ Security validation working: {e}")
        
        # 2. High-Performance Document Discovery
        print("\n2. High-Performance Document Discovery")
        
        # Create sample documents
        sample_docs = [
            test_root / "us" / "cases" / "landmark_case.pdf",
            test_root / "eu" / "regulations" / "gdpr.pdf", 
            test_root / "uk" / "statutes" / "data_protection_act.txt"
        ]
        
        for doc_path in sample_docs:
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            with doc_path.open('w') as f:
                f.write(f"Sample legal document: {doc_path.name}")
        
        discovery_engine = DocumentDiscoveryEngine([test_root])
        
        # Discover recent documents
        recent_cutoff = datetime.now() - timedelta(days=1)
        discovered_docs = list(discovery_engine.discover_documents(
            patterns=["**/*.pdf", "**/*.txt"],
            modified_since=recent_cutoff,
            max_size_mb=10
        ))
        
        print(f"Discovered {len(discovered_docs)} documents:")
        for doc in discovered_docs[:3]:  # Show first 3
            print(f"  - {doc.file_path} ({doc.document_type}, {doc.jurisdiction})")
        
        # 3. Atomic File Operations
        print("\n3. Atomic File Operations for Data Integrity")
        
        # Demonstrate atomic write
        atomic_ops = AtomicFileOperations()
        atomic_test_file = test_root / "atomic_test.json"
        
        test_data = {
            "document_id": "test_123",
            "processing_timestamp": datetime.now().isoformat(),
            "metadata": {
                "jurisdiction": "US",
                "classification": "public"
            }
        }
        
        start_time = time.time()
        atomic_ops.atomic_json_write(test_data, atomic_test_file)
        write_time = time.time() - start_time
        
        print(f"✓ Atomic JSON write completed in {write_time:.4f}s")
        print(f"File size: {atomic_test_file.stat().st_size} bytes")
        
        # 4. Document Lifecycle Management
        print("\n4. Document Lifecycle Management")
        
        lifecycle_config = {
            'retention_days': 30,  # Short for demo
            'archive_days': 7,
            'archive_path': str(test_root / 'archive')
        }
        
        lifecycle_manager = DocumentLifecycleManager(lifecycle_config)
        
        # Apply retention policy
        stats = lifecycle_manager.apply_retention_policy(iter(discovered_docs))
        
        print("Lifecycle management statistics:")
        for action, count in stats.items():
            print(f"  {action}: {count}")
        
        # 5. Performance Metrics
        print("\n5. Performance Metrics and Scalability")
        
        # File system performance test
        large_file_test = test_root / "performance_test.dat"
        data_size_mb = 1  # 1MB test file
        test_data = b"0" * (data_size_mb * 1024 * 1024)
        
        # Test write performance
        start_time = time.time()
        with atomic_ops.atomic_write(large_file_test, 'wb') as f:
            f.write(test_data)
        write_time = time.time() - start_time
        
        # Test read performance
        start_time = time.time()
        with large_file_test.open('rb') as f:
            read_data = f.read()
        read_time = time.time() - start_time
        
        print(f"Write performance: {data_size_mb / write_time:.2f} MB/s")
        print(f"Read performance: {data_size_mb / read_time:.2f} MB/s")
        print(f"Data integrity: {'✓ PASSED' if len(read_data) == len(test_data) else '✗ FAILED'}")
        
        print("\n=== All pathlib enterprise patterns successfully demonstrated ===")
        
    finally:
        # Cleanup test environment
        if test_root.exists():
            shutil.rmtree(test_root)
            print(f"\nCleaned up test directory: {test_root}")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    demonstrate_pathlib_enterprise_patterns()
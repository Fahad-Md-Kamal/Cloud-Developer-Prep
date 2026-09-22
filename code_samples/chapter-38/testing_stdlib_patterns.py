"""
Testing Strategies for Standard Library Patterns

This module demonstrates comprehensive testing approaches for enterprise-grade
systems using Python standard library patterns. Includes unit tests, integration
tests, performance testing, and mocking strategies.

Key testing concepts covered:
- Unit testing with unittest and pytest patterns
- Mocking external dependencies and file system operations
- Performance benchmarking and regression testing
- Integration testing with real dependencies
- Error condition and edge case testing
- Thread safety and concurrency testing

Real-world applications:
- Testing legal document processing pipelines
- Validating configuration management systems
- Performance regression testing for caching systems
- Integration testing for multi-component systems

Author: Technical Interview Preparation Guide
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import shutil
import time
import threading
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from typing import Dict, Any, List
import logging

# Suppress logging during tests
logging.disable(logging.CRITICAL)

# =============================================================================
# TEST UTILITIES AND FIXTURES
# =============================================================================

class TestDataFixtures:
    """Test data fixtures for consistent testing."""
    
    @staticmethod
    def create_sample_legal_document() -> str:
        return """
        Legal Document Test Case
        
        In the case of TestCase v. Example Corp, 123 U.S. 456 (2024), the court
        ruled on the interpretation of 42 U.S.C. § 1983. The Corporation filed
        a motion on January 15, 2024, pursuant to the statute.
        
        The plaintiff sought damages of $50,000 for the alleged violations.
        The court found that notwithstanding the defendant's arguments,
        the case should proceed to trial.
        """
    
    @staticmethod
    def create_sample_document_metadata():
        from pathlib_enterprise_patterns import DocumentMetadata
        from pathlib import Path
        
        return DocumentMetadata(
            file_path=Path("/test/sample_doc.txt"),
            size_bytes=1024,
            modified_time=time.time(),
            content_hash="test_hash_123",
            jurisdiction="US",
            document_type="case_law"
        )
    
    @staticmethod
    def create_sample_citations():
        from data_processing_optimization import LegalCitation
        
        return [
            LegalCitation(
                case_name="Test Case 1",
                year=2024,
                court="Supreme Court",
                citation_id="TEST-001",
                jurisdiction="US",
                relevance_score=0.8
            ),
            LegalCitation(
                case_name="Test Case 2", 
                year=2023,
                court="Appeals Court",
                citation_id="TEST-002",
                jurisdiction="EU",
                relevance_score=0.7
            )
        ]

# =============================================================================
# UNIT TESTS FOR PATHLIB PATTERNS
# =============================================================================

class TestPathlibEnterprisePatterns(unittest.TestCase):
    """Unit tests for pathlib enterprise patterns."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Import here to avoid import errors in demo
        try:
            from pathlib_enterprise_patterns import LegalDocumentPathManager
            self.path_manager_class = LegalDocumentPathManager
        except ImportError:
            self.skipTest("pathlib_enterprise_patterns module not available")
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
    
    def test_path_manager_initialization(self):
        """Test LegalDocumentPathManager initialization."""
        jurisdiction_mapping = {"US": "us", "EU": "eu"}
        manager = self.path_manager_class(self.test_path, jurisdiction_mapping)
        
        self.assertEqual(manager.base_path, self.test_path)
        self.assertEqual(manager.jurisdiction_mapping, jurisdiction_mapping)
        self.assertTrue(self.test_path.exists())
    
    def test_secure_path_sanitization(self):
        """Test path sanitization security features."""
        jurisdiction_mapping = {"US": "us"}
        manager = self.path_manager_class(self.test_path, jurisdiction_mapping)
        
        # Test normal path
        safe_path = manager.sanitize_path("documents/legal.pdf")
        self.assertTrue(str(safe_path).startswith(str(self.test_path)))
        
        # Test path traversal attempt
        with self.assertRaises(Exception):  # Should raise SecurityError
            manager.sanitize_path("../../etc/passwd")
    
    def test_document_path_creation(self):
        """Test document path creation with collision avoidance."""
        jurisdiction_mapping = {"US": "us"}
        manager = self.path_manager_class(self.test_path, jurisdiction_mapping)
        
        # Create first document path
        path1 = manager.create_document_path("US", "cases", "test_doc")
        self.assertTrue("us" in str(path1))
        self.assertTrue("cases" in str(path1))
        
        # Create the file to test collision avoidance
        path1.parent.mkdir(parents=True, exist_ok=True)
        path1.write_text("test content")
        
        # Create second document with same parameters
        path2 = manager.create_document_path("US", "cases", "test_doc")
        self.assertNotEqual(path1, path2)  # Should avoid collision
        self.assertTrue("test_doc_1" in str(path2))
    
    @patch('pathlib.Path.glob')
    def test_document_discovery_with_mock(self, mock_glob):
        """Test document discovery with mocked file system."""
        from pathlib_enterprise_patterns import DocumentDiscoveryEngine
        
        # Mock glob results
        mock_files = [
            Path("/test/doc1.pdf"),
            Path("/test/doc2.txt"), 
            Path("/test/doc3.pdf")
        ]
        mock_glob.return_value = mock_files
        
        # Mock stat results
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            mock_stat.return_value.st_mtime = time.time()
            
            with patch.object(Path, 'is_file', return_value=True):
                discovery_engine = DocumentDiscoveryEngine([self.test_path])
                
                documents = list(discovery_engine.discover_documents(
                    patterns=["**/*.pdf", "**/*.txt"],
                    max_size_mb=10
                ))
                
                self.assertEqual(len(documents), len(mock_files))

# =============================================================================
# UNIT TESTS FOR DATA PROCESSING OPTIMIZATION  
# =============================================================================

class TestDataProcessingOptimization(unittest.TestCase):
    """Unit tests for collections and itertools patterns."""
    
    def setUp(self):
        """Set up test data."""
        self.sample_citations = TestDataFixtures.create_sample_citations()
    
    def test_citation_analyzer_performance(self):
        """Test citation analyzer with performance monitoring."""
        try:
            from data_processing_optimization import LegalCitationAnalyzer
        except ImportError:
            self.skipTest("data_processing_optimization module not available")
        
        analyzer = LegalCitationAnalyzer()
        
        # Test batch processing
        batch_stats = analyzer.process_citation_batch(self.sample_citations)
        
        self.assertIn('processed_count', batch_stats)
        self.assertIn('new_citations', batch_stats)
        self.assertEqual(batch_stats['processed_count'], len(self.sample_citations))
    
    def test_analytics_engine_threading(self):
        """Test analytics engine thread safety."""
        try:
            from data_processing_optimization import RealTimeAnalyticsEngine, UserEvent
            from datetime import datetime
        except ImportError:
            self.skipTest("data_processing_optimization module not available")
        
        engine = RealTimeAnalyticsEngine(window_size=1000)
        results = []
        errors = []
        
        def process_events(thread_id: int):
            try:
                for i in range(100):
                    event = UserEvent(
                        user_id=f"user_{thread_id}_{i}",
                        event_type="test_event",
                        timestamp=datetime.now()
                    )
                    result = engine.process_event(event)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Test concurrent processing
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=process_events, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        self.assertEqual(len(results), 500)  # 5 threads * 100 events
    
    def test_streaming_processor_memory_efficiency(self):
        """Test streaming processor memory efficiency."""
        try:
            from data_processing_optimization import StreamingDataProcessor
        except ImportError:
            self.skipTest("data_processing_optimization module not available")
        
        processor = StreamingDataProcessor(batch_size=10)
        
        # Create large data stream generator
        def large_data_stream(size: int):
            for i in range(size):
                yield {"id": i, "data": f"item_{i}"}
        
        # Process stream in batches
        batch_count = 0
        processed_items = 0
        
        for batch in processor.batch_processor(large_data_stream(1000)):
            batch_count += 1
            processed_items += len(batch)
            self.assertLessEqual(len(batch), 10)  # Respect batch size
        
        self.assertEqual(processed_items, 1000)
        self.assertEqual(batch_count, 100)  # 1000 items / 10 per batch

# =============================================================================
# UNIT TESTS FOR CONFIGURATION MANAGEMENT
# =============================================================================

class TestConfigurationManagement(unittest.TestCase):
    """Unit tests for enterprise configuration patterns."""
    
    def setUp(self):
        """Set up test configuration directory."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / "config"
        self.config_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment."""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_configuration_loading_hierarchy(self):
        """Test hierarchical configuration loading."""
        try:
            from enterprise_configuration import LegalCrawlerConfiguration
        except ImportError:
            self.skipTest("enterprise_configuration module not available")
        
        # Create test configuration files
        (self.config_dir / "default.ini").write_text("""
[crawler]
rate_limit = 10
user_agent = Test/1.0

[database]
host = localhost
port = 5432
        """)
        
        (self.config_dir / "development.ini").write_text("""
[crawler]
rate_limit = 2

[database]
host = dev.example.com
        """)
        
        config_manager = LegalCrawlerConfiguration(self.config_dir)
        config = config_manager.load_configuration("development")
        
        # Test override behavior
        self.assertEqual(config_manager.get("crawler.rate_limit"), 2)  # Overridden
        self.assertEqual(config_manager.get("crawler.user_agent"), "Test/1.0")  # Default
        self.assertEqual(config_manager.get("database.host"), "dev.example.com")  # Overridden
        self.assertEqual(config_manager.get("database.port"), 5432)  # Default
    
    def test_environment_variable_override(self):
        """Test environment variable configuration overrides."""
        try:
            from enterprise_configuration import LegalCrawlerConfiguration
            import os
        except ImportError:
            self.skipTest("enterprise_configuration module not available")
        
        # Create basic config
        (self.config_dir / "default.ini").write_text("""
[crawler]
rate_limit = 10

[database]
host = localhost
        """)
        
        # Set environment variables
        test_env_vars = {
            "CRAWLER_CRAWLER_RATE_LIMIT": "25",
            "CRAWLER_DATABASE_HOST": "env.example.com"
        }
        
        for key, value in test_env_vars.items():
            os.environ[key] = value
        
        try:
            config_manager = LegalCrawlerConfiguration(self.config_dir)
            config = config_manager.load_configuration("development")
            
            # Test environment overrides
            self.assertEqual(config_manager.get("crawler.rate_limit"), 25)
            self.assertEqual(config_manager.get("database.host"), "env.example.com")
            
        finally:
            # Clean up environment variables
            for key in test_env_vars.keys():
                if key in os.environ:
                    del os.environ[key]
    
    def test_configuration_validation(self):
        """Test configuration validation against schema."""
        try:
            from enterprise_configuration import LegalCrawlerConfiguration
        except ImportError:
            self.skipTest("enterprise_configuration module not available")
        
        # Create invalid configuration
        (self.config_dir / "default.ini").write_text("""
[crawler]
rate_limit = -5  # Invalid: should be positive

[database]
port = 99999  # Invalid: port out of range
        """)
        
        config_manager = LegalCrawlerConfiguration(self.config_dir)
        
        # Should raise validation error
        with self.assertRaises(ValueError):
            config_manager.load_configuration("development")

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegratedSystem(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create test documents
        self.docs_dir = self.test_path / "documents" / "jurisdictions" / "us" / "cases"
        self.docs_dir.mkdir(parents=True)
        
        for i in range(3):
            doc_file = self.docs_dir / f"test_case_{i+1}.txt"
            doc_file.write_text(TestDataFixtures.create_sample_legal_document())
        
        # Create test configuration
        self.config_dir = self.test_path / "config"
        self.config_dir.mkdir()
        
        (self.config_dir / "default.ini").write_text("""
[crawler]
rate_limit = 100
concurrent_workers = 2

[storage]
base_path = """ + str(self.test_path / "documents") + """
temp_path = """ + str(self.test_path / "temp") + """

[processing]
batch_size = 5
        """)
    
    def tearDown(self):
        """Clean up integration test environment."""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)
    
    def test_full_document_processing_pipeline(self):
        """Test complete document processing pipeline integration."""
        try:
            from integrated_stdlib_system import LegalDocumentProcessingSystem
        except ImportError:
            self.skipTest("integrated_stdlib_system module not available")
        
        # Initialize system
        processing_system = LegalDocumentProcessingSystem(self.config_dir)
        init_result = processing_system.initialize("development")
        
        self.assertEqual(init_result['status'], 'initialized')
        
        try:
            # Discover documents
            discovered_docs = list(processing_system.discover_documents(
                jurisdictions=["US"],
                max_documents=5
            ))
            
            self.assertGreater(len(discovered_docs), 0)
            
            # Process documents
            processed_results = list(processing_system.batch_process_documents(
                discovered_docs[:2], max_workers=1
            ))
            
            self.assertEqual(len(processed_results), 2)
            
            # Verify processing results
            for result in processed_results:
                self.assertIn('status', result)
                self.assertIn('document_id', result)
                
                if result['status'] == 'completed':
                    self.assertIn('entities', result)
                    self.assertIn('metrics', result)
                    self.assertIn('processing_time_seconds', result)
            
            # Generate report
            report = processing_system.generate_processing_report()
            
            self.assertIn('processing_statistics', report)
            self.assertIn('system_status', report)
            self.assertEqual(report['system_status'], 'running')
            
        finally:
            processing_system.shutdown()

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance(unittest.TestCase):
    """Performance and benchmarking tests."""
    
    def test_caching_performance_improvement(self):
        """Test caching provides significant performance improvement."""
        try:
            from functools_enterprise_patterns import LegalDocumentNLPProcessor
        except ImportError:
            self.skipTest("functools_enterprise_patterns module not available")
        
        processor = LegalDocumentNLPProcessor()
        test_document = TestDataFixtures.create_sample_legal_document()
        
        # Measure uncached performance (first call)
        start_time = time.perf_counter()
        result1 = processor.extract_legal_entities(test_document)
        uncached_time = time.perf_counter() - start_time
        
        # Measure cached performance (second call)
        start_time = time.perf_counter()
        result2 = processor.extract_legal_entities(test_document)
        cached_time = time.perf_counter() - start_time
        
        # Verify results are identical
        self.assertEqual(result1, result2)
        
        # Verify caching provides significant speedup
        speedup = uncached_time / cached_time if cached_time > 0 else float('inf')
        self.assertGreater(speedup, 2.0, "Caching should provide at least 2x speedup")
    
    def test_collections_performance_vs_builtin(self):
        """Test that specialized collections outperform built-in alternatives."""
        from collections import Counter, deque
        
        # Test Counter vs dict for frequency counting
        test_data = ["item_" + str(i % 100) for i in range(10000)]
        
        # Test Counter performance
        start_time = time.perf_counter()
        counter = Counter(test_data)
        most_common_counter = counter.most_common(10)
        counter_time = time.perf_counter() - start_time
        
        # Test dict performance
        start_time = time.perf_counter()
        freq_dict = {}
        for item in test_data:
            freq_dict[item] = freq_dict.get(item, 0) + 1
        most_common_dict = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        dict_time = time.perf_counter() - start_time
        
        # Counter should be faster or comparable
        speedup = dict_time / counter_time
        self.assertGreater(speedup, 0.8, "Counter should be competitive with dict")
        
        # Test deque vs list for queue operations
        operations = 5000
        
        # Test deque performance
        test_deque = deque()
        start_time = time.perf_counter()
        for i in range(operations):
            test_deque.append(i)
        for i in range(operations // 2):
            test_deque.popleft()
        deque_time = time.perf_counter() - start_time
        
        # Test list performance
        test_list = []
        start_time = time.perf_counter()
        for i in range(operations):
            test_list.append(i)
        for i in range(operations // 2):
            test_list.pop(0)
        list_time = time.perf_counter() - start_time
        
        # deque should be significantly faster for queue operations
        queue_speedup = list_time / deque_time
        self.assertGreater(queue_speedup, 5.0, "deque should be much faster for queue operations")

# =============================================================================
# ERROR CONDITION AND EDGE CASE TESTS
# =============================================================================

class TestErrorConditions(unittest.TestCase):
    """Test error conditions and edge cases."""
    
    def test_file_system_error_handling(self):
        """Test graceful handling of file system errors."""
        try:
            from pathlib_enterprise_patterns import DocumentDiscoveryEngine
        except ImportError:
            self.skipTest("pathlib_enterprise_patterns module not available")
        
        # Test with non-existent directory
        non_existent_path = Path("/non/existent/directory")
        discovery_engine = DocumentDiscoveryEngine([non_existent_path])
        
        # Should handle gracefully without throwing exceptions
        documents = list(discovery_engine.discover_documents())
        self.assertEqual(len(documents), 0)
    
    def test_configuration_error_recovery(self):
        """Test configuration system error recovery."""
        try:
            from enterprise_configuration import LegalCrawlerConfiguration
        except ImportError:
            self.skipTest("enterprise_configuration module not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create invalid configuration file
            (config_dir / "default.ini").write_text("invalid config content [")
            
            config_manager = LegalCrawlerConfiguration(config_dir)
            
            # Should raise appropriate exception
            with self.assertRaises((ValueError, Exception)):
                config_manager.load_configuration("development")
    
    def test_concurrent_processing_stability(self):
        """Test system stability under concurrent load."""
        try:
            from data_processing_optimization import RealTimeAnalyticsEngine, UserEvent
            from datetime import datetime
        except ImportError:
            self.skipTest("data_processing_optimization module not available")
        
        engine = RealTimeAnalyticsEngine(window_size=1000)
        errors = []
        processed_count = [0]
        
        def stress_test_worker(worker_id: int, event_count: int):
            try:
                for i in range(event_count):
                    event = UserEvent(
                        user_id=f"stress_user_{worker_id}_{i}",
                        event_type=f"stress_event_{i % 5}",
                        timestamp=datetime.now()
                    )
                    engine.process_event(event)
                    processed_count[0] += 1
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run stress test with multiple workers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(stress_test_worker, i, 50)
                for i in range(10)
            ]
            
            for future in futures:
                future.result()  # Wait for completion
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent processing errors: {errors}")
        self.assertEqual(processed_count[0], 500)  # 10 workers * 50 events

# =============================================================================
# TEST SUITE RUNNER
# =============================================================================

def run_comprehensive_test_suite():
    """Run the complete test suite with reporting."""
    print("=== Comprehensive Testing Suite for Standard Library Patterns ===\n")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestPathlibEnterprisePatterns,
        TestDataProcessingOptimization,
        TestConfigurationManagement,
        TestIntegratedSystem,
        TestPerformance,
        TestErrorConditions
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed reporting
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    start_time = time.time()
    
    result = runner.run(test_suite)
    
    end_time = time.time()
    
    # Print summary
    print(f"\n=== Test Suite Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 'N/A'}")
    print(f"Total time: {end_time - start_time:.2f} seconds")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) 
                   / result.testsRun * 100) if result.testsRun > 0 else 0
    
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Re-enable logging for test output
    logging.disable(logging.NOTSET)
    
    success = run_comprehensive_test_suite()
    sys.exit(0 if success else 1)
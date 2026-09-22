"""
Data Processing Optimization with collections and itertools for Enterprise Systems

This module demonstrates memory-efficient data processing patterns applied to
realistic scenarios like those used at Lawstronaut and Optimizely for handling
millions of legal documents and AI/ML analytics at scale.

Key concepts covered:
- Advanced collections for high-performance data structures
- itertools for memory-efficient streaming computations  
- Real-time analytics patterns with specialized collections
- Functional programming approaches to data transformation
- Memory optimization techniques for large dataset processing

Real-world applications:
- Legal document frequency analysis and citation mapping
- Real-time user behavior analytics for A/B testing
- Streaming data processing for AI model training

Author: Technical Interview Preparation Guide
"""

from typing import Iterator, Dict, List, Tuple, Optional, Any, Callable, Protocol
from collections import Counter, defaultdict, deque, ChainMap, OrderedDict, namedtuple
from itertools import (
    islice, chain, groupby, accumulate, compress, dropwhile, takewhile,
    cycle, repeat, count, product, combinations, permutations, 
    combinations_with_replacement, filterfalse, starmap, zip_longest
)
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import time
import logging
import threading
import queue
import heapq
import bisect
from concurrent.futures import ThreadPoolExecutor
import json
import random
from datetime import datetime, timedelta
import sys
from functools import partial, reduce

# =============================================================================
# ADVANCED COLLECTIONS FOR REAL-TIME ANALYTICS
# =============================================================================

@dataclass
class LegalCitation:
    """Represents a legal citation with metadata."""
    case_name: str
    year: int
    court: str
    citation_id: str
    jurisdiction: str
    relevance_score: float = 0.0

@dataclass 
class UserEvent:
    """Represents a user interaction event for analytics."""
    user_id: str
    event_type: str
    timestamp: datetime
    experiment_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

class LegalCitationAnalyzer:
    """
    High-performance legal citation analysis using specialized collections.
    
    Demonstrates Counter, defaultdict, and custom data structures for
    processing millions of legal citations in real-time.
    """
    
    def __init__(self):
        # Counter for O(1) frequency analysis
        self.citation_frequency = Counter()
        self.court_frequency = Counter()
        self.yearly_frequency = Counter()
        
        # defaultdict for automatic grouping without key checks
        self.citations_by_court = defaultdict(list)
        self.citations_by_jurisdiction = defaultdict(lambda: defaultdict(list))
        
        # OrderedDict for LRU-like behavior in citation cache
        self.citation_cache = OrderedDict()
        self.cache_max_size = 10000
        
        # Thread-safe operations tracking
        self._lock = threading.Lock()
        self._processing_stats = {
            'total_processed': 0,
            'processing_errors': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def process_citation_batch(self, citations: List[LegalCitation]) -> Dict[str, Any]:
        """
        Process a batch of citations with optimized collection operations.
        
        Uses Counter for frequency analysis, defaultdict for grouping,
        and OrderedDict for caching - all in O(1) or O(log n) time.
        """
        batch_stats = {
            'processed_count': 0,
            'new_citations': 0,
            'duplicate_citations': 0
        }
        
        with self._lock:
            for citation in citations:
                citation_key = f"{citation.case_name}_{citation.year}"
                
                # Check cache first (LRU-like behavior)
                if citation_key in self.citation_cache:
                    # Move to end (most recently used)
                    self.citation_cache.move_to_end(citation_key)
                    self._processing_stats['cache_hits'] += 1
                    batch_stats['duplicate_citations'] += 1
                    continue
                
                # Process new citation
                self._process_single_citation(citation)
                
                # Add to cache with LRU eviction
                self.citation_cache[citation_key] = citation
                if len(self.citation_cache) > self.cache_max_size:
                    self.citation_cache.popitem(last=False)  # Remove oldest
                
                self._processing_stats['cache_misses'] += 1
                batch_stats['new_citations'] += 1
                batch_stats['processed_count'] += 1
        
        return batch_stats
    
    def _process_single_citation(self, citation: LegalCitation):
        """Process individual citation with O(1) collection operations."""
        # Counter operations - O(1) amortized
        self.citation_frequency[citation.case_name] += 1
        self.court_frequency[citation.court] += 1  
        self.yearly_frequency[citation.year] += 1
        
        # defaultdict operations - O(1) amortized, no key existence checks
        self.citations_by_court[citation.court].append(citation)
        self.citations_by_jurisdiction[citation.jurisdiction][citation.court].append(citation)
    
    def get_top_citations(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently cited cases using Counter's most_common."""
        return self.citation_frequency.most_common(limit)
    
    def get_jurisdiction_summary(self) -> Dict[str, Dict[str, int]]:
        """
        Get citation summary by jurisdiction using defaultdict.
        
        Demonstrates nested defaultdict access without key checks.
        """
        summary = {}
        for jurisdiction, courts in self.citations_by_jurisdiction.items():
            summary[jurisdiction] = {
                court: len(citations) 
                for court, citations in courts.items()
            }
        return summary

class RealTimeAnalyticsEngine:
    """
    Real-time user analytics engine using collections for Optimizely-style A/B testing.
    
    Demonstrates deque for sliding windows, Counter for event tracking,
    and ChainMap for configuration layering.
    """
    
    def __init__(self, window_size: int = 1000, config_layers: List[Dict] = None):
        # deque for O(1) operations at both ends - perfect for sliding windows
        self.event_window = deque(maxlen=window_size)
        
        # Counter for real-time event frequency analysis
        self.event_counts = Counter()
        self.experiment_counts = Counter() 
        self.user_activity = Counter()
        
        # ChainMap for layered configuration without dict merging overhead
        config_layers = config_layers or [{}]
        self.config = ChainMap(*config_layers)
        
        # Thread-safe metrics collection
        self._metrics_lock = threading.Lock()
        self.metrics = {
            'events_per_second': deque(maxlen=60),  # Last 60 seconds
            'active_experiments': set(),
            'unique_users': set()
        }
    
    def process_event(self, event: UserEvent) -> Dict[str, Any]:
        """
        Process user event with O(1) collection operations.
        
        Uses deque sliding window for real-time metrics and Counter
        for frequency analysis without manual counting.
        """
        current_time = time.time()
        
        with self._metrics_lock:
            # Add to sliding window (automatic eviction of old events)
            self.event_window.append((event, current_time))
            
            # Update counters - O(1) operations
            self.event_counts[event.event_type] += 1
            self.user_activity[event.user_id] += 1
            
            if event.experiment_id:
                self.experiment_counts[event.experiment_id] += 1
                self.metrics['active_experiments'].add(event.experiment_id)
            
            self.metrics['unique_users'].add(event.user_id)
            
            # Update real-time metrics
            self._update_realtime_metrics(current_time)
        
        return self._get_current_stats()
    
    def _update_realtime_metrics(self, current_time: float):
        """Update real-time metrics using deque for efficient windowing."""
        # Count events in last second using deque iteration
        recent_events = sum(
            1 for _, timestamp in self.event_window 
            if current_time - timestamp <= 1.0
        )
        self.metrics['events_per_second'].append(recent_events)
    
    def get_experiment_performance(self, experiment_id: str) -> Dict[str, Any]:
        """
        Calculate A/B test performance metrics using collections.
        
        Demonstrates filtering with collections and statistical computations.
        """
        experiment_events = [
            event for event, _ in self.event_window 
            if event.experiment_id == experiment_id
        ]
        
        if not experiment_events:
            return {'error': 'No data for experiment'}
        
        # Use Counter for conversion tracking
        conversion_counter = Counter()
        user_counter = Counter()
        
        for event in experiment_events:
            user_counter[event.user_id] += 1
            if event.event_type in ('purchase', 'signup', 'conversion'):
                conversion_counter[event.user_id] += 1
        
        total_users = len(user_counter)
        converted_users = len(conversion_counter)
        conversion_rate = converted_users / total_users if total_users > 0 else 0
        
        return {
            'experiment_id': experiment_id,
            'total_users': total_users,
            'converted_users': converted_users,
            'conversion_rate': conversion_rate,
            'total_events': len(experiment_events),
            'events_per_user': sum(user_counter.values()) / total_users if total_users > 0 else 0
        }
    
    def _get_current_stats(self) -> Dict[str, Any]:
        """Get current analytics statistics."""
        avg_events_per_sec = (
            sum(self.metrics['events_per_second']) / len(self.metrics['events_per_second'])
            if self.metrics['events_per_second'] else 0
        )
        
        return {
            'total_events': len(self.event_window),
            'unique_users': len(self.metrics['unique_users']),
            'active_experiments': len(self.metrics['active_experiments']),
            'avg_events_per_second': avg_events_per_sec,
            'top_events': self.event_counts.most_common(5)
        }

# =============================================================================
# MEMORY-EFFICIENT PROCESSING WITH ITERTOOLS
# =============================================================================

class StreamingDataProcessor:
    """
    Memory-efficient data processing using itertools for large datasets.
    
    Processes data streams without loading entire datasets into memory,
    perfect for legal document analysis or AI training data preprocessing.
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.logger = logging.getLogger(__name__)
        
    def batch_processor(self, data_stream: Iterator[Any]) -> Iterator[List[Any]]:
        """
        Create batches from infinite data stream using islice.
        
        Memory-efficient batching without loading entire stream.
        """
        iterator = iter(data_stream)
        while True:
            batch = list(islice(iterator, self.batch_size))
            if not batch:
                break
            yield batch
    
    def process_legal_documents_stream(self, document_stream: Iterator[Dict]) -> Iterator[Dict]:
        """
        Process legal documents with streaming transformations.
        
        Demonstrates chaining itertools operations for complex data pipelines
        without intermediate storage.
        """
        # Chain multiple document sources
        def enhance_document(doc: Dict) -> Dict:
            """Add computed fields to document."""
            doc['word_count'] = len(doc.get('content', '').split())
            doc['processing_timestamp'] = datetime.now().isoformat()
            return doc
        
        # Filter documents by criteria  
        def is_valid_document(doc: Dict) -> bool:
            return (
                doc.get('content', '') and
                len(doc.get('content', '')) > 100 and
                doc.get('jurisdiction') is not None
            )
        
        # Process with itertools pipeline
        enhanced_docs = map(enhance_document, document_stream)
        valid_docs = filter(is_valid_document, enhanced_docs)
        
        # Group by jurisdiction using groupby (requires sorted input)
        def get_jurisdiction(doc: Dict) -> str:
            return doc.get('jurisdiction', 'unknown')
        
        # Sort first, then group
        sorted_docs = sorted(valid_docs, key=get_jurisdiction)
        grouped_docs = groupby(sorted_docs, key=get_jurisdiction)
        
        for jurisdiction, doc_group in grouped_docs:
            doc_list = list(doc_group)
            yield {
                'jurisdiction': jurisdiction,
                'document_count': len(doc_list),
                'total_words': sum(doc['word_count'] for doc in doc_list),
                'documents': doc_list
            }
    
    def create_document_combinations(self, documents: List[Dict], 
                                   combination_size: int = 2) -> Iterator[Tuple[Dict, ...]]:
        """
        Generate document combinations for similarity analysis.
        
        Uses itertools.combinations for memory-efficient pairing
        without creating full Cartesian product in memory.
        """
        # Filter documents first to reduce combination space
        valid_documents = [
            doc for doc in documents 
            if doc.get('content') and len(doc['content']) > 50
        ]
        
        # Generate combinations without storing all in memory
        return combinations(valid_documents, combination_size)
    
    def compute_sliding_statistics(self, data_stream: Iterator[float], 
                                 window_size: int = 100) -> Iterator[Dict[str, float]]:
        """
        Compute sliding window statistics using itertools and collections.
        
        Memory-efficient streaming statistics without storing entire dataset.
        """
        window = deque(maxlen=window_size)
        
        for value in data_stream:
            window.append(value)
            
            if len(window) >= window_size:
                # Compute statistics on current window
                sorted_window = sorted(window)
                window_sum = sum(window)
                window_len = len(window)
                
                yield {
                    'mean': window_sum / window_len,
                    'median': sorted_window[window_len // 2],
                    'min': sorted_window[0],
                    'max': sorted_window[-1],
                    'count': window_len
                }
    
    def parallel_batch_processing(self, data_stream: Iterator[Any],
                                processing_func: Callable,
                                max_workers: int = 4) -> Iterator[Any]:
        """
        Process batches in parallel using ThreadPoolExecutor and itertools.
        
        Demonstrates combining itertools batching with concurrent processing
        for CPU-bound operations on large datasets.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create batches and submit for processing
            batch_futures = []
            
            for batch in self.batch_processor(data_stream):
                future = executor.submit(processing_func, batch)
                batch_futures.append(future)
                
                # Process completed batches as they finish
                if len(batch_futures) >= max_workers * 2:  # Keep pipeline full
                    completed_futures = []
                    for future in as_completed(batch_futures):
                        try:
                            result = future.result()
                            for item in result:
                                yield item
                            completed_futures.append(future)
                        except Exception as e:
                            self.logger.error(f"Batch processing error: {e}")
                            completed_futures.append(future)
                    
                    # Remove completed futures
                    for future in completed_futures:
                        batch_futures.remove(future)
            
            # Process remaining batches
            for future in as_completed(batch_futures):
                try:
                    result = future.result()
                    for item in result:
                        yield item
                except Exception as e:
                    self.logger.error(f"Final batch processing error: {e}")

# =============================================================================
# FUNCTIONAL PROGRAMMING WITH COLLECTIONS AND ITERTOOLS
# =============================================================================

class FunctionalDataPipeline:
    """
    Functional programming patterns for data transformation pipelines.
    
    Demonstrates composing itertools and collections operations for
    complex data processing workflows common in AI/ML and legal analytics.
    """
    
    @staticmethod
    def create_citation_network(citations: List[LegalCitation]) -> Dict[str, List[str]]:
        """
        Create citation network using functional programming patterns.
        
        Demonstrates reduce, groupby, and collection transformations.
        """
        # Group citations by court using itertools and reduce
        def group_by_court(acc: Dict[str, List[LegalCitation]], citation: LegalCitation) -> Dict[str, List[LegalCitation]]:
            if citation.court not in acc:
                acc[citation.court] = []
            acc[citation.court].append(citation)
            return acc
        
        court_groups = reduce(group_by_court, citations, {})
        
        # Create network connections using combinations
        citation_network = {}
        
        for court, court_citations in court_groups.items():
            # Create connections between citations in same court
            for citation1, citation2 in combinations(court_citations, 2):
                key1 = f"{citation1.case_name}_{citation1.year}"
                key2 = f"{citation2.case_name}_{citation2.year}" 
                
                if key1 not in citation_network:
                    citation_network[key1] = []
                if key2 not in citation_network:
                    citation_network[key2] = []
                
                citation_network[key1].append(key2)
                citation_network[key2].append(key1)
        
        return citation_network
    
    @staticmethod
    def analyze_user_journey_patterns(events: List[UserEvent]) -> Dict[str, Any]:
        """
        Analyze user journey patterns using functional transformations.
        
        Uses itertools operations to identify common user behavior patterns
        for conversion optimization.
        """
        # Sort events by user and timestamp
        sorted_events = sorted(events, key=lambda e: (e.user_id, e.timestamp))
        
        # Group events by user
        user_journeys = {}
        for user_id, user_events in groupby(sorted_events, key=lambda e: e.user_id):
            journey = list(user_events)
            user_journeys[user_id] = [event.event_type for event in journey]
        
        # Find common journey patterns using Counter
        journey_patterns = Counter()
        
        # Generate n-grams (sequences) from each user journey
        for user_id, journey in user_journeys.items():
            for n in range(2, min(6, len(journey) + 1)):  # 2-5 step patterns
                for pattern in zip(*[journey[i:] for i in range(n)]):
                    pattern_key = " -> ".join(pattern)
                    journey_patterns[pattern_key] += 1
        
        # Calculate conversion patterns
        conversion_events = {'purchase', 'signup', 'conversion'}
        conversion_patterns = Counter()
        
        for pattern, count in journey_patterns.items():
            steps = pattern.split(" -> ")
            if any(step in conversion_events for step in steps):
                conversion_patterns[pattern] = count
        
        return {
            'total_users': len(user_journeys),
            'total_patterns': len(journey_patterns),
            'most_common_patterns': journey_patterns.most_common(10),
            'conversion_patterns': conversion_patterns.most_common(10),
            'avg_journey_length': sum(len(journey) for journey in user_journeys.values()) / len(user_journeys)
        }

# =============================================================================
# PERFORMANCE BENCHMARKING AND OPTIMIZATION
# =============================================================================

class CollectionsPerformanceBenchmark:
    """
    Performance benchmarking for collections and itertools operations.
    
    Demonstrates measuring and optimizing data structure performance
    for enterprise-scale applications.
    """
    
    def __init__(self):
        self.results = {}
    
    def benchmark_counter_vs_dict(self, data_size: int = 100000) -> Dict[str, float]:
        """
        Benchmark Counter vs dict for frequency counting operations.
        """
        # Generate test data
        test_data = [f"item_{i % 1000}" for i in range(data_size)]
        
        # Test Counter performance
        start_time = time.perf_counter()
        counter = Counter(test_data)
        most_common = counter.most_common(10)
        counter_time = time.perf_counter() - start_time
        
        # Test dict performance
        start_time = time.perf_counter()
        freq_dict = {}
        for item in test_data:
            freq_dict[item] = freq_dict.get(item, 0) + 1
        
        # Sort to get most common (equivalent operation)
        sorted_items = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        dict_time = time.perf_counter() - start_time
        
        return {
            'counter_time': counter_time,
            'dict_time': dict_time,
            'counter_faster_by': dict_time / counter_time if counter_time > 0 else float('inf'),
            'data_size': data_size
        }
    
    def benchmark_deque_vs_list(self, operations: int = 10000) -> Dict[str, float]:
        """
        Benchmark deque vs list for queue operations.
        """
        # Test deque performance for queue operations
        test_deque = deque()
        start_time = time.perf_counter()
        
        for i in range(operations):
            test_deque.append(i)
        for i in range(operations // 2):
            test_deque.popleft()
        
        deque_time = time.perf_counter() - start_time
        
        # Test list performance for same operations
        test_list = []
        start_time = time.perf_counter()
        
        for i in range(operations):
            test_list.append(i)
        for i in range(operations // 2):
            test_list.pop(0)  # O(n) operation
        
        list_time = time.perf_counter() - start_time
        
        return {
            'deque_time': deque_time,
            'list_time': list_time,
            'deque_faster_by': list_time / deque_time if deque_time > 0 else float('inf'),
            'operations': operations
        }
    
    def benchmark_itertools_vs_loops(self, data_size: int = 100000) -> Dict[str, float]:
        """
        Benchmark itertools vs traditional loops for data processing.
        """
        test_data = list(range(data_size))
        
        # Test itertools chain performance
        start_time = time.perf_counter()
        chained = list(chain(test_data, test_data, test_data))
        itertools_time = time.perf_counter() - start_time
        
        # Test traditional loop performance
        start_time = time.perf_counter()
        manual_chain = []
        for sublist in [test_data, test_data, test_data]:
            manual_chain.extend(sublist)
        loop_time = time.perf_counter() - start_time
        
        return {
            'itertools_time': itertools_time,
            'loop_time': loop_time,
            'itertools_faster_by': loop_time / itertools_time if itertools_time > 0 else float('inf'),
            'result_size': len(chained)
        }

# =============================================================================
# DEMONSTRATION AND INTEGRATION
# =============================================================================

def generate_sample_citations(count: int = 1000) -> List[LegalCitation]:
    """Generate sample legal citations for testing."""
    courts = ['Supreme Court', 'Appeals Court', 'District Court', 'Federal Circuit']
    jurisdictions = ['US', 'EU', 'UK', 'Canada']
    
    citations = []
    for i in range(count):
        citation = LegalCitation(
            case_name=f"Sample Case {i % 200}",  # Some duplicates for frequency analysis
            year=random.randint(1950, 2024),
            court=random.choice(courts),
            citation_id=f"CITE-{i:06d}",
            jurisdiction=random.choice(jurisdictions),
            relevance_score=random.uniform(0.1, 1.0)
        )
        citations.append(citation)
    
    return citations

def generate_sample_events(count: int = 5000) -> List[UserEvent]:
    """Generate sample user events for analytics testing."""
    event_types = ['page_view', 'click', 'signup', 'purchase', 'logout']
    experiment_ids = ['exp_001', 'exp_002', 'exp_003', None]
    
    events = []
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(count):
        event = UserEvent(
            user_id=f"user_{i % 500}",  # 500 unique users
            event_type=random.choice(event_types),
            timestamp=base_time + timedelta(seconds=random.randint(0, 86400)),
            experiment_id=random.choice(experiment_ids),
            properties={'session_id': f"session_{i % 1000}"}
        )
        events.append(event)
    
    return events

def demonstrate_data_processing_optimization():
    """
    Comprehensive demonstration of collections and itertools optimization
    for enterprise data processing systems.
    """
    
    print("=== Data Processing Optimization with collections and itertools ===\n")
    
    # 1. Legal Citation Analysis with Advanced Collections
    print("1. Legal Citation Analysis with Advanced Collections")
    
    citations = generate_sample_citations(10000)
    citation_analyzer = LegalCitationAnalyzer()
    
    # Process citations in batches
    batch_size = 1000
    total_time = 0
    
    for i in range(0, len(citations), batch_size):
        batch = citations[i:i + batch_size]
        start_time = time.perf_counter()
        
        batch_stats = citation_analyzer.process_citation_batch(batch)
        batch_time = time.perf_counter() - start_time
        total_time += batch_time
        
        if i == 0:  # Show stats for first batch
            print(f"Batch processing stats: {batch_stats}")
    
    print(f"Total processing time: {total_time:.4f}s")
    print(f"Processing rate: {len(citations) / total_time:.0f} citations/second")
    
    # Show top citations and jurisdiction summary
    top_citations = citation_analyzer.get_top_citations(5)
    print(f"Top 5 citations: {top_citations}")
    
    jurisdiction_summary = citation_analyzer.get_jurisdiction_summary()
    print(f"Citations by jurisdiction: {jurisdiction_summary}")
    
    # 2. Real-Time Analytics Engine
    print("\n2. Real-Time Analytics Engine for A/B Testing")
    
    events = generate_sample_events(20000)
    analytics_engine = RealTimeAnalyticsEngine(window_size=5000)
    
    # Process events and measure performance
    start_time = time.perf_counter()
    processed_count = 0
    
    for event in events:
        stats = analytics_engine.process_event(event)
        processed_count += 1
        
        # Show stats every 5000 events
        if processed_count % 5000 == 0:
            print(f"Processed {processed_count} events: {stats}")
    
    processing_time = time.perf_counter() - start_time
    print(f"Event processing rate: {len(events) / processing_time:.0f} events/second")
    
    # Analyze experiment performance
    exp_performance = analytics_engine.get_experiment_performance('exp_001')
    print(f"Experiment exp_001 performance: {exp_performance}")
    
    # 3. Memory-Efficient Streaming Processing
    print("\n3. Memory-Efficient Streaming Processing with itertools")
    
    processor = StreamingDataProcessor(batch_size=500)
    
    # Create sample document stream
    def document_generator(count: int = 5000):
        jurisdictions = ['US', 'EU', 'UK', 'Canada']
        for i in range(count):
            yield {
                'doc_id': f"doc_{i:06d}",
                'jurisdiction': random.choice(jurisdictions),
                'content': f"Legal document content {i} " * random.randint(10, 100),
                'created_date': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
            }
    
    # Process document stream
    start_time = time.perf_counter()
    processed_jurisdictions = 0
    
    for jurisdiction_data in processor.process_legal_documents_stream(document_generator()):
        processed_jurisdictions += 1
        if processed_jurisdictions <= 3:  # Show first 3 jurisdictions
            print(f"Jurisdiction: {jurisdiction_data['jurisdiction']}, "
                  f"Documents: {jurisdiction_data['document_count']}, "
                  f"Total words: {jurisdiction_data['total_words']}")
    
    streaming_time = time.perf_counter() - start_time
    print(f"Streaming processing completed in {streaming_time:.4f}s")
    print(f"Memory usage: Processed {processed_jurisdictions} jurisdiction groups without loading all documents")
    
    # 4. Functional Programming Patterns
    print("\n4. Functional Programming Analysis Patterns")
    
    pipeline = FunctionalDataPipeline()
    
    # Analyze citation networks
    sample_citations = citations[:1000]  # Use subset for demo
    citation_network = pipeline.create_citation_network(sample_citations)
    
    network_stats = {
        'total_citations': len(citation_network),
        'avg_connections': sum(len(connections) for connections in citation_network.values()) / len(citation_network) if citation_network else 0,
        'most_connected': max(citation_network.items(), key=lambda x: len(x[1]))[0] if citation_network else None
    }
    print(f"Citation network stats: {network_stats}")
    
    # Analyze user journey patterns
    sample_events = events[:2000]  # Use subset for demo
    journey_analysis = pipeline.analyze_user_journey_patterns(sample_events)
    
    print(f"User journey analysis:")
    print(f"  Total users analyzed: {journey_analysis['total_users']}")
    print(f"  Average journey length: {journey_analysis['avg_journey_length']:.1f}")
    print(f"  Most common pattern: {journey_analysis['most_common_patterns'][0] if journey_analysis['most_common_patterns'] else 'None'}")
    
    # 5. Performance Benchmarking
    print("\n5. Performance Benchmarking and Optimization")
    
    benchmark = CollectionsPerformanceBenchmark()
    
    # Test Counter vs dict performance
    counter_results = benchmark.benchmark_counter_vs_dict(50000)
    print(f"Counter vs dict benchmark:")
    print(f"  Counter: {counter_results['counter_time']:.4f}s")
    print(f"  Dict: {dict_results['dict_time']:.4f}s") if 'dict_time' in counter_results else None
    print(f"  Counter is {counter_results['counter_faster_by']:.1f}x faster")
    
    # Test deque vs list performance
    deque_results = benchmark.benchmark_deque_vs_list(10000)
    print(f"deque vs list benchmark (queue operations):")
    print(f"  deque: {deque_results['deque_time']:.4f}s")
    print(f"  list: {deque_results['list_time']:.4f}s")
    print(f"  deque is {deque_results['deque_faster_by']:.1f}x faster")
    
    # Test itertools vs loops performance
    itertools_results = benchmark.benchmark_itertools_vs_loops(25000)
    print(f"itertools vs loops benchmark:")
    print(f"  itertools chain: {itertools_results['itertools_time']:.4f}s")
    print(f"  manual loops: {itertools_results['loop_time']:.4f}s")
    print(f"  itertools is {itertools_results['itertools_faster_by']:.1f}x faster")
    
    print("\n=== All data processing optimization patterns successfully demonstrated ===")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run demonstration
    demonstrate_data_processing_optimization()
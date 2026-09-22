"""
Comprehensive Performance Profiling Tools for Enterprise Applications

This module demonstrates advanced profiling techniques for identifying and
analyzing performance bottlenecks in production Python applications like
those used at Lawstronaut (legal document processing) and Optimizely
(real-time personalization systems).

Key concepts covered:
- CPU profiling with cProfile and py-spy
- Memory profiling with memory_profiler and tracemalloc
- I/O performance analysis
- Production profiling strategies
- Performance hotspot identification

Author: Technical Interview Preparation Guide
"""

import cProfile
import pstats
import tracemalloc
import psutil
import time
import asyncio
import io
import sys
import functools
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from contextlib import contextmanager
from memory_profiler import profile as memory_profile
import threading
import queue
import json

# =============================================================================
# CPU PROFILING SYSTEM
# =============================================================================

@dataclass
class ProfileResult:
    """Structured profiling result data"""
    function_name: str
    call_count: int
    cumulative_time: float
    per_call_time: float
    total_time: float
    filename: str
    line_number: int

class CPUProfiler:
    """Advanced CPU profiling with detailed analysis"""
    
    def __init__(self):
        self.profiler = None
        self.profile_data = {}
        self.profiling_active = False
    
    @contextmanager
    def profile_context(self, description: str = ""):
        """Context manager for profiling code blocks"""
        profiler = cProfile.Profile()
        
        print(f"Starting profiling: {description}")
        start_time = time.time()
        
        profiler.enable()
        try:
            yield profiler
        finally:
            profiler.disable()
            
            duration = time.time() - start_time
            print(f"Profiling completed in {duration:.3f}s")
            
            # Analyze results
            self._analyze_profile_results(profiler, description)
    
    def _analyze_profile_results(self, profiler: cProfile.Profile, description: str):
        """Analyze and display profiling results"""
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        print(f"\n=== CPU Profile Results: {description} ===")
        print(s.getvalue())
        
        # Extract top functions for structured analysis
        stats.sort_stats('cumulative')
        top_functions = []
        
        for func, (call_count, _, cumulative_time, per_call_time, callers) in stats.stats.items():
            if len(top_functions) >= 10:  # Top 10 functions
                break
                
            filename, line_number, function_name = func
            
            top_functions.append(ProfileResult(
                function_name=function_name,
                call_count=call_count,
                cumulative_time=cumulative_time,
                per_call_time=per_call_time / call_count if call_count > 0 else 0,
                total_time=cumulative_time,
                filename=filename.split('/')[-1],  # Just filename
                line_number=line_number
            ))
        
        self.profile_data[description] = top_functions
        return top_functions
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator for profiling individual functions"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.profile_context(f"Function: {func.__name__}"):
                return func(*args, **kwargs)
        return wrapper
    
    def get_hotspots(self, threshold_percent: float = 5.0) -> List[ProfileResult]:
        """Identify performance hotspots across all profiles"""
        all_functions = {}
        
        for profile_name, functions in self.profile_data.items():
            for func_result in functions:
                key = f"{func_result.filename}:{func_result.function_name}"
                
                if key not in all_functions:
                    all_functions[key] = func_result
                else:
                    # Aggregate results from multiple profiles
                    existing = all_functions[key]
                    existing.call_count += func_result.call_count
                    existing.cumulative_time += func_result.cumulative_time
                    existing.total_time += func_result.total_time
        
        # Calculate total time across all functions
        total_time = sum(func.cumulative_time for func in all_functions.values())
        
        # Filter hotspots (functions taking more than threshold% of total time)
        hotspots = [
            func for func in all_functions.values()
            if (func.cumulative_time / total_time * 100) >= threshold_percent
        ]
        
        return sorted(hotspots, key=lambda x: x.cumulative_time, reverse=True)

# =============================================================================
# MEMORY PROFILING SYSTEM
# =============================================================================

class MemoryProfiler:
    """Advanced memory profiling and leak detection"""
    
    def __init__(self):
        self.baseline_memory = None
        self.memory_snapshots = []
        self.tracking_active = False
    
    @contextmanager
    def memory_tracking(self, description: str = ""):
        """Context manager for memory usage tracking"""
        if not self.tracking_active:
            tracemalloc.start()
            self.tracking_active = True
        
        # Take baseline snapshot
        snapshot_start = tracemalloc.take_snapshot()
        memory_start = psutil.Process().memory_info().rss
        
        print(f"Starting memory tracking: {description}")
        
        try:
            yield
        finally:
            # Take end snapshot
            snapshot_end = tracemalloc.take_snapshot()
            memory_end = psutil.Process().memory_info().rss
            
            memory_diff = (memory_end - memory_start) / 1024 / 1024  # MB
            
            print(f"Memory usage change: {memory_diff:+.2f} MB")
            
            # Analyze memory growth
            self._analyze_memory_growth(snapshot_start, snapshot_end, description)
    
    def _analyze_memory_growth(self, snapshot_start, snapshot_end, description: str):
        """Analyze memory allocation patterns"""
        top_stats = snapshot_end.compare_to(snapshot_start, 'lineno')
        
        print(f"\n=== Memory Growth Analysis: {description} ===")
        print("Top 10 memory allocations:")
        
        for index, stat in enumerate(top_stats[:10], 1):
            print(f"{index:2d}. {stat}")
    
    def memory_profile_function(self, func: Callable) -> Callable:
        """Decorator for memory profiling individual functions"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self.memory_tracking(f"Function: {func.__name__}"):
                return func(*args, **kwargs)
        return wrapper
    
    def detect_memory_leaks(self, iterations: int = 10) -> Dict[str, Any]:
        """Detect potential memory leaks through repeated operations"""
        if not self.tracking_active:
            tracemalloc.start()
            self.tracking_active = True
        
        memory_usage = []
        snapshots = []
        
        def sample_operation():
            # Simulate memory-intensive operation
            data = list(range(10000))
            processed = [x * 2 for x in data if x % 2 == 0]
            return processed
        
        for i in range(iterations):
            # Take snapshot before operation
            snapshot_before = tracemalloc.take_snapshot()
            memory_before = psutil.Process().memory_info().rss
            
            # Perform operation
            result = sample_operation()
            
            # Take snapshot after operation
            snapshot_after = tracemalloc.take_snapshot()
            memory_after = psutil.Process().memory_info().rss
            
            memory_usage.append({
                'iteration': i,
                'memory_before_mb': memory_before / 1024 / 1024,
                'memory_after_mb': memory_after / 1024 / 1024,
                'memory_diff_mb': (memory_after - memory_before) / 1024 / 1024
            })
            
            snapshots.append((snapshot_before, snapshot_after))
        
        # Analyze for memory leaks
        leak_analysis = self._analyze_leak_patterns(memory_usage, snapshots)
        
        return {
            'memory_usage_pattern': memory_usage,
            'leak_detected': leak_analysis['leak_detected'],
            'growth_rate_mb_per_iteration': leak_analysis['growth_rate'],
            'recommendations': leak_analysis['recommendations']
        }
    
    def _analyze_leak_patterns(self, memory_usage: List[Dict], snapshots: List[tuple]) -> Dict[str, Any]:
        """Analyze memory usage patterns for potential leaks"""
        if len(memory_usage) < 3:
            return {'leak_detected': False, 'growth_rate': 0, 'recommendations': []}
        
        # Calculate memory growth trend
        memory_diffs = [usage['memory_diff_mb'] for usage in memory_usage]
        avg_growth = sum(memory_diffs) / len(memory_diffs)
        
        # Check for consistent growth (potential leak indicator)
        leak_detected = avg_growth > 0.1  # Growing by more than 0.1 MB per iteration
        
        recommendations = []
        if leak_detected:
            recommendations.extend([
                "Investigate object lifecycle management",
                "Check for unclosed resources (files, connections)",
                "Review cache implementations for unbounded growth",
                "Analyze circular references preventing garbage collection"
            ])
        
        return {
            'leak_detected': leak_detected,
            'growth_rate': avg_growth,
            'recommendations': recommendations
        }

# =============================================================================
# I/O PERFORMANCE MONITORING
# =============================================================================

class IOPerformanceMonitor:
    """Monitor and analyze I/O performance patterns"""
    
    def __init__(self):
        self.io_stats = {
            'file_operations': [],
            'network_operations': [],
            'database_operations': []
        }
    
    @contextmanager
    def monitor_file_io(self, operation_name: str, file_path: str = ""):
        """Monitor file I/O operations"""
        io_counters_start = psutil.Process().io_counters()
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            io_counters_end = psutil.Process().io_counters()
            
            duration = (end_time - start_time) * 1000  # milliseconds
            bytes_read = io_counters_end.read_bytes - io_counters_start.read_bytes
            bytes_written = io_counters_end.write_bytes - io_counters_start.write_bytes
            
            io_stat = {
                'operation': operation_name,
                'file_path': file_path,
                'duration_ms': duration,
                'bytes_read': bytes_read,
                'bytes_written': bytes_written,
                'read_throughput_mbps': (bytes_read / (1024 * 1024)) / (duration / 1000) if duration > 0 else 0,
                'write_throughput_mbps': (bytes_written / (1024 * 1024)) / (duration / 1000) if duration > 0 else 0,
                'timestamp': time.time()
            }
            
            self.io_stats['file_operations'].append(io_stat)
            
            print(f"File I/O: {operation_name} completed in {duration:.2f}ms")
            print(f"  Read: {bytes_read} bytes ({io_stat['read_throughput_mbps']:.2f} MB/s)")
            print(f"  Write: {bytes_written} bytes ({io_stat['write_throughput_mbps']:.2f} MB/s)")
    
    @contextmanager
    def monitor_network_io(self, operation_name: str, endpoint: str = ""):
        """Monitor network I/O operations"""
        network_start = psutil.net_io_counters()
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            network_end = psutil.net_io_counters()
            
            duration = (end_time - start_time) * 1000  # milliseconds
            bytes_sent = network_end.bytes_sent - network_start.bytes_sent
            bytes_received = network_end.bytes_recv - network_start.bytes_recv
            
            network_stat = {
                'operation': operation_name,
                'endpoint': endpoint,
                'duration_ms': duration,
                'bytes_sent': bytes_sent,
                'bytes_received': bytes_received,
                'send_throughput_mbps': (bytes_sent / (1024 * 1024)) / (duration / 1000) if duration > 0 else 0,
                'receive_throughput_mbps': (bytes_received / (1024 * 1024)) / (duration / 1000) if duration > 0 else 0,
                'timestamp': time.time()
            }
            
            self.io_stats['network_operations'].append(network_stat)
            
            print(f"Network I/O: {operation_name} completed in {duration:.2f}ms")
            print(f"  Sent: {bytes_sent} bytes ({network_stat['send_throughput_mbps']:.2f} MB/s)")
            print(f"  Received: {bytes_received} bytes ({network_stat['receive_throughput_mbps']:.2f} MB/s)")
    
    def analyze_io_patterns(self) -> Dict[str, Any]:
        """Analyze I/O performance patterns and identify bottlenecks"""
        analysis = {
            'file_io_analysis': self._analyze_file_operations(),
            'network_io_analysis': self._analyze_network_operations(),
            'performance_recommendations': []
        }
        
        # Generate recommendations based on analysis
        file_analysis = analysis['file_io_analysis']
        if file_analysis['avg_duration_ms'] > 100:
            analysis['performance_recommendations'].append(
                "File I/O operations are slow (>100ms avg). Consider async I/O or caching."
            )
        
        if file_analysis['avg_throughput_mbps'] < 10:
            analysis['performance_recommendations'].append(
                "Low file I/O throughput detected. Check disk performance or use SSD storage."
            )
        
        network_analysis = analysis['network_io_analysis']
        if network_analysis['avg_duration_ms'] > 500:
            analysis['performance_recommendations'].append(
                "Network operations are slow (>500ms avg). Check network latency and connection pooling."
            )
        
        return analysis
    
    def _analyze_file_operations(self) -> Dict[str, Any]:
        """Analyze file I/O operation patterns"""
        ops = self.io_stats['file_operations']
        if not ops:
            return {'operation_count': 0}
        
        durations = [op['duration_ms'] for op in ops]
        throughputs = [op['read_throughput_mbps'] + op['write_throughput_mbps'] for op in ops]
        
        return {
            'operation_count': len(ops),
            'avg_duration_ms': sum(durations) / len(durations),
            'max_duration_ms': max(durations),
            'min_duration_ms': min(durations),
            'avg_throughput_mbps': sum(throughputs) / len(throughputs) if throughputs else 0,
            'total_bytes_processed': sum(op['bytes_read'] + op['bytes_written'] for op in ops)
        }
    
    def _analyze_network_operations(self) -> Dict[str, Any]:
        """Analyze network I/O operation patterns"""
        ops = self.io_stats['network_operations']
        if not ops:
            return {'operation_count': 0}
        
        durations = [op['duration_ms'] for op in ops]
        throughputs = [op['send_throughput_mbps'] + op['receive_throughput_mbps'] for op in ops]
        
        return {
            'operation_count': len(ops),
            'avg_duration_ms': sum(durations) / len(durations),
            'max_duration_ms': max(durations),
            'min_duration_ms': min(durations),
            'avg_throughput_mbps': sum(throughputs) / len(throughputs) if throughputs else 0,
            'total_bytes_transferred': sum(op['bytes_sent'] + op['bytes_received'] for op in ops)
        }

# =============================================================================
# PRODUCTION PROFILING SYSTEM
# =============================================================================

class ProductionProfiler:
    """Non-intrusive production profiling system"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.profiling_active = False
        self.profile_thread = None
        self.profile_queue = queue.Queue()
        self.system_metrics = []
    
    def start_continuous_profiling(self):
        """Start continuous system profiling in background"""
        if self.profiling_active:
            return
        
        self.profiling_active = True
        self.profile_thread = threading.Thread(target=self._continuous_profiling_worker)
        self.profile_thread.daemon = True
        self.profile_thread.start()
        
        print("Started continuous profiling")
    
    def stop_continuous_profiling(self):
        """Stop continuous profiling"""
        self.profiling_active = False
        if self.profile_thread:
            self.profile_thread.join()
        
        print("Stopped continuous profiling")
    
    def _continuous_profiling_worker(self):
        """Background worker for collecting system metrics"""
        while self.profiling_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                network_io = psutil.net_io_counters()
                
                process = psutil.Process()
                process_memory = process.memory_info()
                process_cpu = process.cpu_percent()
                
                metrics = {
                    'timestamp': time.time(),
                    'system': {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available_gb': memory.available / (1024**3),
                        'disk_read_bytes': disk_io.read_bytes if disk_io else 0,
                        'disk_write_bytes': disk_io.write_bytes if disk_io else 0,
                        'network_bytes_sent': network_io.bytes_sent if network_io else 0,
                        'network_bytes_recv': network_io.bytes_recv if network_io else 0
                    },
                    'process': {
                        'cpu_percent': process_cpu,
                        'memory_rss_mb': process_memory.rss / (1024**2),
                        'memory_vms_mb': process_memory.vms / (1024**2),
                        'num_threads': process.num_threads(),
                        'open_files': len(process.open_files())
                    }
                }
                
                self.system_metrics.append(metrics)
                
                # Keep only recent metrics (last 1000 samples)
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-1000:]
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"Error in profiling worker: {e}")
                time.sleep(self.sampling_interval)
    
    def get_performance_summary(self, last_minutes: int = 5) -> Dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = time.time() - (last_minutes * 60)
        recent_metrics = [m for m in self.system_metrics if m['timestamp'] > cutoff_time]
        
        if not recent_metrics:
            return {'error': 'No recent metrics available'}
        
        # Calculate averages and trends
        cpu_values = [m['system']['cpu_percent'] for m in recent_metrics]
        memory_values = [m['process']['memory_rss_mb'] for m in recent_metrics]
        
        return {
            'time_period_minutes': last_minutes,
            'sample_count': len(recent_metrics),
            'cpu_utilization': {
                'avg_percent': sum(cpu_values) / len(cpu_values),
                'max_percent': max(cpu_values),
                'min_percent': min(cpu_values)
            },
            'memory_usage': {
                'avg_mb': sum(memory_values) / len(memory_values),
                'max_mb': max(memory_values),
                'min_mb': min(memory_values),
                'trend': 'increasing' if memory_values[-1] > memory_values[0] else 'stable'
            },
            'performance_health': self._assess_performance_health(recent_metrics)
        }
    
    def _assess_performance_health(self, metrics: List[Dict]) -> str:
        """Assess overall performance health"""
        if not metrics:
            return 'unknown'
        
        latest = metrics[-1]
        
        # Check various health indicators
        cpu_health = latest['system']['cpu_percent'] < 80
        memory_health = latest['system']['memory_percent'] < 85
        process_memory_stable = all(
            abs(m['process']['memory_rss_mb'] - metrics[0]['process']['memory_rss_mb']) < 100
            for m in metrics[-10:]  # Last 10 samples
        )
        
        if cpu_health and memory_health and process_memory_stable:
            return 'healthy'
        elif cpu_health and memory_health:
            return 'warning'
        else:
            return 'critical'

# =============================================================================
# DEMONSTRATION AND TESTING
# =============================================================================

def simulate_legal_document_processing(document_count: int = 1000) -> List[Dict]:
    """Simulate CPU-intensive legal document processing for Lawstronaut"""
    documents = []
    
    for i in range(document_count):
        # Simulate document processing with various operations
        doc_content = f"Legal document {i} with provisions and clauses " * 50
        
        # Text processing simulation
        words = doc_content.split()
        word_count = len(words)
        
        # Simulate legal term extraction (CPU intensive)
        legal_terms = []
        for word in words:
            if len(word) > 6:  # Simulate complex legal term detection
                legal_terms.append(word.upper())
        
        # Simulate document classification
        classification = "contract" if i % 3 == 0 else "regulation" if i % 3 == 1 else "judgment"
        
        documents.append({
            'id': i,
            'word_count': word_count,
            'legal_terms': legal_terms,
            'classification': classification,
            'processing_complexity': len(legal_terms) * word_count
        })
    
    return documents

def simulate_personalization_data_processing(user_count: int = 10000) -> Dict[str, Any]:
    """Simulate memory-intensive personalization processing for Optimizely"""
    users = {}
    
    for user_id in range(user_count):
        # Simulate user profile with behavioral data
        user_profile = {
            'user_id': user_id,
            'demographics': {
                'age_group': f"group_{user_id % 5}",
                'location': f"region_{user_id % 10}",
                'interests': [f"interest_{j}" for j in range(user_id % 20)]
            },
            'behavior_history': [
                {
                    'action': f"action_{j}",
                    'timestamp': time.time() - (j * 3600),
                    'value': user_id + j
                }
                for j in range(50)  # 50 actions per user
            ],
            'recommendations': [f"item_{k}" for k in range(user_id % 100)]
        }
        
        users[user_id] = user_profile
    
    # Simulate recommendation engine processing
    recommendation_matrix = {}
    for user_id, profile in users.items():
        scores = {}
        for other_user_id in range(min(100, len(users))):  # Compare with 100 other users
            if other_user_id != user_id:
                # Simulate similarity calculation
                similarity = abs(hash(str(profile['demographics'])) - hash(str(users[other_user_id]['demographics']))) % 100
                scores[other_user_id] = similarity
        
        recommendation_matrix[user_id] = scores
    
    return {
        'user_profiles': users,
        'recommendation_matrix': recommendation_matrix,
        'total_users': len(users),
        'total_comparisons': sum(len(scores) for scores in recommendation_matrix.values())
    }

async def demonstrate_profiling_tools():
    """Comprehensive demonstration of all profiling tools"""
    
    print("=== Enterprise Performance Profiling Tools Demo ===\n")
    
    # Initialize profilers
    cpu_profiler = CPUProfiler()
    memory_profiler = MemoryProfiler()
    io_monitor = IOPerformanceMonitor()
    production_profiler = ProductionProfiler(sampling_interval=0.5)
    
    # Start production profiling
    production_profiler.start_continuous_profiling()
    
    print("1. CPU Profiling - Legal Document Processing")
    print("-" * 50)
    
    # CPU profiling example
    @cpu_profiler.profile_function
    def process_legal_documents():
        return simulate_legal_document_processing(500)
    
    with cpu_profiler.profile_context("Legal Document Processing"):
        documents = process_legal_documents()
        
        print(f"Processed {len(documents)} legal documents")
    
    print("\n2. Memory Profiling - Personalization Engine")
    print("-" * 50)
    
    # Memory profiling example
    @memory_profiler.memory_profile_function
    def process_personalization_data():
        return simulate_personalization_data_processing(1000)
    
    with memory_profiler.memory_tracking("Personalization Data Processing"):
        personalization_data = process_personalization_data()
        
        print(f"Processed personalization data for {personalization_data['total_users']} users")
    
    print("\n3. I/O Performance Monitoring")
    print("-" * 50)
    
    # File I/O monitoring
    with io_monitor.monitor_file_io("Large File Write", "/tmp/test_file.txt"):
        with open("/tmp/test_file.txt", "w") as f:
            for i in range(10000):
                f.write(f"Line {i}: Some legal document content here\n")
    
    with io_monitor.monitor_file_io("Large File Read", "/tmp/test_file.txt"):
        with open("/tmp/test_file.txt", "r") as f:
            content = f.read()
    
    # Network I/O monitoring (simulated)
    with io_monitor.monitor_network_io("API Request", "https://api.example.com"):
        # Simulate network request
        await asyncio.sleep(0.1)  # Simulate network delay
    
    print("\n4. Memory Leak Detection")
    print("-" * 50)
    
    leak_analysis = memory_profiler.detect_memory_leaks(iterations=5)
    print(f"Memory leak detected: {leak_analysis['leak_detected']}")
    print(f"Growth rate: {leak_analysis['growth_rate_mb_per_iteration']:.3f} MB/iteration")
    
    if leak_analysis['recommendations']:
        print("Recommendations:")
        for rec in leak_analysis['recommendations']:
            print(f"  - {rec}")
    
    print("\n5. Performance Hotspot Analysis")
    print("-" * 50)
    
    hotspots = cpu_profiler.get_hotspots(threshold_percent=2.0)
    print(f"Found {len(hotspots)} performance hotspots:")
    
    for i, hotspot in enumerate(hotspots[:5], 1):
        print(f"{i}. {hotspot.function_name} ({hotspot.filename})")
        print(f"   Cumulative time: {hotspot.cumulative_time:.3f}s")
        print(f"   Call count: {hotspot.call_count}")
        print(f"   Per-call time: {hotspot.per_call_time:.6f}s")
    
    print("\n6. I/O Performance Analysis")
    print("-" * 50)
    
    io_analysis = io_monitor.analyze_io_patterns()
    
    file_stats = io_analysis['file_io_analysis']
    print(f"File I/O Operations: {file_stats['operation_count']}")
    print(f"Average duration: {file_stats.get('avg_duration_ms', 0):.2f}ms")
    print(f"Average throughput: {file_stats.get('avg_throughput_mbps', 0):.2f} MB/s")
    
    if io_analysis['performance_recommendations']:
        print("\nPerformance Recommendations:")
        for rec in io_analysis['performance_recommendations']:
            print(f"  - {rec}")
    
    print("\n7. Production Performance Summary")
    print("-" * 50)
    
    # Let production profiler collect some data
    await asyncio.sleep(2)
    
    perf_summary = production_profiler.get_performance_summary(last_minutes=1)
    
    if 'error' not in perf_summary:
        cpu_stats = perf_summary['cpu_utilization']
        memory_stats = perf_summary['memory_usage']
        
        print(f"Sample count: {perf_summary['sample_count']}")
        print(f"CPU utilization: {cpu_stats['avg_percent']:.1f}% (max: {cpu_stats['max_percent']:.1f}%)")
        print(f"Memory usage: {memory_stats['avg_mb']:.1f}MB (trend: {memory_stats['trend']})")
        print(f"Performance health: {perf_summary['performance_health']}")
    
    # Stop production profiler
    production_profiler.stop_continuous_profiling()
    
    print("\n=== Profiling Demo Completed ===")
    print("\nKey Insights:")
    print("- CPU profiling identified performance hotspots in document processing")
    print("- Memory profiling tracked allocation patterns and detected potential leaks")
    print("- I/O monitoring revealed file and network performance characteristics")
    print("- Production profiling provided continuous system health monitoring")
    
    # Clean up
    import os
    if os.path.exists("/tmp/test_file.txt"):
        os.remove("/tmp/test_file.txt")

if __name__ == "__main__":
    # Run the comprehensive profiling demonstration
    asyncio.run(demonstrate_profiling_tools())
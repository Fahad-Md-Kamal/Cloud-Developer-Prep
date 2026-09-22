import asyncio
import threading
import multiprocessing
import time
import requests
import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Callable
import psutil

class ConcurrencyBenchmark:
    """Benchmark different concurrency approaches for various workloads"""
    
    @staticmethod
    def cpu_intensive_task(n: int) -> int:
        """Simulate CPU-intensive work (calculate prime numbers)"""
        count = 0
        for i in range(2, n):
            for j in range(2, int(i ** 0.5) + 1):
                if i % j == 0:
                    break
            else:
                count += 1
        return count
    
    @staticmethod
    def io_intensive_task(url: str) -> dict:
        """Simulate I/O-intensive work (HTTP request)"""
        try:
            response = requests.get(url, timeout=10)
            return {'url': url, 'status': response.status_code, 'size': len(response.content)}
        except Exception as e:
            return {'url': url, 'error': str(e)}
    
    @staticmethod
    async def async_io_task(session: aiohttp.ClientSession, url: str) -> dict:
        """Async version of I/O task"""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                content = await response.read()
                return {'url': url, 'status': response.status, 'size': len(content)}
        except Exception as e:
            return {'url': url, 'error': str(e)}

# Benchmark I/O-bound workload
async def benchmark_io_bound():
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2", 
        # ... more URLs
    ] * 10  # 20 total requests
    
    print("=== I/O-Bound Workload Benchmark ===")
    
    # 1. Sequential (baseline)
    start = time.time()
    results_sequential = []
    for url in urls:
        result = ConcurrencyBenchmark.io_intensive_task(url)
        results_sequential.append(result)
    sequential_time = time.time() - start
    print(f"Sequential: {sequential_time:.2f}s")
    
    # 2. Threading
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results_threading = list(executor.map(ConcurrencyBenchmark.io_intensive_task, urls))
    threading_time = time.time() - start
    print(f"Threading: {threading_time:.2f}s ({sequential_time/threading_time:.1f}x faster)")
    
    # 3. AsyncIO
    start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [ConcurrencyBenchmark.async_io_task(session, url) for url in urls]
        results_asyncio = await asyncio.gather(*tasks, return_exceptions=True)
    asyncio_time = time.time() - start
    print(f"AsyncIO: {asyncio_time:.2f}s ({sequential_time/asyncio_time:.1f}x faster)")
    
    return {
        'sequential': sequential_time,
        'threading': threading_time,
        'asyncio': asyncio_time
    }

# Benchmark CPU-bound workload
def benchmark_cpu_bound():
    tasks = [10000] * 8  # 8 CPU-intensive tasks
    
    print("\n=== CPU-Bound Workload Benchmark ===")
    
    # 1. Sequential
    start = time.time()
    results_sequential = []
    for task in tasks:
        result = ConcurrencyBenchmark.cpu_intensive_task(task)
        results_sequential.append(result)
    sequential_time = time.time() - start
    print(f"Sequential: {sequential_time:.2f}s")
    
    # 2. Threading (GIL limitation)
    start = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results_threading = list(executor.map(ConcurrencyBenchmark.cpu_intensive_task, tasks))
    threading_time = time.time() - start
    print(f"Threading: {threading_time:.2f}s ({sequential_time/threading_time:.1f}x speedup)")
    
    # 3. Multiprocessing
    start = time.time()
    with ProcessPoolExecutor(max_workers=psutil.cpu_count()) as executor:
        results_multiprocessing = list(executor.map(ConcurrencyBenchmark.cpu_intensive_task, tasks))
    multiprocessing_time = time.time() - start
    print(f"Multiprocessing: {multiprocessing_time:.2f}s ({sequential_time/multiprocessing_time:.1f}x speedup)")
    
    return {
        'sequential': sequential_time,
        'threading': threading_time,
        'multiprocessing': multiprocessing_time
    }

# Decision helper function
def choose_concurrency_approach(workload_type: str, io_ratio: float = 0.8) -> str:
    """
    Help choose the right concurrency approach based on workload characteristics
    
    Args:
        workload_type: 'io_bound', 'cpu_bound', or 'mixed'
        io_ratio: For mixed workloads, ratio of I/O to CPU work (0.0 = all CPU, 1.0 = all I/O)
    """
    
    if workload_type == 'io_bound' or (workload_type == 'mixed' and io_ratio > 0.7):
        return """
        🚀 **Recommended: AsyncIO**
        
        Best for:
        - Web crawling and API calls
        - Database queries with connection pooling
        - File I/O operations
        - Network operations
        
        Benefits:
        - Highest throughput for I/O-bound tasks
        - Lower memory overhead than threading
        - Excellent for handling many concurrent connections
        - Built-in support for timeouts and cancellation
        
        Example use cases:
        - Legal document crawling (Lawstronaut)
        - API request handling (Optimizely)
        """
    
    elif workload_type == 'cpu_bound' or (workload_type == 'mixed' and io_ratio < 0.3):
        return """
        ⚡ **Recommended: Multiprocessing**
        
        Best for:
        - Data processing and transformation
        - Mathematical computations
        - Document parsing and analysis
        - Machine learning model inference
        
        Benefits:
        - True parallelism (bypasses GIL)
        - Scales with CPU cores
        - Fault isolation between processes
        
        Example use cases:
        - Legal document text analysis
        - AI model serving
        """
    
    else:  # Mixed workload
        return """
        🔄 **Recommended: Hybrid Approach**
        
        Use AsyncIO for I/O operations and ProcessPoolExecutor for CPU tasks
        """

# Usage example
async def main():
    # Run benchmarks to understand performance characteristics
    await benchmark_io_bound()
    benchmark_cpu_bound()
    
    # Get recommendation
    print(choose_concurrency_approach('mixed', io_ratio=0.6))

if __name__ == "__main__":
    asyncio.run(main())

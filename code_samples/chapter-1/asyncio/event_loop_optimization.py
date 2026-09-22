import asyncio
import uvloop  # High-performance event loop
import time
import aiohttp
from typing import List, Optional, Callable, Any
import logging

# Custom event loop with performance monitoring
class MonitoredEventLoop:
    def __init__(self, use_uvloop: bool = True):
        if use_uvloop:
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                logging.warning("uvloop not available, using default event loop")
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Performance monitoring
        self.task_count = 0
        self.start_time = time.time()
        self.completed_tasks = 0
    
    async def run_with_monitoring(self, coro):
        """Run coroutine with performance monitoring"""
        start = time.time()
        self.task_count += 1
        
        try:
            result = await coro
            self.completed_tasks += 1
            duration = time.time() - start
            
            if duration > 1.0:  # Log slow operations
                logging.warning(f"Slow operation detected: {duration:.2f}s")
            
            return result
        except Exception as e:
            logging.error(f"Task failed after {time.time() - start:.2f}s: {e}")
            raise
    
    def get_stats(self) -> dict:
        runtime = time.time() - self.start_time
        return {
            "total_tasks": self.task_count,
            "completed_tasks": self.completed_tasks,
            "runtime_seconds": runtime,
            "tasks_per_second": self.completed_tasks / runtime if runtime > 0 else 0,
            "pending_tasks": len(asyncio.all_tasks(self.loop))
        }

# High-performance web crawler with event loop optimization
class OptimizedWebCrawler:
    def __init__(self, max_concurrent: int = 100, request_delay: float = 0.1):
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Connection pooling for better performance
        self.connector = aiohttp.TCPConnector(
            limit=200,  # Total connection pool size
            limit_per_host=20,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=aiohttp.ClientTimeout(total=30, connect=10),
            headers={'User-Agent': 'Legal-Crawler/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self.connector.close()
    
    async def fetch_url(self, url: str) -> Optional[dict]:
        """Fetch a single URL with rate limiting and error handling"""
        
        async with self.semaphore:  # Limit concurrent requests
            await asyncio.sleep(self.request_delay)  # Rate limiting
            
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return {
                            'url': url,
                            'status': response.status,
                            'content': content,
                            'headers': dict(response.headers),
                            'size': len(content)
                        }
                    else:
                        logging.warning(f"HTTP {response.status} for {url}")
                        return {'url': url, 'status': response.status, 'error': 'HTTP error'}
                        
            except asyncio.TimeoutError:
                logging.error(f"Timeout for {url}")
                return {'url': url, 'error': 'timeout'}
            except Exception as e:
                logging.error(f"Error fetching {url}: {e}")
                return {'url': url, 'error': str(e)}
    
    async def crawl_urls(self, urls: List[str]) -> List[dict]:
        """Crawl multiple URLs concurrently with optimal performance"""
        
        # Create tasks for all URLs
        tasks = [self.fetch_url(url) for url in urls]
        
        # Execute with monitoring
        monitor = MonitoredEventLoop()
        
        # Use asyncio.gather for optimal task scheduling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                valid_results.append(result)
            elif isinstance(result, Exception):
                logging.error(f"Task exception: {result}")
        
        # Log performance stats
        stats = monitor.get_stats()
        logging.info(f"Crawling completed: {stats}")
        
        return valid_results

# Usage example for legal document crawling
async def crawl_legal_sites():
    legal_urls = [
        "https://www.legislation.gov.uk/ukpga/2023/1",
        "https://www.legislation.gov.uk/ukpga/2023/2",
        "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R0001",
        # ... more URLs
    ]
    
    async with OptimizedWebCrawler(max_concurrent=50, request_delay=0.05) as crawler:
        results = await crawler.crawl_urls(legal_urls)
        
        print(f"Successfully crawled {len(results)} documents")
        
        # Process results
        for result in results:
            if 'content' in result:
                print(f"Fetched {result['url']}: {result['size']} bytes")

# Run with optimized event loop
if __name__ == "__main__":
    # Set up high-performance event loop
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("Using uvloop for better performance")
    except ImportError:
        print("Using default event loop")
    
    asyncio.run(crawl_legal_sites())

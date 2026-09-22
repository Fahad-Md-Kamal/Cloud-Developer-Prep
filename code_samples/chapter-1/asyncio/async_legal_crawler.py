import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional, AsyncGenerator
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import logging
from pathlib import Path
import json
import os

@dataclass
class CrawlResult:
    url: str
    status_code: int
    content: str = ""
    links: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    error: Optional[str] = None
    fetch_time: float = 0.0

@dataclass 
class CrawlerConfig:
    max_concurrent: int = 50
    max_depth: int = 3
    delay: float = 0.1
    timeout: int = 30
    max_pages: int = 1000
    allowed_domains: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    custom_headers: Dict[str, str] = field(default_factory=dict)

class AsyncLegalCrawler:
    """Production-grade async web crawler for legal documents"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[CrawlResult] = []
        
        # Rate limiting
        self.semaphore = asyncio.Semaphore(config.max_concurrent)
        
        # Statistics
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'total_links_found': 0,
            'start_time': 0,
            'bytes_downloaded': 0
        }
    
    async def __aenter__(self):
        # Optimized connector for high-performance crawling
        connector = aiohttp.TCPConnector(
            limit=200,
            limit_per_host=50,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        headers = {
            'User-Agent': 'LegalCrawler/1.0 (+https://example.com/bot)',
            **self.config.custom_headers
        }
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        )
        
        self.stats['start_time'] = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def should_crawl(self, url: str) -> bool:
        """Determine if URL should be crawled based on rules"""
        parsed = urlparse(url)
        
        # Check allowed domains
        if self.config.allowed_domains:
            if not any(domain in parsed.netloc for domain in self.config.allowed_domains):
                return False
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if pattern in url:
                return False
        
        # Already visited
        if url in self.visited:
            return False
        
        # Max pages limit
        if len(self.visited) >= self.config.max_pages:
            return False
        
        return True
    
    async def fetch_page(self, url: str) -> CrawlResult:
        """Fetch a single page with comprehensive error handling"""
        
        async with self.semaphore:
            # Rate limiting
            await asyncio.sleep(self.config.delay)
            
            start_time = time.time()
            result = CrawlResult(url=url, status_code=0)
            
            try:
                async with self.session.get(url) as response:
                    result.status_code = response.status
                    result.fetch_time = time.time() - start_time
                    
                    if response.status == 200:
                        content = await response.text()
                        result.content = content
                        
                        # Update statistics
                        self.stats['bytes_downloaded'] += len(content.encode('utf-8'))
                        self.stats['pages_crawled'] += 1
                        
                        # Extract metadata
                        result.metadata = {
                            'content_type': response.headers.get('content-type', ''),
                            'content_length': len(content),
                            'server': response.headers.get('server', ''),
                            'last_modified': response.headers.get('last-modified', '')
                        }
                        
                        # Extract links
                        result.links = await self.extract_links(content, url)
                        self.stats['total_links_found'] += len(result.links)
                        
                    else:
                        result.error = f"HTTP {response.status}"
                        self.stats['pages_failed'] += 1
                        
            except asyncio.TimeoutError:
                result.error = "Request timeout"
                result.fetch_time = time.time() - start_time
                self.stats['pages_failed'] += 1
                
            except Exception as e:
                result.error = str(e)
                result.fetch_time = time.time() - start_time
                self.stats['pages_failed'] += 1
            
            return result
    
    async def extract_links(self, content: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Basic URL cleaning
                if absolute_url.startswith(('http://', 'https://')):
                    # Remove fragments
                    if '#' in absolute_url:
                        absolute_url = absolute_url.split('#')[0]
                    
                    links.append(absolute_url)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logging.error(f"Error extracting links from {base_url}: {e}")
            return []
    
    async def crawl(self, start_urls: List[str]) -> AsyncGenerator[CrawlResult, None]:
        """Main crawling method with breadth-first search"""
        
        # Initialize queue with start URLs
        current_level = [(url, 0) for url in start_urls]
        
        while current_level and len(self.visited) < self.config.max_pages:
            next_level = []
            
            # Process current level concurrently
            tasks = []
            for url, depth in current_level:
                if self.should_crawl(url):
                    self.visited.add(url)
                    tasks.append(self.fetch_page(url))
            
            if not tasks:
                break
            
            # Execute all tasks for current level
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and collect links for next level
            for result in results:
                if isinstance(result, CrawlResult):
                    yield result
                    
                    # Add links for next level if within depth limit
                    if result.links and depth < self.config.max_depth:
                        for link in result.links:
                            if self.should_crawl(link):
                                next_level.append((link, depth + 1))
                
                elif isinstance(result, Exception):
                    logging.error(f"Task failed: {result}")
            
            current_level = next_level
            
            # Log progress
            if len(self.visited) % 50 == 0:
                runtime = time.time() - self.stats['start_time']
                rate = len(self.visited) / runtime if runtime > 0 else 0
                logging.info(f"Crawled {len(self.visited)} pages ({rate:.1f} pages/sec)")
    
    def get_statistics(self) -> Dict:
        """Get comprehensive crawling statistics"""
        runtime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'pages_per_second': self.stats['pages_crawled'] / runtime if runtime > 0 else 0,
            'mb_downloaded': self.stats['bytes_downloaded'] / (1024 * 1024),
            'success_rate': (
                self.stats['pages_crawled'] / 
                (self.stats['pages_crawled'] + self.stats['pages_failed'])
                if (self.stats['pages_crawled'] + self.stats['pages_failed']) > 0 else 0
            )
        }

def is_legal_document(result: CrawlResult) -> bool:
    """Identify if a crawled page contains legal content"""
    content_lower = result.content.lower()
    
    # Legal document indicators
    legal_indicators = [
        'act of parliament',
        'statutory instrument',
        'regulation',
        'directive',
        'whereas',
        'article',
        'section',
        'subsection',
        'paragraph',
        'subparagraph'
    ]
    
    # Count legal indicators
    indicator_count = sum(1 for indicator in legal_indicators if indicator in content_lower)
    
    # Minimum threshold for legal content
    return indicator_count >= 3

# Usage example: Crawling legal websites
async def crawl_legal_documents():
    """Example usage for legal document crawling"""
    
    config = CrawlerConfig(
        max_concurrent=30,
        max_depth=2,
        delay=0.05,  # 50ms delay
        max_pages=500,
        allowed_domains=[
            'legislation.gov.uk',
            'eur-lex.europa.eu',
            'congress.gov'
        ],
        exclude_patterns=[
            '/search',
            '/api/',
            '.pdf',
            '.doc',
            'mailto:'
        ],
        custom_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1'
        }
    )
    
    start_urls = [
        'https://www.legislation.gov.uk/ukpga/2023',
        'https://eur-lex.europa.eu/browse/directories/legislation.html'
    ]
    
    # Results storage
    all_results = []
    legal_documents = []
    
    async with AsyncLegalCrawler(config) as crawler:
        print("Starting legal document crawl...")
        
        async for result in crawler.crawl(start_urls):
            all_results.append(result)
            
            # Filter for legal documents
            if result.status_code == 200 and is_legal_document(result):
                legal_documents.append(result)
                print(f"Found legal document: {result.url}")
        
        # Get final statistics
        stats = crawler.get_statistics()
        print(f"\n=== Crawling Statistics ===")
        print(f"Pages crawled: {stats['pages_crawled']}")
        print(f"Success rate: {stats['success_rate']:.1%}")
        print(f"Download speed: {stats['pages_per_second']:.1f} pages/sec")
        print(f"Data downloaded: {stats['mb_downloaded']:.1f} MB")
        print(f"Legal documents found: {len(legal_documents)}")
    
    return legal_documents

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(crawl_legal_documents())

from typing import Protocol, runtime_checkable, List
from abc import ABC, abstractmethod
import aiohttp
from bs4 import BeautifulSoup
import json

# Protocol for crawlable content
@runtime_checkable
class Crawlable(Protocol):
    url: str
    
    async def fetch(self) -> str:
        ...
    
    def extract_links(self, content: str) -> List[str]:
        ...
    
    def should_follow(self, url: str) -> bool:
        ...

# Different implementations can satisfy the protocol
class LegalSiteCrawler:
    def __init__(self, url: str, allowed_domains: List[str]):
        self.url = url
        self.allowed_domains = allowed_domains
    
    async def fetch(self) -> str:
        # Implementation for legal site crawling
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                return await response.text()
    
    def extract_links(self, content: str) -> List[str]:
        # BeautifulSoup implementation
        soup = BeautifulSoup(content, 'html.parser')
        return [a.get('href') for a in soup.find_all('a', href=True)]
    
    def should_follow(self, url: str) -> bool:
        return any(domain in url for domain in self.allowed_domains)

class APIEndpointCrawler:
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
    
    async def fetch(self) -> str:
        # API-specific implementation
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(self.url) as response:
                return await response.text()
    
    def extract_links(self, content: str) -> List[str]:
        # JSON API link extraction
        data = json.loads(content)
        return data.get('links', [])
    
    def should_follow(self, url: str) -> bool:
        return url.startswith('https://api.')

# Generic crawler function that works with any Crawlable
async def crawl_content(crawler: Crawlable, max_depth: int = 3) -> List[str]:
    visited = set()
    to_visit = [crawler.url]
    all_content = []
    
    for depth in range(max_depth):
        if not to_visit:
            break
            
        current_urls = to_visit.copy()
        to_visit.clear()
        
        for url in current_urls:
            if url in visited:
                continue
                
            visited.add(url)
            
            # Create new crawler instance for this URL
            if isinstance(crawler, LegalSiteCrawler):
                current_crawler = LegalSiteCrawler(url, crawler.allowed_domains)
            else:
                current_crawler = APIEndpointCrawler(url, crawler.api_key)
            
            try:
                content = await current_crawler.fetch()
                all_content.append(content)
                
                # Extract and filter new links
                links = current_crawler.extract_links(content)
                new_links = [link for link in links 
                           if current_crawler.should_follow(link) and link not in visited]
                to_visit.extend(new_links)
                
            except Exception as e:
                print(f"Error crawling {url}: {e}")
    
    return all_content

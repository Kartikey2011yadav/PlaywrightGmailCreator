"""
Advanced Proxy Management System for Gmail Creator

This module provides comprehensive proxy management with health checks,
rotation, validation, and support for multiple proxy types.
"""

import asyncio
import aiohttp
import random
import time
import json
import logging
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse
import requests

# Optional imports with fallbacks
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False
    UserAgent = None

logger = logging.getLogger(__name__)


class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    TESTING = "testing"


@dataclass
class ProxyInfo:
    """Data class for proxy information"""
    host: str
    port: int
    proxy_type: ProxyType
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    status: ProxyStatus = ProxyStatus.INACTIVE
    last_checked: Optional[float] = None
    response_time: Optional[float] = None
    success_rate: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    
    @property
    def url(self) -> str:
        """Get proxy URL"""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"
    
    @property
    def dict_format(self) -> dict:
        """Get proxy in dictionary format for requests/aiohttp"""
        proxy_url = self.url
        if self.proxy_type in [ProxyType.HTTP, ProxyType.HTTPS]:
            return {"http": proxy_url, "https": proxy_url}
        else:
            return {"http": proxy_url, "https": proxy_url}


class ProxyManager:
    """Advanced proxy management system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.proxies: List[ProxyInfo] = []
        self.active_proxies: List[ProxyInfo] = []
        self.current_proxy_index = 0
        self.config_file = config_file
        self.user_agent = UserAgent() if FAKE_USERAGENT_AVAILABLE else None
        self.health_check_interval = 300  # 5 minutes
        self.max_failures = 3
        self.timeout = 10
        self.test_urls = [
            "http://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "http://ip-api.com/json"
        ]
        
    def add_proxy(self, host: str, port: int, proxy_type: ProxyType, 
                  username: str = None, password: str = None, 
                  country: str = None, city: str = None) -> None:
        """Add a proxy to the manager"""
        proxy = ProxyInfo(
            host=host,
            port=port,
            proxy_type=proxy_type,
            username=username,
            password=password,
            country=country,
            city=city
        )
        self.proxies.append(proxy)
        logger.info(f"Added proxy: {proxy.host}:{proxy.port}")
    
    def load_proxies_from_file(self, file_path: str) -> None:
        """Load proxies from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                proxy_data = json.load(f)
                
            for proxy_info in proxy_data:
                self.add_proxy(
                    host=proxy_info['host'],
                    port=proxy_info['port'],
                    proxy_type=ProxyType(proxy_info['type']),
                    username=proxy_info.get('username'),
                    password=proxy_info.get('password'),
                    country=proxy_info.get('country'),
                    city=proxy_info.get('city')
                )
            logger.info(f"Loaded {len(proxy_data)} proxies from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load proxies from file: {e}")
    
    def load_proxies_from_list(self, proxy_list: List[str]) -> None:
        """Load proxies from a list of strings in format 'host:port' or 'host:port:username:password'"""
        for proxy_string in proxy_list:
            parts = proxy_string.strip().split(':')
            if len(parts) >= 2:
                host = parts[0]
                port = int(parts[1])
                username = parts[2] if len(parts) > 2 else None
                password = parts[3] if len(parts) > 3 else None
                proxy_type = ProxyType.HTTP  # Default to HTTP
                
                self.add_proxy(host, port, proxy_type, username, password)
    
    async def test_proxy(self, proxy: ProxyInfo) -> bool:
        """Test if a proxy is working"""
        proxy.status = ProxyStatus.TESTING
        proxy.last_checked = time.time()
        
        test_url = random.choice(self.test_urls)
        
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': self.user_agent.random if self.user_agent else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            ) as session:
                
                start_time = time.time()
                
                async with session.get(
                    test_url,
                    proxy=proxy.url
                ) as response:
                    if response.status == 200:
                        proxy.response_time = time.time() - start_time
                        proxy.status = ProxyStatus.ACTIVE
                        proxy.total_requests += 1
                        
                        # Update success rate
                        proxy.success_rate = ((proxy.total_requests - proxy.failed_requests) / 
                                            proxy.total_requests) * 100
                        
                        logger.info(f"Proxy {proxy.host}:{proxy.port} is working "
                                  f"(Response time: {proxy.response_time:.2f}s)")
                        return True
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            proxy.status = ProxyStatus.FAILED
            proxy.failed_requests += 1
            proxy.total_requests += 1
            
            if proxy.total_requests > 0:
                proxy.success_rate = ((proxy.total_requests - proxy.failed_requests) / 
                                    proxy.total_requests) * 100
            
            logger.warning(f"Proxy {proxy.host}:{proxy.port} failed: {e}")
            return False
    
    async def test_all_proxies(self) -> None:
        """Test all proxies concurrently"""
        logger.info("Testing all proxies...")
        tasks = [self.test_proxy(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_count = sum(1 for proxy in self.proxies if proxy.status == ProxyStatus.ACTIVE)
        self.active_proxies = [proxy for proxy in self.proxies if proxy.status == ProxyStatus.ACTIVE]
        
        logger.info(f"Proxy testing complete. {active_count}/{len(self.proxies)} proxies are active")
    
    def get_random_proxy(self) -> Optional[ProxyInfo]:
        """Get a random active proxy"""
        if not self.active_proxies:
            logger.warning("No active proxies available")
            return None
        
        return random.choice(self.active_proxies)
    
    def get_next_proxy(self) -> Optional[ProxyInfo]:
        """Get next proxy in rotation"""
        if not self.active_proxies:
            logger.warning("No active proxies available")
            return None
        
        proxy = self.active_proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.active_proxies)
        return proxy
    
    def get_best_proxy(self) -> Optional[ProxyInfo]:
        """Get proxy with best success rate and response time"""
        if not self.active_proxies:
            return None
        
        # Sort by success rate (descending) then by response time (ascending)
        best_proxy = max(
            self.active_proxies,
            key=lambda p: (p.success_rate, -p.response_time if p.response_time else 0)
        )
        return best_proxy
    
    def get_proxy_by_country(self, country: str) -> Optional[ProxyInfo]:
        """Get a proxy from specific country"""
        country_proxies = [p for p in self.active_proxies 
                          if p.country and p.country.lower() == country.lower()]
        
        if not country_proxies:
            logger.warning(f"No active proxies found for country: {country}")
            return None
        
        return random.choice(country_proxies)
    
    def mark_proxy_failed(self, proxy: ProxyInfo) -> None:
        """Mark a proxy as failed and remove from active list"""
        proxy.failed_requests += 1
        proxy.total_requests += 1
        
        if proxy.failed_requests >= self.max_failures:
            proxy.status = ProxyStatus.FAILED
            if proxy in self.active_proxies:
                self.active_proxies.remove(proxy)
                logger.warning(f"Proxy {proxy.host}:{proxy.port} marked as failed and removed")
    
    def get_proxy_stats(self) -> Dict:
        """Get statistics about proxies"""
        total = len(self.proxies)
        active = len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE])
        failed = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        inactive = len([p for p in self.proxies if p.status == ProxyStatus.INACTIVE])
        
        avg_response_time = 0
        if active > 0:
            response_times = [p.response_time for p in self.active_proxies if p.response_time]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total": total,
            "active": active,
            "failed": failed,
            "inactive": inactive,
            "average_response_time": avg_response_time,
            "success_rate": (active / total * 100) if total > 0 else 0
        }
    
    def save_proxy_stats(self, file_path: str) -> None:
        """Save proxy statistics to file"""
        stats = self.get_proxy_stats()
        proxy_details = []
        
        for proxy in self.proxies:
            proxy_details.append({
                "host": proxy.host,
                "port": proxy.port,
                "type": proxy.proxy_type.value,
                "status": proxy.status.value,
                "success_rate": proxy.success_rate,
                "response_time": proxy.response_time,
                "total_requests": proxy.total_requests,
                "failed_requests": proxy.failed_requests,
                "country": proxy.country,
                "city": proxy.city
            })
        
        data = {
            "statistics": stats,
            "proxies": proxy_details,
            "timestamp": time.time()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Proxy statistics saved to {file_path}")


class FreeProxyFetcher:
    """Fetch free proxies from various sources"""
    
    @staticmethod
    async def fetch_from_proxy_list() -> List[str]:
        """Fetch proxies from free proxy APIs"""
        proxies = []
        
        # Example sources (you can add more)
        sources = [
            "https://www.proxy-list.download/api/v1/get?type=http",
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all"
        ]
        
        for source in sources:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            proxy_list = content.strip().split('\n')
                            proxies.extend(proxy_list)
            except Exception as e:
                logger.warning(f"Failed to fetch from {source}: {e}")
        
        return proxies
    
    @staticmethod
    async def fetch_and_setup_manager() -> ProxyManager:
        """Fetch free proxies and set up a ProxyManager"""
        manager = ProxyManager()
        
        logger.info("Fetching free proxies...")
        free_proxies = await FreeProxyFetcher.fetch_from_proxy_list()
        
        if free_proxies:
            manager.load_proxies_from_list(free_proxies)
            await manager.test_all_proxies()
        
        return manager


# Example usage and testing
async def main():
    """Example usage of ProxyManager"""
    
    # Create proxy manager
    manager = ProxyManager()
    
    # Add some example proxies (replace with real ones)
    example_proxies = [
        "proxy1.example.com:8080",
        "proxy2.example.com:3128",
        "proxy3.example.com:8888:username:password"
    ]
    
    manager.load_proxies_from_list(example_proxies)
    
    # Or fetch free proxies
    # manager = await FreeProxyFetcher.fetch_and_setup_manager()
    
    # Test all proxies
    await manager.test_all_proxies()
    
    # Get proxy statistics
    stats = manager.get_proxy_stats()
    print(f"Proxy Stats: {stats}")
    
    # Get different types of proxies
    random_proxy = manager.get_random_proxy()
    best_proxy = manager.get_best_proxy()
    
    if random_proxy:
        print(f"Random proxy: {random_proxy.url}")
    
    if best_proxy:
        print(f"Best proxy: {best_proxy.url} (Success rate: {best_proxy.success_rate}%)")


if __name__ == "__main__":
    asyncio.run(main())
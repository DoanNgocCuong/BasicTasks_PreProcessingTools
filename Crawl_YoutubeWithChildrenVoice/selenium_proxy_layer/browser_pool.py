#!/usr/bin/env python3
"""
Browser pool management for Selenium proxy layer.

Manages multiple browser instances with different proxy configurations
for IP rotation and load balancing.
"""

import time
import random
import threading
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.common.exceptions import WebDriverException
import logging

from .config import ProxyConfig


@dataclass
class BrowserInstance:
    """Represents a single browser instance in the pool."""
    driver: webdriver.Remote
    proxy_url: Optional[str]
    is_healthy: bool = True
    last_used: float = 0.0
    request_count: int = 0
    failure_count: int = 0
    created_at: float = 0.0
    current_ip: Optional[str] = None


class BrowserPool:
    """Manages a pool of browser instances for proxy rotation."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize browser pool with configuration."""
        self.config = config
        self.browsers: List[BrowserInstance] = []
        self.current_index = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize browsers
        self._initialize_browsers()
    
    def _initialize_browsers(self) -> None:
        """Initialize browser instances with proxy configurations."""
        self.logger.info(f"Initializing {self.config.browser_pool_size} browser instances...")
        
        for i in range(self.config.browser_pool_size):
            proxy_url = self._get_proxy_for_browser(i)
            try:
                driver = self._create_browser(proxy_url)
                browser = BrowserInstance(
                    driver=driver,
                    proxy_url=proxy_url,
                    created_at=time.time()
                )
                
                # Test the browser and get current IP
                if self._test_browser(browser):
                    self.browsers.append(browser)
                    self.logger.info(f"Browser {i+1} initialized successfully with IP: {browser.current_ip}")
                else:
                    self.logger.warning(f"Browser {i+1} failed initial test, skipping")
                    driver.quit()
                    
            except Exception as e:
                self.logger.error(f"Failed to initialize browser {i+1}: {e}")
        
        if not self.browsers:
            raise RuntimeError("Failed to initialize any browsers")
        
        self.logger.info(f"Successfully initialized {len(self.browsers)} browsers")
    
    def _get_proxy_for_browser(self, browser_index: int) -> Optional[str]:
        """Get proxy URL for a specific browser index."""
        if not self.config.proxy_list:
            return None
        
        # Distribute proxies across browsers
        proxy_index = browser_index % len(self.config.proxy_list)
        return self.config.proxy_list[proxy_index]
    
    def _create_browser(self, proxy_url: Optional[str]) -> webdriver.Remote:
        """Create a browser instance with the specified proxy."""
        if self.config.browser_type.lower() == 'chrome':
            return self._create_chrome_browser(proxy_url)
        elif self.config.browser_type.lower() == 'firefox':
            return self._create_firefox_browser(proxy_url)
        elif self.config.browser_type.lower() == 'edge':
            return self._create_edge_browser(proxy_url)
        else:
            raise ValueError(f"Unsupported browser type: {self.config.browser_type}")
    
    def _create_chrome_browser(self, proxy_url: Optional[str]) -> webdriver.Chrome:
        """Create a Chrome browser instance."""
        options = ChromeOptions()
        
        if self.config.headless:
            options.add_argument('--headless')
        
        # Performance optimizations
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        
        # Random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        if proxy_url:
            options.add_argument(f'--proxy-server={proxy_url}')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        driver.implicitly_wait(self.config.implicit_wait)
        
        return driver
    
    def _create_firefox_browser(self, proxy_url: Optional[str]) -> webdriver.Firefox:
        """Create a Firefox browser instance."""
        options = FirefoxOptions()
        
        if self.config.headless:
            options.add_argument('--headless')
        
        if proxy_url:
            # Parse proxy URL
            if '://' in proxy_url:
                protocol, host_port = proxy_url.split('://', 1)
            else:
                protocol, host_port = 'http', proxy_url
            
            if ':' in host_port:
                host, port = host_port.split(':', 1)
                port = int(port)
            else:
                host, port = host_port, 8080
            
            # Set proxy preferences
            options.set_preference('network.proxy.type', 1)
            options.set_preference('network.proxy.http', host)
            options.set_preference('network.proxy.http_port', port)
            options.set_preference('network.proxy.ssl', host)
            options.set_preference('network.proxy.ssl_port', port)
        
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        driver.implicitly_wait(self.config.implicit_wait)
        
        return driver
    
    def _create_edge_browser(self, proxy_url: Optional[str]) -> webdriver.Edge:
        """Create an Edge browser instance."""
        options = EdgeOptions()
        
        if self.config.headless:
            options.add_argument('--headless')
        
        # Same optimizations as Chrome
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        if proxy_url:
            options.add_argument(f'--proxy-server={proxy_url}')
        
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        driver.implicitly_wait(self.config.implicit_wait)
        
        return driver
    
    def _test_browser(self, browser: BrowserInstance) -> bool:
        """Test if a browser instance is working and get its IP."""
        try:
            browser.driver.get(self.config.health_check_url)
            
            # Try to get IP from response
            try:
                page_source = browser.driver.page_source
                if 'origin' in page_source:
                    import json
                    import re
                    # Extract JSON from page
                    json_match = re.search(r'\{[^}]*"origin"[^}]*\}', page_source)
                    if json_match:
                        ip_data = json.loads(json_match.group())
                        browser.current_ip = ip_data.get('origin', 'Unknown')
                else:
                    browser.current_ip = 'Unknown'
            except Exception:
                browser.current_ip = 'Unknown'
            
            browser.is_healthy = True
            return True
            
        except Exception as e:
            self.logger.error(f"Browser test failed: {e}")
            browser.is_healthy = False
            return False
    
    def get_next_browser(self) -> Optional[BrowserInstance]:
        """Get the next available browser instance."""
        with self.lock:
            if not self.browsers:
                return None
            
            # Filter healthy browsers
            healthy_browsers = [b for b in self.browsers if b.is_healthy]
            if not healthy_browsers:
                self.logger.warning("No healthy browsers available")
                return None
            
            # Round-robin selection
            browser = healthy_browsers[self.current_index % len(healthy_browsers)]
            self.current_index = (self.current_index + 1) % len(healthy_browsers)
            
            # Update usage statistics
            browser.last_used = time.time()
            browser.request_count += 1
            
            return browser
    
    def mark_browser_failed(self, browser: BrowserInstance) -> None:
        """Mark a browser as failed."""
        with self.lock:
            browser.failure_count += 1
            browser.is_healthy = False
            
            # If too many failures, restart the browser
            if browser.failure_count >= 3:
                self.logger.warning(f"Browser with IP {browser.current_ip} failed too many times, restarting...")
                self._restart_browser(browser)
    
    def _restart_browser(self, browser: BrowserInstance) -> None:
        """Restart a failed browser instance."""
        try:
            # Close old browser
            browser.driver.quit()
            
            # Create new browser
            new_driver = self._create_browser(browser.proxy_url)
            browser.driver = new_driver
            browser.failure_count = 0
            browser.created_at = time.time()
            
            # Test new browser
            if self._test_browser(browser):
                self.logger.info(f"Browser restarted successfully with IP: {browser.current_ip}")
            else:
                self.logger.error("Failed to restart browser")
                
        except Exception as e:
            self.logger.error(f"Error restarting browser: {e}")
            browser.is_healthy = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all browsers."""
        with self.lock:
            healthy_count = sum(1 for b in self.browsers if b.is_healthy)
            
            browser_stats = []
            for i, browser in enumerate(self.browsers):
                browser_stats.append({
                    'index': i,
                    'proxy_url': browser.proxy_url,
                    'current_ip': browser.current_ip,
                    'is_healthy': browser.is_healthy,
                    'request_count': browser.request_count,
                    'failure_count': browser.failure_count,
                    'uptime': time.time() - browser.created_at
                })
            
            return {
                'total_browsers': len(self.browsers),
                'healthy_browsers': healthy_count,
                'unhealthy_browsers': len(self.browsers) - healthy_count,
                'browser_stats': browser_stats
            }
    
    def close_all(self) -> None:
        """Close all browser instances."""
        with self.lock:
            for browser in self.browsers:
                try:
                    browser.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error closing browser: {e}")
            
            self.browsers.clear()
            self.logger.info("All browsers closed")

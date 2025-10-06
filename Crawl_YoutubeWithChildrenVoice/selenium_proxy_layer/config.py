#!/usr/bin/env python3
"""
Configuration management for Selenium proxy layer.

Handles proxy settings, browser configurations, and rotation strategies.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class ProxyConfig:
    """Configuration for the Selenium proxy layer."""
    
    # Local proxy server settings
    local_proxy_host: str = '127.0.0.1'
    local_proxy_port: int = 8080
    
    # Browser settings
    browser_type: str = 'chrome'  # 'chrome', 'firefox', 'edge'
    browser_pool_size: int = 3
    headless: bool = True
    
    # Proxy list (external proxies to route through)
    proxy_list: List[str] = field(default_factory=list)
    
    # Rotation settings
    rotation_strategy: str = 'request_based'  # 'time_based', 'request_based', 'failure_based'
    rotation_interval: int = 10  # requests or seconds depending on strategy
    
    # Health monitoring
    health_check_interval: int = 60  # seconds
    health_check_timeout: int = 10   # seconds
    health_check_url: str = 'https://httpbin.org/ip'
    
    # Browser options
    browser_timeout: int = 30
    page_load_timeout: int = 20
    implicit_wait: int = 10
    
    # Request handling
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 30
    
    # Logging
    log_level: str = 'INFO'
    log_requests: bool = True
    log_responses: bool = False
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ProxyConfig':
        """Load configuration from JSON file."""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config file
            default_config = cls()
            default_config.save_to_file(config_path)
            return default_config
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
            
        return cls(**config_dict)
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to JSON file."""
        config_dict = {
            'local_proxy_host': self.local_proxy_host,
            'local_proxy_port': self.local_proxy_port,
            'browser_type': self.browser_type,
            'browser_pool_size': self.browser_pool_size,
            'headless': self.headless,
            'proxy_list': self.proxy_list,
            'rotation_strategy': self.rotation_strategy,
            'rotation_interval': self.rotation_interval,
            'health_check_interval': self.health_check_interval,
            'health_check_timeout': self.health_check_timeout,
            'health_check_url': self.health_check_url,
            'browser_timeout': self.browser_timeout,
            'page_load_timeout': self.page_load_timeout,
            'implicit_wait': self.implicit_wait,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'request_timeout': self.request_timeout,
            'log_level': self.log_level,
            'log_requests': self.log_requests,
            'log_responses': self.log_responses
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    def get_proxy_url(self) -> str:
        """Get the local proxy URL."""
        return f'http://{self.local_proxy_host}:{self.local_proxy_port}'

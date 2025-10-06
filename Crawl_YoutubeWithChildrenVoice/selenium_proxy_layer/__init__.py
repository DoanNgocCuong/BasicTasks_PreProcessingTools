#!/usr/bin/env python3
"""
Selenium Proxy Layer Package

Provides IP rotation capabilities through Selenium-managed proxy browsers
for transparent HTTP request interception and routing.

Author: Assistant
"""

from .proxy_manager import SeleniumProxyManager
from .http_proxy_server import HTTPProxyServer
from .browser_pool import BrowserPool
from .rotation_strategies import RotationStrategy, TimeBasedRotation, RequestBasedRotation
from .config import ProxyConfig
from .health_monitor import ProxyHealthMonitor

def start_proxy_system(config_file=None):
    """Start the complete Selenium proxy system.
    
    Args:
        config_file: Optional path to config file (uses default if None)
        
    Returns:
        SeleniumProxyManager: Running proxy manager instance
    """
    proxy_manager = SeleniumProxyManager(config_file)
    proxy_manager.start()
    return proxy_manager

__all__ = [
    'SeleniumProxyManager',
    'HTTPProxyServer', 
    'BrowserPool',
    'RotationStrategy',
    'TimeBasedRotation',
    'RequestBasedRotation',
    'ProxyConfig',
    'ProxyHealthMonitor',
    'start_proxy_system'
]

__version__ = '1.0.0'

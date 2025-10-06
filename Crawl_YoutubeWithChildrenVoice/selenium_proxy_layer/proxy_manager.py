#!/usr/bin/env python3
"""
Selenium Proxy Manager - Main orchestration class.

Provides high-level interface for managing the entire Selenium proxy layer,
including server lifecycle, configuration, and monitoring.
"""

import time
import signal
import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .config import ProxyConfig
from .http_proxy_server import HTTPProxyServer


class SeleniumProxyManager:
    """Main manager for the Selenium proxy layer."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the proxy manager."""
        # Load configuration
        if config_file is None:
            config_file = str(Path(__file__).parent / "proxy_config.json")
        
        self.config = ProxyConfig.from_file(config_file)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize proxy server
        self.proxy_server: Optional[HTTPProxyServer] = None
        self.is_running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Selenium Proxy Manager initialized")
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('selenium_proxy.log')
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def start(self) -> None:
        """Start the proxy server and all components."""
        if self.is_running:
            self.logger.warning("Proxy manager is already running")
            return
        
        try:
            self.logger.info("Starting Selenium Proxy Manager...")
            
            # Validate configuration
            self._validate_config()
            
            # Create and start proxy server
            self.proxy_server = HTTPProxyServer(self.config)
            self.proxy_server.start()
            
            self.is_running = True
            
            self.logger.info("\n" + "="*60)
            self.logger.info("🚀 SELENIUM PROXY LAYER STARTED SUCCESSFULLY")
            self.logger.info("="*60)
            self.logger.info(f"📡 Proxy URL: {self.config.get_proxy_url()}")
            self.logger.info(f"🌐 Browser Pool: {self.config.browser_pool_size} {self.config.browser_type} instances")
            self.logger.info(f"🔄 Rotation: {self.config.rotation_strategy} every {self.config.rotation_interval}")
            self.logger.info(f"📊 Admin Interface: {self.config.get_proxy_url()}/_proxy_admin/status")
            self.logger.info("="*60)
            
            # Print usage instructions
            self._print_usage_instructions()
            
        except Exception as e:
            self.logger.error(f"Failed to start proxy manager: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the proxy server and cleanup resources."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping Selenium Proxy Manager...")
        
        try:
            if self.proxy_server:
                self.proxy_server.stop()
            
            self.is_running = False
            self.logger.info("Selenium Proxy Manager stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def _validate_config(self) -> None:
        """Validate configuration before starting."""
        if self.config.browser_pool_size <= 0:
            raise ValueError("Browser pool size must be greater than 0")
        
        if self.config.local_proxy_port <= 0 or self.config.local_proxy_port > 65535:
            raise ValueError("Invalid proxy port number")
        
        # Validate browser type
        supported_browsers = ['chrome', 'firefox', 'edge']
        if self.config.browser_type.lower() not in supported_browsers:
            raise ValueError(f"Unsupported browser type: {self.config.browser_type}")
        
        # Validate rotation strategy
        supported_strategies = ['time_based', 'request_based', 'failure_based', 'hybrid']
        if self.config.rotation_strategy.lower() not in supported_strategies:
            raise ValueError(f"Unsupported rotation strategy: {self.config.rotation_strategy}")
        
        self.logger.info("Configuration validation passed")
    
    def _print_usage_instructions(self) -> None:
        """Print usage instructions for the proxy."""
        proxy_url = self.config.get_proxy_url()
        
        print("\n📋 USAGE INSTRUCTIONS:")
        print("="*50)
        print("\n1. 🔧 Set environment variables:")
        print(f"   export HTTP_PROXY={proxy_url}")
        print(f"   export HTTPS_PROXY={proxy_url}")
        print("\n2. 🐍 Or configure in Python:")
        print("   import os")
        print(f"   os.environ['HTTP_PROXY'] = '{proxy_url}'")
        print(f"   os.environ['HTTPS_PROXY'] = '{proxy_url}'")
        print("\n3. 📊 Monitor status:")
        print(f"   curl {proxy_url}/_proxy_admin/status")
        print(f"   curl {proxy_url}/_proxy_admin/health")
        print("\n4. 🔄 Force rotation:")
        print(f"   curl {proxy_url}/_proxy_admin/force_rotation")
        print("\n⚠️  Your YouTube crawler will now automatically use rotating IPs!")
        print("="*50)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        if not self.proxy_server:
            return {
                'manager_status': 'not_started',
                'is_running': False
            }
        
        return {
            'manager_status': 'running' if self.is_running else 'stopped',
            'is_running': self.is_running,
            'config': {
                'proxy_url': self.config.get_proxy_url(),
                'browser_type': self.config.browser_type,
                'browser_pool_size': self.config.browser_pool_size,
                'rotation_strategy': self.config.rotation_strategy,
                'rotation_interval': self.config.rotation_interval
            },
            'proxy_server': self.proxy_server.get_status() if self.proxy_server else None
        }
    
    def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal or manual stop."""
        try:
            while self.is_running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
            self.stop()
    
    def run_forever(self) -> None:
        """Start the proxy and run until interrupted."""
        try:
            self.start()
            self.wait_for_shutdown()
        finally:
            self.stop()


def main():
    """Main entry point for standalone proxy server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Selenium Proxy Layer')
    parser.add_argument('--config', '-c', type=str, help='Configuration file path')
    parser.add_argument('--port', '-p', type=int, help='Proxy port (overrides config)')
    parser.add_argument('--browsers', '-b', type=int, help='Number of browsers (overrides config)')
    
    args = parser.parse_args()
    
    try:
        # Create manager
        manager = SeleniumProxyManager(config_file=args.config)
        
        # Override config if command line arguments provided
        if args.port:
            manager.config.local_proxy_port = args.port
        if args.browsers:
            manager.config.browser_pool_size = args.browsers
        
        # Run proxy server
        manager.run_forever()
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Integration helpers for YouTube crawler.

Provides utilities to easily integrate the Selenium proxy layer
with the existing YouTube crawler without code changes.
"""

import os
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path

from .proxy_manager import SeleniumProxyManager


class ProxyIntegration:
    """Helper class for integrating proxy layer with YouTube crawler."""
    
    def __init__(self, auto_start: bool = True, config_file: Optional[str] = None):
        """Initialize proxy integration."""
        self.manager: Optional[SeleniumProxyManager] = None
        self.auto_start = auto_start
        self.config_file = config_file
        
        if auto_start:
            self.start_proxy_layer()
    
    def start_proxy_layer(self) -> bool:
        """Start the proxy layer and configure environment."""
        try:
            print("🚀 Starting Selenium proxy layer for IP rotation...")
            
            # Create and start proxy manager
            self.manager = SeleniumProxyManager(config_file=self.config_file)
            self.manager.start()
            
            # Configure environment variables for automatic proxy usage
            proxy_url = self.manager.config.get_proxy_url()
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            
            print(f"✅ Proxy layer started successfully!")
            print(f"🔗 Proxy URL: {proxy_url}")
            print(f"🌐 All HTTP requests will now use rotating IPs")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start proxy layer: {e}")
            print("⚠️  Continuing without proxy (using original IP)")
            return False
    
    def stop_proxy_layer(self) -> None:
        """Stop the proxy layer and cleanup."""
        if self.manager:
            print("⏹️  Stopping proxy layer...")
            self.manager.stop()
            
            # Remove environment variables
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            
            print("✅ Proxy layer stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get proxy layer status."""
        if not self.manager:
            return {'status': 'not_started', 'is_running': False}
        
        return self.manager.get_status()
    
    def is_running(self) -> bool:
        """Check if proxy layer is running."""
        return self.manager is not None and self.manager.is_running
    
    def __enter__(self):
        """Context manager entry."""
        if not self.is_running():
            self.start_proxy_layer()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_proxy_layer()


def enable_proxy_for_crawler(config_file: Optional[str] = None) -> ProxyIntegration:
    """Simple function to enable proxy layer for the crawler."""
    return ProxyIntegration(auto_start=True, config_file=config_file)


def run_crawler_with_proxy(crawler_function, *args, **kwargs):
    """Run a crawler function with proxy layer enabled."""
    with enable_proxy_for_crawler() as proxy:
        if proxy.is_running():
            print("🔄 Running crawler with IP rotation enabled")
        else:
            print("⚠️  Running crawler without proxy (original IP)")
        
        return crawler_function(*args, **kwargs)


def create_crawler_startup_script():
    """Create a startup script that runs the crawler with proxy."""
    script_content = '''#!/usr/bin/env python3
"""
YouTube Crawler with Selenium Proxy Layer

Automatically starts the proxy layer and runs the crawler with IP rotation.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from selenium_proxy_layer.integration import run_crawler_with_proxy
from youtube_video_crawler import main as crawler_main


def main():
    """Main function that runs crawler with proxy."""
    print("🎯 YouTube Crawler with IP Rotation")
    print("="*50)
    
    try:
        # Run crawler with proxy layer
        run_crawler_with_proxy(crawler_main)
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawler interrupted by user")
    except Exception as e:
        print(f"❌ Crawler error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
    
    script_path = Path(__file__).parent.parent / "run_crawler_with_proxy.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Created startup script: {script_path}")
    print("🚀 Run your crawler with: python run_crawler_with_proxy.py")
    
    return script_path


if __name__ == "__main__":
    # Create the startup script when this module is run directly
    create_crawler_startup_script()

#!/usr/bin/env python3
"""
Simple launcher for the Selenium Proxy Layer.

Provides an easy way to start and stop the proxy server.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from selenium_proxy_layer import SeleniumProxyManager


def main():
    """Main launcher function."""
    print("🚀 Starting Selenium Proxy Layer...")
    print("📋 This will create a local proxy server that routes requests through rotating IPs")
    print("⏳ Please wait while browsers are initialized...\n")
    
    try:
        # Create and start proxy manager
        manager = SeleniumProxyManager()
        manager.start()
        
        print("\n✅ Proxy layer is running!")
        print("🔗 Configure your applications to use the proxy URL shown above")
        print("⌨️  Press Ctrl+C to stop the proxy server\n")
        
        # Wait for shutdown
        manager.wait_for_shutdown()
        
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down proxy server...")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    print("👋 Proxy server stopped. Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

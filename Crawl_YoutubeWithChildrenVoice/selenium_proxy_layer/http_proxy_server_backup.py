#!/usr/bin/env python3
"""
HTTP Proxy Server for Selenium proxy layer.

Implements a local HTTP proxy server that intercepts requests and routes them
through the Selenium browser pool for IP rotation and anonymization.
"""

import socket
import threading
import time
import urllib.parse
import http.server
import socketserver
from typing import Dict, Optional, Any, Tuple
import logging
import json
import requests
from datetime import datetime

from .config import ProxyConfig
from .browser_pool import BrowserPool, BrowserInstance
from .rotation_strategies import create_rotation_strategy
from .health_monitor import ProxyHealthMonitor


class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles individual proxy requests."""
    
    def __init__(self, request, client_address, server):
        """Initialize request handler."""
        self.proxy_server = server
        super().__init__(request, client_address, server)
    
    def do_GET(self):
        """Handle GET requests."""
        self._handle_request('GET')
    
    def do_POST(self):
        """Handle POST requests."""
        self._handle_request('POST')
    
    def do_PUT(self):
        """Handle PUT requests."""
        self._handle_request('PUT')
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        self._handle_request('DELETE')
    
    def do_CONNECT(self):
        """Handle CONNECT requests for HTTPS tunneling."""
        try:
            # Parse the target host and port
            host, port = self.path.split(':')
            port = int(port)
            
            # Get a browser to handle the connection
            browser = self.proxy_server.get_next_browser()
            if not browser:
                self.send_error(503, "No healthy browsers available")
                return
            
            # For HTTPS, we need to tunnel the connection
            # This is a simplified implementation
            self.send_response(200, 'Connection established')
            self.end_headers()
            
            # Note: Full HTTPS tunneling would require more complex implementation
            # For now, we'll close the connection
            self.connection.close()
            
        except Exception as e:
            self.proxy_server.logger.error(f"CONNECT request failed: {e}")
            self.send_error(500, str(e))
    
    def _handle_request(self, method: str):
        """Handle HTTP requests by routing through browser pool."""
        try:
            # Check for special admin endpoints
            if self.path.startswith('/_proxy_admin/'):
                self._handle_admin_request()
                return
            
            # Get target URL
            target_url = self.path
            if not target_url.startswith('http'):
                # Construct full URL from headers
                host = self.headers.get('Host')
                if host:
                    scheme = 'https' if self.proxy_server.config.local_proxy_port == 443 else 'http'
                    target_url = f"{scheme}://{host}{self.path}"
                else:
                    self.send_error(400, "Invalid request URL")
                    return
            
            # Get request body for POST/PUT
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Route request through browser pool
            response = self.proxy_server.route_request(
                method=method,
                url=target_url,
                headers=dict(self.headers),
                body=request_body
            )
            
            if response:
                # Send response back to client
                self.send_response(response['status_code'])
                
                # Send headers
                for header, value in response.get('headers', {}).items():
                    if header.lower() not in ['connection', 'transfer-encoding']:
                        self.send_header(header, value)
                
                self.end_headers()
                
                # Send body
                if response.get('content'):
                    self.wfile.write(response['content'])
            else:
                self.send_error(503, "Service temporarily unavailable")
                
        except Exception as e:
            self.proxy_server.logger.error(f"Request handling error: {e}")
            self.send_error(500, str(e))
    
    def _handle_admin_request(self):
        """Handle administrative requests for monitoring and control."""
        if self.path == '/_proxy_admin/status':
            # Return status information
            status = self.proxy_server.get_status()
            self._send_json_response(status)
        
        elif self.path == '/_proxy_admin/health':
            # Return health information
            health = self.proxy_server.get_health_report()
            self._send_json_response(health)
        
        elif self.path == '/_proxy_admin/force_rotation':
            # Force browser rotation
            result = self.proxy_server.force_rotation()
            self._send_json_response({'rotated': result})
        
        elif self.path == '/_proxy_admin/test':
            # Test endpoint to verify proxy is working
            proxy_instance = getattr(self.server, 'proxy_server_instance', None)
            total_requests = proxy_instance.total_requests if proxy_instance else 0
            
            test_result = {
                'proxy_working': True,
                'timestamp': datetime.now().isoformat(),
                'total_requests_processed': total_requests,
                'message': 'Proxy is intercepting requests successfully!',
                'test_ip_check': 'Visit https://httpbin.org/ip through proxy to see current IP'
            }
            print(f"\n🧪 PROXY TEST REQUEST - Admin endpoint accessed")
            print(f"   Total requests processed so far: {total_requests}")
            self._send_json_response(test_result)
        
        else:
            self.send_error(404, "Admin endpoint not found")
    
    def _send_json_response(self, data: Dict):
        """Send JSON response."""
        response_json = json.dumps(data, indent=2, ensure_ascii=False)
        response_bytes = response_json.encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        proxy_instance = getattr(self.server, 'proxy_server_instance', None)
        if proxy_instance and proxy_instance.config.log_requests:
            proxy_instance.logger.info(f"{self.address_string()} - {format % args}")


class HTTPProxyServer:
    """Main HTTP proxy server that routes requests through Selenium browsers."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize the proxy server."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.browser_pool = BrowserPool(config)
        self.rotation_strategy = create_rotation_strategy(config)
        self.health_monitor = ProxyHealthMonitor(config, self.browser_pool)
        
        # Server state
        self.server: Optional[socketserver.TCPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        # Statistics
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        
        # Thread safety
        self.stats_lock = threading.Lock()
        
        self.logger.info(f"Proxy server initialized on {config.local_proxy_host}:{config.local_proxy_port}")
    
    def start(self) -> None:
        """Start the proxy server."""
        if self.is_running:
            self.logger.warning("Proxy server is already running")
            return
        
        try:
            # Create server
            self.server = socketserver.ThreadingTCPServer(
                (self.config.local_proxy_host, self.config.local_proxy_port),
                ProxyRequestHandler
            )
            
            # Allow address reuse
            self.server.allow_reuse_address = True
            
            # Store reference to this proxy server instance
            self.server.proxy_server_instance = self
            
            # Start server thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            # Start health monitoring
            self.health_monitor.start_monitoring()
            
            self.is_running = True
            self.start_time = time.time()
            
            self.logger.info(f"Proxy server started on {self.config.local_proxy_host}:{self.config.local_proxy_port}")
            self.logger.info(f"Browser pool initialized with {len(self.browser_pool.browsers)} browsers")
            self.logger.info(f"Rotation strategy: {self.rotation_strategy.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to start proxy server: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the proxy server."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping proxy server...")
        
        # Stop health monitoring
        self.health_monitor.stop_monitoring()
        
        # Stop server
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        # Wait for server thread
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
        
        # Close browsers
        self.browser_pool.close_all()
        
        self.is_running = False
        self.logger.info("Proxy server stopped")
    
    def get_next_browser(self) -> Optional[BrowserInstance]:
        """Get the next available browser instance."""
        # Check if rotation is needed
        if self.rotation_strategy.should_rotate():
            self.logger.info("Rotation strategy triggered browser switch")
        
        return self.browser_pool.get_next_browser()
    
    def route_request(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        """Route a request through the browser pool."""
        start_time = time.time()
        
        with self.stats_lock:
            self.total_requests += 1
            request_id = self.total_requests
        
        # Always log requests for visibility
        print(f"\n🔄 PROXY REQUEST #{request_id}:")
        print(f"   Method: {method}")
        print(f"   URL: {url[:80]}{'...' if len(url) > 80 else ''}")
        print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Get browser instance
            browser = self.get_next_browser()
            if not browser:
                print(f"❌ PROXY REQUEST #{request_id}: No healthy browsers available")
                self.logger.error("No healthy browsers available")
                return None
            
            print(f"   🌐 Using Browser IP: {browser.current_ip}")
            
            # Execute request through browser
            response = self._execute_browser_request(browser, method, url, headers, body)
            
            # Update statistics
            response_time = time.time() - start_time
            with self.stats_lock:
                self.total_response_time += response_time
                if response:
                    self.successful_requests += 1
                    self.rotation_strategy.on_request_complete(True)
                    print(f"   ✅ SUCCESS: {response.get('status_code', 'OK')} ({response_time:.2f}s)")
                else:
                    self.failed_requests += 1
                    self.rotation_strategy.on_request_failed()
                    self.browser_pool.mark_browser_failed(browser)
                    print(f"   ❌ FAILED: ({response_time:.2f}s)")
            
            # Show rotation info
            rotation_stats = self.rotation_strategy.get_stats()
            if 'request_count' in rotation_stats:
                remaining = rotation_stats.get('requests_until_rotation', 0)
                print(f"   🔄 Requests until rotation: {remaining}")
            
            return response
            
        except Exception as e:
            print(f"❌ PROXY REQUEST #{request_id}: Error - {str(e)[:50]}")
            self.logger.error(f"Request routing error: {e}")
            response_time = time.time() - start_time
            
            with self.stats_lock:
                self.failed_requests += 1
                self.total_response_time += response_time
            
            self.rotation_strategy.on_request_failed()
            return None
    
    def _execute_browser_request(self, browser: BrowserInstance, method: str, url: str, headers: Dict[str, str], body: Optional[bytes]) -> Optional[Dict[str, Any]]:
        """Execute a request through a specific browser instance."""
        try:
            # For simple GET requests, we can use Selenium directly
            if method == 'GET' and not body:
                browser.driver.get(url)
                
                # Get page source as response
                page_source = browser.driver.page_source
                
                return {
                    'status_code': 200,
                    'headers': {'Content-Type': 'text/html'},
                    'content': page_source.encode('utf-8')
                }
            
            else:
                # For complex requests, we need to use JavaScript execution
                # This is a simplified implementation
                script = f"""
                var xhr = new XMLHttpRequest();
                xhr.open('{method}', '{url}', false);
                """
                
                # Add headers
                for header, value in headers.items():
                    if header.lower() not in ['host', 'content-length']:
                        script += f"xhr.setRequestHeader('{header}', '{value}');\n"
                
                # Send request
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    script += f"xhr.send('{body_str}');\n"
                else:
                    script += "xhr.send();\n"
                
                script += "return {status: xhr.status, response: xhr.responseText};"
                
                result = browser.driver.execute_script(script)
                
                return {
                    'status_code': result.get('status', 500),
                    'headers': {'Content-Type': 'application/json'},
                    'content': result.get('response', '').encode('utf-8')
                }
                
        except Exception as e:
            self.logger.error(f"Browser request execution failed: {e}")
            return None
    
    def force_rotation(self) -> bool:
        """Force browser rotation."""
        try:
            # Reset rotation strategy counters to force rotation
            self.rotation_strategy._reset_counters()
            self.logger.info("Forced browser rotation")
            return True
        except Exception as e:
            self.logger.error(f"Failed to force rotation: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current server status."""
        with self.stats_lock:
            uptime = time.time() - self.start_time
            avg_response_time = self.total_response_time / max(1, self.total_requests)
            success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
            
            return {
                'server': {
                    'is_running': self.is_running,
                    'uptime_seconds': uptime,
                    'proxy_url': self.config.get_proxy_url(),
                    'start_time': datetime.fromtimestamp(self.start_time).isoformat()
                },
                'statistics': {
                    'total_requests': self.total_requests,
                    'successful_requests': self.successful_requests,
                    'failed_requests': self.failed_requests,
                    'success_rate_percent': success_rate,
                    'avg_response_time_seconds': avg_response_time
                },
                'browser_pool': self.browser_pool.get_health_status(),
                'rotation_strategy': self.rotation_strategy.get_stats()
            }
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        return {
            'server_status': self.get_status(),
            'health_monitor': self.health_monitor.get_health_report(),
            'summary': self.health_monitor.get_summary_status()
        }

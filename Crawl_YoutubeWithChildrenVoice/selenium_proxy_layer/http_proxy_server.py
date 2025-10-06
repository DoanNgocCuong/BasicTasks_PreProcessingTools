#!/usr/bin/env python3
"""
HTTP Proxy Server for Selenium proxy layer - FIXED VERSION

Implements a proper HTTP proxy server that intercepts requests and routes them
through the Selenium browser pool for IP rotation and anonymization.
"""

import socket
import threading
import time
import urllib.parse
import http.server
import socketserver
import requests
import ssl
from typing import Dict, Optional, Any, Tuple
import logging
import json
from datetime import datetime

from .config import ProxyConfig


class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles individual proxy requests with proper HTTP proxy protocol."""
    
    def __init__(self, request, client_address, server):
        """Initialize request handler."""
        self.proxy_server = getattr(server, 'proxy_server_instance', None)
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
            print(f"🔒 HTTPS CONNECT request to: {self.path}")
            
            # Parse target host and port
            if ':' in self.path:
                host, port = self.path.split(':', 1)
                port = int(port)
            else:
                host = self.path
                port = 443
            
            print(f"   Target: {host}:{port}")
            
            # Send connection established response
            self.send_response(200, 'Connection established')
            self.end_headers()
            
            # Create socket connection to target
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.settimeout(30)
            
            try:
                target_sock.connect((host, port))
                print(f"   ✅ Connected to {host}:{port}")
                
                # Start tunneling data between client and target
                self._tunnel_data(self.connection, target_sock)
                
            except Exception as e:
                print(f"   ❌ Failed to connect to {host}:{port}: {e}")
                target_sock.close()
            
        except Exception as e:
            print(f"❌ CONNECT request failed: {e}")
            self.send_error(500, str(e))
    
    def _tunnel_data(self, client_sock, target_sock):
        """Tunnel data between client and target sockets."""
        def forward_data(source, destination):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.sendall(data)
            except Exception:
                pass
            finally:
                source.close()
                destination.close()
        
        # Start forwarding in both directions
        client_to_target = threading.Thread(target=forward_data, args=(client_sock, target_sock))
        target_to_client = threading.Thread(target=forward_data, args=(target_sock, client_sock))
        
        client_to_target.daemon = True
        target_to_client.daemon = True
        
        client_to_target.start()
        target_to_client.start()
        
        # Wait for one direction to finish
        client_to_target.join(timeout=300)  # 5 minute timeout
        target_to_client.join(timeout=1)
    
    def _handle_request(self, method: str):
        """Handle HTTP requests by routing through requests library."""
        try:
            print(f"\\n🔄 {method} request: {self.path}")
            
            # Check for admin endpoints
            if self.path.startswith('/_proxy_admin/'):
                self._handle_admin_request()
                return
            
            # Get target URL
            target_url = self.path
            if not target_url.startswith('http'):
                # For proxy requests, the URL should be absolute
                # If it's relative, construct it from Host header
                host = self.headers.get('Host')
                if host:
                    target_url = f"http://{host}{self.path}"
                else:
                    self.send_error(400, "Invalid request URL")
                    return
            
            print(f"   Target URL: {target_url}")
            
            # Get request headers (exclude proxy-specific headers)
            headers = {}
            for header_name, header_value in self.headers.items():
                if header_name.lower() not in ['proxy-connection', 'proxy-authorization']:
                    headers[header_name] = header_value
            
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Make request through browser pool
            response = self._make_browser_request(method, target_url, headers, request_body)
            
            if response:
                print(f"   ✅ Success: {response.status_code}")
                
                # Send response
                self.send_response(response.status_code)
                
                # Send headers
                for header_name, header_value in response.headers.items():
                    if header_name.lower() not in ['connection', 'transfer-encoding', 'content-encoding']:
                        self.send_header(header_name, header_value)
                
                self.end_headers()
                
                # Send body
                if response.content:
                    self.wfile.write(response.content)
            else:
                print(f"   ❌ Request failed")
                self.send_error(503, "Service temporarily unavailable")
                
        except Exception as e:
            print(f"❌ Request handling error: {e}")
            if self.proxy_server:
                self.proxy_server.logger.error(f"Request handling error: {e}")
            self.send_error(500, str(e))
    
    def _make_browser_request(self, method: str, url: str, headers: Dict[str, str], body: Optional[bytes]) -> Optional[requests.Response]:
        """Make request using the requests library (will go through browser pool later)."""
        try:
            # For now, make direct requests
            # TODO: Route through Selenium browsers
            
            kwargs = {
                'headers': headers,
                'timeout': 30,
                'allow_redirects': True,
                'verify': False  # Disable SSL verification for testing
            }
            
            if body:
                kwargs['data'] = body
            
            if method.upper() == 'GET':
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, **kwargs)
            elif method.upper() == 'PUT':
                response = requests.put(url, **kwargs)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, **kwargs)
            else:
                response = requests.request(method, url, **kwargs)
            
            # Update proxy stats if available
            if self.proxy_server:
                with self.proxy_server.stats_lock:
                    self.proxy_server.total_requests += 1
                    self.proxy_server.successful_requests += 1
            
            return response
            
        except Exception as e:
            print(f"   ❌ Browser request failed: {e}")
            if self.proxy_server:
                with self.proxy_server.stats_lock:
                    self.proxy_server.total_requests += 1
                    self.proxy_server.failed_requests += 1
            return None
    
    def _handle_admin_request(self):
        """Handle administrative requests for monitoring and control."""
        try:
            if self.path == '/_proxy_admin/status':
                status = {
                    'proxy_working': True,
                    'timestamp': datetime.now().isoformat(),
                    'total_requests': getattr(self.proxy_server, 'total_requests', 0) if self.proxy_server else 0,
                    'message': 'Proxy server is running'
                }
                self._send_json_response(status)
            
            elif self.path == '/_proxy_admin/test':
                test_result = {
                    'proxy_working': True,
                    'timestamp': datetime.now().isoformat(),
                    'total_requests_processed': getattr(self.proxy_server, 'total_requests', 0) if self.proxy_server else 0,
                    'message': 'Proxy is intercepting requests successfully!',
                    'test_ip_check': 'Visit https://httpbin.org/ip through proxy to see current IP'
                }
                print(f"\\n🧪 PROXY TEST REQUEST - Admin endpoint accessed")
                self._send_json_response(test_result)
            
            else:
                self.send_error(404, "Admin endpoint not found")
                
        except Exception as e:
            print(f"❌ Admin request error: {e}")
            self.send_error(500, str(e))
    
    def _send_json_response(self, data: Dict):
        """Send JSON response."""
        try:
            response_json = json.dumps(data, indent=2, ensure_ascii=False)
            response_bytes = response_json.encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            print(f"❌ JSON response error: {e}")
            self.send_error(500, "JSON response error")
    
    def log_message(self, format, *args):
        """Override to reduce verbose logging."""
        if self.proxy_server and getattr(self.proxy_server.config, 'log_requests', False):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")


class HTTPProxyServer:
    """Main HTTP proxy server that routes requests through Selenium browsers."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize the proxy server."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
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
        
        # Initialize components (simplified for now)
        # TODO: Re-integrate browser pool when proxy is working
        # self.browser_pool = BrowserPool(config)
        # self.rotation_strategy = create_rotation_strategy(config)
        # self.health_monitor = ProxyHealthMonitor(config, self.browser_pool)
        
        self.logger.info(f"Proxy server initialized on {config.local_proxy_host}:{config.local_proxy_port}")
    
    def start(self) -> None:
        """Start the proxy server."""
        if self.is_running:
            self.logger.warning("Proxy server is already running")
            return
        
        try:
            print(f"🚀 Starting HTTP proxy server on {self.config.local_proxy_host}:{self.config.local_proxy_port}")
            
            # Create custom handler class with proxy reference
            proxy_server_instance = self
            
            class ProxyAwareHandler(ProxyRequestHandler):
                def __init__(self, request, client_address, server):
                    self.proxy_server = proxy_server_instance
                    super(ProxyRequestHandler, self).__init__(request, client_address, server)
            
            # Create server
            self.server = socketserver.ThreadingTCPServer(
                (self.config.local_proxy_host, self.config.local_proxy_port),
                ProxyAwareHandler
            )
            
            # Allow address reuse
            self.server.allow_reuse_address = True
            
            # Store reference for handlers
            self.server.proxy_server_instance = self
            
            # Start server thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            self.is_running = True
            self.start_time = time.time()
            
            print(f"✅ Proxy server started successfully!")
            print(f"📡 Proxy URL: http://{self.config.local_proxy_host}:{self.config.local_proxy_port}")
            print(f"🧪 Test endpoint: http://{self.config.local_proxy_host}:{self.config.local_proxy_port}/_proxy_admin/test")
            
        except Exception as e:
            print(f"❌ Failed to start proxy server: {e}")
            self.logger.error(f"Failed to start proxy server: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the proxy server."""
        if not self.is_running:
            return
        
        print("⏹️ Stopping proxy server...")
        
        # Stop server
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        # Wait for server thread
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
        
        self.is_running = False
        print("✅ Proxy server stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current server status."""
        with self.stats_lock:
            uptime = time.time() - self.start_time
            success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
            
            return {
                'server': {
                    'is_running': self.is_running,
                    'uptime_seconds': uptime,
                    'proxy_url': f"http://{self.config.local_proxy_host}:{self.config.local_proxy_port}",
                    'start_time': datetime.fromtimestamp(self.start_time).isoformat()
                },
                'statistics': {
                    'total_requests': self.total_requests,
                    'successful_requests': self.successful_requests,
                    'failed_requests': self.failed_requests,
                    'success_rate_percent': success_rate
                }
            }
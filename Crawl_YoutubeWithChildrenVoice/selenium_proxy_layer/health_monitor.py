#!/usr/bin/env python3
"""
Health monitoring for Selenium proxy layer.

Monitors the health of browser instances and proxy connections,
providing automated recovery and reporting capabilities.
"""

import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

from .config import ProxyConfig
from .browser_pool import BrowserPool, BrowserInstance


class ProxyHealthMonitor:
    """Monitors and maintains the health of proxy browser instances."""
    
    def __init__(self, config: ProxyConfig, browser_pool: BrowserPool):
        """Initialize health monitor."""
        self.config = config
        self.browser_pool = browser_pool
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_check_time = 0.0
        
        # Health statistics
        self.health_checks_performed = 0
        self.health_check_failures = 0
        self.recovery_attempts = 0
        self.successful_recoveries = 0
        
        # Performance tracking
        self.response_times: List[float] = []
        self.max_response_time_samples = 100
    
    def start_monitoring(self) -> None:
        """Start the health monitoring thread."""
        if self.is_running:
            self.logger.warning("Health monitor is already running")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Health monitor started")
    
    def stop_monitoring(self) -> None:
        """Stop the health monitoring thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("Health monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info(f"Health monitoring loop started (interval: {self.config.health_check_interval}s)")
        
        while self.is_running:
            try:
                # Check if it's time for health check
                current_time = time.time()
                if current_time - self.last_check_time >= self.config.health_check_interval:
                    self._perform_health_check()
                    self.last_check_time = current_time
                
                # Sleep for a short interval
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5.0)  # Wait before retrying
    
    def _perform_health_check(self) -> None:
        """Perform health check on all browsers."""
        self.logger.debug("Performing health check on all browsers")
        self.health_checks_performed += 1
        
        unhealthy_browsers = []
        
        # Check each browser
        for browser in self.browser_pool.browsers:
            if not self._check_browser_health(browser):
                unhealthy_browsers.append(browser)
        
        # Attempt recovery for unhealthy browsers
        if unhealthy_browsers:
            self.logger.warning(f"Found {len(unhealthy_browsers)} unhealthy browsers, attempting recovery")
            for browser in unhealthy_browsers:
                self._attempt_browser_recovery(browser)
    
    def _check_browser_health(self, browser: BrowserInstance) -> bool:
        """Check the health of a single browser instance."""
        try:
            start_time = time.time()
            
            # Navigate to health check URL
            browser.driver.set_page_load_timeout(self.config.health_check_timeout)
            browser.driver.get(self.config.health_check_url)
            
            # Measure response time
            response_time = time.time() - start_time
            self._record_response_time(response_time)
            
            # Check if page loaded successfully
            page_source = browser.driver.page_source
            if len(page_source) < 10:  # Minimal content check
                self.logger.warning(f"Browser {browser.current_ip} returned minimal content")
                return False
            
            # Update browser status
            browser.is_healthy = True
            self.logger.debug(f"Browser {browser.current_ip} health check passed ({response_time:.2f}s)")
            return True
            
        except Exception as e:
            self.logger.warning(f"Health check failed for browser {browser.current_ip}: {e}")
            browser.is_healthy = False
            self.health_check_failures += 1
            return False
    
    def _record_response_time(self, response_time: float) -> None:
        """Record response time for performance tracking."""
        self.response_times.append(response_time)
        
        # Keep only recent samples
        if len(self.response_times) > self.max_response_time_samples:
            self.response_times = self.response_times[-self.max_response_time_samples:]
    
    def _attempt_browser_recovery(self, browser: BrowserInstance) -> None:
        """Attempt to recover an unhealthy browser."""
        self.recovery_attempts += 1
        
        try:
            self.logger.info(f"Attempting to recover browser {browser.current_ip}")
            
            # Mark browser for restart
            self.browser_pool.mark_browser_failed(browser)
            
            # Give the browser pool time to restart
            time.sleep(2.0)
            
            # Check if recovery was successful
            if browser.is_healthy:
                self.successful_recoveries += 1
                self.logger.info(f"Successfully recovered browser {browser.current_ip}")
            else:
                self.logger.error(f"Failed to recover browser {browser.current_ip}")
                
        except Exception as e:
            self.logger.error(f"Error during browser recovery: {e}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report."""
        # Calculate statistics
        current_time = time.time()
        uptime = current_time - (self.last_check_time - self.config.health_check_interval)
        
        # Browser pool status
        pool_status = self.browser_pool.get_health_status()
        
        # Response time statistics
        response_stats = self._calculate_response_stats()
        
        # Health check statistics
        success_rate = 0.0
        if self.health_checks_performed > 0:
            success_rate = ((self.health_checks_performed - self.health_check_failures) / self.health_checks_performed) * 100
        
        recovery_rate = 0.0
        if self.recovery_attempts > 0:
            recovery_rate = (self.successful_recoveries / self.recovery_attempts) * 100
        
        return {
            'timestamp': datetime.now().isoformat(),
            'monitor_status': {
                'is_running': self.is_running,
                'uptime_seconds': uptime,
                'last_check_time': datetime.fromtimestamp(self.last_check_time).isoformat() if self.last_check_time > 0 else None
            },
            'browser_pool': pool_status,
            'health_checks': {
                'total_performed': self.health_checks_performed,
                'total_failures': self.health_check_failures,
                'success_rate_percent': success_rate
            },
            'recovery': {
                'attempts': self.recovery_attempts,
                'successful': self.successful_recoveries,
                'success_rate_percent': recovery_rate
            },
            'performance': response_stats
        }
    
    def _calculate_response_stats(self) -> Dict[str, float]:
        """Calculate response time statistics."""
        if not self.response_times:
            return {
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'samples_count': 0
            }
        
        return {
            'avg_response_time': sum(self.response_times) / len(self.response_times),
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'samples_count': len(self.response_times)
        }
    
    def get_summary_status(self) -> str:
        """Get a brief summary of health status."""
        pool_status = self.browser_pool.get_health_status()
        healthy_browsers = pool_status['healthy_browsers']
        total_browsers = pool_status['total_browsers']
        
        if healthy_browsers == 0:
            return "🔴 CRITICAL: No healthy browsers available"
        elif healthy_browsers < total_browsers / 2:
            return f"🟡 WARNING: Only {healthy_browsers}/{total_browsers} browsers healthy"
        elif healthy_browsers == total_browsers:
            return f"🟢 HEALTHY: All {total_browsers} browsers operational"
        else:
            return f"🟢 GOOD: {healthy_browsers}/{total_browsers} browsers healthy"
    
    def force_health_check(self) -> Dict[str, Any]:
        """Force an immediate health check and return results."""
        self.logger.info("Forcing immediate health check")
        self._perform_health_check()
        return self.get_health_report()

#!/usr/bin/env python3
"""
Rotation strategies for Selenium proxy layer.

Implements different strategies for when and how to rotate IP addresses
through the browser pool.
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

from .config import ProxyConfig


class RotationStrategy(ABC):
    """Abstract base class for rotation strategies."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize rotation strategy."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self._reset_counters()
    
    @abstractmethod
    def should_rotate(self) -> bool:
        """Determine if rotation should occur."""
        pass
    
    @abstractmethod
    def on_request_complete(self, success: bool) -> None:
        """Called when a request is completed."""
        pass
    
    @abstractmethod
    def on_request_failed(self) -> None:
        """Called when a request fails."""
        pass
    
    @abstractmethod
    def _reset_counters(self) -> None:
        """Reset internal counters."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rotation statistics."""
        return {
            'strategy_type': self.__class__.__name__,
            'rotation_interval': self.config.rotation_interval
        }


class TimeBasedRotation(RotationStrategy):
    """Rotate IP addresses based on time intervals."""
    
    def _reset_counters(self) -> None:
        """Reset time-based counters."""
        self.last_rotation_time = time.time()
        self.rotation_count = 0
    
    def should_rotate(self) -> bool:
        """Check if enough time has passed for rotation."""
        with self.lock:
            current_time = time.time()
            time_elapsed = current_time - self.last_rotation_time
            
            if time_elapsed >= self.config.rotation_interval:
                self.last_rotation_time = current_time
                self.rotation_count += 1
                self.logger.info(f"Time-based rotation triggered after {time_elapsed:.1f}s")
                return True
            
            return False
    
    def on_request_complete(self, success: bool) -> None:
        """No action needed for time-based rotation."""
        pass
    
    def on_request_failed(self) -> None:
        """No action needed for time-based rotation."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get time-based rotation statistics."""
        with self.lock:
            stats = super().get_stats()
            stats.update({
                'last_rotation_time': self.last_rotation_time,
                'rotation_count': self.rotation_count,
                'time_since_last_rotation': time.time() - self.last_rotation_time
            })
            return stats


class RequestBasedRotation(RotationStrategy):
    """Rotate IP addresses based on number of requests."""
    
    def _reset_counters(self) -> None:
        """Reset request-based counters."""
        self.request_count = 0
        self.rotation_count = 0
        self.last_rotation_time = time.time()
    
    def should_rotate(self) -> bool:
        """Check if enough requests have been made for rotation."""
        with self.lock:
            if self.request_count >= self.config.rotation_interval:
                self.request_count = 0
                self.rotation_count += 1
                self.last_rotation_time = time.time()
                self.logger.info(f"Request-based rotation triggered after {self.config.rotation_interval} requests")
                return True
            
            return False
    
    def on_request_complete(self, success: bool) -> None:
        """Increment request counter."""
        with self.lock:
            self.request_count += 1
    
    def on_request_failed(self) -> None:
        """Count failed requests towards rotation."""
        self.on_request_complete(False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get request-based rotation statistics."""
        with self.lock:
            stats = super().get_stats()
            stats.update({
                'request_count': self.request_count,
                'rotation_count': self.rotation_count,
                'requests_until_rotation': self.config.rotation_interval - self.request_count,
                'last_rotation_time': self.last_rotation_time
            })
            return stats


class FailureBasedRotation(RotationStrategy):
    """Rotate IP addresses based on failure patterns."""
    
    def _reset_counters(self) -> None:
        """Reset failure-based counters."""
        self.consecutive_failures = 0
        self.total_failures = 0
        self.total_requests = 0
        self.rotation_count = 0
        self.last_rotation_time = time.time()
    
    def should_rotate(self) -> bool:
        """Check if failure threshold is reached."""
        with self.lock:
            # Rotate if we have consecutive failures
            if self.consecutive_failures >= self.config.rotation_interval:
                self.consecutive_failures = 0
                self.rotation_count += 1
                self.last_rotation_time = time.time()
                self.logger.warning(f"Failure-based rotation triggered after {self.config.rotation_interval} consecutive failures")
                return True
            
            # Also rotate if failure rate is too high
            if self.total_requests >= 10:  # Minimum sample size
                failure_rate = self.total_failures / self.total_requests
                if failure_rate > 0.5:  # 50% failure rate
                    self.total_failures = 0
                    self.total_requests = 0
                    self.rotation_count += 1
                    self.last_rotation_time = time.time()
                    self.logger.warning(f"Failure-based rotation triggered due to high failure rate: {failure_rate:.2%}")
                    return True
            
            return False
    
    def on_request_complete(self, success: bool) -> None:
        """Track request success/failure."""
        with self.lock:
            self.total_requests += 1
            
            if success:
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                self.total_failures += 1
    
    def on_request_failed(self) -> None:
        """Record request failure."""
        self.on_request_complete(False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get failure-based rotation statistics."""
        with self.lock:
            failure_rate = (self.total_failures / self.total_requests) if self.total_requests > 0 else 0
            
            stats = super().get_stats()
            stats.update({
                'consecutive_failures': self.consecutive_failures,
                'total_failures': self.total_failures,
                'total_requests': self.total_requests,
                'failure_rate': failure_rate,
                'rotation_count': self.rotation_count,
                'failures_until_rotation': self.config.rotation_interval - self.consecutive_failures,
                'last_rotation_time': self.last_rotation_time
            })
            return stats


class HybridRotation(RotationStrategy):
    """Combines multiple rotation strategies."""
    
    def __init__(self, config: ProxyConfig):
        """Initialize hybrid rotation with multiple strategies."""
        super().__init__(config)
        
        # Create sub-strategies
        self.time_strategy = TimeBasedRotation(config)
        self.request_strategy = RequestBasedRotation(config)
        self.failure_strategy = FailureBasedRotation(config)
        
        # Configure thresholds for hybrid mode
        self.time_strategy.config.rotation_interval = config.rotation_interval * 2  # Longer time intervals
        self.failure_strategy.config.rotation_interval = max(3, config.rotation_interval // 2)  # Lower failure threshold
    
    def _reset_counters(self) -> None:
        """Reset all sub-strategy counters."""
        self.time_strategy._reset_counters()
        self.request_strategy._reset_counters()
        self.failure_strategy._reset_counters()
    
    def should_rotate(self) -> bool:
        """Check if any strategy indicates rotation should occur."""
        # Check failure strategy first (highest priority)
        if self.failure_strategy.should_rotate():
            self.logger.info("Hybrid rotation triggered by failure strategy")
            return True
        
        # Check request strategy
        if self.request_strategy.should_rotate():
            self.logger.info("Hybrid rotation triggered by request strategy")
            return True
        
        # Check time strategy (lowest priority)
        if self.time_strategy.should_rotate():
            self.logger.info("Hybrid rotation triggered by time strategy")
            return True
        
        return False
    
    def on_request_complete(self, success: bool) -> None:
        """Notify all sub-strategies of request completion."""
        self.time_strategy.on_request_complete(success)
        self.request_strategy.on_request_complete(success)
        self.failure_strategy.on_request_complete(success)
    
    def on_request_failed(self) -> None:
        """Notify all sub-strategies of request failure."""
        self.time_strategy.on_request_failed()
        self.request_strategy.on_request_failed()
        self.failure_strategy.on_request_failed()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all strategies."""
        stats = super().get_stats()
        stats.update({
            'time_strategy': self.time_strategy.get_stats(),
            'request_strategy': self.request_strategy.get_stats(),
            'failure_strategy': self.failure_strategy.get_stats()
        })
        return stats


def create_rotation_strategy(config: ProxyConfig) -> RotationStrategy:
    """Factory function to create rotation strategy based on config."""
    strategy_map = {
        'time_based': TimeBasedRotation,
        'request_based': RequestBasedRotation,
        'failure_based': FailureBasedRotation,
        'hybrid': HybridRotation
    }
    
    strategy_class = strategy_map.get(config.rotation_strategy.lower())
    if not strategy_class:
        raise ValueError(f"Unknown rotation strategy: {config.rotation_strategy}")
    
    return strategy_class(config)

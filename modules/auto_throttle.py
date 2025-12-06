"""
Auto-throttle detector for handling rate limits and failures.

This module monitors request failures (429, 5xx errors) and automatically
adjusts request rates, pausing or slowing down shards/cohorts that are
experiencing elevated error rates to avoid detection and bans.

Author: BYNNΛI
License: MIT
"""

import os
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AutoThrottle:
    """
    Automatic throttling based on error rate monitoring.
    
    Features:
    - Tracks 429 (rate limit) and 5xx (server error) responses
    - Detects abnormal failure spikes per shard/cohort
    - Auto-pauses or slows down problematic shards
    - Exponential backoff for repeated failures
    - Automatic recovery after cooldown period
    """
    
    def __init__(
        self,
        error_threshold: float = 0.3,
        error_window_seconds: int = 300,
        min_samples: int = 10,
        pause_duration_seconds: int = 600,
        backoff_multiplier: float = 2.0,
        max_pause_duration_seconds: int = 3600
    ):
        """
        Initialize auto-throttle detector.
        
        Args:
            error_threshold: Error rate threshold (0.0-1.0) to trigger throttle
            error_window_seconds: Time window to calculate error rate
            min_samples: Minimum requests before calculating rate
            pause_duration_seconds: Initial pause duration on throttle
            backoff_multiplier: Multiplier for repeated throttles
            max_pause_duration_seconds: Maximum pause duration
        """
        self.error_threshold = float(
            os.getenv('AUTO_THROTTLE_ERROR_THRESHOLD', str(error_threshold))
        )
        self.error_window_seconds = int(
            os.getenv('AUTO_THROTTLE_ERROR_WINDOW', str(error_window_seconds))
        )
        self.min_samples = int(
            os.getenv('AUTO_THROTTLE_MIN_SAMPLES', str(min_samples))
        )
        self.pause_duration_seconds = int(
            os.getenv('AUTO_THROTTLE_PAUSE_DURATION', str(pause_duration_seconds))
        )
        self.backoff_multiplier = float(
            os.getenv('AUTO_THROTTLE_BACKOFF_MULTIPLIER', str(backoff_multiplier))
        )
        self.max_pause_duration_seconds = int(
            os.getenv('AUTO_THROTTLE_MAX_PAUSE', str(max_pause_duration_seconds))
        )
        
        # Tracking structures
        # identifier -> deque of (timestamp, is_error)
        self.request_history: Dict[str, deque] = {}
        
        # identifier -> (pause_until, current_pause_duration)
        self.paused_identifiers: Dict[str, Tuple[datetime, int]] = {}
        
        # Statistics
        self.throttle_events = 0
        self.total_pauses = 0
        
        logger.info(
            "Auto-throttle initialized",
            error_threshold=self.error_threshold,
            error_window_seconds=self.error_window_seconds,
            min_samples=self.min_samples,
            pause_duration_seconds=self.pause_duration_seconds
        )
    
    def record_request(
        self,
        identifier: str,
        is_error: bool,
        status_code: Optional[int] = None
    ):
        """
        Record a request outcome for monitoring.
        
        Args:
            identifier: Shard/wallet/cohort identifier
            is_error: Whether the request resulted in an error
            status_code: Optional HTTP status code
        """
        now = datetime.utcnow()
        
        # Initialize history if needed
        if identifier not in self.request_history:
            self.request_history[identifier] = deque()
        
        # Record this request
        self.request_history[identifier].append((now, is_error, status_code))
        
        # Clean old entries outside window
        cutoff = now - timedelta(seconds=self.error_window_seconds)
        history = self.request_history[identifier]
        while history and history[0][0] < cutoff:
            history.popleft()
        
        # Check if we should throttle based on error status codes
        if status_code in [429, 500, 502, 503, 504]:
            self._check_and_throttle(identifier)
    
    def _check_and_throttle(self, identifier: str):
        """
        Check error rate and throttle if threshold exceeded.
        
        Args:
            identifier: Identifier to check
        """
        history = self.request_history.get(identifier, deque())
        
        if len(history) < self.min_samples:
            return  # Not enough samples yet
        
        # Calculate error rate
        error_count = sum(1 for _, is_error, _ in history if is_error)
        error_rate = error_count / len(history)
        
        if error_rate >= self.error_threshold:
            # Throttle this identifier
            self._apply_throttle(identifier, error_rate)
    
    def _apply_throttle(self, identifier: str, error_rate: float):
        """
        Apply throttle to an identifier.
        
        Args:
            identifier: Identifier to throttle
            error_rate: Current error rate
        """
        now = datetime.utcnow()
        
        # Determine pause duration
        if identifier in self.paused_identifiers:
            # Repeated throttle - apply backoff
            _, current_duration = self.paused_identifiers[identifier]
            new_duration = min(
                int(current_duration * self.backoff_multiplier),
                self.max_pause_duration_seconds
            )
        else:
            new_duration = self.pause_duration_seconds
        
        pause_until = now + timedelta(seconds=new_duration)
        self.paused_identifiers[identifier] = (pause_until, new_duration)
        
        self.throttle_events += 1
        self.total_pauses += 1
        
        logger.warning(
            "Auto-throttle triggered",
            identifier=identifier,
            error_rate=round(error_rate, 3),
            pause_duration_seconds=new_duration,
            pause_until=pause_until.isoformat()
        )
    
    def is_paused(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if an identifier is currently paused.
        
        Args:
            identifier: Identifier to check
        
        Returns:
            (is_paused, seconds_remaining)
        """
        if identifier not in self.paused_identifiers:
            return False, None
        
        pause_until, _ = self.paused_identifiers[identifier]
        now = datetime.utcnow()
        
        if now >= pause_until:
            # Pause expired, remove it
            del self.paused_identifiers[identifier]
            logger.info("Auto-throttle pause expired", identifier=identifier)
            return False, None
        
        seconds_remaining = int((pause_until - now).total_seconds())
        return True, seconds_remaining
    
    def get_error_rate(self, identifier: str) -> Optional[float]:
        """
        Get current error rate for an identifier.
        
        Args:
            identifier: Identifier to check
        
        Returns:
            Error rate (0.0-1.0) or None if insufficient data
        """
        history = self.request_history.get(identifier, deque())
        
        if len(history) < self.min_samples:
            return None
        
        error_count = sum(1 for _, is_error, _ in history if is_error)
        return error_count / len(history)
    
    def reset_throttle(self, identifier: str):
        """
        Manually reset throttle for an identifier.
        
        Args:
            identifier: Identifier to reset
        """
        if identifier in self.paused_identifiers:
            del self.paused_identifiers[identifier]
            logger.info("Manually reset throttle", identifier=identifier)
        
        if identifier in self.request_history:
            self.request_history[identifier].clear()
    
    def get_slowdown_factor(self, identifier: str) -> float:
        """
        Get slowdown factor for an identifier based on error rate.
        
        Returns a multiplier for delays:
        - 1.0 = normal speed
        - >1.0 = slow down (e.g., 2.0 = twice as slow)
        
        Args:
            identifier: Identifier to check
        
        Returns:
            Slowdown factor
        """
        error_rate = self.get_error_rate(identifier)
        
        if error_rate is None:
            return 1.0
        
        if error_rate < self.error_threshold * 0.5:
            return 1.0  # Normal speed
        elif error_rate < self.error_threshold:
            return 1.5  # Slight slowdown
        else:
            return 3.0  # Significant slowdown
    
    def get_stats(self) -> Dict:
        """Get auto-throttle statistics."""
        active_pauses = len(self.paused_identifiers)
        monitored_identifiers = len(self.request_history)
        
        # Calculate average error rate across all identifiers
        total_requests = 0
        total_errors = 0
        for history in self.request_history.values():
            total_requests += len(history)
            total_errors += sum(1 for _, is_error, _ in history if is_error)
        
        avg_error_rate = total_errors / total_requests if total_requests > 0 else 0.0
        
        return {
            'throttle_events': self.throttle_events,
            'total_pauses': self.total_pauses,
            'active_pauses': active_pauses,
            'monitored_identifiers': monitored_identifiers,
            'avg_error_rate': round(avg_error_rate, 3),
            'error_threshold': self.error_threshold
        }

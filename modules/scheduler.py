"""
Scheduling entropy manager for human-like behavior patterns.

This module provides sophisticated timing controls including off-days, night/weekend
lulls, day-part windows, non-uniform jitter, and per-wallet skip patterns to avoid
detection by anti-Sybil systems.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BYNNΛI - AirdropFarm
Sophisticated multi-chain airdrop farming automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: BYNNΛI
Project: AirdropFarm
License: MIT
Repository: https://github.com/BYNNAI/airdrop-farming-bot
"""

import os
import random
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta, time as dt_time
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SchedulerEntropy:
    """
    Manages scheduling entropy for human-like activity patterns.
    
    Features:
    - Configurable off-days (e.g., system "rest" days)
    - Night/weekend lull periods with reduced activity
    - Day-part windows (morning, afternoon, evening preferences)
    - Non-uniform inter-arrival jitter
    - Per-wallet skip-days to create irregular patterns
    """
    
    def __init__(
        self,
        off_days: Optional[List[int]] = None,
        night_lull_windows: Optional[List[Tuple[int, int]]] = None,
        daypart_windows: Optional[Dict[str, Tuple[int, int]]] = None,
        weekend_activity_reduction: float = 0.3,
        night_activity_reduction: float = 0.5
    ):
        """
        Initialize scheduling entropy manager.
        
        Args:
            off_days: List of day indices (0=Monday) for system off-days
            night_lull_windows: List of (start_hour, end_hour) tuples for night lulls
            daypart_windows: Dict of window names to (start_hour, end_hour) tuples
            weekend_activity_reduction: Probability reduction for weekend (0.0-1.0)
            night_activity_reduction: Probability reduction for night (0.0-1.0)
        """
        # Parse off-days from environment
        off_days_env = os.getenv('OFF_DAYS', '')
        if off_days_env:
            self.off_days = [int(d.strip()) for d in off_days_env.split(',') if d.strip()]
        else:
            self.off_days = off_days or []
        
        # Parse night lull windows
        night_lull_env = os.getenv('NIGHT_LULL_WINDOWS', '')
        if night_lull_env:
            # Format: "0-6,22-24" -> [(0,6), (22,24)]
            self.night_lull_windows = []
            for window in night_lull_env.split(','):
                if '-' in window:
                    start, end = window.split('-')
                    self.night_lull_windows.append((int(start), int(end)))
        else:
            self.night_lull_windows = night_lull_windows or [(0, 6), (22, 24)]
        
        # Parse daypart windows
        daypart_env = os.getenv('DAYPART_WINDOWS', '')
        if daypart_env:
            # Format: "morning:6-12,afternoon:12-18,evening:18-22"
            self.daypart_windows = {}
            for part in daypart_env.split(','):
                if ':' in part:
                    name, hours = part.split(':')
                    start, end = hours.split('-')
                    self.daypart_windows[name] = (int(start), int(end))
        else:
            self.daypart_windows = daypart_windows or {
                'morning': (6, 12),
                'afternoon': (12, 18),
                'evening': (18, 22)
            }
        
        self.weekend_activity_reduction = float(
            os.getenv('WEEKEND_ACTIVITY_REDUCTION', str(weekend_activity_reduction))
        )
        self.night_activity_reduction = float(
            os.getenv('NIGHT_ACTIVITY_REDUCTION', str(night_activity_reduction))
        )
        
        # Per-wallet skip tracking
        self.wallet_skip_days: Dict[str, Set[str]] = {}  # wallet -> set of skip dates
        self.wallet_last_activity: Dict[str, datetime] = {}
        
        logger.info(
            "Scheduler entropy initialized",
            off_days=self.off_days,
            night_lull_windows=self.night_lull_windows,
            daypart_windows=self.daypart_windows,
            weekend_reduction=self.weekend_activity_reduction,
            night_reduction=self.night_activity_reduction
        )
    
    def should_execute_now(
        self,
        wallet_address: Optional[str] = None,
        respect_lulls: bool = True
    ) -> bool:
        """
        Determine if an action should execute now based on scheduling rules.
        
        Args:
            wallet_address: Optional wallet to check skip-days for
            respect_lulls: Whether to apply night/weekend lull probability
        
        Returns:
            True if action should proceed, False to skip
        """
        now = datetime.utcnow()
        
        # Check if today is an off-day
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        if weekday in self.off_days:
            logger.debug("Skipping due to off-day", weekday=weekday)
            return False
        
        # Check wallet-specific skip-days
        if wallet_address:
            date_str = now.strftime('%Y-%m-%d')
            if wallet_address in self.wallet_skip_days:
                if date_str in self.wallet_skip_days[wallet_address]:
                    logger.debug(
                        "Skipping due to wallet skip-day",
                        wallet=wallet_address[:10],
                        date=date_str
                    )
                    return False
        
        if not respect_lulls:
            return True
        
        # Apply lull probability reductions
        current_hour = now.hour
        
        # Check night lull
        in_night_lull = any(
            start <= current_hour < end or (start > end and (current_hour >= start or current_hour < end))
            for start, end in self.night_lull_windows
        )
        
        if in_night_lull:
            if random.random() > (1.0 - self.night_activity_reduction):
                logger.debug("Skipping due to night lull", hour=current_hour)
                return False
        
        # Check weekend lull
        is_weekend = weekday in [5, 6]  # Saturday, Sunday
        if is_weekend:
            if random.random() > (1.0 - self.weekend_activity_reduction):
                logger.debug("Skipping due to weekend lull", weekday=weekday)
                return False
        
        return True
    
    def get_jittered_delay(
        self,
        base_delay: float,
        jitter_min_pct: float = 0.5,
        jitter_max_pct: float = 2.0,
        distribution: str = 'uniform'
    ) -> float:
        """
        Apply non-uniform jitter to a base delay.
        
        Args:
            base_delay: Base delay in seconds
            jitter_min_pct: Minimum jitter percentage (e.g., 0.5 = 50% of base)
            jitter_max_pct: Maximum jitter percentage (e.g., 2.0 = 200% of base)
            distribution: 'uniform', 'gaussian', 'exponential'
        
        Returns:
            Jittered delay in seconds
        """
        if distribution == 'gaussian':
            # Gaussian with mean at base_delay and some std dev
            mean = base_delay
            std_dev = base_delay * 0.3
            jittered = random.gauss(mean, std_dev)
            # Clamp to reasonable bounds
            jittered = max(base_delay * jitter_min_pct, min(base_delay * jitter_max_pct, jittered))
        elif distribution == 'exponential':
            # Exponential with lambda to achieve desired mean
            lambda_param = 1.0 / base_delay
            jittered = random.expovariate(lambda_param)
            jittered = max(base_delay * jitter_min_pct, min(base_delay * jitter_max_pct, jittered))
        else:  # uniform
            jittered = random.uniform(
                base_delay * jitter_min_pct,
                base_delay * jitter_max_pct
            )
        
        return jittered
    
    def get_next_execution_time(
        self,
        base_delay: float,
        daypart_preference: Optional[str] = None,
        wallet_address: Optional[str] = None
    ) -> datetime:
        """
        Calculate next execution time with daypart preference.
        
        Args:
            base_delay: Base delay from now in seconds
            daypart_preference: Preferred daypart ('morning', 'afternoon', 'evening')
            wallet_address: Optional wallet for tracking
        
        Returns:
            Next execution datetime
        """
        now = datetime.utcnow()
        jittered_delay = self.get_jittered_delay(base_delay)
        next_time = now + timedelta(seconds=jittered_delay)
        
        # If daypart preference specified, adjust to that window
        if daypart_preference and daypart_preference in self.daypart_windows:
            start_hour, end_hour = self.daypart_windows[daypart_preference]
            
            # If next_time is outside preferred window, move it
            if not (start_hour <= next_time.hour < end_hour):
                # Move to start of next occurrence of this daypart
                if next_time.hour < start_hour:
                    # Same day, later
                    next_time = next_time.replace(
                        hour=start_hour,
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                else:
                    # Next day
                    next_time = next_time + timedelta(days=1)
                    next_time = next_time.replace(
                        hour=start_hour,
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
        
        # Track last activity
        if wallet_address:
            self.wallet_last_activity[wallet_address] = now
        
        return next_time
    
    def add_wallet_skip_day(
        self,
        wallet_address: str,
        date: Optional[datetime] = None
    ):
        """
        Add a skip-day for a specific wallet.
        
        Args:
            wallet_address: Wallet to skip
            date: Date to skip (defaults to today)
        """
        if date is None:
            date = datetime.utcnow()
        
        date_str = date.strftime('%Y-%m-%d')
        
        if wallet_address not in self.wallet_skip_days:
            self.wallet_skip_days[wallet_address] = set()
        
        self.wallet_skip_days[wallet_address].add(date_str)
        
        logger.debug(
            "Added wallet skip-day",
            wallet=wallet_address[:10],
            date=date_str
        )
    
    def randomly_assign_skip_days(
        self,
        wallet_addresses: List[str],
        skip_probability: float = 0.1,
        days_ahead: int = 7
    ):
        """
        Randomly assign skip-days to wallets for upcoming days.
        
        Args:
            wallet_addresses: List of wallet addresses
            skip_probability: Probability each wallet skips each day
            days_ahead: Number of days to plan ahead
        """
        now = datetime.utcnow()
        
        for wallet in wallet_addresses:
            for day_offset in range(days_ahead):
                if random.random() < skip_probability:
                    date = now + timedelta(days=day_offset)
                    self.add_wallet_skip_day(wallet, date)
        
        logger.info(
            "Assigned random skip-days",
            wallet_count=len(wallet_addresses),
            skip_probability=skip_probability,
            days_ahead=days_ahead
        )
    
    def get_stats(self) -> Dict:
        """Get scheduler statistics."""
        return {
            'off_days': self.off_days,
            'night_lull_windows': self.night_lull_windows,
            'daypart_windows': self.daypart_windows,
            'wallets_with_skip_days': len(self.wallet_skip_days),
            'tracked_wallets': len(self.wallet_last_activity)
        }

"""
Anti-detection coordinator for airdrop farming operations.

This module coordinates all anti-detection measures including IP rotation,
User-Agent spoofing, scheduling entropy, and auto-throttling to create
human-like behavior patterns that avoid Sybil detection systems.

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
from typing import Dict, Optional, List
from datetime import datetime
from utils.logging_config import get_logger

# Import anti-detection components
from modules.ip_manager import IPManager
from modules.ua_rotation import UserAgentRotator
from modules.scheduler import SchedulerEntropy
from modules.auto_throttle import AutoThrottle

logger = get_logger(__name__)


class AntiDetection:
    """
    Coordinates all anti-detection measures.
    
    Provides a unified interface for:
    - IP rotation and sharding
    - User-Agent rotation
    - Scheduling entropy
    - Auto-throttling
    - Faucet behavior controls
    - Action diversity
    """
    
    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        enable_ip_rotation: bool = True,
        enable_ua_rotation: bool = True,
        enable_scheduling: bool = True,
        enable_auto_throttle: bool = True
    ):
        """
        Initialize anti-detection coordinator.
        
        Args:
            proxy_list: List of proxy URLs
            enable_ip_rotation: Enable IP rotation features
            enable_ua_rotation: Enable User-Agent rotation
            enable_scheduling: Enable scheduling entropy
            enable_auto_throttle: Enable auto-throttle
        """
        self.enable_ip_rotation = enable_ip_rotation and (
            proxy_list or os.getenv('PROXY_LIST', '') or os.getenv('USE_PROXIES', 'false').lower() == 'true'
        )
        self.enable_ua_rotation = enable_ua_rotation
        self.enable_scheduling = enable_scheduling
        self.enable_auto_throttle = enable_auto_throttle
        
        # Initialize components
        self.ip_manager = None
        if self.enable_ip_rotation:
            self.ip_manager = IPManager(proxy_list=proxy_list)
        
        self.ua_rotator = None
        if self.enable_ua_rotation:
            self.ua_rotator = UserAgentRotator()
        
        self.scheduler = None
        if self.enable_scheduling:
            self.scheduler = SchedulerEntropy()
        
        self.auto_throttle = None
        if self.enable_auto_throttle:
            self.auto_throttle = AutoThrottle()
        
        # Faucet behavior controls
        self.over_cooldown_jitter_min = float(
            os.getenv('OVER_COOLDOWN_JITTER_MIN', '0.1')
        )
        self.over_cooldown_jitter_max = float(
            os.getenv('OVER_COOLDOWN_JITTER_MAX', '0.3')
        )
        self.faucet_skip_prob = float(
            os.getenv('FAUCET_SKIP_PROB', '0.05')
        )
        self.action_skip_prob = float(
            os.getenv('ACTION_SKIP_PROB', '0.1')
        )
        
        logger.info(
            "Anti-detection coordinator initialized",
            ip_rotation=self.enable_ip_rotation,
            ua_rotation=self.enable_ua_rotation,
            scheduling=self.enable_scheduling,
            auto_throttle=self.enable_auto_throttle,
            faucet_skip_prob=self.faucet_skip_prob,
            action_skip_prob=self.action_skip_prob
        )
    
    def get_request_config(
        self,
        wallet_address: str,
        shard_id: Optional[int] = None,
        traffic_type: str = 'general',
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Get complete request configuration with all anti-detection measures.
        
        Args:
            wallet_address: Wallet address
            shard_id: Optional shard ID
            traffic_type: Type of traffic ('faucet', 'rpc', 'general')
            session_id: Optional session identifier
        
        Returns:
            Dictionary with proxy, headers, and timing information
        """
        config = {
            'proxy': None,
            'headers': {},
            'should_proceed': True,
            'delay_seconds': 0
        }
        
        # Check if we should proceed (scheduling entropy)
        if self.scheduler:
            config['should_proceed'] = self.scheduler.should_execute_now(
                wallet_address=wallet_address
            )
            if not config['should_proceed']:
                return config
        
        # Get proxy
        if self.ip_manager:
            config['proxy'] = self.ip_manager.get_proxy_for_wallet(
                wallet_address=wallet_address,
                shard_id=shard_id,
                traffic_type=traffic_type
            )
        
        # Get headers with User-Agent
        if self.ua_rotator:
            config['headers'] = self.ua_rotator.get_headers(
                session_id=session_id,
                wallet_address=wallet_address,
                shard_id=shard_id
            )
        
        # Check auto-throttle
        if self.auto_throttle:
            identifier = f"shard_{shard_id}" if shard_id is not None else wallet_address
            is_paused, seconds_remaining = self.auto_throttle.is_paused(identifier)
            
            if is_paused:
                config['should_proceed'] = False
                config['delay_seconds'] = seconds_remaining
                logger.info(
                    "Request paused by auto-throttle",
                    identifier=identifier,
                    seconds_remaining=seconds_remaining
                )
        
        return config
    
    def should_skip_faucet(self, wallet_address: str) -> bool:
        """
        Decide whether to skip a faucet claim for randomness.
        
        Args:
            wallet_address: Wallet address
        
        Returns:
            True if should skip, False if should proceed
        """
        if random.random() < self.faucet_skip_prob:
            logger.debug(
                "Skipping faucet due to random skip",
                wallet=wallet_address[:10],
                skip_prob=self.faucet_skip_prob
            )
            return True
        return False
    
    def should_skip_action(self, wallet_address: str) -> bool:
        """
        Decide whether to skip an action for randomness.
        
        Args:
            wallet_address: Wallet address
        
        Returns:
            True if should skip, False if should proceed
        """
        if random.random() < self.action_skip_prob:
            logger.debug(
                "Skipping action due to random skip",
                wallet=wallet_address[:10],
                skip_prob=self.action_skip_prob
            )
            return True
        return False
    
    def get_overcooldown_delay(self, base_cooldown_seconds: float) -> float:
        """
        Add random delay beyond stated cooldown period.
        
        Args:
            base_cooldown_seconds: Base cooldown in seconds
        
        Returns:
            Extended cooldown with jitter
        """
        jitter_pct = random.uniform(
            self.over_cooldown_jitter_min,
            self.over_cooldown_jitter_max
        )
        additional_delay = base_cooldown_seconds * jitter_pct
        
        return base_cooldown_seconds + additional_delay
    
    def shuffle_actions(self, actions: List[str], shard_id: Optional[int] = None) -> List[str]:
        """
        Shuffle action order for a shard/day to create diversity.
        
        Args:
            actions: List of action names
            shard_id: Optional shard ID for deterministic shuffling
        
        Returns:
            Shuffled list of actions
        """
        if shard_id is not None:
            # Use shard and date for deterministic shuffle
            seed = shard_id + int(datetime.utcnow().strftime('%Y%m%d'))
            random.seed(seed)
        
        shuffled = actions.copy()
        random.shuffle(shuffled)
        
        # Reset random seed
        random.seed()
        
        return shuffled
    
    def record_request_outcome(
        self,
        identifier: str,
        success: bool,
        status_code: Optional[int] = None
    ):
        """
        Record request outcome for auto-throttle monitoring.
        
        Args:
            identifier: Shard/wallet identifier
            success: Whether request succeeded
            status_code: Optional HTTP status code
        """
        if self.auto_throttle:
            self.auto_throttle.record_request(
                identifier=identifier,
                is_error=not success,
                status_code=status_code
            )
    
    def get_jittered_delay(
        self,
        base_delay: float,
        distribution: str = 'uniform'
    ) -> float:
        """
        Get jittered delay for timing randomization.
        
        Args:
            base_delay: Base delay in seconds
            distribution: Distribution type ('uniform', 'gaussian', 'exponential')
        
        Returns:
            Jittered delay in seconds
        """
        if self.scheduler:
            return self.scheduler.get_jittered_delay(
                base_delay=base_delay,
                distribution=distribution
            )
        
        # Fallback to simple uniform jitter
        return random.uniform(base_delay * 0.5, base_delay * 1.5)
    
    def get_stats(self) -> Dict:
        """Get comprehensive anti-detection statistics."""
        stats = {
            'enabled_features': {
                'ip_rotation': self.enable_ip_rotation,
                'ua_rotation': self.enable_ua_rotation,
                'scheduling': self.enable_scheduling,
                'auto_throttle': self.enable_auto_throttle
            },
            'faucet_skip_prob': self.faucet_skip_prob,
            'action_skip_prob': self.action_skip_prob
        }
        
        if self.ip_manager:
            stats['ip_manager'] = self.ip_manager.get_stats()
        
        if self.ua_rotator:
            stats['ua_rotator'] = self.ua_rotator.get_stats()
        
        if self.scheduler:
            stats['scheduler'] = self.scheduler.get_stats()
        
        if self.auto_throttle:
            stats['auto_throttle'] = self.auto_throttle.get_stats()
        
        return stats

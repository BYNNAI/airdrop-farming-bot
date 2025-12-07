"""
IP rotation and sharding management for anti-detection.

This module provides intelligent IP rotation with wallet-to-IP sharding,
stickiness windows, and separate policies for faucet vs RPC traffic to
avoid pattern detection by blockchain networks and faucet services.

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
import time
import random
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from utils.logging_config import get_logger

logger = get_logger(__name__)


class IPManager:
    """
    Manages IP rotation with wallet sharding and stickiness.
    
    Features:
    - Configurable wallet-to-IP sharding (e.g., 10 wallets per IP)
    - Stickiness windows to maintain IP consistency for a period
    - Separate policies for faucet vs RPC traffic
    - Slow randomized rotation to avoid detection patterns
    """
    
    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        ip_shard_size: int = 10,
        ip_sticky_hours: float = 24.0,
        faucet_ip_sticky_hours: Optional[float] = None,
        rpc_ip_sticky_hours: Optional[float] = None,
        rotation_jitter_pct: float = 0.2
    ):
        """
        Initialize IP manager.
        
        Args:
            proxy_list: List of proxy URLs (http://user:pass@ip:port)
            ip_shard_size: Number of wallets per IP shard
            ip_sticky_hours: Default IP stickiness window in hours
            faucet_ip_sticky_hours: Override stickiness for faucet traffic
            rpc_ip_sticky_hours: Override stickiness for RPC traffic
            rotation_jitter_pct: Randomization percentage for rotation timing
        """
        # Parse proxies from environment if not provided
        if proxy_list is None:
            proxy_str = os.getenv('PROXY_LIST', '')
            proxy_list = [p.strip() for p in proxy_str.split(',') if p.strip()]
        
        self.proxy_list = proxy_list or []
        self.ip_shard_size = int(os.getenv('IP_SHARD_SIZE', str(ip_shard_size)))
        self.ip_sticky_hours = float(os.getenv('IP_STICKY_HOURS', str(ip_sticky_hours)))
        
        # Separate stickiness for faucet and RPC
        self.faucet_ip_sticky_hours = float(
            os.getenv('FAUCET_IP_STICKY_HOURS', 
                     str(faucet_ip_sticky_hours or self.ip_sticky_hours))
        )
        self.rpc_ip_sticky_hours = float(
            os.getenv('RPC_IP_STICKY_HOURS',
                     str(rpc_ip_sticky_hours or self.ip_sticky_hours))
        )
        
        self.rotation_jitter_pct = float(
            os.getenv('IP_ROTATION_JITTER_PCT', str(rotation_jitter_pct))
        )
        
        # Tracking structures
        self.wallet_to_proxy: Dict[str, Tuple[str, datetime]] = {}
        self.shard_to_proxy: Dict[int, Tuple[str, datetime]] = {}
        self.traffic_type_proxy: Dict[Tuple[str, str], Tuple[str, datetime]] = {}
        
        # Statistics
        self.rotation_count = 0
        self.stick_count = 0
        
        logger.info(
            "IP manager initialized",
            proxy_count=len(self.proxy_list),
            ip_shard_size=self.ip_shard_size,
            ip_sticky_hours=self.ip_sticky_hours,
            faucet_ip_sticky_hours=self.faucet_ip_sticky_hours,
            rpc_ip_sticky_hours=self.rpc_ip_sticky_hours
        )
    
    def get_proxy_for_wallet(
        self,
        wallet_address: str,
        shard_id: Optional[int] = None,
        traffic_type: str = 'general'
    ) -> Optional[str]:
        """
        Get appropriate proxy for a wallet with stickiness enforcement.
        
        Args:
            wallet_address: Wallet address
            shard_id: Optional shard ID for shard-based routing
            traffic_type: Type of traffic ('faucet', 'rpc', 'general')
        
        Returns:
            Proxy URL or None if no proxies configured
        """
        if not self.proxy_list:
            return None
        
        # Determine stickiness window based on traffic type
        if traffic_type == 'faucet':
            sticky_hours = self.faucet_ip_sticky_hours
        elif traffic_type == 'rpc':
            sticky_hours = self.rpc_ip_sticky_hours
        else:
            sticky_hours = self.ip_sticky_hours
        
        # Add jitter to stickiness window
        jitter = random.uniform(-self.rotation_jitter_pct, self.rotation_jitter_pct)
        sticky_hours_with_jitter = sticky_hours * (1 + jitter)
        
        # Check if we have a sticky IP for this wallet
        key = (wallet_address, traffic_type)
        if key in self.traffic_type_proxy:
            proxy, assigned_at = self.traffic_type_proxy[key]
            age_hours = (datetime.utcnow() - assigned_at).total_seconds() / 3600
            
            if age_hours < sticky_hours_with_jitter:
                self.stick_count += 1
                logger.debug(
                    "Using sticky proxy",
                    wallet=wallet_address[:10],
                    traffic_type=traffic_type,
                    age_hours=round(age_hours, 2),
                    proxy_index=self.proxy_list.index(proxy) if proxy in self.proxy_list else -1
                )
                return proxy
        
        # Need to assign/rotate IP
        proxy = self._select_new_proxy(wallet_address, shard_id, traffic_type)
        self.traffic_type_proxy[key] = (proxy, datetime.utcnow())
        self.rotation_count += 1
        
        logger.info(
            "Assigned new proxy",
            wallet=wallet_address[:10],
            traffic_type=traffic_type,
            shard_id=shard_id,
            proxy_index=self.proxy_list.index(proxy) if proxy in self.proxy_list else -1
        )
        
        return proxy
    
    def _select_new_proxy(
        self,
        wallet_address: str,
        shard_id: Optional[int],
        traffic_type: str
    ) -> str:
        """
        Select a new proxy for assignment.
        
        Strategy: Use deterministic selection based on wallet/shard to maintain
        consistency while allowing for rotation over time.
        """
        if shard_id is not None:
            # Shard-based selection with rotation
            base_index = shard_id % len(self.proxy_list)
            rotation_offset = (int(time.time() / (self.ip_sticky_hours * 3600))) % len(self.proxy_list)
            index = (base_index + rotation_offset) % len(self.proxy_list)
        else:
            # Hash-based selection for individual wallets using hashlib for consistency
            hash_input = f"{wallet_address}{traffic_type}{int(time.time() / (self.ip_sticky_hours * 3600))}"
            hash_val = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
            index = hash_val % len(self.proxy_list)
        
        # Add small random offset to avoid patterns
        if len(self.proxy_list) > 1:
            offset = random.randint(0, min(2, len(self.proxy_list) - 1))
            index = (index + offset) % len(self.proxy_list)
        
        return self.proxy_list[index]
    
    def get_proxy_for_shard(
        self,
        shard_id: int,
        traffic_type: str = 'general'
    ) -> Optional[str]:
        """
        Get proxy for an entire shard with stickiness.
        
        Args:
            shard_id: Shard identifier
            traffic_type: Type of traffic ('faucet', 'rpc', 'general')
        
        Returns:
            Proxy URL or None if no proxies configured
        """
        if not self.proxy_list:
            return None
        
        # Determine stickiness window
        if traffic_type == 'faucet':
            sticky_hours = self.faucet_ip_sticky_hours
        elif traffic_type == 'rpc':
            sticky_hours = self.rpc_ip_sticky_hours
        else:
            sticky_hours = self.ip_sticky_hours
        
        # Check existing assignment
        key = (shard_id, traffic_type)
        if key in self.shard_to_proxy:
            proxy, assigned_at = self.shard_to_proxy[key]
            age_hours = (datetime.utcnow() - assigned_at).total_seconds() / 3600
            
            if age_hours < sticky_hours:
                return proxy
        
        # Assign new proxy
        proxy = self._select_new_proxy(f"shard_{shard_id}", shard_id, traffic_type)
        self.shard_to_proxy[key] = (proxy, datetime.utcnow())
        
        return proxy
    
    def force_rotation(
        self,
        wallet_address: Optional[str] = None,
        shard_id: Optional[int] = None,
        traffic_type: Optional[str] = None
    ):
        """
        Force immediate rotation for a wallet, shard, or traffic type.
        
        Args:
            wallet_address: Optional wallet to rotate
            shard_id: Optional shard to rotate
            traffic_type: Optional traffic type to rotate
        """
        if wallet_address and traffic_type:
            key = (wallet_address, traffic_type)
            if key in self.traffic_type_proxy:
                del self.traffic_type_proxy[key]
                logger.info(
                    "Forced proxy rotation",
                    wallet=wallet_address[:10],
                    traffic_type=traffic_type
                )
        
        if shard_id is not None and traffic_type:
            key = (shard_id, traffic_type)
            if key in self.shard_to_proxy:
                del self.shard_to_proxy[key]
                logger.info(
                    "Forced shard proxy rotation",
                    shard_id=shard_id,
                    traffic_type=traffic_type
                )
    
    def get_stats(self) -> Dict:
        """Get IP manager statistics."""
        return {
            'proxy_count': len(self.proxy_list),
            'rotation_count': self.rotation_count,
            'stick_count': self.stick_count,
            'active_wallet_assignments': len(self.traffic_type_proxy),
            'active_shard_assignments': len(self.shard_to_proxy),
            'ip_shard_size': self.ip_shard_size,
            'ip_sticky_hours': self.ip_sticky_hours
        }

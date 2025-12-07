"""
User-Agent rotation for anti-detection.

This module provides realistic User-Agent rotation with session persistence
and optional custom headers to mimic legitimate browser traffic patterns.

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
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from utils.logging_config import get_logger

logger = get_logger(__name__)


# Realistic User-Agent pool representing common browsers and versions
DEFAULT_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0",
    
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
    
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


class UserAgentRotator:
    """
    Manages User-Agent rotation with session persistence.
    
    Features:
    - Realistic UA pool with common browsers
    - Session-based persistence (UA sticks for a session/shard)
    - Optional custom headers per request
    - Load custom UA lists from file
    """
    
    def __init__(
        self,
        ua_list: Optional[List[str]] = None,
        ua_pool_path: Optional[str] = None,
        session_duration_hours: float = 12.0
    ):
        """
        Initialize User-Agent rotator.
        
        Args:
            ua_list: Custom list of User-Agents
            ua_pool_path: Path to file with User-Agents (one per line)
            session_duration_hours: How long to stick with same UA
        """
        # Load User-Agents
        if ua_list:
            self.user_agents = ua_list
        elif ua_pool_path or os.getenv('UA_POOL_PATH'):
            path = ua_pool_path or os.getenv('UA_POOL_PATH')
            self.user_agents = self._load_ua_from_file(path)
        else:
            ua_list_env = os.getenv('UA_LIST')
            if ua_list_env:
                self.user_agents = [ua.strip() for ua in ua_list_env.split('|||') if ua.strip()]
            else:
                self.user_agents = DEFAULT_USER_AGENTS.copy()
        
        self.session_duration_hours = float(
            os.getenv('UA_SESSION_DURATION_HOURS', str(session_duration_hours))
        )
        
        # Tracking
        self.session_ua: Dict[str, tuple] = {}  # session_id -> (ua, assigned_at)
        self.wallet_ua: Dict[str, tuple] = {}   # wallet -> (ua, assigned_at)
        
        logger.info(
            "User-Agent rotator initialized",
            ua_count=len(self.user_agents),
            session_duration_hours=self.session_duration_hours
        )
    
    def _load_ua_from_file(self, path: str) -> List[str]:
        """Load User-Agents from a file."""
        try:
            with open(path, 'r') as f:
                uas = [line.strip() for line in f if line.strip()]
            logger.info("Loaded User-Agents from file", path=path, count=len(uas))
            return uas
        except FileNotFoundError:
            logger.warning(
                "User-Agent file not found, using defaults",
                path=path
            )
            return DEFAULT_USER_AGENTS.copy()
    
    def get_user_agent(
        self,
        session_id: Optional[str] = None,
        wallet_address: Optional[str] = None,
        shard_id: Optional[int] = None
    ) -> str:
        """
        Get User-Agent for a session/wallet with stickiness.
        
        Args:
            session_id: Session identifier
            wallet_address: Wallet address
            shard_id: Shard ID
        
        Returns:
            User-Agent string
        """
        # Determine identifier for stickiness
        identifier = session_id or wallet_address or f"shard_{shard_id}" if shard_id is not None else "default"
        
        # Check if we have an active UA for this identifier
        if identifier in self.session_ua:
            ua, assigned_at = self.session_ua[identifier]
            age_hours = (datetime.utcnow() - assigned_at).total_seconds() / 3600
            
            if age_hours < self.session_duration_hours:
                return ua
        
        # Assign new UA
        ua = random.choice(self.user_agents)
        self.session_ua[identifier] = (ua, datetime.utcnow())
        
        logger.debug(
            "Assigned new User-Agent",
            identifier=identifier[:20] if len(identifier) > 20 else identifier,
            ua_preview=ua[:50]
        )
        
        return ua
    
    def get_headers(
        self,
        session_id: Optional[str] = None,
        wallet_address: Optional[str] = None,
        shard_id: Optional[int] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Get complete headers including User-Agent and common browser headers.
        
        Args:
            session_id: Session identifier
            wallet_address: Wallet address
            shard_id: Shard ID
            extra_headers: Additional headers to include
        
        Returns:
            Dictionary of HTTP headers
        """
        ua = self.get_user_agent(session_id, wallet_address, shard_id)
        
        # Build realistic browser headers
        headers = {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Add extra headers if provided
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def rotate(self, identifier: str):
        """Force rotation of User-Agent for an identifier."""
        if identifier in self.session_ua:
            del self.session_ua[identifier]
            logger.info("Forced User-Agent rotation", identifier=identifier[:20])
    
    def get_stats(self) -> Dict:
        """Get UA rotator statistics."""
        return {
            'ua_pool_size': len(self.user_agents),
            'active_sessions': len(self.session_ua),
            'session_duration_hours': self.session_duration_hours
        }

"""
Multi-chain faucet automation with cooldown management and human-like behavior.

This module orchestrates automated faucet claims across multiple blockchain networks
with built-in cooldown tracking, rate limiting, and anti-detection measures including
IP rotation, user-agent spoofing, and randomized timing patterns.

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
import asyncio
import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
import yaml
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

from utils.database import (
    Wallet, FaucetRequest, FaucetCooldown,
    get_db_session, db_manager
)
from utils.logging_config import get_logger, log_faucet_request
from modules.captcha_broker import CaptchaBroker
from modules.anti_detection import AntiDetection

logger = get_logger(__name__)


class FaucetConfig:
    """Faucet configuration loaded from YAML."""
    
    def __init__(self, config_path: str = None):
        """Load faucet configuration.
        
        Args:
            config_path: Path to faucets.yaml
        """
        self.config_path = config_path or os.getenv(
            "FAUCET_CONFIG_PATH",
            "config/faucets.yaml"
        )
        self.config = self._load_config()
        self.chains = self.config.get('chains', {})
        self.global_settings = self.config.get('global_settings', {})
    
    def _load_config(self) -> dict:
        """Load YAML configuration."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(
                    "faucet_config_loaded",
                    config_path=self.config_path,
                    chains=len(config.get('chains', {}))
                )
                return config
        except Exception as e:
            logger.error(
                "faucet_config_load_failed",
                config_path=self.config_path,
                error=str(e)
            )
            return {'chains': {}, 'global_settings': {}}
    
    def get_chain_faucets(self, chain: str) -> List[Dict]:
        """Get all enabled faucets for a chain.
        
        Args:
            chain: Chain identifier
            
        Returns:
            List of faucet configurations
        """
        chain_config = self.chains.get(chain, {})
        faucets = chain_config.get('faucets', [])
        
        # Filter enabled faucets and sort by priority
        enabled = [f for f in faucets if f.get('enabled', True)]
        enabled.sort(key=lambda x: x.get('priority', 999))
        
        return enabled
    
    def get_all_chains(self) -> List[str]:
        """Get list of all configured chains."""
        return list(self.chains.keys())


class FaucetWorker:
    """Worker for claiming from individual faucets with rate limiting and cooldowns."""
    
    def __init__(
        self,
        config: FaucetConfig,
        captcha_broker: CaptchaBroker,
        proxy_list: Optional[List[str]] = None,
        anti_detection: Optional[AntiDetection] = None
    ):
        """Initialize faucet worker.
        
        Args:
            config: Faucet configuration
            captcha_broker: Captcha solving broker
            proxy_list: Optional list of proxy URLs
            anti_detection: Optional anti-detection coordinator
        """
        self.config = config
        self.captcha_broker = captcha_broker
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        
        # Initialize anti-detection if not provided
        self.anti_detection = anti_detection or AntiDetection(proxy_list=proxy_list)
        
        # Worker settings
        self.timeout = int(os.getenv("FAUCET_REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("FAUCET_RETRY_MAX_ATTEMPTS", "3"))
        self.backoff_min = int(os.getenv("FAUCET_RETRY_BACKOFF_MIN", "5"))
        self.backoff_max = int(os.getenv("FAUCET_RETRY_BACKOFF_MAX", "60"))
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation."""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def _generate_idempotency_key(
        self,
        faucet_name: str,
        wallet_address: str,
        chain: str,
        date: datetime
    ) -> str:
        """Generate idempotency key for deduplication.
        
        Args:
            faucet_name: Name of faucet
            wallet_address: Wallet address
            chain: Chain identifier
            date: Date for the request
            
        Returns:
            Idempotency key
        """
        date_str = date.strftime("%Y-%m-%d")
        key_input = f"{faucet_name}:{wallet_address}:{chain}:{date_str}"
        return hashlib.sha256(key_input.encode()).hexdigest()
    
    def _check_cooldown(
        self,
        faucet_name: str,
        wallet_address: str,
        chain: str,
        cooldown_hours: int
    ) -> Tuple[bool, Optional[datetime]]:
        """Check if faucet is in cooldown period.
        
        Args:
            faucet_name: Name of faucet
            wallet_address: Wallet address
            chain: Chain identifier
            cooldown_hours: Cooldown period in hours
            
        Returns:
            Tuple of (is_in_cooldown, cooldown_expires_at)
        """
        with get_db_session() as session:
            cooldown = session.query(FaucetCooldown).filter_by(
                faucet_name=faucet_name,
                wallet_address=wallet_address,
                chain=chain
            ).first()
            
            if not cooldown:
                return False, None
            
            now = datetime.utcnow()
            if cooldown.cooldown_until > now:
                return True, cooldown.cooldown_until
            
            return False, None
    
    def _update_cooldown(
        self,
        faucet_name: str,
        wallet_address: str,
        chain: str,
        cooldown_hours: int,
        daily_limit: int
    ):
        """Update cooldown record after successful claim.
        
        Args:
            faucet_name: Name of faucet
            wallet_address: Wallet address
            chain: Chain identifier
            cooldown_hours: Cooldown period in hours
            daily_limit: Daily request limit
        """
        with get_db_session() as session:
            now = datetime.utcnow()
            cooldown_until = now + timedelta(hours=cooldown_hours)
            
            cooldown = session.query(FaucetCooldown).filter_by(
                faucet_name=faucet_name,
                wallet_address=wallet_address,
                chain=chain
            ).first()
            
            if cooldown:
                # Check if it's a new day
                if cooldown.last_request_at.date() < now.date():
                    cooldown.requests_today = 1
                else:
                    cooldown.requests_today += 1
                
                cooldown.last_request_at = now
                cooldown.cooldown_until = cooldown_until
            else:
                cooldown = FaucetCooldown(
                    faucet_name=faucet_name,
                    wallet_address=wallet_address,
                    chain=chain,
                    last_request_at=now,
                    cooldown_until=cooldown_until,
                    requests_today=1,
                    daily_limit=daily_limit
                )
                session.add(cooldown)
            
            session.commit()
    
    async def claim_from_faucet(
        self,
        wallet: Wallet,
        faucet_config: Dict,
        chain: str
    ) -> bool:
        """Claim tokens from a single faucet.
        
        Args:
            wallet: Wallet to fund
            faucet_config: Faucet configuration
            chain: Chain identifier
            
        Returns:
            True if successful, False otherwise
        """
        faucet_name = faucet_config['name']
        
        # Generate idempotency key
        idempotency_key = self._generate_idempotency_key(
            faucet_name,
            wallet.address,
            chain,
            datetime.utcnow()
        )
        
        # Check for existing request today
        with get_db_session() as session:
            existing = session.query(FaucetRequest).filter_by(
                idempotency_key=idempotency_key
            ).first()
            
            if existing and existing.status == 'success':
                logger.info(
                    "faucet_already_claimed_today",
                    wallet=wallet.address,
                    chain=chain,
                    faucet=faucet_name
                )
                return True
        
        # Check cooldown first (more efficient to skip if in cooldown)
        cooldown_hours = faucet_config.get('cooldown_hours', 24)
        extended_cooldown_hours = self.anti_detection.get_overcooldown_delay(
            cooldown_hours * 3600
        ) / 3600.0
        
        in_cooldown, cooldown_until = self._check_cooldown(
            faucet_name,
            wallet.address,
            chain,
            int(extended_cooldown_hours)
        )
        
        if in_cooldown:
            logger.info(
                "faucet_in_cooldown",
                wallet=wallet.address,
                chain=chain,
                faucet=faucet_name,
                cooldown_until=cooldown_until.isoformat()
            )
            return False
        
        # Check if we should skip this faucet claim for anti-detection
        if self.anti_detection.should_skip_faucet(wallet.address):
            logger.info(
                "faucet_skipped_for_anti_detection",
                wallet=wallet.address,
                chain=chain,
                faucet=faucet_name
            )
            return False
        
        # Create request record
        with get_db_session() as session:
            request = FaucetRequest(
                wallet_id=wallet.id,
                chain=chain,
                faucet_name=faucet_name,
                idempotency_key=idempotency_key,
                status='in_progress',
                amount_requested=faucet_config.get('amount', '0'),
                requested_at=datetime.utcnow()
            )
            session.add(request)
            session.commit()
            request_id = request.id
        
        # Attempt to claim
        try:
            # Solve captcha if required
            captcha_token = None
            if faucet_config.get('requires_captcha', False):
                logger.info(
                    "solving_captcha",
                    wallet=wallet.address,
                    faucet=faucet_name
                )
                
                captcha_token = self.captcha_broker.solve_captcha(
                    site_url=faucet_config['url'],
                    site_key=faucet_config.get('captcha_site_key', 'unknown'),
                    captcha_type=faucet_config.get('captcha_type', 'recaptcha_v2')
                )
                
                if not captcha_token:
                    raise Exception("Failed to solve captcha")
            
            # Make faucet request
            success = await self._make_faucet_request(
                wallet.address,
                faucet_config,
                captcha_token
            )
            
            if success:
                # Update request as successful
                with get_db_session() as session:
                    request = session.query(FaucetRequest).get(request_id)
                    request.status = 'success'
                    request.completed_at = datetime.utcnow()
                    request.captcha_solved = captcha_token is not None
                    session.commit()
                
                # Update cooldown
                self._update_cooldown(
                    faucet_name,
                    wallet.address,
                    chain,
                    cooldown_hours,
                    faucet_config.get('daily_limit', 1)
                )
                
                log_faucet_request(
                    logger,
                    wallet=wallet.address,
                    chain=chain,
                    faucet=faucet_name,
                    status='success'
                )
                
                return True
            else:
                raise Exception("Faucet request failed")
        
        except Exception as e:
            # Update request as failed
            with get_db_session() as session:
                request = session.query(FaucetRequest).get(request_id)
                request.status = 'failed'
                request.last_error = str(e)
                request.error_class = type(e).__name__
                request.attempts += 1
                session.commit()
            
            log_faucet_request(
                logger,
                wallet=wallet.address,
                chain=chain,
                faucet=faucet_name,
                status='failed',
                error=str(e)
            )
            
            return False
    
    async def _make_faucet_request(
        self,
        address: str,
        faucet_config: Dict,
        captcha_token: Optional[str]
    ) -> bool:
        """Make HTTP request to faucet endpoint.
        
        Args:
            address: Wallet address to fund
            faucet_config: Faucet configuration
            captcha_token: Optional captcha token
            
        Returns:
            True if successful
        """
        method = faucet_config.get('method', 'POST')
        
        # Handle CLI-based faucets (like Solana)
        if method == 'CLI':
            logger.info(
                "faucet_cli_method",
                address=address,
                faucet=faucet_config['name'],
                notes=faucet_config.get('notes', '')
            )
            # CLI faucets require external tooling and are not automated here
            return False
        
        # Skip faucets without URLs or endpoints
        if not faucet_config.get('url'):
            logger.warning(
                "faucet_no_url",
                faucet=faucet_config['name']
            )
            return False
        
        # Build URL
        url = faucet_config['url']
        api_endpoint = faucet_config.get('api_endpoint')
        if api_endpoint:
            url = url.rstrip('/') + '/' + api_endpoint.lstrip('/')
        
        # Get payload format and address field name
        payload_format = faucet_config.get('payload_format', 'json')
        address_field = faucet_config.get('address_field', 'address')
        
        # Build request payload with configurable address field
        payload = {
            address_field: address
        }
        
        # Add alternative address fields for compatibility
        if address_field != 'address':
            payload['address'] = address
        if address_field != 'wallet':
            payload['wallet'] = address
        
        # Add captcha token if present
        if captcha_token:
            payload['captcha'] = captcha_token
            payload['g-recaptcha-response'] = captcha_token
            payload['h-captcha-response'] = captcha_token  # For hCaptcha
            payload['cf-turnstile-response'] = captcha_token  # For Cloudflare Turnstile
        
        # Get anti-detection request config
        request_config = self.anti_detection.get_request_config(
            wallet_address=address,
            shard_id=None,
            traffic_type='faucet'
        )
        
        if not request_config['should_proceed']:
            logger.info(
                "faucet_request_delayed_by_anti_detection",
                address=address,
                delay_seconds=request_config.get('delay_seconds', 0)
            )
            if request_config.get('delay_seconds', 0) > 0:
                await asyncio.sleep(min(request_config['delay_seconds'], 60))
            return False
        
        proxy = request_config.get('proxy') or self._get_next_proxy()
        headers = request_config.get('headers', {})
        
        # Merge custom headers from faucet config
        if 'headers' in faucet_config and faucet_config['headers']:
            headers.update(faucet_config['headers'])
        
        # Add jitter before request
        if self.config.global_settings.get('enable_jitter', True):
            jitter_min = self.config.global_settings.get('jitter_min', 1)
            jitter_max = self.config.global_settings.get('jitter_max', 30)
            base_delay = random.uniform(jitter_min, jitter_max)
            jittered_delay = self.anti_detection.get_jittered_delay(base_delay)
            await asyncio.sleep(jittered_delay)
        
        # Make request
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                if method == 'POST':
                    # Choose content type based on payload format
                    if payload_format == 'form':
                        # Send as form data
                        async with session.post(
                            url,
                            data=payload,
                            proxy=proxy,
                            headers=headers
                        ) as response:
                            return await self._handle_faucet_response(response, url, address)
                    else:
                        # Send as JSON (default)
                        async with session.post(
                            url,
                            json=payload,
                            proxy=proxy,
                            headers=headers
                        ) as response:
                            return await self._handle_faucet_response(response, url, address)
                else:
                    # GET request
                    async with session.get(
                        url,
                        params=payload,
                        proxy=proxy,
                        headers=headers
                    ) as response:
                        return await self._handle_faucet_response(response, url, address)
            
            except aiohttp.ClientError as e:
                logger.warning(
                    "faucet_network_error",
                    url=url,
                    error=str(e)
                )
                return False
    
    async def _handle_faucet_response(
        self,
        response: aiohttp.ClientResponse,
        url: str,
        address: str
    ) -> bool:
        """Handle and parse faucet response.
        
        Args:
            response: HTTP response object
            url: Request URL
            address: Wallet address
            
        Returns:
            True if successful
        """
        # Record request outcome for auto-throttle
        success = response.status in [200, 201]
        self.anti_detection.record_request_outcome(
            identifier=f"faucet_{address[:10]}",
            success=success,
            status_code=response.status
        )
        
        # Handle specific status codes
        if response.status == 429:
            error_text = await response.text()
            logger.warning(
                "faucet_rate_limited",
                url=url,
                response_body=error_text[:200]
            )
            raise Exception(f"Rate limited: {error_text[:100]}")
        elif response.status >= 500:
            error_text = await response.text()
            logger.error(
                "faucet_server_error",
                url=url,
                status=response.status,
                response_body=error_text[:200]
            )
            raise Exception(f"Server error {response.status}: {error_text[:100]}")
        elif response.status >= 400:
            # Try to extract error message from response
            try:
                error_text = await response.text()
                # Try to parse as JSON if content type indicates it
                error_msg = error_text[:100]
                if response.content_type == 'application/json' and error_text:
                    try:
                        import json
                        error_json = json.loads(error_text)
                        error_msg = error_json.get('error', error_json.get('message', error_text[:100]))
                    except json.JSONDecodeError:
                        pass  # Use text as-is
            except Exception as e:
                error_msg = f"HTTP {response.status}"
            
            logger.warning(
                "faucet_request_failed",
                url=url,
                status=response.status,
                error=error_msg
            )
            raise Exception(f"Faucet request failed: {error_msg}")
        
        # Log successful response for debugging
        if success:
            try:
                response_text = await response.text()
                logger.info(
                    "faucet_request_success",
                    url=url,
                    status=response.status,
                    response_preview=response_text[:200] if response_text else "empty"
                )
            except Exception:
                pass
        
        return success


class FaucetOrchestrator:
    """Orchestrate faucet funding across multiple wallets and chains."""
    
    def __init__(
        self,
        config_path: str = None,
        concurrency: int = None
    ):
        """Initialize faucet orchestrator.
        
        Args:
            config_path: Path to faucets.yaml
            concurrency: Max concurrent workers
        """
        self.config = FaucetConfig(config_path)
        self.captcha_broker = CaptchaBroker()
        
        # Load proxy list
        proxy_env = os.getenv("PROXY_LIST", "")
        self.proxy_list = [p.strip() for p in proxy_env.split(',') if p.strip()]
        
        self.concurrency = concurrency or int(
            os.getenv("FAUCET_WORKER_CONCURRENCY", "5")
        )
        
        # Initialize anti-detection coordinator
        self.anti_detection = AntiDetection(proxy_list=self.proxy_list)
        
        self.worker = FaucetWorker(
            self.config,
            self.captcha_broker,
            self.proxy_list,
            self.anti_detection
        )
    
    async def fund_wallet(
        self,
        wallet: Wallet,
        chains: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Fund a single wallet across specified chains.
        
        Args:
            wallet: Wallet to fund
            chains: List of chains (None = all chains)
            
        Returns:
            Dictionary mapping chain to success status
        """
        chains = chains or self.config.get_all_chains()
        results = {}
        
        for chain in chains:
            faucets = self.config.get_chain_faucets(chain)
            
            if not faucets:
                logger.warning(f"No faucets configured for chain: {chain}")
                continue
            
            # Try each faucet until one succeeds
            success = False
            for faucet_config in faucets:
                try:
                    success = await self.worker.claim_from_faucet(
                        wallet,
                        faucet_config,
                        chain
                    )
                    
                    if success:
                        break
                    
                except Exception as e:
                    logger.error(
                        "faucet_claim_error",
                        wallet=wallet.address,
                        chain=chain,
                        faucet=faucet_config['name'],
                        error=str(e)
                    )
            
            results[chain] = success
        
        return results
    
    async def fund_wallets(
        self,
        wallets: List[Wallet],
        chains: Optional[List[str]] = None,
        shard_stagger: bool = True
    ) -> Dict[str, Dict[str, int]]:
        """Fund multiple wallets with human-like staggering.
        
        Args:
            wallets: List of wallets to fund
            chains: List of chains (None = all chains)
            shard_stagger: Whether to stagger by shard
            
        Returns:
            Summary statistics
        """
        chains = chains or self.config.get_all_chains()
        
        # Group wallets by shard if staggering enabled
        if shard_stagger:
            shards = {}
            for wallet in wallets:
                shard_id = wallet.shard_id
                if shard_id not in shards:
                    shards[shard_id] = []
                shards[shard_id].append(wallet)
        else:
            shards = {0: wallets}
        
        stats = {
            'total': len(wallets),
            'success': 0,
            'failed': 0,
            'by_chain': {}
        }
        
        # Process each shard with staggering
        for shard_id, shard_wallets in sorted(shards.items()):
            logger.info(
                "processing_shard",
                shard_id=shard_id,
                wallet_count=len(shard_wallets)
            )
            
            # Create tasks for this shard with semaphore for concurrency
            semaphore = asyncio.Semaphore(self.concurrency)
            
            async def fund_with_semaphore(wallet):
                async with semaphore:
                    return await self.fund_wallet(wallet, chains)
            
            tasks = [fund_with_semaphore(w) for w in shard_wallets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for result in results:
                if isinstance(result, Exception):
                    stats['failed'] += 1
                    continue
                
                for chain, success in result.items():
                    if chain not in stats['by_chain']:
                        stats['by_chain'][chain] = {'success': 0, 'failed': 0}
                    
                    if success:
                        stats['by_chain'][chain]['success'] += 1
                        stats['success'] += 1
                    else:
                        stats['by_chain'][chain]['failed'] += 1
                        stats['failed'] += 1
            
            # Stagger between shards
            if shard_stagger and shard_id < max(shards.keys()):
                stagger_seconds = int(os.getenv("STAGGER_REQUESTS_SECONDS", "60"))
                jitter = random.uniform(0, stagger_seconds * 0.3)
                await asyncio.sleep(stagger_seconds + jitter)
        
        logger.info(
            "funding_completed",
            stats=stats
        )
        
        return stats

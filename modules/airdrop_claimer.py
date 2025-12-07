"""
Airdrop claiming module for automated airdrop detection and claiming.

This module provides functionality to:
- Manage airdrop configurations via YAML
- Check wallet eligibility for airdrops
- Execute airdrop claims with multiple methods
- Track claim status in database

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
import yaml
import asyncio
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dateutil import parser as date_parser
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.database import get_db_session, AirdropClaim, Wallet, WalletAction
from utils.logging_config import get_logger
from modules.wallet_manager import WalletManager
from modules.anti_detection import AntiDetection

logger = get_logger(__name__)


class AirdropRegistry:
    """Manage airdrop configurations and registry."""
    
    def __init__(self, config_path: str = "config/airdrops.yaml"):
        """Initialize airdrop registry.
        
        Args:
            config_path: Path to airdrops configuration YAML file
        """
        self.config_path = config_path
        self.airdrops = {}
        self.load_config()
    
    def load_config(self):
        """Load airdrop configurations from YAML file."""
        if not os.path.exists(self.config_path):
            logger.warning(
                "airdrop_config_missing",
                config_path=self.config_path
            )
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not config or 'airdrops' not in config:
                logger.warning("airdrop_config_empty", config_path=self.config_path)
                return
            
            self.airdrops = config['airdrops']
            
            logger.info(
                "airdrop_config_loaded",
                config_path=self.config_path,
                airdrop_count=len(self.airdrops)
            )
        
        except Exception as e:
            logger.error(
                "airdrop_config_load_failed",
                config_path=self.config_path,
                error=str(e)
            )
    
    def get_airdrop(self, name: str) -> Optional[Dict]:
        """Get airdrop configuration by name.
        
        Args:
            name: Airdrop name
            
        Returns:
            Airdrop configuration dictionary or None
        """
        return self.airdrops.get(name)
    
    def get_all_airdrops(self) -> Dict[str, Dict]:
        """Get all airdrop configurations.
        
        Returns:
            Dictionary of airdrop configurations
        """
        return self.airdrops
    
    def get_active_airdrops(self, chain: Optional[str] = None) -> Dict[str, Dict]:
        """Get active (claimable) airdrops.
        
        Args:
            chain: Filter by chain (optional)
            
        Returns:
            Dictionary of active airdrop configurations
        """
        active = {}
        now = datetime.now(timezone.utc)
        
        for name, config in self.airdrops.items():
            # Check if enabled
            if not config.get('enabled', True):
                continue
            
            # Check if claimable status
            if config.get('status') != 'claimable':
                continue
            
            # Check chain filter
            if chain and config.get('chain') != chain:
                continue
            
            # Check claim window
            try:
                claim_start = date_parser.parse(config.get('claim_start', '2000-01-01T00:00:00Z'))
                claim_end = date_parser.parse(config.get('claim_end', '2099-12-31T23:59:59Z'))
                
                if claim_start <= now <= claim_end:
                    active[name] = config
            except Exception as e:
                logger.warning(
                    "airdrop_date_parse_failed",
                    airdrop=name,
                    error=str(e)
                )
        
        return active
    
    def get_airdrops_by_status(self, status: str) -> Dict[str, Dict]:
        """Get airdrops by status.
        
        Args:
            status: Status to filter by (upcoming, claimable, ended)
            
        Returns:
            Dictionary of filtered airdrop configurations
        """
        return {
            name: config
            for name, config in self.airdrops.items()
            if config.get('status') == status
        }


class EligibilityChecker:
    """Check wallet eligibility for airdrops."""
    
    def __init__(self):
        """Initialize eligibility checker."""
        pass
    
    async def check_eligibility(
        self,
        wallet: Wallet,
        airdrop_config: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if wallet is eligible for an airdrop.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            
        Returns:
            Tuple of (is_eligible, reason, metadata)
        """
        airdrop_name = airdrop_config.get('name', 'Unknown')
        
        # Check required actions
        min_actions = airdrop_config.get('min_actions', 0)
        required_actions = airdrop_config.get('required_actions', [])
        
        # Query wallet actions from database
        with get_db_session() as session:
            wallet_actions = session.query(WalletAction).filter(
                WalletAction.wallet_id == wallet.id,
                WalletAction.status == 'success'
            ).all()
            
            # Count actions by type
            action_counts = {}
            for action in wallet_actions:
                action_type = action.action_type
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
            # Check if required actions are met
            for req_action in required_actions:
                if action_counts.get(req_action, 0) == 0:
                    reason = f"Missing required action: {req_action}"
                    logger.debug(
                        "wallet_ineligible",
                        wallet=wallet.address[:10],
                        airdrop=airdrop_name,
                        reason=reason
                    )
                    return False, reason, None
            
            # Check minimum action count
            total_actions = sum(action_counts.values())
            if total_actions < min_actions:
                reason = f"Insufficient actions: {total_actions}/{min_actions}"
                logger.debug(
                    "wallet_ineligible",
                    wallet=wallet.address[:10],
                    airdrop=airdrop_name,
                    reason=reason
                )
                return False, reason, None
        
        # Check chain match
        if wallet.chain != airdrop_config.get('chain'):
            reason = f"Chain mismatch: {wallet.chain} != {airdrop_config.get('chain')}"
            return False, reason, None
        
        # Perform method-specific eligibility check
        claim_method = airdrop_config.get('claim_method', 'direct')
        
        if claim_method == 'merkle':
            return await self._check_merkle_eligibility(wallet, airdrop_config)
        elif claim_method == 'api':
            return await self._check_api_eligibility(wallet, airdrop_config)
        elif claim_method == 'direct':
            # For direct claims, basic checks are sufficient
            return True, "Eligible for direct claim", {'action_counts': action_counts}
        else:
            return False, f"Unknown claim method: {claim_method}", None
    
    async def _check_merkle_eligibility(
        self,
        wallet: Wallet,
        airdrop_config: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check merkle proof-based eligibility.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            
        Returns:
            Tuple of (is_eligible, reason, metadata)
        """
        # In a real implementation, this would:
        # 1. Query the eligibility API for merkle proof
        # 2. Verify the proof against the contract
        # 3. Return eligibility status with proof data
        
        eligibility_api = airdrop_config.get('eligibility_api')
        
        if not eligibility_api:
            logger.debug(
                "merkle_no_api",
                wallet=wallet.address[:10],
                airdrop=airdrop_config.get('name')
            )
            # If no API, assume eligible if basic checks passed
            return True, "Eligible (no merkle API configured)", None
        
        # Simulated API check (in real implementation, make HTTP request)
        logger.debug(
            "merkle_check_simulated",
            wallet=wallet.address[:10],
            api=eligibility_api
        )
        
        # For testnet/development, assume eligible
        return True, "Eligible (merkle proof available)", {
            'proof': ['0x' + '00' * 32],  # Placeholder
            'amount': '1000000000000000000'  # 1 token
        }
    
    async def _check_api_eligibility(
        self,
        wallet: Wallet,
        airdrop_config: Dict
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check API-based eligibility.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            
        Returns:
            Tuple of (is_eligible, reason, metadata)
        """
        # In a real implementation, this would:
        # 1. Make HTTP request to eligibility API
        # 2. Parse response for eligibility status
        # 3. Return status with any claim metadata
        
        eligibility_api = airdrop_config.get('eligibility_api')
        
        if not eligibility_api:
            return False, "No eligibility API configured", None
        
        # Simulated API check (in real implementation, make HTTP request)
        logger.debug(
            "api_check_simulated",
            wallet=wallet.address[:10],
            api=eligibility_api
        )
        
        # For testnet/development, assume eligible
        return True, "Eligible (API check passed)", {
            'amount': '500000000000000000'  # 0.5 tokens
        }


class AirdropClaimer:
    """Execute airdrop claims for eligible wallets."""
    
    def __init__(
        self,
        wallet_manager: Optional[WalletManager] = None,
        anti_detection: Optional[AntiDetection] = None
    ):
        """Initialize airdrop claimer.
        
        Args:
            wallet_manager: Wallet manager instance
            anti_detection: Anti-detection module instance
        """
        self.wallet_manager = wallet_manager or WalletManager()
        self.anti_detection = anti_detection or AntiDetection()
        self.registry = AirdropRegistry()
        self.eligibility_checker = EligibilityChecker()
    
    async def check_and_claim_airdrops(
        self,
        wallets: List[Wallet],
        airdrop_name: Optional[str] = None,
        check_only: bool = False,
        shard_id: Optional[int] = None
    ) -> Dict:
        """Check eligibility and claim airdrops for multiple wallets.
        
        Args:
            wallets: List of wallet records
            airdrop_name: Specific airdrop to check/claim (optional)
            check_only: Only check eligibility, don't claim
            shard_id: Shard ID for tracking
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_wallets': len(wallets),
            'total_checks': 0,
            'eligible': 0,
            'ineligible': 0,
            'claimed': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Get airdrops to check
        if airdrop_name:
            airdrop_config = self.registry.get_airdrop(airdrop_name)
            if not airdrop_config:
                logger.error("airdrop_not_found", airdrop=airdrop_name)
                return stats
            airdrops_to_check = {airdrop_name: airdrop_config}
        else:
            airdrops_to_check = self.registry.get_active_airdrops()
        
        if not airdrops_to_check:
            logger.warning("no_active_airdrops")
            return stats
        
        logger.info(
            "checking_airdrops",
            wallet_count=len(wallets),
            airdrop_count=len(airdrops_to_check),
            check_only=check_only
        )
        
        # Process each wallet
        for wallet in wallets:
            # Apply anti-detection skip logic
            if self.anti_detection.should_skip_action(wallet.address):
                stats['skipped'] += 1
                continue
            
            # Check each airdrop
            for airdrop_name, airdrop_config in airdrops_to_check.items():
                stats['total_checks'] += 1
                
                # Check if already claimed
                with get_db_session() as session:
                    existing_claim = session.query(AirdropClaim).filter(
                        AirdropClaim.wallet_id == wallet.id,
                        AirdropClaim.airdrop_name == airdrop_name,
                        AirdropClaim.status == 'claimed'
                    ).first()
                    
                    if existing_claim:
                        logger.debug(
                            "already_claimed",
                            wallet=wallet.address[:10],
                            airdrop=airdrop_name
                        )
                        continue
                
                # Check eligibility
                is_eligible, reason, metadata = await self.eligibility_checker.check_eligibility(
                    wallet, airdrop_config
                )
                
                # Record check result
                self._record_check(wallet, airdrop_name, airdrop_config, is_eligible, reason)
                
                if not is_eligible:
                    stats['ineligible'] += 1
                    continue
                
                stats['eligible'] += 1
                
                # Claim if not check-only mode
                if not check_only:
                    # Add human-like delay
                    delay = self.anti_detection.get_jittered_delay(
                        base_delay=random.uniform(2.0, 5.0)
                    )
                    await asyncio.sleep(delay)
                    
                    # Execute claim
                    success = await self._execute_claim(
                        wallet, airdrop_name, airdrop_config, metadata
                    )
                    
                    if success:
                        stats['claimed'] += 1
                    else:
                        stats['failed'] += 1
        
        logger.info("airdrop_check_complete", stats=stats)
        return stats
    
    def _record_check(
        self,
        wallet: Wallet,
        airdrop_name: str,
        airdrop_config: Dict,
        is_eligible: bool,
        reason: Optional[str]
    ):
        """Record eligibility check in database.
        
        Args:
            wallet: Wallet database record
            airdrop_name: Airdrop name
            airdrop_config: Airdrop configuration
            is_eligible: Whether wallet is eligible
            reason: Eligibility check reason/message
        """
        with get_db_session() as session:
            # Check for existing record
            claim = session.query(AirdropClaim).filter(
                AirdropClaim.wallet_id == wallet.id,
                AirdropClaim.airdrop_name == airdrop_name
            ).first()
            
            if not claim:
                claim = AirdropClaim(
                    wallet_id=wallet.id,
                    airdrop_name=airdrop_name,
                    chain=airdrop_config.get('chain', wallet.chain),
                    status='eligible' if is_eligible else 'ineligible',
                    checked_at=datetime.now(timezone.utc)
                )
                session.add(claim)
            else:
                claim.status = 'eligible' if is_eligible else 'ineligible'
                claim.checked_at = datetime.now(timezone.utc)
            
            if not is_eligible and reason:
                claim.error_message = reason
            
            session.commit()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _execute_claim(
        self,
        wallet: Wallet,
        airdrop_name: str,
        airdrop_config: Dict,
        metadata: Optional[Dict]
    ) -> bool:
        """Execute airdrop claim transaction.
        
        Args:
            wallet: Wallet database record
            airdrop_name: Airdrop name
            airdrop_config: Airdrop configuration
            metadata: Eligibility metadata (proof, amount, etc.)
            
        Returns:
            True if claim succeeded, False otherwise
        """
        claim_method = airdrop_config.get('claim_method', 'direct')
        
        logger.info(
            "executing_claim",
            wallet=wallet.address[:10],
            airdrop=airdrop_name,
            method=claim_method,
            chain=wallet.chain
        )
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(
                wallet.address,
                wallet.chain
            )
            
            if not private_key:
                logger.error(
                    "private_key_not_found",
                    wallet=wallet.address[:10]
                )
                self._record_claim_failure(
                    wallet, airdrop_name, "Private key not found"
                )
                return False
            
            # Execute claim based on method
            if claim_method == 'merkle':
                tx_hash = await self._claim_merkle(
                    wallet, airdrop_config, metadata, private_key
                )
            elif claim_method == 'api':
                tx_hash = await self._claim_api(
                    wallet, airdrop_config, metadata, private_key
                )
            elif claim_method == 'direct':
                tx_hash = await self._claim_direct(
                    wallet, airdrop_config, metadata, private_key
                )
            else:
                raise ValueError(f"Unknown claim method: {claim_method}")
            
            # Record successful claim
            self._record_claim_success(
                wallet, airdrop_name, airdrop_config, tx_hash, metadata
            )
            
            return True
        
        except Exception as e:
            logger.error(
                "claim_failed",
                wallet=wallet.address[:10],
                airdrop=airdrop_name,
                error=str(e)
            )
            self._record_claim_failure(wallet, airdrop_name, str(e))
            return False
    
    async def _claim_merkle(
        self,
        wallet: Wallet,
        airdrop_config: Dict,
        metadata: Optional[Dict],
        private_key: str
    ) -> str:
        """Execute merkle proof-based claim.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            metadata: Claim metadata with proof
            private_key: Wallet private key
            
        Returns:
            Transaction hash
        """
        # In a real implementation, this would:
        # 1. Build claim transaction with merkle proof
        # 2. Sign transaction with private key
        # 3. Submit to blockchain
        # 4. Wait for confirmation
        # 5. Return transaction hash
        
        logger.info(
            "merkle_claim_simulated",
            wallet=wallet.address[:10],
            contract=airdrop_config.get('claim_contract')
        )
        
        # Simulated transaction hash
        tx_hash = '0x' + ''.join([random.choice('0123456789abcdef') for _ in range(64)])
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        return tx_hash
    
    async def _claim_api(
        self,
        wallet: Wallet,
        airdrop_config: Dict,
        metadata: Optional[Dict],
        private_key: str
    ) -> str:
        """Execute API-based claim.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            metadata: Claim metadata
            private_key: Wallet private key
            
        Returns:
            Transaction hash or claim ID
        """
        # In a real implementation, this would:
        # 1. Create signature with private key
        # 2. Submit claim request to API
        # 3. Get transaction hash or claim ID
        # 4. Return result
        
        logger.info(
            "api_claim_simulated",
            wallet=wallet.address[:10],
            api=airdrop_config.get('eligibility_api')
        )
        
        # Simulated claim ID
        claim_id = '0x' + ''.join([random.choice('0123456789abcdef') for _ in range(64)])
        
        # Simulate API delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return claim_id
    
    async def _claim_direct(
        self,
        wallet: Wallet,
        airdrop_config: Dict,
        metadata: Optional[Dict],
        private_key: str
    ) -> str:
        """Execute direct contract call claim.
        
        Args:
            wallet: Wallet database record
            airdrop_config: Airdrop configuration
            metadata: Claim metadata
            private_key: Wallet private key
            
        Returns:
            Transaction hash
        """
        # In a real implementation, this would:
        # 1. Build claim transaction
        # 2. Estimate gas
        # 3. Sign transaction with private key
        # 4. Submit to blockchain
        # 5. Wait for confirmation
        # 6. Return transaction hash
        
        logger.info(
            "direct_claim_simulated",
            wallet=wallet.address[:10],
            contract=airdrop_config.get('claim_contract')
        )
        
        # Simulated transaction hash
        tx_hash = '0x' + ''.join([random.choice('0123456789abcdef') for _ in range(64)])
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        return tx_hash
    
    def _record_claim_success(
        self,
        wallet: Wallet,
        airdrop_name: str,
        airdrop_config: Dict,
        tx_hash: str,
        metadata: Optional[Dict]
    ):
        """Record successful claim in database.
        
        Args:
            wallet: Wallet database record
            airdrop_name: Airdrop name
            airdrop_config: Airdrop configuration
            tx_hash: Transaction hash
            metadata: Claim metadata
        """
        with get_db_session() as session:
            claim = session.query(AirdropClaim).filter(
                AirdropClaim.wallet_id == wallet.id,
                AirdropClaim.airdrop_name == airdrop_name
            ).first()
            
            if claim:
                claim.status = 'claimed'
                claim.tx_hash = tx_hash
                claim.claimed_at = datetime.now(timezone.utc)
                
                if metadata and 'amount' in metadata:
                    claim.amount_claimed = metadata['amount']
                
                claim.error_message = None
            else:
                claim = AirdropClaim(
                    wallet_id=wallet.id,
                    airdrop_name=airdrop_name,
                    chain=airdrop_config.get('chain', wallet.chain),
                    status='claimed',
                    tx_hash=tx_hash,
                    claimed_at=datetime.now(timezone.utc),
                    amount_claimed=metadata.get('amount') if metadata else None
                )
                session.add(claim)
            
            session.commit()
            
            logger.info(
                "claim_recorded",
                wallet=wallet.address[:10],
                airdrop=airdrop_name,
                tx_hash=tx_hash
            )
    
    def _record_claim_failure(
        self,
        wallet: Wallet,
        airdrop_name: str,
        error: str
    ):
        """Record failed claim in database.
        
        Args:
            wallet: Wallet database record
            airdrop_name: Airdrop name
            error: Error message
        """
        with get_db_session() as session:
            claim = session.query(AirdropClaim).filter(
                AirdropClaim.wallet_id == wallet.id,
                AirdropClaim.airdrop_name == airdrop_name
            ).first()
            
            if claim:
                claim.status = 'failed'
                claim.error_message = error
            else:
                claim = AirdropClaim(
                    wallet_id=wallet.id,
                    airdrop_name=airdrop_name,
                    chain=wallet.chain,
                    status='failed',
                    error_message=error
                )
                session.add(claim)
            
            session.commit()

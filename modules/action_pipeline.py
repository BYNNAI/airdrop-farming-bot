"""
Eligibility actions pipeline with human-like behavior.

This module provides a framework for executing blockchain actions (staking, swapping,
bridging) with human-like timing patterns, randomization, and anti-detection measures
to maximize airdrop eligibility while avoiding Sybil detection.

Author: BYNNΛI
License: MIT
"""

import os
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

from web3 import Web3
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
import base58

from utils.database import Wallet, WalletAction, get_db_session
from utils.logging_config import get_logger, log_transaction
from modules.anti_detection import AntiDetection
from modules.protocols.uniswap import UniswapIntegration
from modules.protocols.staking import StakingIntegration
from modules.protocols.bridges import BridgeIntegration
from modules.protocols.jupiter import JupiterIntegration
from modules.protocols.solana_stake import SolanaStakeIntegration

logger = get_logger(__name__)


class ActionAdapter(ABC):
    """Abstract base class for chain-specific action adapters."""
    
    @abstractmethod
    async def stake(
        self,
        wallet: Wallet,
        amount: float,
        validator: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute staking action.
        
        Args:
            wallet: Wallet to use
            amount: Amount to stake
            validator: Optional validator address
            **kwargs: Additional parameters
            
        Returns:
            Result dictionary with tx_hash, status, etc.
        """
        pass
    
    @abstractmethod
    async def swap(
        self,
        wallet: Wallet,
        from_token: str,
        to_token: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute swap action.
        
        Args:
            wallet: Wallet to use
            from_token: Source token
            to_token: Destination token
            amount: Amount to swap
            **kwargs: Additional parameters
            
        Returns:
            Result dictionary
        """
        pass
    
    @abstractmethod
    async def bridge(
        self,
        wallet: Wallet,
        to_chain: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute bridge action.
        
        Args:
            wallet: Wallet to use
            to_chain: Destination chain
            amount: Amount to bridge
            **kwargs: Additional parameters
            
        Returns:
            Result dictionary
        """
        pass
    
    @abstractmethod
    async def get_balance(
        self,
        wallet: Wallet,
        token: Optional[str] = None
    ) -> float:
        """Get wallet balance.
        
        Args:
            wallet: Wallet to check
            token: Optional token address (None = native)
            
        Returns:
            Balance amount
        """
        pass


class EVMActionAdapter(ActionAdapter):
    """Action adapter for EVM-compatible chains."""
    
    def __init__(self, chain: str, rpc_url: str):
        """Initialize EVM adapter.
        
        Args:
            chain: Chain identifier
            rpc_url: RPC endpoint URL
        """
        self.chain = chain
        self.rpc_url = rpc_url
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Initialize wallet manager once for reuse
        from modules.wallet_manager import WalletManager
        self.wallet_manager = WalletManager()
        
        # Initialize protocol integrations (lazy load based on config)
        self.uniswap = None
        self.staking = None
        self.bridge = None
        
        # Load contract addresses from environment
        router_addr = os.getenv(f'UNISWAP_ROUTER_{chain.upper()}', '')
        staking_addr = os.getenv(f'STAKING_CONTRACT_{chain.upper()}', '')
        bridge_addr = os.getenv(f'BRIDGE_CONTRACT_{chain.upper()}', '')
        bridge_type = os.getenv(f'BRIDGE_TYPE_{chain.upper()}', 'native')
        
        if router_addr:
            self.uniswap = UniswapIntegration(self.web3, router_addr, chain)
        if staking_addr:
            self.staking = StakingIntegration(self.web3, staking_addr, chain)
        if bridge_addr:
            self.bridge = BridgeIntegration(self.web3, bridge_addr, chain, bridge_type)
        
        logger.info(
            "evm_adapter_initialized",
            chain=chain,
            rpc_url=rpc_url,
            has_uniswap=self.uniswap is not None,
            has_staking=self.staking is not None,
            has_bridge=self.bridge is not None
        )
    
    async def stake(
        self,
        wallet: Wallet,
        amount: float,
        validator: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Stake tokens on EVM chain."""
        logger.info(
            "stake_action",
            chain=self.chain,
            wallet=wallet.address,
            amount=amount,
            validator=validator
        )
        
        if not self.staking:
            logger.warning(
                "staking_not_configured",
                chain=self.chain,
                message="Staking contract not configured for this chain"
            )
            # Fall back to mock behavior if not configured
            await asyncio.sleep(random.uniform(2, 5))
            return {
                'success': False,
                'tx_hash': "0x" + "00" * 31 + "01_NO_STAKING_CONFIG",
                'amount': amount,
                'error': 'Staking not configured'
            }
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(wallet.address, wallet.chain)
            
            if not private_key:
                raise ValueError("Could not derive private key for wallet")
            
            # Convert amount to wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Execute staking
            result = await self.staking.stake(
                amount_wei,
                wallet.address,
                private_key,
                validator
            )
            
            return {
                'success': True,
                'tx_hash': result['tx_hash'],
                'amount': amount,
                'validator': validator
            }
        
        except Exception as e:
            logger.error(
                "stake_failed",
                chain=self.chain,
                wallet=wallet.address,
                error=str(e)
            )
            return {
                'success': False,
                'tx_hash': None,
                'amount': amount,
                'error': str(e)
            }
    
    async def swap(
        self,
        wallet: Wallet,
        from_token: str,
        to_token: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Swap tokens using DEX."""
        logger.info(
            "swap_action",
            chain=self.chain,
            wallet=wallet.address,
            from_token=from_token,
            to_token=to_token,
            amount=amount
        )
        
        if not self.uniswap:
            logger.warning(
                "swap_not_configured",
                chain=self.chain,
                message="DEX not configured for this chain"
            )
            # Fall back to mock behavior if not configured
            await asyncio.sleep(random.uniform(2, 5))
            return {
                'success': False,
                'tx_hash': "0x" + "11" * 31 + "02_NO_SWAP_CONFIG",
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'error': 'Swap not configured'
            }
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(wallet.address, wallet.chain)
            
            if not private_key:
                raise ValueError("Could not derive private key for wallet")
            
            # Convert amount to wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Execute swap (handle ETH to token or token to token)
            if from_token.lower() == 'eth' or from_token == '0x' + '00' * 20:
                result = await self.uniswap.swap_exact_eth_for_tokens(
                    to_token,
                    amount_wei,
                    wallet.address,
                    private_key
                )
            else:
                result = await self.uniswap.swap_exact_tokens_for_tokens(
                    from_token,
                    to_token,
                    amount_wei,
                    wallet.address,
                    private_key
                )
            
            return {
                'success': True,
                'tx_hash': result['tx_hash'],
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'amount_out': self.web3.from_wei(result.get('amount_out_min', 0), 'ether')
            }
        
        except Exception as e:
            logger.error(
                "swap_failed",
                chain=self.chain,
                wallet=wallet.address,
                error=str(e)
            )
            return {
                'success': False,
                'tx_hash': None,
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'error': str(e)
            }
    
    async def bridge(
        self,
        wallet: Wallet,
        to_chain: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Bridge assets to another chain."""
        logger.info(
            "bridge_action",
            from_chain=self.chain,
            to_chain=to_chain,
            wallet=wallet.address,
            amount=amount
        )
        
        if not self.bridge:
            logger.warning(
                "bridge_not_configured",
                chain=self.chain,
                message="Bridge not configured for this chain"
            )
            # Fall back to mock behavior if not configured
            await asyncio.sleep(random.uniform(5, 10))
            return {
                'success': False,
                'tx_hash': "0x" + "22" * 31 + "03_NO_BRIDGE_CONFIG",
                'from_chain': self.chain,
                'to_chain': to_chain,
                'amount': amount,
                'error': 'Bridge not configured'
            }
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(wallet.address, wallet.chain)
            
            if not private_key:
                raise ValueError("Could not derive private key for wallet")
            
            # Convert amount to wei
            amount_wei = self.web3.to_wei(amount, 'ether')
            
            # Get destination chain ID from kwargs or config
            dst_chain_id_str = kwargs.get('dst_chain_id') or os.getenv(f'LAYERZERO_CHAIN_ID_{to_chain.upper()}', '')
            if not dst_chain_id_str:
                dst_chain_id = 0
            else:
                dst_chain_id = int(dst_chain_id_str)
            
            # Execute bridge based on bridge type
            if self.bridge.bridge_type == 'layerzero':
                if not dst_chain_id:
                    raise ValueError(f"LayerZero chain ID not configured for destination chain {to_chain}. Set LAYERZERO_CHAIN_ID_{to_chain.upper()} in environment.")
                result = await self.bridge.bridge_layerzero(
                    dst_chain_id,
                    amount_wei,
                    wallet.address,
                    private_key
                )
            else:
                # Use native L2 bridge
                result = await self.bridge.bridge_native_l2(
                    amount_wei,
                    wallet.address,
                    private_key
                )
            
            return {
                'success': True,
                'tx_hash': result['tx_hash'],
                'from_chain': self.chain,
                'to_chain': to_chain,
                'amount': amount
            }
        
        except Exception as e:
            logger.error(
                "bridge_failed",
                from_chain=self.chain,
                to_chain=to_chain,
                wallet=wallet.address,
                error=str(e)
            )
            return {
                'success': False,
                'tx_hash': None,
                'from_chain': self.chain,
                'to_chain': to_chain,
                'amount': amount,
                'error': str(e)
            }
    
    async def get_balance(
        self,
        wallet: Wallet,
        token: Optional[str] = None
    ) -> float:
        """Get wallet balance."""
        try:
            wallet_address = Web3.to_checksum_address(wallet.address)
            
            if not token or token.lower() == 'eth':
                # Get native balance
                balance_wei = self.web3.eth.get_balance(wallet_address)
                balance = self.web3.from_wei(balance_wei, 'ether')
            else:
                # Get ERC20 balance
                if self.uniswap:
                    token_contract = self.uniswap.get_token_contract(token)
                    balance_wei = token_contract.functions.balanceOf(wallet_address).call()
                    balance = self.web3.from_wei(balance_wei, 'ether')
                else:
                    # Fallback if no uniswap integration
                    from modules.protocols.uniswap import ERC20_ABI
                    token_contract = self.web3.eth.contract(
                        address=Web3.to_checksum_address(token),
                        abi=ERC20_ABI
                    )
                    balance_wei = token_contract.functions.balanceOf(wallet_address).call()
                    balance = self.web3.from_wei(balance_wei, 'ether')
            
            logger.debug(
                "balance_checked",
                chain=self.chain,
                wallet=wallet.address,
                token=token or 'native',
                balance=balance
            )
            
            return float(balance)
        
        except Exception as e:
            logger.error(
                "balance_check_failed",
                chain=self.chain,
                wallet=wallet.address,
                token=token,
                error=str(e)
            )
            return 0.0


class SolanaActionAdapter(ActionAdapter):
    """Action adapter for Solana."""
    
    def __init__(self, rpc_url: str):
        """Initialize Solana adapter.
        
        Args:
            rpc_url: Solana RPC endpoint
        """
        self.chain = "solana"
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
        # Initialize wallet manager once for reuse
        from modules.wallet_manager import WalletManager
        self.wallet_manager = WalletManager()
        
        # Initialize protocol integrations
        self.staking = SolanaStakeIntegration(rpc_url)
        self.jupiter = JupiterIntegration(rpc_url, use_devnet='devnet' in rpc_url or 'testnet' in rpc_url)
        
        logger.info(
            "solana_adapter_initialized",
            rpc_url=rpc_url,
            has_staking=True,
            has_jupiter=True
        )
    
    async def stake(
        self,
        wallet: Wallet,
        amount: float,
        validator: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Stake SOL."""
        logger.info(
            "stake_action",
            chain=self.chain,
            wallet=wallet.address,
            amount=amount,
            validator=validator
        )
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(wallet.address, wallet.chain)
            
            if not private_key:
                raise ValueError("Could not derive private key for wallet")
            
            # Decode private key to Keypair
            private_key_bytes = base58.b58decode(private_key)
            wallet_keypair = Keypair.from_bytes(private_key_bytes)
            
            # Get validator if not specified
            if not validator:
                validators = await self.staking.get_validators(limit=5)
                if validators:
                    # Pick a random validator with low commission
                    validator = random.choice([v['vote_pubkey'] for v in validators if v['commission'] < 10])
                else:
                    raise ValueError("No validators available")
            
            # Convert amount to lamports
            amount_lamports = int(amount * 1e9)
            
            # Execute staking
            result = await self.staking.create_stake_account(
                amount_lamports,
                wallet_keypair,
                validator
            )
            
            return {
                'success': True,
                'tx_hash': result['tx_hash'],
                'amount': amount,
                'validator': validator,
                'stake_account': result.get('stake_account')
            }
        
        except Exception as e:
            logger.error(
                "stake_failed",
                chain=self.chain,
                wallet=wallet.address,
                error=str(e)
            )
            return {
                'success': False,
                'tx_hash': None,
                'amount': amount,
                'error': str(e)
            }
    
    async def swap(
        self,
        wallet: Wallet,
        from_token: str,
        to_token: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Swap on Solana DEX."""
        logger.info(
            "swap_action",
            chain=self.chain,
            wallet=wallet.address,
            from_token=from_token,
            to_token=to_token,
            amount=amount
        )
        
        try:
            # Get private key for wallet
            private_key = self.wallet_manager.get_private_key(wallet.address, wallet.chain)
            
            if not private_key:
                raise ValueError("Could not derive private key for wallet")
            
            # Decode private key to Keypair
            private_key_bytes = base58.b58decode(private_key)
            wallet_keypair = Keypair.from_bytes(private_key_bytes)
            
            # Convert amount to smallest unit (lamports for SOL, or token decimals)
            # For SOL, 1 SOL = 1e9 lamports
            amount_lamports = int(amount * 1e9)
            
            # Execute swap via Jupiter
            result = await self.jupiter.swap(
                from_token,
                to_token,
                amount_lamports,
                wallet_keypair
            )
            
            return {
                'success': True,
                'tx_hash': result['tx_hash'],
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'amount_out': float(result.get('amount_out', 0)) / 1e9
            }
        
        except Exception as e:
            logger.error(
                "swap_failed",
                chain=self.chain,
                wallet=wallet.address,
                error=str(e)
            )
            return {
                'success': False,
                'tx_hash': None,
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'error': str(e)
            }
    
    async def bridge(
        self,
        wallet: Wallet,
        to_chain: str,
        amount: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Bridge from Solana."""
        logger.info(
            "bridge_action",
            from_chain=self.chain,
            to_chain=to_chain,
            wallet=wallet.address,
            amount=amount
        )
        
        # Note: Solana bridges typically require Wormhole or similar protocols
        # For testnet, we'll log the intent but not implement full bridge
        logger.warning(
            "solana_bridge_not_implemented",
            message="Solana bridging requires Wormhole integration (not yet implemented)"
        )
        
        # Simulate bridge delay
        await asyncio.sleep(random.uniform(5, 10))
        
        return {
            'success': False,
            'tx_hash': None,
            'from_chain': self.chain,
            'to_chain': to_chain,
            'amount': amount,
            'error': 'Solana bridging not yet implemented (requires Wormhole)'
        }
    
    async def get_balance(
        self,
        wallet: Wallet,
        token: Optional[str] = None
    ) -> float:
        """Get SOL balance."""
        try:
            from solders.pubkey import Pubkey
            
            wallet_pubkey = Pubkey.from_string(wallet.address)
            
            if not token or token.lower() == 'sol':
                # Get native SOL balance
                result = await self.client.get_balance(wallet_pubkey)
                balance_lamports = result.value
                balance = float(balance_lamports) / 1e9
            else:
                # Get SPL token balance
                balance_lamports = await self.jupiter.get_token_balance(wallet.address, token)
                balance = float(balance_lamports) / 1e9
            
            logger.debug(
                "balance_checked",
                chain=self.chain,
                wallet=wallet.address,
                token=token or 'SOL',
                balance=balance
            )
            
            return balance
        
        except Exception as e:
            logger.error(
                "balance_check_failed",
                chain=self.chain,
                wallet=wallet.address,
                token=token,
                error=str(e)
            )
            return 0.0


class ActionPipeline:
    """Pipeline for executing eligibility actions with human-like behavior."""
    
    def __init__(self, anti_detection: Optional[AntiDetection] = None):
        """Initialize action pipeline.
        
        Args:
            anti_detection: Optional anti-detection coordinator
        """
        self.adapters: Dict[str, ActionAdapter] = {}
        self._initialize_adapters()
        
        # Initialize anti-detection
        self.anti_detection = anti_detection or AntiDetection()
        
        # Settings
        self.enable_staking = os.getenv("ENABLE_STAKING", "true").lower() == "true"
        self.enable_bridging = os.getenv("ENABLE_BRIDGING", "true").lower() == "true"
        self.enable_swapping = os.getenv("ENABLE_SWAPPING", "true").lower() == "true"
        
        self.min_delay = int(os.getenv("MIN_DELAY_SECONDS", "30"))
        self.max_delay = int(os.getenv("MAX_DELAY_SECONDS", "300"))
        self.cooldown_hours = int(os.getenv("ACTION_COOLDOWN_HOURS", "6"))
    
    def _initialize_adapters(self):
        """Initialize chain adapters."""
        # EVM chains
        evm_chains = [
            ('ethereum_sepolia', os.getenv('ETH_RPC_SEPOLIA', '')),
            ('ethereum_goerli', os.getenv('ETH_RPC_GOERLI', '')),
            ('polygon_amoy', os.getenv('POLYGON_RPC_AMOY', '')),
            ('arbitrum_sepolia', os.getenv('ARBITRUM_RPC_SEPOLIA', '')),
            ('base_sepolia', os.getenv('BASE_RPC_SEPOLIA', '')),
            ('bnb_testnet', os.getenv('BNB_RPC_TESTNET', '')),
            ('avalanche_fuji', os.getenv('AVALANCHE_RPC_FUJI', '')),
            ('fantom_testnet', os.getenv('FANTOM_RPC_TESTNET', '')),
        ]
        
        for chain, rpc_url in evm_chains:
            if rpc_url:
                self.adapters[chain] = EVMActionAdapter(chain, rpc_url)
        
        # Solana
        solana_rpc = os.getenv('SOLANA_RPC_DEVNET') or os.getenv('SOLANA_RPC_TESTNET')
        if solana_rpc:
            self.adapters['solana_devnet'] = SolanaActionAdapter(solana_rpc)
            self.adapters['solana_testnet'] = SolanaActionAdapter(solana_rpc)
        
        logger.info(
            "adapters_initialized",
            chains=list(self.adapters.keys())
        )
    
    def _add_human_jitter(self) -> float:
        """Calculate human-like delay with jitter using anti-detection.
        
        Returns:
            Delay in seconds
        """
        base_delay = random.uniform(self.min_delay, self.max_delay)
        return self.anti_detection.get_jittered_delay(base_delay, distribution='gaussian')
    
    def _check_cooldown(self, wallet: Wallet, action_type: str) -> bool:
        """Check if action is in cooldown period.
        
        Args:
            wallet: Wallet to check
            action_type: Action type
            
        Returns:
            True if in cooldown
        """
        with get_db_session() as session:
            cooldown_time = datetime.utcnow() - timedelta(hours=self.cooldown_hours)
            
            recent_action = session.query(WalletAction).filter(
                WalletAction.wallet_id == wallet.id,
                WalletAction.action_type == action_type,
                WalletAction.executed_at > cooldown_time,
                WalletAction.status == 'success'
            ).first()
            
            return recent_action is not None
    
    async def execute_action(
        self,
        wallet: Wallet,
        action_type: str,
        chain: str,
        params: Dict[str, Any]
    ) -> bool:
        """Execute a single action with proper tracking.
        
        Args:
            wallet: Wallet to use
            action_type: Action type (stake, swap, bridge)
            chain: Chain identifier
            params: Action parameters
            
        Returns:
            True if successful
        """
        # Check if we should skip this action for anti-detection
        if self.anti_detection.should_skip_action(wallet.address):
            logger.info(
                "action_skipped_for_anti_detection",
                wallet=wallet.address,
                action_type=action_type,
                chain=chain
            )
            return False
        
        # Check if adapter exists
        adapter = self.adapters.get(chain)
        if not adapter:
            logger.warning(
                "no_adapter_for_chain",
                chain=chain,
                action_type=action_type
            )
            return False
        
        # Check cooldown
        if self._check_cooldown(wallet, action_type):
            logger.info(
                "action_in_cooldown",
                wallet=wallet.address,
                action_type=action_type
            )
            return False
        
        # Create action record
        with get_db_session() as session:
            action = WalletAction(
                wallet_id=wallet.id,
                action_type=action_type,
                chain=chain,
                status='pending',
                params=str(params),
                scheduled_at=datetime.utcnow()
            )
            session.add(action)
            session.commit()
            action_id = action.id
        
        # Add human-like delay before execution
        delay = self._add_human_jitter()
        logger.info(
            "action_delayed",
            wallet=wallet.address,
            action_type=action_type,
            delay=delay
        )
        await asyncio.sleep(delay)
        
        # Execute action
        try:
            with get_db_session() as session:
                action = session.query(WalletAction).get(action_id)
                action.status = 'in_progress'
                action.executed_at = datetime.utcnow()
                session.commit()
            
            # Call appropriate adapter method
            if action_type == 'stake':
                result = await adapter.stake(wallet, **params)
            elif action_type == 'swap':
                result = await adapter.swap(wallet, **params)
            elif action_type == 'bridge':
                result = await adapter.bridge(wallet, **params)
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            # Update as successful
            with get_db_session() as session:
                action = session.query(WalletAction).get(action_id)
                action.status = 'success'
                action.completed_at = datetime.utcnow()
                action.tx_hash = result.get('tx_hash')
                action.result = str(result)
                session.commit()
            
            log_transaction(
                logger,
                wallet=wallet.address,
                chain=chain,
                action=action_type,
                tx_hash=result.get('tx_hash'),
                status='success'
            )
            
            return True
        
        except Exception as e:
            # Update as failed
            with get_db_session() as session:
                action = session.query(WalletAction).get(action_id)
                action.status = 'failed'
                action.error_message = str(e)
                action.attempts += 1
                session.commit()
            
            log_transaction(
                logger,
                wallet=wallet.address,
                chain=chain,
                action=action_type,
                status='failed',
                error=str(e)
            )
            
            return False
    
    async def run_pipeline(
        self,
        wallets: List[Wallet],
        actions: List[Dict[str, Any]],
        concurrency: int = 3
    ) -> Dict[str, int]:
        """Run action pipeline for multiple wallets.
        
        Args:
            wallets: List of wallets
            actions: List of action configurations
            concurrency: Max concurrent actions
            
        Returns:
            Statistics summary
        """
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def execute_with_semaphore(wallet, action):
            async with semaphore:
                stats['total'] += 1
                
                action_type = action['type']
                chain = action['chain']
                params = action.get('params', {})
                
                # Check if action type is enabled
                if action_type == 'stake' and not self.enable_staking:
                    stats['skipped'] += 1
                    return
                elif action_type == 'bridge' and not self.enable_bridging:
                    stats['skipped'] += 1
                    return
                elif action_type == 'swap' and not self.enable_swapping:
                    stats['skipped'] += 1
                    return
                
                success = await self.execute_action(
                    wallet,
                    action_type,
                    chain,
                    params
                )
                
                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        # Create tasks
        tasks = []
        for wallet in wallets:
            for action in actions:
                tasks.append(execute_with_semaphore(wallet, action))
        
        # Execute all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(
            "pipeline_completed",
            stats=stats
        )
        
        return stats

"""Eligibility actions pipeline with human-like behavior."""

import os
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

from utils.database import Wallet, WalletAction, get_db_session
from utils.logging_config import get_logger, log_transaction

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
        
        logger.info(
            "evm_adapter_initialized",
            chain=chain,
            rpc_url=rpc_url
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
        
        # Placeholder implementation
        # In production, integrate with Web3.py and staking contracts
        await asyncio.sleep(random.uniform(2, 5))
        
        # Generate a clearly marked mock transaction hash
        mock_tx_hash = "0x" + "00" * 31 + "01_MOCK_STAKE"
        
        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'amount': amount,
            'validator': validator
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
        
        # Placeholder implementation
        # In production, integrate with Uniswap/PancakeSwap/etc.
        await asyncio.sleep(random.uniform(2, 5))
        
        mock_tx_hash = "0x" + "11" * 31 + "02_MOCK_SWAP"
        
        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'from_token': from_token,
            'to_token': to_token,
            'amount_in': amount,
            'amount_out': amount * random.uniform(0.95, 1.05)
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
        
        # Placeholder implementation
        # In production, integrate with bridge protocols
        await asyncio.sleep(random.uniform(5, 10))
        
        mock_tx_hash = "0x" + "22" * 31 + "03_MOCK_BRIDGE"
        
        return {
            'success': True,
            'tx_hash': mock_tx_hash,
            'from_chain': self.chain,
            'to_chain': to_chain,
            'amount': amount
        }
    
    async def get_balance(
        self,
        wallet: Wallet,
        token: Optional[str] = None
    ) -> float:
        """Get wallet balance."""
        # Placeholder implementation
        # In production, query blockchain via Web3.py
        return random.uniform(0.1, 10.0)


class SolanaActionAdapter(ActionAdapter):
    """Action adapter for Solana."""
    
    def __init__(self, rpc_url: str):
        """Initialize Solana adapter.
        
        Args:
            rpc_url: Solana RPC endpoint
        """
        self.chain = "solana"
        self.rpc_url = rpc_url
        
        logger.info(
            "solana_adapter_initialized",
            rpc_url=rpc_url
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
        
        # Placeholder
        await asyncio.sleep(random.uniform(2, 5))
        
        return {
            'success': True,
            'tx_hash': 'solana_stake_' + 'a' * 64,
            'amount': amount,
            'validator': validator
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
        
        # Placeholder
        await asyncio.sleep(random.uniform(2, 5))
        
        return {
            'success': True,
            'tx_hash': 'solana_swap_' + 'b' * 64,
            'from_token': from_token,
            'to_token': to_token,
            'amount_in': amount,
            'amount_out': amount * random.uniform(0.95, 1.05)
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
        
        # Placeholder
        await asyncio.sleep(random.uniform(5, 10))
        
        return {
            'success': True,
            'tx_hash': 'solana_bridge_' + 'c' * 64,
            'from_chain': self.chain,
            'to_chain': to_chain,
            'amount': amount
        }
    
    async def get_balance(
        self,
        wallet: Wallet,
        token: Optional[str] = None
    ) -> float:
        """Get SOL balance."""
        # Placeholder
        return random.uniform(0.1, 10.0)


class ActionPipeline:
    """Pipeline for executing eligibility actions with human-like behavior."""
    
    def __init__(self):
        """Initialize action pipeline."""
        self.adapters: Dict[str, ActionAdapter] = {}
        self._initialize_adapters()
        
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
        """Calculate human-like delay with jitter.
        
        Returns:
            Delay in seconds
        """
        base_delay = random.uniform(self.min_delay, self.max_delay)
        jitter = random.gauss(0, base_delay * 0.2)  # 20% stddev
        return max(self.min_delay, base_delay + jitter)
    
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

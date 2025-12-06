"""
Solana native staking integration.

Author: BYNNΛI
License: MIT
"""

import os
from typing import Dict, Any, Optional
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import create_account, CreateAccountParams
from solders.instruction import Instruction, AccountMeta
from solders.transaction import Transaction
from solders.message import Message
import base58
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Stake Program ID
STAKE_PROGRAM_ID = Pubkey.from_string("Stake11111111111111111111111111111111111111")


class SolanaStakeIntegration:
    """Integration with Solana native staking."""
    
    def __init__(self, rpc_url: str):
        """Initialize Solana staking integration.
        
        Args:
            rpc_url: Solana RPC endpoint URL
        """
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        
        logger.info(
            "solana_stake_initialized",
            rpc_url=rpc_url
        )
    
    async def create_stake_account(
        self,
        amount: int,
        wallet_keypair: Keypair,
        validator_pubkey: str
    ) -> Dict[str, Any]:
        """Create and delegate a stake account.
        
        Args:
            amount: Amount to stake (in lamports)
            wallet_keypair: Wallet keypair
            validator_pubkey: Validator public key to delegate to
            
        Returns:
            Result dictionary with transaction signature and stake account
        """
        # Note: This is a simplified implementation for testnet
        # IMPORTANT: This only creates a stake account but does NOT initialize or delegate it
        # Full staking requires stake program instructions not exposed in solders 0.21.0
        # For production use, upgrade to newer solders version or use @solana/web3.js
        
        logger.warning(
            "solana_staking_incomplete",
            message="This implementation only creates stake accounts. Stake initialization and delegation are NOT performed due to solders 0.21.0 limitations. Upgrade solders or use @solana/web3.js for full staking functionality."
        )
        
        # Create new stake account
        stake_keypair = Keypair()
        stake_account = stake_keypair.pubkey()
        
        # Get recent blockhash
        recent_blockhash_resp = await self.client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_resp.value.blockhash
        
        # Get minimum rent exemption
        rent_resp = await self.client.get_minimum_balance_for_rent_exemption(200)
        rent_exemption = rent_resp.value
        
        # Create stake account instruction using system program
        create_account_ix = create_account(
            CreateAccountParams(
                from_pubkey=wallet_keypair.pubkey(),
                to_pubkey=stake_account,
                lamports=amount + rent_exemption,
                space=200,
                owner=STAKE_PROGRAM_ID
            )
        )
        
        # Build minimal transaction with just account creation
        # Full staking with initialization and delegation would require
        # constructing custom instructions which solders 0.21.0 doesn't expose
        message = Message.new_with_blockhash(
            [create_account_ix],
            wallet_keypair.pubkey(),
            recent_blockhash
        )
        
        tx = Transaction([wallet_keypair, stake_keypair], message, recent_blockhash)
        
        # Send transaction
        result = await self.client.send_transaction(tx)
        signature = result.value
        
        # Wait for confirmation
        await self.client.confirm_transaction(signature, commitment=Confirmed)
        
        logger.info(
            "solana_stake_account_created",
            stake_account=str(stake_account),
            validator=validator_pubkey,
            amount=amount,
            signature=str(signature),
            note="Stake account created but not yet initialized/delegated (requires stake program instruction construction)"
        )
        
        return {
            'tx_hash': str(signature),
            'stake_account': str(stake_account),
            'validator': validator_pubkey,
            'amount': amount,
            'note': 'Account created but not fully delegated (requires newer solders version or manual instruction encoding)'
        }
    
    async def get_stake_balance(self, stake_account: str) -> int:
        """Get stake account balance.
        
        Args:
            stake_account: Stake account public key
            
        Returns:
            Staked balance in lamports
        """
        pubkey = Pubkey.from_string(stake_account)
        result = await self.client.get_balance(pubkey)
        balance = result.value
        
        logger.debug(
            "stake_balance_checked",
            stake_account=stake_account,
            balance=balance
        )
        
        return balance
    
    async def get_validators(self, limit: int = 10) -> list:
        """Get list of active validators.
        
        Args:
            limit: Maximum number of validators to return
            
        Returns:
            List of validator vote accounts
        """
        result = await self.client.get_vote_accounts()
        validators = result.value.current[:limit]
        
        validator_list = [
            {
                'vote_pubkey': str(v.vote_pubkey),
                'commission': v.commission,
                'activated_stake': v.activated_stake
            }
            for v in validators
        ]
        
        logger.debug(
            "validators_fetched",
            count=len(validator_list)
        )
        
        return validator_list
    
    async def close(self):
        """Close the RPC client connection."""
        await self.client.close()

"""
EVM staking integration (Lido and similar protocols).

Author: BYNNΛI
License: MIT
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lido stETH ABI (minimal for staking)
LIDO_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_referral", "type": "address"}],
        "name": "submit",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getTotalPooledEther",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class StakingIntegration:
    """Integration with EVM staking contracts like Lido."""
    
    def __init__(self, web3: Web3, staking_address: str, chain: str):
        """Initialize staking integration.
        
        Args:
            web3: Web3 instance
            staking_address: Staking contract address (e.g., Lido)
            chain: Chain identifier
        """
        self.web3 = web3
        self.staking_address = Web3.to_checksum_address(staking_address)
        self.chain = chain
        self.contract = self.web3.eth.contract(
            address=self.staking_address,
            abi=LIDO_ABI
        )
        
        logger.info(
            "staking_initialized",
            chain=chain,
            contract=self.staking_address
        )
    
    async def stake(
        self,
        amount: int,
        wallet_address: str,
        private_key: str,
        referral: Optional[str] = None
    ) -> Dict[str, Any]:
        """Stake ETH to receive stETH.
        
        Args:
            amount: Amount to stake (in wei)
            wallet_address: Wallet address
            private_key: Private key for signing
            referral: Optional referral address
            
        Returns:
            Result dictionary with tx_hash and staked amount
        """
        wallet = Web3.to_checksum_address(wallet_address)
        referral_addr = Web3.to_checksum_address(referral) if referral else None
        
        # Use zero address if no referral provided
        if not referral_addr:
            referral_addr = Web3.to_checksum_address('0x' + '00' * 20)
        
        # Check balance
        balance = self.web3.eth.get_balance(wallet)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")
        
        # Build stake transaction
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        tx = self.contract.functions.submit(referral_addr).build_transaction({
            'from': wallet,
            'value': amount,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': self.web3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "stake_completed",
            amount=amount,
            wallet=wallet,
            tx_hash=receipt['transactionHash'].hex(),
            status=receipt['status'],
            gas_used=receipt['gasUsed']
        )
        
        return {
            'tx_hash': receipt['transactionHash'].hex(),
            'amount': amount,
            'status': receipt['status'],
            'gas_used': receipt['gasUsed']
        }
    
    async def get_staked_balance(self, wallet_address: str) -> int:
        """Get staked token balance.
        
        Args:
            wallet_address: Wallet address
            
        Returns:
            Staked balance in wei
        """
        wallet = Web3.to_checksum_address(wallet_address)
        balance = self.contract.functions.balanceOf(wallet).call()
        
        logger.debug(
            "staked_balance_checked",
            wallet=wallet,
            balance=balance
        )
        
        return balance
    
    async def get_total_staked(self) -> int:
        """Get total amount staked in protocol.
        
        Returns:
            Total staked amount in wei
        """
        total = self.contract.functions.getTotalPooledEther().call()
        
        logger.debug(
            "total_staked_checked",
            total=total
        )
        
        return total

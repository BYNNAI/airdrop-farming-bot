"""
Lido staking integration for ETH staking on EVM chains.

Supports Lido testnet deployments for liquid staking.

Author: BYNNΛI
License: MIT
"""

from typing import Dict, Any, Optional
from web3 import Web3
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Lido contract ABI (minimal for staking)
LIDO_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_referral", "type": "address"}],
        "name": "submit",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTotalPooledEther",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Lido testnet contract addresses
LIDO_CONTRACTS = {
    'ethereum_sepolia': '0x3e3FE7dBc6B4C189E7128855dD526361c49b40Af',  # Lido on Sepolia (if available)
    'ethereum_goerli': '0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F',  # Lido on Goerli
    'ethereum_holesky': '0x3F1c547b21f65e10480dE3ad8E19fAAC46C95034',  # Lido on Holesky testnet
}


class LidoStakingIntegration:
    """Integration with Lido for ETH liquid staking."""
    
    def __init__(self, web3: Web3, chain: str):
        """Initialize Lido integration.
        
        Args:
            web3: Web3 instance connected to the chain
            chain: Chain identifier (e.g., 'ethereum_sepolia')
        """
        self.web3 = web3
        self.chain = chain
        self.lido_address = LIDO_CONTRACTS.get(chain)
        
        if not self.lido_address:
            raise ValueError(f"No Lido contract configured for chain: {chain}")
        
        self.lido_contract = web3.eth.contract(
            address=Web3.to_checksum_address(self.lido_address),
            abi=LIDO_ABI
        )
        
        logger.info(
            "lido_integration_initialized",
            chain=chain,
            lido_address=self.lido_address
        )
    
    async def stake(
        self,
        amount: float,
        wallet_address: str,
        private_key: str,
        referral: Optional[str] = None
    ) -> Dict[str, Any]:
        """Stake ETH through Lido.
        
        Args:
            amount: Amount of ETH to stake
            wallet_address: Wallet address staking
            private_key: Wallet's private key
            referral: Optional referral address
            
        Returns:
            Dict with transaction details
        """
        amount_wei = self.web3.to_wei(amount, 'ether')
        
        # Use zero address if no referral
        referral_address = referral or '0x0000000000000000000000000000000000000000'
        
        # Check wallet balance
        balance = self.web3.eth.get_balance(wallet_address)
        if balance < amount_wei:
            raise ValueError(
                f"Insufficient balance: {self.web3.from_wei(balance, 'ether')} ETH "
                f"< {amount} ETH"
            )
        
        # Build staking transaction
        stake_tx = self.lido_contract.functions.submit(
            Web3.to_checksum_address(referral_address)
        ).build_transaction({
            'from': Web3.to_checksum_address(wallet_address),
            'value': amount_wei,
            'nonce': self.web3.eth.get_transaction_count(wallet_address),
            'gas': 150000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        # Estimate gas
        try:
            estimated_gas = self.web3.eth.estimate_gas(stake_tx)
            stake_tx['gas'] = int(estimated_gas * 1.2)  # Add 20% buffer
        except Exception as e:
            logger.warning("gas_estimation_failed", error=str(e))
        
        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(stake_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        success = receipt['status'] == 1
        
        # Get stETH balance after staking
        steth_balance = self.lido_contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        
        logger.info(
            "lido_stake_executed",
            amount=amount,
            tx_hash=tx_hash.hex(),
            status=success,
            steth_balance=self.web3.from_wei(steth_balance, 'ether'),
            gas_used=receipt['gasUsed']
        )
        
        return {
            'success': success,
            'tx_hash': tx_hash.hex(),
            'amount': amount,
            'steth_balance': self.web3.from_wei(steth_balance, 'ether'),
            'gas_used': receipt['gasUsed']
        }
    
    async def get_steth_balance(self, wallet_address: str) -> float:
        """Get stETH balance for a wallet.
        
        Args:
            wallet_address: Wallet address to check
            
        Returns:
            stETH balance in ETH
        """
        balance_wei = self.lido_contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        
        return self.web3.from_wei(balance_wei, 'ether')

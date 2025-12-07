"""
Uniswap V2/V3 integration for token swaps on EVM chains.

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
from typing import Dict, Any, Optional
from web3 import Web3
from web3.contract import Contract
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Uniswap V2 Router ABI (minimal for swaps)
UNISWAP_V2_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI (minimal for approve and balance)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]


class UniswapIntegration:
    """Integration with Uniswap V2 Router for token swaps."""
    
    def __init__(self, web3: Web3, router_address: str, chain: str):
        """Initialize Uniswap integration.
        
        Args:
            web3: Web3 instance
            router_address: Uniswap router contract address
            chain: Chain identifier
        """
        self.web3 = web3
        self.router_address = Web3.to_checksum_address(router_address)
        self.chain = chain
        self.router = self.web3.eth.contract(
            address=self.router_address,
            abi=UNISWAP_V2_ROUTER_ABI
        )
        self.slippage_tolerance = float(os.getenv('SLIPPAGE_TOLERANCE', '0.03'))
        
        logger.info(
            "uniswap_initialized",
            chain=chain,
            router=self.router_address,
            slippage=self.slippage_tolerance
        )
    
    def get_token_contract(self, token_address: str) -> Contract:
        """Get ERC20 token contract instance.
        
        Args:
            token_address: Token contract address
            
        Returns:
            Contract instance
        """
        return self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
    
    def _build_transaction_params(self, wallet: str, nonce: int, gas_limit: int) -> Dict[str, Any]:
        """Build transaction parameters with EIP-1559 support.
        
        Args:
            wallet: Wallet address
            nonce: Transaction nonce
            gas_limit: Gas limit
            
        Returns:
            Transaction parameters dict
        """
        try:
            # Try EIP-1559 transaction (preferred)
            latest_block = self.web3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', 0)
            
            if base_fee > 0:
                # Chain supports EIP-1559
                max_priority_fee = Web3.to_wei(2, 'gwei')
                max_fee = (base_fee * 2) + max_priority_fee
                
                return {
                    'from': wallet,
                    'nonce': nonce,
                    'gas': gas_limit,
                    'maxFeePerGas': max_fee,
                    'maxPriorityFeePerGas': max_priority_fee,
                    'type': '0x2',  # EIP-1559 transaction
                }
        except Exception as e:
            logger.debug(
                "eip1559_not_supported",
                chain=self.chain,
                error=str(e)
            )
        
        # Fallback to legacy transaction
        return {
            'from': wallet,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': self.web3.eth.gas_price,
            'type': '0x0',  # Legacy transaction
        }
    
    async def approve_token(
        self,
        token_address: str,
        wallet_address: str,
        private_key: str,
        amount: int
    ) -> str:
        """Approve token spending by router.
        
        Args:
            token_address: Token to approve
            wallet_address: Wallet address
            private_key: Private key for signing
            amount: Amount to approve (in wei)
            
        Returns:
            Transaction hash
        """
        token = self.get_token_contract(token_address)
        wallet = Web3.to_checksum_address(wallet_address)
        
        # Check current allowance
        allowance = token.functions.allowance(wallet, self.router_address).call()
        
        if allowance >= amount:
            logger.info(
                "token_already_approved",
                token=token_address,
                allowance=allowance,
                required=amount
            )
            return "0x" + "00" * 32  # Return dummy hash if already approved
        
        # Build approval transaction
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        tx = token.functions.approve(
            self.router_address,
            amount
        ).build_transaction(
            self._build_transaction_params(wallet, nonce, 100000)
        )
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "token_approved",
            token=token_address,
            tx_hash=receipt['transactionHash'].hex(),
            status=receipt['status']
        )
        
        return receipt['transactionHash'].hex()
    
    async def swap_exact_tokens_for_tokens(
        self,
        from_token: str,
        to_token: str,
        amount_in: int,
        wallet_address: str,
        private_key: str,
        deadline_minutes: int = 20
    ) -> Dict[str, Any]:
        """Swap exact amount of tokens for tokens.
        
        Args:
            from_token: Source token address
            to_token: Destination token address
            amount_in: Amount to swap (in wei)
            wallet_address: Wallet address
            private_key: Private key for signing
            deadline_minutes: Transaction deadline in minutes
            
        Returns:
            Result dictionary with tx_hash and amounts
        """
        wallet = Web3.to_checksum_address(wallet_address)
        from_token = Web3.to_checksum_address(from_token)
        to_token = Web3.to_checksum_address(to_token)
        
        # Approve token spending first
        await self.approve_token(from_token, wallet_address, private_key, amount_in)
        
        # Get expected output amount
        path = [from_token, to_token]
        amounts_out = self.router.functions.getAmountsOut(amount_in, path).call()
        amount_out_min = int(amounts_out[1] * (1 - self.slippage_tolerance))
        
        # Build swap transaction
        latest_block = self.web3.eth.get_block('latest')
        deadline = latest_block['timestamp'] + (deadline_minutes * 60)
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        tx = self.router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            path,
            wallet,
            deadline
        ).build_transaction(
            self._build_transaction_params(wallet, nonce, 250000)
        )
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "swap_completed",
            from_token=from_token,
            to_token=to_token,
            amount_in=amount_in,
            amount_out_min=amount_out_min,
            tx_hash=receipt['transactionHash'].hex(),
            status=receipt['status']
        )
        
        return {
            'tx_hash': receipt['transactionHash'].hex(),
            'amount_in': amount_in,
            'amount_out_min': amount_out_min,
            'status': receipt['status']
        }
    
    async def swap_exact_eth_for_tokens(
        self,
        to_token: str,
        amount_in: int,
        wallet_address: str,
        private_key: str,
        deadline_minutes: int = 20
    ) -> Dict[str, Any]:
        """Swap exact ETH for tokens.
        
        Args:
            to_token: Destination token address
            amount_in: Amount of ETH to swap (in wei)
            wallet_address: Wallet address
            private_key: Private key for signing
            deadline_minutes: Transaction deadline in minutes
            
        Returns:
            Result dictionary with tx_hash and amounts
        """
        wallet = Web3.to_checksum_address(wallet_address)
        to_token = Web3.to_checksum_address(to_token)
        
        # WETH address - must be configured for the chain
        weth_address = os.getenv(f'WETH_{self.chain.upper()}')
        if not weth_address:
            raise ValueError(f"WETH address not configured for chain {self.chain}. Set WETH_{self.chain.upper()} in environment.")
        weth = Web3.to_checksum_address(weth_address)
        
        # Get expected output amount
        path = [weth, to_token]
        amounts_out = self.router.functions.getAmountsOut(amount_in, path).call()
        amount_out_min = int(amounts_out[1] * (1 - self.slippage_tolerance))
        
        # Build swap transaction
        latest_block = self.web3.eth.get_block('latest')
        deadline = latest_block['timestamp'] + (deadline_minutes * 60)
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        tx_params = self._build_transaction_params(wallet, nonce, 250000)
        tx_params['value'] = amount_in  # Add ETH value
        
        tx = self.router.functions.swapExactETHForTokens(
            amount_out_min,
            path,
            wallet,
            deadline
        ).build_transaction(tx_params)
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "eth_swap_completed",
            to_token=to_token,
            amount_in=amount_in,
            amount_out_min=amount_out_min,
            tx_hash=receipt['transactionHash'].hex(),
            status=receipt['status']
        )
        
        return {
            'tx_hash': receipt['transactionHash'].hex(),
            'amount_in': amount_in,
            'amount_out_min': amount_out_min,
            'status': receipt['status']
        }

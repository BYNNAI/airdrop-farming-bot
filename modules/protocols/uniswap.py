"""
Uniswap DEX integration for token swaps on EVM chains.

Supports Uniswap V2 and V3 on various testnets including Sepolia, Goerli,
and other EVM-compatible test networks.

Author: BYNNΛI
License: MIT
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
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

# ERC20 ABI (minimal for approve)
ERC20_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
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
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Testnet router addresses
UNISWAP_ROUTERS = {
    'ethereum_sepolia': '0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008',  # Uniswap V2 on Sepolia
    'ethereum_goerli': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',  # Uniswap V2 on Goerli
    'base_sepolia': '0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4',  # Base Sepolia router
    'arbitrum_sepolia': '0x101F443B4d1b059569D643917553c771E1b9663E',  # Arbitrum Sepolia
}

# Common testnet tokens (WETH, USDC, DAI equivalents on testnets)
TESTNET_TOKENS = {
    'ethereum_sepolia': {
        'WETH': '0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9',
        'USDC': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
        'DAI': '0x68194a729C2450ad26072b3D33ADaCbcef39D574',
    },
    'ethereum_goerli': {
        'WETH': '0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6',
        'USDC': '0x07865c6E87B9F70255377e024ace6630C1Eaa37F',
        'DAI': '0x11fE4B6AE13d2a6055C8D9cF65c55bac32B5d844',
    },
    'base_sepolia': {
        'WETH': '0x4200000000000000000000000000000000000006',
        'USDC': '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
    },
    'arbitrum_sepolia': {
        'WETH': '0x980B62Da83eFf3D4576C647993b0c1D7faf17c73',
        'USDC': '0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d',
    }
}


class UniswapIntegration:
    """Integration with Uniswap DEX for token swaps."""
    
    def __init__(self, web3: Web3, chain: str):
        """Initialize Uniswap integration.
        
        Args:
            web3: Web3 instance connected to the chain
            chain: Chain identifier (e.g., 'ethereum_sepolia')
        """
        self.web3 = web3
        self.chain = chain
        self.router_address = UNISWAP_ROUTERS.get(chain)
        self.tokens = TESTNET_TOKENS.get(chain, {})
        
        if not self.router_address:
            raise ValueError(f"No Uniswap router configured for chain: {chain}")
        
        self.router_contract = web3.eth.contract(
            address=Web3.to_checksum_address(self.router_address),
            abi=UNISWAP_V2_ROUTER_ABI
        )
        
        logger.info(
            "uniswap_integration_initialized",
            chain=chain,
            router=self.router_address
        )
    
    def get_token_address(self, token_symbol: str) -> str:
        """Get token address by symbol.
        
        Args:
            token_symbol: Token symbol (e.g., 'WETH', 'USDC')
            
        Returns:
            Token address
        """
        # Handle native ETH
        if token_symbol.upper() in ['ETH', 'NATIVE']:
            return '0x0000000000000000000000000000000000000000'
        
        # Check if it's already an address
        if token_symbol.startswith('0x'):
            return token_symbol
        
        # Look up in token list
        token_address = self.tokens.get(token_symbol.upper())
        if not token_address:
            raise ValueError(f"Unknown token symbol: {token_symbol} on {self.chain}")
        
        return token_address
    
    async def approve_token(
        self,
        token_address: str,
        owner_address: str,
        private_key: str,
        amount: int
    ) -> str:
        """Approve token spending for the router.
        
        Args:
            token_address: Token contract address
            owner_address: Owner wallet address
            private_key: Owner's private key
            amount: Amount to approve (in wei)
            
        Returns:
            Transaction hash
        """
        token_contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        # Check current allowance
        current_allowance = token_contract.functions.allowance(
            Web3.to_checksum_address(owner_address),
            Web3.to_checksum_address(self.router_address)
        ).call()
        
        if current_allowance >= amount:
            logger.info(
                "token_already_approved",
                token=token_address,
                allowance=current_allowance,
                required=amount
            )
            return None  # Already approved
        
        # Build approval transaction
        approve_tx = token_contract.functions.approve(
            Web3.to_checksum_address(self.router_address),
            amount
        ).build_transaction({
            'from': Web3.to_checksum_address(owner_address),
            'nonce': self.web3.eth.get_transaction_count(owner_address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "token_approved",
            token=token_address,
            tx_hash=tx_hash.hex(),
            status=receipt['status']
        )
        
        return tx_hash.hex()
    
    async def swap(
        self,
        from_token: str,
        to_token: str,
        amount_in: float,
        wallet_address: str,
        private_key: str,
        slippage_percent: float = 3.0
    ) -> Dict[str, Any]:
        """Execute a token swap.
        
        Args:
            from_token: Source token symbol or address
            to_token: Destination token symbol or address
            amount_in: Amount to swap (in token units, not wei)
            wallet_address: Wallet address executing the swap
            private_key: Wallet's private key
            slippage_percent: Allowed slippage percentage (default 3%)
            
        Returns:
            Dict with transaction details
        """
        from_token_addr = self.get_token_address(from_token)
        to_token_addr = self.get_token_address(to_token)
        
        is_eth_in = from_token_addr == '0x0000000000000000000000000000000000000000'
        is_eth_out = to_token_addr == '0x0000000000000000000000000000000000000000'
        
        # Get token decimals
        if not is_eth_in:
            from_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(from_token_addr),
                abi=ERC20_ABI
            )
            from_decimals = from_contract.functions.decimals().call()
        else:
            from_decimals = 18
        
        # Convert amount to wei
        amount_in_wei = int(amount_in * (10 ** from_decimals))
        
        # Approve token if not ETH
        if not is_eth_in:
            await self.approve_token(
                from_token_addr,
                wallet_address,
                private_key,
                amount_in_wei
            )
        
        # Build swap path
        if is_eth_in or is_eth_out:
            # Direct swap with ETH
            if is_eth_in:
                path = [
                    Web3.to_checksum_address(self.tokens.get('WETH', from_token_addr)),
                    Web3.to_checksum_address(to_token_addr)
                ]
            else:
                path = [
                    Web3.to_checksum_address(from_token_addr),
                    Web3.to_checksum_address(self.tokens.get('WETH', to_token_addr))
                ]
        else:
            # Token to token via WETH
            weth = self.tokens.get('WETH')
            if weth:
                path = [
                    Web3.to_checksum_address(from_token_addr),
                    Web3.to_checksum_address(weth),
                    Web3.to_checksum_address(to_token_addr)
                ]
            else:
                path = [
                    Web3.to_checksum_address(from_token_addr),
                    Web3.to_checksum_address(to_token_addr)
                ]
        
        # Get expected output amount
        try:
            amounts_out = self.router_contract.functions.getAmountsOut(
                amount_in_wei,
                path
            ).call()
            expected_out = amounts_out[-1]
        except Exception as e:
            logger.warning("could_not_get_amounts_out", error=str(e))
            expected_out = 0
        
        # Calculate minimum output with slippage
        min_amount_out = int(expected_out * (1 - slippage_percent / 100))
        
        # Get deadline (10 minutes from now)
        deadline = self.web3.eth.get_block('latest')['timestamp'] + 600
        
        # Build swap transaction
        if is_eth_in:
            swap_tx = self.router_contract.functions.swapExactETHForTokens(
                min_amount_out,
                path,
                Web3.to_checksum_address(wallet_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(wallet_address),
                'value': amount_in_wei,
                'nonce': self.web3.eth.get_transaction_count(wallet_address),
                'gas': 250000,
                'gasPrice': self.web3.eth.gas_price
            })
        elif is_eth_out:
            swap_tx = self.router_contract.functions.swapExactTokensForETH(
                amount_in_wei,
                min_amount_out,
                path,
                Web3.to_checksum_address(wallet_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(wallet_address),
                'nonce': self.web3.eth.get_transaction_count(wallet_address),
                'gas': 250000,
                'gasPrice': self.web3.eth.gas_price
            })
        else:
            swap_tx = self.router_contract.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_amount_out,
                path,
                Web3.to_checksum_address(wallet_address),
                deadline
            ).build_transaction({
                'from': Web3.to_checksum_address(wallet_address),
                'nonce': self.web3.eth.get_transaction_count(wallet_address),
                'gas': 300000,
                'gasPrice': self.web3.eth.gas_price
            })
        
        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(swap_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        success = receipt['status'] == 1
        
        logger.info(
            "swap_executed",
            from_token=from_token,
            to_token=to_token,
            amount_in=amount_in,
            tx_hash=tx_hash.hex(),
            status=success,
            gas_used=receipt['gasUsed']
        )
        
        return {
            'success': success,
            'tx_hash': tx_hash.hex(),
            'from_token': from_token,
            'to_token': to_token,
            'amount_in': amount_in,
            'expected_out': expected_out / (10 ** 18),  # Approximate
            'gas_used': receipt['gasUsed']
        }

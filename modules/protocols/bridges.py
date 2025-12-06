"""
Cross-chain bridge integrations for asset transfers.

Supports LayerZero, Wormhole, and native L2 bridges on testnets.

Author: BYNNΛI
License: MIT
"""

from typing import Dict, Any, Optional
from web3 import Web3
from utils.logging_config import get_logger

logger = get_logger(__name__)

# LayerZero Endpoint ABI (minimal for bridging)
LAYERZERO_ENDPOINT_ABI = [
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "bytes", "name": "_destination", "type": "bytes"},
            {"internalType": "bytes", "name": "_payload", "type": "bytes"},
            {"internalType": "address payable", "name": "_refundAddress", "type": "address"},
            {"internalType": "address", "name": "_zroPaymentAddress", "type": "address"},
            {"internalType": "bytes", "name": "_adapterParams", "type": "bytes"}
        ],
        "name": "send",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "uint16", "name": "_type", "type": "uint16"},
            {"internalType": "bytes", "name": "_adapterParams", "type": "bytes"},
            {"internalType": "bytes", "name": "_payload", "type": "bytes"}
        ],
        "name": "estimateFees",
        "outputs": [
            {"internalType": "uint256", "name": "nativeFee", "type": "uint256"},
            {"internalType": "uint256", "name": "zroFee", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Native L2 Bridge ABI (simplified)
L2_BRIDGE_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_to", "type": "address"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "uint32", "name": "_minGasLimit", "type": "uint32"},
            {"internalType": "bytes", "name": "_extraData", "type": "bytes"}
        ],
        "name": "bridgeETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "depositETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# LayerZero testnet endpoints
LAYERZERO_ENDPOINTS = {
    'ethereum_sepolia': '0xae92d5aD7583AD66E49A0c67BAd18F6ba52dDDc1',
    'ethereum_goerli': '0xbfD2135BFfbb0B5378b56643c2Df8a87552Bfa23',
    'arbitrum_sepolia': '0x6098e96a28E02f27B1e6BD381f870F1C8Bd169d3',
    'base_sepolia': '0x6098e96a28E02f27B1e6BD381f870F1C8Bd169d3',
    'polygon_amoy': '0x6098e96a28E02f27B1e6BD381f870F1C8Bd169d3',
}

# LayerZero chain IDs
LAYERZERO_CHAIN_IDS = {
    'ethereum_sepolia': 10161,
    'ethereum_goerli': 10121,
    'arbitrum_sepolia': 10231,
    'base_sepolia': 10245,
    'polygon_amoy': 10267,
    'bnb_testnet': 10102,
}

# Native L2 Bridge contracts (for Optimism, Arbitrum, Base)
L2_BRIDGE_CONTRACTS = {
    'arbitrum_sepolia': '0x902b3E5f8F19571859F4AB1003B960a5dF693aFF',  # Arbitrum Sepolia bridge
    'base_sepolia': '0x49048044D57e1C92A77f79988d21Fa8fAF74E97e',  # Base Sepolia bridge
    'optimism_sepolia': '0x5b47E1A08Ea6d985D6649300584e6722Ec4B1383',  # Optimism Sepolia bridge
}


class BridgeIntegration:
    """Integration with cross-chain bridge protocols."""
    
    def __init__(self, web3: Web3, chain: str):
        """Initialize bridge integration.
        
        Args:
            web3: Web3 instance connected to the source chain
            chain: Source chain identifier
        """
        self.web3 = web3
        self.chain = chain
        
        # Initialize LayerZero if available
        self.layerzero_endpoint = LAYERZERO_ENDPOINTS.get(chain)
        if self.layerzero_endpoint:
            self.layerzero_contract = web3.eth.contract(
                address=Web3.to_checksum_address(self.layerzero_endpoint),
                abi=LAYERZERO_ENDPOINT_ABI
            )
        
        # Initialize native L2 bridge if available
        self.l2_bridge_address = L2_BRIDGE_CONTRACTS.get(chain)
        if self.l2_bridge_address:
            self.l2_bridge_contract = web3.eth.contract(
                address=Web3.to_checksum_address(self.l2_bridge_address),
                abi=L2_BRIDGE_ABI
            )
        
        logger.info(
            "bridge_integration_initialized",
            chain=chain,
            has_layerzero=bool(self.layerzero_endpoint),
            has_l2_bridge=bool(self.l2_bridge_address)
        )
    
    async def bridge_via_layerzero(
        self,
        to_chain: str,
        amount: float,
        wallet_address: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Bridge assets using LayerZero.
        
        Args:
            to_chain: Destination chain identifier
            amount: Amount to bridge (in ETH)
            wallet_address: Source wallet address
            private_key: Wallet's private key
            
        Returns:
            Dict with transaction details
        """
        if not self.layerzero_endpoint:
            raise ValueError(f"LayerZero not available on {self.chain}")
        
        dst_chain_id = LAYERZERO_CHAIN_IDS.get(to_chain)
        if not dst_chain_id:
            raise ValueError(f"Unknown destination chain: {to_chain}")
        
        amount_wei = self.web3.to_wei(amount, 'ether')
        
        # Prepare destination address (same wallet on destination chain)
        destination = Web3.to_checksum_address(wallet_address)
        destination_bytes = destination.encode('utf-8')
        
        # Prepare payload (simple transfer)
        payload = self.web3.codec.encode(['address', 'uint256'], [destination, amount_wei])
        
        # Adapter params (default)
        adapter_params = b''
        
        # Estimate fees
        try:
            native_fee, zro_fee = self.layerzero_contract.functions.estimateFees(
                dst_chain_id,
                1,  # Type 1: send
                adapter_params,
                payload
            ).call()
        except Exception as e:
            logger.warning("fee_estimation_failed", error=str(e))
            native_fee = self.web3.to_wei(0.01, 'ether')  # Default estimate
            zro_fee = 0
        
        # Build bridge transaction
        total_value = amount_wei + native_fee
        
        bridge_tx = self.layerzero_contract.functions.send(
            dst_chain_id,
            destination_bytes,
            payload,
            Web3.to_checksum_address(wallet_address),  # Refund address
            '0x0000000000000000000000000000000000000000',  # No ZRO payment
            adapter_params
        ).build_transaction({
            'from': Web3.to_checksum_address(wallet_address),
            'value': total_value,
            'nonce': self.web3.eth.get_transaction_count(wallet_address),
            'gas': 200000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(bridge_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        success = receipt['status'] == 1
        
        logger.info(
            "layerzero_bridge_executed",
            from_chain=self.chain,
            to_chain=to_chain,
            amount=amount,
            tx_hash=tx_hash.hex(),
            status=success
        )
        
        return {
            'success': success,
            'tx_hash': tx_hash.hex(),
            'from_chain': self.chain,
            'to_chain': to_chain,
            'amount': amount,
            'bridge_type': 'layerzero',
            'gas_used': receipt['gasUsed']
        }
    
    async def bridge_via_native_l2(
        self,
        amount: float,
        wallet_address: str,
        private_key: str,
        min_gas_limit: int = 200000
    ) -> Dict[str, Any]:
        """Bridge to L2 using native bridge.
        
        Args:
            amount: Amount to bridge (in ETH)
            wallet_address: Source wallet address
            private_key: Wallet's private key
            min_gas_limit: Minimum gas limit for L2 execution
            
        Returns:
            Dict with transaction details
        """
        if not self.l2_bridge_address:
            raise ValueError(f"Native L2 bridge not available on {self.chain}")
        
        amount_wei = self.web3.to_wei(amount, 'ether')
        
        # Determine destination chain from source
        if 'arbitrum' in self.chain:
            to_chain = 'arbitrum'
        elif 'base' in self.chain:
            to_chain = 'base'
        elif 'optimism' in self.chain:
            to_chain = 'optimism'
        else:
            to_chain = 'unknown_l2'
        
        # Build bridge transaction
        try:
            # Try bridgeETH method first
            bridge_tx = self.l2_bridge_contract.functions.bridgeETH(
                Web3.to_checksum_address(wallet_address),
                amount_wei,
                min_gas_limit,
                b''  # No extra data
            ).build_transaction({
                'from': Web3.to_checksum_address(wallet_address),
                'value': amount_wei,
                'nonce': self.web3.eth.get_transaction_count(wallet_address),
                'gas': 150000,
                'gasPrice': self.web3.eth.gas_price
            })
        except Exception:
            # Fall back to simpler depositETH method
            bridge_tx = self.l2_bridge_contract.functions.depositETH(
            ).build_transaction({
                'from': Web3.to_checksum_address(wallet_address),
                'value': amount_wei,
                'nonce': self.web3.eth.get_transaction_count(wallet_address),
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price
            })
        
        # Sign and send transaction
        signed_tx = self.web3.eth.account.sign_transaction(bridge_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for receipt
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        success = receipt['status'] == 1
        
        logger.info(
            "native_l2_bridge_executed",
            from_chain=self.chain,
            to_chain=to_chain,
            amount=amount,
            tx_hash=tx_hash.hex(),
            status=success
        )
        
        return {
            'success': success,
            'tx_hash': tx_hash.hex(),
            'from_chain': self.chain,
            'to_chain': to_chain,
            'amount': amount,
            'bridge_type': 'native_l2',
            'gas_used': receipt['gasUsed']
        }
    
    async def bridge(
        self,
        to_chain: str,
        amount: float,
        wallet_address: str,
        private_key: str,
        bridge_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bridge assets to another chain.
        
        Args:
            to_chain: Destination chain identifier
            amount: Amount to bridge (in ETH)
            wallet_address: Source wallet address
            private_key: Wallet's private key
            bridge_type: Optional bridge type ('layerzero' or 'native_l2')
            
        Returns:
            Dict with transaction details
        """
        # Auto-detect bridge type if not specified
        if not bridge_type:
            if self.layerzero_endpoint and to_chain in LAYERZERO_CHAIN_IDS:
                bridge_type = 'layerzero'
            elif self.l2_bridge_address:
                bridge_type = 'native_l2'
            else:
                raise ValueError(f"No bridge available from {self.chain} to {to_chain}")
        
        if bridge_type == 'layerzero':
            return await self.bridge_via_layerzero(to_chain, amount, wallet_address, private_key)
        elif bridge_type == 'native_l2':
            return await self.bridge_via_native_l2(amount, wallet_address, private_key)
        else:
            raise ValueError(f"Unknown bridge type: {bridge_type}")

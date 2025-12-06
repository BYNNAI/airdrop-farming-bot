"""
Bridge integrations for cross-chain transfers (LayerZero, native bridges).

Author: BYNNΛI
License: MIT
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Generic bridge ABI (simplified for testnet bridges)
BRIDGE_ABI = [
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "bytes", "name": "_toAddress", "type": "bytes"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "address payable", "name": "_refundAddress", "type": "address"},
            {"internalType": "address", "name": "_zroPaymentAddress", "type": "address"},
            {"internalType": "bytes", "name": "_adapterParams", "type": "bytes"}
        ],
        "name": "sendFrom",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint16", "name": "_dstChainId", "type": "uint16"},
            {"internalType": "bytes", "name": "_toAddress", "type": "bytes"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "bool", "name": "_useZro", "type": "bool"},
            {"internalType": "bytes", "name": "_adapterParams", "type": "bytes"}
        ],
        "name": "estimateSendFee",
        "outputs": [
            {"internalType": "uint256", "name": "nativeFee", "type": "uint256"},
            {"internalType": "uint256", "name": "zroFee", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Native bridge ABI (for L2 native bridges)
NATIVE_BRIDGE_ABI = [
    {
        "inputs": [],
        "name": "depositETH",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "_to", "type": "address"},
            {"internalType": "uint256", "name": "_amount", "type": "uint256"},
            {"internalType": "uint32", "name": "_gasLimit", "type": "uint32"},
            {"internalType": "bytes", "name": "_data", "type": "bytes"}
        ],
        "name": "depositETHTo",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]


class BridgeIntegration:
    """Integration with bridge protocols."""
    
    def __init__(
        self,
        web3: Web3,
        bridge_address: str,
        chain: str,
        bridge_type: str = 'layerzero'
    ):
        """Initialize bridge integration.
        
        Args:
            web3: Web3 instance
            bridge_address: Bridge contract address
            chain: Source chain identifier
            bridge_type: Type of bridge (layerzero, native)
        """
        self.web3 = web3
        self.bridge_address = Web3.to_checksum_address(bridge_address)
        self.chain = chain
        self.bridge_type = bridge_type
        
        # Select appropriate ABI
        abi = BRIDGE_ABI if bridge_type == 'layerzero' else NATIVE_BRIDGE_ABI
        self.contract = self.web3.eth.contract(
            address=self.bridge_address,
            abi=abi
        )
        
        logger.info(
            "bridge_initialized",
            chain=chain,
            bridge=self.bridge_address,
            type=bridge_type
        )
    
    async def bridge_native_l2(
        self,
        amount: int,
        wallet_address: str,
        private_key: str,
        gas_limit: int = 200000
    ) -> Dict[str, Any]:
        """Bridge native token to L2 using native bridge.
        
        Args:
            amount: Amount to bridge (in wei)
            wallet_address: Wallet address
            private_key: Private key for signing
            gas_limit: Gas limit for L2 transaction
            
        Returns:
            Result dictionary with tx_hash
        """
        wallet = Web3.to_checksum_address(wallet_address)
        
        # Check balance
        balance = self.web3.eth.get_balance(wallet)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")
        
        # Build bridge transaction
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        # For native bridges, typically just call depositETH or depositETHTo
        tx = self.contract.functions.depositETHTo(
            wallet,  # recipient on L2
            amount,
            gas_limit,
            b''  # empty data
        ).build_transaction({
            'from': wallet,
            'value': amount,
            'nonce': nonce,
            'gas': 150000,
            'gasPrice': self.web3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "bridge_completed",
            bridge_type="native_l2",
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
            'gas_used': receipt['gasUsed'],
            'bridge_type': 'native_l2'
        }
    
    async def bridge_layerzero(
        self,
        dst_chain_id: int,
        amount: int,
        wallet_address: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Bridge using LayerZero protocol.
        
        Args:
            dst_chain_id: Destination chain ID (LayerZero format)
            amount: Amount to bridge (in wei)
            wallet_address: Wallet address
            private_key: Private key for signing
            
        Returns:
            Result dictionary with tx_hash
        """
        wallet = Web3.to_checksum_address(wallet_address)
        
        # Encode destination address (LayerZero expects address as bytes)
        # Remove '0x' prefix and convert hex to bytes
        to_address = bytes.fromhex(wallet[2:] if wallet.startswith('0x') else wallet)
        
        # Estimate fees
        adapter_params = b''
        native_fee, zro_fee = self.contract.functions.estimateSendFee(
            dst_chain_id,
            to_address,
            amount,
            False,
            adapter_params
        ).call()
        
        # Check balance
        balance = self.web3.eth.get_balance(wallet)
        total_needed = amount + native_fee
        if balance < total_needed:
            raise ValueError(f"Insufficient balance: {balance} < {total_needed}")
        
        # Build bridge transaction
        nonce = self.web3.eth.get_transaction_count(wallet)
        
        tx = self.contract.functions.sendFrom(
            dst_chain_id,
            to_address,
            amount,
            wallet,  # refund address
            Web3.to_checksum_address('0x' + '00' * 20),  # no ZRO payment
            adapter_params
        ).build_transaction({
            'from': wallet,
            'value': amount + native_fee,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price,
        })
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        logger.info(
            "bridge_completed",
            bridge_type="layerzero",
            dst_chain_id=dst_chain_id,
            amount=amount,
            wallet=wallet,
            tx_hash=receipt['transactionHash'].hex(),
            status=receipt['status'],
            gas_used=receipt['gasUsed']
        )
        
        return {
            'tx_hash': receipt['transactionHash'].hex(),
            'amount': amount,
            'dst_chain_id': dst_chain_id,
            'status': receipt['status'],
            'gas_used': receipt['gasUsed'],
            'bridge_type': 'layerzero'
        }

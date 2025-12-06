"""
Jupiter aggregator integration for Solana swaps.

Author: BYNNΛI
License: MIT
"""

import os
from typing import Dict, Any, Optional
import aiohttp
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
import base64
from utils.logging_config import get_logger

logger = get_logger(__name__)


class JupiterIntegration:
    """Integration with Jupiter aggregator for Solana swaps."""
    
    def __init__(self, rpc_url: str, use_devnet: bool = True):
        """Initialize Jupiter integration.
        
        Args:
            rpc_url: Solana RPC endpoint URL
            use_devnet: Whether to use devnet API (default: True for testing)
        """
        self.client = AsyncClient(rpc_url)
        self.rpc_url = rpc_url
        
        # Jupiter API endpoints
        # IMPORTANT: Jupiter does not provide a testnet/devnet API
        # All Jupiter API calls will use mainnet pricing and routes
        # For true testnet trading, consider using Raydium testnet instead
        self.api_base = "https://quote-api.jup.ag/v6"
        
        if use_devnet:
            logger.warning(
                "jupiter_mainnet_api_only",
                message="Jupiter API only supports mainnet. Quotes and routes will be from mainnet even though RPC is devnet/testnet. For testnet DEX functionality, consider Raydium or other testnet-compatible DEXes."
            )
        
        self.slippage_bps = int(float(os.getenv('SLIPPAGE_TOLERANCE', '0.03')) * 10000)
        
        logger.info(
            "jupiter_initialized",
            rpc_url=rpc_url,
            api_base=self.api_base,
            slippage_bps=self.slippage_bps
        )
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int
    ) -> Dict[str, Any]:
        """Get swap quote from Jupiter.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Input amount (in token's smallest unit)
            
        Returns:
            Quote data
        """
        params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': str(amount),
            'slippageBps': self.slippage_bps,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_base}/quote", params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Jupiter quote failed: {error_text}")
                
                quote = await response.json()
                
                logger.info(
                    "jupiter_quote_received",
                    input_mint=input_mint,
                    output_mint=output_mint,
                    in_amount=amount,
                    out_amount=quote.get('outAmount'),
                    price_impact=quote.get('priceImpactPct')
                )
                
                return quote
    
    async def swap(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        wallet_keypair: Keypair
    ) -> Dict[str, Any]:
        """Execute swap via Jupiter.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Input amount (in token's smallest unit)
            wallet_keypair: Wallet keypair for signing
            
        Returns:
            Result dictionary with transaction signature
        """
        # Get quote
        quote = await self.get_quote(input_mint, output_mint, amount)
        
        # Get swap transaction
        swap_request = {
            'quoteResponse': quote,
            'userPublicKey': str(wallet_keypair.pubkey()),
            'wrapAndUnwrapSol': True,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_base}/swap", json=swap_request) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Jupiter swap transaction failed: {error_text}")
                
                swap_data = await response.json()
        
        # Decode and sign transaction
        swap_transaction_buf = base64.b64decode(swap_data['swapTransaction'])
        tx = VersionedTransaction.from_bytes(swap_transaction_buf)
        
        # Sign transaction
        tx.sign([wallet_keypair])
        
        # Send transaction
        result = await self.client.send_transaction(tx)
        signature = result.value
        
        # Wait for confirmation
        await self.client.confirm_transaction(signature, commitment=Confirmed)
        
        logger.info(
            "jupiter_swap_completed",
            input_mint=input_mint,
            output_mint=output_mint,
            in_amount=amount,
            out_amount=quote.get('outAmount'),
            signature=str(signature)
        )
        
        return {
            'tx_hash': str(signature),
            'input_mint': input_mint,
            'output_mint': output_mint,
            'amount_in': amount,
            'amount_out': quote.get('outAmount')
        }
    
    async def get_token_balance(self, wallet_pubkey: str, token_mint: str) -> int:
        """Get SPL token balance.
        
        Args:
            wallet_pubkey: Wallet public key
            token_mint: Token mint address
            
        Returns:
            Token balance in smallest unit
        """
        pubkey = Pubkey.from_string(wallet_pubkey)
        
        # Get token accounts
        result = await self.client.get_token_accounts_by_owner(
            pubkey,
            {"mint": Pubkey.from_string(token_mint)}
        )
        
        if not result.value:
            return 0
        
        # Get balance from first token account
        token_account = result.value[0].pubkey
        balance_result = await self.client.get_token_account_balance(token_account)
        balance = int(balance_result.value.amount)
        
        logger.debug(
            "token_balance_checked",
            wallet=wallet_pubkey,
            token_mint=token_mint,
            balance=balance
        )
        
        return balance
    
    async def close(self):
        """Close the RPC client connection."""
        await self.client.close()

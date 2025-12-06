"""
Jupiter aggregator integration for Solana token swaps.

Supports Jupiter API for optimal swap routing on Solana devnet/testnet.

Author: BYNNΛI
License: MIT
"""

import asyncio
from typing import Dict, Any, Optional
import aiohttp
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from utils.logging_config import get_logger
import base64

logger = get_logger(__name__)

# Jupiter API endpoints
JUPITER_API_BASE = "https://quote-api.jup.ag/v6"

# Common Solana testnet/devnet tokens
SOLANA_TOKENS = {
    'SOL': 'So11111111111111111111111111111111111111112',  # Native SOL (wrapped)
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC (may not be on devnet)
    'WSOL': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
}


class JupiterIntegration:
    """Integration with Jupiter aggregator for Solana swaps."""
    
    def __init__(self, rpc_client: AsyncClient):
        """Initialize Jupiter integration.
        
        Args:
            rpc_client: Solana RPC client
        """
        self.rpc_client = rpc_client
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info("jupiter_integration_initialized")
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def get_token_mint(self, token_symbol: str) -> str:
        """Get token mint address by symbol.
        
        Args:
            token_symbol: Token symbol (e.g., 'SOL', 'USDC')
            
        Returns:
            Token mint address
        """
        # Check if it's already an address
        if len(token_symbol) > 32:
            return token_symbol
        
        # Look up in token list
        token_mint = SOLANA_TOKENS.get(token_symbol.upper())
        if not token_mint:
            raise ValueError(f"Unknown token symbol: {token_symbol}")
        
        return token_mint
    
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 300  # 3% = 300 basis points
    ) -> Dict[str, Any]:
        """Get swap quote from Jupiter.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Input amount in lamports/smallest unit
            slippage_bps: Slippage tolerance in basis points (default 300 = 3%)
            
        Returns:
            Quote data
        """
        await self._ensure_session()
        
        params = {
            'inputMint': input_mint,
            'outputMint': output_mint,
            'amount': str(amount),
            'slippageBps': str(slippage_bps),
        }
        
        try:
            async with self.session.get(
                f"{JUPITER_API_BASE}/quote",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Jupiter API error: {response.status} - {error_text}")
                
                quote_data = await response.json()
                return quote_data
        except Exception as e:
            logger.error("jupiter_quote_failed", error=str(e))
            raise
    
    async def get_swap_transaction(
        self,
        quote: Dict[str, Any],
        user_public_key: str
    ) -> str:
        """Get swap transaction from Jupiter.
        
        Args:
            quote: Quote data from get_quote()
            user_public_key: User's public key (base58 string)
            
        Returns:
            Serialized transaction (base64)
        """
        await self._ensure_session()
        
        payload = {
            'quoteResponse': quote,
            'userPublicKey': user_public_key,
            'wrapAndUnwrapSol': True,
        }
        
        try:
            async with self.session.post(
                f"{JUPITER_API_BASE}/swap",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Jupiter swap API error: {response.status} - {error_text}")
                
                swap_data = await response.json()
                return swap_data.get('swapTransaction')
        except Exception as e:
            logger.error("jupiter_swap_transaction_failed", error=str(e))
            raise
    
    async def swap(
        self,
        from_token: str,
        to_token: str,
        amount: float,
        keypair: Keypair,
        slippage_percent: float = 3.0
    ) -> Dict[str, Any]:
        """Execute a token swap via Jupiter.
        
        Args:
            from_token: Source token symbol or mint address
            to_token: Destination token symbol or mint address
            amount: Amount to swap (in token units, not lamports)
            keypair: Wallet keypair
            slippage_percent: Slippage tolerance percentage (default 3%)
            
        Returns:
            Dict with transaction details
        """
        input_mint = self.get_token_mint(from_token)
        output_mint = self.get_token_mint(to_token)
        
        # Convert amount to lamports (assuming 9 decimals for SOL)
        # For production, should query token decimals
        decimals = 9
        amount_lamports = int(amount * (10 ** decimals))
        
        slippage_bps = int(slippage_percent * 100)
        
        # Get quote
        logger.info(
            "requesting_jupiter_quote",
            from_token=from_token,
            to_token=to_token,
            amount=amount
        )
        
        quote = await self.get_quote(
            input_mint,
            output_mint,
            amount_lamports,
            slippage_bps
        )
        
        # Get swap transaction
        user_public_key = str(keypair.pubkey())
        swap_transaction_b64 = await self.get_swap_transaction(quote, user_public_key)
        
        # Deserialize transaction
        swap_transaction_bytes = base64.b64decode(swap_transaction_b64)
        
        try:
            # Try to deserialize as VersionedTransaction
            transaction = VersionedTransaction.from_bytes(swap_transaction_bytes)
            
            # Sign the transaction
            signed_tx = VersionedTransaction.populate(
                transaction.message,
                [keypair]
            )
            
            # Serialize signed transaction
            serialized_tx = bytes(signed_tx)
        except Exception as e:
            logger.warning("versioned_transaction_failed", error=str(e))
            # Fallback to legacy transaction
            transaction = Transaction.deserialize(swap_transaction_bytes)
            transaction.sign(keypair)
            serialized_tx = transaction.serialize()
        
        # Send transaction
        try:
            result = await self.rpc_client.send_raw_transaction(
                serialized_tx,
                opts={'skip_preflight': False, 'preflight_commitment': 'confirmed'}
            )
            
            tx_hash = str(result.value)
            
            # Wait for confirmation
            confirmation = await self.rpc_client.confirm_transaction(
                tx_hash,
                commitment='confirmed'
            )
            
            success = not confirmation.value.err
            
            out_amount = float(quote.get('outAmount', 0)) / (10 ** decimals)
            
            logger.info(
                "jupiter_swap_executed",
                from_token=from_token,
                to_token=to_token,
                amount_in=amount,
                amount_out=out_amount,
                tx_hash=tx_hash,
                status=success
            )
            
            return {
                'success': success,
                'tx_hash': tx_hash,
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount,
                'amount_out': out_amount
            }
        except Exception as e:
            logger.error("jupiter_swap_send_failed", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'from_token': from_token,
                'to_token': to_token,
                'amount_in': amount
            }
    
    async def simple_sol_transfer(
        self,
        from_keypair: Keypair,
        to_pubkey: Pubkey,
        amount_sol: float
    ) -> Dict[str, Any]:
        """Execute a simple SOL transfer (fallback for testing).
        
        Args:
            from_keypair: Source wallet keypair
            to_pubkey: Destination public key
            amount_sol: Amount of SOL to transfer
            
        Returns:
            Dict with transaction details
        """
        amount_lamports = int(amount_sol * 1e9)
        
        # Create transfer instruction
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=from_keypair.pubkey(),
                to_pubkey=to_pubkey,
                lamports=amount_lamports
            )
        )
        
        # Get recent blockhash
        recent_blockhash = await self.rpc_client.get_latest_blockhash()
        
        # Create and sign transaction
        transaction = Transaction(
            recent_blockhash=recent_blockhash.value.blockhash,
            fee_payer=from_keypair.pubkey()
        ).add(transfer_ix)
        
        transaction.sign(from_keypair)
        
        # Send transaction
        result = await self.rpc_client.send_transaction(transaction)
        tx_hash = str(result.value)
        
        # Wait for confirmation
        confirmation = await self.rpc_client.confirm_transaction(
            tx_hash,
            commitment='confirmed'
        )
        
        success = not confirmation.value.err
        
        logger.info(
            "sol_transfer_executed",
            amount=amount_sol,
            tx_hash=tx_hash,
            status=success
        )
        
        return {
            'success': success,
            'tx_hash': tx_hash,
            'amount': amount_sol
        }

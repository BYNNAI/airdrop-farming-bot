"""HD wallet generation and management with encryption."""

import os
from typing import List, Optional, Dict, Tuple
from cryptography.fernet import Fernet
from mnemonic import Mnemonic
from eth_account import Account
from eth_account.hdaccount import HDPath
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from utils.database import Wallet, db_manager, get_db_session
from utils.logging_config import get_logger
import base58

logger = get_logger(__name__)


class WalletManager:
    """Manage HD wallet generation, derivation, and encryption."""
    
    def __init__(
        self,
        seed_mnemonic: Optional[str] = None,
        encryption_key: Optional[str] = None,
        derivation_path: str = "m/44'/60'/0'/0"
    ):
        """Initialize wallet manager.
        
        Args:
            seed_mnemonic: BIP39 mnemonic seed phrase
            encryption_key: Encryption key for securing sensitive data
            derivation_path: HD derivation path (BIP44 format)
        """
        self.seed_mnemonic = seed_mnemonic or os.getenv("WALLET_SEED_MNEMONIC", "")
        encryption_key = encryption_key or os.getenv("WALLET_ENCRYPTION_KEY", "")
        
        # Validate inputs
        if not self.seed_mnemonic or self.seed_mnemonic == "your_24_word_seed_phrase_here":
            logger.warning("No valid seed mnemonic provided. Generate one first.")
            self.seed_mnemonic = None
        
        if not encryption_key or len(encryption_key) < 32:
            logger.warning("Encryption key should be at least 32 characters")
            # Generate a key if none provided (for development only)
            encryption_key = Fernet.generate_key().decode()
            logger.info("Generated temporary encryption key (not suitable for production)")
        
        self.encryption_key = encryption_key
        self.fernet = Fernet(self._derive_fernet_key(encryption_key))
        self.derivation_path = derivation_path
        
        # Enable HD wallet derivation
        Account.enable_unaudited_hdwallet_features()
        
    def _derive_fernet_key(self, key: str) -> bytes:
        """Derive a valid Fernet key from arbitrary string.
        
        Args:
            key: Input key string
            
        Returns:
            Valid Fernet key bytes
        """
        import hashlib
        import base64
        
        # Hash and encode to get 32-byte key
        hashed = hashlib.sha256(key.encode()).digest()
        return base64.urlsafe_b64encode(hashed)
    
    def generate_mnemonic(self, word_count: int = 24) -> str:
        """Generate a new BIP39 mnemonic seed phrase.
        
        Args:
            word_count: Number of words (12 or 24)
            
        Returns:
            Mnemonic seed phrase
        """
        strength = 128 if word_count == 12 else 256
        mnemo = Mnemonic("english")
        mnemonic = mnemo.generate(strength=strength)
        
        logger.info(
            "mnemonic_generated",
            word_count=word_count,
            entropy_bits=strength
        )
        
        return mnemonic
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data.
        
        Args:
            data: Plain text data
            
        Returns:
            Encrypted data (base64 encoded)
        """
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt encrypted data.
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
            
        Returns:
            Decrypted plain text
        """
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def derive_evm_wallet(self, index: int) -> Tuple[str, str]:
        """Derive an EVM wallet from HD seed.
        
        Args:
            index: Derivation index
            
        Returns:
            Tuple of (address, private_key)
        """
        if not self.seed_mnemonic:
            raise ValueError("No seed mnemonic available")
        
        # Validate mnemonic before derivation
        mnemo = Mnemonic("english")
        if not mnemo.check(self.seed_mnemonic):
            raise ValueError("Invalid BIP39 mnemonic phrase")
        
        # Derive account from mnemonic
        account = Account.from_mnemonic(
            self.seed_mnemonic,
            account_path=f"{self.derivation_path}/{index}"
        )
        
        address = account.address
        private_key = account.key.hex()
        
        return address, private_key
    
    def derive_solana_wallet(self, index: int) -> Tuple[str, str]:
        """Derive a Solana wallet from HD seed.
        
        Args:
            index: Derivation index
            
        Returns:
            Tuple of (address, private_key_base58)
        """
        if not self.seed_mnemonic:
            raise ValueError("No seed mnemonic available")
        
        # For Solana, we'll use a simple derivation from the seed
        # In production, use proper BIP44 Solana derivation (m/44'/501'/0'/0')
        import hashlib
        
        # Derive a deterministic seed for this index
        seed_with_index = f"{self.seed_mnemonic}:{index}:solana"
        derived_seed = hashlib.sha256(seed_with_index.encode()).digest()
        
        # Create keypair from seed
        keypair = Keypair.from_seed(derived_seed[:32])
        
        address = str(keypair.pubkey())
        private_key = base58.b58encode(bytes(keypair)).decode()
        
        return address, private_key
    
    def generate_wallets(
        self,
        count: int,
        chains: List[str] = None,
        shard_size: int = 10
    ) -> Dict[str, List[str]]:
        """Generate multiple HD-derived wallets and store in database.
        
        Args:
            count: Number of wallets to generate per chain
            chains: List of chains ('evm', 'solana', 'all')
            shard_size: Number of wallets per shard
            
        Returns:
            Dictionary mapping chain to list of addresses
        """
        if not self.seed_mnemonic:
            raise ValueError("No seed mnemonic available. Generate one first.")
        
        chains = chains or ['evm', 'solana']
        if 'all' in chains:
            chains = ['evm', 'solana']
        
        generated = {}
        
        with get_db_session() as session:
            for chain in chains:
                addresses = []
                
                for i in range(count):
                    shard_id = i // shard_size
                    
                    try:
                        if chain == 'evm':
                            address, private_key = self.derive_evm_wallet(i)
                        elif chain == 'solana':
                            address, private_key = self.derive_solana_wallet(i)
                        else:
                            logger.warning(f"Unsupported chain: {chain}")
                            continue
                        
                        # Check if wallet already exists
                        existing = session.query(Wallet).filter_by(
                            address=address,
                            chain=chain
                        ).first()
                        
                        if not existing:
                            wallet = Wallet(
                                address=address,
                                chain=chain,
                                derivation_index=i,
                                shard_id=shard_id,
                                enabled=True
                            )
                            session.add(wallet)
                            addresses.append(address)
                            
                            logger.info(
                                "wallet_generated",
                                chain=chain,
                                address=address,
                                index=i,
                                shard=shard_id
                            )
                        else:
                            addresses.append(address)
                            logger.debug(
                                "wallet_exists",
                                chain=chain,
                                address=address
                            )
                    
                    except Exception as e:
                        logger.error(
                            "wallet_generation_failed",
                            chain=chain,
                            index=i,
                            error=str(e)
                        )
                
                generated[chain] = addresses
                session.commit()
        
        logger.info(
            "wallets_generated",
            total=sum(len(addrs) for addrs in generated.values()),
            by_chain={k: len(v) for k, v in generated.items()}
        )
        
        return generated
    
    def get_wallets(
        self,
        chain: Optional[str] = None,
        shard_id: Optional[int] = None,
        enabled_only: bool = True
    ) -> List[Wallet]:
        """Get wallets from database.
        
        Args:
            chain: Filter by chain
            shard_id: Filter by shard
            enabled_only: Only return enabled wallets
            
        Returns:
            List of wallet records
        """
        with get_db_session() as session:
            query = session.query(Wallet)
            
            if chain:
                query = query.filter(Wallet.chain == chain)
            if shard_id is not None:
                query = query.filter(Wallet.shard_id == shard_id)
            if enabled_only:
                query = query.filter(Wallet.enabled == True)
            
            wallets = query.all()
            
            # Detach from session
            session.expunge_all()
            
            return wallets
    
    def get_private_key(self, address: str, chain: str) -> Optional[str]:
        """Get private key for a wallet address.
        
        IMPORTANT: Private keys are derived on-demand from seed, never stored.
        
        Args:
            address: Wallet address
            chain: Blockchain name
            
        Returns:
            Private key or None if not found
        """
        with get_db_session() as session:
            wallet = session.query(Wallet).filter_by(
                address=address,
                chain=chain
            ).first()
            
            if not wallet:
                return None
            
            # Derive private key from seed
            try:
                if chain == 'evm':
                    _, private_key = self.derive_evm_wallet(wallet.derivation_index)
                elif chain == 'solana':
                    _, private_key = self.derive_solana_wallet(wallet.derivation_index)
                else:
                    return None
                
                return private_key
            except Exception as e:
                logger.error(
                    "private_key_derivation_failed",
                    address=address,
                    chain=chain,
                    error=str(e)
                )
                return None
    
    def update_nonce(self, address: str, chain: str, nonce: int):
        """Update wallet nonce (for EVM chains).
        
        Args:
            address: Wallet address
            chain: Blockchain name
            nonce: New nonce value
        """
        with get_db_session() as session:
            wallet = session.query(Wallet).filter_by(
                address=address,
                chain=chain
            ).first()
            
            if wallet:
                wallet.nonce = nonce
                session.commit()
                
                logger.debug(
                    "nonce_updated",
                    address=address,
                    chain=chain,
                    nonce=nonce
                )

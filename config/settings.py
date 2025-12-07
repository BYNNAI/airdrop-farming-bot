"""
Configuration settings for airdrop farming system.

This module provides centralized configuration management with environment variable
support for network settings, timing parameters, and behavioral patterns.

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
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Wallet Settings
    MAX_WALLETS = 50
    WALLET_ENCRYPTION_ENABLED = True
    
    # Network Settings
    TESTNET_MODE = os.getenv('TESTNET_MODE', 'true').lower() == 'true'
    SOLANA_NETWORK = 'devnet' if TESTNET_MODE else 'mainnet-beta'
    ETH_NETWORK = 'sepolia' if TESTNET_MODE else 'mainnet'
    
    # RPC Endpoints
    SOLANA_RPC = {
        'mainnet': os.getenv('SOLANA_RPC_MAINNET', 'https://api.mainnet-beta.solana.com'),
        'testnet': os.getenv('SOLANA_RPC_TESTNET', 'https://api.testnet.solana.com'),
        'devnet': os.getenv('SOLANA_RPC_DEVNET', 'https://api.devnet.solana.com')
    }
    
    ETH_RPC = {
        'mainnet': os.getenv('ETH_RPC_MAINNET', 'https://eth.llamarpc.com'),
        'sepolia': os.getenv('ETH_RPC_SEPOLIA', 'https://rpc.sepolia.org')
    }
    
    # Timing Settings (in seconds)
    MIN_DELAY = int(os.getenv('MIN_DELAY_SECONDS', 30))
    MAX_DELAY = int(os.getenv('MAX_DELAY_SECONDS', 120))
    FAUCET_RETRY_DELAY = 300  # 5 minutes
    TRANSACTION_TIMEOUT = 60
    
    # Activity Limits
    DAILY_TRANSACTIONS_PER_WALLET = int(os.getenv('DAILY_TRANSACTIONS_PER_WALLET', 10))
    MAX_SWAP_ATTEMPTS = 3
    MAX_FAUCET_ATTEMPTS = 5
    
    # Swap Settings
    SLIPPAGE_TOLERANCE = 0.03  # 3%
    MIN_SWAP_AMOUNT = 0.01
    MAX_SWAP_AMOUNT = 0.5
    
    # Staking Settings
    STAKE_PERCENTAGE = 0.6  # Stake 60% of balance
    MIN_STAKE_AMOUNT = 0.1
    VALIDATOR_ROTATION_DAYS = 14
    
    # Bridge Settings
    MIN_BRIDGE_AMOUNT = 0.1
    MAX_BRIDGE_AMOUNT = 0.3
    BRIDGE_COOLDOWN_HOURS = 6
    
    # Proxy Settings
    USE_PROXIES = True
    PROXY_ROTATION_ENABLED = True
    PROXY_TIMEOUT = 30
    
    # Captcha Settings
    TWOCAPTCHA_API_KEY = os.getenv('TWOCAPTCHA_API_KEY', '')
    ANTICAPTCHA_API_KEY = os.getenv('ANTICAPTCHA_API_KEY', '')
    CAPTCHA_TIMEOUT = 120
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/bot.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/bot.log')
    LOG_ROTATION = '100 MB'
    LOG_RETENTION = '30 days'
    
    # Anti-Detection: Basic
    RANDOMIZE_USER_AGENT = True
    HUMAN_LIKE_DELAYS = True
    BEHAVIOR_PATTERNS = {
        'early_bird': {'start_hour': 6, 'end_hour': 10},
        'day_trader': {'start_hour': 10, 'end_hour': 18},
        'night_owl': {'start_hour': 20, 'end_hour': 2}
    }
    
    # Anti-Detection: IP Management
    IP_SHARD_SIZE = int(os.getenv('IP_SHARD_SIZE', 10))
    IP_STICKY_HOURS = float(os.getenv('IP_STICKY_HOURS', 24.0))
    FAUCET_IP_STICKY_HOURS = float(os.getenv('FAUCET_IP_STICKY_HOURS', 24.0))
    RPC_IP_STICKY_HOURS = float(os.getenv('RPC_IP_STICKY_HOURS', 12.0))
    IP_ROTATION_JITTER_PCT = float(os.getenv('IP_ROTATION_JITTER_PCT', 0.2))
    
    # Anti-Detection: User-Agent Rotation
    UA_POOL_PATH = os.getenv('UA_POOL_PATH', '')
    UA_LIST = os.getenv('UA_LIST', '')
    UA_SESSION_DURATION_HOURS = float(os.getenv('UA_SESSION_DURATION_HOURS', 12.0))
    
    # Anti-Detection: Scheduling Entropy
    OFF_DAYS = os.getenv('OFF_DAYS', '')
    NIGHT_LULL_WINDOWS = os.getenv('NIGHT_LULL_WINDOWS', '0-6,22-24')
    DAYPART_WINDOWS = os.getenv('DAYPART_WINDOWS', 'morning:6-12,afternoon:12-18,evening:18-22')
    WEEKEND_ACTIVITY_REDUCTION = float(os.getenv('WEEKEND_ACTIVITY_REDUCTION', 0.3))
    NIGHT_ACTIVITY_REDUCTION = float(os.getenv('NIGHT_ACTIVITY_REDUCTION', 0.5))
    
    # Anti-Detection: Faucet Behavior
    OVER_COOLDOWN_JITTER_MIN = float(os.getenv('OVER_COOLDOWN_JITTER_MIN', 0.1))
    OVER_COOLDOWN_JITTER_MAX = float(os.getenv('OVER_COOLDOWN_JITTER_MAX', 0.3))
    FAUCET_SKIP_PROB = float(os.getenv('FAUCET_SKIP_PROB', 0.05))
    ACTION_SKIP_PROB = float(os.getenv('ACTION_SKIP_PROB', 0.1))
    
    # Anti-Detection: Auto-Throttle
    AUTO_THROTTLE_ERROR_THRESHOLD = float(os.getenv('AUTO_THROTTLE_ERROR_THRESHOLD', 0.3))
    AUTO_THROTTLE_ERROR_WINDOW = int(os.getenv('AUTO_THROTTLE_ERROR_WINDOW', 300))
    AUTO_THROTTLE_MIN_SAMPLES = int(os.getenv('AUTO_THROTTLE_MIN_SAMPLES', 10))
    AUTO_THROTTLE_PAUSE_DURATION = int(os.getenv('AUTO_THROTTLE_PAUSE_DURATION', 600))
    AUTO_THROTTLE_BACKOFF_MULTIPLIER = float(os.getenv('AUTO_THROTTLE_BACKOFF_MULTIPLIER', 2.0))
    AUTO_THROTTLE_MAX_PAUSE = int(os.getenv('AUTO_THROTTLE_MAX_PAUSE', 3600))
    
    # Transaction Gas Settings
    GAS_PRICE_MULTIPLIER = 1.1
    MAX_PRIORITY_FEE = 0.0001  # SOL
    
    # Error Handling
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2
    
    @classmethod
    def get_rpc_url(cls, chain='solana'):
        """Get appropriate RPC URL based on chain and mode"""
        if chain == 'solana':
            return cls.SOLANA_RPC[cls.SOLANA_NETWORK]
        elif chain == 'ethereum':
            return cls.ETH_RPC[cls.ETH_NETWORK]
        return None
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.TWOCAPTCHA_API_KEY and not cls.ANTICAPTCHA_API_KEY:
            errors.append('At least one captcha service API key required')
        
        if cls.MIN_DELAY >= cls.MAX_DELAY:
            errors.append('MIN_DELAY must be less than MAX_DELAY')
        
        if cls.DAILY_TRANSACTIONS_PER_WALLET < 1:
            errors.append('DAILY_TRANSACTIONS_PER_WALLET must be at least 1')
        
        return errors if errors else None
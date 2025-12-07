"""
Protocol integrations for blockchain actions.

This package provides real implementations for interacting with various
DeFi protocols including DEXes, staking contracts, and bridges.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BYNNΛI - AirdropFarm
Sophisticated multi-chain airdrop farming automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: BYNNΛI
Project: AirdropFarm
License: MIT
Repository: https://github.com/BYNNAI/airdrop-farming-bot
"""

from .uniswap import UniswapIntegration
from .staking import StakingIntegration
from .bridges import BridgeIntegration
from .jupiter import JupiterIntegration
from .solana_stake import SolanaStakeIntegration

__all__ = [
    'UniswapIntegration',
    'StakingIntegration',
    'BridgeIntegration',
    'JupiterIntegration',
    'SolanaStakeIntegration',
]

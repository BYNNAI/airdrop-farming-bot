"""
Protocol-specific blockchain integrations.

This package contains integrations with DeFi protocols for staking, swapping,
and bridging on various blockchain networks.

Author: BYNNΛI
License: MIT
"""

from .uniswap import UniswapIntegration
from .lido import LidoStakingIntegration
from .bridges import BridgeIntegration
from .jupiter import JupiterIntegration

__all__ = [
    'UniswapIntegration',
    'LidoStakingIntegration',
    'BridgeIntegration',
    'JupiterIntegration',
]

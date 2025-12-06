"""Tests for protocol integrations."""

import os
import sys
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from solana.rpc.async_api import AsyncClient

from modules.protocols.uniswap import UniswapIntegration
from modules.protocols.lido import LidoStakingIntegration
from modules.protocols.bridges import BridgeIntegration
from modules.protocols.jupiter import JupiterIntegration


def test_uniswap_initialization():
    """Test Uniswap integration initialization."""
    print("\nTesting Uniswap initialization...")
    
    # Create a mock Web3 instance
    web3 = Mock(spec=Web3)
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.to_checksum_address = Web3.to_checksum_address
    
    # Initialize Uniswap for Sepolia
    uniswap = UniswapIntegration(web3, 'ethereum_sepolia')
    
    assert uniswap.chain == 'ethereum_sepolia'
    assert uniswap.router_address is not None
    assert 'WETH' in uniswap.tokens
    
    print("✓ Uniswap initialization passed")


def test_uniswap_token_address_lookup():
    """Test token address lookup."""
    print("\nTesting token address lookup...")
    
    web3 = Mock(spec=Web3)
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.to_checksum_address = Web3.to_checksum_address
    
    uniswap = UniswapIntegration(web3, 'ethereum_sepolia')
    
    # Test native ETH
    eth_addr = uniswap.get_token_address('ETH')
    assert eth_addr == '0x0000000000000000000000000000000000000000'
    
    # Test WETH lookup
    weth_addr = uniswap.get_token_address('WETH')
    assert weth_addr.startswith('0x')
    
    # Test direct address passthrough
    test_addr = '0x1234567890123456789012345678901234567890'
    result = uniswap.get_token_address(test_addr)
    assert result == test_addr
    
    print("✓ Token address lookup passed")


def test_lido_initialization():
    """Test Lido integration initialization."""
    print("\nTesting Lido initialization...")
    
    web3 = Mock(spec=Web3)
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.to_checksum_address = Web3.to_checksum_address
    
    # Initialize Lido for Goerli
    lido = LidoStakingIntegration(web3, 'ethereum_goerli')
    
    assert lido.chain == 'ethereum_goerli'
    assert lido.lido_address is not None
    
    print("✓ Lido initialization passed")


def test_bridge_initialization():
    """Test bridge integration initialization."""
    print("\nTesting bridge initialization...")
    
    web3 = Mock(spec=Web3)
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.to_checksum_address = Web3.to_checksum_address
    web3.codec = Mock()
    
    # Initialize bridge for Sepolia (has LayerZero)
    bridge = BridgeIntegration(web3, 'ethereum_sepolia')
    
    assert bridge.chain == 'ethereum_sepolia'
    assert bridge.layerzero_endpoint is not None
    
    print("✓ Bridge initialization passed")


async def test_jupiter_initialization():
    """Test Jupiter integration initialization."""
    print("\nTesting Jupiter initialization...")
    
    # Create mock Solana client
    client = Mock(spec=AsyncClient)
    
    jupiter = JupiterIntegration(client)
    
    assert jupiter.rpc_client is not None
    
    # Test token mint lookup
    sol_mint = jupiter.get_token_mint('SOL')
    assert sol_mint == 'So11111111111111111111111111111111111111112'
    
    # Close session
    await jupiter.close()
    
    print("✓ Jupiter initialization passed")


def test_bridge_protocol_selection():
    """Test bridge protocol auto-selection."""
    print("\nTesting bridge protocol selection...")
    
    web3 = Mock(spec=Web3)
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.to_checksum_address = Web3.to_checksum_address
    web3.codec = Mock()
    
    # Test Arbitrum (has native L2 bridge)
    bridge_arb = BridgeIntegration(web3, 'arbitrum_sepolia')
    assert bridge_arb.l2_bridge_address is not None
    
    # Test Base (has both LayerZero and native bridge)
    bridge_base = BridgeIntegration(web3, 'base_sepolia')
    assert bridge_base.layerzero_endpoint is not None
    assert bridge_base.l2_bridge_address is not None
    
    print("✓ Bridge protocol selection passed")


def run_all_tests():
    """Run all protocol tests."""
    print("=" * 60)
    print("Running Protocol Integration Tests")
    print("=" * 60)
    
    try:
        test_uniswap_initialization()
        test_uniswap_token_address_lookup()
        test_lido_initialization()
        test_bridge_initialization()
        test_bridge_protocol_selection()
        
        # Run async tests
        asyncio.run(test_jupiter_initialization())
        
        print("\n" + "=" * 60)
        print("✓ All protocol tests passed!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

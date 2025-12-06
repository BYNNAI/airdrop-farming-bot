"""Tests for blockchain protocol integrations."""

import os
import sys
import asyncio
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from modules.protocols.uniswap import UniswapIntegration
from modules.protocols.staking import StakingIntegration
from modules.protocols.bridges import BridgeIntegration


def test_uniswap_initialization():
    """Test Uniswap integration initialization."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=Mock())
    
    router_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    uniswap = UniswapIntegration(mock_web3, router_address, "ethereum_sepolia")
    
    assert uniswap.web3 == mock_web3
    assert uniswap.chain == "ethereum_sepolia"
    assert uniswap.router_address == Web3.to_checksum_address(router_address)
    assert uniswap.slippage_tolerance == 0.03  # Default


def test_staking_initialization():
    """Test staking integration initialization."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=Mock())
    
    staking_address = "0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F"
    staking = StakingIntegration(mock_web3, staking_address, "ethereum_goerli")
    
    assert staking.web3 == mock_web3
    assert staking.chain == "ethereum_goerli"
    assert staking.staking_address == Web3.to_checksum_address(staking_address)


def test_bridge_initialization():
    """Test bridge integration initialization."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=Mock())
    
    bridge_address = "0x1234567890123456789012345678901234567890"
    bridge = BridgeIntegration(mock_web3, bridge_address, "ethereum_sepolia", "native")
    
    assert bridge.web3 == mock_web3
    assert bridge.chain == "ethereum_sepolia"
    assert bridge.bridge_type == "native"
    assert bridge.bridge_address == Web3.to_checksum_address(bridge_address)


async def test_uniswap_approve_token():
    """Test token approval for Uniswap."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.to_checksum_address = Web3.to_checksum_address
    mock_web3.to_wei = Web3.to_wei
    mock_web3.from_wei = Web3.from_wei
    
    # Mock token contract
    mock_token_contract = Mock()
    mock_token_contract.functions = Mock()
    mock_token_contract.functions.allowance = Mock(return_value=Mock(call=Mock(return_value=0)))
    mock_token_contract.functions.approve = Mock(return_value=Mock(
        build_transaction=Mock(return_value={
            'from': '0x' + '11' * 20,
            'nonce': 0,
            'gas': 100000,
            'gasPrice': 1000000000
        })
    ))
    
    # Mock eth methods
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=mock_token_contract)
    mock_web3.eth.get_transaction_count = Mock(return_value=0)
    mock_web3.eth.gas_price = 1000000000
    
    # Mock account signing
    mock_signed_tx = Mock()
    mock_signed_tx.raw_transaction = b'signed_tx'
    mock_web3.eth.account = Mock()
    mock_web3.eth.account.sign_transaction = Mock(return_value=mock_signed_tx)
    mock_web3.eth.send_raw_transaction = Mock(return_value=b'tx_hash')
    mock_web3.eth.wait_for_transaction_receipt = Mock(return_value={
        'transactionHash': Mock(hex=Mock(return_value='0xabc123')),
        'status': 1
    })
    
    router_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    uniswap = UniswapIntegration(mock_web3, router_address, "ethereum_sepolia")
    
    token_address = "0x" + "22" * 20
    wallet_address = "0x" + "11" * 20
    private_key = "0x" + "33" * 32
    amount = 1000000000000000000
    
    tx_hash = await uniswap.approve_token(token_address, wallet_address, private_key, amount)
    
    assert tx_hash == '0xabc123'
    mock_web3.eth.send_raw_transaction.assert_called_once()


async def test_staking_get_staked_balance():
    """Test getting staked balance."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.to_checksum_address = Web3.to_checksum_address
    
    # Mock contract
    mock_contract = Mock()
    mock_contract.functions = Mock()
    mock_contract.functions.balanceOf = Mock(return_value=Mock(call=Mock(return_value=1000000000000000000)))
    
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=mock_contract)
    
    staking_address = "0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F"
    staking = StakingIntegration(mock_web3, staking_address, "ethereum_goerli")
    
    wallet_address = "0x" + "11" * 20
    balance = await staking.get_staked_balance(wallet_address)
    
    assert balance == 1000000000000000000
    mock_contract.functions.balanceOf.assert_called_once()


def test_token_contract_creation():
    """Test ERC20 token contract creation."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.to_checksum_address = Web3.to_checksum_address
    mock_web3.eth = Mock()
    mock_web3.eth.contract = Mock(return_value=Mock())
    
    router_address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    uniswap = UniswapIntegration(mock_web3, router_address, "ethereum_sepolia")
    
    token_address = "0x" + "22" * 20
    contract = uniswap.get_token_contract(token_address)
    
    assert contract is not None
    mock_web3.eth.contract.assert_called()


def run_all_tests():
    """Run all protocol tests."""
    print("=" * 60)
    print("Running Protocol Integration Tests")
    print("=" * 60)
    
    try:
        test_uniswap_initialization()
        print("✓ Uniswap initialization test passed")
        
        test_staking_initialization()
        print("✓ Staking initialization test passed")
        
        test_bridge_initialization()
        print("✓ Bridge initialization test passed")
        
        test_token_contract_creation()
        print("✓ Token contract creation test passed")
        
        # Run async tests
        asyncio.run(test_uniswap_approve_token())
        print("✓ Uniswap approve token test passed")
        
        asyncio.run(test_staking_get_staked_balance())
        print("✓ Staking balance check test passed")
        
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

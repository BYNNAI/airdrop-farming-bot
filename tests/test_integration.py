"""Integration tests for airdrop farming system."""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, get_db_session, Wallet
from utils.logging_config import configure_logging
from modules.wallet_manager import WalletManager
from modules.faucet_automation import FaucetOrchestrator, FaucetConfig
from modules.action_pipeline import ActionPipeline
from modules.captcha_broker import CaptchaBroker


def test_database_initialization():
    """Test database initialization."""
    print("Testing database initialization...")
    
    # Use in-memory database for testing
    init_db("sqlite:///:memory:")
    
    with get_db_session() as session:
        wallet_count = session.query(Wallet).count()
        assert wallet_count == 0, "Fresh database should have no wallets"
    
    print("✓ Database initialization passed")


def test_wallet_generation():
    """Test HD wallet generation."""
    print("\nTesting wallet generation...")
    
    # Initialize database
    init_db("sqlite:///:memory:")
    
    # Create wallet manager with test seed
    test_seed = "test test test test test test test test test test test junk"
    wallet_manager = WalletManager(
        seed_mnemonic=test_seed,
        encryption_key="test_encryption_key_32chars_min"
    )
    
    # Generate wallets
    generated = wallet_manager.generate_wallets(
        count=10,
        chains=['evm'],
        shard_size=5
    )
    
    assert 'evm' in generated, "Should have generated EVM wallets"
    assert len(generated['evm']) == 10, "Should have generated 10 wallets"
    
    # Verify in database
    wallets = wallet_manager.get_wallets(chain='evm')
    assert len(wallets) == 10, "Should have 10 wallets in database"
    
    # Verify sharding
    shard_0 = wallet_manager.get_wallets(chain='evm', shard_id=0)
    shard_1 = wallet_manager.get_wallets(chain='evm', shard_id=1)
    assert len(shard_0) == 5, "Shard 0 should have 5 wallets"
    assert len(shard_1) == 5, "Shard 1 should have 5 wallets"
    
    print("✓ Wallet generation passed")


def test_faucet_config_loading():
    """Test faucet configuration loading."""
    print("\nTesting faucet configuration...")
    
    config = FaucetConfig()
    
    # Verify chains loaded
    chains = config.get_all_chains()
    assert len(chains) > 0, "Should have loaded chains"
    
    # Verify chains configuration structure (including disabled faucets)
    import yaml
    with open(config.config_path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Check that Ethereum Sepolia has faucets configured (even if disabled)
    eth_all_faucets = raw_config['chains']['ethereum_sepolia']['faucets']
    assert len(eth_all_faucets) > 0, "Should have Ethereum Sepolia faucets configured"
    
    # Check that Optimism Sepolia was added
    assert 'optimism_sepolia' in raw_config['chains'], "Should have Optimism Sepolia chain"
    opt_faucets = raw_config['chains']['optimism_sepolia']['faucets']
    assert len(opt_faucets) > 0, "Should have Optimism Sepolia faucets configured"
    
    # Get only enabled faucets (may be 0 if all require web interaction)
    eth_enabled = config.get_chain_faucets('ethereum_sepolia')
    
    # Verify priority sorting for enabled faucets (if any)
    if len(eth_enabled) > 0:
        priorities = [f.get('priority', 999) for f in eth_enabled]
        assert priorities == sorted(priorities), "Faucets should be sorted by priority"
    
    # Verify Solana CLI faucet is enabled (should work via automation)
    solana_enabled = config.get_chain_faucets('solana_devnet')
    assert len(solana_enabled) > 0, "Solana devnet should have at least one enabled faucet (CLI)"
    
    print(f"✓ Faucet configuration passed ({len(chains)} chains, {len(eth_all_faucets)} ETH faucets configured, {len(eth_enabled)} enabled)")


def test_captcha_broker():
    """Test captcha broker initialization."""
    print("\nTesting captcha broker...")
    
    # Test with manual solver (no API key)
    broker = CaptchaBroker(provider='manual')
    assert not broker.check_availability(), "Manual solver should not be auto-available"
    
    print("✓ Captcha broker passed")


async def test_action_pipeline():
    """Test action pipeline initialization."""
    print("\nTesting action pipeline...")
    
    # Initialize database with test wallets
    init_db("sqlite:///:memory:")
    
    test_seed = "test test test test test test test test test test test junk"
    wallet_manager = WalletManager(
        seed_mnemonic=test_seed,
        encryption_key="test_encryption_key_32chars_min"
    )
    
    # Generate test wallet
    wallet_manager.generate_wallets(count=1, chains=['evm'], shard_size=1)
    wallets = wallet_manager.get_wallets(chain='evm')
    
    # Initialize pipeline
    pipeline = ActionPipeline()
    
    # Note: Adapters may not be initialized if RPC URLs aren't set in environment
    # This is expected behavior - adapters are only created for chains with RPC URLs
    adapter_count = len(pipeline.adapters)
    print(f"✓ Action pipeline passed ({adapter_count} adapters initialized, may be 0 if no RPC URLs set)")


def test_logging_configuration():
    """Test logging configuration."""
    print("\nTesting logging configuration...")
    
    configure_logging(log_level='INFO', log_format='json')
    
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
    
    # Test structured logging
    logger.info(
        "test_event",
        test_key="test_value",
        timestamp=datetime.utcnow().isoformat()
    )
    
    print("✓ Logging configuration passed")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Airdrop Farming Integration Tests")
    print("=" * 60)
    
    try:
        test_database_initialization()
        test_wallet_generation()
        test_faucet_config_loading()
        test_captcha_broker()
        test_logging_configuration()
        
        # Run async test
        asyncio.run(test_action_pipeline())
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
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

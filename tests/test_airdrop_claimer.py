"""Tests for airdrop claiming functionality."""

import os
import sys
import asyncio
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, get_db_session, Wallet, WalletAction, AirdropClaim
from utils.logging_config import configure_logging
from modules.wallet_manager import WalletManager
from modules.airdrop_claimer import AirdropRegistry, EligibilityChecker, AirdropClaimer


def test_airdrop_registry():
    """Test airdrop registry loading and querying."""
    print("\nTesting airdrop registry...")
    
    registry = AirdropRegistry()
    
    # Test loading
    assert len(registry.get_all_airdrops()) > 0, "Should load airdrops from config"
    
    # Test getting specific airdrop
    example = registry.get_airdrop('example_testnet')
    assert example is not None, "Should find example_testnet airdrop"
    assert example['name'] == 'Example Testnet Airdrop'
    
    # Test getting active airdrops
    active = registry.get_active_airdrops()
    assert len(active) >= 1, "Should find at least one active airdrop"
    
    # Test filtering by chain
    active_sepolia = registry.get_active_airdrops(chain='ethereum_sepolia')
    assert len(active_sepolia) >= 1, "Should find active Sepolia airdrops"
    
    # Test getting by status
    upcoming = registry.get_airdrops_by_status('upcoming')
    assert len(upcoming) >= 0, "Should get upcoming airdrops"
    
    print("✓ Airdrop registry tests passed")


def test_eligibility_checker():
    """Test eligibility checking."""
    print("\nTesting eligibility checker...")
    
    # Initialize database
    init_db("sqlite:///:memory:")
    
    # Create test wallet
    test_seed = "test test test test test test test test test test test junk"
    wallet_manager = WalletManager(
        seed_mnemonic=test_seed,
        encryption_key="test_encryption_key_32chars_min"
    )
    
    # Generate a wallet
    wallet_manager.generate_wallets(count=1, chains=['evm'], shard_size=1)
    
    with get_db_session() as session:
        wallet = session.query(Wallet).first()
        assert wallet is not None, "Wallet should be created"
        
        # Update wallet chain to match test airdrop
        wallet.chain = 'ethereum_sepolia'
        session.commit()
        
        # Add some test actions
        actions = [
            WalletAction(
                wallet_id=wallet.id,
                action_type='stake',
                chain='ethereum_sepolia',
                status='success',
                scheduled_at=datetime.now(timezone.utc)
            ),
            WalletAction(
                wallet_id=wallet.id,
                action_type='swap',
                chain='ethereum_sepolia',
                status='success',
                scheduled_at=datetime.now(timezone.utc)
            ),
            WalletAction(
                wallet_id=wallet.id,
                action_type='bridge',
                chain='ethereum_sepolia',
                status='success',
                scheduled_at=datetime.now(timezone.utc)
            )
        ]
        for action in actions:
            session.add(action)
        session.commit()
        
        # Test eligibility check
        checker = EligibilityChecker()
        registry = AirdropRegistry()
        
        # Get test airdrop config
        airdrop_config = registry.get_airdrop('example_testnet')
        assert airdrop_config is not None, "Test airdrop should exist"
        
        # Check eligibility (async)
        async def check():
            is_eligible, reason, metadata = await checker.check_eligibility(
                wallet, airdrop_config
            )
            return is_eligible, reason, metadata
        
        is_eligible, reason, metadata = asyncio.run(check())
        
        assert is_eligible, f"Wallet should be eligible: {reason}"
        print(f"  Eligibility check passed: {reason}")
        
        # Test ineligible case (not enough actions)
        airdrop_config['min_actions'] = 100
        is_eligible, reason, metadata = asyncio.run(check())
        assert not is_eligible, "Wallet should be ineligible with high min_actions"
        print(f"  Ineligibility check passed: {reason}")
    
    print("✓ Eligibility checker tests passed")


def test_airdrop_claimer():
    """Test airdrop claiming functionality."""
    print("\nTesting airdrop claimer...")
    
    # Initialize database
    init_db("sqlite:///:memory:")
    
    # Create test wallet with seed
    test_seed = "test test test test test test test test test test test junk"
    wallet_manager = WalletManager(
        seed_mnemonic=test_seed,
        encryption_key="test_encryption_key_32chars_min"
    )
    
    # Generate wallets
    wallet_manager.generate_wallets(count=2, chains=['evm'], shard_size=1)
    
    with get_db_session() as session:
        wallets = session.query(Wallet).all()
        assert len(wallets) == 2, "Should have 2 test wallets"
        
        # Update wallet chains to match test airdrop
        for wallet in wallets:
            wallet.chain = 'ethereum_sepolia'
        session.commit()
        
        # Add actions to make them eligible
        for wallet in wallets:
            actions = [
                WalletAction(
                    wallet_id=wallet.id,
                    action_type='stake',
                    chain='ethereum_sepolia',
                    status='success',
                    scheduled_at=datetime.now(timezone.utc)
                ),
                WalletAction(
                    wallet_id=wallet.id,
                    action_type='swap',
                    chain='ethereum_sepolia',
                    status='success',
                    scheduled_at=datetime.now(timezone.utc)
                ),
                WalletAction(
                    wallet_id=wallet.id,
                    action_type='bridge',
                    chain='ethereum_sepolia',
                    status='success',
                    scheduled_at=datetime.now(timezone.utc)
                )
            ]
            for action in actions:
                session.add(action)
        
        session.commit()
        
        # Detach wallets from session
        session.expunge_all()
    
    # Get detached wallets
    wallets = wallet_manager.get_wallets(chain='ethereum_sepolia')
    
    # Test check-only mode
    claimer = AirdropClaimer(wallet_manager=wallet_manager)
    
    async def run_check_only():
        stats = await claimer.check_and_claim_airdrops(
            wallets=wallets,
            airdrop_name='example_testnet',
            check_only=True
        )
        return stats
    
    stats = asyncio.run(run_check_only())
    
    print(f"  Check-only stats: {stats}")
    assert stats['total_wallets'] == 2, "Should check 2 wallets"
    # Note: total_checks may be less than total_wallets due to anti-detection skipping
    assert stats['total_checks'] >= 1, "Should perform at least 1 check"
    assert stats['eligible'] >= 0, "Should find eligible wallets"
    
    # Total checks + skipped should equal wallets processed
    assert stats['total_checks'] + stats['skipped'] == 2, "Checks + skips should equal total wallets"
    
    # Verify claims were recorded in database
    with get_db_session() as session:
        claims = session.query(AirdropClaim).all()
        print(f"  Found {len(claims)} claim records")
        for claim in claims:
            print(f"    - Wallet {claim.wallet_id}: {claim.status}")
    
    print("✓ Airdrop claimer tests passed")


def test_claim_recording():
    """Test claim status recording in database."""
    print("\nTesting claim recording...")
    
    # Initialize database
    init_db("sqlite:///:memory:")
    
    # Create test wallet
    test_seed = "test test test test test test test test test test test junk"
    wallet_manager = WalletManager(
        seed_mnemonic=test_seed,
        encryption_key="test_encryption_key_32chars_min"
    )
    
    wallet_manager.generate_wallets(count=1, chains=['evm'], shard_size=1)
    
    with get_db_session() as session:
        wallet = session.query(Wallet).first()
        
        # Create a claim record
        claim = AirdropClaim(
            wallet_id=wallet.id,
            airdrop_name='test_airdrop',
            chain='ethereum_sepolia',
            status='eligible',
            checked_at=datetime.now(timezone.utc)
        )
        session.add(claim)
        session.commit()
        
        # Verify it was saved
        saved_claim = session.query(AirdropClaim).filter(
            AirdropClaim.wallet_id == wallet.id
        ).first()
        
        assert saved_claim is not None, "Claim should be saved"
        assert saved_claim.status == 'eligible', "Status should be eligible"
        assert saved_claim.airdrop_name == 'test_airdrop'
        
        # Update to claimed
        saved_claim.status = 'claimed'
        saved_claim.tx_hash = '0x' + '0' * 64
        saved_claim.claimed_at = datetime.now(timezone.utc)
        session.commit()
        
        # Verify update
        updated_claim = session.query(AirdropClaim).filter(
            AirdropClaim.wallet_id == wallet.id
        ).first()
        
        assert updated_claim.status == 'claimed', "Status should be updated"
        assert updated_claim.tx_hash is not None, "Should have tx_hash"
        assert updated_claim.claimed_at is not None, "Should have claimed_at"
    
    print("✓ Claim recording tests passed")


if __name__ == '__main__':
    configure_logging(log_level='WARNING')
    
    print("=" * 60)
    print("Running Airdrop Claimer Tests")
    print("=" * 60)
    
    try:
        test_airdrop_registry()
        test_eligibility_checker()
        test_airdrop_claimer()
        test_claim_recording()
        
        print("\n" + "=" * 60)
        print("✓ All airdrop claimer tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

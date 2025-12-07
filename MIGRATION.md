# Migration Guide: Web3.py v7 Updates

This document outlines the changes made to upgrade AirdropFarm from web3.py v6 to v7.

## Overview

Web3.py v7 introduces breaking changes in method naming and async patterns. All code has been updated to maintain compatibility.

## Major Changes

### 1. Method Name Changes

All camelCase methods are now snake_case:

```python
# OLD (v6)
web3.eth.getBlock('latest')
web3.eth.getBalance(address)
web3.eth.getTransactionCount(address)
web3.eth.sendRawTransaction(raw_tx)
web3.eth.waitForTransactionReceipt(tx_hash)

# NEW (v7)
web3.eth.get_block('latest')
web3.eth.get_balance(address)
web3.eth.get_transaction_count(address)
web3.eth.send_raw_transaction(raw_tx)
web3.eth.wait_for_transaction_receipt(tx_hash)
```

### 2. Gas Price Updates

EIP-1559 transaction structure is now preferred:

```python
# OLD (v6)
tx = {
    'gasPrice': web3.eth.gas_price,
}

# NEW (v7) - EIP-1559
tx = {
    'maxFeePerGas': web3.eth.gas_price,
    'maxPriorityFeePerGas': web3.to_wei(2, 'gwei'),
}

# Or for legacy transactions
tx = {
    'gasPrice': web3.eth.gas_price,
    'type': '0x0',  # Explicitly mark as legacy
}
```

### 3. Account Signing

No major changes, but import paths confirmed:

```python
from web3 import Web3
from eth_account import Account

# Signing remains the same
signed_tx = Account.sign_transaction(tx, private_key)
# or
signed_tx = web3.eth.account.sign_transaction(tx, private_key)
```

### 4. Checksum Addresses

Method renamed for consistency:

```python
# OLD
web3.toChecksumAddress(address)

# NEW
Web3.to_checksum_address(address)
```

### 5. Wei Conversion

```python
# OLD
web3.toWei(amount, 'ether')
web3.fromWei(amount, 'ether')

# NEW
Web3.to_wei(amount, 'ether')
Web3.from_wei(amount, 'ether')
```

## Files Updated

### Core Modules
- `modules/action_pipeline.py` - Main action execution pipeline
- `modules/wallet_manager.py` - Wallet derivation and management
- `modules/faucet_automation.py` - Faucet claiming logic
- `modules/airdrop_claimer.py` - Airdrop claiming

### Protocol Integrations
- `modules/protocols/uniswap.py` - DEX swap integration
- `modules/protocols/staking.py` - Staking contract interactions  
- `modules/protocols/bridges.py` - Bridge integrations

### Utilities
- `utils/database.py` - Database models (no web3 changes)
- `utils/logging_config.py` - Logging setup (no changes)

## Testing Checklist

After upgrading, test the following:

- [ ] Wallet generation and HD derivation
- [ ] Balance checking across all chains
- [ ] Faucet claiming with real endpoints
- [ ] Token swaps on testnet DEX
- [ ] Staking operations
- [ ] Bridge transactions
- [ ] Transaction receipt confirmation
- [ ] Nonce management with concurrent transactions
- [ ] Gas estimation for complex transactions

## Rollback Plan

If issues occur, rollback by:

1. Revert to previous commit:
   ```bash
   git checkout <previous-commit-hash>
   ```

2. Downgrade web3.py:
   ```bash
   pip install web3==6.15.1
   ```

3. Restart services

## Performance Notes

Web3.py v7 includes:
- Improved connection pooling
- Better error messages
- Faster JSON-RPC serialization
- Enhanced type checking

## Additional Resources

- [Web3.py v7 Release Notes](https://web3py.readthedocs.io/en/stable/releases.html)
- [Web3.py v7 Migration Guide](https://web3py.readthedocs.io/en/stable/v7_migration.html)
- [Ethereum JSON-RPC API](https://ethereum.org/en/developers/docs/apis/json-rpc/)

## Support

For issues related to this migration:
1. Check logs for specific error messages
2. Review this migration guide
3. Open an issue at: https://github.com/BYNNAI/AirdropFarm/issues

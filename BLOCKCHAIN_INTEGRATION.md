# Blockchain Integration Guide

This document describes the real blockchain integrations implemented in the airdrop farming bot.

## Overview

The bot now supports real on-chain transactions for:
- **Staking**: Native ETH/token staking via Lido and similar protocols
- **Swapping**: Token swaps via Uniswap V2/V3 on EVM chains and Jupiter on Solana
- **Bridging**: Cross-chain transfers via LayerZero and native L2 bridges
- **Balance Checking**: Real-time balance queries for native and ERC20/SPL tokens

## Architecture

### Protocol Integrations (`modules/protocols/`)

The bot uses a modular architecture with dedicated protocol integrations:

```
modules/protocols/
├── __init__.py
├── uniswap.py         # Uniswap V2/V3 integration for EVM swaps
├── staking.py         # EVM staking (Lido, etc.)
├── bridges.py         # Bridge protocols (LayerZero, native L2)
├── jupiter.py         # Jupiter aggregator for Solana swaps
└── solana_stake.py    # Solana native staking
```

### Action Adapters (`modules/action_pipeline.py`)

The `EVMActionAdapter` and `SolanaActionAdapter` classes provide a unified interface for blockchain interactions:

- Initialize Web3/Solana clients
- Load contract addresses from environment variables
- Execute stake/swap/bridge operations
- Query balances

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Uniswap V2 Router Addresses (Testnets)
UNISWAP_ROUTER_ETHEREUM_SEPOLIA=0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
UNISWAP_ROUTER_ETHEREUM_GOERLI=0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
UNISWAP_ROUTER_BNB_TESTNET=0xD99D1c33F9fC3444f8101754aBC46c52416550D1

# Staking Contract Addresses
STAKING_CONTRACT_ETHEREUM_GOERLI=0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F

# Bridge Contract Addresses
BRIDGE_CONTRACT_ETHEREUM_SEPOLIA=<bridge_address>
BRIDGE_TYPE_ETHEREUM_SEPOLIA=native  # or 'layerzero'

# LayerZero Chain IDs
LAYERZERO_CHAIN_ID_ETHEREUM_SEPOLIA=10161
LAYERZERO_CHAIN_ID_POLYGON_AMOY=10267
LAYERZERO_CHAIN_ID_ARBITRUM_SEPOLIA=10231

# WETH Addresses (for swaps)
WETH_ETHEREUM_SEPOLIA=0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14
WETH_ETHEREUM_GOERLI=0xB4FBF271143F4FBf7B91A5ded31805e42b2208d6

# Slippage tolerance (0.03 = 3%)
SLIPPAGE_TOLERANCE=0.03
```

## Usage Examples

### Staking

```python
from modules.action_pipeline import ActionPipeline

pipeline = ActionPipeline()

# Execute staking action
await pipeline.execute_action(
    wallet=my_wallet,
    action_type='stake',
    chain='ethereum_goerli',
    params={
        'amount': 0.1,  # Amount in ETH
        'validator': None  # Optional validator address
    }
)
```

### Swapping

```python
# Swap ETH for token
await pipeline.execute_action(
    wallet=my_wallet,
    action_type='swap',
    chain='ethereum_sepolia',
    params={
        'from_token': 'ETH',
        'to_token': '0x...token_address...',
        'amount': 0.05
    }
)

# Swap token for token
await pipeline.execute_action(
    wallet=my_wallet,
    action_type='swap',
    chain='ethereum_sepolia',
    params={
        'from_token': '0x...token_a...',
        'to_token': '0x...token_b...',
        'amount': 10.0
    }
)
```

### Bridging

```python
# Bridge via native L2 bridge
await pipeline.execute_action(
    wallet=my_wallet,
    action_type='bridge',
    chain='ethereum_sepolia',
    params={
        'to_chain': 'arbitrum_sepolia',
        'amount': 0.1
    }
)

# Bridge via LayerZero (requires chain ID configuration)
await pipeline.execute_action(
    wallet=my_wallet,
    action_type='bridge',
    chain='ethereum_sepolia',
    params={
        'to_chain': 'polygon_amoy',
        'amount': 0.1,
        'dst_chain_id': 10267  # Optional, loaded from env if not provided
    }
)
```

## Supported Chains

### EVM Chains

- Ethereum Sepolia
- Ethereum Goerli
- Polygon Amoy
- Arbitrum Sepolia
- Base Sepolia
- BNB Testnet
- Avalanche Fuji
- Fantom Testnet

### Non-EVM Chains

- Solana Devnet
- Solana Testnet

## Transaction Flow

### EVM Transactions

1. **Stake**:
   - Check wallet balance
   - Build staking transaction
   - Estimate gas
   - Sign with private key
   - Send transaction
   - Wait for confirmation
   - Return transaction hash

2. **Swap**:
   - Approve token spending (if ERC20)
   - Get expected output amount
   - Calculate slippage protection
   - Build swap transaction
   - Sign and send
   - Wait for confirmation

3. **Bridge**:
   - Estimate bridge fees (LayerZero)
   - Build bridge transaction
   - Sign and send
   - Return source chain tx hash

### Solana Transactions

1. **Stake**:
   - Create stake account
   - Get validator list
   - Build stake instructions
   - Sign with keypair
   - Send transaction

2. **Swap** (via Jupiter):
   - Get swap quote from Jupiter API
   - Build swap transaction
   - Sign and send
   - Wait for confirmation

## Security Considerations

### Private Key Management

- Private keys are **never stored** on disk
- Keys are derived on-demand from encrypted seed phrase
- WalletManager handles secure key derivation
- Keys are only in memory during transaction signing

### Transaction Safety

- All transactions include gas estimation
- Slippage protection on swaps (default 3%)
- Balance checks before transactions
- Transaction simulation where possible
- Proper error handling and logging

### Testnet Enforcement

- `TESTNET_MODE=true` enforced in configuration
- Only testnet RPCs should be configured
- No mainnet transactions should occur

## Error Handling

The adapters handle various error scenarios:

- **Insufficient balance**: Returns error without attempting transaction
- **Missing configuration**: Falls back gracefully or returns descriptive error
- **Network errors**: Logged with full context
- **Failed transactions**: Status tracked in database
- **Gas estimation failures**: Transaction not sent

## Limitations

### Solana Staking

Due to `solders` version 0.21.0 limitations, Solana staking only creates stake accounts but does not initialize or delegate them. For full staking functionality:
- Upgrade to newer `solders` version with stake program support
- Or use `@solana/web3.js` with Node.js bridge

### Jupiter API

Jupiter only provides mainnet API. Devnet/testnet swaps will use mainnet pricing and routes. For true testnet DEX functionality, consider using Raydium or other testnet-compatible DEXes.

### Wormhole Bridging

Solana bridging via Wormhole is not yet implemented. This requires additional integration work with the Wormhole protocol.

## Testing

Run the protocol integration tests:

```bash
python tests/test_protocols.py
```

Run full integration tests:

```bash
python tests/test_integration.py
```

## Monitoring

All transactions are logged with structured logging:

```json
{
  "event": "swap_completed",
  "chain": "ethereum_sepolia",
  "wallet": "0x...",
  "from_token": "ETH",
  "to_token": "0x...",
  "amount_in": 0.1,
  "tx_hash": "0x...",
  "status": "success"
}
```

Transaction details are also stored in the database (`wallet_actions` table) for historical tracking and analysis.

## Troubleshooting

### "Staking not configured"

Add the staking contract address for your chain to `.env`:
```bash
STAKING_CONTRACT_<CHAIN>=<contract_address>
```

### "WETH address not configured"

Add the WETH address for your chain:
```bash
WETH_<CHAIN>=<weth_address>
```

### "LayerZero chain ID not configured"

Add the destination chain ID:
```bash
LAYERZERO_CHAIN_ID_<CHAIN>=<chain_id>
```

### Transaction failures

Check:
1. Sufficient balance for transaction + gas
2. Contract addresses are correct for the testnet
3. RPC endpoint is responding
4. Gas price is reasonable
5. Token approvals are successful

## Future Enhancements

- [ ] Support for more DEXes (SushiSwap, PancakeSwap V3)
- [ ] Additional bridge protocols (Wormhole, Stargate)
- [ ] Full Solana staking with delegation
- [ ] Raydium integration for Solana testnet swaps
- [ ] Transaction batching for gas optimization
- [ ] MEV protection on swaps
- [ ] Multi-hop routing for better swap rates

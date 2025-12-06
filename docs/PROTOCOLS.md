# Supported Protocols

This document describes the blockchain protocols integrated for real on-chain activity to maximize airdrop eligibility.

## Overview

The system supports three main types of on-chain actions:
- **Staking**: Lock tokens with validators or liquid staking protocols
- **Swapping**: Trade tokens on decentralized exchanges (DEXs)
- **Bridging**: Transfer assets across blockchain networks

## EVM Chain Integrations

### 🔄 Uniswap V2 (DEX Swaps)

**Supported Networks:**
- Ethereum Sepolia
- Ethereum Goerli
- Arbitrum Sepolia
- Base Sepolia
- Other EVM testnets

**Features:**
- Token-to-token swaps via Uniswap V2 Router
- Native ETH to token swaps
- Token to native ETH swaps
- Automatic ERC20 token approval
- Configurable slippage tolerance (default 3%)
- Gas estimation and optimization

**Usage:**
```python
await adapter.swap(
    wallet=wallet,
    from_token='ETH',
    to_token='USDC',
    amount=0.1,
    slippage_percent=3.0
)
```

**Testnet Tokens:**
- WETH (Wrapped ETH)
- USDC (USD Coin testnet)
- DAI (DAI testnet)

### 🏦 Lido (Liquid Staking)

**Supported Networks:**
- Ethereum Sepolia
- Ethereum Goerli
- Ethereum Holesky

**Features:**
- Liquid ETH staking (receive stETH)
- Maintain liquidity while earning rewards
- Referral support
- Balance tracking

**Usage:**
```python
await adapter.stake(
    wallet=wallet,
    amount=0.5,  # ETH amount
    validator=None  # Optional referral address
)
```

### 🌉 Cross-Chain Bridges

#### LayerZero

**Supported Networks:**
- Ethereum Sepolia ↔ Other chains
- Ethereum Goerli ↔ Other chains
- Arbitrum Sepolia ↔ Other chains
- Base Sepolia ↔ Other chains
- Polygon Amoy ↔ Other chains
- BNB Testnet ↔ Other chains

**Features:**
- Omnichain messaging and token transfers
- Automatic fee estimation
- Supports multiple destination chains
- Trustless cross-chain communication

**Usage:**
```python
await adapter.bridge(
    wallet=wallet,
    to_chain='arbitrum_sepolia',
    amount=0.1,
    bridge_type='layerzero'
)
```

#### Native L2 Bridges

**Supported Networks:**
- Arbitrum Sepolia (Ethereum ↔ Arbitrum)
- Base Sepolia (Ethereum ↔ Base)
- Optimism Sepolia (Ethereum ↔ Optimism)

**Features:**
- Native L2 bridge contracts
- Optimized for specific L2 networks
- Lower fees compared to third-party bridges
- Canonical bridging

**Usage:**
```python
await adapter.bridge(
    wallet=wallet,
    to_chain='base',
    amount=0.1,
    bridge_type='native_l2'
)
```

## Solana Integrations

### 🪐 Jupiter Aggregator (DEX Swaps)

**Network:** Solana Devnet/Testnet

**Features:**
- Optimal swap routing via Jupiter API
- Multi-hop swaps for best prices
- Automatic slippage calculation
- Support for SPL tokens
- Versioned transaction support

**Usage:**
```python
await adapter.swap(
    wallet=wallet,
    from_token='SOL',
    to_token='USDC',
    amount=0.5,
    slippage_percent=3.0
)
```

**Supported Tokens:**
- SOL (Native Solana)
- WSOL (Wrapped SOL)
- USDC (on devnet/testnet)

### 🏦 Solana Staking

**Status:** Partially implemented (placeholder)

**Note:** Full Solana native staking requires:
- Stake account creation
- Validator selection and delegation
- Epoch timing considerations

For production use, this should be implemented using Solana's stake program.

### 🌉 Solana Bridging

**Status:** Placeholder (requires Wormhole integration)

**Note:** Cross-chain bridging from Solana requires:
- Wormhole Portal Bridge integration
- Token wrapping/unwrapping
- Cross-chain message verification

## Gas Management

All transactions include:
- **Gas Estimation**: Automatic estimation before sending
- **Gas Buffer**: 20% buffer added to estimates
- **Gas Price**: Uses current network gas price
- **Transaction Timeout**: 120 seconds default

## Error Handling

Each integration includes:
- Pre-flight balance checks
- Transaction simulation (where supported)
- Graceful fallback to mock for unconfigured chains
- Detailed error logging
- Retry logic (via parent pipeline)

## Configuration

### Environment Variables

Protocol-specific contracts are configured via environment variables in `.env.example`:

```bash
# Uniswap Routers
UNISWAP_ROUTER_SEPOLIA=0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008
UNISWAP_ROUTER_GOERLI=0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D

# Lido Contracts
LIDO_CONTRACT_SEPOLIA=0x3e3FE7dBc6B4C189E7128855dD526361c49b40Af
LIDO_CONTRACT_GOERLI=0x1643E812aE58766192Cf7D2Cf9567dF2C37e9B7F

# LayerZero Endpoints
LAYERZERO_ENDPOINT_SEPOLIA=0xae92d5aD7583AD66E49A0c67BAd18F6ba52dDDc1

# L2 Bridges
L2_BRIDGE_ARBITRUM_SEPOLIA=0x902b3E5f8F19571859F4AB1003B960a5dF693aFF

# Jupiter API
JUPITER_API_BASE=https://quote-api.jup.ag/v6
```

### Action Pipeline Settings

```bash
ENABLE_STAKING=true
ENABLE_SWAPPING=true
ENABLE_BRIDGING=true
ACTION_COOLDOWN_HOURS=6
DAILY_ACTIONS_PER_WALLET=5
```

## Security Considerations

### ✅ Implemented
- **Testnet Only**: All contracts are testnet deployments
- **Private Key Security**: Keys derived on-demand, never stored
- **Transaction Signing**: Local signing before broadcast
- **Balance Checks**: Pre-flight validation
- **Gas Limits**: Maximum gas per transaction

### ⚠️ Important Notes
- Only use testnet funds
- Never use mainnet RPCs with this configuration
- Verify contract addresses before use
- Monitor transaction status

## Testing

Run protocol integration tests:

```bash
python tests/test_protocols.py
```

Run full integration tests:

```bash
python tests/test_integration.py
```

## Future Enhancements

### Planned
- Full Solana native staking implementation
- Wormhole bridge integration for Solana
- Additional DEX integrations (PancakeSwap, SushiSwap)
- Uniswap V3 concentrated liquidity support
- Token account creation for Solana SPL tokens

### Under Consideration
- Yield farming protocols (Aave, Compound testnets)
- NFT interactions
- DAO voting participation
- Protocol-specific tasks (e.g., Lens Protocol, Farcaster)

## Troubleshooting

### Common Issues

**"No Uniswap router configured for chain"**
- Ensure the chain is supported
- Check that testnet has a deployed Uniswap instance

**"Could not derive private key for wallet"**
- Verify wallet exists in database
- Check WalletManager configuration
- Ensure seed mnemonic is set

**"Gas estimation failed"**
- Check wallet has sufficient balance
- Verify RPC endpoint is responding
- Confirm contract addresses are correct

**"Transaction timeout"**
- Network congestion on testnet
- RPC endpoint may be slow
- Consider increasing timeout in code

## References

- [Uniswap V2 Documentation](https://docs.uniswap.org/contracts/v2/overview)
- [Lido Documentation](https://docs.lido.fi/)
- [LayerZero Documentation](https://layerzero.network/developers)
- [Jupiter Documentation](https://station.jup.ag/docs/apis/swap-api)
- [Solana Staking Documentation](https://docs.solana.com/staking)

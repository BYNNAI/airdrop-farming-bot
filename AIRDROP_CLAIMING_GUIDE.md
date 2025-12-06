# Airdrop Claiming Module Guide

## Overview

The airdrop claiming module automates the detection and claiming of airdrops for wallets that have performed eligibility actions (staking, bridging, swapping).

## Components

### 1. AirdropRegistry
Manages airdrop configurations loaded from `config/airdrops.yaml`.

**Features:**
- Load and parse airdrop configurations
- Filter by status (upcoming, claimable, ended)
- Filter by chain
- Track claim windows

### 2. EligibilityChecker
Verifies wallet eligibility for airdrops using multiple methods.

**Eligibility Methods:**
- **Merkle Proof**: Verify against on-chain merkle tree
- **API-based**: Query external eligibility API
- **Direct**: Check wallet actions against requirements

**Checks performed:**
- Minimum action count
- Required action types (stake, swap, bridge)
- Chain matching
- Method-specific verification

### 3. AirdropClaimer
Executes claim transactions with retry logic and anti-detection.

**Features:**
- Multiple claim methods (merkle, API, direct)
- Exponential backoff retry (up to 3 attempts)
- Human-like delays and behavior
- Transaction simulation before execution
- Comprehensive database tracking

## Configuration

### Airdrop Configuration (`config/airdrops.yaml`)

```yaml
airdrops:
  example_airdrop:
    name: "Example Protocol Airdrop"
    chain: "ethereum_sepolia"
    status: "claimable"  # upcoming, claimable, ended
    claim_start: "2025-01-01T00:00:00Z"
    claim_end: "2025-06-01T00:00:00Z"
    claim_contract: "0x..."
    claim_method: "merkle"  # merkle, api, direct
    eligibility_api: "https://api.example.com/eligibility"
    min_actions: 5  # minimum actions required
    required_actions:
      - stake
      - swap
      - bridge
    description: "Example testnet airdrop"
    enabled: true
    priority: 1
```

### Database Model

The `AirdropClaim` model tracks all claim attempts:

```python
class AirdropClaim:
    id: int
    wallet_id: int  # Foreign key to Wallet
    airdrop_name: str
    chain: str
    status: str  # eligible, claimed, failed, ineligible
    amount_claimed: str
    tx_hash: str
    checked_at: datetime
    claimed_at: datetime
    error_message: str
```

## CLI Commands

### List Airdrops

View all configured airdrops and their status:

```bash
python main.py list-airdrops
```

Output shows:
- Airdrop name
- Blockchain chain
- Status (claimable, upcoming, ended)
- Claim method
- Minimum required actions
- Enabled/disabled status

### Check Eligibility (Dry Run)

Check wallet eligibility without claiming:

```bash
# Check all wallets for all active airdrops
python main.py claim-airdrops --check-only

# Check specific airdrop
python main.py claim-airdrops --airdrop example_protocol --check-only

# Check specific shard
python main.py claim-airdrops --shard 0 --check-only

# Check specific chain
python main.py claim-airdrops --chain ethereum_sepolia --check-only
```

### Claim Airdrops

Execute actual claims for eligible wallets:

```bash
# Claim all active airdrops
python main.py claim-airdrops

# Claim specific airdrop
python main.py claim-airdrops --airdrop example_protocol

# Claim for specific shard
python main.py claim-airdrops --shard 0

# Claim with limit
python main.py claim-airdrops --limit 10
```

### View Statistics

View overall statistics including airdrop claims:

```bash
python main.py stats
```

## Usage Examples

### Example 1: Check Eligibility Before Claiming

```bash
# First, check which wallets are eligible
python main.py claim-airdrops --check-only

# Review the results, then claim for eligible wallets
python main.py claim-airdrops
```

### Example 2: Claim Specific Airdrop by Shard

```bash
# Process shard 0
python main.py claim-airdrops --airdrop sepolia_rewards --shard 0

# Wait, then process shard 1
python main.py claim-airdrops --airdrop sepolia_rewards --shard 1
```

### Example 3: Chain-Specific Claims

```bash
# Claim all Ethereum Sepolia airdrops
python main.py claim-airdrops --chain ethereum_sepolia

# Claim all Solana airdrops
python main.py claim-airdrops --chain solana
```

## Programmatic Usage

### Check Eligibility

```python
from modules.airdrop_claimer import AirdropRegistry, EligibilityChecker
from modules.wallet_manager import WalletManager

# Load registry
registry = AirdropRegistry()
active_airdrops = registry.get_active_airdrops()

# Get wallets
wallet_manager = WalletManager()
wallets = wallet_manager.get_wallets(chain='ethereum_sepolia')

# Check eligibility
checker = EligibilityChecker()
airdrop_config = registry.get_airdrop('example_testnet')

for wallet in wallets:
    is_eligible, reason, metadata = await checker.check_eligibility(
        wallet, airdrop_config
    )
    print(f"{wallet.address}: {reason}")
```

### Execute Claims

```python
from modules.airdrop_claimer import AirdropClaimer
from modules.wallet_manager import WalletManager

# Initialize claimer
wallet_manager = WalletManager()
claimer = AirdropClaimer(wallet_manager=wallet_manager)

# Get wallets
wallets = wallet_manager.get_wallets(chain='ethereum_sepolia')

# Check and claim
stats = await claimer.check_and_claim_airdrops(
    wallets=wallets,
    airdrop_name='example_testnet',
    check_only=False
)

print(f"Eligible: {stats['eligible']}")
print(f"Claimed: {stats['claimed']}")
print(f"Failed: {stats['failed']}")
```

## Anti-Detection Features

The module integrates with the existing `AntiDetection` system:

1. **Random Delays**: Jittered delays between operations (2-5 seconds base)
2. **Skip Probability**: Random action skipping (configurable via `ACTION_SKIP_PROB`)
3. **Human-like Patterns**: Uses existing scheduler entropy and timing
4. **Retry Logic**: Exponential backoff with jitter

## Security Considerations

1. **Private Key Safety**:
   - Private keys are never logged
   - Keys derived on-demand from encrypted seed
   - Never stored in claim records

2. **Contract Validation**:
   - Contract addresses validated before interaction
   - Transaction simulation recommended before execution

3. **Rate Limiting**:
   - Respects claim windows
   - Auto-throttle on errors
   - Configurable delays between operations

4. **Database Security**:
   - All claim attempts recorded
   - Error messages logged for debugging
   - No sensitive data in error logs

## Claim Methods Explained

### Merkle Proof Claims

Used when airdrop uses merkle tree for eligibility:

1. Query eligibility API for merkle proof
2. Verify proof against on-chain merkle root
3. Build claim transaction with proof
4. Submit to blockchain

### API-Based Claims

Used when airdrop provider has centralized claim API:

1. Query eligibility API with wallet address
2. Sign claim request with private key
3. Submit to API endpoint
4. Receive transaction hash or claim ID

### Direct Claims

Used for simple contract-based claims:

1. Check wallet meets basic requirements
2. Build claim transaction
3. Estimate gas
4. Submit to blockchain

## Troubleshooting

### No Active Airdrops

**Problem**: `claim-airdrops` shows no active airdrops

**Solutions**:
- Check `config/airdrops.yaml` exists and is valid
- Verify airdrop status is "claimable"
- Check claim windows (claim_start and claim_end)
- Ensure `enabled: true` in config

### Wallets Not Eligible

**Problem**: All wallets show as ineligible

**Solutions**:
- Verify wallets have performed required actions
- Check action status is "success" in database
- Verify chain matches airdrop configuration
- Check minimum action count requirement

### Claims Failing

**Problem**: Claims show as "failed" in database

**Solutions**:
- Check wallet private keys are retrievable
- Verify contract addresses are correct
- Check network connectivity
- Review error_message in AirdropClaim table
- Ensure wallet has gas for transactions

### Private Key Not Found

**Problem**: "Private key not found" errors

**Solutions**:
- Verify `WALLET_SEED_MNEMONIC` is set correctly
- Check wallet derivation_index is set in database
- Ensure WalletManager can access seed mnemonic

## Database Queries

### Check Claim Status

```sql
-- View all claims
SELECT w.address, ac.airdrop_name, ac.status, ac.tx_hash, ac.claimed_at
FROM airdrop_claims ac
JOIN wallets w ON ac.wallet_id = w.id
ORDER BY ac.checked_at DESC;

-- Count claims by status
SELECT status, COUNT(*) as count
FROM airdrop_claims
GROUP BY status;

-- Find eligible but unclaimed
SELECT w.address, ac.airdrop_name, ac.checked_at
FROM airdrop_claims ac
JOIN wallets w ON ac.wallet_id = w.id
WHERE ac.status = 'eligible';
```

### Check Wallet Actions

```sql
-- View wallet actions
SELECT w.address, wa.action_type, wa.status, wa.executed_at
FROM wallet_actions wa
JOIN wallets w ON wa.wallet_id = w.id
WHERE w.chain = 'ethereum_sepolia'
ORDER BY wa.executed_at DESC;

-- Count actions by wallet
SELECT w.address, wa.action_type, COUNT(*) as count
FROM wallet_actions wa
JOIN wallets w ON wa.wallet_id = w.id
WHERE wa.status = 'success'
GROUP BY w.address, wa.action_type;
```

## Best Practices

1. **Always test with --check-only first**: Verify eligibility before claiming
2. **Use shard-based processing**: Distribute load across time
3. **Monitor claim status**: Check database regularly
4. **Keep configs updated**: Remove ended airdrops, add new ones
5. **Set realistic min_actions**: Avoid false positives
6. **Use appropriate delays**: Balance speed with detection avoidance
7. **Review errors**: Check error_message field for failed claims
8. **Test claim methods**: Verify merkle proofs and API endpoints work

## Future Enhancements

Potential improvements for production:

1. **Real RPC Integration**: Connect to actual blockchain nodes
2. **Gas Optimization**: Smart gas price estimation
3. **Batch Claims**: Claim multiple airdrops in one transaction
4. **Notification System**: Alert on successful claims
5. **Analytics Dashboard**: Track claim success rates
6. **Auto-Discovery**: Automatically detect new airdrops
7. **Proof Verification**: Full merkle proof verification on-chain
8. **Multi-sig Support**: Handle multi-signature wallets

## Support

For issues or questions:
- Check logs in the database `error_message` field
- Review claim status with `python main.py stats`
- Test with `--check-only` flag first
- Verify configuration in `config/airdrops.yaml`

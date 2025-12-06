# Airdrop Farming

🤖 **Sophisticated multi-chain testnet automation by BYNNΛI**

Professional-grade airdrop farming system with automated faucet claims, wallet orchestration, and human-like behavior patterns across 10+ blockchain networks.

## ⚠️ Disclaimer & Safety

This system is designed for **testnet environments only**. Always comply with project terms of service and airdrop eligibility requirements. 

**Important Safety Notes:**
- ✅ Only use on testnets (TESTNET_MODE=true)
- ✅ Never commit private keys or seed phrases to version control
- ✅ Store seeds encrypted with strong encryption keys (32+ characters)
- ✅ Use human-like scheduling to avoid Sybil detection
- ✅ Respect faucet rate limits and cooldowns
- ❌ Never use automation where prohibited by platform policies
- ❌ Never store plaintext private keys on disk

## ✨ Core Features

### 🔐 Wallet Management
- **HD Derivation**: BIP32/BIP39 hierarchical deterministic wallet generation
- **Multi-Chain Support**: EVM (Ethereum, Polygon, Arbitrum, Base, BNB, Avalanche, Fantom) + Solana, Aptos, Algorand
- **Encrypted Seeds**: Never stores plaintext private keys; derives on-demand from encrypted seed
- **Wallet Sharding**: Groups wallets into shards for staggered operations
- **100+ Wallets**: Manage hundreds of wallets with optimistic nonce management

### 💧 Faucet Automation
- **Multi-Chain Faucets**: 10+ networks with 30+ faucet providers
- **Config-Driven**: YAML-based faucet configuration (no code changes needed)
- **Cooldown Enforcement**: Per-faucet cooldown tracking with database persistence
- **Rate Limit Handling**: Exponential backoff with jitter for 429/5xx responses
- **Idempotency**: Prevents duplicate claims per (faucet, wallet, chain, day)
- **Balance Validation**: Pre-flight and post-claim balance checks
- **Captcha Solving**: Pluggable solver interface (2Captcha, AntiCaptcha, Manual)
- **IP Rotation**: Optional proxy pool support with round-robin rotation
- **Human-Like Timing**: Randomized delays, jitter, and shard-based staggering

### 🎯 Eligibility Actions
- **Staking**: Automated token staking with validator selection
- **Swapping**: DEX integration for token swaps with slippage protection
- **Bridging**: Cross-chain asset transfers via bridge protocols
- **Human Behavior**: Timing jitter, parameter variance, per-wallet cooldowns
- **Pre-Flight Checks**: Automatic balance validation before actions

### 📊 Observability & Resilience
- **Structured Logging**: JSON logs with wallet, chain, action, tx_hash, duration, error class
- **Metrics**: Success/fail rates, rate-limit hits, cooldown deferrals, nonce errors
- **Database Persistence**: SQLite (default) or PostgreSQL for state survival across restarts
- **Dead Letter Queue**: Stalled task marking for repeated failures
- **Error Classification**: Detailed error tracking and retry logic

### 🛠️ Developer Experience
- **Rich CLI**: Beautiful command-line interface with progress bars and tables
- **Concurrency Control**: Configurable worker pools with bounded semaphores
- **Environment-Based Config**: All settings via .env file
- **Comprehensive Documentation**: Setup, usage, configuration guides

## 🛠️ Technology Stack

- **Python 3.9+**: Core runtime
- **SQLAlchemy**: Database ORM with SQLite/PostgreSQL support
- **Web3.py**: Ethereum and EVM chain interactions
- **Solana/Solders**: Solana blockchain integration
- **Structlog**: Structured JSON logging
- **Click + Rich**: Beautiful CLI interface
- **AsyncIO**: Asynchronous task execution
- **Tenacity**: Retry logic with exponential backoff
- **Cryptography**: AES encryption for sensitive data

## 📦 Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/theoraclescript/airdrop-farming.git
cd airdrop-farming

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings (see Configuration section)
nano .env  # or use your preferred editor
```

## ⚙️ Configuration

### 1. Generate Seed Phrase

First, generate a secure BIP39 seed phrase:

```bash
python main.py seed --generate --word-count 24
```

**IMPORTANT:** Save this seed phrase securely! Add it to your `.env` file as `WALLET_SEED_MNEMONIC`.

### 2. Configure Environment Variables

Edit `.env` with required settings:

**Required:**
```env
# Wallet seed (from step 1)
WALLET_SEED_MNEMONIC=your_24_word_seed_phrase_here
WALLET_ENCRYPTION_KEY=your_strong_32_character_encryption_key_here
WALLET_COUNT=100

# Safety mode
TESTNET_MODE=true
```

**Optional but Recommended:**
```env
# Captcha solver (for automated faucet claiming)
SOLVER_PROVIDER=2captcha  # or anticaptcha, manual
SOLVER_API_KEY=your_solver_api_key_here

# RPC endpoints (use public or your own endpoints)
ETH_RPC_SEPOLIA=https://rpc.sepolia.org
POLYGON_RPC_AMOY=https://rpc-amoy.polygon.technology
# ... (see .env.example for all chains)

# Database (SQLite by default, can use PostgreSQL)
DATABASE_URL=sqlite:///data/airdrop_farming.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/airdrop_farming

# Proxy support (optional)
USE_PROXIES=false
PROXY_LIST=http://user:pass@ip:port,http://user:pass@ip2:port2
```

### 3. Faucet Configuration

Faucets are configured in `config/faucets.yaml`. This file includes:
- All supported chains (BNB, Avalanche, Ethereum, Polygon, Arbitrum, Base, Solana, Aptos, Algorand, Fantom)
- Multiple faucet providers per chain
- Cooldown periods, daily limits, captcha requirements
- Priority ordering

You can edit this file to:
- Enable/disable specific faucets
- Adjust cooldown periods
- Add new faucet endpoints
- Change priority ordering

## 🚀 Usage

### Create Wallets

Generate HD-derived wallets from your seed:

```bash
# Generate 100 wallets for EVM and Solana
python main.py create-wallets --count 100 --chains evm,solana --shard-size 10

# Generate wallets for specific chains
python main.py create-wallets --count 50 --chains evm
```

### List Wallets

View your generated wallets:

```bash
# List all wallets
python main.py list-wallets

# Filter by chain
python main.py list-wallets --chain evm

# Filter by shard
python main.py list-wallets --shard 0

# Limit display
python main.py list-wallets --limit 10
```

### Fund Wallets via Faucets

Automatically claim testnet tokens from configured faucets:

```bash
# Fund all wallets on all chains
python main.py fund-wallets

# Fund specific chains
python main.py fund-wallets --chains ethereum_sepolia,polygon_amoy

# Fund specific shard
python main.py fund-wallets --shard 0

# Limit number of wallets
python main.py fund-wallets --limit 10

# Adjust concurrency
python main.py fund-wallets --concurrency 10
```

**Note:** Funding respects cooldowns and rate limits. Wallets are processed with human-like staggering to avoid detection.

### Run Eligibility Actions

Execute staking, swapping, and bridging operations:

```bash
# Run all actions for all wallets
python main.py run-actions --action all

# Run specific action type
python main.py run-actions --action stake
python main.py run-actions --action swap
python main.py run-actions --action bridge

# Run for specific shard
python main.py run-actions --shard 0 --action all

# Run for specific chain
python main.py run-actions --chain ethereum_sepolia --action swap

# Adjust concurrency
python main.py run-actions --action all --concurrency 5
```

### Check Status

View statistics and service status:

```bash
# View overall statistics
python main.py stats

# Check solver balance and service status
python main.py check-balance
```

### Advanced Usage

```bash
# Custom log level
python main.py --log-level DEBUG fund-wallets

# Custom database URL
python main.py --db-url postgresql://user:pass@localhost/db stats
```

## 📁 Project Structure

```
airdrop-farming/
├── config/                      # Configuration files
│   ├── faucets.yaml            # Multi-chain faucet configuration
│   ├── settings.py             # Legacy settings (being deprecated)
│   └── __init__.py
├── modules/                     # Core functionality
│   ├── wallet_manager.py       # HD wallet generation and management
│   ├── faucet_automation.py    # Faucet orchestration and workers
│   ├── captcha_broker.py       # Pluggable captcha solving
│   ├── action_pipeline.py      # Eligibility actions (stake, swap, bridge)
│   └── __init__.py
├── utils/                       # Utility functions
│   ├── database.py             # SQLAlchemy models and DB management
│   ├── logging_config.py       # Structured JSON logging
│   └── __init__.py
├── cli/                         # Command-line interface
│   ├── commands.py             # CLI commands implementation
│   └── __init__.py
├── data/                        # Database files (not in git)
│   └── airdrop_farming.db
├── logs/                        # Log files (not in git)
│   └── airdrop_farming.log
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🔐 Security Best Practices

### Critical Security Measures

✅ **DO:**
- Store only encrypted seeds in `.env` (never plaintext keys)
- Use strong encryption keys (32+ characters, random)
- Keep `.env` and database files out of version control
- Use HD derivation to derive keys on-demand
- Test on testnets only (TESTNET_MODE=true)
- Rotate seeds periodically for long-running operations
- Use environment variables for all sensitive configuration
- Enable human-like scheduling to reduce Sybil detection
- Respect faucet cooldowns and rate limits

❌ **DON'T:**
- Never commit `.env`, private keys, or seed phrases
- Never store plaintext private keys on disk
- Never use this on mainnet without explicit understanding of risks
- Never violate platform terms of service
- Never share your seed phrase or encryption key
- Don't use predictable encryption keys
- Don't disable TESTNET_MODE for production use

## 📊 Recommended Activity Schedule

To maximize airdrop eligibility while maintaining human-like behavior:

### Week 1-2: Initial Setup
- Generate wallets and fund via faucets
- Allow wallet "aging" (no additional activity)
- Stagger funding across multiple days

### Week 3-4: Basic Activity
- Begin small swap operations (2-4 per wallet per day)
- Introduce random timing jitter
- Use different action patterns per shard

### Week 5+: Full Automation
- Enable staking, swapping, and bridging
- Maintain per-wallet cooldowns (6+ hours)
- Continue human-like scheduling with jitter
- Rotate through different action types

### Anti-Sybil Best Practices
- Don't execute actions simultaneously across all wallets
- Use wallet sharding (10-20 wallets per shard)
- Stagger shard processing (60+ seconds between shards)
- Vary transaction amounts slightly
- Randomize timing within configured ranges
- Respect daily action limits per wallet

## 🌐 Supported Networks

### EVM Chains
- ✅ Ethereum Sepolia & Goerli
- ✅ Polygon Amoy
- ✅ Arbitrum Sepolia & Goerli
- ✅ Base Sepolia
- ✅ BNB Smart Chain Testnet
- ✅ Avalanche Fuji
- ✅ Fantom Testnet

### Non-EVM Chains
- ✅ Solana Devnet & Testnet
- ✅ Aptos Testnet
- ✅ Algorand Testnet

## 🔧 Customization & Extension

### Adding New Faucets

Edit `config/faucets.yaml` to add new faucets:

```yaml
chains:
  your_chain:
    name: "Your Chain Name"
    chain_id: 12345
    native_token: "TOKEN"
    faucets:
      - name: "Your Faucet"
        url: "https://faucet.example.com"
        api_endpoint: "/api/claim"
        method: "POST"
        amount: "1.0"
        cooldown_hours: 24
        daily_limit: 1
        requires_captcha: true
        enabled: true
        priority: 1
```

### Database Backend

Switch to PostgreSQL for production:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/airdrop_farming
```

The system will automatically use the configured database.

### Custom Action Adapters

Extend `ActionAdapter` in `modules/action_pipeline.py` to add support for new chains or protocols.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional chain support
- New faucet providers
- Enhanced anti-Sybil measures
- Performance optimizations
- Documentation improvements

Please ensure all contributions maintain testnet-only focus and follow security best practices.

## 📄 License

MIT License - See LICENSE file for details

## 🔍 Troubleshooting

### Common Issues

**"No seed mnemonic configured"**
- Run `python main.py seed --generate` to create a seed
- Add the seed to your `.env` file as `WALLET_SEED_MNEMONIC`

**"Failed to solve captcha"**
- Verify your `SOLVER_API_KEY` is correct
- Check solver balance: `python main.py check-balance`
- Consider using `SOLVER_PROVIDER=manual` for manual solving

**"No wallets found"**
- Create wallets first: `python main.py create-wallets --count 10`
- Check database: `python main.py list-wallets`

**"Faucet in cooldown"**
- This is expected behavior - faucets have 12-24 hour cooldowns
- Wait for cooldown period to expire
- Try different faucets for the same chain

**Database locked errors**
- For SQLite: Reduce concurrency settings
- For production: Use PostgreSQL instead

## 🔗 Resources

- [Repository](https://github.com/theoraclescript/airdrop-farming)
- [Testnet Faucets Directory](https://faucetlink.to/)
- [BIP39 Mnemonic Generator](https://iancoleman.io/bip39/)
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Solana Developer Docs](https://docs.solana.com/)

## ⚡ Support

**By BYNNΛI**

For issues and questions:
- Open a [GitHub Issue](https://github.com/theoraclescript/airdrop-farming/issues)
- Contact via [LinkTree](https://linktr.ee/oraclescript)

## 📝 Changelog

### Version 2.0.0 (Current)
- ✨ Complete rewrite with production-grade architecture
- ✨ Multi-chain faucet automation (10+ networks)
- ✨ HD wallet derivation with encrypted seed management
- ✨ Pluggable captcha solver interface
- ✨ Human-like behavior with jitter and staggering
- ✨ SQLAlchemy ORM with SQLite/PostgreSQL support
- ✨ Structured JSON logging
- ✨ Rich CLI with progress tracking
- ✨ Config-driven faucet management

---

**Remember**: Always follow project rules and never use automation where prohibited. This tool is designed for **legitimate testnet farming only**. Respect rate limits, use human-like timing, and never expose your private keys.
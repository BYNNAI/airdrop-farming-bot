# Airdrop Farming Bot

🤖 Sophisticated airdrop farming automation for Phantom (Solana) and Cake Wallet with testnet token management, bridging, staking, and swapping capabilities.

## ⚠️ Disclaimer

This bot is for **educational and testnet purposes only**. Always comply with project terms of service and airdrop eligibility requirements. Using automation on mainnets may violate platform policies and result in disqualification.

## ✨ Features

- **Multi-Wallet Management**: Generate and manage multiple Phantom and Cake wallets
- **Automated Faucet Claiming**: Testnet token acquisition from multiple sources
- **Swap Automation**: Intelligent token swapping with anti-detection measures
- **Staking Operations**: Automated staking and reward claiming
- **Bridge Transactions**: Cross-chain bridging for airdrop eligibility
- **Anti-Sybil Protection**: Randomized behavior patterns and timing
- **Proxy Rotation**: IP rotation for enhanced anonymity
- **Comprehensive Logging**: Detailed activity tracking and analytics

## 🛠️ Technology Stack

- Python 3.9+
- Solana Web3.py / Solders
- Web3.py (Ethereum/EVM chains)
- SQLite for data persistence
- Celery + Redis for task queuing

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/theoraclescript/airdrop-farming-bot.git
cd airdrop-farming-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
nano .env
```

## ⚙️ Configuration

1. **Generate Wallets**: Run wallet generator to create new Phantom/Cake wallets
2. **Configure .env**: Add RPC endpoints, API keys, and proxy settings
3. **Set Testnet Mode**: Ensure `TESTNET_MODE=true` in .env
4. **Encryption**: Set a strong `ENCRYPTION_KEY` for wallet security

## 🚀 Usage

```bash
# Generate new wallets
python main.py --generate-wallets 10

# Start faucet claiming
python main.py --claim-faucets

# Run full automation
python main.py --auto

# Check wallet balances
python main.py --check-balances

# View statistics
python main.py --stats
```

## 📁 Project Structure

```
airdrop-farming-bot/
├── config/              # Configuration files
│   ├── faucets.json    # Faucet URLs and limits
│   └── settings.py     # Bot settings
├── modules/             # Core functionality
│   ├── wallet_manager.py
│   ├── faucet_claimer.py
│   ├── swap_executor.py
│   ├── stake_manager.py
│   ├── bridge_handler.py
│   └── anti_detection.py
├── utils/               # Utility functions
│   ├── logging.py
│   ├── database.py
│   └── proxy_rotation.py
├── main.py              # Entry point
├── requirements.txt     # Dependencies
└── .env.example         # Environment template
```

## 🔐 Security Best Practices

- Never commit `.env` or `wallets.json` to version control
- Use hardware wallets for mainnet operations
- Keep private keys encrypted
- Test thoroughly on devnet before testnet
- Use residential proxies for better anonymity
- Rotate wallets and proxies regularly

## 📊 Activity Scheduling

**Week 1-2**: Faucet claiming and wallet aging
**Week 3-4**: Begin swap operations (2-4 per day)
**Week 5+**: Full automation with staking and bridging

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## 📄 License

MIT License - See LICENSE file for details

## 🔗 Resources

- [Solana Documentation](https://docs.solana.com/)
- [Phantom Wallet](https://phantom.app/)
- [Cake Wallet](https://cakewallet.com/)
- [Testnet Faucets List](https://github.com/theoraclescript/airdrop-farming-bot/wiki/faucets)

## ⚡ Support

For issues and questions, please open a GitHub issue or contact via [LinkTree](https://linktr.ee/oraclescript).

---

**Remember**: Always follow project rules and never use automation where prohibited. This tool is designed for legitimate testnet farming only.
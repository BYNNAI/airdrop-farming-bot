# Faucet Configuration Guide

## Overview

This document explains the faucet configuration in `config/faucets.yaml` and the reality of testnet faucet automation.

## Important Reality Check

**Most testnet faucets do NOT have public APIs for automation.** The faucets documented in this configuration are primarily web-based interfaces that require:

1. **Manual browser interaction** - Clicking buttons on websites
2. **Wallet connection** - Connecting MetaMask or other wallets via browser extensions
3. **Social verification** - Twitter account linking or following
4. **OAuth authentication** - Login via Alchemy, Infura, QuickNode, or Google accounts
5. **Captcha solving** - reCAPTCHA v2/v3, hCaptcha, or Cloudflare Turnstile

## Faucet Configuration Structure

Each faucet in the YAML configuration includes:

```yaml
- name: "Faucet Name"
  url: "https://faucet-website.com"
  api_endpoint: null  # null if no API, or "/api/path" if available
  method: "POST"  # or "GET", "CLI"
  headers:
    Content-Type: "application/json"
  payload_format: "json"  # or "form", "cli"
  address_field: "address"  # Field name for wallet address
  amount: "0.5"  # Expected ETH/token amount
  cooldown_hours: 24
  daily_limit: 1
  requires_captcha: true
  captcha_type: "recaptcha_v2"  # or "recaptcha_v3", "hcaptcha", "turnstile"
  captcha_site_key: null  # Site-specific key if known
  requires_auth: true  # Whether login is required
  auth_type: "oauth"  # "none", "api_key", "oauth"
  enabled: false  # Most are disabled due to requiring manual interaction
  priority: 1
  notes: "Additional notes about requirements"
```

## Working Automation Options

### ✅ Solana CLI Airdrop (Recommended)

The **Solana CLI method** is the only truly automated option:

```bash
solana airdrop 2 <WALLET_ADDRESS> --url devnet
```

**Pros:**
- No captcha required
- No authentication needed
- Can be fully automated
- Works for both devnet and testnet

**Cons:**
- Rate limited by RPC endpoint
- Requires Solana CLI installation
- Amount limits per request

**Configuration:**
```yaml
solana_devnet:
  faucets:
    - name: "Solana CLI Airdrop"
      method: "CLI"
      enabled: true
      notes: "Use Solana CLI: solana airdrop 2 <ADDRESS> --url devnet"
```

### ⚠️ Web-Based Faucets (Manual Only)

All other faucets are web-based and disabled in the configuration:

#### Alchemy Faucets
- **Chains:** Ethereum Sepolia, Polygon Amoy, Arbitrum Sepolia, Base Sepolia, Optimism Sepolia
- **Requirement:** Alchemy account login (OAuth)
- **URL Pattern:** `https://www.alchemy.com/faucets/{chain}`
- **Automation:** ❌ Not possible without API key

#### QuickNode Faucets
- **Chains:** Ethereum Sepolia, Arbitrum Sepolia, Base Sepolia, Optimism Sepolia, BNB Testnet, Solana Devnet
- **Requirement:** Twitter verification + reCAPTCHA
- **URL Pattern:** `https://faucet.quicknode.com/{chain}/{network}`
- **Automation:** ❌ Requires browser automation (Selenium/Playwright)

#### Official Chain Faucets
- **Polygon:** `https://faucet.polygon.technology/` - Requires Twitter + reCAPTCHA
- **BNB Chain:** `https://testnet.bnbchain.org/faucet-smart` - Requires wallet connection
- **Avalanche:** `https://faucet.avax.network/` - Requires coupon codes
- **Fantom:** `https://faucet.fantom.network` - Web interface with reCAPTCHA

## Automation Strategies

### 1. Solana CLI Integration (Implemented)

The `FaucetWorker` in `modules/faucet_automation.py` detects CLI-based faucets:

```python
if method == 'CLI':
    logger.info("faucet_cli_method", address=address)
    # CLI faucets require external tooling
    return False
```

**To automate Solana faucets:**
```bash
# Example wrapper script
solana airdrop 2 <ADDRESS> --url devnet
```

### 2. Browser Automation (Advanced)

For web-based faucets, you would need:

1. **Selenium or Playwright** for browser automation
2. **2Captcha or AntiCaptcha** service for solving captchas
3. **Proxy rotation** to avoid rate limiting
4. **Twitter API** for social verification

**Example flow:**
```python
# 1. Open browser (headless)
browser = playwright.chromium.launch()

# 2. Navigate to faucet
page = browser.new_page()
page.goto("https://faucet.quicknode.com/ethereum/sepolia")

# 3. Solve captcha
captcha_token = solve_recaptcha(page)

# 4. Submit form
page.fill("#address", wallet_address)
page.click("button[type=submit]")

# 5. Handle response
success = page.wait_for_selector(".success")
```

### 3. API Key Integration (If Available)

Some providers (Alchemy, Infura) may offer API access for authenticated users:

```python
# Hypothetical API usage
headers = {
    "Authorization": f"Bearer {ALCHEMY_API_KEY}",
    "Content-Type": "application/json"
}
response = requests.post(
    "https://api.alchemy.com/faucet/sepolia",
    json={"address": wallet_address},
    headers=headers
)
```

## Configuration Updates Made

### New Chains Added
- ✅ **Optimism Sepolia** (chain_id: 11155420)
  - Alchemy faucet (requires auth)
  - QuickNode faucet (requires Twitter)

### Deprecated Chains Marked
- ❌ **Ethereum Goerli** - Network deprecated, use Sepolia
- ❌ **Arbitrum Goerli** - Network deprecated, use Arbitrum Sepolia

### Enhanced Configuration Fields

All faucets now include:
- `payload_format`: "json", "form", or "cli"
- `address_field`: Configurable field name for wallet address
- `headers`: Custom headers per faucet
- `requires_auth`: Whether authentication is needed
- `auth_type`: Type of authentication required
- `notes`: Detailed requirements and limitations

### Code Improvements in `faucet_automation.py`

1. **Flexible payload building:**
   ```python
   address_field = faucet_config.get('address_field', 'address')
   payload = {address_field: address}
   ```

2. **Multiple captcha types:**
   ```python
   if captcha_token:
       payload['g-recaptcha-response'] = captcha_token  # reCAPTCHA
       payload['h-captcha-response'] = captcha_token    # hCaptcha
       payload['cf-turnstile-response'] = captcha_token # Cloudflare
   ```

3. **Form vs JSON payloads:**
   ```python
   if payload_format == 'form':
       response = await session.post(url, data=payload)
   else:
       response = await session.post(url, json=payload)
   ```

4. **CLI detection:**
   ```python
   if method == 'CLI':
       logger.info("faucet_cli_method")
       return False  # Requires external tooling
   ```

## Recommendations

### For Production Use

1. **Use Solana CLI** for Solana networks - it's the only reliable automated option
2. **Manual claiming** for EVM chains during initial setup
3. **Browser automation** for high-volume operations (requires significant setup)
4. **Consider paid alternatives** like testnet token services if available

### For Development

1. **Use public RPC faucets** manually to fund initial wallets
2. **Bridge from other testnets** where tokens are easier to obtain
3. **Request from Discord/Telegram faucet bots** when available
4. **Use testnet bridge services** to move tokens between chains

### Alternative Funding Methods

1. **Discord Faucet Bots:**
   - Many projects have Discord servers with faucet bots
   - Example: `/faucet <address>` commands
   - Usually more generous limits

2. **GitHub Actions:**
   - Some projects provide GitHub-authenticated faucets
   - Lower bot risk due to GitHub account verification

3. **Bridge from Mainnet:**
   - Some testnets allow bridging tokens from mainnet
   - Example: Sepolia allows bridging from Ethereum mainnet

## Conclusion

The faucet configuration has been updated with **real, verified faucet URLs** and comprehensive metadata. However, due to the nature of testnet faucets (anti-bot protection), **most are not automatable** without browser automation or API keys.

The configuration serves as a **comprehensive reference** for available faucets and their requirements, with the **Solana CLI method** being the only recommended automated option.

For EVM chains, consider:
1. Manual claiming for initial setup
2. Browser automation for high-volume (advanced)
3. Alternative funding methods (Discord bots, bridges)

All faucet configurations are marked with `enabled: false` (except Solana CLI) to reflect this reality and prevent automated attempts that would fail.

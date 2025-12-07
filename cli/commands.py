"""
Command-line interface for airdrop farming operations.

This module provides a comprehensive CLI for managing multi-chain testnet wallets,
faucet automation, and eligibility actions with anti-detection capabilities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BYNNΛI - AirdropFarm
Sophisticated multi-chain airdrop farming automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: BYNNΛI
Project: AirdropFarm
License: MIT
Repository: https://github.com/BYNNAI/airdrop-farming-bot
"""

import os
import sys
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import init_db, get_db_session, Wallet, AirdropClaim
from utils.logging_config import configure_logging, get_logger
from modules.wallet_manager import WalletManager
from modules.faucet_automation import FaucetOrchestrator
from modules.action_pipeline import ActionPipeline
from modules.airdrop_claimer import AirdropClaimer, AirdropRegistry

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option('--log-level', default='INFO', help='Log level (DEBUG, INFO, WARNING, ERROR)')
@click.option('--db-url', help='Database URL override')
def cli(log_level, db_url):
    """Airdrop Farming - Multi-chain testnet automation by BYNNΛI."""
    # Configure logging
    configure_logging(log_level=log_level)
    
    # Initialize database
    init_db(db_url)
    
    console.print("[bold green]Airdrop Farming CLI[/bold green]")
    console.print(f"Log level: {log_level}")


@cli.command()
@click.option('--generate', is_flag=True, help='Generate a new seed mnemonic')
@click.option('--word-count', default=24, type=click.Choice(['12', '24']), help='Word count for mnemonic')
def seed(generate, word_count):
    """Manage wallet seed mnemonic."""
    wallet_manager = WalletManager()
    
    if generate:
        mnemonic = wallet_manager.generate_mnemonic(int(word_count))
        
        console.print("\n[bold red]IMPORTANT - SAVE THIS SECURELY![/bold red]")
        console.print("\n[yellow]Your new seed phrase:[/yellow]")
        console.print(f"\n[bold cyan]{mnemonic}[/bold cyan]\n")
        console.print("[yellow]Add this to your .env file as WALLET_SEED_MNEMONIC[/yellow]")
        console.print("[red]Never share this with anyone or commit it to version control![/red]\n")
    else:
        if wallet_manager.seed_mnemonic:
            console.print("[green]Seed mnemonic is configured[/green]")
        else:
            console.print("[red]No seed mnemonic found. Run with --generate to create one.[/red]")


@cli.command()
@click.option('--count', default=100, help='Number of wallets to generate per chain')
@click.option('--chains', default='evm,solana', help='Chains to generate wallets for (comma-separated)')
@click.option('--shard-size', default=10, help='Wallets per shard')
def create_wallets(count, chains, shard_size):
    """Generate HD-derived wallets and store in database."""
    wallet_manager = WalletManager()
    
    if not wallet_manager.seed_mnemonic:
        console.print("[red]Error: No seed mnemonic configured. Run 'seed --generate' first.[/red]")
        return
    
    chain_list = [c.strip() for c in chains.split(',')]
    
    console.print(f"\n[bold]Generating {count} wallets per chain...[/bold]")
    console.print(f"Chains: {', '.join(chain_list)}")
    console.print(f"Shard size: {shard_size}\n")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Generating wallets...", total=count * len(chain_list))
        
        generated = wallet_manager.generate_wallets(
            count=count,
            chains=chain_list,
            shard_size=shard_size
        )
        
        progress.update(task, completed=count * len(chain_list))
    
    # Display summary
    table = Table(title="Generated Wallets")
    table.add_column("Chain", style="cyan")
    table.add_column("Count", style="green")
    
    for chain, addresses in generated.items():
        table.add_row(chain, str(len(addresses)))
    
    console.print(table)
    console.print(f"\n[green]Successfully generated wallets![/green]\n")


@cli.command()
@click.option('--chain', help='Filter by chain')
@click.option('--shard', type=int, help='Filter by shard ID')
@click.option('--limit', default=20, help='Max wallets to display')
def list_wallets(chain, shard, limit):
    """List generated wallets from database."""
    wallet_manager = WalletManager()
    wallets = wallet_manager.get_wallets(chain=chain, shard_id=shard)
    
    if not wallets:
        console.print("[yellow]No wallets found.[/yellow]")
        return
    
    table = Table(title=f"Wallets (showing {min(limit, len(wallets))} of {len(wallets)})")
    table.add_column("ID", style="cyan")
    table.add_column("Address", style="green")
    table.add_column("Chain", style="yellow")
    table.add_column("Shard", style="magenta")
    table.add_column("Index", style="blue")
    
    for wallet in wallets[:limit]:
        table.add_row(
            str(wallet.id),
            wallet.address[:10] + "..." + wallet.address[-8:],
            wallet.chain,
            str(wallet.shard_id),
            str(wallet.derivation_index)
        )
    
    console.print(table)


@cli.command()
@click.option('--chains', help='Chains to fund (comma-separated, default: all)')
@click.option('--shard', type=int, help='Only fund specific shard')
@click.option('--limit', type=int, help='Limit number of wallets to fund')
@click.option('--concurrency', default=5, help='Concurrent workers')
def fund_wallets(chains, shard, limit, concurrency):
    """Fund wallets using faucet automation."""
    wallet_manager = WalletManager()
    
    # Get wallets to fund
    wallets = wallet_manager.get_wallets(shard_id=shard)
    
    if not wallets:
        console.print("[red]No wallets found. Create wallets first.[/red]")
        return
    
    if limit:
        wallets = wallets[:limit]
    
    chain_list = None
    if chains:
        chain_list = [c.strip() for c in chains.split(',')]
    
    console.print(f"\n[bold]Funding {len(wallets)} wallets...[/bold]")
    if chain_list:
        console.print(f"Chains: {', '.join(chain_list)}")
    console.print(f"Concurrency: {concurrency}\n")
    
    # Run faucet orchestrator
    orchestrator = FaucetOrchestrator(concurrency=concurrency)
    
    async def run_funding():
        stats = await orchestrator.fund_wallets(
            wallets=wallets,
            chains=chain_list,
            shard_stagger=True
        )
        return stats
    
    stats = asyncio.run(run_funding())
    
    # Display results
    console.print("\n[bold]Funding Results:[/bold]")
    console.print(f"Total wallets: {stats['total']}")
    console.print(f"Success: [green]{stats['success']}[/green]")
    console.print(f"Failed: [red]{stats['failed']}[/red]")
    
    if stats.get('by_chain'):
        table = Table(title="Results by Chain")
        table.add_column("Chain", style="cyan")
        table.add_column("Success", style="green")
        table.add_column("Failed", style="red")
        
        for chain, chain_stats in stats['by_chain'].items():
            table.add_row(
                chain,
                str(chain_stats['success']),
                str(chain_stats['failed'])
            )
        
        console.print("\n")
        console.print(table)


@cli.command()
@click.option('--shard', type=int, help='Only run for specific shard')
@click.option('--chain', help='Specific chain')
@click.option('--action', type=click.Choice(['stake', 'swap', 'bridge', 'all']), default='all')
@click.option('--limit', type=int, help='Limit number of wallets')
@click.option('--concurrency', default=3, help='Concurrent actions')
def run_actions(shard, chain, action, limit, concurrency):
    """Run eligibility actions (staking, swapping, bridging)."""
    wallet_manager = WalletManager()
    
    # Get wallets
    wallets = wallet_manager.get_wallets(chain=chain, shard_id=shard)
    
    if not wallets:
        console.print("[red]No wallets found.[/red]")
        return
    
    if limit:
        wallets = wallets[:limit]
    
    console.print(f"\n[bold]Running actions for {len(wallets)} wallets...[/bold]")
    console.print(f"Action type: {action}")
    console.print(f"Concurrency: {concurrency}\n")
    
    # Define actions to run
    actions_config = []
    
    # Example action configurations
    if action in ['stake', 'all']:
        actions_config.append({
            'type': 'stake',
            'chain': chain or 'ethereum_sepolia',
            'params': {'amount': 0.1}
        })
    
    if action in ['swap', 'all']:
        actions_config.append({
            'type': 'swap',
            'chain': chain or 'ethereum_sepolia',
            'params': {
                'from_token': 'ETH',
                'to_token': 'USDC',
                'amount': 0.01
            }
        })
    
    if action in ['bridge', 'all']:
        actions_config.append({
            'type': 'bridge',
            'chain': chain or 'ethereum_sepolia',
            'params': {
                'to_chain': 'polygon_amoy',
                'amount': 0.05
            }
        })
    
    # Run pipeline
    pipeline = ActionPipeline()
    
    async def run_pipeline():
        stats = await pipeline.run_pipeline(
            wallets=wallets,
            actions=actions_config,
            concurrency=concurrency
        )
        return stats
    
    stats = asyncio.run(run_pipeline())
    
    # Display results
    console.print("\n[bold]Action Results:[/bold]")
    console.print(f"Total actions: {stats['total']}")
    console.print(f"Success: [green]{stats['success']}[/green]")
    console.print(f"Failed: [red]{stats['failed']}[/red]")
    console.print(f"Skipped: [yellow]{stats['skipped']}[/yellow]")


@cli.command()
def check_balance():
    """Check solver and service balances."""
    from modules.captcha_broker import CaptchaBroker
    
    broker = CaptchaBroker()
    
    console.print("\n[bold]Service Status:[/bold]\n")
    
    # Check captcha solver
    if broker.check_availability():
        balance = broker.get_balance()
        if balance is not None:
            console.print(f"Captcha Solver ({broker.provider}): [green]${balance:.2f}[/green]")
        else:
            console.print(f"Captcha Solver ({broker.provider}): [yellow]Connected (balance unavailable)[/yellow]")
    else:
        console.print(f"Captcha Solver: [red]Manual mode or not configured[/red]")
    
    console.print()


@cli.command()
def stats():
    """Display statistics and metrics."""
    from utils.database import FaucetRequest, WalletAction
    
    with get_db_session() as session:
        # Wallet stats
        total_wallets = session.query(Wallet).count()
        enabled_wallets = session.query(Wallet).filter(Wallet.enabled == True).count()
        
        # Faucet stats
        total_faucet_requests = session.query(FaucetRequest).count()
        successful_requests = session.query(FaucetRequest).filter(
            FaucetRequest.status == 'success'
        ).count()
        
        # Action stats
        total_actions = session.query(WalletAction).count()
        successful_actions = session.query(WalletAction).filter(
            WalletAction.status == 'success'
        ).count()
        
        # Airdrop stats
        total_claims = session.query(AirdropClaim).count()
        successful_claims = session.query(AirdropClaim).filter(
            AirdropClaim.status == 'claimed'
        ).count()
        eligible_claims = session.query(AirdropClaim).filter(
            AirdropClaim.status == 'eligible'
        ).count()
    
    # Display stats
    table = Table(title="Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Wallets", str(total_wallets))
    table.add_row("Enabled Wallets", str(enabled_wallets))
    table.add_row("Faucet Requests", str(total_faucet_requests))
    table.add_row("Successful Faucet Claims", str(successful_requests))
    table.add_row("Total Actions", str(total_actions))
    table.add_row("Successful Actions", str(successful_actions))
    table.add_row("Airdrop Claims Checked", str(total_claims))
    table.add_row("Airdrops Eligible", str(eligible_claims))
    table.add_row("Airdrops Claimed", str(successful_claims))
    
    console.print("\n")
    console.print(table)
    console.print("\n")


@cli.command()
def list_airdrops():
    """List all configured airdrops and their status."""
    registry = AirdropRegistry()
    airdrops = registry.get_all_airdrops()
    
    if not airdrops:
        console.print("[yellow]No airdrops configured.[/yellow]")
        return
    
    table = Table(title="Configured Airdrops")
    table.add_column("Name", style="cyan")
    table.add_column("Chain", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Claim Method", style="blue")
    table.add_column("Min Actions", style="green")
    table.add_column("Enabled", style="white")
    
    for name, config in airdrops.items():
        status = config.get('status', 'unknown')
        status_color = {
            'claimable': 'green',
            'upcoming': 'yellow',
            'ended': 'red'
        }.get(status, 'white')
        
        enabled = "✓" if config.get('enabled', True) else "✗"
        
        table.add_row(
            config.get('name', name),
            config.get('chain', 'unknown'),
            f"[{status_color}]{status}[/{status_color}]",
            config.get('claim_method', 'unknown'),
            str(config.get('min_actions', 0)),
            enabled
        )
    
    console.print("\n")
    console.print(table)
    console.print("\n")


@cli.command()
@click.option('--airdrop', help='Specific airdrop to check/claim')
@click.option('--check-only', is_flag=True, help='Only check eligibility, do not claim')
@click.option('--shard', type=int, help='Only process specific shard')
@click.option('--chain', help='Filter by chain')
@click.option('--limit', type=int, help='Limit number of wallets to process')
def claim_airdrops(airdrop, check_only, shard, chain, limit):
    """Check eligibility and claim available airdrops."""
    wallet_manager = WalletManager()
    
    # Get wallets
    wallets = wallet_manager.get_wallets(chain=chain, shard_id=shard)
    
    if not wallets:
        console.print("[red]No wallets found.[/red]")
        return
    
    if limit:
        wallets = wallets[:limit]
    
    mode = "Checking eligibility" if check_only else "Claiming airdrops"
    console.print(f"\n[bold]{mode} for {len(wallets)} wallets...[/bold]")
    
    if airdrop:
        console.print(f"Airdrop: {airdrop}")
    else:
        console.print("All active airdrops")
    
    if chain:
        console.print(f"Chain: {chain}")
    if shard is not None:
        console.print(f"Shard: {shard}")
    
    console.print()
    
    # Run claimer
    claimer = AirdropClaimer()
    
    async def run_claims():
        stats = await claimer.check_and_claim_airdrops(
            wallets=wallets,
            airdrop_name=airdrop,
            check_only=check_only,
            shard_id=shard
        )
        return stats
    
    stats = asyncio.run(run_claims())
    
    # Display results
    console.print("\n[bold]Results:[/bold]")
    console.print(f"Total wallets: {stats['total_wallets']}")
    console.print(f"Total checks: {stats['total_checks']}")
    console.print(f"Eligible: [green]{stats['eligible']}[/green]")
    console.print(f"Ineligible: [yellow]{stats['ineligible']}[/yellow]")
    
    if not check_only:
        console.print(f"Claimed: [green]{stats['claimed']}[/green]")
        console.print(f"Failed: [red]{stats['failed']}[/red]")
    
    console.print(f"Skipped: {stats['skipped']}")
    console.print()


if __name__ == '__main__':
    cli()

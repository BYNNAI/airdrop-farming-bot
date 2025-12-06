#!/usr/bin/env python3
"""
Airdrop Farming - Multi-chain testnet automation
By BYNNΛI

Main entry point for the airdrop farming system.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.commands import cli

if __name__ == '__main__':
    cli()

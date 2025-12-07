"""
Structured logging configuration with JSON output.

This module configures structured logging using structlog with JSON formatting
for production-grade observability and log aggregation.

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
import logging
from pathlib import Path
from datetime import datetime
import structlog
from structlog.types import EventDict, Processor


def add_timestamp(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    if method_name == "warn":
        # Backwards compatibility
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def configure_logging(
    log_level: str = None,
    log_file: str = None,
    log_format: str = "json"
):
    """Configure structured logging with JSON output.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        log_format: Log format ('json' or 'console')
    """
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_file = log_file or os.getenv("LOG_FILE", "logs/airdrop_farming.log")
    log_format = log_format or os.getenv("LOG_FORMAT", "json")
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    
    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Format-specific processors
    if log_format == "json":
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # JSON format for file logs
        if log_format == "json":
            file_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def get_logger(name: str = None):
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Structured logger
    """
    return structlog.get_logger(name)


# Convenience functions for common logging patterns
def log_faucet_request(
    logger,
    wallet: str,
    chain: str,
    faucet: str,
    status: str,
    **kwargs
):
    """Log faucet request with standard fields."""
    logger.info(
        "faucet_request",
        wallet=wallet,
        chain=chain,
        faucet=faucet,
        status=status,
        **kwargs
    )


def log_transaction(
    logger,
    wallet: str,
    chain: str,
    action: str,
    tx_hash: str = None,
    status: str = "pending",
    **kwargs
):
    """Log blockchain transaction with standard fields."""
    logger.info(
        "transaction",
        wallet=wallet,
        chain=chain,
        action=action,
        tx_hash=tx_hash,
        status=status,
        **kwargs
    )


def log_error(
    logger,
    error_class: str,
    error_message: str,
    **kwargs
):
    """Log error with standard fields."""
    logger.error(
        "error_occurred",
        error_class=error_class,
        error_message=error_message,
        **kwargs
    )


def log_metric(
    logger,
    metric_name: str,
    metric_value: float,
    **kwargs
):
    """Log metric with standard fields."""
    logger.info(
        "metric",
        metric_name=metric_name,
        metric_value=metric_value,
        **kwargs
    )

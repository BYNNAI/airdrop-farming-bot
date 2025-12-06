"""Database models and connection management for airdrop farming."""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from contextlib import contextmanager

Base = declarative_base()


class Wallet(Base):
    """Wallet model for tracking generated wallets."""
    __tablename__ = 'wallets'
    
    id = Column(Integer, primary_key=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    chain = Column(String(50), nullable=False, index=True)
    derivation_index = Column(Integer, nullable=False)
    shard_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    nonce = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    
    # Relationships
    faucet_requests = relationship("FaucetRequest", back_populates="wallet")
    actions = relationship("WalletAction", back_populates="wallet")
    
    __table_args__ = (
        Index('idx_wallet_chain_shard', 'chain', 'shard_id'),
    )


class FaucetRequest(Base):
    """Track faucet funding requests and their status."""
    __tablename__ = 'faucet_requests'
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id'), nullable=False)
    chain = Column(String(50), nullable=False, index=True)
    faucet_name = Column(String(255), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Request details
    status = Column(String(50), default='pending', index=True)
    # Status: pending, in_progress, success, failed, rate_limited, cooldown
    
    amount_requested = Column(String(50))
    amount_received = Column(String(50))
    tx_hash = Column(String(255))
    
    # Timing and attempts
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    last_attempt_at = Column(DateTime)
    next_retry_at = Column(DateTime)
    attempts = Column(Integer, default=0)
    
    # Error tracking
    last_error = Column(Text)
    error_class = Column(String(100))
    
    # Network details
    source_ip = Column(String(50))
    captcha_required = Column(Boolean, default=False)
    captcha_solved = Column(Boolean, default=False)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="faucet_requests")
    
    __table_args__ = (
        Index('idx_faucet_status_chain', 'status', 'chain'),
        Index('idx_faucet_next_retry', 'next_retry_at'),
    )


class WalletAction(Base):
    """Track wallet actions (staking, swapping, bridging)."""
    __tablename__ = 'wallet_actions'
    
    id = Column(Integer, primary_key=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id'), nullable=False)
    action_type = Column(String(50), nullable=False, index=True)
    # Type: stake, swap, bridge, claim
    
    chain = Column(String(50), nullable=False)
    status = Column(String(50), default='pending', index=True)
    # Status: pending, in_progress, success, failed, cancelled
    
    # Action details (JSON-serializable data)
    params = Column(Text)
    result = Column(Text)
    
    tx_hash = Column(String(255))
    gas_used = Column(Float)
    
    # Timing
    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Error tracking
    error_message = Column(Text)
    attempts = Column(Integer, default=0)
    
    # Relationships
    wallet = relationship("Wallet", back_populates="actions")
    
    __table_args__ = (
        Index('idx_action_scheduled', 'scheduled_at', 'status'),
        Index('idx_action_type_chain', 'action_type', 'chain'),
    )


class FaucetCooldown(Base):
    """Track per-faucet cooldowns and rate limits."""
    __tablename__ = 'faucet_cooldowns'
    
    id = Column(Integer, primary_key=True)
    faucet_name = Column(String(255), nullable=False)
    chain = Column(String(50), nullable=False)
    wallet_address = Column(String(255), nullable=False)
    
    last_request_at = Column(DateTime, nullable=False, index=True)
    cooldown_until = Column(DateTime, nullable=False, index=True)
    requests_today = Column(Integer, default=1)
    daily_limit = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index('idx_cooldown_lookup', 'faucet_name', 'wallet_address', 'chain'),
        Index('idx_cooldown_expiry', 'cooldown_until'),
    )


class Metric(Base):
    """Track metrics and observability data."""
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(Text)  # JSON string for labels
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_metric_name_time', 'metric_name', 'timestamp'),
    )


class DatabaseManager:
    """Manage database connections and sessions."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            database_url: Database URL. If None, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL', 
            'sqlite:///data/airdrop_farming.db'
        )
        self.engine = None
        self.SessionLocal = None
        
    def initialize(self):
        """Initialize database engine and create tables."""
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(self.database_url)
        
        # Ensure data directory exists for SQLite
        if parsed.scheme == 'sqlite':
            # Extract path from SQLite URL properly
            db_path = parsed.path.lstrip('/')
            if db_path and db_path != ':memory:':
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
                else:
                    os.makedirs('data', exist_ok=True)
            
            # SQLite-specific settings
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True
            )
        else:
            # PostgreSQL and other databases
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
        
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup.
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_direct(self) -> Session:
        """Get a database session directly (caller must manage cleanup)."""
        return self.SessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def init_db(database_url: Optional[str] = None):
    """Initialize the global database manager.
    
    Args:
        database_url: Optional database URL override
    """
    global db_manager
    if database_url:
        db_manager = DatabaseManager(database_url)
    db_manager.initialize()


def get_db_session() -> Session:
    """Get a database session (context manager usage).
    
    Returns:
        Database session context manager
    """
    return db_manager.get_session()

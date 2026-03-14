"""Database models for the Macro Reasoning Agent."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, String, Float, DateTime, 
    Integer, Text, JSON, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

Base = declarative_base()


class Question(Base):
    """Polymarket question being tracked."""
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True)  # Polymarket condition_id
    slug = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # geopolitics, central_banks, energy, etc.
    
    # Market metadata
    token_id_yes = Column(String)
    token_id_no = Column(String)
    resolution_date = Column(DateTime)
    liquidity = Column(Float)
    volume_24h = Column(Float)
    
    # Status
    status = Column(String, default="active")  # active, paused, resolved
    outcome = Column(String)  # yes, no, or None if unresolved
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    daily_logs = relationship("DailyLog", back_populates="question", cascade="all, delete-orphan")
    resolution = relationship("Resolution", back_populates="question", uselist=False)


class DailyLog(Base):
    """Daily reasoning log for a question."""
    __tablename__ = "daily_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Probabilities
    prior_probability = Column(Float)
    posterior_probability = Column(Float)
    delta = Column(Float)
    polymarket_price = Column(Float)
    divergence_from_market = Column(Float)
    
    # Evidence and reasoning
    key_evidence = Column(JSON, default=list)
    evidence_classification = Column(JSON, default=dict)
    bull_case = Column(Text)
    bear_case = Column(Text)
    what_would_change_my_mind = Column(Text)
    update_confidence = Column(String)  # low, medium, high
    reasoning_summary = Column(Text)
    
    # Flags
    anchoring_warning = Column(Boolean, default=False)
    overreaction_warning = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="daily_logs")


class Resolution(Base):
    """Resolution record for post-hoc analysis."""
    __tablename__ = "resolutions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    
    # Outcome
    outcome = Column(String, nullable=False)  # yes or no
    resolved_at = Column(DateTime)
    
    # Scores
    agent_brier_score = Column(Float)
    market_brier_score = Column(Float)
    
    # Post-mortem
    post_mortem = Column(JSON, default=dict)  # Structured post-mortem data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question", back_populates="resolution")


class NewsArticle(Base):
    """Cached news articles for reference."""
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    source = Column(String)
    published_at = Column(DateTime)
    content = Column(Text)
    keywords = Column(JSON, default=list)
    
    # Timestamps
    fetched_at = Column(DateTime, default=datetime.utcnow)


# Database setup functions
def get_engine(db_path: str = "sqlite:///macro_reasoning.db"):
    """Create a synchronous engine."""
    return create_engine(db_path, echo=False)


def get_async_engine(db_path: str = "sqlite+aiosqlite:///macro_reasoning.db"):
    """Create an async engine."""
    return create_async_engine(db_path, echo=False)


def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(engine)


async def init_async_db(engine):
    """Initialize database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


SessionLocal = sessionmaker(autocommit=False, autoflush=False)

"""Data layer for the Macro Reasoning Agent."""
from .polymarket import (
    GammaMarketsClient, 
    ClobClient, 
    PolymarketClient,
    get_eligible_markets_sync
)
from .news import NewsAPIClient, NewsAggregator, fetch_news_sync
from .ingestion import DataIngestionPipeline, run_discovery, run_intake, run_daily_ingestion

__all__ = [
    "GammaMarketsClient",
    "ClobClient",
    "PolymarketClient",
    "NewsAPIClient",
    "NewsAggregator",
    "DataIngestionPipeline",
    "run_discovery",
    "run_intake",
    "run_daily_ingestion",
    "get_eligible_markets_sync",
    "fetch_news_sync",
]

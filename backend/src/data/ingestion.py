"""Data ingestion script for the Macro Reasoning Agent."""
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from ..models.database import (
    Question, DailyLog, NewsArticle, 
    get_engine, SessionLocal, init_db
)
from .polymarket import PolymarketClient, GammaMarketsClient
from .news import NewsAggregator

load_dotenv()


class DataIngestionPipeline:
    """Pipeline for ingesting data from Polymarket and news sources."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.polymarket: Optional[PolymarketClient] = None
        self.news: Optional[NewsAggregator] = None
    
    async def __aenter__(self):
        self.polymarket = PolymarketClient()
        self.news = NewsAggregator()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.polymarket:
            await self.polymarket.close()
        if self.news:
            await self.news.close()
    
    def set_db_session(self, session: Session):
        """Set the database session."""
        self.db = session
    
    async def discover_questions(
        self,
        tags: List[str] = None,
        min_liquidity: float = 50000,
        min_days: int = 14,
        max_days: int = 28,
        limit_per_tag: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Discover eligible questions from Polymarket.
        
        Args:
            tags: List of tags to search
            min_liquidity: Minimum liquidity in USD
            min_days: Minimum days to resolution
            max_days: Maximum days to resolution
            limit_per_tag: Max results per tag
            
        Returns:
            List of eligible market dictionaries
        """
        tags = tags or ["geopolitics", "central-banks", "energy"]
        all_markets = []
        
        for tag in tags:
            print(f"Searching tag: {tag}")
            markets = await self.polymarket.gamma.get_markets_by_tag(
                tag=tag,
                min_liquidity=min_liquidity,
                limit=limit_per_tag
            )
            print(f"  Found {len(markets)} markets with liquidity > ${min_liquidity:,.0f}")
            
            filtered = self.polymarket.gamma.filter_by_horizon(
                markets, min_days, max_days
            )
            print(f"  {len(filtered)} markets within {min_days}-{max_days} day horizon")
            
            for m in filtered:
                m["source_tag"] = tag
            all_markets.extend(filtered)
        
        return all_markets
    
    async def intake_question(self, condition_id: str, category: str = None) -> Question:
        """
        Intake a new question from Polymarket.
        
        Args:
            condition_id: Polymarket condition ID
            category: Optional category override
            
        Returns:
            Created Question model
        """
        # Fetch market data - try direct endpoint first, fallback to events
        market = await self.polymarket.gamma.get_market(condition_id)
        if not market:
            raise ValueError(f"Market {condition_id} not found or inaccessible")
        
        # Extract token IDs
        tokens = market.get("tokens", [])
        token_id_yes = tokens[0].get("token_id") if len(tokens) > 0 else None
        token_id_no = tokens[1].get("token_id") if len(tokens) > 1 else None
        
        # Parse resolution date
        end_date = None
        end_date_str = market.get("endDate") or market.get("resolutionDate")
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        
        # Create question
        question = Question(
            id=condition_id,
            slug=market.get("slug", ""),
            title=market.get("question", ""),
            description=market.get("description", ""),
            category=category or market.get("source_tag", "general"),
            token_id_yes=token_id_yes,
            token_id_no=token_id_no,
            resolution_date=end_date,
            liquidity=float(market.get("liquidityNum", 0) or 0),
            volume_24h=float(market.get("volume24hr", 0) or 0),
            status="active"
        )
        
        if self.db:
            self.db.add(question)
            self.db.commit()
            self.db.refresh(question)
        
        return question
    
    async def fetch_current_price(self, question: Question) -> Optional[float]:
        """
        Fetch current Polymarket price for a question.
        
        Args:
            question: Question model
            
        Returns:
            Current price (0-1) or None
        """
        if not question.token_id_yes:
            return None
        
        try:
            price_data = await self.polymarket.clob.get_price(question.token_id_yes)
            return float(price_data.get("price", 0))
        except Exception as e:
            print(f"Error fetching price for {question.id}: {e}")
            return None
    
    async def ingest_daily_data(
        self, 
        question: Question,
        fetch_news: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest daily data for a question.
        
        Args:
            question: Question model
            fetch_news: Whether to fetch news articles
            
        Returns:
            Dict with price and news data
        """
        result = {
            "question_id": question.id,
            "date": datetime.utcnow(),
            "polymarket_price": None,
            "articles": []
        }
        
        # Fetch current price
        price = await self.fetch_current_price(question)
        result["polymarket_price"] = price
        
        # Fetch news
        if fetch_news:
            try:
                question_dict = {
                    "title": question.title,
                    "description": question.description,
                    "category": question.category
                }
                articles = await self.news.get_relevant_news(question_dict, max_articles=15)
                result["articles"] = articles
                
                # Cache articles in DB
                if self.db:
                    for article in articles:
                        self._cache_article(article)
                        
            except Exception as e:
                print(f"Error fetching news for {question.id}: {e}")
        
        return result
    
    def _cache_article(self, article: Dict[str, Any]):
        """Cache a news article in the database."""
        try:
            existing = self.db.query(NewsArticle).filter(
                NewsArticle.url == article.get("url")
            ).first()
            
            if existing:
                return
            
            # Parse published date
            published_at = None
            published_str = article.get("publishedAt")
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            
            db_article = NewsArticle(
                url=article.get("url"),
                title=article.get("title", ""),
                source=article.get("source", {}).get("name", "") if article.get("source") else "",
                published_at=published_at,
                content=article.get("content", ""),
                keywords=[article.get("search_keyword", "")] if article.get("search_keyword") else []
            )
            
            self.db.add(db_article)
            self.db.commit()
            
        except Exception as e:
            print(f"Error caching article: {e}")
            self.db.rollback()


async def run_discovery(tags: List[str] = None) -> List[Dict[str, Any]]:
    """
    Run question discovery (standalone).
    
    Args:
        tags: List of tags to search
        
    Returns:
        List of eligible markets
    """
    async with DataIngestionPipeline() as pipeline:
        markets = await pipeline.discover_questions(tags=tags)
        return markets


async def run_intake(condition_id: str, db_path: str = "sqlite:///macro_reasoning.db"):
    """
    Intake a single question (standalone).
    
    Args:
        condition_id: Polymarket condition ID
        db_path: Database path
    """
    engine = get_engine(db_path)
    init_db(engine)
    
    session = SessionLocal(bind=engine)
    
    try:
        async with DataIngestionPipeline() as pipeline:
            pipeline.set_db_session(session)
            
            # Check if already exists
            existing = session.query(Question).filter(Question.id == condition_id).first()
            if existing:
                print(f"Question {condition_id} already exists")
                return existing
            
            question = await pipeline.intake_question(condition_id)
            print(f"Intaked question: {question.title}")
            print(f"  Category: {question.category}")
            print(f"  Liquidity: ${question.liquidity:,.2f}")
            print(f"  Resolution: {question.resolution_date}")
            
            return question
            
    finally:
        session.close()


async def run_daily_ingestion(db_path: str = "sqlite:///macro_reasoning.db"):
    """
    Run daily ingestion for all active questions.
    
    Args:
        db_path: Database path
    """
    engine = get_engine(db_path)
    init_db(engine)
    
    session = SessionLocal(bind=engine)
    
    try:
        # Get active questions
        questions = session.query(Question).filter(Question.status == "active").all()
        
        if not questions:
            print("No active questions to process")
            return
        
        print(f"Processing {len(questions)} active questions...")
        
        async with DataIngestionPipeline() as pipeline:
            pipeline.set_db_session(session)
            
            for question in questions:
                print(f"\nProcessing: {question.title[:60]}...")
                
                data = await pipeline.ingest_daily_data(question, fetch_news=True)
                
                print(f"  Polymarket price: {data['polymarket_price']}")
                print(f"  Articles fetched: {len(data['articles'])}")
        
        print("\nDaily ingestion complete")
        
    finally:
        session.close()


# CLI entry points
def main_discovery():
    """CLI: Discover eligible questions."""
    import json
    
    markets = asyncio.run(run_discovery())
    
    print(f"\n=== Found {len(markets)} eligible markets ===\n")
    
    for m in markets[:10]:  # Show first 10
        print(f"Title: {m.get('question', 'N/A')[:80]}")
        print(f"  Condition ID: {m.get('conditionId')}")
        print(f"  Liquidity: ${m.get('liquidityNum', 0):,.2f}")
        print(f"  End Date: {m.get('endDate')}")
        print(f"  Tag: {m.get('source_tag')}")
        print()


def main_intake():
    """CLI: Intake a question."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.data.ingestion intake <condition_id>")
        sys.exit(1)
    
    condition_id = sys.argv[1]
    asyncio.run(run_intake(condition_id))


def main_daily():
    """CLI: Run daily ingestion."""
    asyncio.run(run_daily_ingestion())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.data.ingestion [discover|intake|daily]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "discover":
        main_discovery()
    elif command == "intake":
        main_intake()
    elif command == "daily":
        main_daily()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python -m src.data.ingestion [discover|intake|daily]")

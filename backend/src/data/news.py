"""News API client for fetching relevant news articles."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

load_dotenv()


class NewsAPIClient:
    """Client for NewsAPI (newsapi.org)."""
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWSAPI_KEY")
        self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("NewsAPI key required. Set NEWSAPI_KEY environment variable.")
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                headers={
                    "X-Api-Key": self.api_key,
                    "User-Agent": "MacroReasoningAgent/0.2"
                }
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
    
    async def get_everything(
        self,
        q: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for news articles.
        
        Args:
            q: Search query (keywords, phrases)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Language code (default: en)
            sort_by: Sort by (relevancy, popularity, publishedAt)
            page_size: Number of results per page (max 100)
            page: Page number
        """
        params = {
            "q": q,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(page_size, 100),
            "page": page
        }
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
            
        try:
            response = await self._get_client().get("/everything", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching news: {e}")
            print(f"Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"Error fetching news: {e}")
            raise
    
    async def get_top_headlines(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        q: Optional[str] = None,
        page_size: int = 20,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Get top headlines.
        
        Args:
            country: 2-letter ISO 3166-1 code
            category: Category (business, entertainment, general, health, science, sports, technology)
            q: Search query
            page_size: Number of results per page (max 100)
            page: Page number
        """
        params = {
            "pageSize": min(page_size, 100),
            "page": page
        }
        
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if q:
            params["q"] = q
            
        try:
            response = await self._get_client().get("/top-headlines", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching headlines: {e}")
            raise
        except Exception as e:
            print(f"Error fetching headlines: {e}")
            raise
    
    async def get_news_last_24h(
        self,
        keywords: List[str],
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get news from the last 24 hours for given keywords.
        
        Args:
            keywords: List of keywords to search
            page_size: Max articles per keyword
            
        Returns:
            List of unique articles
        """
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        all_articles = []
        seen_urls = set()
        
        for keyword in keywords:
            try:
                result = await self.get_everything(
                    q=keyword,
                    from_date=yesterday,
                    to_date=today,
                    page_size=page_size,
                    sort_by="publishedAt"
                )
                
                articles = result.get("articles", [])
                for article in articles:
                    url = article.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        article["search_keyword"] = keyword
                        all_articles.append(article)
                        
            except Exception as e:
                print(f"Error fetching news for keyword '{keyword}': {e}")
                continue
        
        # Sort by published date
        all_articles.sort(
            key=lambda x: x.get("publishedAt", ""), 
            reverse=True
        )
        
        return all_articles


class NewsAggregator:
    """Aggregates news from multiple sources for a question."""
    
    # Topic-specific keywords for better search
    TOPIC_KEYWORDS = {
        "geopolitics": [
            "war", "conflict", "sanctions", "diplomacy", 
            "treaty", "invasion", "ceasefire", "negotiation",
            "middle east", "ukraine", "china", "taiwan",
            "iran", "israel", "gaza", "nato", "united nations"
        ],
        "central_banks": [
            "federal reserve", "fed", "interest rate", "ecb",
            "bank of japan", "boj", "central bank", "monetary policy",
            "inflation", "rate hike", "rate cut", "fomc"
        ],
        "energy": [
            "oil", "brent", "wti", "crude", "opec",
            "natural gas", "energy supply", "oil production",
            "oil price", "gasoline", "petroleum", "saudi arabia"
        ]
    }
    
    def __init__(self, news_api_key: Optional[str] = None):
        self.news = NewsAPIClient(news_api_key)
        self._has_api_key = bool(news_api_key or os.getenv("NEWSAPI_KEY"))
    
    async def close(self):
        await self.news.close()
    
    def is_available(self) -> bool:
        """Check if news API is configured."""
        return self._has_api_key
    
    def extract_keywords(self, question: Dict[str, Any]) -> List[str]:
        """
        Extract relevant keywords from a question.
        
        Args:
            question: Question dict with title, description, category
            
        Returns:
            List of keywords for news search
        """
        keywords = []
        
        # Add category-specific keywords
        category = question.get("category", "")
        if category in self.TOPIC_KEYWORDS:
            keywords.extend(self.TOPIC_KEYWORDS[category])
        
        # Extract from title
        title = question.get("title", "")
        description = question.get("description", "")
        
        # Add important words from title (simple extraction)
        title_words = title.lower().split()
        important_words = [
            w for w in title_words 
            if len(w) > 4 and w not in ["will", "there", "be", "the", "that", "with", "from", "have", "been"]
        ]
        keywords.extend(important_words)
        
        return list(set(keywords))[:10]  # Limit to 10 keywords
    
    async def get_relevant_news(
        self,
        question: Dict[str, Any],
        max_articles: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get relevant news for a question.
        
        Args:
            question: Question dict
            max_articles: Maximum articles to return
            
        Returns:
            List of relevant articles
        """
        if not self.is_available():
            print("NewsAPI not configured - skipping news fetch")
            return []
        
        keywords = self.extract_keywords(question)
        
        articles = await self.news.get_news_last_24h(
            keywords=keywords,
            page_size=max(5, max_articles // len(keywords)) if keywords else 10
        )
        
        return articles[:max_articles]


# Synchronous wrappers for CLI use
def fetch_news_sync(keywords: List[str], max_articles: int = 20) -> List[Dict[str, Any]]:
    """
    Synchronously fetch news articles.
    
    Args:
        keywords: List of keywords to search
        max_articles: Maximum articles to return
    """
    import asyncio
    
    async def _fetch():
        client = NewsAPIClient()
        try:
            articles = await client.get_news_last_24h(keywords, max_articles)
            return articles
        finally:
            await client.close()
    
    return asyncio.run(_fetch())

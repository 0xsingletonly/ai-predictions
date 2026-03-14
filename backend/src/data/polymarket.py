"""Polymarket API clients for Gamma and CLOB APIs."""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import httpx
from dotenv import load_dotenv

load_dotenv()


class GammaMarketsClient:
    """Client for Polymarket Gamma API (market metadata)."""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("POLYMARKET_GAMMA_API_KEY")
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "MacroReasoningAgent/0.2"
            }
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def get_markets(
        self,
        active: bool = True,
        tag: Optional[str] = None,
        liquidity_num_min: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch markets from Gamma API.
        
        Args:
            active: Only active markets
            tag: Filter by tag (e.g., 'geopolitics', 'crypto', 'sports')
            liquidity_num_min: Minimum liquidity in USD
            limit: Number of results to return
            offset: Pagination offset
        """
        params = {
            "active": str(active).lower(),
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "offset": offset,
        }
        
        if tag:
            params["tag"] = tag
        if liquidity_num_min:
            params["liquidityNumMin"] = liquidity_num_min
            
        try:
            response = await self.client.get("/markets", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching markets: {e}")
            raise
        except Exception as e:
            print(f"Error fetching markets: {e}")
            raise
    
    async def get_all_markets_via_events(
        self,
        active: bool = True,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all markets via events endpoint (includes event-grouped markets).
        
        This is more comprehensive than get_markets() as it includes markets
        that are part of events (like 'US forces enter Iran by...' event).
        
        Args:
            active: Only active events
            limit: Number of events to fetch
        """
        params = {
            "active": str(active).lower(),
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "order": "liquidity",
            "ascending": "false",
        }
        
        try:
            response = await self.client.get("/events", params=params)
            response.raise_for_status()
            events = response.json()
            
            # Flatten events into individual markets
            all_markets = []
            for event in events:
                event_markets = event.get("markets", [])
                # Add event context to each market
                for market in event_markets:
                    market["_event_title"] = event.get("title")
                    market["_event_slug"] = event.get("slug")
                all_markets.extend(event_markets)
            
            return all_markets
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching events: {e}")
            raise
        except Exception as e:
            print(f"Error fetching events: {e}")
            raise
    
    async def get_market(self, condition_id: str) -> Dict[str, Any]:
        """
        Fetch a single market by condition_id.
        
        Args:
            condition_id: The Polymarket condition ID
        """
        try:
            response = await self.client.get(f"/markets/{condition_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching market {condition_id}: {e}")
            raise
        except Exception as e:
            print(f"Error fetching market {condition_id}: {e}")
            raise
    
    async def get_markets_by_tag(
        self, 
        tag: str, 
        min_liquidity: float = 50000,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get markets by tag with minimum liquidity.
        
        Args:
            tag: Market tag/category
            min_liquidity: Minimum liquidity in USD (default $50k)
            limit: Max number of results
        """
        return await self.get_markets(
            active=True,
            tag=tag,
            liquidity_num_min=min_liquidity,
            limit=limit
        )
    
    def filter_by_horizon(
        self, 
        markets: List[Dict[str, Any]], 
        min_days: int = 14,
        max_days: int = 28
    ) -> List[Dict[str, Any]]:
        """
        Filter markets by resolution horizon.
        
        Args:
            markets: List of market dictionaries
            min_days: Minimum days to resolution
            max_days: Maximum days to resolution
        """
        filtered = []
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        for market in markets:
            end_date_str = market.get("endDate") or market.get("resolutionDate")
            if not end_date_str:
                continue
                
            try:
                # Handle ISO format dates
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                days_to_resolution = (end_date - now).days
                
                if min_days <= days_to_resolution <= max_days:
                    filtered.append(market)
            except (ValueError, TypeError):
                continue
                
        return filtered


class ClobClient:
    """Client for Polymarket CLOB API (price feeds)."""
    
    BASE_URL = "https://clob.polymarket.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("POLYMARKET_CLOB_API_KEY")
        headers = {
            "Accept": "application/json",
            "User-Agent": "MacroReasoningAgent/0.2"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers=headers
        )
    
    async def close(self):
        await self.client.aclose()
    
    async def get_price(self, token_id: str, side: str = "BUY") -> Dict[str, Any]:
        """
        Get current price for a token.
        
        Args:
            token_id: The token ID (from Gamma API)
            side: Side of the trade (BUY or SELL), default BUY
        """
        try:
            response = await self.client.get(
                f"/price", 
                params={"token_id": token_id, "side": side}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching price for {token_id}: {e}")
            raise
        except Exception as e:
            print(f"Error fetching price for {token_id}: {e}")
            raise
    
    async def get_prices(self, token_ids: List[str]) -> Dict[str, Any]:
        """
        Get prices for multiple tokens.
        
        Args:
            token_ids: List of token IDs
        """
        try:
            response = await self.client.post(
                "/prices",
                json={"tokens": token_ids}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching prices: {e}")
            raise
        except Exception as e:
            print(f"Error fetching prices: {e}")
            raise
    
    async def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """
        Get order book for a token.
        
        Args:
            token_id: The token ID
        """
        try:
            response = await self.client.get(f"/book", params={"token_id": token_id})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching order book for {token_id}: {e}")
            raise
        except Exception as e:
            print(f"Error fetching order book for {token_id}: {e}")
            raise
    
    async def get_market_trades(self, market_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades for a market.
        
        Args:
            market_id: The market ID
            limit: Number of trades to return
        """
        try:
            response = await self.client.get(
                f"/trades",
                params={"market": market_id, "limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching trades for {market_id}: {e}")
            raise
        except Exception as e:
            print(f"Error fetching trades for {market_id}: {e}")
            raise


class PolymarketClient:
    """Unified client for both Gamma and CLOB APIs."""
    
    def __init__(self, gamma_api_key: Optional[str] = None, clob_api_key: Optional[str] = None):
        self.gamma = GammaMarketsClient(gamma_api_key)
        self.clob = ClobClient(clob_api_key)
    
    async def close(self):
        await self.gamma.close()
        await self.clob.close()
    
    async def get_market_with_price(self, condition_id: str) -> Dict[str, Any]:
        """
        Fetch market metadata and current price.
        
        Args:
            condition_id: The Polymarket condition ID
            
        Returns:
            Market dict with added 'current_price' field
        """
        market = await self.gamma.get_market(condition_id)
        
        # Get token IDs from market (from clobTokenIds field)
        import json
        clob_tokens_raw = market.get("clobTokenIds", "[]")
        if isinstance(clob_tokens_raw, str):
            try:
                clob_tokens = json.loads(clob_tokens_raw)
            except json.JSONDecodeError:
                clob_tokens = []
        else:
            clob_tokens = clob_tokens_raw or []
        if clob_tokens:
            # Usually index 0 is YES, index 1 is NO
            yes_token_id = clob_tokens[0] if len(clob_tokens) > 0 else None
            if yes_token_id:
                try:
                    price_data = await self.clob.get_price(yes_token_id)
                    market["current_price"] = price_data.get("price", 0)
                    market["yes_token_price"] = price_data.get("price", 0)
                except Exception as e:
                    print(f"Could not fetch price: {e}")
                    market["current_price"] = None
        
        return market


# Synchronous wrapper for convenience
def get_eligible_markets_sync(
    tags: List[str] = None,
    min_liquidity: float = 50000,
    min_days: int = 14,
    max_days: int = 28,
    limit_per_tag: int = 20
) -> List[Dict[str, Any]]:
    """
    Synchronously fetch eligible markets (for CLI use).
    
    Args:
        tags: List of tags to search (default: ['geopolitics', 'central-banks', 'energy'])
        min_liquidity: Minimum liquidity in USD
        min_days: Minimum days to resolution
        max_days: Maximum days to resolution
        limit_per_tag: Max results per tag
    """
    import asyncio
    
    tags = tags or ["geopolitics", "central-banks", "energy"]
    all_markets = []
    
    async def _fetch():
        client = GammaMarketsClient()
        try:
            for tag in tags:
                markets = await client.get_markets_by_tag(
                    tag=tag,
                    min_liquidity=min_liquidity,
                    limit=limit_per_tag
                )
                filtered = client.filter_by_horizon(markets, min_days, max_days)
                for m in filtered:
                    m["source_tag"] = tag
                all_markets.extend(filtered)
        finally:
            await client.close()
    
    asyncio.run(_fetch())
    return all_markets

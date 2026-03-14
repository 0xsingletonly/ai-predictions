#!/usr/bin/env python3
"""CLI tool to discover eligible Polymarket questions."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.data.polymarket import GammaMarketsClient


async def main():
    print("🔍 Discovering eligible Polymarket questions...\n")
    
    client = GammaMarketsClient()
    try:
        # Search for geopolitics markets
        print("Searching for geopolitics markets with >$50k liquidity...")
        markets = await client.get_markets_by_tag(
            tag="geopolitics",
            min_liquidity=50000,
            limit=20
        )
        
        # Filter by horizon (2-4 weeks)
        filtered = client.filter_by_horizon(markets, min_days=14, max_days=28)
        
        print(f"\n✅ Found {len(filtered)} eligible markets:\n")
        
        for i, m in enumerate(filtered[:10], 1):
            liq = m.get("liquidityNum") or 0
            end_date = m.get("endDate", "N/A")
            print(f"{i}. {m.get('question', 'N/A')[:70]}")
            print(f"   Condition ID: {m.get('conditionId')}")
            print(f"   Liquidity: ${liq:,.2f}")
            print(f"   End Date: {end_date}")
            
            # Get outcome prices if available
            prices = m.get("outcomePrices")
            if prices:
                print(f"   Current Price (Yes): ${prices[0]}")
            print()
            
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

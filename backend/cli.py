#!/usr/bin/env python3
"""CLI for the Macro Reasoning Agent.

Commands:
- intake: Add a new Polymarket question by condition_id
- list: List all tracked questions
- update: Run daily update manually
- status: Show status of all questions
- resolve: Mark a question as resolved with outcome
"""
import asyncio
import argparse
import sys
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.database import (
    Question, DailyLog, Resolution,
    get_engine, init_db, SessionLocal
)
from src.data.ingestion import DataIngestionPipeline, run_intake
from src.scheduler.daily_job import run_daily_job
from src.utils.evaluation import compute_brier_score, compute_brier_scores_at_resolution


def cmd_intake(args):
    """Intake a new question from Polymarket."""
    print(f"🔍 Intaking question with condition_id: {args.condition_id}")
    
    question = asyncio.run(run_intake(args.condition_id, args.db))
    
    if question:
        print(f"\n✅ Successfully intaked question:")
        print(f"  ID: {question.id}")
        print(f"  Title: {question.title}")
        print(f"  Category: {question.category}")
        print(f"  Liquidity: ${question.liquidity:,.2f}")
        print(f"  Resolution Date: {question.resolution_date}")
    else:
        print(f"\n❌ Failed to intake question")
        sys.exit(1)


def cmd_list(args):
    """List all tracked questions."""
    engine = get_engine(args.db)
    init_db(engine)
    session = SessionLocal(bind=engine)
    
    try:
        questions = session.query(Question).all()
        
        if not questions:
            print("No questions tracked yet.")
            return
        
        print(f"\n{'ID':<40} {'Status':<10} {'Category':<15} {'Title':<50}")
        print("="*115)
        
        for q in questions:
            title = q.title[:47] + "..." if len(q.title) > 50 else q.title
            print(f"{q.id:<40} {q.status:<10} {q.category or 'N/A':<15} {title:<50}")
        
        print(f"\nTotal: {len(questions)} questions")
        
    finally:
        session.close()


def cmd_status(args):
    """Show detailed status of questions."""
    engine = get_engine(args.db)
    init_db(engine)
    session = SessionLocal(bind=engine)
    
    try:
        questions = session.query(Question).filter(Question.status == "active").all()
        
        if not questions:
            print("No active questions.")
            return
        
        print("\n📊 ACTIVE QUESTIONS STATUS")
        print("="*80)
        
        for q in questions:
            # Get latest log
            latest_log = session.query(DailyLog).filter(
                DailyLog.question_id == q.id
            ).order_by(DailyLog.date.desc()).first()
            
            print(f"\n📝 {q.title[:70]}")
            print(f"   ID: {q.id}")
            print(f"   Category: {q.category or 'N/A'}")
            
            if latest_log:
                print(f"   Last Update: {latest_log.date.strftime('%Y-%m-%d')}")
                print(f"   Probability: {latest_log.posterior_probability:.2f}")
                print(f"   Market Price: {latest_log.polymarket_price:.2f}" if latest_log.polymarket_price else "   Market Price: N/A")
                print(f"   Divergence: {latest_log.divergence_from_market:+.2f}" if latest_log.divergence_from_market else "   Divergence: N/A")
                print(f"   Confidence: {latest_log.update_confidence}")
                
                if latest_log.anchoring_warning:
                    print(f"   ⚠️  Anchoring Warning")
                if latest_log.overreaction_warning:
                    print(f"   ⚠️  Overreaction Warning")
            else:
                print(f"   Status: No updates yet")
        
    finally:
        session.close()


def cmd_update(args):
    """Run daily update manually."""
    print("🔄 Running daily update...")
    results = asyncio.run(run_daily_job(args.db))
    
    print(f"\n✅ Update complete!")
    print(f"  Processed: {results['questions_processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")


def cmd_resolve(args):
    """Mark a question as resolved."""
    engine = get_engine(args.db)
    init_db(engine)
    session = SessionLocal(bind=engine)
    
    try:
        # Find question
        question = session.query(Question).filter(Question.id == args.question_id).first()
        
        if not question:
            print(f"❌ Question not found: {args.question_id}")
            sys.exit(1)
        
        # Get all daily logs for this question
        logs = session.query(DailyLog).filter(
            DailyLog.question_id == question.id
        ).order_by(DailyLog.date).all()
        
        if not logs:
            print(f"❌ No daily logs found for question: {args.question_id}")
            sys.exit(1)
        
        # Compute Brier scores
        outcome = 1 if args.outcome.lower() == "yes" else 0
        
        agent_probs = [log.posterior_probability for log in logs if log.posterior_probability is not None]
        market_probs = [log.polymarket_price for log in logs if log.polymarket_price is not None]
        
        # Calculate Brier scores
        agent_brier = sum((p - outcome) ** 2 for p in agent_probs) / len(agent_probs) if agent_probs else None
        market_brier = sum((p - outcome) ** 2 for p in market_probs) / len(market_probs) if market_probs else None
        
        # Create resolution record
        resolution = Resolution(
            question_id=question.id,
            outcome="yes" if outcome == 1 else "no",
            resolved_at=datetime.utcnow(),
            agent_brier_score=agent_brier,
            market_brier_score=market_brier,
            post_mortem={
                "num_predictions": len(agent_probs),
                "agent_average_brier": agent_brier,
                "market_average_brier": market_brier,
                "agent_vs_market": agent_brier - market_brier if agent_brier and market_brier else None
            }
        )
        
        # Update question
        question.status = "resolved"
        question.outcome = "yes" if outcome == 1 else "no"
        
        session.add(resolution)
        session.commit()
        
        print(f"\n✅ Question resolved:")
        print(f"  Title: {question.title}")
        print(f"  Outcome: {'YES' if outcome == 1 else 'NO'}")
        print(f"  Agent Brier Score: {agent_brier:.4f}" if agent_brier else "  Agent Brier Score: N/A")
        print(f"  Market Brier Score: {market_brier:.4f}" if market_brier else "  Market Brier Score: N/A")
        
        if agent_brier and market_brier:
            if agent_brier < market_brier:
                print(f"  🎯 Agent outperformed market by {market_brier - agent_brier:.4f}")
            else:
                print(f"  📉 Market outperformed agent by {agent_brier - market_brier:.4f}")
        
    finally:
        session.close()


def cmd_discover(args):
    """Discover eligible questions from Polymarket."""
    from src.data.polymarket import GammaMarketsClient
    from datetime import datetime
    
    print("🔍 Discovering eligible Polymarket questions...\n")
    
    async def _discover():
        client = GammaMarketsClient()
        try:
            all_markets = []
            
            if args.use_tags:
                # Legacy: Search by tags (most markets don't have tags)
                tags = args.tags.split(",") if args.tags else ["geopolitics", "politics"]
                for tag in tags:
                    print(f"Searching tag: {tag}...")
                    markets = await client.get_markets_by_tag(
                        tag=tag.strip(),
                        min_liquidity=args.min_liquidity,
                        limit=20
                    )
                    if args.no_date_filter:
                        filtered = markets
                    else:
                        filtered = client.filter_by_horizon(markets, min_days=args.min_days, max_days=args.max_days)
                    for m in filtered:
                        m["source_tag"] = tag
                    all_markets.extend(filtered)
            else:
                # New: Get all markets (tags are often empty in API)
                print(f"Fetching all active markets (will filter by liquidity locally)...")
                markets = await client.get_markets(
                    active=True,
                    limit=args.limit
                )
                
                # Filter by liquidity locally (API filter doesn't work well)
                markets = [m for m in markets if (m.get("liquidityNum") or 0) >= args.min_liquidity]
                
                # Filter by date if requested
                if not args.no_date_filter:
                    markets = client.filter_by_horizon(markets, min_days=args.min_days, max_days=args.max_days)
                
                # Filter by keywords if specified
                if args.keywords:
                    keywords = [k.strip().lower() for k in args.keywords.split(",")]
                    filtered_by_keyword = []
                    for m in markets:
                        question = m.get("question", "").lower()
                        if any(kw in question for kw in keywords):
                            filtered_by_keyword.append(m)
                    markets = filtered_by_keyword
                    print(f"  Filtered by keywords '{args.keywords}': {len(markets)} matches")
                
                all_markets.extend(markets)
            
            # Remove duplicates and sort by liquidity
            seen = set()
            unique_markets = []
            for m in all_markets:
                cid = m.get("conditionId")
                if cid and cid not in seen:
                    seen.add(cid)
                    unique_markets.append(m)
            
            # Sort by liquidity (highest first)
            unique_markets.sort(key=lambda x: x.get("liquidityNum") or 0, reverse=True)
            
            print(f"\n✅ Found {len(unique_markets)} eligible markets:\n")
            
            now = datetime.utcnow()
            for i, m in enumerate(unique_markets[:20], 1):
                liq = m.get("liquidityNum") or 0
                end_date = m.get("endDate", "N/A")
                prices = m.get("outcomePrices", [])
                
                # Calculate days to resolution
                days_str = "N/A"
                if end_date and end_date != "N/A":
                    try:
                        dt = datetime.fromisoformat(end_date.replace("Z", "+00:00")).replace(tzinfo=None)
                        days = (dt - now).days
                        days_str = f"{days}d"
                    except:
                        pass
                
                price_str = ""
                if prices and len(prices) > 0:
                    try:
                        price_val = float(prices[0]) * 100
                        price_str = f" | 📊 Yes: {price_val:.1f}%"
                    except:
                        pass
                
                print(f"{i}. {m.get('question', 'N/A')[:65]}")
                print(f"   💰 ${liq:,.0f} | 📅 {days_str} | 🔚 {end_date[:10] if end_date else 'N/A'}{price_str}")
                print(f"   🆔 {m.get('conditionId')}")
                print()
            
            if len(unique_markets) > 20:
                print(f"... and {len(unique_markets) - 20} more")
                
        finally:
            await client.close()
    
    asyncio.run(_discover())


def main():
    parser = argparse.ArgumentParser(
        description="Macro Reasoning Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover eligible questions
  python cli.py discover
  
  # Intake a specific question
  python cli.py intake 0xabc123...
  
  # List all questions
  python cli.py list
  
  # Check status
  python cli.py status
  
  # Run daily update
  python cli.py update
  
  # Resolve a question
  python cli.py resolve 0xabc123... --outcome yes
        """
    )
    
    parser.add_argument("--db", default="sqlite:///macro_reasoning.db", help="Database path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Intake command
    intake_parser = subparsers.add_parser("intake", help="Intake a new question from Polymarket")
    intake_parser.add_argument("condition_id", help="Polymarket condition ID")
    intake_parser.set_defaults(func=cmd_intake)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all tracked questions")
    list_parser.set_defaults(func=cmd_list)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show detailed status")
    status_parser.set_defaults(func=cmd_status)
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Run daily update manually")
    update_parser.set_defaults(func=cmd_update)
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Mark a question as resolved")
    resolve_parser.add_argument("question_id", help="Question ID to resolve")
    resolve_parser.add_argument("--outcome", choices=["yes", "no"], required=True, help="Resolution outcome")
    resolve_parser.set_defaults(func=cmd_resolve)
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover eligible questions")
    discover_parser.add_argument("--tags", default="geopolitics,politics", help="Comma-separated tags to search (legacy)")
    discover_parser.add_argument("--use-tags", action="store_true", help="Use tag-based search (most markets have no tags)")
    discover_parser.add_argument("--keywords", type=str, help="Filter by keywords in question (comma-separated, e.g., 'trump,war,election')")
    discover_parser.add_argument("--min-liquidity", type=float, default=50000, help="Minimum liquidity")
    discover_parser.add_argument("--min-days", type=int, default=7, help="Minimum days to resolution (default: 7)")
    discover_parser.add_argument("--max-days", type=int, default=180, help="Maximum days to resolution (default: 180)")
    discover_parser.add_argument("--no-date-filter", action="store_true", help="Skip date range filtering (show all)")
    discover_parser.add_argument("--limit", type=int, default=100, help="Max markets to fetch")
    discover_parser.set_defaults(func=cmd_discover)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()

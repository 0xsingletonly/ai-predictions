"""Daily scheduled job for the Macro Reasoning Agent.

Uses APScheduler to run daily ingestion and reasoning updates.
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from ..models.database import (
    Question, DailyLog, Resolution, 
    get_engine, init_db, SessionLocal
)
from ..data.ingestion import DataIngestionPipeline
from ..data.news import NewsAggregator
from ..agents.reasoning import KimiReasoningAgent
from ..utils.evaluation import detect_anchoring, detect_overreaction

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyReasoningJob:
    """Daily job that runs ingestion and reasoning for all active questions."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session
        self.pipeline: Optional[DataIngestionPipeline] = None
        self.agent: Optional[KimiReasoningAgent] = None
    
    async def __aenter__(self):
        self.pipeline = await DataIngestionPipeline().__aenter__()
        self.agent = KimiReasoningAgent()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.pipeline:
            await self.pipeline.__aexit__(exc_type, exc_val, exc_tb)
    
    def set_db_session(self, session: Session):
        """Set the database session."""
        self.db = session
        if self.pipeline:
            self.pipeline.set_db_session(session)
    
    async def process_question(self, question: Question) -> Optional[DailyLog]:
        """
        Process a single question - fetch data and run reasoning.
        
        Args:
            question: The Question to process
            
        Returns:
            Created DailyLog or None if skipped
        """
        logger.info(f"Processing question: {question.title[:60]}...")
        
        try:
            # Step 1: Fetch current price and news
            logger.info("  Fetching market data and news...")
            data = await self.pipeline.ingest_daily_data(question, fetch_news=True)
            polymarket_price = data.get("polymarket_price")
            articles = data.get("articles", [])
            
            logger.info(f"  Polymarket price: {polymarket_price}")
            logger.info(f"  Articles fetched: {len(articles)}")
            
            # Step 2: Get prior probability (last day's posterior or default)
            prior_probability = await self._get_prior_probability(question)
            logger.info(f"  Prior probability: {prior_probability}")
            
            # Step 3: Run reasoning pipeline
            logger.info("  Running LLM reasoning...")
            reasoning_result = await self.agent.run_full_reasoning_pipeline(
                question={
                    "id": question.id,
                    "title": question.title,
                    "description": question.description,
                    "category": question.category
                },
                articles=articles,
                prior_probability=prior_probability,
                polymarket_price=polymarket_price
            )
            
            # Check if LLM reasoning actually succeeded or returned fallback values
            if reasoning_result.get("reasoning_summary", "").startswith("Error"):
                error_msg = reasoning_result.get("reasoning_summary", "Unknown error")
                logger.error(f"  ❌ LLM reasoning failed: {error_msg}")
                raise RuntimeError(f"LLM reasoning failed: {error_msg}")
            
            # Validate we got real results, not just defaults
            if reasoning_result.get("posterior_probability") is None:
                logger.error("  ❌ LLM returned None for posterior_probability")
                raise RuntimeError("LLM returned invalid posterior probability")
            
            logger.info(f"  ✅ Reasoning complete: posterior={reasoning_result.get('posterior_probability'):.2f}, "
                       f"delta={reasoning_result.get('delta', 0):+.2f}")
            
            # Step 4: Check for warnings
            logger.info("  Checking for warnings...")
            
            # Get recent logs for anchoring detection
            recent_logs = self.db.query(DailyLog).filter(
                DailyLog.question_id == question.id
            ).order_by(DailyLog.date.desc()).limit(5).all()
            
            log_dicts = [
                {
                    "date": log.date.isoformat() if log.date else "",
                    "delta": log.delta,
                    "update_confidence": log.update_confidence,
                    "evidence_classification": log.evidence_classification
                }
                for log in recent_logs
            ]
            
            anchoring_result = detect_anchoring(log_dicts)
            overreaction_result = detect_overreaction([{
                "date": datetime.utcnow().isoformat(),
                "delta": reasoning_result.get("delta", 0),
                "evidence_classification": reasoning_result.get("evidence_classification", {})
            }])
            
            # Step 5: Create daily log
            daily_log = DailyLog(
                question_id=question.id,
                date=datetime.utcnow(),
                prior_probability=prior_probability,
                posterior_probability=reasoning_result.get("posterior_probability"),
                delta=reasoning_result.get("delta"),
                polymarket_price=polymarket_price,
                divergence_from_market=reasoning_result.get("divergence_from_market"),
                key_evidence=reasoning_result.get("key_evidence", []),
                evidence_classification=reasoning_result.get("evidence_classification", {}),
                bull_case=reasoning_result.get("bull_case", ""),
                bear_case=reasoning_result.get("bear_case", ""),
                what_would_change_my_mind=reasoning_result.get("what_would_change_my_mind", ""),
                update_confidence=reasoning_result.get("update_confidence", "low"),
                reasoning_summary=reasoning_result.get("reasoning_summary", ""),
                anchoring_warning=anchoring_result.get("warning", False),
                overreaction_warning=overreaction_result.get("warning", False)
            )
            
            self.db.add(daily_log)
            self.db.commit()
            
            logger.info(f"  ✅ Complete: posterior={reasoning_result.get('posterior_probability')}, "
                       f"delta={reasoning_result.get('delta'):+.2f}, "
                       f"confidence={reasoning_result.get('update_confidence')}")
            
            if anchoring_result.get("warning"):
                logger.warning(f"  ⚠️  Anchoring warning detected")
            if overreaction_result.get("warning"):
                logger.warning(f"  ⚠️  Overreaction warning detected")
            
            return daily_log
            
        except Exception as e:
            logger.error(f"  ❌ Error processing question {question.id}: {e}")
            self.db.rollback()
            return None
    
    async def _get_prior_probability(self, question: Question) -> float:
        """Get the prior probability for a question."""
        # Try to get the most recent daily log
        last_log = self.db.query(DailyLog).filter(
            DailyLog.question_id == question.id
        ).order_by(DailyLog.date.desc()).first()
        
        if last_log:
            return last_log.posterior_probability
        
        # Default to market price or 0.5
        try:
            price = await self.pipeline.fetch_current_price(question)
            if price is not None:
                return price
        except Exception:
            pass
        
        return 0.5
    
    async def run_daily_update(self) -> Dict[str, Any]:
        """
        Run daily update for all active questions.
        
        Returns:
            Dict with summary of the update
        """
        logger.info("="*60)
        logger.info("STARTING DAILY UPDATE")
        logger.info("="*60)
        
        # Get active questions
        questions = self.db.query(Question).filter(Question.status == "active").all()
        logger.info(f"Found {len(questions)} active questions")
        
        if not questions:
            logger.info("No active questions to process")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "questions_processed": 0,
                "successful": 0,
                "failed": 0
            }
        
        # Process each question
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "questions_processed": len(questions),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for question in questions:
            log = await self.process_question(question)
            
            if log:
                results["successful"] += 1
                results["details"].append({
                    "question_id": question.id,
                    "title": question.title[:50],
                    "status": "success",
                    "posterior": log.posterior_probability,
                    "delta": log.delta
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "question_id": question.id,
                    "title": question.title[:50],
                    "status": "failed"
                })
        
        logger.info("="*60)
        logger.info(f"DAILY UPDATE COMPLETE: {results['successful']}/{results['questions_processed']} successful")
        logger.info("="*60)
        
        return results
    
    async def fetch_data(self) -> Dict[str, Any]:
        """
        Step 1: Fetch Polymarket prices and news for all active questions.
        Stores data in PendingUpdate table for later reasoning.
        
        Returns:
            Dict with fetch summary
        """
        from ..models.database import PendingUpdate
        
        logger.info("="*60)
        logger.info("FETCHING DATA (Step 1/2)")
        logger.info("="*60)
        
        questions = self.db.query(Question).filter(Question.status == "active").all()
        logger.info(f"Found {len(questions)} active questions")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "fetched": 0,
            "failed": 0,
            "details": []
        }
        
        for question in questions:
            try:
                logger.info(f"Fetching: {question.title[:60]}...")
                
                # Fetch price and news
                data = await self.pipeline.ingest_daily_data(question, fetch_news=True)
                
                # Store in PendingUpdate
                pending = PendingUpdate(
                    question_id=question.id,
                    polymarket_price=data.get("polymarket_price"),
                    articles=data.get("articles", []),
                    fetched_at=datetime.utcnow(),
                    processed=False
                )
                self.db.add(pending)
                self.db.commit()
                
                results["fetched"] += 1
                results["details"].append({
                    "question_id": question.id,
                    "title": question.title[:50],
                    "price": data.get("polymarket_price"),
                    "articles": len(data.get("articles", []))
                })
                
                logger.info(f"  ✓ Price: {data.get('polymarket_price')}, Articles: {len(data.get('articles', []))}")
                
            except Exception as e:
                logger.error(f"  ✗ Error fetching {question.id}: {e}")
                results["failed"] += 1
                self.db.rollback()
        
        logger.info("="*60)
        logger.info(f"FETCH COMPLETE: {results['fetched']} fetched, {results['failed']} failed")
        logger.info("You can now disconnect VPN and run: python cli.py reason")
        logger.info("="*60)
        
        return results
    
    async def run_reasoning(self) -> Dict[str, Any]:
        """
        Step 2: Run LLM reasoning on fetched data.
        Processes all unprocessed PendingUpdate entries.
        
        Returns:
            Dict with reasoning summary
        """
        from ..models.database import PendingUpdate
        
        logger.info("="*60)
        logger.info("RUNNING REASONING (Step 2/2)")
        logger.info("="*60)
        
        pending_updates = self.db.query(PendingUpdate).filter(
            PendingUpdate.processed == False
        ).all()
        
        logger.info(f"Found {len(pending_updates)} pending updates to process")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "processed": 0,
            "failed": 0,
            "details": []
        }
        
        for pending in pending_updates:
            question = pending.question
            
            try:
                logger.info(f"Reasoning: {question.title[:60]}...")
                
                # Get prior probability
                prior = await self._get_prior_probability(question)
                
                # Run LLM reasoning
                reasoning_result = await self.agent.run_full_reasoning_pipeline(
                    question={
                        "id": question.id,
                        "title": question.title,
                        "description": question.description,
                        "category": question.category
                    },
                    articles=pending.articles,
                    prior_probability=prior,
                    polymarket_price=pending.polymarket_price
                )
                
                # Check for errors
                if reasoning_result.get("reasoning_summary", "").startswith("Error"):
                    raise RuntimeError(f"LLM reasoning failed: {reasoning_result.get('reasoning_summary')}")
                
                if reasoning_result.get("posterior_probability") is None:
                    raise RuntimeError("LLM returned invalid posterior")
                
                # Check warnings
                recent_logs = self.db.query(DailyLog).filter(
                    DailyLog.question_id == question.id
                ).order_by(DailyLog.date.desc()).limit(5).all()
                
                log_dicts = [{"date": log.date.isoformat() if log.date else "", 
                             "delta": log.delta,
                             "update_confidence": log.update_confidence,
                             "evidence_classification": log.evidence_classification} 
                            for log in recent_logs]
                
                anchoring = detect_anchoring(log_dicts)
                overreaction = detect_overreaction([{
                    "date": datetime.utcnow().isoformat(),
                    "delta": reasoning_result.get("delta", 0),
                    "evidence_classification": reasoning_result.get("evidence_classification", {})
                }])
                
                # Create daily log
                daily_log = DailyLog(
                    question_id=question.id,
                    date=datetime.utcnow(),
                    prior_probability=prior,
                    posterior_probability=reasoning_result.get("posterior_probability"),
                    delta=reasoning_result.get("delta"),
                    polymarket_price=pending.polymarket_price,
                    divergence_from_market=reasoning_result.get("divergence_from_market"),
                    key_evidence=reasoning_result.get("key_evidence", []),
                    evidence_classification=reasoning_result.get("evidence_classification", {}),
                    bull_case=reasoning_result.get("bull_case", ""),
                    bear_case=reasoning_result.get("bear_case", ""),
                    what_would_change_my_mind=reasoning_result.get("what_would_change_my_mind", ""),
                    update_confidence=reasoning_result.get("update_confidence", "low"),
                    reasoning_summary=reasoning_result.get("reasoning_summary", ""),
                    anchoring_warning=anchoring.get("warning", False),
                    overreaction_warning=overreaction.get("warning", False)
                )
                
                self.db.add(daily_log)
                pending.processed = True
                self.db.commit()
                
                results["processed"] += 1
                results["details"].append({
                    "question_id": question.id,
                    "title": question.title[:50],
                    "prior": prior,
                    "posterior": reasoning_result.get("posterior_probability"),
                    "delta": reasoning_result.get("delta")
                })
                
                logger.info(f"  ✓ Complete: {prior:.2f} → {reasoning_result.get('posterior_probability'):.2f}")
                
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
                results["failed"] += 1
                self.db.rollback()
        
        logger.info("="*60)
        logger.info(f"REASONING COMPLETE: {results['processed']} processed, {results['failed']} failed")
        logger.info("="*60)
        
        return results


# Standalone functions for running the daily job
async def run_daily_job(db_path: str = "sqlite:///macro_reasoning.db") -> Dict[str, Any]:
    """
    Run the daily job (can be called from CLI or scheduler).
    
    Args:
        db_path: Database path
        
    Returns:
        Job results
    """
    engine = get_engine(db_path)
    init_db(engine)
    
    session = SessionLocal(bind=engine)
    
    try:
        async with DailyReasoningJob() as job:
            job.set_db_session(session)
            results = await job.run_daily_update()
            return results
    finally:
        session.close()


async def run_fetch_step(db_path: str = "sqlite:///macro_reasoning.db") -> Dict[str, Any]:
    """
    Run only the fetch step (Step 1/2).
    Fetches Polymarket prices and news, stores in PendingUpdate.
    
    Args:
        db_path: Database path
        
    Returns:
        Fetch results
    """
    engine = get_engine(db_path)
    init_db(engine)
    
    session = SessionLocal(bind=engine)
    
    try:
        async with DailyReasoningJob() as job:
            job.set_db_session(session)
            results = await job.fetch_data()
            return results
    finally:
        session.close()


async def run_reason_step(db_path: str = "sqlite:///macro_reasoning.db") -> Dict[str, Any]:
    """
    Run only the reasoning step (Step 2/2).
    Processes PendingUpdate entries with LLM reasoning.
    
    Args:
        db_path: Database path
        
    Returns:
        Reasoning results
    """
    engine = get_engine(db_path)
    init_db(engine)
    
    session = SessionLocal(bind=engine)
    
    try:
        async with DailyReasoningJob() as job:
            job.set_db_session(session)
            results = await job.run_reasoning()
            return results
    finally:
        session.close()


# CLI entry point
def main():
    """CLI entry point for running daily job."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run daily reasoning update")
    parser.add_argument("--db", default="sqlite:///macro_reasoning.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't save to DB)")
    parser.add_argument("fetch", action="store_true", help="Only fetch data (Step 1/2)")
    parser.add_argument("reason", action="store_true", help="Only run reasoning (Step 2/2)")
    
    args = parser.parse_args()
    
    if args.fetch:
        results = asyncio.run(run_fetch_step(args.db))
        print("\n" + "="*60)
        print("FETCH RESULTS")
        print("="*60)
        print(f"Questions fetched: {results['fetched']}")
        print(f"Failed: {results['failed']}")
        print("\nNext step: Disconnect VPN, then run: python cli.py reason")
        
    elif args.reason:
        results = asyncio.run(run_reason_step(args.db))
        print("\n" + "="*60)
        print("REASONING RESULTS")
        print("="*60)
        print(f"Questions processed: {results['processed']}")
        print(f"Failed: {results['failed']}")
        
    else:
        # Run full update
        results = asyncio.run(run_daily_job(args.db))
        print("\n" + "="*60)
        print("DAILY UPDATE RESULTS")
        print("="*60)
        print(f"Questions processed: {results['questions_processed']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        if results['details']:
            print("\nDetails:")
            for detail in results['details']:
                status_icon = "✅" if detail['status'] == 'success' else "❌"
                print(f"  {status_icon} {detail['title'][:50]}...")


if __name__ == "__main__":
    main()

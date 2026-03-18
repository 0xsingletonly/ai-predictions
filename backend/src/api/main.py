"""FastAPI backend for the Macro Reasoning Agent.

API Endpoints:
- GET /questions - List all active questions
- GET /questions/{id} - Get specific question details
- GET /questions/{id}/logs - Get daily log history
- GET /questions/{id}/performance - Get performance metrics
- GET /questions/{id}/reasoning/{date} - Get reasoning for specific date
"""
import os
from typing import List, Optional
from datetime import datetime, date
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from ..models.database import (
    Question, DailyLog, Resolution,
    get_engine, init_db, SessionLocal
)
from ..utils.evaluation import (
    compute_brier_score,
    detect_anchoring,
    detect_overreaction
)

load_dotenv()

# Database setup
engine = get_engine(os.getenv("DATABASE_URL", "sqlite:///macro_reasoning.db"))
init_db(engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal(bind=engine)
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Starting Macro Reasoning Agent API")
    yield
    # Shutdown
    print("🛑 Shutting down API")


app = FastAPI(
    title="Macro Reasoning Agent API",
    description="API for the Polymarket-integrated Geopolitical Forecasting System",
    version="0.2.0",
    lifespan=lifespan
)

# CORS configuration for React dev server
# Note: allow_credentials=True cannot be used with allow_origins=["*"]
# Using specific origins for development
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # React default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# Add any additional origins from environment variable
import os
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    origins.extend(cors_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Pydantic models for API responses
from pydantic import BaseModel


class QuestionSummary(BaseModel):
    """Summary of a question for list view."""
    id: str
    title: str
    category: Optional[str]
    status: str
    current_probability: Optional[float]
    polymarket_price: Optional[float]
    divergence: Optional[float]
    last_updated: Optional[str]
    
    class Config:
        from_attributes = True


class QuestionDetail(BaseModel):
    """Detailed question information."""
    id: str
    slug: str
    title: str
    description: Optional[str]
    category: Optional[str]
    status: str
    outcome: Optional[str]
    resolution_date: Optional[str]
    liquidity: Optional[float]
    volume_24h: Optional[float]
    token_id_yes: Optional[str]
    token_id_no: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class DailyLogEntry(BaseModel):
    """Daily log entry."""
    id: int
    date: str
    prior_probability: Optional[float]
    posterior_probability: Optional[float]
    delta: Optional[float]
    polymarket_price: Optional[float]
    divergence_from_market: Optional[float]
    key_evidence: List[str]
    update_confidence: Optional[str]
    reasoning_summary: Optional[str]
    anchoring_warning: bool
    overreaction_warning: bool
    
    class Config:
        from_attributes = True


class ReasoningDetail(BaseModel):
    """Full reasoning trace for a specific day."""
    date: str
    question_id: str
    prior_probability: Optional[float]
    posterior_probability: Optional[float]
    delta: Optional[float]
    polymarket_price: Optional[float]
    divergence_from_market: Optional[float]
    evidence_classification: dict
    bull_case: str
    bear_case: str
    what_would_change_my_mind: Optional[str]
    update_confidence: Optional[str]
    reasoning_summary: Optional[str]
    key_evidence: List[str]
    
    class Config:
        from_attributes = True


class PerformanceMetrics(BaseModel):
    """Performance metrics for a question."""
    question_id: str
    status: str
    num_updates: int
    first_update: Optional[str]
    last_update: Optional[str]
    
    # Probability evolution
    probability_range: dict
    avg_divergence_from_market: Optional[float]
    max_divergence: Optional[float]
    
    # If resolved
    brier_score: Optional[float]
    market_brier_score: Optional[float]
    agent_vs_market: Optional[float]
    
    # Warnings
    anchoring_warnings: int
    overreaction_warnings: int
    
    class Config:
        from_attributes = True


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Macro Reasoning Agent API",
        "version": "0.2.0",
        "status": "running",
        "endpoints": [
            "/questions",
            "/questions/{id}",
            "/questions/{id}/logs",
            "/questions/{id}/performance",
            "/questions/{id}/reasoning/{date}"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/questions", response_model=List[QuestionSummary])
async def list_questions(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all questions with latest probability info.
    
    Args:
        status: Filter by status (active, paused, resolved)
        category: Filter by category
    """
    query = db.query(Question)
    
    if status:
        query = query.filter(Question.status == status)
    if category:
        query = query.filter(Question.category == category)
    
    questions = query.all()
    
    result = []
    for q in questions:
        # Get latest log for probability info
        latest_log = db.query(DailyLog).filter(
            DailyLog.question_id == q.id
        ).order_by(DailyLog.date.desc()).first()
        
        summary = QuestionSummary(
            id=q.id,
            title=q.title,
            category=q.category,
            status=q.status,
            current_probability=latest_log.posterior_probability if latest_log else None,
            polymarket_price=latest_log.polymarket_price if latest_log else None,
            divergence=latest_log.divergence_from_market if latest_log else None,
            last_updated=latest_log.date.isoformat() if latest_log else None
        )
        result.append(summary)
    
    return result


@app.get("/questions/{question_id}", response_model=QuestionDetail)
async def get_question(question_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific question."""
    question = db.query(Question).filter(Question.id == question_id).first()
    
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    return QuestionDetail(
        id=question.id,
        slug=question.slug,
        title=question.title,
        description=question.description,
        category=question.category,
        status=question.status,
        outcome=question.outcome,
        resolution_date=question.resolution_date.isoformat() if question.resolution_date else None,
        liquidity=question.liquidity,
        volume_24h=question.volume_24h,
        token_id_yes=question.token_id_yes,
        token_id_no=question.token_id_no,
        created_at=question.created_at.isoformat() if question.created_at else None,
        updated_at=question.updated_at.isoformat() if question.updated_at else None
    )


@app.get("/questions/{question_id}/logs", response_model=List[DailyLogEntry])
async def get_question_logs(
    question_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get daily log history for a question.
    
    Args:
        question_id: The question ID
        limit: Maximum number of logs to return
    """
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    logs = db.query(DailyLog).filter(
        DailyLog.question_id == question_id
    ).order_by(DailyLog.date.desc()).limit(limit).all()
    
    return [
        DailyLogEntry(
            id=log.id,
            date=log.date.isoformat() if log.date else None,
            prior_probability=log.prior_probability,
            posterior_probability=log.posterior_probability,
            delta=log.delta,
            polymarket_price=log.polymarket_price,
            divergence_from_market=log.divergence_from_market,
            key_evidence=log.key_evidence or [],
            update_confidence=log.update_confidence,
            reasoning_summary=log.reasoning_summary,
            anchoring_warning=log.anchoring_warning or False,
            overreaction_warning=log.overreaction_warning or False
        )
        for log in logs
    ]


@app.get("/questions/{question_id}/reasoning/{log_date}", response_model=ReasoningDetail)
async def get_reasoning_for_date(
    question_id: str,
    log_date: str,  # Format: YYYY-MM-DD
    db: Session = Depends(get_db)
):
    """
    Get full reasoning trace for a specific date.
    
    Args:
        question_id: The question ID
        log_date: Date in YYYY-MM-DD format
    """
    # Parse date
    try:
        target_date = datetime.strptime(log_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    # Find log for that date
    log = db.query(DailyLog).filter(
        DailyLog.question_id == question_id,
        DailyLog.date >= datetime.combine(target_date, datetime.min.time()),
        DailyLog.date < datetime.combine(target_date, datetime.max.time())
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=404, 
            detail=f"No log found for {log_date} on question {question_id}"
        )
    
    return ReasoningDetail(
        date=log.date.isoformat() if log.date else None,
        question_id=log.question_id,
        prior_probability=log.prior_probability,
        posterior_probability=log.posterior_probability,
        delta=log.delta,
        polymarket_price=log.polymarket_price,
        divergence_from_market=log.divergence_from_market,
        evidence_classification=log.evidence_classification or {},
        bull_case=log.bull_case or "",
        bear_case=log.bear_case or "",
        what_would_change_my_mind=log.what_would_change_my_mind,
        update_confidence=log.update_confidence,
        reasoning_summary=log.reasoning_summary,
        key_evidence=log.key_evidence or []
    )


@app.get("/questions/{question_id}/performance", response_model=PerformanceMetrics)
async def get_question_performance(
    question_id: str,
    db: Session = Depends(get_db)
):
    """Get performance metrics for a question."""
    # Verify question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")
    
    # Get all logs
    logs = db.query(DailyLog).filter(
        DailyLog.question_id == question_id
    ).order_by(DailyLog.date).all()
    
    if not logs:
        return PerformanceMetrics(
            question_id=question_id,
            status=question.status,
            num_updates=0,
            first_update=None,
            last_update=None,
            probability_range={"min": None, "max": None},
            avg_divergence_from_market=None,
            max_divergence=None,
            brier_score=None,
            market_brier_score=None,
            agent_vs_market=None,
            anchoring_warnings=0,
            overreaction_warnings=0
        )
    
    # Calculate metrics
    probabilities = [log.posterior_probability for log in logs if log.posterior_probability is not None]
    divergences = [log.divergence_from_market for log in logs if log.divergence_from_market is not None]
    
    probability_range = {
        "min": min(probabilities) if probabilities else None,
        "max": max(probabilities) if probabilities else None
    }
    
    avg_divergence = sum(divergences) / len(divergences) if divergences else None
    max_divergence = max([abs(d) for d in divergences]) if divergences else None
    
    # Count warnings
    anchoring_warnings = sum(1 for log in logs if log.anchoring_warning)
    overreaction_warnings = sum(1 for log in logs if log.overreaction_warning)
    
    # If resolved, calculate Brier scores
    brier_score = None
    market_brier_score = None
    agent_vs_market = None
    
    if question.status == "resolved" and question.outcome:
        outcome = 1 if question.outcome == "yes" else 0
        
        agent_probs = [log.posterior_probability for log in logs if log.posterior_probability is not None]
        market_probs = [log.polymarket_price for log in logs if log.polymarket_price is not None]
        
        if agent_probs:
            agent_briers = [compute_brier_score(p, outcome) for p in agent_probs]
            brier_score = sum(agent_briers) / len(agent_briers)
        
        if market_probs:
            market_briers = [compute_brier_score(p, outcome) for p in market_probs]
            market_brier_score = sum(market_briers) / len(market_briers)
        
        if brier_score is not None and market_brier_score is not None:
            agent_vs_market = brier_score - market_brier_score
    
    return PerformanceMetrics(
        question_id=question_id,
        status=question.status,
        num_updates=len(logs),
        first_update=logs[0].date.isoformat() if logs else None,
        last_update=logs[-1].date.isoformat() if logs else None,
        probability_range=probability_range,
        avg_divergence_from_market=avg_divergence,
        max_divergence=max_divergence,
        brier_score=brier_score,
        market_brier_score=market_brier_score,
        agent_vs_market=agent_vs_market,
        anchoring_warnings=anchoring_warnings,
        overreaction_warnings=overreaction_warnings
    )


@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get overall system statistics."""
    total_questions = db.query(Question).count()
    active_questions = db.query(Question).filter(Question.status == "active").count()
    resolved_questions = db.query(Question).filter(Question.status == "resolved").count()
    
    total_logs = db.query(DailyLog).count()
    
    # Get questions with best performance (if any resolved)
    resolutions = db.query(Resolution).all()
    
    return {
        "questions": {
            "total": total_questions,
            "active": active_questions,
            "resolved": resolved_questions
        },
        "daily_logs": {
            "total": total_logs
        },
        "resolutions": len(resolutions),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

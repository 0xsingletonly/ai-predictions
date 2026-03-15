"""Evaluation utilities for the Macro Reasoning Agent.

Includes Brier score computation and anchoring detection.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class BrierScoreResult:
    """Result of Brier score computation."""
    question_id: str
    outcome: int  # 0 or 1
    agent_brier: float
    market_brier: Optional[float]
    agent_vs_market: Optional[float]  # negative means agent was better
    resolution_date: datetime


def compute_brier_score(probability: float, outcome: int) -> float:
    """
    Compute Brier score: (probability - outcome)^2
    
    Args:
        probability: Predicted probability (0.0 to 1.0)
        outcome: Actual outcome (0 or 1)
        
    Returns:
        Brier score (lower is better, 0 is perfect, 1 is worst)
    """
    return (probability - outcome) ** 2


def compute_brier_scores_at_resolution(
    question_id: str,
    agent_probabilities: List[float],
    market_probabilities: List[float],
    outcome: int,
    resolution_date: datetime
) -> Dict[str, Any]:
    """
    Compute Brier scores for agent vs market at resolution.
    
    Args:
        question_id: The question ID
        agent_probabilities: List of agent's daily probability estimates
        market_probabilities: List of market's daily prices
        outcome: Actual outcome (0 or 1)
        resolution_date: When the question resolved
        
    Returns:
        Dict with Brier scores and comparison
    """
    # Compute average Brier scores over the lifetime of the question
    agent_scores = [compute_brier_score(p, outcome) for p in agent_probabilities]
    market_scores = [compute_brier_score(p, outcome) for p in market_probabilities]
    
    agent_avg = sum(agent_scores) / len(agent_scores) if agent_scores else None
    market_avg = sum(market_scores) / len(market_scores) if market_scores else None
    
    # Final day Brier scores
    agent_final = compute_brier_score(agent_probabilities[-1], outcome) if agent_probabilities else None
    market_final = compute_brier_score(market_probabilities[-1], outcome) if market_probabilities else None
    
    return {
        "question_id": question_id,
        "outcome": outcome,
        "resolution_date": resolution_date.isoformat(),
        "agent": {
            "average_brier": agent_avg,
            "final_brier": agent_final,
            "num_predictions": len(agent_probabilities)
        },
        "market": {
            "average_brier": market_avg,
            "final_brier": market_final,
            "num_predictions": len(market_probabilities)
        },
        "comparison": {
            "agent_vs_market_avg": agent_avg - market_avg if agent_avg and market_avg else None,
            "agent_vs_market_final": agent_final - market_final if agent_final and market_final else None,
            "agent_better": agent_avg < market_avg if agent_avg and market_avg else None
        }
    }


def detect_anchoring(
    daily_logs: List[Dict[str, Any]],
    min_consecutive_days: int = 3,
    max_delta: float = 0.02
) -> Dict[str, Any]:
    """
    Detect anchoring - when probability doesn't change much despite high confidence.
    
    Args:
        daily_logs: List of daily log entries with 'delta' and 'update_confidence'
        min_consecutive_days: Minimum consecutive days of small delta to trigger
        max_delta: Maximum delta to consider "small"
        
    Returns:
        Dict with anchoring analysis
    """
    if len(daily_logs) < min_consecutive_days:
        return {
            "anchoring_detected": False,
            "consecutive_small_deltas": 0,
            "max_streak": 0,
            "warning": False
        }
    
    # Sort by date
    sorted_logs = sorted(daily_logs, key=lambda x: x.get("date", ""))
    
    # Find consecutive days with small delta
    current_streak = 0
    max_streak = 0
    streaks = []
    
    for log in sorted_logs:
        delta_val = log.get("delta")
        delta = abs(delta_val) if delta_val is not None else 0
        confidence = log.get("update_confidence", "").lower()
        
        if delta <= max_delta:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            if current_streak >= min_consecutive_days:
                streaks.append(current_streak)
            current_streak = 0
    
    # Check final streak
    if current_streak >= min_consecutive_days:
        streaks.append(current_streak)
    
    # Anchoring detected if high confidence but small delta
    def safe_delta(log):
        d = log.get("delta")
        return abs(d) if d is not None else 0
    
    high_confidence_small_delta = any(
        log.get("update_confidence", "").lower() == "high" and 
        safe_delta(log) <= max_delta
        for log in sorted_logs[-min_consecutive_days:]
    )
    
    return {
        "anchoring_detected": max_streak >= min_consecutive_days,
        "consecutive_small_deltas": max_streak,
        "num_streaks": len(streaks),
        "high_confidence_small_delta": high_confidence_small_delta,
        "warning": high_confidence_small_delta or max_streak >= min_consecutive_days,
        "details": {
            "min_consecutive_days": min_consecutive_days,
            "max_delta_threshold": max_delta,
            "total_logs_analyzed": len(sorted_logs)
        }
    }


def detect_overreaction(
    daily_logs: List[Dict[str, Any]],
    noise_threshold: float = 0.10
) -> Dict[str, Any]:
    """
    Detect overreaction - when probability moves significantly on noise-classified evidence.
    
    Args:
        daily_logs: List of daily log entries
        noise_threshold: Probability change threshold to flag as overreaction
        
    Returns:
        Dict with overreaction analysis
    """
    overreactions = []
    
    for log in daily_logs:
        delta_val = log.get("delta")
        delta = abs(delta_val) if delta_val is not None else 0
        evidence = log.get("evidence_classification", {})
        
        # Check if noise was dominant but delta was large
        noise_count = len(evidence.get("noise", []))
        signal_count = len(evidence.get("supports_yes", [])) + len(evidence.get("supports_no", []))
        
        if noise_count > signal_count and delta > noise_threshold:
            overreactions.append({
                "date": log.get("date"),
                "delta": delta,
                "noise_items": noise_count,
                "signal_items": signal_count
            })
    
    return {
        "overreaction_detected": len(overreactions) > 0,
        "num_overreactions": len(overreactions),
        "overreactions": overreactions,
        "warning": len(overreactions) > 0
    }


def compute_calibration_curve(
    predictions: List[float],
    outcomes: List[int],
    num_bins: int = 10
) -> List[Dict[str, Any]]:
    """
    Compute calibration curve data.
    
    Args:
        predictions: List of predicted probabilities
        outcomes: List of actual outcomes (0 or 1)
        num_bins: Number of bins for the curve
        
    Returns:
        List of bin data with predicted vs actual frequencies
    """
    bins = []
    bin_size = 1.0 / num_bins
    
    for i in range(num_bins):
        bin_lower = i * bin_size
        bin_upper = (i + 1) * bin_size
        bin_center = (bin_lower + bin_upper) / 2
        
        # Find predictions in this bin
        bin_predictions = []
        bin_outcomes = []
        
        for pred, outcome in zip(predictions, outcomes):
            if bin_lower <= pred < bin_upper or (i == num_bins - 1 and pred == 1.0):
                bin_predictions.append(pred)
                bin_outcomes.append(outcome)
        
        if bin_predictions:
            avg_predicted = sum(bin_predictions) / len(bin_predictions)
            actual_frequency = sum(bin_outcomes) / len(bin_outcomes)
            
            bins.append({
                "bin_center": bin_center,
                "bin_range": [bin_lower, bin_upper],
                "predicted_probability": avg_predicted,
                "actual_frequency": actual_frequency,
                "count": len(bin_predictions)
            })
    
    return bins

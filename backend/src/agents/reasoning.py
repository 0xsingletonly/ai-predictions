"""LLM Reasoning Agent using Kimi API."""
import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class KimiReasoningAgent:
    """
    LLM Reasoning Agent for geopolitical forecasting.
    Uses Kimi K2.5 model via OpenAI-compatible API.
    """
    
    # Kimi API configuration
    BASE_URL = "https://api.moonshot.ai/v1"
    MODEL = "kimi-k2.5"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError("Kimi API key required. Set KIMI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL
        )
    
    async def classify_evidence(
        self,
        question: str,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Step 1: Evidence Classification
        Classify each news item as supports_yes, supports_no, neutral, or noise.
        
        Args:
            question: The prediction market question
            articles: List of news articles
            
        Returns:
            Dict with classified evidence
        """
        if not articles:
            return {
                "supports_yes": [],
                "supports_no": [],
                "neutral": [],
                "noise": [],
                "rationale": "No articles provided"
            }
        
        # Format articles for the prompt
        articles_text = "\n\n".join([
            f"Article {i+1}:\nTitle: {a.get('title', 'N/A')}\n"
            f"Content: {a.get('content', a.get('description', 'N/A'))[:500]}"
            for i, a in enumerate(articles[:10])  # Limit to 10 articles
        ])
        
        prompt = f"""You are analyzing news articles for a prediction market question.

Question: "{question}"

Here are the news articles from the last 24 hours:

{articles_text}

For each article, classify it as one of:
- supports_yes: Evidence suggests the event is MORE likely to happen
- supports_no: Evidence suggests the event is LESS likely to happen  
- neutral: Relevant but doesn't clearly support either outcome
- noise: Not relevant to the question

Provide your classification in this JSON format:
{{
    "supports_yes": ["Article 1: brief rationale", "Article 3: brief rationale"],
    "supports_no": ["Article 2: brief rationale"],
    "neutral": ["Article 4: brief rationale"],
    "noise": ["Article 5: brief rationale"],
    "rationale": "Overall assessment of the evidence quality and direction"
}}

Only output valid JSON."""

        try:
            # Combine system prompt into user message (Kimi K2.5 works better without system messages)
            full_prompt = "You are a geopolitical analysis assistant. Respond only with valid JSON.\n\n" + prompt
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            return self._parse_json_response(content)
            
        except Exception as e:
            print(f"Error in evidence classification: {e}")
            return {
                "supports_yes": [],
                "supports_no": [],
                "neutral": [],
                "noise": [],
                "rationale": f"Error: {str(e)}"
            }
    
    async def generate_bull_case(
        self,
        question: str,
        evidence: Dict[str, Any],
        current_probability: float
    ) -> str:
        """
        Step 2: Bull Case Synthesis
        Make the strongest case for why probability should be HIGHER.
        
        Args:
            question: The prediction market question
            evidence: Classified evidence from step 1
            current_probability: Current probability estimate
            
        Returns:
            Bull case argument (1-2 paragraphs)
        """
        evidence_summary = self._format_evidence_summary(evidence)
        
        prompt = f"""You are making the strongest possible BULL case for a prediction market question.

Question: "{question}"
Current probability estimate: {current_probability:.2f}

Evidence summary:
{evidence_summary}

Make the strongest possible argument for why the probability should be HIGHER.
Consider:
- What evidence supports the "yes" outcome?
- What trends or momentum might be building?
- What could surprise the market to the upside?
- Why might the current probability be too low?

Write 1-2 compelling paragraphs arguing for a higher probability.
Be specific, cite evidence, and steelman the case."""

        try:
            full_prompt = "You are a sharp geopolitical analyst making the strongest bull case.\n\n" + prompt
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating bull case: {e}")
            return f"Error generating bull case: {str(e)}"
    
    async def generate_bear_case(
        self,
        question: str,
        evidence: Dict[str, Any],
        current_probability: float
    ) -> str:
        """
        Step 3: Bear Case Synthesis
        Make the strongest case for why probability should be LOWER.
        
        Args:
            question: The prediction market question
            evidence: Classified evidence from step 1
            current_probability: Current probability estimate
            
        Returns:
            Bear case argument (1-2 paragraphs)
        """
        evidence_summary = self._format_evidence_summary(evidence)
        
        prompt = f"""You are making the strongest possible BEAR case for a prediction market question.

Question: "{question}"
Current probability estimate: {current_probability:.2f}

Evidence summary:
{evidence_summary}

Make the strongest possible argument for why the probability should be LOWER.
Consider:
- What evidence supports the "no" outcome?
- What obstacles or resistance exist?
- What could surprise the market to the downside?
- Why might the current probability be too high?

Write 1-2 compelling paragraphs arguing for a lower probability.
Be specific, cite evidence, and steelman the case."""

        try:
            full_prompt = "You are a sharp geopolitical analyst making the strongest bear case.\n\n" + prompt
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating bear case: {e}")
            return f"Error generating bear case: {str(e)}"
    
    async def generate_posterior(
        self,
        question: str,
        prior_probability: float,
        polymarket_price: Optional[float],
        evidence: Dict[str, Any],
        bull_case: str,
        bear_case: str
    ) -> Dict[str, Any]:
        """
        Step 4: Posterior Update + WTCMM
        Weigh bull/bear cases and output new probability with WTCMM.
        
        Args:
            question: The prediction market question
            prior_probability: Previous day's probability
            polymarket_price: Current Polymarket price (if available)
            evidence: Classified evidence
            bull_case: Bull case text
            bear_case: Bear case text
            
        Returns:
            Structured output with posterior probability, WTCMM, etc.
        """
        prompt = f"""You are a geopolitical forecaster updating a probability estimate.

Question: "{question}"

Prior probability: {prior_probability:.2f}
{f"Polymarket price: {polymarket_price:.2f}" if polymarket_price else ""}

BULL CASE (argument for higher probability):
{bull_case}

BEAR CASE (argument for lower probability):
{bear_case}

EVIDENCE SUMMARY:
- Supports YES: {len(evidence.get('supports_yes', []))} items
- Supports NO: {len(evidence.get('supports_no', []))} items
- Neutral: {len(evidence.get('neutral', []))} items

Your task:
1. Weigh the bull and bear cases
2. Calculate a new posterior probability (0.0 to 1.0)
3. Determine your confidence in this update (low/medium/high)
4. Write a "What Would Change My Mind" (WTCMM) statement - what specific evidence would cause you to significantly revise this probability?
5. Summarize your reasoning

Respond in this exact JSON format:
{{
    "posterior_probability": 0.55,
    "delta": 0.05,
    "update_confidence": "medium",
    "what_would_change_my_mind": "Specific falsifiable condition that would change my view",
    "reasoning_summary": "Brief summary of the key factors in this update"
}}

Rules:
- posterior_probability must be between 0.05 and 0.95 (never 0 or 1)
- delta is posterior minus prior
- WTCMM must be specific and falsifiable (not vague)
- update_confidence must be exactly: "low", "medium", or "high"

Output only valid JSON."""

        try:
            full_prompt = "You are a calibrated geopolitical forecaster. Respond only with valid JSON.\n\n" + prompt
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            result = self._parse_json_response(content)
            
            # Add computed fields
            result["prior_probability"] = prior_probability
            if polymarket_price is not None:
                result["polymarket_price"] = polymarket_price
                result["divergence_from_market"] = result.get("posterior_probability", 0) - polymarket_price
            
            # Validate WTCMM
            wtcmm = result.get("what_would_change_my_mind", "")
            result["wtcmm_valid"] = len(wtcmm) >= 20 and not wtcmm.lower().startswith("i would change")
            
            return result
            
        except Exception as e:
            print(f"Error generating posterior: {e}")
            return {
                "posterior_probability": prior_probability,
                "delta": 0.0,
                "prior_probability": prior_probability,
                "update_confidence": "low",
                "what_would_change_my_mind": f"Error: {str(e)}",
                "reasoning_summary": f"Error in reasoning: {str(e)}",
                "wtcmm_valid": False
            }
    
    async def run_full_reasoning_pipeline(
        self,
        question: Dict[str, Any],
        articles: List[Dict[str, Any]],
        prior_probability: float = 0.5,
        polymarket_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run all 4 reasoning steps for a question.
        
        Args:
            question: Question dict with title, description, etc.
            articles: List of news articles
            prior_probability: Previous day's probability
            polymarket_price: Current market price
            
        Returns:
            Complete reasoning output
        """
        question_text = question.get("title", "")
        
        print(f"  Step 1/4: Classifying evidence ({len(articles)} articles)...")
        evidence = await self.classify_evidence(question_text, articles)
        
        print(f"  Step 2/4: Generating bull case...")
        bull_case = await self.generate_bull_case(question_text, evidence, prior_probability)
        
        print(f"  Step 3/4: Generating bear case...")
        bear_case = await self.generate_bear_case(question_text, evidence, prior_probability)
        
        print(f"  Step 4/4: Computing posterior...")
        posterior = await self.generate_posterior(
            question_text,
            prior_probability,
            polymarket_price,
            evidence,
            bull_case,
            bear_case
        )
        
        # Compile full output
        output = {
            "question_id": question.get("id"),
            "date": datetime.utcnow().isoformat(),
            "prior_probability": prior_probability,
            "posterior_probability": posterior.get("posterior_probability"),
            "delta": posterior.get("delta"),
            "polymarket_price": polymarket_price,
            "divergence_from_market": posterior.get("divergence_from_market"),
            "key_evidence": evidence.get("supports_yes", [])[:3] + evidence.get("supports_no", [])[:3],
            "evidence_classification": {
                "supports_yes": evidence.get("supports_yes", []),
                "supports_no": evidence.get("supports_no", []),
                "neutral": evidence.get("neutral", []),
                "noise": evidence.get("noise", [])
            },
            "bull_case": bull_case,
            "bear_case": bear_case,
            "what_would_change_my_mind": posterior.get("what_would_change_my_mind"),
            "update_confidence": posterior.get("update_confidence"),
            "reasoning_summary": posterior.get("reasoning_summary"),
            "anchoring_warning": posterior.get("delta", 0) < 0.02 and posterior.get("update_confidence") == "high",
            "wtcmm_valid": posterior.get("wtcmm_valid", False)
        }
        
        return output
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        # Try to find JSON object
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start:end+1])
                except json.JSONDecodeError:
                    pass
            
            print(f"Could not parse JSON from: {content[:200]}...")
            return {"error": "Failed to parse JSON", "raw_content": content[:500]}
    
    def _format_evidence_summary(self, evidence: Dict[str, Any]) -> str:
        """Format evidence for prompts."""
        lines = []
        
        yes_items = evidence.get("supports_yes", [])
        no_items = evidence.get("supports_no", [])
        neutral_items = evidence.get("neutral", [])
        
        if yes_items:
            lines.append(f"Evidence supporting YES ({len(yes_items)} items):")
            for item in yes_items[:3]:
                lines.append(f"  - {item}")
        
        if no_items:
            lines.append(f"Evidence supporting NO ({len(no_items)} items):")
            for item in no_items[:3]:
                lines.append(f"  - {item}")
        
        if neutral_items:
            lines.append(f"Neutral evidence ({len(neutral_items)} items):")
            for item in neutral_items[:2]:
                lines.append(f"  - {item}")
        
        return "\n".join(lines) if lines else "No evidence items classified"


# Convenience function for testing
async def test_reasoning_agent():
    """Test the reasoning agent with mock data."""
    agent = KimiReasoningAgent()
    
    question = {
        "id": "test-123",
        "title": "Will there be a ceasefire in Gaza by March 31, 2026?"
    }
    
    articles = [
        {
            "title": "UN calls for immediate ceasefire in Gaza",
            "content": "The United Nations Security Council has passed a resolution calling for an immediate ceasefire...",
            "source": {"name": "Reuters"}
        },
        {
            "title": "Israel continues military operations in Gaza Strip",
            "content": "Israeli forces have expanded operations in southern Gaza despite international pressure...",
            "source": {"name": "Al Jazeera"}
        },
        {
            "title": "Hamas signals openness to new truce talks",
            "content": "Hamas leaders have indicated willingness to resume negotiations under certain conditions...",
            "source": {"name": "BBC"}
        }
    ]
    
    result = await agent.run_full_reasoning_pipeline(
        question=question,
        articles=articles,
        prior_probability=0.42,
        polymarket_price=0.45
    )
    
    print("\n" + "="*60)
    print("REASONING RESULT")
    print("="*60)
    print(f"Prior: {result['prior_probability']:.2f}")
    print(f"Posterior: {result['posterior_probability']:.2f}")
    print(f"Delta: {result['delta']:+.2f}")
    print(f"Confidence: {result['update_confidence']}")
    print(f"\nWTCMM: {result['what_would_change_my_mind']}")
    print(f"\nBull Case:\n{result['bull_case'][:300]}...")
    print(f"\nBear Case:\n{result['bear_case'][:300]}...")
    
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_reasoning_agent())

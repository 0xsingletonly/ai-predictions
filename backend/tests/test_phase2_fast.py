"""Fast Phase 2 Verification Tests - Consolidated into fewer API calls."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from src.agents.reasoning import KimiReasoningAgent


MOCK_ARTICLES = [
    {
        "title": "UN calls for immediate ceasefire in Gaza",
        "content": "The United Nations Security Council has passed a resolution calling for an immediate ceasefire in Gaza.",
        "source": {"name": "Reuters"}
    },
    {
        "title": "Israel continues military operations in Gaza Strip",
        "content": "Israeli forces have expanded operations in southern Gaza despite international pressure.",
        "source": {"name": "BBC"}
    },
    {
        "title": "Hamas signals openness to new truce talks",
        "content": "Hamas leaders have indicated willingness to resume negotiations under certain conditions.",
        "source": {"name": "Al Jazeera"}
    },
    {
        "title": "US brokers indirect talks between parties",
        "content": "American diplomats are facilitating back-channel communications between Israeli and Hamas representatives.",
        "source": {"name": "NYT"}
    },
    {
        "title": "Celebrity fashion trends this summer",
        "content": "The latest fashion trends from Hollywood celebrities include vintage styles...",
        "source": {"name": "Fashion Weekly"}
    }
]

MOCK_QUESTION = {
    "id": "test-gaza-ceasefire-123",
    "title": "Will there be a ceasefire in Gaza by March 31, 2026?",
}


async def run_consolidated_tests():
    """Run all Phase 2 tests in one go to minimize API calls."""
    print("\n" + "="*60)
    print("PHASE 2 CONSOLIDATED TESTS (LLM Reasoning Agent)")
    print("="*60)
    
    # Check API key
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        raise ValueError("KIMI_API_KEY not set in environment")
    
    agent = KimiReasoningAgent(api_key)
    
    # Run full pipeline once (covers P2-T1 through P2-T5)
    print("\nRunning full reasoning pipeline...")
    print("  (This makes 4 API calls: evidence + bull + bear + posterior)")
    
    result = await agent.run_full_reasoning_pipeline(
        question=MOCK_QUESTION,
        articles=MOCK_ARTICLES,
        prior_probability=0.42,
        polymarket_price=0.45
    )
    
    # Test Results
    results = {}
    
    # P2-T1: Evidence Classification
    print("\n=== P2-T1: Evidence Classification ===")
    evidence = result.get("evidence_classification", {})
    total_classified = (
        len(evidence.get("supports_yes", [])) +
        len(evidence.get("supports_no", [])) +
        len(evidence.get("neutral", [])) +
        len(evidence.get("noise", []))
    )
    print(f"  Total classified: {total_classified}")
    print(f"  Supports YES: {len(evidence.get('supports_yes', []))}")
    print(f"  Supports NO: {len(evidence.get('supports_no', []))}")
    
    if total_classified >= 3:
        print("  ✅ P2-T1 PASSED")
        results["P2-T1"] = True
    else:
        print("  ❌ P2-T1 FAILED")
        results["P2-T1"] = False
    
    # P2-T2: Bull/Bear Generation
    print("\n=== P2-T2: Bull/Bear Generation ===")
    bull_words = len(result.get("bull_case", "").split())
    bear_words = len(result.get("bear_case", "").split())
    print(f"  Bull case: {bull_words} words")
    print(f"  Bear case: {bear_words} words")
    
    bull_pass = bull_words >= 50
    bear_pass = bear_words >= 50
    
    if bull_pass and bear_pass:
        print("  ✅ P2-T2 PASSED")
        results["P2-T2"] = True
    else:
        if not bull_pass:
            print(f"  ❌ Bull case too short (< 50 words)")
        if not bear_pass:
            print(f"  ❌ Bear case too short (< 50 words)")
        results["P2-T2"] = False
    
    # P2-T3: Posterior Schema Validation
    print("\n=== P2-T3: Posterior Schema Validation ===")
    required_fields = [
        "question_id", "date", "prior_probability", "posterior_probability",
        "delta", "bull_case", "bear_case", "what_would_change_my_mind",
        "update_confidence", "reasoning_summary"
    ]
    missing = [f for f in required_fields if f not in result or result[f] is None]
    
    if not missing:
        print(f"  All {len(required_fields)} required fields present")
        print("  ✅ P2-T3 PASSED")
        results["P2-T3"] = True
    else:
        print(f"  Missing fields: {missing}")
        print("  ❌ P2-T3 FAILED")
        results["P2-T3"] = False
    
    # P2-T4: WTCMM Validation
    print("\n=== P2-T4: WTCMM Validation ===")
    wtcmm = result.get("what_would_change_my_mind", "")
    wtcmm_len = len(wtcmm)
    wtcmm_valid = wtcmm_len >= 20 and not wtcmm.lower().startswith("i would change")
    
    print(f"  WTCMM length: {wtcmm_len} chars")
    print(f"  WTCMM valid: {wtcmm_valid}")
    print(f"  WTCMM: {wtcmm[:80]}...")
    
    if wtcmm_valid:
        print("  ✅ P2-T4 PASSED")
        results["P2-T4"] = True
    else:
        print("  ❌ P2-T4 FAILED")
        results["P2-T4"] = False
    
    # P2-T5: Full Agent Run (already done)
    print("\n=== P2-T5: Full Agent Run ===")
    posterior = result.get("posterior_probability")
    prior = result.get("prior_probability")
    
    print(f"  Prior: {prior}")
    print(f"  Posterior: {posterior}")
    print(f"  Delta: {result.get('delta')}")
    print(f"  Confidence: {result.get('update_confidence')}")
    
    if posterior is not None and 0.05 <= posterior <= 0.95:
        print("  ✅ P2-T5 PASSED")
        results["P2-T5"] = True
    else:
        print("  ❌ P2-T5 FAILED")
        results["P2-T5"] = False
    
    # P2-T6: Malformed Response Handling (local test, no API)
    print("\n=== P2-T6: Malformed Response Handling ===")
    test_cases = [
        ('```json\n{"key": "value"}\n```', {"key": "value"}),
        ('{"key": "value"}', {"key": "value"}),
        ('Here is the result:\n{"key": "value"}\nDone!', {"key": "value"}),
        ('not json', None),
    ]
    
    passed = 0
    for input_text, expected in test_cases:
        parsed = agent._parse_json_response(input_text)
        if expected is None and "error" in parsed:
            passed += 1
        elif parsed.get("key") == expected.get("key"):
            passed += 1
    
    print(f"  Passed {passed}/{len(test_cases)} parsing tests")
    
    if passed >= 3:
        print("  ✅ P2-T6 PASSED")
        results["P2-T6"] = True
    else:
        print("  ❌ P2-T6 FAILED")
        results["P2-T6"] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for test_id, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_id}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL PHASE 2 TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_consolidated_tests())
    sys.exit(0 if success else 1)

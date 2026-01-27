#!/usr/bin/env python3
"""Test semantic category detection with LLM fallback"""

import asyncio
from app.core.orchestrator import RecommendationOrchestrator

async def test_semantic_category():
    orchestrator = RecommendationOrchestrator()
    
    test_cases = [
        "tôi muốn mua một thứ gì đó để uống",  # Should detect: nước ngọt or trà
        "tôi cần một loại đồ uống nóng",  # Should detect: trà
        "tôi muốn mua gì đó làm mát",  # Should detect: nước ngọt
        "tôi muốn mua những cái để tập luyện",  # Should detect: dụng cụ or giày
    ]
    
    print("Testing semantic category detection with LLM fallback:")
    print("=" * 60)
    
    for user_input in test_cases:
        print(f"\nUser: '{user_input}'")
        
        # Test keyword detection
        keyword_result = orchestrator.intent_detector._detect_category(user_input)
        print(f"  Keyword detection: {keyword_result.get('category')} (confidence: {keyword_result.get('confidence', 0):.2f})")
        
        # Test LLM detection if keyword fails
        if not keyword_result.get("category") or keyword_result.get("confidence", 0) < 0.5:
            print(f"  → Confidence too low, trying LLM...")
            llm_result = orchestrator._detect_category_with_llm(user_input)
            print(f"  LLM detection: {llm_result.get('category')} (confidence: {llm_result.get('confidence', 0):.2f})")
        
        print()

if __name__ == "__main__":
    asyncio.run(test_semantic_category())

#!/usr/bin/env python3
"""Test semantic extraction with attributes"""

import asyncio
from app.core.orchestrator import RecommendationOrchestrator

async def test():
    orch = RecommendationOrchestrator()
    
    test_inputs = [
        "tôi muốn mua nước ngọt cocacola",
        "tôi muốn mua giày chạy bộ nike",
        "tôi muốn mua cái gì đó để uống",
    ]
    
    print("Testing LLM semantic extraction with attributes:\n")
    
    for inp in test_inputs:
        result = orch._extract_category_from_input(inp)
        print(f"Input: '{inp}'")
        print(f"  Category: {result.get('category')}")
        print(f"  Attributes: {result.get('attributes')}")
        print(f"  Confidence: {result.get('confidence')}")
        print()

if __name__ == "__main__":
    asyncio.run(test())

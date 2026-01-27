#!/usr/bin/env python3
"""Test LLM suggestions with caching"""

from app.core.orchestrator import RecommendationOrchestrator

o = RecommendationOrchestrator()

# Test 1: Call LLM for suggestions
print("=" * 60)
print("TEST 1: First call - should hit LLM")
print("=" * 60)
result1 = o._detect_category_with_llm("tôi muốn mua gì đó để uống")
print(f"\nSuggestions: {result1.get('suggested_categories')}")
print(f"Best match: {result1.get('best_match')}")

# Test 2: Same input - should use cache
print("\n" + "=" * 60)
print("TEST 2: Second call - should use cache (no LLM call)")
print("=" * 60)
result2 = o._detect_category_with_llm("tôi muốn mua gì đó để uống")
print(f"\nSuggestions: {result2.get('suggested_categories')}")
print(f"Best match: {result2.get('best_match')}")
print(f"\nCache size: {len(o.llm_suggestion_cache)} items")

#!/usr/bin/env python3
"""
Test LLM API call - Monitor if OpenAI API is being called
"""
from app.core.intent_mapper import IntentMapper
import os

print("=" * 70)
print("Testing Intent Mapping with LLM API Call")
print("=" * 70)

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
print(f"\n✅ API Key loaded: {api_key[:30]}..." if api_key else "❌ No API key")

# Test input
test_input = "tôi đang không biết mua gì tặng bố vào dịp tết"
print(f"\nInput: '{test_input}'")

# Initialize mapper
mapper = IntentMapper()

print(f"\n{'='*70}")
print("CALLING INTENT MAPPER (will call OpenAI API if pattern fails)")
print(f"{'='*70}\n")

# This will show DEBUG output
result = mapper.map_intent(test_input)

print(f"\n{'='*70}")
print("RESULT")
print(f"{'='*70}")
print(f"Intent: {result.get('intent')}")
print(f"Categories: {result.get('categories')}")
print(f"Method: {result.get('method')}")
print(f"Confidence: {result.get('confidence'):.1%}")

if result.get('method') == 'llm':
    print("\n✅ SUCCESS: OpenAI API was called!")
    print("   LLM understood semantic meaning and mapped categories")
elif result.get('method') == 'pattern':
    print("\n✅ Pattern matched (no API call needed)")
else:
    print("\n⚠️ No intent detected")

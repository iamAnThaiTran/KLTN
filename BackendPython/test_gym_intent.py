#!/usr/bin/env python3
"""
Test intent mapping for: "tôi muốn mua hỗ trợ tập gym"
Analyze pattern matching vs LLM fallback
"""
from app.core.intent_mapper import IntentMapper
import os

print("=" * 80)
print("DETAILED INTENT ANALYSIS")
print("=" * 80)

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
print(f"\n✅ API Key: {api_key[:30]}..." if api_key else "❌ No API key")

test_input = "tôi muốn mua hỗ trợ tập gym"
print(f"\nUser Input: '{test_input}'")

# Initialize mapper
mapper = IntentMapper()

print(f"\n{'='*80}")
print("STEP 1: Check Pattern Matching")
print(f"{'='*80}\n")

# Check all patterns
test_input_lower = test_input.lower()
matched = False
import re

print("Checking patterns:")
for pattern, categories in mapper.intent_patterns.items():
    if re.search(pattern, test_input_lower):
        print(f"  ✅ MATCH: {pattern}")
        print(f"     → Categories: {categories}")
        matched = True
        break

if not matched:
    print("  ❌ NO PATTERN MATCHED")
    print(f"   Pattern check for keywords:")
    print(f"   - 'tập thể dục' in input? {('tập thể dục' in test_input_lower)}")
    print(f"   - 'tập gym' in input? {('tập gym' in test_input_lower)}")
    print(f"   - 'tập yoga' in input? {('tập yoga' in test_input_lower)}")
    print(f"   \n   → Will fallback to LLM")

print(f"\n{'='*80}")
print("STEP 2: CALLING INTENT MAPPER (may trigger LLM API)")
print(f"{'='*80}\n")

result = mapper.map_intent(test_input)

print(f"\n{'='*80}")
print("RESULT")
print(f"{'='*80}")
print(f"Intent: {result.get('intent')}")
print(f"Categories: {result.get('categories')}")
print(f"Method: {result.get('method')}")
print(f"Confidence: {result.get('confidence'):.1%}")

if result.get('method') == 'llm':
    print("\n✅ LLM FALLBACK WORKED!")
    print("   → OpenAI API was called")
    print("   → Semantic understanding applied")
    print("   → Smart categories mapped")
elif result.get('method') == 'pattern':
    print("\n✅ PATTERN MATCHED!")
    print("   → Fast regex match")
    print("   → No API call needed")
else:
    print("\n⚠️ NO MATCH")
    print("   → Generic question will be shown")

# Check what smart question would be generated
if result.get('intent') and result.get('categories'):
    print(f"\n{'='*80}")
    print("SMART QUESTION THAT WILL BE SHOWN")
    print(f"{'='*80}")
    fallback_q = mapper.get_fallback_question(
        result.get('intent'),
        result.get('categories')
    )
    print(f"\nQuestion: {fallback_q['question']}")
    print(f"Options: {[opt['label'] for opt in fallback_q['options']]}")

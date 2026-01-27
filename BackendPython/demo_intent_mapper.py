#!/usr/bin/env python3
"""
Simple test to demonstrate LLM-based intent mapping
Shows how system handles dynamic intents like "ấm áp" (warm)
"""

import os
import sys
sys.path.insert(0, '/Code/KLTN/BackendPython')

# Check if OpenAI key is set
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  WARNING: OPENAI_API_KEY not set!")
    print("   Add to .env file: OPENAI_API_KEY=sk-...")
    print("\nDemo mode: Showing hard-coded patterns only\n")

from app.core.intent_mapper import IntentMapper

def demo():
    mapper = IntentMapper()
    
    print("=" * 70)
    print("Intent Mapper - Pattern vs LLM Approach")
    print("=" * 70)
    
    # CASE 1: Hard-coded pattern (fast)
    print("\n📍 CASE 1: Hard-coded intent pattern")
    print("-" * 70)
    input_1 = "tôi muốn mua quà cho bạn gái"
    result_1 = mapper.map_intent(input_1)
    print(f"Input: '{input_1}'")
    print(f"Method: {result_1['method']} (fast regex matching)")
    print(f"Intent: {result_1['intent']}")
    print(f"Categories: {result_1['categories']}")
    print(f"Confidence: {result_1['confidence']:.1%}")
    
    # CASE 2: Dynamic semantic intent (needs LLM)
    print("\n📍 CASE 2: Dynamic semantic intent (needs LLM)")
    print("-" * 70)
    input_2 = "tôi muốn mua gì đó ấm áp"
    result_2 = mapper.map_intent(input_2)
    print(f"Input: '{input_2}'")
    print(f"Method: {result_2['method']}")
    if result_2['method'] == 'llm':
        print(f"Intent: {result_2['intent']} (detected by LLM semantic understanding)")
        print(f"Categories: {result_2['categories']}")
        print(f"Confidence: {result_2['confidence']:.1%}")
    else:
        print("⚠️  LLM not configured yet. Pattern matching failed.")
        print("   Add OPENAI_API_KEY to .env to enable this!")
    
    # CASE 3: Another dynamic case
    print("\n📍 CASE 3: Weather-based intent")
    print("-" * 70)
    input_3 = "chuẩn bị cho chuyến đi mưa"
    result_3 = mapper.map_intent(input_3)
    print(f"Input: '{input_3}'")
    print(f"Method: {result_3['method']}")
    if result_3['method'] == 'llm':
        print(f"Intent: {result_3['intent']}")
        print(f"Categories: {result_3['categories']}")
    else:
        print("⚠️  LLM not configured")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
✅ Hard-coded patterns (Fast, 0.9 confidence):
   - "quà cho bạn gái" → [áo, giày, mỹ phẩm, ...]
   - "để giải khát" → [nước, cà phê, trà, ...]
   - Works for common, predictable intents

✅ LLM fallback (Smart, 0.7 confidence):
   - "gì đó ấm áp" → [quần áo, nệm, gối] (semantic understanding)
   - "trời mưa" → [ba lô, giày, quần áo] (context aware)
   - Handles edge cases, dynamic intents
   - Requires: OPENAI_API_KEY in .env

🎯 Strategy:
   1. Try fast pattern matching first
   2. If no match, fallback to LLM semantic understanding
   3. User gets smart categories for ANY intent!
""")

if __name__ == "__main__":
    demo()

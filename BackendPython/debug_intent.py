#!/usr/bin/env python3
"""
Debug script - Check why intent detection fails for "tôi muốn mua gì đó ngọt ngào cho bạn gái"
"""

import sys
import os
sys.path.insert(0, '/Code/KLTN/BackendPython')

# Load .env
from dotenv import load_dotenv
load_dotenv()

from app.core.intent_mapper import IntentMapper

def test_intent():
    mapper = IntentMapper()
    
    test_input = "tôi muốn mua gì đó ngọt ngào cho bạn gái"
    
    print("=" * 70)
    print(f"Testing intent detection for: '{test_input}'")
    print("=" * 70)
    
    # Check 1: API Key loaded?
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"\n✅ OpenAI API Key loaded: {api_key[:30]}...")
    else:
        print(f"\n❌ OpenAI API Key NOT loaded!")
        print("   Check .env file!")
        return
    
    # Check 2: LLM fallback enabled?
    print(f"✅ LLM fallback enabled: {mapper.enable_llm_fallback}")
    
    # Check 3: Pattern matching
    print(f"\nStep 1: Try pattern matching...")
    for pattern in mapper.intent_patterns.keys():
        if pattern in str(mapper.intent_patterns.keys()):
            import re
            if re.search(pattern, test_input.lower()):
                print(f"  ✅ Pattern matched: {pattern}")
                break
    else:
        print(f"  ❌ No pattern matched")
        print(f"   Trying LLM fallback...")
    
    # Check 4: Full intent mapping
    print(f"\nStep 2: Full intent mapping call...")
    result = mapper.map_intent(test_input)
    
    print(f"\nResult:")
    print(f"  Intent: {result.get('intent')}")
    print(f"  Categories: {result.get('categories')}")
    print(f"  Confidence: {result.get('confidence')}")
    print(f"  Method: {result.get('method')}")
    
    if result['intent'] and result['categories']:
        print(f"\n✅ SUCCESS! Intent detected via {result['method']}")
        print(f"   Should ask smart question with these categories")
    else:
        print(f"\n❌ FAILED! No intent detected")
        print(f"   Will show generic question with all categories")
        print(f"   This is the problem!")

if __name__ == "__main__":
    test_intent()

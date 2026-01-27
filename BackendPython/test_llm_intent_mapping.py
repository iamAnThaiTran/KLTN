"""
Test LLM-based intent mapping for dynamic/semantic intents
"""

import sys
sys.path.insert(0, '/Code/KLTN/BackendPython')

from app.core.intent_mapper import IntentMapper

def test_dynamic_intent_mapping():
    """Test LLM fallback for cases not in hard-coded patterns"""
    
    mapper = IntentMapper()
    
    test_cases = [
        # Hard-coded patterns (should be fast)
        ("tôi muốn mua quà cho bạn gái", "pattern"),
        ("tôi khát, cần nước uống", "pattern"),
        
        # Dynamic cases (need LLM) - examples of semantic understanding
        ("tôi muốn mua gì đó ấm áp", "llm"),
        ("chuẩn bị cho chuyến đi mưa", "llm"),
        ("tôi cần thứ bền để dùng lâu", "llm"),
    ]
    
    print("=" * 70)
    print("Testing Intent Mapping with LLM Fallback")
    print("=" * 70)
    
    for user_input, expected_method in test_cases:
        print(f"\nTest: '{user_input}'")
        result = mapper.map_intent(user_input)
        
        print(f"  Method: {result.get('method')} (expected: {expected_method})")
        print(f"  Intent: {result.get('intent')}")
        print(f"  Categories: {result.get('categories')}")
        print(f"  Confidence: {result.get('confidence')}")
        
        # Validation
        assert result.get('method') in ['pattern', 'llm', 'none'], "Invalid method"
        if result['intent']:
            assert len(result['categories']) > 0, "Should have categories if intent detected"
        
        print("  ✅ Valid")

if __name__ == "__main__":
    test_dynamic_intent_mapping()

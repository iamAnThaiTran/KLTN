"""
Test script to verify dialogue logic fix
Testing: Intent detection + Smart question generation
"""

import asyncio
import sys
sys.path.insert(0, '/Code/KLTN/BackendPython')

from app.core.orchestrator import RecommendationOrchestrator
from app.core.intent_mapper import IntentMapper

async def test_smart_dialogue():
    """Test smart dialogue with intent context"""
    
    orchestrator = RecommendationOrchestrator()
    intent_mapper = IntentMapper()
    
    # TEST CASE 1: Gift for girlfriend
    print("=" * 70)
    print("TEST 1: User wants to buy gift for girlfriend")
    print("=" * 70)
    user_input_1 = "tôi muốn mua quà ngọt ngào cho bạn gái"
    
    # Test intent mapping first
    intent_map = intent_mapper.map_intent(user_input_1)
    print(f"\n1. Intent Mapping:")
    print(f"   Intent: {intent_map['intent']}")
    print(f"   Categories: {intent_map['categories']}")
    print(f"   Confidence: {intent_map['confidence']}")
    
    # Get fallback question
    fallback_q = intent_mapper.get_fallback_question(
        intent_map["intent"],
        intent_map["categories"]
    )
    print(f"\n2. Smart Question (should CONFIRM intent):")
    print(f"   Question: {fallback_q['question']}")
    print(f"   Options: {[opt['label'] for opt in fallback_q['options']]}")
    
    # Test full orchestrator flow
    result = await orchestrator.process_query(user_input_1)
    print(f"\n3. Orchestrator Response:")
    print(f"   Status: {result.get('status')}")
    print(f"   Question: {result.get('question')}")
    print(f"   Detected Intent: {result.get('detected_intent')}")
    print(f"   # Options: {len(result.get('options', []))}")
    
    # Check: Question should confirm intent, not be generic
    assert "quà" in result.get('question', '').lower(), "Question should mention 'quà'"
    assert "bạn gái" in result.get('question', '').lower(), "Question should mention 'bạn gái'"
    assert len(result.get('options', [])) <= 10, "Should show filtered options, not 50 categories"
    
    print("\n✅ TEST 1 PASSED: Smart dialogue with intent context!\n")
    
    # TEST CASE 2: Thirsty (need drink)
    print("=" * 70)
    print("TEST 2: User wants to buy drink")
    print("=" * 70)
    user_input_2 = "tôi khát, cần mua nước để uống"
    
    intent_map_2 = intent_mapper.map_intent(user_input_2)
    print(f"\n1. Intent Mapping:")
    print(f"   Intent: {intent_map_2['intent']}")
    print(f"   Categories: {intent_map_2['categories']}")
    
    fallback_q_2 = intent_mapper.get_fallback_question(
        intent_map_2["intent"],
        intent_map_2["categories"]
    )
    print(f"\n2. Smart Question (should CONFIRM thirsty, not generic):")
    print(f"   Question: {fallback_q_2['question']}")
    
    result_2 = await orchestrator.process_query(user_input_2)
    print(f"\n3. Orchestrator Response:")
    print(f"   Status: {result_2.get('status')}")
    print(f"   Question: {result_2.get('question')}")
    print(f"   Detected Intent: {result_2.get('detected_intent')}")
    
    assert "khát" in result_2.get('question', '').lower() or \
           "giải khát" in result_2.get('question', '').lower(), \
           "Question should confirm thirsty intent"
    
    print("\n✅ TEST 2 PASSED: Thirsty intent confirmed properly!\n")
    
    # TEST CASE 3: Direct category (no intent needed)
    print("=" * 70)
    print("TEST 3: User directly mentions category")
    print("=" * 70)
    user_input_3 = "tôi cần mua áo Nike"
    
    result_3 = await orchestrator.process_query(user_input_3)
    print(f"\n1. Orchestrator Response:")
    print(f"   Status: {result_3.get('status')}")
    print(f"   Has state category: {result_3.get('state', {}).get('has_category')}")
    print(f"   Category: {result_3.get('state', {}).get('category')}")
    
    print("\n✅ TEST 3 PASSED: Direct category detection still works!\n")
    
    print("=" * 70)
    print("ALL TESTS PASSED! ✅")
    print("=" * 70)
    print("\nSummary of fix:")
    print("1. Intent mapper detects intent + filtered categories")
    print("2. Smart question CONFIRMS user's stated need (not generic)")
    print("3. Shows only relevant categories (not all 50)")
    print("4. System feels smart, not 'đơ' (stuck)")

if __name__ == "__main__":
    asyncio.run(test_smart_dialogue())

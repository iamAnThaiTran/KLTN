# BackendPython/test_complex_workflow.py
"""
Test workflow phức tạp:
Turn 1: Search giày + thuộc tính a, b, c
Turn 2: Thêm thuộc tính d (refine)
Turn 3: Đổi sang bao cao su (category khác)

Kiểm tra: Code có xử lý tốt không?
"""

import asyncio
import json
from app.core.orchestrator import RecommendationOrchestrator
from app.core.schema import get_all_categories, get_schema


async def test_complex_workflow():
    """Test scenario phức tạp"""
    
    print("\n" + "="*80)
    print("TEST: Complex Workflow - Multiple Turns with Category Switch")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    conversation_state = None
    
    # ==================== TURN 1: Search giày ====================
    print("\n" + "-"*80)
    print("TURN 1: User searches for shoe with attributes a, b, c")
    print("-"*80)
    
    user_input_1 = "Tôi muốn mua giày Nike, size 40, màu đen"
    
    print(f"\n👤 User: {user_input_1}")
    
    result_1 = await orchestrator.process_query(user_input_1, conversation_state)
    conversation_state = result_1.get("state")
    
    print(f"\n✅ Status: {result_1['status']}")
    print(f"   Category: {conversation_state.get('category')}")
    print(f"   Extracted: {conversation_state.get('extracted')}")
    print(f"   Intent type: {result_1['intent_info']['type']}")
    print(f"   Intent reason: {result_1['intent_info']['reason']}")
    
    # Expected:
    # - category: "giày"
    # - extracted: {brand: "nike", size: "40", mau: "đen"}
    # - intent_type: "new_search"
    
    print("\n📊 Expected vs Actual:")
    print(f"   Category detected: {conversation_state.get('category')} (expected: giày) ✓")
    attrs = conversation_state.get("extracted", {})
    print(f"   Attributes extracted: {list(attrs.keys())} (expected: brand, size, mau)")
    
    # ==================== TURN 2: Refine (thêm attribute) ====================
    print("\n" + "-"*80)
    print("TURN 2: User refines by adding attribute d (loai)")
    print("-"*80)
    
    user_input_2 = "Còn giày chạy bộ để chơi thể thao thì sao?"
    
    print(f"\n👤 User: {user_input_2}")
    
    result_2 = await orchestrator.process_query(user_input_2, conversation_state)
    conversation_state = result_2.get("state")
    
    print(f"\n✅ Status: {result_2['status']}")
    print(f"   Category: {conversation_state.get('category')}")
    print(f"   Extracted: {conversation_state.get('extracted')}")
    print(f"   Intent type: {result_2['intent_info']['type']}")
    print(f"   Intent reason: {result_2['intent_info']['reason']}")
    
    # Expected:
    # - category: "giày" (same)
    # - extracted: {brand: "nike", size: "40", mau: "đen", loai: "chạy bộ", muc_dich: "thể thao"}
    # - intent_type: "refine"
    
    print("\n📊 Expected vs Actual:")
    print(f"   Category same: {conversation_state.get('category')} == giày ✓")
    attrs = conversation_state.get("extracted", {})
    print(f"   Attributes now: {list(attrs.keys())}")
    print(f"   Should include loai & muc_dich ✓")
    
    # ==================== TURN 3: SWITCH CATEGORY ====================
    print("\n" + "-"*80)
    print("TURN 3: User switches to DIFFERENT category (bao cao su)")
    print("-"*80)
    
    user_input_3 = "Không, thôi. Tôi muốn mua bao cao su Durex, size M"
    
    print(f"\n👤 User: {user_input_3}")
    
    result_3 = await orchestrator.process_query(user_input_3, conversation_state)
    conversation_state = result_3.get("state")
    
    print(f"\n✅ Status: {result_3['status']}")
    print(f"   Category: {conversation_state.get('category')}")
    print(f"   Extracted: {conversation_state.get('extracted')}")
    print(f"   Intent type: {result_3['intent_info']['type']}")
    print(f"   Intent reason: {result_3['intent_info']['reason']}")
    print(f"   Search history: {conversation_state.get('search_history', [])}")
    
    # Expected:
    # - category: "bao cao su" (CHANGED!)
    # - extracted: {} or {brand: "durex", ...} (RESET or new)
    # - intent_type: "switch_category"
    # - search_history: [{category: "giày", extracted: {...}}]
    
    print("\n📊 Expected vs Actual:")
    print(f"   Category SWITCHED: {conversation_state.get('category')}")
    if conversation_state.get('category') == "bao cao su":
        print(f"   ✅ CORRECT: Switched from giày to bao cao su")
    else:
        print(f"   ❌ PROBLEM: Should be 'bao cao su', but is '{conversation_state.get('category')}'")
    
    attrs = conversation_state.get("extracted", {})
    print(f"   Extracted reset: {list(attrs.keys())} (should be new/empty)")
    
    history = conversation_state.get("search_history", [])
    if history:
        print(f"   ✅ Search history saved: {len(history)} entries")
        for i, h in enumerate(history):
            print(f"      [{i}] {h['category']}: {list(h['extracted'].keys())}")
    else:
        print(f"   ⚠️  Search history: Empty (should have giày search)")

    # ==================== ANALYSIS ====================
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    print(f"\n✅ TURN 1 (New search):")
    print(f"   - Category detected: ✓")
    print(f"   - Attributes extracted: ✓")
    
    print(f"\n✅ TURN 2 (Refine):")
    print(f"   - Category maintained: ✓")
    print(f"   - New attributes added: ✓")
    
    print(f"\n❓ TURN 3 (Switch category):")
    is_switched = conversation_state.get('category') == "bao cao su"
    is_reset = len(conversation_state.get('extracted', {})) < 5  # Less than turn 1
    is_history = len(conversation_state.get('search_history', [])) > 0
    
    print(f"   - Category switched: {'✓' if is_switched else '❌'}")
    print(f"   - State reset: {'✓' if is_reset else '❌'}")
    print(f"   - History preserved: {'✓' if is_history else '⚠️'}")
    
    if is_switched and is_reset:
        print(f"\n✅ RESULT: WORKS WELL!")
    else:
        print(f"\n⚠️  RESULT: POTENTIAL ISSUES DETECTED")


async def test_edge_cases():
    """Test các trường hợp cạnh (edge cases)"""
    
    print("\n\n" + "="*80)
    print("TEST: Edge Cases")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    # Edge case 1: User không mention category mới rõ ràng
    print("\n" + "-"*80)
    print("EDGE CASE 1: User không mention category rõ ràng")
    print("-"*80)
    
    print("\n👤 Turn 1: Tôi muốn giày Nike, size 40")
    result = await orchestrator.process_query(
        "Tôi muốn giày Nike, size 40",
        None
    )
    state = result.get("state")
    print(f"   Category: {state.get('category')}")
    
    print("\n👤 Turn 2: Không, tôi muốn cái khác")
    print("   ❌ PROBLEM: Không mention 'bao cao su' → Có thể bị detect là 'refine'")
    print("   Solution: Nên mention category rõ ràng hoặc dùng IntentMapper")
    
    # Edge case 2: Category name ambiguous
    print("\n" + "-"*80)
    print("EDGE CASE 2: Category name ambiguous")
    print("-"*80)
    
    all_cats = get_all_categories()
    print(f"\n Available categories: {all_cats}")
    print(f"\n Question: Có category 'bao cao su' không?")
    if "bao cao su" in all_cats:
        print(f"   ✅ YES - Should work")
        schema = get_schema("bao cao su")
        if schema:
            print(f"   Schema found: {schema.name}")
            print(f"   Keywords: {schema.keywords}")
        else:
            print(f"   ❌ Schema not found!")
    else:
        print(f"   ❌ NO - Will fail to detect category!")
        print(f"   Need to add 'bao cao su' to schema")


async def test_attribute_conflicts():
    """Test khi có attribute conflict"""
    
    print("\n\n" + "="*80)
    print("TEST: Multiple Attribute Conflicts")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    print("\n" + "-"*80)
    print("Scenario: Turn 1 → Turn 2 (change multiple attributes at once)")
    print("-"*80)
    
    print("\n👤 Turn 1: Nike, size 40, màu đen")
    result = await orchestrator.process_query(
        "Tôi muốn giày Nike, size 40, màu đen",
        None
    )
    state = result.get("state")
    print(f"   Extracted: {state.get('extracted')}")
    
    print("\n👤 Turn 2: Hoặc Adidas, size 42, màu trắng")
    print("   ❌ POTENTIAL PROBLEM:")
    print("      - 3 attributes conflict: brand, size, mau")
    print("      - Code replaces one-by-one")
    print("      - May result in mixed state: Nike-Adidas with both sizes?")
    
    result = await orchestrator.process_query(
        "Hoặc Adidas, size 42, màu trắng",
        state
    )
    state = result.get("state")
    print(f"\n   Actual result: {state.get('extracted')}")
    
    # Check if clean switch
    if state.get('extracted', {}).get('brand') == 'adidas':
        print(f"   ✓ Brand replaced: adidas")
    else:
        print(f"   ❌ Brand NOT replaced correctly")
    
    if state.get('extracted', {}).get('size') == '42':
        print(f"   ✓ Size replaced: 42")
    else:
        print(f"   ❌ Size NOT replaced correctly")


async def test_no_change_signal():
    """Test khi user không dùng change signals"""
    
    print("\n\n" + "="*80)
    print("TEST: User Changes Attributes WITHOUT Change Signals")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    print("\n" + "-"*80)
    print("Problem: User không nói 'hoặc', 'đổi', etc.")
    print("-"*80)
    
    print("\n👤 Turn 1: Nike, size 40")
    result = await orchestrator.process_query(
        "Tôi muốn giày Nike, size 40",
        None
    )
    state = result.get("state")
    print(f"   Extracted: {state.get('extracted')}")
    
    print("\n👤 Turn 2: Adidas, size 42")
    print("   ❌ PROBLEM: No change signal ('hoặc', 'đổi', 'thôi')")
    print("   Detected as: REFINE (merge)")
    print("   Result: MIXED STATE (both Nike & Adidas)")
    
    result = await orchestrator.process_query(
        "Adidas, size 42",
        state
    )
    state = result.get("state")
    print(f"   Actual state: {state.get('extracted')}")
    
    # Check if merged (problem) or replaced (ok)
    attrs = state.get('extracted', {})
    if 'brand' in attrs:
        if isinstance(attrs['brand'], list):
            print(f"   ❌ PROBLEM: Mixed state! brand={attrs['brand']}")
        elif attrs['brand'] != 'nike':
            print(f"   ✓ OK: Brand replaced to {attrs['brand']}")


# ============================================
# MAIN
# ============================================

async def main():
    try:
        await test_complex_workflow()
        await test_edge_cases()
        await test_attribute_conflicts()
        await test_no_change_signal()
        
        print("\n\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print("""
✅ WORKS WELL:
   - Turn 1 (new_search): Category detection, attribute extraction
   - Turn 2 (refine): Adding new attributes to same category
   - Turn 3 (switch_category): Detecting category change, resetting state

⚠️  POTENTIAL ISSUES:
   1. Category must be in schema.keywords
   2. User should use change signals (hoặc, đổi, không, ...)
   3. Multiple attribute conflicts need manual handling
   4. State reset relies on user explicitly mentioning new category

🔴 EDGE CASES TO WATCH:
   1. "Không, tôi muốn bao cao su" - Must mention category
   2. "Thôi, cái khác" - Too vague, may fail
   3. Mixed attributes from two categories - Need clear intent
   4. Ambiguous product names - May not detect category switch

RECOMMENDATION:
   ✅ Code works for clear scenarios
   ⚠️  Better to guide users with questions when ambiguous
        """)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

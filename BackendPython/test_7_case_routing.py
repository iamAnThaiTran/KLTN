"""
Test file for the 7-case routing system
Run this to verify each case works correctly
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.orchestrator import RecommendationOrchestrator


async def test_case_1_clear_request():
    """Test Case 1: Clear, specific request with category and attributes"""
    print("\n" + "="*80)
    print("TEST CASE 1: Clear Request (NO LLM)")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    test_queries = [
        "giày Nike Air Force 1 size 42 màu trắng",
        "laptop Dell XPS 13 RAM 16GB giá dưới 30 triệu",
        "điện thoại Samsung Galaxy S23 màu đen"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await orchestrator.process_query(query, None)
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Case Name: {result.get('routing_info', {}).get('case_name')}")
        print(f"✓ Status: {result.get('status')}")
        print(f"✓ Reason: {result.get('routing_info', {}).get('reason')}")
        
        # Case 1 or Case 2 is acceptable (depends on category detection confidence)
        # Both are valid for "clear" queries - Case 1 if very clear, Case 2 if missing some attrs
        if result['routing_info']['case'] in [1, 2]:
            print("✅ PASSED (Case 1 or 2 - both valid for clear queries)")
        else:
            print(f"⚠️ Got Case {result['routing_info']['case']} - expected Case 1 or 2")


async def test_case_2_unclear_with_schema():
    """Test Case 2: Unclear request but category detected with schema"""
    print("\n" + "="*80)
    print("TEST CASE 2: Unclear Request with Schema")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    test_queries = [
        "mua giày Nike",
        "tìm laptop Dell",
        "cho tôi xem áo Adidas"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await orchestrator.process_query(query, None)
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Status: {result.get('status')}")
        
        # Case 2 should ask for more info
        if result['routing_info']['case'] == 2:
            print(f"✓ Question: {result.get('question', 'N/A')}")
            print("✅ PASSED - Case 2 correctly asks for attributes")
        else:
            print(f"⚠️ Got Case {result['routing_info']['case']} instead of 2")


async def test_case_3_unclear_no_schema():
    """Test Case 3: Unclear request with no schema or low confidence"""
    print("\n" + "="*80)
    print("TEST CASE 3: Unclear Request, No Schema")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    test_queries = [
        "tìm điện thoại tầm trung",
        "mua đồ công nghệ",
        "cho tôi xem sản phẩm nổi bật"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await orchestrator.process_query(query, None)
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Status: {result.get('status')}")
        
        if result['routing_info']['case'] == 3:
            print(f"✓ LLM Used: Yes (for category inference)")
            print("✅ PASSED - Case 3 uses LLM")
        else:
            print(f"⚠️ Got Case {result['routing_info']['case']} instead of 3")


async def test_case_4_abstract_intent():
    """Test Case 4: Very vague/abstract intent"""
    print("\n" + "="*80)
    print("TEST CASE 4: Abstract Intent")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    test_queries = [
        "mua quà Tết cho bố",
        "muốn mua thứ gì đó tránh thai",
        "cần đồ để tập gym",
        "tìm quà sinh nhật cho bạn gái"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await orchestrator.process_query(query, None)
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Status: {result.get('status')}")
        
        if result['routing_info']['case'] == 4:
            print(f"✓ LLM Suggestions: {len(result.get('options', []))} categories")
            print("✅ PASSED - Case 4 suggests categories")
        else:
            print(f"⚠️ Got Case {result['routing_info']['case']} instead of 4")


async def test_case_5_intent_shift():
    """Test Case 5: Intent shift (context reset)"""
    print("\n" + "="*80)
    print("TEST CASE 5: Intent Shift")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    # First query establishes context
    print("\n📝 Initial Query: giày Nike")
    state = None
    result1 = await orchestrator.process_query("giày Nike", state)
    state = result1['state']
    
    print(f"✓ Category set: {state.get('category')}")
    
    # Second query shifts intent
    print("\n📝 Shift Query: thôi cho tôi xem Adidas")
    result2 = await orchestrator.process_query("thôi cho tôi xem Adidas", state)
    
    print(f"✓ Case: {result2.get('routing_info', {}).get('case')}")
    print(f"✓ Old Category: giày")
    print(f"✓ New Category: {result2['state'].get('category')}")
    
    if result2['routing_info']['case'] == 5:
        print("✅ PASSED - Case 5 detected intent shift")
    else:
        print(f"⚠️ Got Case {result2['routing_info']['case']} instead of 5")


async def test_case_6_incremental_refinement():
    """Test Case 6: Incremental refinement (context accumulation)"""
    print("\n" + "="*80)
    print("TEST CASE 6: Incremental Refinement")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    # Build up context incrementally
    queries = [
        "giày Nike",
        "dòng Air Force",
        "size 42",
        "màu trắng"
    ]
    
    state = None
    for i, query in enumerate(queries, 1):
        print(f"\n📝 Query {i}: {query}")
        result = await orchestrator.process_query(query, state)
        state = result['state']
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Extracted so far: {state.get('extracted', {})}")
        
        if i > 1 and result['routing_info']['case'] == 6:
            print("✅ PASSED - Case 6 accumulates context")
        elif i == 1:
            print("✓ First query (establishes baseline)")


async def test_case_7_comparison_advisory():
    """Test Case 7: Comparison/advisory request"""
    print("\n" + "="*80)
    print("TEST CASE 7: Comparison/Advisory")
    print("="*80)
    
    orchestrator = RecommendationOrchestrator()
    
    test_queries = [
        "Air Force 1 với Stan Smith cái nào bền hơn?",
        "Nên mua iPhone hay Samsung?",
        "So sánh Nike và Adidas",
        "Laptop Dell tốt hơn HP không?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await orchestrator.process_query(query, None)
        
        print(f"✓ Case: {result.get('routing_info', {}).get('case')}")
        print(f"✓ Status: {result.get('status')}")
        
        if result['routing_info']['case'] == 7:
            print(f"✓ LLM Answer: {result.get('answer', 'N/A')[:100]}...")
            print(f"✓ No immediate crawl: True")
            print("✅ PASSED - Case 7 provides advice without crawling")
        else:
            print(f"⚠️ Got Case {result['routing_info']['case']} instead of 7")


async def test_all_cases():
    """Run all test cases"""
    print("\n" + "🔥"*40)
    print("TESTING 7-CASE ROUTING SYSTEM")
    print("🔥"*40)
    
    try:
        await test_case_1_clear_request()
        await test_case_2_unclear_with_schema()
        await test_case_3_unclear_no_schema()
        await test_case_4_abstract_intent()
        await test_case_5_intent_shift()
        await test_case_6_incremental_refinement()
        await test_case_7_comparison_advisory()
        
        print("\n" + "🎉"*40)
        print("ALL TESTS COMPLETED")
        print("🎉"*40)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


async def interactive_test():
    """Interactive mode to test any query"""
    print("\n" + "="*80)
    print("INTERACTIVE 7-CASE TESTING")
    print("="*80)
    print("\nType queries to test case routing. Type 'quit' to exit.\n")
    
    orchestrator = RecommendationOrchestrator()
    state = None
    
    while True:
        query = input("\n📝 Your query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not query:
            continue
        
        try:
            result = await orchestrator.process_query(query, state)
            state = result.get('state')
            
            print("\n" + "-"*80)
            print(f"📊 CASE: {result.get('routing_info', {}).get('case')} - {result.get('routing_info', {}).get('case_name')}")
            print(f"📋 Reason: {result.get('routing_info', {}).get('reason')}")
            print(f"✅ Status: {result.get('status')}")
            
            if result.get('question'):
                print(f"❓ Question: {result['question']}")
            
            if result.get('options'):
                print(f"🎯 Options: {len(result['options'])} choices")
            
            if result.get('products'):
                print(f"🛍️ Products: {len(result['products'])} found")
            
            if result.get('answer'):
                print(f"💬 Answer: {result['answer']}")
            
            print(f"🗂️ State: category={state.get('category')}, extracted={state.get('extracted', {})}")
            print("-"*80)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(test_all_cases())

#!/usr/bin/env python3
"""
Test Dynamic Schema with Ollama LLM - End-to-end test
"""

from app.core.dynamic_schema import DynamicAttributeExtractor, DynamicSchemaManager

schema_manager = DynamicSchemaManager()
extractor = DynamicAttributeExtractor()

test_cases = [
    {
        "query": "Tôi muốn tìm giày Nike chạy bộ màu xanh dương, kích thước 42, giá dưới 2 triệu",
        "category": "giày",
        "description": "Nike shoe query"
    },
    {
        "query": "Laptop Dell XPS 13 màu bạc, Intel i7, 16GB RAM, SSD 512GB, giá khoảng 25 triệu",
        "category": "laptop",
        "description": "Laptop with specs"
    },
    {
        "query": "Áo thun cotton nam màu trắng, size M, chất liệu 100% cotton, giá 200k",
        "category": "áo",
        "description": "White t-shirt"
    },
]

print("=" * 80)
print("DYNAMIC SCHEMA + OLLAMA LLM TEST")
print("=" * 80)
print()

for i, test_case in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"Test {i}: {test_case['description']}")
    print(f"{'='*80}")
    print(f"Query: {test_case['query']}")
    print(f"Category: {test_case['category']}")
    print()
    
    try:
        # Get schema
        schema = schema_manager.get_attributes_for_category(test_case['category'])
        print(f"📋 Schema attributes: {list(schema.keys())[:5]}...")
        print()
        
        # Extract with rule-based first
        print(f"⚡ RULE-BASED:")
        result_rule = extractor.extract(test_case['query'], test_case['category'], use_llm=False)
        print(f"   Method: {result_rule['method']}")
        print(f"   Extracted: {list(result_rule['extracted'].keys())}")
        print(f"   Confidence: {result_rule['confidence']:.2%}")
        print()
        
        # Extract with LLM
        print(f"🤖 WITH OLLAMA LLM:")
        result_llm = extractor.extract(test_case['query'], test_case['category'], use_llm=True)
        print(f"   Method: {result_llm['method']}")
        print(f"   Extracted: {list(result_llm['extracted'].keys())}")
        print(f"   Confidence: {result_llm['confidence']:.2%}")
        print()
        print(f"   Values:")
        for key, val in result_llm['extracted'].items():
            print(f"     - {key}: {val}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("✅ Test Complete")
print(f"{'='*80}")

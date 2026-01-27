#!/usr/bin/env python3
"""
Test LLM generation with mock responses - See what the LLM would generate
"""

import sys
import json
from app.core.dynamic_schema import DynamicAttributeExtractor, DynamicSchemaManager

# Initialize components
schema_manager = DynamicSchemaManager()
extractor = DynamicAttributeExtractor()

test_cases = [
    {
        "query": "Tôi muốn tìm giày Nike chạy bộ màu xanh dương, kích thước 42, giá dưới 2 triệu",
        "category": "giày",
        "description": "Nike shoe - blue, size 42, under 2M"
    },
    {
        "query": "Laptop Dell XPS 13 màu bạc, Intel i7, 16GB RAM, SSD 512GB, giá khoảng 25 triệu",
        "category": "laptop",
        "description": "Dell laptop - i7, 16GB RAM, 512GB SSD, ~25M"
    },
    {
        "query": "Áo thun cotton nam màu trắng, size M, chất liệu 100% cotton, giá 200k",
        "category": "áo",
        "description": "White t-shirt, size M, 100% cotton, 200k"
    },
    {
        "query": "iPhone 15 Pro Max màu gold, 256GB, 5G, camera 48MP",
        "category": "điện thoại",
        "description": "iPhone 15 Pro Max - gold, 256GB, camera 48MP"
    },
    {
        "query": "Mì tôm Omachi chua cay, gói 30 grams, giá 5k",
        "category": "mì tôm",
        "description": "Spicy instant noodles, 30g, 5k"
    },
]

print("=" * 80)
print("LLM GENERATION TEST - Rule-based vs Mock LLM")
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
        # Get schema for this category
        schema = schema_manager.get_attributes_for_category(test_case['category'])
        print(f"📋 Schema for '{test_case['category']}':")
        attrs_list = list(schema.keys())
        print(f"   Available attributes: {', '.join(attrs_list[:5])}{', ...' if len(attrs_list) > 5 else ''}")
        print()
        
        # Extract using rule-based first
        print(f"⚡ RULE-BASED EXTRACTION:")
        result_rule = extractor.extract(test_case['query'], test_case['category'], use_llm=False)
        print(f"   Method: {result_rule['method']}")
        print(f"   Confidence: {result_rule['confidence']:.2%}")
        
        if result_rule['extracted']:
            print(f"   Extracted: {result_rule['extracted']}")
        else:
            print(f"   Extracted: (none)")
        
        print()
        
        # Now with LLM fallback
        print(f"🤖 WITH LLM FALLBACK:")
        result_llm = extractor.extract(test_case['query'], test_case['category'], use_llm=True)
        print(f"   Method: {result_llm['method']}")
        print(f"   Confidence: {result_llm['confidence']:.2%}")
        
        if result_llm['extracted']:
            print(f"   Extracted: {result_llm['extracted']}")
        else:
            print(f"   Extracted: (none)")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("✅ Test Complete")
print(f"{'='*80}")
print()
print("📝 Notes:")
print("   • Rule-based = Regex patterns for brand, color, size, price, RAM, storage, CPU")
print("   • LLM fallback = Uses Qwen, Claude, or OpenAI when rule-based < 2 attributes")
print("   • Current setup: LLM disabled due to no API available (requires Qwen/OpenAI/Claude)")

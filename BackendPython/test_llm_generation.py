#!/usr/bin/env python3
"""
Test LLM generation output - See what the LLM generates for attribute extraction
"""

import sys
import json
from app.core.dynamic_schema import DynamicAttributeExtractor, DynamicSchemaManager, DynamicCategoryDetector

# Initialize components
schema_manager = DynamicSchemaManager()
detector = DynamicCategoryDetector()
extractor = DynamicAttributeExtractor()  # Will use LLM when needed

test_cases = [
    {
        "query": "Tôi muốn tìm giày Nike chạy bộ màu xanh dương, kích thước 42, giá dưới 2 triệu",
        "category": "giày",
        "description": "Shoe query in Vietnamese"
    },
    {
        "query": "Laptop Dell XPS 13 màu bạc, Intel i7, 16GB RAM, SSD 512GB, giá khoảng 25 triệu",
        "category": "laptop",
        "description": "Laptop query with specs"
    },
    {
        "query": "Áo thun cotton nam màu trắng, size M, chất liệu 100% cotton, giá 200k",
        "category": "áo",
        "description": "T-shirt query"
    },
    {
        "query": "Nước hoa Chanel No.5, hương hoa, dung tích 50ml, giá 3 triệu",
        "category": "nước hoa",
        "description": "Perfume query"
    },
    {
        "query": "Bao cao su Durex Extra Safe, hộp 10 cái, an toàn cao",
        "category": "bao cao su",
        "description": "Condom query"
    },
]

print("=" * 80)
print("LLM GENERATION TEST - Seeing what LLM generates")
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
        print(f"📋 Schema attributes for '{test_case['category']}':")
        for attr_name, attr_constraint in schema.items():
            print(f"   • {attr_name}: {attr_constraint}")
        print()
        
        # Extract using LLM (forced)
        print(f"🤖 Calling LLM to extract attributes...")
        result = extractor.extract(test_case['query'], test_case['category'], use_llm=True)
        
        print(f"\n📊 LLM EXTRACTION RESULT:")
        print(f"   Method: {result['method']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print()
        
        print(f"✨ Extracted Attributes:")
        if result['extracted']:
            for key, value in result['extracted'].items():
                print(f"   • {key}: {value}")
        else:
            print(f"   (No attributes extracted)")
        
        if result['missing_required']:
            print()
            print(f"⚠️  Missing Required:")
            for attr in result['missing_required']:
                print(f"   • {attr}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("✅ LLM Generation Test Complete")
print(f"{'='*80}")

#!/usr/bin/env python3
"""
Test Ollama LLM with simple input like 'mì tôm'
"""

from app.core.llm_utils import call_ollama
from app.core.dynamic_schema import DynamicCategoryDetector, DynamicSchemaManager, DynamicAttributeExtractor

detector = DynamicCategoryDetector()
schema_manager = DynamicSchemaManager()
extractor = DynamicAttributeExtractor()

test_inputs = [
    "mì tôm",
    "giày",
    "laptop",
    "áo",
    "bao cao su",
    "nước hoa",
    "điện thoại",
    "sách",
]

print("=" * 80)
print("TEST: Simple input + Ollama LLM generation")
print("=" * 80)
print()

for input_text in test_inputs:
    print(f"\n{'='*80}")
    print(f"Input: '{input_text}'")
    print(f"{'='*80}")
    
    # Step 1: Detect category
    category, confidence = detector.detect_category(input_text)
    print(f"📂 Category Detection: {category} ({confidence:.0%})")
    print()
    
    if category:
        cat = category
        
        # Step 2: Get schema for this category
        schema = schema_manager.get_attributes_for_category(cat)
        print(f"📋 Available attributes: {list(schema.keys())}")
        print()
        
        # Step 3: Try extraction with LLM
        print(f"🤖 Calling Ollama to extract from just '{input_text}'...")
        result = extractor.extract(input_text, cat, use_llm=True)
        
        print(f"   Method: {result['method']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        
        if result['extracted']:
            print(f"   Extracted attributes:")
            for key, val in result['extracted'].items():
                print(f"     • {key}: {val}")
        else:
            print(f"   Extracted: (none)")
    else:
        print(f"❌ Category NOT detected for '{input_text}'")
        print(f"   (Add to UNIVERSAL_KEYWORDS if you want to support it)")

print(f"\n{'='*80}")
print("✅ Test Complete")
print(f"{'='*80}")

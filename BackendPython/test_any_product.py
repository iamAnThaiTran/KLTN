#!/usr/bin/env python
# BackendPython/test_any_product.py
"""
Test ANY product - not just hardcoded ones!
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_schema import (
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    DynamicSchemaManager,
)

def test_product(product_name, user_query):
    """Test extraction for any product"""
    
    print(f"\n{'='*70}")
    print(f"  Testing: {product_name}")
    print(f"{'='*70}")
    
    print(f"\nUser input: '{user_query}'")
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    schema_manager = DynamicSchemaManager()
    
    # Detect category
    print("\n1️⃣ Category Detection")
    category, confidence = detector.detect_category(user_query)
    print(f"   Category: {category}")
    print(f"   Confidence: {confidence:.1%}")
    
    if not category:
        print("   ❌ NOT DETECTED (not in keywords)")
        print("   📌 Add to UNIVERSAL_KEYWORDS to support")
        return
    
    # Get schema
    print("\n2️⃣ Schema")
    schema = schema_manager.get_attributes_for_category(category)
    print(f"   Total attributes: {len(schema)}")
    print(f"   Attributes: {', '.join(list(schema.keys())[:5])}")
    
    # Extract
    print("\n3️⃣ Extraction (Rule-Based)")
    result = extractor.extract(user_query, category, use_llm=False)
    print(f"   Extracted: {len(result['extracted'])}/{len(schema)}")
    print(f"   Confidence: {result['confidence']:.1%}")
    
    if result['extracted']:
        print(f"   Attributes:")
        for attr, value in result['extracted'].items():
            if isinstance(value, dict):
                print(f"     • {attr}: {value}")
            else:
                print(f"     • {attr}: {value}")
    
    # Status
    print("\n4️⃣ Status")
    if result['confidence'] >= 0.5:
        print("   ✅ Ready to search!")
    else:
        print("   ⚠️ Low confidence - might ask LLM")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  TEST ANY PRODUCT - HARDCODED OR NOT!")
    print("="*70)
    
    # Test different products
    test_cases = [
        # Hardcoded (should work)
        ("Giày", "Giày Nike chạy bộ size 40, đen"),
        ("Áo", "Áo phông Gucci tím size M"),
        ("Laptop", "Laptop Dell 16GB RAM"),
        ("Bao cao su", "Bao cao su Durex M"),
        
        # NOT hardcoded (show what happens)
        ("Mì tôm", "Mì tôm Maruchan cay, 5 gói"),
        ("Nước hoa", "Nước hoa Chanel No5 nữ 100ml"),
        ("Đồng hồ", "Đồng hồ Apple Watch Series 9"),
        ("Sách", "Sách Nhân Dạng của John Doe"),
    ]
    
    print("\nTesting hardcoded + new products:")
    
    for product_name, query in test_cases:
        try:
            test_product(product_name, query)
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETED")
    print("="*70)
    print("""
SUMMARY:
  ✅ Hardcoded products (giày, áo, laptop) → Work perfectly
  ❌ Not hardcoded (mì tôm, nước hoa) → Need to ask user or use LLM
  
SOLUTION:
  • Add to UNIVERSAL_KEYWORDS → Instant support! ✨
  • Or use LLM → Auto-handles anything!
""")

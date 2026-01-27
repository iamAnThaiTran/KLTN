#!/usr/bin/env python
# BackendPython/demo_full_flow.py
"""
Demo complete flow: Category Detection → Attribute Extraction → Filter Application
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_schema import (
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    DynamicSchemaManager,
)

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_step(num, title):
    print(f"\n{'─'*80}")
    print(f"STEP {num}: {title}")
    print(f"{'─'*80}")

def demo_flow(user_input):
    """Complete flow demo"""
    
    print_header(f"USER INPUT: {user_input}")
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    schema_manager = DynamicSchemaManager()
    
    # =========== STEP 1: DETECT CATEGORY ===========
    print_step(1, "Detect Product Category")
    
    category, confidence = detector.detect_category(user_input)
    
    print(f"Input: {user_input}")
    print(f"Detected category: {category}")
    print(f"Confidence: {confidence:.1%}")
    
    if not category:
        print("❌ Could not detect category!")
        return
    
    # =========== STEP 2: GET SCHEMA ===========
    print_step(2, "Get Product Schema for Category")
    
    schema = schema_manager.get_attributes_for_category(category)
    
    print(f"Category '{category}' has {len(schema)} possible attributes:")
    for i, (attr_name, constraint) in enumerate(schema.items()):
        if i < 10:
            print(f"  • {attr_name}: {constraint.type}")
    if len(schema) > 10:
        print(f"  ... and {len(schema) - 10} more")
    
    # =========== STEP 3: EXTRACT FILTERS/ATTRIBUTES ===========
    print_step(3, "Extract Filters/Attributes")
    
    result = extractor.extract(user_input, category, use_llm=False)
    
    print(f"Extraction method: {result['method']}")
    print(f"Overall confidence: {result['confidence']:.1%}")
    print(f"\nExtracted filters/attributes:")
    
    if result['extracted']:
        for attr_name, value in result['extracted'].items():
            if isinstance(value, dict):
                # Price range
                print(f"  ✅ {attr_name}: {value}")
            else:
                print(f"  ✅ {attr_name}: {value}")
    else:
        print("  (No attributes extracted)")
    
    # =========== STEP 4: APPLY FILTERS ===========
    print_step(4, "Filter Application (for search)")
    
    print(f"Using {len(result['extracted'])} filters for search:")
    filters = {}
    
    for attr_name, value in result['extracted'].items():
        if isinstance(value, dict):
            # Range filter
            filters[attr_name] = {
                "type": "range",
                "value": value
            }
            print(f"  🔍 {attr_name}: range {value['min']} - {value['max']}")
        else:
            # Enum filter
            filters[attr_name] = {
                "type": "enum",
                "value": value
            }
            print(f"  🔍 {attr_name}: equals '{value}'")
    
    # =========== SUMMARY ===========
    print_step(5, "Summary")
    
    print(f"""
Category:     {category}
Filters:      {len(filters)} applied
Confidence:   {result['confidence']:.1%}
Method:       {result['method']}

Next step: Use filters to search Lazada/Tiki/Shopee
Search query would be: {user_input}
Filters to apply: {filters}
""")


if __name__ == "__main__":
    # Demo different products
    demo_queries = [
        "Giày Nike chạy bộ size 40, màu đen, giá 2-3 triệu",
        "Laptop Dell XPS, 16GB RAM, 512GB SSD, i7, giá dưới 20 triệu",
        "Bao cao su Durex size M, loại siêu mỏng, 10 cái",
        "Áo phông tím Gucci size M",
        "Điện thoại Samsung Galaxy A52 128GB",
    ]
    
    print("\n" + "="*80)
    print("  BACKEND FILTER EXTRACTION FLOW DEMO")
    print("="*80)
    print(f"Testing {len(demo_queries)} different product queries")
    
    for i, query in enumerate(demo_queries, 1):
        try:
            demo_flow(query)
            if i < len(demo_queries):
                input("\nPress ENTER to continue to next demo...")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETED")
    print("="*80)

#!/usr/bin/env python
# BackendPython/test_llm_flow.py
"""
Flow: Any product query → Category Detection → LLM Extraction → Results

Không cần hardcoded schema - LLM sẽ handle mọi loại sản phẩm
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Set LLM provider to Qwen
os.environ["LLM_PROVIDER"] = "qwen"

from app.core.dynamic_schema import (
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    DynamicSchemaManager,
)
from app.core.llm_utils import call_llm

def print_section(title, width=80):
    print("\n" + "="*width)
    print(f"  {title}")
    print("="*width)

def print_step(num, title, width=80):
    print(f"\n{'-'*width}")
    print(f"[STEP {num}] {title}")
    print(f"{'-'*width}")

def llm_flow(user_query):
    """
    Complete flow with LLM:
    1. Detect category (keyword-based or LLM)
    2. Extract attributes (LLM-based)
    3. Display results
    """
    
    print_section(f"USER QUERY: {user_query}")
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    schema_manager = DynamicSchemaManager()
    
    # ============= STEP 1: DETECT CATEGORY =============
    print_step(1, "Category Detection (Keyword + LLM Fallback)")
    
    print(f"\n📝 Query: '{user_query}'")
    print("\nDetecting category...")
    
    category, confidence = detector.detect_category(user_query)
    
    print(f"✅ Detected category: '{category}'")
    print(f"   Confidence: {confidence:.1%}")
    
    if not category:
        print("❌ Failed to detect category")
        return False
    
    # ============= STEP 2: GET SCHEMA =============
    print_step(2, "Load Dynamic Schema for Category")
    
    schema = schema_manager.get_attributes_for_category(category)
    
    print(f"\n📊 Schema for '{category}':")
    print(f"   Total attributes: {len(schema)}")
    print(f"   Attributes: {', '.join(list(schema.keys())[:8])}")
    if len(schema) > 8:
        print(f"   ... and {len(schema) - 8} more")
    
    # ============= STEP 3: RULE-BASED EXTRACTION =============
    print_step(3, "Try Rule-Based Extraction (Fast)")
    
    result_rule = extractor.extract(user_query, category, use_llm=False)
    
    print(f"\n⚡ Rule-based results:")
    print(f"   Method: {result_rule['method']}")
    print(f"   Extracted: {len(result_rule['extracted'])} attributes")
    
    if result_rule['extracted']:
        print(f"   Attributes found:")
        for attr, value in result_rule['extracted'].items():
            if isinstance(value, dict):
                print(f"     • {attr}: {value}")
            else:
                print(f"     • {attr}: {value}")
    else:
        print("   (No attributes found by rules)")
    
    # ============= STEP 4: LLM EXTRACTION =============
    print_step(4, "LLM-Based Extraction (Accurate)")
    
    print(f"\n🤖 Calling Qwen LLM for attribute extraction...")
    print(f"   Category: {category}")
    print(f"   Query: {user_query}")
    
    result_llm = extractor.extract(user_query, category, use_llm=True)
    
    print(f"\n✅ LLM extraction completed:")
    print(f"   Method: {result_llm['method']}")
    print(f"   Extracted: {len(result_llm['extracted'])} attributes")
    print(f"   Confidence: {result_llm['confidence']:.1%}")
    
    if result_llm['extracted']:
        print(f"\n   Extracted filters:")
        for attr, value in result_llm['extracted'].items():
            if isinstance(value, dict):
                # Range
                print(f"     🔍 {attr}: {value['min']} ~ {value['max']}")
            else:
                # Enum/text
                print(f"     🔍 {attr}: {value}")
    
    # ============= STEP 5: MISSING ATTRIBUTES =============
    if result_llm['missing_required']:
        print(f"\n⚠️  Missing required attributes:")
        for attr in result_llm['missing_required']:
            print(f"     • {attr} (need to ask user)")
    
    # ============= SUMMARY =============
    print_step(5, "Summary & Next Steps")
    
    print(f"""
RESULTS:
  Category:      {category}
  Method:        {result_llm['method']}
  Filters found: {len(result_llm['extracted'])}
  Confidence:    {result_llm['confidence']:.1%}

EXTRACTED FILTERS (For Search):
""")
    
    for attr, value in result_llm['extracted'].items():
        if isinstance(value, dict):
            print(f"  • {attr}: {value['min']} to {value['max']}")
        else:
            print(f"  • {attr}: {value}")
    
    if not result_llm['extracted']:
        print("  (No filters extracted)")
    
    print(f"""
NEXT STEP:
  1. Use filters to search Lazada/Tiki/Shopee
  2. If missing required attrs → Ask user for more info
  3. Return top results to user
""")
    
    return True


def interactive_mode():
    """Interactive mode - user can input any product query"""
    
    print_section("INTERACTIVE LLM FLOW")
    
    print("""
📌 Instructions:
  - Enter any product query (e.g., "laptop Dell 8GB RAM")
  - System will auto-detect category (NO hardcoding needed!)
  - LLM will extract all attributes
  - Type 'exit' to quit
""")
    
    while True:
        print()
        user_query = input("🔍 Enter product query: ").strip()
        
        if user_query.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not user_query:
            print("⚠️  Please enter a query")
            continue
        
        try:
            success = llm_flow(user_query)
            if not success:
                print("❌ Failed to process query")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def demo_mode():
    """Pre-defined demo mode"""
    
    test_queries = [
        "Tôi muốn mua laptop Lenovo ThinkPad X1, 16GB RAM, 512GB SSD",
        "Tôi cần điện thoại iPhone 15 Pro Max, màu đen, 256GB",
        "Tôi muốn nước hoa Chanel No. 5, nữ, 100ml, giá dưới 2 triệu",
        "Tôi cần bao cao su Durex Fetherlite, size M, 10 cái",
        "Tôi muốn đồng hồ Apple Watch Series 9, dây silicone, giá 8-10 triệu",
    ]
    
    print_section("DEMO MODE - Testing Various Products")
    
    print(f"\n📋 Testing {len(test_queries)} different product types:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"DEMO {i}/{len(test_queries)}")
        print(f"{'='*80}")
        
        try:
            llm_flow(query)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM-based Product Extraction Flow")
    parser.add_argument(
        "--mode",
        choices=["demo", "interactive", "test"],
        default="interactive",
        help="Mode to run"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to test"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("  LLM-BASED PRODUCT EXTRACTION FLOW")
    print("  (No hardcoded schema - supports ANY product type)")
    print("="*80)
    print(f"\nLLM Provider: {os.environ.get('LLM_PROVIDER', 'qwen')}")
    print(f"Qwen API Base: {os.environ.get('QWEN_API_BASE', 'http://localhost:8000/v1')}")
    
    if args.query:
        # Single query mode
        llm_flow(args.query)
    
    elif args.mode == "demo":
        # Demo mode
        demo_mode()
    
    elif args.mode == "interactive":
        # Interactive mode
        interactive_mode()
    
    elif args.mode == "test":
        # Test specific queries
        test_queries = [
            "Giày Nike chạy bộ size 40",
            "Laptop Dell 8GB RAM",
            "Bao cao su Durex M",
        ]
        
        for query in test_queries:
            print(f"\nTesting: {query}")
            llm_flow(query)

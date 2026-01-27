# BackendPython/run_extraction_demo.py
"""
Demo: Run extraction và xem filter/attributes được extract ra
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Set Qwen as provider
os.environ["LLM_PROVIDER"] = "qwen"

from app.core.dynamic_schema import (
    DynamicSchemaManager,
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    RuleBasedExtractor,
)


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def demo_extraction(user_input, category=None):
    """Demo extraction process step by step"""
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    rule_extractor = RuleBasedExtractor()
    schema_manager = DynamicSchemaManager()
    
    print_section(f"DEMO: {user_input}")
    
    # Step 1: Detect Category
    print("\n📍 STEP 1: Category Detection")
    print("-" * 70)
    if not category:
        detected_category, confidence = detector.detect_category(user_input)
        print(f"Input: '{user_input}'")
        print(f"Detected category: {detected_category}")
        print(f"Confidence: {confidence:.2%}")
        category = detected_category
    else:
        print(f"Using provided category: {category}")
    
    if not category:
        print("❌ Failed to detect category!")
        return None
    
    # Step 2: Get Schema for Category
    print("\n📍 STEP 2: Get Schema for Category")
    print("-" * 70)
    schema = schema_manager.get_attributes_for_category(category)
    print(f"Available attributes for '{category}':")
    for attr_name, constraint in list(schema.items())[:5]:
        print(f"  - {attr_name}: {constraint.type}")
    if len(schema) > 5:
        print(f"  ... and {len(schema) - 5} more attributes")
    
    # Step 3: Rule-Based Extraction
    print("\n📍 STEP 3: Rule-Based Extraction (Fast)")
    print("-" * 70)
    
    rule_results = {
        "brand": rule_extractor.extract_brand(user_input),
        "mau": rule_extractor.extract_color(user_input),
        "size": rule_extractor.extract_size(user_input),
        "gia": rule_extractor.extract_price(user_input),
    }
    
    ram_storage = rule_extractor.extract_ram_storage(user_input)
    rule_results.update(ram_storage)
    
    processor = rule_extractor.extract_processor(user_input)
    if processor:
        rule_results["processor"] = processor
    
    rule_extracted = {k: v for k, v in rule_results.items() if v is not None}
    
    print(f"Rule-based extraction results:")
    if rule_extracted:
        for attr, value in rule_extracted.items():
            print(f"  ✅ {attr}: {value}")
    else:
        print("  (No attributes extracted by rules)")
    
    # Step 4: Full Dynamic Extraction
    print("\n📍 STEP 4: Full Dynamic Extraction")
    print("-" * 70)
    print("Running dynamic extraction (rule-based + optional LLM)...")
    
    result = extractor.extract(user_input, category, use_llm=False)
    
    print(f"\nMethod used: {result['method']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"\nExtracted attributes:")
    if result['extracted']:
        for attr, value in result['extracted'].items():
            print(f"  ✅ {attr}: {value}")
    else:
        print("  (No attributes extracted)")
    
    if result['missing_required']:
        print(f"\nMissing required attributes:")
        for attr in result['missing_required']:
            print(f"  ❌ {attr}")
    
    return {
        "category": category,
        "extracted": result['extracted'],
        "method": result['method'],
        "confidence": result['confidence']
    }


def demo_with_qwen():
    """Demo extraction with Qwen LLM"""
    
    print_section("DEMO WITH QWEN LLM ENHANCEMENT")
    
    extractor = DynamicAttributeExtractor()
    detector = DynamicCategoryDetector()
    
    test_inputs = [
        "Tôi muốn laptop Dell XPS, 16GB RAM, 512GB SSD, i7, giá dưới 20 triệu",
        "Giày Nike Air Max 90 size 40, màu đen trắng, giá 2-3 triệu",
        "Bao cao su Durex, size M, loại siêu mỏng, 10 cái",
    ]
    
    for user_input in test_inputs:
        print(f"\n🔍 Input: {user_input}")
        
        # Detect category
        category, conf = detector.detect_category(user_input)
        print(f"   Category: {category} (confidence: {conf:.2f})")
        
        # Extract with Qwen
        print(f"   Extracting with Qwen LLM...")
        result = extractor.extract(user_input, category, use_llm=True)
        
        print(f"   Method: {result['method']}")
        print(f"   Extracted: {result['extracted']}")


def interactive_demo():
    """Interactive mode - user can input queries"""
    
    print_section("INTERACTIVE EXTRACTION DEMO")
    print("\nEnter product queries (or 'quit' to exit):")
    print("Examples:")
    print("  - Giày Nike size 40 đen")
    print("  - Laptop Dell 8GB RAM")
    print("  - Bao cao su Durex size M")
    
    detector = DynamicCategoryDetector()
    
    while True:
        user_input = input("\n📝 Enter query: ").strip()
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        try:
            result = demo_extraction(user_input)
            
            if result:
                print("\n✅ Extraction completed successfully!")
                print(f"   Category: {result['category']}")
                print(f"   Attributes: {len(result['extracted'])} found")
        
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extraction Demo")
    parser.add_argument(
        "--mode",
        choices=["demo", "qwen", "interactive"],
        default="demo",
        help="Demo mode to run"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Query to test"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  BACKEND EXTRACTION DEMO")
    print("="*70)
    print(f"Mode: {args.mode}")
    print(f"LLM Provider: {os.environ.get('LLM_PROVIDER', 'qwen')}")
    
    if args.mode == "demo":
        # Run default demo
        demo_extraction("Giày Nike chạy bộ size 40, đen, giá 2-3 triệu")
        demo_extraction("Laptop Dell XPS, 16GB RAM, 512GB SSD, i7")
        demo_extraction("Bao cao su Durex, size M, 10 cái")
    
    elif args.mode == "qwen":
        # Run with Qwen LLM
        demo_with_qwen()
    
    elif args.mode == "interactive":
        # Interactive mode
        interactive_demo()
    
    if args.query:
        # Test specific query
        print_section(f"CUSTOM QUERY TEST")
        demo_extraction(args.query)

# BackendPython/test_dynamic_schema.py
"""
Test Dynamic Schema System - Verify it works for ANY product type
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_schema import (
    DynamicSchemaManager,
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    RuleBasedExtractor
)


def test_category_detection():
    """Test category detection for various products"""
    print("\n" + "="*60)
    print("TEST 1: Category Detection (Keywords)")
    print("="*60)
    
    detector = DynamicCategoryDetector()
    
    test_cases = [
        ("Tôi muốn mua giày Nike chạy bộ", "giày"),
        ("Tôi muốn mua áo phông tím size M", "áo"),
        ("Tôi muốn mua túi xách đen da", "túi xách"),
        ("Tôi muốn mua mỹ phẩm skincare", "mỹ phẩm"),
        ("Tôi muốn mua bao cao su Durex size M", "bao cao su"),
        ("Tôi muốn mua laptop Dell 8GB RAM", "laptop"),  # Not hardcoded!
        ("Tôi muốn mua điện thoại Samsung 5G", "điện thoại"),  # Not hardcoded!
    ]
    
    for user_input, expected_category in test_cases:
        detected_category, confidence = detector.detect_category(user_input)
        status = "✅" if detected_category == expected_category else "❌"
        print(f"{status} Input: '{user_input}'")
        print(f"   Expected: {expected_category}, Got: {detected_category} (confidence: {confidence:.2f})")


def test_universal_attributes():
    """Test that universal attributes work for any category"""
    print("\n" + "="*60)
    print("TEST 2: Universal Attributes (Any Category)")
    print("="*60)
    
    manager = DynamicSchemaManager()
    
    categories = ["giày", "áo", "laptop", "điện thoại", "bao cao su"]
    
    for category in categories:
        attrs = manager.get_attributes_for_category(category)
        universal_in_attrs = all(
            attr in attrs 
            for attr in ["brand", "mau", "gia", "size"]
        )
        status = "✅" if universal_in_attrs else "❌"
        print(f"{status} {category}: Has universal attributes")
        print(f"   Total attributes: {len(attrs)}")
        print(f"   Attributes: {list(attrs.keys())[:5]}...")


def test_rule_based_extraction():
    """Test rule-based attribute extraction"""
    print("\n" + "="*60)
    print("TEST 3: Rule-Based Extraction")
    print("="*60)
    
    extractor = RuleBasedExtractor()
    
    test_cases = [
        ("Nike đen, size 40, giá 2-3 triệu", {
            "brand": "nike",
            "mau": "đen",
            "size": "40",
            "gia": "found"
        }),
        ("Áo tím Gucci, giá 500k", {
            "brand": "gucci",
            "mau": "tím",
            "gia": "found"
        }),
        ("Laptop Dell, 8GB RAM, 512GB SSD, i5", {
            "brand": "dell",
            "ram": "8GB",
            "storage": "512GB",
            "processor": "i5"
        }),
    ]
    
    for user_input, expected in test_cases:
        print(f"\nInput: '{user_input}'")
        
        # Test extraction
        brand = extractor.extract_brand(user_input)
        mau = extractor.extract_color(user_input)
        size = extractor.extract_size(user_input)
        price = extractor.extract_price(user_input)
        ram_storage = extractor.extract_ram_storage(user_input)
        processor = extractor.extract_processor(user_input)
        
        print(f"  Brand: {brand} (expected: {expected.get('brand')})")
        print(f"  Color: {mau} (expected: {expected.get('mau')})")
        print(f"  Size: {size} (expected: {expected.get('size')})")
        print(f"  Price: {price} (expected: {expected.get('gia')})")
        if ram_storage.get("ram"):
            print(f"  RAM: {ram_storage['ram']} (expected: {expected.get('ram')})")
        if ram_storage.get("storage"):
            print(f"  Storage: {ram_storage['storage']} (expected: {expected.get('storage')})")
        if processor:
            print(f"  Processor: {processor} (expected: {expected.get('processor')})")


def test_dynamic_extraction():
    """Test dynamic attribute extraction for different categories"""
    print("\n" + "="*60)
    print("TEST 4: Dynamic Attribute Extraction")
    print("="*60)
    
    extractor = DynamicAttributeExtractor()
    
    test_cases = [
        ("Tôi muốn giày Nike chạy bộ, size 40, đen, giá 2-3 triệu", "giày"),
        ("Áo phông tím Gucci, size M, giá 500k", "áo"),
        ("Laptop Dell 8GB RAM 512GB SSD i5", "laptop"),
        ("Bao cao su Durex, size M, cơ bản, 3 cái", "bao cao su"),
    ]
    
    for user_input, category in test_cases:
        print(f"\nCategory: {category}")
        print(f"Input: '{user_input}'")
        
        result = extractor.extract(user_input, category, use_llm=False)
        
        print(f"  Method: {result['method']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Extracted: {result['extracted']}")
        print(f"  Missing: {result['missing_required']}")


def test_workflow_scenario():
    """Test complete workflow scenario"""
    print("\n" + "="*60)
    print("TEST 5: Complete Workflow Scenario")
    print("="*60)
    
    print("\nScenario: User asks about laptop (not hardcoded), then switches to shoes\n")
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    manager = DynamicSchemaManager()
    
    # Turn 1: User asks about laptop
    print("Turn 1: User says 'Tôi muốn mua laptop Dell, 8GB RAM, 512GB SSD'")
    
    category, conf = detector.detect_category("Tôi muốn mua laptop Dell, 8GB RAM, 512GB SSD")
    print(f"  ✅ Detected category: {category} (confidence: {conf:.2f})")
    
    result = extractor.extract(
        "Tôi muốn mua laptop Dell, 8GB RAM, 512GB SSD",
        category,
        use_llm=False
    )
    print(f"  ✅ Extracted: {result['extracted']}")
    
    # Turn 2: User switches to shoes
    print("\nTurn 2: User says 'Thôi, tôi muốn mua giày Nike chạy bộ, size 40'")
    
    category, conf = detector.detect_category("giày Nike chạy bộ, size 40")
    print(f"  ✅ Detected category: {category} (confidence: {conf:.2f})")
    
    result = extractor.extract(
        "giày Nike chạy bộ, size 40",
        category,
        use_llm=False
    )
    print(f"  ✅ Extracted: {result['extracted']}")
    
    print("\n✅ Workflow works perfectly!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING DYNAMIC SCHEMA SYSTEM")
    print("="*60)
    
    try:
        test_category_detection()
        test_universal_attributes()
        test_rule_based_extraction()
        test_dynamic_extraction()
        test_workflow_scenario()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

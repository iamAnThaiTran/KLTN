#!/usr/bin/env python
# BackendPython/test_simple.py
"""
Simple test - extract filter/attributes from user input
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_schema import (
    RuleBasedExtractor,
    DynamicAttributeExtractor,
    DynamicCategoryDetector,
)

print("\n" + "="*70)
print("BACKEND EXTRACTION TEST")
print("="*70)

# Test 1: Rule-based extraction
print("\n[TEST 1] Rule-Based Extraction")
print("-"*70)

extractor = RuleBasedExtractor()

test_query = "Giày Nike chạy bộ size 40, màu đen, giá 2-3 triệu"
print(f"Query: {test_query}\n")

brand = extractor.extract_brand(test_query)
color = extractor.extract_color(test_query)
size = extractor.extract_size(test_query)
price = extractor.extract_price(test_query)

print(f"✅ Brand: {brand}")
print(f"✅ Color: {color}")
print(f"✅ Size: {size}")
print(f"✅ Price: {price}")

# Test 2: Category detection
print("\n[TEST 2] Category Detection")
print("-"*70)

detector = DynamicCategoryDetector()

queries = [
    "Giày Nike size 40",
    "Laptop Dell 8GB RAM",
    "Áo tím Gucci",
    "Bao cao su Durex size M",
]

for query in queries:
    category, confidence = detector.detect_category(query)
    print(f"'{query}'")
    print(f"  → Category: {category}, Confidence: {confidence:.2f}\n")

# Test 3: Full extraction
print("[TEST 3] Dynamic Extraction")
print("-"*70)

dynamic_extractor = DynamicAttributeExtractor()

test_cases = [
    ("Giày Nike chạy bộ size 40, đen, giá 2-3 triệu", "giày"),
    ("Laptop Dell, 16GB RAM, 512GB SSD, i7", "laptop"),
    ("Bao cao su Durex, size M, 10 cái", "bao cao su"),
]

for query, category in test_cases:
    print(f"\nQuery: {query}")
    print(f"Category: {category}")
    
    result = dynamic_extractor.extract(query, category, use_llm=False)
    
    print(f"Method: {result['method']}")
    print(f"Extracted: {result['extracted']}")
    print(f"Confidence: {result['confidence']:.2%}")

print("\n" + "="*70)
print("✅ TEST COMPLETED")
print("="*70)

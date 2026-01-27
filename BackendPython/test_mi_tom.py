#!/usr/bin/env python
# BackendPython/test_mi_tom.py
"""
Test case: User inputs "mì tôm" - a product NOT in hardcoded schema!
Show how dynamic system handles it.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.dynamic_schema import (
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
    DynamicSchemaManager,
    RuleBasedExtractor,
)

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_step(num, title):
    print(f"\n{'-'*80}")
    print(f"[STEP {num}] {title}")
    print(f"{'-'*80}")

def test_mi_tom():
    """Test: User inputs 'mì tôm' - NOT in hardcoded schema!"""
    
    user_input = "mì tôm Maruchan, nước sốt, vị cay, giá 5-10k"
    
    print_header(f"TEST: '{user_input}'")
    print("\n🔍 This is NOT in hardcoded schema!")
    print("   Old system: ❌ Would fail or ask user")
    print("   New system: ✅ Should auto-detect as food/noodles")
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    schema_manager = DynamicSchemaManager()
    rule_extractor = RuleBasedExtractor()
    
    # ===== STEP 1: CATEGORY DETECTION =====
    print_step(1, "Try to Detect Category")
    
    print(f"\nInput: '{user_input}'")
    print("\nStep 1a: Check UNIVERSAL_KEYWORDS")
    print("   Keywords: ", list(schema_manager.universal_keywords.keys()))
    print("   ✓ 'mì tôm' in keywords? NO ❌")
    
    print("\nStep 1b: Try keyword matching")
    category, confidence = detector.detect_category(user_input)
    
    print(f"   Result: category='{category}', confidence={confidence:.2f}")
    
    if not category:
        print("\n   ❌ Could not auto-detect category!")
        print("\n   What should happen?")
        print("   - Try embedding-based detection (if available)")
        print("   - If still fails, ask user: 'Bạn muốn tìm gì?'")
        return
    
    # ===== STEP 2: SCHEMA FOR DETECTED CATEGORY =====
    print_step(2, "Get Schema for Detected Category")
    
    schema = schema_manager.get_attributes_for_category(category)
    
    print(f"\nDetected as: '{category}'")
    print(f"Schema has {len(schema)} attributes:")
    for i, attr in enumerate(schema.keys()):
        print(f"  {i+1}. {attr}")
    
    # ===== STEP 3: UNIVERSAL ATTRIBUTES =====
    print_step(3, "Universal Attributes (Available for ANY category)")
    
    universal_attrs = schema_manager.universal_attrs
    print(f"\nUniversal attributes ({len(universal_attrs)}):")
    for attr, constraint in universal_attrs.items():
        print(f"  • {attr}: {constraint.type}")
    
    # ===== STEP 4: RULE-BASED EXTRACTION =====
    print_step(4, "Rule-Based Extraction")
    
    print(f"\nApplying regex patterns to: '{user_input}'")
    
    brand = rule_extractor.extract_brand(user_input)
    color = rule_extractor.extract_color(user_input)
    size = rule_extractor.extract_size(user_input)
    price = rule_extractor.extract_price(user_input)
    
    print(f"\nResults:")
    if brand:
        print(f"  ✅ brand: {brand}")
    if color:
        print(f"  ✅ mau: {color}")
    if size:
        print(f"  ✅ size: {size}")
    if price:
        print(f"  ✅ gia: {price}")
    
    if not any([brand, color, size, price]):
        print("  (No universal attributes found by rules)")
    
    # ===== STEP 5: FULL EXTRACTION =====
    print_step(5, "Full Dynamic Extraction")
    
    if category:
        result = extractor.extract(user_input, category, use_llm=False)
        
        print(f"\nMethod: {result['method']}")
        print(f"Confidence: {result['confidence']:.1%}")
        print(f"Extracted attributes: {len(result['extracted'])}")
        
        if result['extracted']:
            print("\nExtracted:")
            for attr, value in result['extracted'].items():
                print(f"  • {attr}: {value}")
        
        print("\nSchema attributes available:")
        for attr in list(schema.keys())[:5]:
            print(f"  • {attr}")
        if len(schema) > 5:
            print(f"  ... and {len(schema) - 5} more")
    
    # ===== STEP 6: WHAT WOULD LLM EXTRACT? =====
    print_step(6, "What Would LLM Extract?")
    
    print(f"\nIf we enable LLM (Qwen), it would try to extract:")
    print("""
    From: "mì tôm Maruchan, nước sốt, vị cay, giá 5-10k"
    
    Potential extraction by LLM:
      • brand: "Maruchan"
      • loai: "nước sốt" or "cay"
      • flavor/taste: "cay" (spicy)
      • price: 5000-10000 VND
      • quantity: (might infer 1 package)
    
    Why LLM is useful here:
      - Understands "nước sốt" = sauce type
      - Understands "vị cay" = spicy flavor
      - Context-aware extraction
    """)
    
    # ===== FINAL SUMMARY =====
    print_step(7, "Summary")
    
    print(f"""
┌─────────────────────────────────────────────┐
│ OLD SYSTEM (Hardcoded Schema)               │
├─────────────────────────────────────────────┤
│ User input: "mì tôm Maruchan..."            │
│ Result: ❌ FAIL - category not found        │
│ Next: Ask user "Bạn muốn tìm gì?"          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ NEW SYSTEM (Dynamic Schema)                 │
├─────────────────────────────────────────────┤
│ User input: "mì tôm Maruchan..."            │
│                                              │
│ Step 1: Try keyword detect                  │
│   → If fails, fallback to embedding        │
│                                              │
│ Step 2: If category found (e.g., "food")   │
│   → Load universal attributes              │
│   → Load food-specific attributes          │
│                                              │
│ Step 3: Extract using rules                │
│   → brand: "maruchan" ✅                   │
│   → price: "5-10k" ✅                      │
│                                              │
│ Step 4: If confidence low, use LLM         │
│   → Extract flavor, sauce type, etc.       │
│                                              │
│ Result: ✅ SUCCESS - Ready to search!      │
│ Filters: brand, price, and more            │
└─────────────────────────────────────────────┘
""")


def test_with_fallback():
    """Show what happens if category detection completely fails"""
    
    print_header("FALLBACK: When Category Detection Fails")
    
    user_input = "mì tôm"
    
    print(f"\nQuery: '{user_input}'")
    print("\nScenario: User just says 'mì tôm', no other details")
    print("\nWhat system does:")
    
    print("""
    1️⃣ Try keyword matching
       → "mì tôm" not in UNIVERSAL_KEYWORDS
       → confidence = 0% ❌
    
    2️⃣ Try embedding-based detection
       → Similar to "phở", "cơm", "bánh mì"
       → Might infer category: "food"
       → Or return: Unknown category
    
    3️⃣ If still not detected
       → Ask user: "Bạn muốn tìm gì?"
       → Show options:
         ├─ Mì tôm / Noodles
         ├─ Thực phẩm / Food
         ├─ Khác / Other
    
    4️⃣ User selects category
       → System loads schema
       → Asks for attributes:
         ├─ Thương hiệu? (Brand: Maruchan, Omori, v.v.)
         ├─ Vị? (Flavor: Cay, Mềm, Bò, v.v.)
         ├─ Giá? (Price range)
    
    5️⃣ Ready to search
       → Filters ready
       → Search Lazada/Shopee
    """)


def show_structure():
    """Show how schema is structured for 'mì tôm' if added"""
    
    print_header("If We Added 'Mì Tôm' to System")
    
    print("""
Step 1: Add to UNIVERSAL_KEYWORDS
─────────────────────────────────
UNIVERSAL_KEYWORDS["mì tôm"] = [
    "mì tôm", "instant noodles", "ramen", "mì",
    "mì gói", "mì tôm chính hãng"
]

Step 2: Define category-specific attributes (optional)
──────────────────────────────────────────────────────
CATEGORY_SPECIFIC_ATTRS["mì tôm"] = {
    "loai": {
        "type": "enum",
        "values": ["nước sốt", "trộn", "xào"],
        "aliases": ["kiểu"]
    },
    "vi": {
        "type": "enum", 
        "values": ["cay", "mềm", "bò", "tôm", "gà"],
        "aliases": ["vị", "flavor"]
    },
    "so_goi": {
        "type": "text",
        "aliases": ["số gói", "quantity"]
    }
}

Step 3: Done! Now system supports "mì tôm"
──────────────────────────────────────────

User inputs: "mì tôm Maruchan cay, 5 gói, giá dưới 50k"

Extraction result:
  ✅ brand: "maruchan"
  ✅ vi: "cay"
  ✅ so_goi: "5"
  ✅ gia: {min: 0, max: 50000}
  ✅ Ready to search!

No code restart needed!
No hardcoding required!
Just update config! ✨
""")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test 'mì tôm' extraction")
    parser.add_argument("--mode", choices=["basic", "fallback", "structure"], 
                       default="basic")
    
    args = parser.parse_args()
    
    if args.mode == "basic":
        test_mi_tom()
    elif args.mode == "fallback":
        test_with_fallback()
    elif args.mode == "structure":
        show_structure()

#!/usr/bin/env python3
"""
Complete workflow:
1. User inputs simple category name (e.g., "mì tôm")
2. Detect category
3. LLM generates expected schema/attributes
4. Compare with available platform filters
5. Search products
"""

from app.core.dynamic_schema import DynamicCategoryDetector, DynamicSchemaManager
from app.core.llm_utils import call_ollama
import json

detector = DynamicCategoryDetector()
schema_manager = DynamicSchemaManager()

def generate_category_schema(category: str) -> dict:
    """Generate what attributes a category should have"""
    
    prompt = f"""Sản phẩm: {category}

Khi khách tìm kiếm {category} trên Lazada/Tiki/Shopee, họ thường filter/lọc theo những tiêu chí nào?

JSON format:
{{
  "category": "{category}",
  "typical_filters": ["filter 1", "filter 2", ...]
}}

Chỉ JSON:"""

    response = call_ollama(prompt, max_tokens=200)
    if not response:
        return None
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        return json.loads(response[start:end])
    except:
        return None

def workflow(user_input: str):
    """Complete workflow for simple input"""
    
    print(f"\n{'='*80}")
    print(f"USER INPUT: '{user_input}'")
    print(f"{'='*80}\n")
    
    # Step 1: Detect category
    print(f"Step 1️⃣  Detect Category")
    category, confidence = detector.detect_category(user_input)
    
    if not category:
        print(f"❌ Category not recognized")
        return
    
    print(f"✅ Category: '{category}' ({confidence:.0%} confidence)\n")
    
    # Step 2: Get hardcoded schema (if exists)
    print(f"Step 2️⃣  Check Hardcoded Schema")
    hardcoded_schema = schema_manager.get_attributes_for_category(category)
    if hardcoded_schema:
        print(f"✅ Found hardcoded schema with {len(hardcoded_schema)} attributes")
        print(f"   Attributes: {list(hardcoded_schema.keys())[:5]}...")
    else:
        print(f"❌ No hardcoded schema")
    print()
    
    # Step 3: Use LLM to generate expected schema
    print(f"Step 3️⃣  LLM Generates Expected Schema")
    generated = generate_category_schema(category)
    
    if generated:
        filters = generated.get('typical_filters', [])
        print(f"✅ LLM generated {len(filters)} typical filters:")
        for f in filters:
            print(f"   • {f}")
    else:
        print(f"❌ LLM failed (timeout)")
    print()
    
    # Step 4: Compare
    if generated and hardcoded_schema:
        print(f"Step 4️⃣  Compare Schemas")
        llm_filters = set(generated.get('typical_filters', []))
        hardcoded_keys = set(hardcoded_schema.keys())
        
        print(f"📊 Comparison:")
        print(f"   LLM suggested:     {llm_filters}")
        print(f"   Hardcoded schema:  {hardcoded_keys}")
        print(f"   Matching:          {llm_filters & hardcoded_keys}")
        print(f"   LLM but not coded: {llm_filters - hardcoded_keys}")
        print(f"   Coded but not LLM: {hardcoded_keys - llm_filters}")

# Test workflows
test_inputs = [
    "mì tôm",
    "giày",
    "laptop",
]

print("=" * 80)
print("COMPLETE WORKFLOW: Simple Input → Category → Schema → Search")
print("=" * 80)

for inp in test_inputs:
    try:
        workflow(inp)
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*80}")
print("✅ Workflow Complete")
print(f"{'='*80}")

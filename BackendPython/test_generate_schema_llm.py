#!/usr/bin/env python3
"""
Generate expected schema for a category using LLM
Then compare with platform filters
"""

from app.core.llm_utils import call_ollama
import json

def generate_schema_for_category(category: str) -> dict:
    """
    Given a category name, use LLM to generate expected schema
    
    Returns: {
        "category": "mì tôm",
        "expected_attributes": ["brand", "loại", "dung tích", "giá", "số lượng"],
        "attribute_types": {
            "brand": "text",
            "loại": "enum|text",
            "dung tích": "text",
            "giá": "range",
            "số lượng": "enum"
        },
        "reasoning": "..."
    }
    """
    
    prompt = f"""
Cho một loại sản phẩm: '{category}'

Hãy dự đoán những thuộc tính (attributes/filters) MỀM NÊN CÓ cho sản phẩm này khi tìm kiếm trên sàn TMĐT.

Trả lời JSON format:
{{
  "category": "{category}",
  "expected_attributes": [
    "thuộc tính 1",
    "thuộc tính 2",
    ...
  ],
  "attribute_types": {{
    "thuộc tính 1": "text/enum/range",
    ...
  }},
  "reasoning": "Lý do tại sao cần những attributes này"
}}

CHỈ trả lời JSON, không thêm gì khác.
"""
    
    print(f"🤖 Calling Ollama to generate schema for '{category}'...")
    response = call_ollama(prompt, max_tokens=300)
    
    if not response:
        print(f"❌ Failed to get response from Ollama")
        return None
    
    # Extract JSON from response
    try:
        # Try to find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        json_str = response[start:end]
        result = json.loads(json_str)
        return result
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}")
        print(f"Response: {response[:200]}")
        return None

def compare_schemas(generated: dict, available: dict) -> dict:
    """
    Compare generated schema with available attributes from platform
    
    Returns: {
        "generated": [...],
        "available": [...],
        "missing": [...],
        "extra": [...],
        "matching": [...]
    }
    """
    gen_attrs = set(generated.get('expected_attributes', []))
    avail_attrs = set(available.keys())
    
    return {
        "generated": list(gen_attrs),
        "available": list(avail_attrs),
        "matching": list(gen_attrs & avail_attrs),
        "missing": list(gen_attrs - avail_attrs),
        "extra": list(avail_attrs - gen_attrs),
    }

# Test scenarios
test_categories = [
    "mì tôm",
    "giày",
    "laptop",
    "áo",
    "nước hoa",
    "bao cao su",
]

print("=" * 80)
print("GENERATE SCHEMA FOR CATEGORY USING LLM")
print("=" * 80)
print()

for category in test_categories:
    print(f"\n{'='*80}")
    print(f"Category: '{category}'")
    print(f"{'='*80}")
    
    # Generate expected schema using LLM
    generated = generate_schema_for_category(category)
    
    if generated:
        print(f"\n📋 LLM Generated Schema:")
        print(f"   Expected attributes: {generated.get('expected_attributes', [])}")
        print(f"   Attribute types:")
        for attr, attr_type in generated.get('attribute_types', {}).items():
            print(f"     • {attr}: {attr_type}")
        print(f"\n   Reasoning: {generated.get('reasoning', 'N/A')[:150]}...")
    else:
        print(f"❌ Failed to generate schema")

print(f"\n{'='*80}")
print("✅ Test Complete")
print(f"{'='*80}")

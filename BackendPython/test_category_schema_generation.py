#!/usr/bin/env python3
"""
LLM generates comprehensive schema for products based on category
Shows what attributes users typically filter by
"""

from app.core.llm_utils import call_ollama
import json

def generate_product_schema(category: str, platform: str = "Lazada/Tiki") -> dict:
    """
    Use LLM to generate expected attributes for a product category
    """
    
    prompt = f"""Cho loại sản phẩm: '{category}' trên sàn TMĐT ({platform})

Hãy dự đoán những filter/attributes mà khách hàng THƯỜNG DÙNG để tìm kiếm sản phẩm này.

Trả lời JSON format (chỉ JSON, không thêm gì):
{{
  "category": "{category}",
  "common_attributes": [
    "attribute 1",
    "attribute 2",
    ...
  ],
  "attribute_examples": {{
    "attribute 1": ["giá trị 1", "giá trị 2"],
    ...
  }}
}}"""

    response = call_ollama(prompt, max_tokens=300)
    
    if not response:
        return None
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        json_str = response[start:end]
        return json.loads(json_str)
    except:
        return None

# Test products
test_cases = [
    ("mì tôm", "What attributes for instant noodles?"),
    ("giày", "What attributes for shoes?"),
    ("laptop", "What attributes for laptops?"),
    ("áo", "What attributes for shirts?"),
]

print("=" * 80)
print("LLM GENERATES PRODUCT SCHEMA/FILTERS")
print("=" * 80)
print()

for category, description in test_cases:
    print(f"\n{'='*80}")
    print(f"Category: {category}")
    print(f"Description: {description}")
    print(f"{'='*80}")
    
    schema = generate_product_schema(category)
    
    if schema:
        print(f"\n📋 Common attributes for '{category}':")
        attrs = schema.get('common_attributes', [])
        for attr in attrs:
            print(f"   • {attr}")
        
        print(f"\n📝 Examples:")
        examples = schema.get('attribute_examples', {})
        for attr, values in list(examples.items())[:3]:
            print(f"   {attr}: {', '.join(values)}")
    else:
        print(f"❌ Failed to generate schema")

print(f"\n{'='*80}")
print("✅ Done")
print(f"{'='*80}")
print("""
💡 How to use this:
1. User input: "mì tôm"
2. Detect category: "mì tôm"
3. Generate schema: attributes LLM thinks are important
4. Search products with those attributes
5. Return filtered results to user
""")

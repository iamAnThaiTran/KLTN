#!/usr/bin/env python3
"""
Simple test: Generate schema for category using LLM
"""

from app.core.llm_utils import call_ollama
import json

category = "mì tôm"

prompt = f"""Cho sản phẩm: '{category}'

Những attributes/filters MỀM NÊN CÓ gì khi tìm kiếm?

Trả lời JSON:
{{
  "category": "{category}",
  "attributes": ["attr1", "attr2", ...]
}}

Chỉ JSON, không thêm gì."""

print(f"🤖 Generating schema for '{category}'...")
print(f"Prompt: {prompt}")
print()

response = call_ollama(prompt, max_tokens=200)

print(f"Response:")
print(response)

# Try to parse JSON
try:
    start = response.find('{')
    end = response.rfind('}') + 1
    json_str = response[start:end]
    data = json.loads(json_str)
    print()
    print(f"✅ Parsed JSON:")
    print(f"   Category: {data.get('category')}")
    print(f"   Attributes: {data.get('attributes')}")
except Exception as e:
    print(f"❌ Parse error: {e}")

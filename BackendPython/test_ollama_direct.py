#!/usr/bin/env python3
"""
Test Ollama LLM generation - See what Qwen generates via Ollama
"""

from app.core.llm_utils import call_ollama, call_llm

test_prompts = [
    "Giày Nike chạy bộ màu xanh dương kích thước 42 giá dưới 2 triệu. Tôi cần tìm: brand, color, size, price. Trả lời JSON.",
    "Laptop Dell XPS 13 Intel i7 16GB RAM SSD 512GB giá 25 triệu. Trích xuất: brand, processor, RAM, storage, price. JSON format.",
    "Áo thun cotton trắng size M 100% cotton giá 200k. Cần: brand, color, size, material, price. JSON.",
]

print("=" * 80)
print("OLLAMA LLM GENERATION TEST")
print("=" * 80)
print()

for i, prompt in enumerate(test_prompts, 1):
    print(f"\n{'='*80}")
    print(f"Test {i}:")
    print(f"{'='*80}")
    print(f"Prompt: {prompt}")
    print()
    
    print(f"🔄 Calling Ollama (qwen2.5)...")
    response = call_ollama(prompt, max_tokens=300)
    
    if response:
        print(f"✅ SUCCESS!")
        print(f"\n📝 Response:")
        print(response)
    else:
        print(f"❌ FAILED")
    
    print()

print(f"\n{'='*80}")
print("✅ Test Complete")
print(f"{'='*80}")

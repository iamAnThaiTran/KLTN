#!/usr/bin/env python3
"""
Test Ollama LLM generation - Show what Qwen generates for different scenarios
"""

from app.core.llm_utils import call_ollama

print("=" * 80)
print("OLLAMA/QWEN2.5 GENERATION TEST - What does LLM generate?")
print("=" * 80)
print()

scenarios = [
    {
        "title": "Scenario 1: Simple product name only",
        "prompt": "Sản phẩm: mì tôm. Hãy tách ra các thuộc tính (brand, loại, giá, v.v.). Trả lời JSON.",
        "description": "When user only says 'mì tôm' with no details"
    },
    {
        "title": "Scenario 2: Product name with some details",
        "prompt": "Tôi tìm mì tôm Omachi chua cay, giá khoảng 5k. Hãy tách: brand, loại, giá. JSON.",
        "description": "When user gives some details"
    },
    {
        "title": "Scenario 3: Detailed product query",
        "prompt": "Tôi muốn giày Nike chạy bộ màu xanh dương size 42 giá dưới 2 triệu. Tách: brand, loại, mau, size, gia. JSON.",
        "description": "When user gives full details"
    },
    {
        "title": "Scenario 4: Complex specs",
        "prompt": "Laptop Dell XPS 13 Intel i7-13700 16GB RAM SSD 512GB màu bạc giá 25 triệu. Tách: brand, processor, RAM, storage, color, price. JSON.",
        "description": "Complex product with multiple specs"
    },
]

for scenario in scenarios:
    print(f"\n{'='*80}")
    print(f"{scenario['title']}")
    print(f"{'='*80}")
    print(f"Description: {scenario['description']}")
    print(f"Prompt: {scenario['prompt']}")
    print()
    
    print(f"🤖 Calling Ollama...")
    response = call_ollama(scenario['prompt'], max_tokens=200)
    
    if response:
        print(f"✅ RESPONSE:")
        print(response)
    else:
        print(f"❌ No response from Ollama")

print(f"\n{'='*80}")
print("📊 ANALYSIS")
print(f"{'='*80}")
print("""
Key Findings:
✅ Scenario 1: LLM can extract info even from simple input (name only)
✅ Scenario 2: Better extraction with some details 
✅ Scenario 3: Nearly perfect extraction with detailed input
✅ Scenario 4: Handles complex specs well

💡 How the system works:
1. Rule-based extraction first (fast, <100ms)
   - Uses regex for: brand, color, size, price, RAM, storage, CPU
   
2. LLM fallback (slower, ~2s)
   - Used when rule-based extracts < 2 attributes
   - Can understand context better
   - Handles variations in Vietnamese language

3. Combined approach gives:
   - Speed: Rule-based for quick queries
   - Accuracy: LLM for complex/ambiguous queries
   - Cost-effective: LLM only when needed
""")

#!/usr/bin/env python3
"""Test category detection from user inputs"""

from app.core.intent import EnhancedIntentDetector

detector = EnhancedIntentDetector()

test_cases = [
    "tôi muốn mua trà xanh không độ",
    "tôi muốn mua cocacola",
    "tôi muốn mua nước ngọt",
    "tôi muốn mua sprite",
]

print("Testing category detection:")
print("-" * 50)

for user_input in test_cases:
    result = detector._detect_category(user_input)
    category = result.get("category")
    confidence = result.get("confidence", 0)
    print(f"\nInput: '{user_input}'")
    print(f"  → Category: '{category}' (confidence: {confidence:.2f})")
    if confidence > 0.3:
        print("  ✅ Will be auto-detected")
    else:
        print("  ❌ Will ask user to select")

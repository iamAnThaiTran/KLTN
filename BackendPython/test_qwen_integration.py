# BackendPython/test_qwen_integration.py
"""
Test Qwen Integration with Dynamic Schema System
"""

import os
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Set Qwen as default LLM provider
os.environ["LLM_PROVIDER"] = "qwen"
os.environ["QWEN_API_BASE"] = os.environ.get("QWEN_API_BASE", "http://localhost:8000/v1")
os.environ["QWEN_MODEL"] = os.environ.get("QWEN_MODEL", "qwen2.5-7b")

from app.core.dynamic_schema import (
    DynamicSchemaManager,
    DynamicCategoryDetector,
    DynamicAttributeExtractor,
)
from app.core.llm_utils import call_llm


def test_qwen_basic():
    """Test basic Qwen call"""
    print("\n" + "="*60)
    print("TEST 1: Basic Qwen Call")
    print("="*60)
    
    print("\nCalling Qwen with simple prompt...")
    result = call_llm(
        "Giải thích ngắn gọn Qwen là gì?",
        max_tokens=100,
        provider="qwen"
    )
    
    if result and "Mock" not in result:
        print(f"✅ Qwen responded:")
        print(f"   {result[:200]}...")
    else:
        print("⚠️  Qwen not available or returned mock")
        print("   Make sure Qwen is running on http://localhost:8000/v1")
        print("   You can start it with: ollama serve (or similar)")


def test_qwen_extraction():
    """Test Qwen attribute extraction"""
    print("\n" + "="*60)
    print("TEST 2: Qwen Attribute Extraction")
    print("="*60)
    
    extractor = DynamicAttributeExtractor()
    
    test_cases = [
        ("Tôi muốn laptop Dell 8GB RAM 512GB SSD", "laptop"),
        ("Áo tím size M hãng Gucci", "áo"),
        ("Giày Nike chạy bộ size 40 giá 2-3 triệu", "giày"),
    ]
    
    for user_input, category in test_cases:
        print(f"\n📝 Input: '{user_input}'")
        print(f"   Category: {category}")
        
        # Test with LLM enabled
        result = extractor.extract(user_input, category, use_llm=True)
        
        print(f"   Method: {result['method']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Extracted: {result['extracted']}")


def test_qwen_category_detection():
    """Test category detection with various products"""
    print("\n" + "="*60)
    print("TEST 3: Category Detection for New Products")
    print("="*60)
    
    detector = DynamicCategoryDetector()
    
    new_products = [
        "laptop Dell XPS",
        "điện thoại Samsung Galaxy",
        "đồng hồ Apple Watch",
        "nước hoa Chanel",
        "bao cao su Durex",
    ]
    
    for product in new_products:
        category, confidence = detector.detect_category(product)
        status = "✅" if category else "⚠️"
        print(f"{status} '{product}' → {category} (confidence: {confidence:.2f})")


def test_workflow_with_qwen():
    """Test complete workflow with Qwen LLM"""
    print("\n" + "="*60)
    print("TEST 4: Complete Workflow with Qwen")
    print("="*60)
    
    detector = DynamicCategoryDetector()
    extractor = DynamicAttributeExtractor()
    
    # Scenario: User asks about 3 products (not all hardcoded)
    scenarios = [
        "Tôi muốn mua laptop Lenovo 16GB RAM i7",
        "Thôi, tôi muốn giày Nike chạy bộ size 40",
        "Không, tôi muốn mua nước hoa Dior, nữ, giá dưới 1 triệu",
    ]
    
    for i, user_input in enumerate(scenarios, 1):
        print(f"\n🔄 Turn {i}: '{user_input}'")
        
        # Detect category
        category, conf = detector.detect_category(user_input)
        print(f"   Category: {category} (confidence: {conf:.2f})")
        
        # Extract attributes with Qwen
        result = extractor.extract(user_input, category, use_llm=True)
        print(f"   Method: {result['method']}")
        print(f"   Extracted: {result['extracted']}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING QWEN INTEGRATION WITH DYNAMIC SCHEMA")
    print("="*60)
    print("\n⚠️  Make sure Qwen is running!")
    print(f"   API Base: {os.environ.get('QWEN_API_BASE', 'http://localhost:8000/v1')}")
    print(f"   Model: {os.environ.get('QWEN_MODEL', 'qwen2.5-7b')}")
    print(f"   Provider: {os.environ.get('LLM_PROVIDER', 'qwen')}")
    
    try:
        test_qwen_basic()
        test_qwen_extraction()
        test_qwen_category_detection()
        test_workflow_with_qwen()
        
        print("\n" + "="*60)
        print("✅ TESTS COMPLETED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

# -*- coding: utf-8 -*-
"""
Test suite for CategorySchemaEvolution semantic validation

Tests semantic attribute detection:
- Fuzzy matching (synonym detection)
- Common feature filtering
- LLM semantic validation
- Integration flow
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock LLM client for testing
class MockLLMClient:
    """Mock LLM client for testing without real LLM calls"""
    
    async def complete(self, prompt: str, temperature: float = 0.3, max_tokens: int = 200) -> str:
        """Mock LLM completion"""
        
        # Simple rule-based responses for testing
        if "độ ồn" in prompt.lower():
            return json.dumps({
                "decision": "new_attribute",
                "mapped_to": None,
                "confidence": 0.95,
                "reason": "độ ồn là attribute thực tế cho washing machine"
            })
        elif "kiểu cửa" in prompt.lower() or "loại cửa" in prompt.lower():
            return json.dumps({
                "decision": "reuse",
                "mapped_to": "loại cửa",
                "confidence": 0.92,
                "reason": "kiểu cửa và loại cửa cùng ý nghĩa"
            })
        else:
            return json.dumps({
                "decision": "new_attribute",
                "mapped_to": None,
                "confidence": 0.5,
                "reason": "Không có matching pattern"
            })


# Import after mock setup
import sys
sys.path.insert(0, r'c:\Code\KLTN\services\recommender_service')
from services.category_schema_evolution import CategorySchemaEvolution


async def test_fuzzy_matching():
    """Test fuzzy matching (synonym detection)"""
    print("\n" + "="*70)
    print("TEST 1: Fuzzy Matching (Synonym Detection)")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["hãng", "loại cửa", "khối lượng giặt"]
    detected = ["thương hiệu", "kiểu cửa", "dung lượng giặt"]
    
    print(f"\nExisting attributes: {existing}")
    print(f"Detected attributes: {detected}")
    
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"\nResults:")
    print(f"  Truly new: {truly_new}")
    print(f"\nDetailed validation:")
    for attr, result in details.items():
        print(f"\n  '{attr}':")
        print(f"    Decision: {result['decision']}")
        print(f"    Mapped to: {result.get('mapped_to', 'N/A')}")
        print(f"    Confidence: {result['confidence']:.2%}")
        print(f"    Method: {result['validation_method']}")
        print(f"    Reason: {result['reason']}")
    
    # Assertions
    assert "thương hiệu" not in truly_new, "thương hiệu should be recognized as fuzzy match for hãng"
    assert "kiểu cửa" not in truly_new, "kiểu cửa should be recognized as fuzzy match for loại cửa"
    print("\n✅ Fuzzy matching test PASSED")


async def test_common_feature_filtering():
    """Test filtering of common product features"""
    print("\n" + "="*70)
    print("TEST 2: Common Feature Filtering")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["hãng", "loại lồng giặt", "khối lượng giặt"]
    detected = ["thương hiệu", "inverter", "AI DD", "OLED", "độ ồn"]
    
    print(f"\nExisting attributes: {existing}")
    print(f"Detected attributes: {detected}")
    
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"\nResults:")
    print(f"  Truly new: {truly_new}")
    print(f"\nFeature detection:")
    for attr in ["inverter", "AI DD", "OLED"]:
        if attr in details:
            result = details[attr]
            print(f"\n  '{attr}':")
            print(f"    Decision: {result['decision']}")
            print(f"    Method: {result['validation_method']}")
            print(f"    Reason: {result['reason']}")
    
    # Assertions
    assert "inverter" not in truly_new, "inverter should be filtered as feature"
    assert "AI DD" not in truly_new, "AI DD should be filtered as feature"
    assert "OLED" not in truly_new, "OLED should be filtered as feature"
    assert "độ ồn" in truly_new, "độ ồn should be recognized as true attribute"
    print("\n✅ Feature filtering test PASSED")


async def test_exact_match():
    """Test exact match detection"""
    print("\n" + "="*70)
    print("TEST 3: Exact Match Detection")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["màu sắc", "dung lượng pin", "kích thước"]
    detected = ["Màu Sắc", "DUNG LƯỢNG PIN", "Kích Thước"]  # Different casing
    
    print(f"\nExisting attributes: {existing}")
    print(f"Detected attributes (different casing): {detected}")
    
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "smartphone"
    )
    
    print(f"\nResults:")
    print(f"  Truly new: {truly_new}")
    print(f"\nValidation methods used:")
    for attr, result in details.items():
        print(f"  '{attr}': {result['validation_method']}")
    
    # Assertions
    assert len(truly_new) == 0, "All detected attributes should match exactly"
    assert all(result['validation_method'] == 'exact_match' for result in details.values())
    print("\n✅ Exact match test PASSED")


async def test_llm_semantic_validation():
    """Test LLM semantic validation for unresolved attributes"""
    print("\n" + "="*70)
    print("TEST 4: LLM Semantic Validation")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["hãng", "loại cửa", "khối lượng giặt"]
    detected = ["thương hiệu", "AI DD", "độ ồn"]
    
    print(f"\nExisting attributes: {existing}")
    print(f"Detected attributes: {detected}")
    
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"\nResults:")
    print(f"  Truly new: {truly_new}")
    print(f"\nValidation flow:")
    for attr in ["thương hiệu", "AI DD", "độ ồn"]:
        result = details[attr]
        print(f"\n  '{attr}':")
        print(f"    Flow: Exact → Fuzzy → LLM")
        print(f"    Decision: {result['decision']}")
        print(f"    Method: {result['validation_method']}")
        if result['validation_method'] == 'llm':
            print(f"    (LLM called for unresolved)")
        print(f"    Reason: {result['reason']}")
    
    # Assertions
    assert "độ ồn" in truly_new, "độ ồn should be new after LLM validation"
    assert details["thương hiệu"]["validation_method"] == "fuzzy_match"
    assert details["AI DD"]["validation_method"] == "common_feature"
    print("\n✅ LLM semantic validation test PASSED")


async def test_caching():
    """Test LLM result caching"""
    print("\n" + "="*70)
    print("TEST 5: LLM Result Caching")
    print("="*70)
    
    llm_client = MockLLMClient()
    service = CategorySchemaEvolution(llm_client=llm_client)
    
    existing = ["hãng", "loại cửa"]
    detected = ["độ ồn"]
    
    print(f"\nCalling detect_new_attributes first time...")
    truly_new_1, details_1 = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"Cache state after first call: {len(service._llm_validation_cache)} cached items")
    
    print(f"\nCalling detect_new_attributes second time (same attribute)...")
    truly_new_2, details_2 = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"Cache state after second call: {len(service._llm_validation_cache)} cached items")
    print(f"\nResults are identical: {details_1 == details_2}")
    
    # Assertions
    assert len(service._llm_validation_cache) > 0, "Cache should have items"
    assert details_1 == details_2, "Cached results should be identical"
    print("\n✅ Caching test PASSED")


async def test_confidence_scores():
    """Test confidence scoring"""
    print("\n" + "="*70)
    print("TEST 6: Confidence Scoring")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["hãng", "loại cửa", "khối lượng giặt"]
    detected = ["thương hiệu", "kiểu cửa", "khối lượng", "độ ồn"]
    
    print(f"\nExisting attributes: {existing}")
    print(f"Detected attributes: {detected}")
    
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    print(f"\nConfidence scores by validation method:")
    for attr, result in details.items():
        print(f"  '{attr}' ({result['validation_method']}): {result['confidence']:.2%}")
    
    # Assertions
    assert details["thương hiệu"]["confidence"] >= 0.75, "Fuzzy match should have high confidence"
    assert details["kiểu cửa"]["confidence"] >= 0.75, "Fuzzy match should have high confidence"
    print("\n✅ Confidence scoring test PASSED")


async def test_batch_processing():
    """Test batch processing of multiple attributes"""
    print("\n" + "="*70)
    print("TEST 7: Batch Processing")
    print("="*70)
    
    service = CategorySchemaEvolution(llm_client=MockLLMClient())
    
    existing = ["hãng", "loại cửa", "khối lượng giặt", "năng lượng tiêu thụ"]
    detected = [
        "thương hiệu",      # fuzzy match → hãng
        "AI DD",            # feature → ignore
        "inverter",         # feature → ignore
        "OLED",             # feature → ignore
        "độ ồn",            # true attribute → new
        "kiểu cửa",         # fuzzy match → loại cửa
        "điện năng",        # fuzzy match → năng lượng tiêu thụ
    ]
    
    print(f"\nProcessing {len(detected)} detected attributes...")
    truly_new, details = await service.detect_new_attributes(
        existing, detected, "washing_machine"
    )
    
    # Count by decision
    reuse_count = sum(1 for r in details.values() if r['decision'] == 'reuse')
    ignore_count = sum(1 for r in details.values() if r['decision'] == 'ignore')
    new_count = sum(1 for r in details.values() if r['decision'] == 'new_attribute')
    
    print(f"\nResults summary:")
    print(f"  Total detected: {len(detected)}")
    print(f"  Reuse: {reuse_count}")
    print(f"  Ignore: {ignore_count}")
    print(f"  New: {new_count}")
    print(f"  Total: {reuse_count + ignore_count + new_count}")
    
    print(f"\nTruly new attributes: {truly_new}")
    
    # Assertions
    assert len(truly_new) > 0, "Should have some new attributes"
    assert reuse_count > 0, "Should have some reused attributes"
    assert ignore_count > 0, "Should have some ignored attributes"
    print("\n✅ Batch processing test PASSED")


async def main():
    """Run all tests"""
    print("\n" + "🧪 CategorySchemaEvolution Semantic Validation Tests ".center(70, "="))
    
    try:
        await test_fuzzy_matching()
        await test_common_feature_filtering()
        await test_exact_match()
        await test_llm_semantic_validation()
        await test_caching()
        await test_confidence_scores()
        await test_batch_processing()
        
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70 + "\n")
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
    except Exception as e:
        logger.exception(f"❌ Test error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

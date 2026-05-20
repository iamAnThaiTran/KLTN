#!/usr/bin/env python3
"""
Simple test script to run inside recommender-service container
Loop through 200 test cases and check coverage %
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add app to path
sys.path.insert(0, '/app')

from core.orchestrator import RecommendationOrchestrator

def compare_category(expected: str, predicted: str) -> bool:
    """Check if category matches"""
    exp = expected.strip().lower()
    pred = predicted.strip().lower()
    return exp == pred or exp in pred or pred in exp

def check_attributes(expected: Dict, predicted: list) -> int:
    """Check how many expected attributes are found in predicted"""
    if not expected:
        return 1  # All match if no expected attrs
    
    matches = 0
    for attr_name, attr_value in expected.items():
        attr_value_str = str(attr_value).lower()
        for pred in predicted:
            pred_values = pred.get('expected_values', [])
            for val in pred_values:
                if attr_value_str in str(val).lower():
                    matches += 1
                    break
    
    return matches / len(expected)

def main():
    print("="*80)
    print("🧪 Comprehensive Intent Analysis Test")
    print("="*80)
    
    # Load test data
    try:
        with open('/app/testAC.json', 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        print(f"✓ Loaded {len(test_cases)} test cases\n")
    except Exception as e:
        print(f"✗ Failed to load test data: {e}")
        sys.exit(1)
    
    # Initialize orchestrator
    try:
        orchestrator = RecommendationOrchestrator()
        print("✓ Orchestrator initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        sys.exit(1)
    
    # Run tests
    results = {
        "total": 0,
        "category_match": 0,
        "category_partial": 0,
        "attr_100_percent": 0,
        "attr_50_plus": 0,
        "failed": 0
    }
    
    print("Running tests...")
    print("-"*80)
    
    for idx, test in enumerate(test_cases, 1):
        try:
            query = test.get('query', '')
            expected_cat = test.get('expected_category', '')
            expected_attrs = test.get('expected_attributes', {})
            
            # Call LLM
            result = orchestrator._comprehensive_intent_analysis(
                merged_intent=query,
                conversation_state=None
            )
            
            pred_cat = result.get('category', '')
            pred_attrs = result.get('extracted_attributes', [])
            
            # Check category
            cat_match = compare_category(expected_cat, pred_cat)
            
            # Check attributes
            attr_coverage = check_attributes(expected_attrs, pred_attrs)
            
            # Update results
            results["total"] += 1
            if cat_match:
                results["category_match"] += 1
            else:
                results["category_partial"] += 1
            
            if attr_coverage >= 1.0:
                results["attr_100_percent"] += 1
            elif attr_coverage >= 0.5:
                results["attr_50_plus"] += 1
            
            # Print progress
            status = "✓" if cat_match and attr_coverage >= 0.8 else "⚠" if cat_match or attr_coverage >= 0.5 else "✗"
            print(f"[{idx:3d}] {status} {query[:50]:50} | Cat: {cat_match:5} | Attr: {attr_coverage*100:5.1f}%")
            
        except Exception as e:
            results["failed"] += 1
            print(f"[{idx:3d}] ✗ ERROR: {str(e)[:60]}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80)
    
    total = results["total"]
    cat_pct = (results["category_match"] / total * 100) if total > 0 else 0
    cat_cov = ((results["category_match"] + results["category_partial"]) / total * 100) if total > 0 else 0
    attr_pct = (results["attr_100_percent"] / total * 100) if total > 0 else 0
    attr_cov = ((results["attr_100_percent"] + results["attr_50_plus"]) / total * 100) if total > 0 else 0
    
    print(f"\n📌 CATEGORY:")
    print(f"   Exact Match: {results['category_match']:3}/{total} ({cat_pct:5.1f}%)")
    print(f"   Partial:    {results['category_partial']:3}/{total}")
    print(f"   Coverage:   {results['category_match'] + results['category_partial']:3}/{total} ({cat_cov:5.1f}%)")
    
    print(f"\n📌 ATTRIBUTES:")
    print(f"   100% Match: {results['attr_100_percent']:3}/{total} ({attr_pct:5.1f}%)")
    print(f"   50%+ Match: {results['attr_50_plus']:3}/{total}")
    print(f"   Coverage:   {results['attr_100_percent'] + results['attr_50_plus']:3}/{total} ({attr_cov:5.1f}%)")
    
    print(f"\n⚠️  FAILED:    {results['failed']:3}/{total}")
    
    print("\n" + "="*80)
    if cat_pct >= 85 and attr_pct >= 80:
        print("✅ RESULTS ACCEPTED - Coverage is good!")
    elif cat_pct >= 70 and attr_pct >= 60:
        print("⚠️  RESULTS PARTIAL - Could be better")
    else:
        print("❌ RESULTS POOR - Needs improvement")
    print("="*80)

if __name__ == "__main__":
    main()

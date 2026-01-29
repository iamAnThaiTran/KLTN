#!/usr/bin/env python3
"""
Test: Category Validation Flow
Verify that category validation works before crawling
"""

import asyncio
from app.services.category_validator import CategoryValidator

async def test_category_validation():
    """Test CategoryValidator"""
    validator = CategoryValidator()
    
    test_cases = [
        ("giày", "Exact match with existing category"),
        ("giày thể thao nam", "Variant that should map to Giay"),
        ("đồng hồ", "Another existing category"),
        ("đồng hồ thông minh", "Smartwatch variant"),
        ("laptop", "Existing category"),
        ("tai nghe", "Existing category"),
    ]
    
    print("=" * 80)
    print("CATEGORY VALIDATION TEST")
    print("=" * 80)
    
    for user_input, description in test_cases:
        print(f"\nTest: {user_input}")
        print(f"   {description}")
        
        result = validator.validate_category(user_input)
        
        print(f"   Result:")
        print(f"     Success: {result['success']}")
        print(f"     Category: {result['category']}")
        print(f"     ID: {result['category_id']}")
        print(f"     Status: {result['status']}")
        print(f"     Reason: {result['reason']}")
        
        if not result['success']:
            print("   FAILED")
        else:
            print("   PASSED")

if __name__ == "__main__":
    asyncio.run(test_category_validation())

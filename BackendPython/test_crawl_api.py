#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the crawl-products endpoint
"""

import asyncio
import json
from app.db.sku_repository import SKURepository
from app.services.category_validator import CategoryValidator

async def test_crawl_filter():
    """Test crawl and filter flow"""
    
    repo = SKURepository()
    validator = CategoryValidator()
    
    print("=" * 80)
    print("TEST 1: Validate category 'giày'")
    print("=" * 80)
    
    result = validator.validate_category("giày")
    print(f"\n✅ Validation result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if not result["success"]:
        print("❌ Category validation failed!")
        return
    
    category_name = result["category"]
    print(f"\n✅ Category mapped to: {category_name}")
    
    # Get slug
    slug = repo.get_category_slug_from_name(category_name)
    print(f"✅ Category slug: {slug}")
    
    if not slug:
        print("❌ Could not find category slug!")
        return
    
    print("\n" + "=" * 80)
    print(f"TEST 2: Get available filters for category '{slug}'")
    print("=" * 80)
    
    filters = repo.get_available_filters(slug)
    print(f"\n✅ Available filters:")
    for f in filters:
        print(f"\n  Attribute: {f['attribute_name']}")
        print(f"  Display name: {f['display_name']}")
        print(f"  Data type: {f['data_type']}")
        print(f"  Options count: {len(f.get('options', []))}")
        if f.get('options'):
            for opt in f['options'][:3]:  # Show first 3
                print(f"    - {opt['attribute_value']}: {opt['product_count']} products")
            if len(f['options']) > 3:
                print(f"    ... and {len(f['options']) - 3} more")
    
    print("\n" + "=" * 80)
    print(f"TEST 3: Search products without filters")
    print("=" * 80)
    
    products, total = repo.search_products(
        category_slug=slug,
        filters={},
        page=1,
        page_size=5
    )
    
    print(f"\n✅ Found {total} products")
    print(f"✅ Showing {len(products)} products:")
    
    for p in products:
        print(f"\n  Product: {p['title']}")
        print(f"  Brand: {p['brand']}")
        print(f"  SKUs: {len(p['skus'])}")
        if p['skus']:
            first_sku = p['skus'][0]
            print(f"    - Price: {first_sku['price']:,}")
            if first_sku.get('attributes'):
                for attr_name, attr_val in list(first_sku['attributes'].items())[:3]:
                    print(f"      {attr_name}: {attr_val}")
    
    print("\n" + "=" * 80)
    print(f"TEST 4: Search products with filters (size=42, color=Đen)")
    print("=" * 80)
    
    filtered_products, filtered_total = repo.search_products(
        category_slug=slug,
        filters={
            "size": ["42"],
            "color": ["Đen"]
        },
        page=1,
        page_size=5
    )
    
    print(f"\n✅ Found {filtered_total} products with size=42, color=Đen")
    print(f"✅ Showing {len(filtered_products)} products:")
    
    for p in filtered_products:
        print(f"\n  Product: {p['title']}")
        if p['skus']:
            for sku in p['skus'][:2]:
                if sku.get('attributes'):
                    attrs_str = ", ".join([f"{k}={v}" for k, v in sku['attributes'].items()])
                    print(f"    SKU: {attrs_str}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_crawl_filter())

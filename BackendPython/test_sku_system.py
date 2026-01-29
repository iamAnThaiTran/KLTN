# test_sku_system.py
"""
Test SKU-based product system
Demo queries and API usage
"""

import os
from dotenv import load_dotenv
from app.db.sku_repository import SKURepository
import json

load_dotenv()

def test_search_products():
    """Test product search with filters"""
    print("\n" + "="*70)
    print("TEST 1: Search products with filters")
    print("="*70)
    
    repo = SKURepository()
    
    # Test 1: Search giày size 42
    print("\n📍 Search: Giày size 42")
    products, total = repo.search_products(
        category_slug="giay",
        filters={"size": ["42"]},
        page=1,
        page_size=10
    )
    
    print(f"✓ Found {total} products")
    for p in products:
        print(f"\n  Product: {p['title']}")
        print(f"  Brand: {p['brand']}")
        print(f"  Price range: {p['min_price']:,.0f} - {p['max_price']:,.0f} VNĐ")
        print(f"  SKUs: {len(p['skus'])}")
        for sku in p['skus']:
            attrs_str = ", ".join([f"{k}={v}" for k, v in sku['attributes'].items()])
            print(f"    - {sku['sku_code']}: {sku['price']:,.0f} VNĐ | {attrs_str}")
    
    # Test 2: Search giày size 42 AND color Đen
    print("\n" + "-"*70)
    print("📍 Search: Giày size 42 AND color Đen")
    products, total = repo.search_products(
        category_slug="giay",
        filters={
            "size": ["42"],
            "color": ["Đen"]
        },
        page=1,
        page_size=10
    )
    
    print(f"✓ Found {total} products")
    for p in products:
        print(f"\n  Product: {p['title']}")
        matching_skus = [
            sku for sku in p['skus']
            if sku['attributes'].get('size') == '42' 
            and sku['attributes'].get('color') == 'Đen'
        ]
        print(f"  Matching SKUs: {len(matching_skus)}")
        for sku in matching_skus:
            print(f"    - {sku['sku_code']}: {sku['price']:,.0f} VNĐ")
    
    # Test 3: Search with price range
    print("\n" + "-"*70)
    print("📍 Search: Giày price 2M - 3M")
    products, total = repo.search_products(
        category_slug="giay",
        filters={},
        min_price=2000000,
        max_price=3000000,
        page=1,
        page_size=10
    )
    
    print(f"✓ Found {total} products in price range")


def test_get_filters():
    """Test getting available filters"""
    print("\n" + "="*70)
    print("TEST 2: Get available filters for UI")
    print("="*70)
    
    repo = SKURepository()
    
    filters = repo.get_available_filters("giay")
    
    print(f"\n✓ Found {len(filters)} filter groups\n")
    
    for filter_group in filters:
        print(f"📋 {filter_group['display_name']} ({filter_group['attribute_name']})")
        print(f"   Type: {filter_group['data_type']}")
        
        if filter_group['options']:
            print(f"   Options ({len(filter_group['options'])}):")
            for opt in filter_group['options'][:5]:  # Show first 5
                print(f"     ☑ {opt['attribute_value']} ({opt['product_count']} products)")
            
            if len(filter_group['options']) > 5:
                print(f"     ... and {len(filter_group['options']) - 5} more")
        print()


def test_get_product():
    """Test getting single product"""
    print("\n" + "="*70)
    print("TEST 3: Get single product by ID")
    print("="*70)
    
    repo = SKURepository()
    
    product = repo.get_product_by_id(1)
    
    if product:
        print(f"\n✓ Product: {product['title']}")
        print(f"  Brand: {product['brand']}")
        print(f"  Category ID: {product['category_id']}")
        print(f"  Source: {product['source']}")
        print(f"  URL: {product['product_url']}")
        print(f"\n  SKUs ({len(product['skus'])}):")
        
        for sku in product['skus']:
            attrs = ", ".join([f"{k}={v}" for k, v in sku['attributes'].items()])
            availability = "✓ In stock" if sku['stock'] > 0 else "✗ Out of stock"
            print(f"\n    {sku['sku_code']}")
            print(f"      Price: {sku['price']:,.0f} VNĐ")
            print(f"      Attributes: {attrs}")
            print(f"      Stock: {sku['stock']} | {availability}")
    else:
        print("❌ Product not found")


def show_example_ui_json():
    """Show example JSON for UI"""
    print("\n" + "="*70)
    print("EXAMPLE: JSON Response for UI")
    print("="*70)
    
    example_response = {
        "products": [
            {
                "id": 1,
                "title": "Nike Air Max 2024",
                "brand": "Nike",
                "thumbnail": "nike_air_max.jpg",
                "min_price": 2500000,
                "max_price": 2500000,
                "available_count": 3,
                "skus": [
                    {
                        "id": 1,
                        "sku_code": "NIKE-AM-42-BLACK",
                        "price": 2500000,
                        "stock": 10,
                        "attributes": {
                            "size": "42",
                            "color": "Đen",
                            "gender": "Nam"
                        }
                    }
                ]
            }
        ],
        "filters": [
            {
                "attribute_name": "size",
                "display_name": "Kích cỡ",
                "data_type": "enum",
                "options": [
                    {"attribute_value": "42", "product_count": 10},
                    {"attribute_value": "43", "product_count": 8}
                ]
            },
            {
                "attribute_name": "color",
                "display_name": "Màu sắc",
                "data_type": "enum",
                "options": [
                    {"attribute_value": "Đen", "product_count": 15},
                    {"attribute_value": "Trắng", "product_count": 12}
                ]
            }
        ],
        "total": 100,
        "page": 1,
        "total_pages": 5
    }
    
    print("\nExample API response:")
    print(json.dumps(example_response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print("\n🧪 TESTING SKU-BASED PRODUCT SYSTEM")
    
    test_search_products()
    test_get_filters()
    test_get_product()
    show_example_ui_json()
    
    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70)

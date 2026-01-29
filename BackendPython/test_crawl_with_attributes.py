#!/usr/bin/env python3
"""
Test crawl via API endpoint (works in uvicorn)

Steps:
1. Start uvicorn server: poetry run uvicorn app.main:app --reload
2. In another terminal, run this script
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"

def test_crawl_giay_with_attributes():
    """Test crawling giày with full attribute extraction"""
    print("=" * 80)
    print("🔍 Test: Crawl Giày with Attribute Extraction")
    print("=" * 80)
    
    # Crawl giày (shoes) - luôn extract attributes từ Tiki API
    response = httpx.post(
        f"{BASE_URL}/api/v1/products/crawl",
        json={
            "category": "giày",
            "attributes": {}  # User k specify, nhưng crawler sẽ extract toàn bộ
        },
        timeout=120.0  # 2 min timeout vì crawl detail mất lâu
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        products = data.get("data", {}).get("products", [])
        print(f"\n✅ Crawled {len(products)} products\n")
        
        # Show first 3 products with attributes
        for i, product in enumerate(products[:3], 1):
            print(f"📦 Product {i}:")
            print(f"   Title: {product.get('title', 'N/A')}")
            print(f"   Brand: {product.get('brand', 'N/A')}")
            print(f"   Price: {product.get('price', 'N/A')}")
            print(f"   Discount: {product.get('discount', 'N/A')}")
            
            # KEY: extracted_attributes từ Tiki API
            attributes = product.get('extracted_attributes', {})
            if attributes:
                print(f"   ✨ Extracted Attributes:")
                for key, value in attributes.items():
                    if isinstance(value, list):
                        print(f"      - {key}: {', '.join(str(v) for v in value[:3])}{'...' if len(value) > 3 else ''}")
                    else:
                        print(f"      - {key}: {value}")
            else:
                print(f"   ⚠️  No attributes extracted")
            print()
    else:
        print(f"❌ Error: {data}")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)
    
    try:
        test_crawl_giay_with_attributes()
    except httpx.ConnectError:
        print("❌ Cannot connect to API server")
        print("Make sure uvicorn is running: poetry run uvicorn app.main:app --reload")

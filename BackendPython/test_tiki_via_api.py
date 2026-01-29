"""
Test Tiki crawler qua API (vì uvicorn hoạt động bình thường)
"""

import requests

def test_via_api():
    print("=" * 70)
    print("🧪 TEST TIKI QUA API")
    print("=" * 70)
    
    # Start server first: poetry run uvicorn main:app
    print("\n⚠️  Đảm bảo server đang chạy:")
    print("    poetry run uvicorn main:app")
    print()
    
    input("Press Enter khi server đã chạy...")
    
    # Test API
    print("\n📡 Calling API /api/query...")
    
    response = requests.post(
        "http://127.0.0.1:8000/api/query",
        json={
            "user_input": "tìm giày thể thao",
            "conversation_id": None
        },
        timeout=60
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Response: {data.get('response_type')}")
        
        if "products" in data:
            products = data["products"]
            print(f"📦 Found {len(products)} products")
            
            for i, p in enumerate(products[:3], 1):
                print(f"\n{i}. {p.get('name', 'N/A')[:60]}")
                print(f"   Price: {p.get('price', 0):,} VNĐ")
                print(f"   Source: {p.get('source', 'N/A')}")
            
            # Now save to SKU database
            print("\n💾 Saving to SKU database...")
            from app.services.crawler_adapter import CrawlerToSKUAdapter
            
            adapter = CrawlerToSKUAdapter()
            result = adapter.save_crawled_products(products[:5], "giày")
            
            if result['success']:
                print(f"✅ Saved {result['products_saved']} products")
            else:
                print(f"❌ Error: {result.get('error')}")
        else:
            print("⚠️ No products in response")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_via_api()

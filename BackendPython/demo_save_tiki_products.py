#!/usr/bin/env python
"""
Demo: Save mock Tiki products to SKU database
Shows how crawler data flows into SKU system
"""

from app.services.crawler_adapter import CrawlerToSKUAdapter
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def demo_save_products():
    print("=" * 70)
    print("🧪 DEMO: SAVE TIKI PRODUCTS TO SKU DATABASE")
    print("=" * 70)
    
    # Mock data from Tiki crawler
    mock_products = [
        {
            "title": "Giày Thể Thao Nam Adidas Ultraboost 22 - Size 42 - Màu Đen",
            "price": 3500000,
            "brand": "Adidas",
            "link": "https://tiki.vn/giay-adidas-ultraboost-42-den-p123456.html",
            "image": "https://salt.tikicdn.com/cache/750x750/ts/product/adidas.jpg",
            "source": "tiki",
            "discount": 20,
            "sold": 250
        },
        {
            "title": "Giày Sneaker Nữ Nike Air Force 1 Size 38 Trắng",
            "price": 2800000,
            "brand": "Nike",
            "link": "https://tiki.vn/giay-nike-airforce1-38-trang-p234567.html",
            "image": "https://salt.tikicdn.com/cache/750x750/ts/product/nike.jpg",
            "source": "tiki",
            "discount": 15,
            "sold": 180
        },
        {
            "title": "Giày Chạy Bộ Nam New Balance Fresh Foam 1080v12 Size 43 Xanh",
            "price": 4200000,
            "brand": "New Balance",
            "link": "https://tiki.vn/giay-newbalance-1080v12-43-xanh-p345678.html",
            "image": "https://salt.tikicdn.com/cache/750x750/ts/product/nb.jpg",
            "source": "tiki",
            "discount": 10,
            "sold": 95
        }
    ]
    
    print(f"\n📦 Mock products from Tiki: {len(mock_products)}")
    for i, p in enumerate(mock_products, 1):
        print(f"   {i}. {p['title'][:50]}... - {p['price']:,} VNĐ")
    
    # Save to database
    print("\n💾 Saving to SKU database...")
    adapter = CrawlerToSKUAdapter()
    result = adapter.save_crawled_products(mock_products, "giày")
    
    if result['success']:
        print(f"✅ Successfully saved!")
        print(f"   Products saved: {result['products_saved']}")
        print(f"   SKUs saved: {result['skus_saved']}")
    else:
        print(f"❌ Error: {result.get('error')}")
        return
    
    # Show what's in database
    print("\n🔍 Database contents (category: Giày):")
    print("-" * 70)
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.id,
            p.title,
            p.brand,
            s.sku_code,
            s.price,
            s.stock,
            COUNT(sa.sku_id) as attr_count
        FROM products p
        JOIN skus s ON s.product_id = p.id
        LEFT JOIN sku_attributes sa ON sa.sku_id = s.id
        WHERE p.category_id = 1
        GROUP BY p.id, p.title, p.brand, s.id, s.sku_code, s.price, s.stock
        ORDER BY p.created_at DESC
        LIMIT 5
    """)
    
    products = cursor.fetchall()
    
    for p in products:
        prod_id, title, brand, sku_code, price, stock, attr_count = p
        print(f"\n📦 Product #{prod_id}: {brand}")
        print(f"   Title: {title[:60]}")
        print(f"   SKU: {sku_code}")
        print(f"   Price: {price:,} VNĐ")
        print(f"   Stock: {stock}")
        print(f"   Attributes: {attr_count}")
        
        # Show attributes
        cursor.execute("""
            SELECT attribute_name, attribute_value
            FROM sku_attributes sa
            JOIN skus s ON s.id = sa.sku_id
            JOIN products p ON p.id = s.product_id
            WHERE p.id = %s
        """, (prod_id,))
        
        attrs = cursor.fetchall()
        if attrs:
            print("   Details:")
            for attr_name, attr_value in attrs:
                print(f"     • {attr_name}: {attr_value}")
    
    # Show filter options
    print("\n" + "=" * 70)
    print("🎯 AVAILABLE FILTERS (for UI)")
    print("=" * 70)
    
    cursor.execute("""
        SELECT 
            sa.attribute_name,
            sa.attribute_value,
            COUNT(DISTINCT s.product_id) as product_count
        FROM sku_attributes sa
        JOIN skus s ON s.id = sa.sku_id
        JOIN products p ON p.id = s.product_id
        WHERE p.category_id = 1
          AND s.is_available = true
        GROUP BY sa.attribute_name, sa.attribute_value
        ORDER BY sa.attribute_name, product_count DESC
    """)
    
    filters = {}
    for attr_name, attr_value, count in cursor.fetchall():
        if attr_name not in filters:
            filters[attr_name] = []
        filters[attr_name].append((attr_value, count))
    
    for filter_name, options in filters.items():
        print(f"\n📋 {filter_name.upper()}")
        for value, count in options:
            print(f"   ☑ {value} ({count} products)")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETED!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   1. Fix Playwright for Python 3.14 (or use Python 3.11)")
    print("   2. Integrate crawler_adapter into orchestrator")
    print("   3. Auto-save products when crawling")


if __name__ == "__main__":
    demo_save_products()

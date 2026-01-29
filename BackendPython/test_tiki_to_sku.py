#!/usr/bin/env python
"""
Demo: Tiki crawler → SKU database
Test crawling products and saving to new SKU system
"""

import asyncio
import sys
from app.crawler.crawler import TikiCrawler
from app.services.crawler_adapter import CrawlerToSKUAdapter

# Fix Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def test_tiki_to_sku():
    print("=" * 70)
    print("🧪 TEST: TIKI CRAWLER → SKU DATABASE")
    print("=" * 70)
    
    # 1. Crawl products from Tiki
    print("\n📡 Step 1: Crawling Tiki...")
    crawler = TikiCrawler()
    
    # Test with "giày thể thao"
    products = await crawler.crawl(
        category="giày thể thao",
        attributes=None,  # No specific filters
        get_details=False  # Just get product list
    )
    
    print(f"✅ Crawled {len(products)} products from Tiki")
    
    if products:
        print("\n📦 Sample product:")
        sample = products[0]
        print(f"  Title: {sample.get('title')}")
        print(f"  Price: {sample.get('price'):,} VNĐ")
        print(f"  Brand: {sample.get('brand')}")
        print(f"  Link: {sample.get('link')[:60]}...")
    
    # 2. Save to SKU database
    print("\n💾 Step 2: Saving to SKU database...")
    adapter = CrawlerToSKUAdapter()
    
    result = adapter.save_crawled_products(products[:5], "giày")  # Save first 5 products
    
    if result['success']:
        print(f"✅ Successfully saved!")
        print(f"   Products saved: {result['products_saved']}")
        print(f"   SKUs saved: {result['skus_saved']}")
        print(f"   Category ID: {result['category_id']}")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # 3. Verify in database
    print("\n🔍 Step 3: Verifying database...")
    
    import psycopg2
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    # Count products
    cursor.execute("SELECT COUNT(*) FROM products WHERE category_id = 1")
    product_count = cursor.fetchone()[0]
    print(f"   Products in DB (category Giày): {product_count}")
    
    # Count SKUs
    cursor.execute("""
        SELECT COUNT(*) FROM skus s
        JOIN products p ON p.id = s.product_id
        WHERE p.category_id = 1
    """)
    sku_count = cursor.fetchone()[0]
    print(f"   SKUs in DB: {sku_count}")
    
    # Get latest product with SKU
    cursor.execute("""
        SELECT 
            p.title,
            p.brand,
            s.sku_code,
            s.price,
            s.stock
        FROM products p
        JOIN skus s ON s.product_id = p.id
        WHERE p.category_id = 1
        ORDER BY p.created_at DESC
        LIMIT 1
    """)
    
    latest = cursor.fetchone()
    if latest:
        print(f"\n   📌 Latest product:")
        print(f"      Title: {latest[0]}")
        print(f"      Brand: {latest[1]}")
        print(f"      SKU: {latest[2]}")
        print(f"      Price: {latest[3]:,} VNĐ")
        print(f"      Stock: {latest[4]}")
        
        # Get attributes
        cursor.execute("""
            SELECT attribute_name, attribute_value
            FROM sku_attributes
            WHERE sku_id = (
                SELECT s.id FROM skus s
                JOIN products p ON p.id = s.product_id
                WHERE p.category_id = 1
                ORDER BY p.created_at DESC
                LIMIT 1
            )
        """)
        
        attributes = cursor.fetchall()
        if attributes:
            print(f"      Attributes:")
            for attr_name, attr_value in attributes:
                print(f"        - {attr_name}: {attr_value}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_tiki_to_sku())

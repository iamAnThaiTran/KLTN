#!/usr/bin/env python
"""
Test Tiki crawler thật và save vào database
"""

import asyncio
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Import TRƯỚC khi set event loop policy
from app.crawler.crawler import TikiCrawler
from app.services.crawler_adapter import CrawlerToSKUAdapter

# Không cần set lại event loop policy vì crawler.py đã set rồi

async def test_real_tiki():
    print("=" * 70)
    print("🔥 TEST TIKI CRAWLER THẬT")
    print("=" * 70)
    
    # 1. Crawl from Tiki
    print("\n📡 Step 1: Crawling Tiki.vn cho 'giày thể thao'...")
    crawler = TikiCrawler()
    
    try:
        products = await crawler.crawl(
            category="giày thể thao",
            attributes=None,
            get_details=False  # Chỉ lấy danh sách, không crawl detail
        )
        
        print(f"✅ Crawled {len(products)} products")
        
        if products:
            print("\n📦 Sample products:")
            for i, p in enumerate(products[:3], 1):
                print(f"\n{i}. {p.get('title', 'N/A')[:60]}...")
                print(f"   Price: {p.get('price', 0):,} VNĐ")
                print(f"   Brand: {p.get('brand', 'N/A')}")
                print(f"   Link: {p.get('link', '')[:50]}...")
        else:
            print("⚠️ Không crawl được sản phẩm nào")
            return
        
        # 2. Save to database
        print("\n💾 Step 2: Saving to database...")
        adapter = CrawlerToSKUAdapter()
        
        # Save first 5 products
        result = adapter.save_crawled_products(products[:5], "giày")
        
        if result['success']:
            print(f"✅ Saved successfully!")
            print(f"   Products: {result['products_saved']}")
            print(f"   SKUs: {result['skus_saved']}")
        else:
            print(f"❌ Error: {result.get('error')}")
            
        # 3. Verify
        print("\n🔍 Step 3: Verifying in database...")
        
        import psycopg2
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM products WHERE category_id = 1
        """)
        total_products = cursor.fetchone()[0]
        print(f"   Total products (Giày): {total_products}")
        
        cursor.execute("""
            SELECT p.title, s.price, s.stock
            FROM products p
            JOIN skus s ON s.product_id = p.id
            WHERE p.category_id = 1
            ORDER BY p.created_at DESC
            LIMIT 3
        """)
        
        latest = cursor.fetchall()
        if latest:
            print("\n   📌 Latest products:")
            for title, price, stock in latest:
                print(f"      • {title[:50]}... - {price:,} VNĐ")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    # Dùng cách tạo event loop giống uvicorn
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_real_tiki())
    finally:
        loop.close()

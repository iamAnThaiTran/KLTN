#!/usr/bin/env python
"""
Test crawl details và save vào SKU database
"""

import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)

from app.crawler.crawler import TikiCrawler

# Không cần set event loop policy vì crawler.py đã set rồi

async def test_crawl_with_details():
    print("=" * 70)
    print("🧪 TEST: CRAWL TIKI WITH DETAILS → SKU DATABASE")
    print("=" * 70)
    
    crawler = TikiCrawler()
    
    # Test crawl với get_details=True
    print("\n📡 Crawling 'giày thể thao' with DETAILS...")
    products = await crawler.crawl(
        category="giày thể thao",
        attributes=None,
        get_details=True  # BẬT crawl details
    )
    
    print(f"\n✅ Crawled {len(products)} products")
    
    if products:
        print("\n" + "=" * 70)
        print("📦 SAMPLE PRODUCT WITH ATTRIBUTES:")
        print("=" * 70)
        
        sample = products[0]
        print(f"\nTitle: {sample.get('title')}")
        print(f"Price: {sample.get('price'):,} VNĐ")
        print(f"Brand: {sample.get('brand')}")
        
        if 'attributes' in sample:
            attrs = sample['attributes']
            print(f"\n🎯 Extracted Attributes:")
            print(f"   Sizes: {attrs.get('sizes', [])}")
            print(f"   Colors: {attrs.get('colors', [])}")
            print(f"   Materials: {attrs.get('materials', [])}")
            print(f"   Category: {attrs.get('category', 'N/A')}")
            print(f"   Stock: {attrs.get('stock', False)}")
    
    # Verify in database
    print("\n" + "=" * 70)
    print("🔍 VERIFYING DATABASE:")
    print("=" * 70)
    
    import psycopg2
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    # Check latest products
    cursor.execute("""
        SELECT 
            p.id,
            p.title,
            p.brand,
            COUNT(DISTINCT s.id) as sku_count,
            COUNT(DISTINCT sa.attribute_name) as attr_count
        FROM products p
        LEFT JOIN skus s ON s.product_id = p.id
        LEFT JOIN sku_attributes sa ON sa.sku_id = s.id
        WHERE p.category_id = 1
        GROUP BY p.id, p.title, p.brand
        ORDER BY p.created_at DESC
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    print("\n📊 Latest products in database:")
    for prod_id, title, brand, sku_count, attr_count in results:
        print(f"\n  [{prod_id}] {brand}")
        print(f"      {title[:60]}...")
        print(f"      SKUs: {sku_count} | Attributes: {attr_count}")
        
        # Show attributes
        cursor.execute("""
            SELECT DISTINCT sa.attribute_name, sa.attribute_value
            FROM sku_attributes sa
            JOIN skus s ON s.id = sa.sku_id
            WHERE s.product_id = %s
            LIMIT 10
        """, (prod_id,))
        
        attrs = cursor.fetchall()
        if attrs:
            print(f"      Attrs: {', '.join([f'{k}={v}' for k,v in attrs])}")
    
    # Check category attributes
    print("\n" + "=" * 70)
    print("📋 CATEGORY ATTRIBUTES DEFINED:")
    print("=" * 70)
    
    cursor.execute("""
        SELECT name, display_name, data_type, possible_values
        FROM category_attributes
        WHERE category_id = 1
        ORDER BY name
    """)
    
    cat_attrs = cursor.fetchall()
    print(f"\nCategory 'Giày' has {len(cat_attrs)} attributes defined:")
    for name, display_name, dtype, pvalues in cat_attrs:
        print(f"  • {display_name} ({name}) - {dtype}")
        if pvalues:
            import json
            vals = json.loads(pvalues) if isinstance(pvalues, str) else pvalues
            print(f"    Possible values: {vals[:5]}...")  # Show first 5
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_crawl_with_details())
    finally:
        loop.close()

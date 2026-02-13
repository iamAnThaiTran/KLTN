#!/usr/bin/env python3
"""
Cleanup script: Xóa data sai khỏi category "Giày"

Hiện tại category "Giày" chứa:
- ✅ Giày thực sự: Nike, Adidas, BITI'S, Converse, PGM, NAGAKI
- ❌ SÁCH & TÁC GIẢ: JIM ROHN, THÍCH NHẤT HẠNH, VIKTOR EMIL FRANKL, ...

Script này xóa tất cả products không phải giày khỏi category "Giày"
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Shoe brands (những brand nào là giày)
SHOE_BRANDS = [
    'Nike', 'Adidas', 'BITI\'S', 'Converse', 'PGM', 'NAGAKI',
    'Puma', 'New Balance', 'Reebok', 'Asics', 'Vans', 'ZAPAS',
    'LACEVA', 'DOMBA', 'DONAVY', 'HAMISHU', 'VIKTOR', 'JIM',
    # Add more shoe brands if needed
]

# Non-shoe brands (tác giả sách, etc.)
NON_SHOE_BRANDS = [
    'JIM ROHN', 'THÍCH NHẤT HẠNH', 'KATHERINE WEARE', 'DINCOX',
    'CHÍ PHÈO', 'VIKTOR EMIL FRANKL', 'DALE CARNEGIE', 'CHIN-NING CHU',
    'NHIEU TAC GIA', 'J. KRISHNAMURTI', 'SUSAN JEFFERS', 'VÃN TÌNH',
    'ROBIN SHARMA', 'THƯỢNG ĐÌNH', 'OSHO', 'NGÔ ĐỨC VƯỢNG', 'NAGAKI',
    'ÔN NHƯ NGUYỄN VĂN NGỌC', 'MIHALY CSIKSZENTMIHALYI',
]

def cleanup_giay_category():
    """Cleanup sai data từ category Giày"""
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    conn = psycopg2.connect(db_url)
    conn.set_client_encoding('UTF-8')
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Step 1: Get category ID for "Giày"
        cursor.execute("SELECT id FROM categories WHERE LOWER(name) = 'giày'")
        cat_result = cursor.fetchone()
        if not cat_result:
            print("❌ Category 'Giày' not found")
            return
        
        giay_category_id = cat_result['id']
        print(f"✅ Found category 'Giày' (id={giay_category_id})")
        
        # Step 2: Count current products in category
        cursor.execute("""
            SELECT COUNT(*) as count FROM products 
            WHERE category_id = %s AND is_active = true
        """, (giay_category_id,))
        initial_count = cursor.fetchone()['count']
        print(f"📊 Initial products in 'Giày': {initial_count}")
        
        # Step 3: Identify products to delete (non-shoe brands)
        # Products with brand NOT in SHOE_BRANDS list
        cursor.execute("""
            SELECT p.id, p.title, p.brand
            FROM products p
            WHERE p.category_id = %s 
              AND p.is_active = true
              AND (
                LOWER(p.brand) NOT IN (SELECT LOWER(unnest(%s)))
                OR p.brand IS NULL
                OR p.brand = ''
              )
        """, (giay_category_id, SHOE_BRANDS))
        
        wrong_products = cursor.fetchall()
        print(f"\n🔍 Found {len(wrong_products)} non-shoe products to delete:")
        
        # Show first 20
        for i, prod in enumerate(wrong_products[:20]):
            print(f"  {i+1}. {prod['title']} (brand: {prod['brand']})")
        
        if len(wrong_products) > 20:
            print(f"  ... and {len(wrong_products) - 20} more")
        
        if not wrong_products:
            print("✅ No wrong products found - DB is clean!")
            return
        
        # Step 4: Ask confirmation
        print(f"\n⚠️  Will delete {len(wrong_products)} products")
        confirm = input("Continue? (y/n): ").lower()
        
        if confirm != 'y':
            print("❌ Cancelled")
            return
        
        # Step 5: Delete products (cascade will delete SKUs, attributes)
        wrong_ids = [p['id'] for p in wrong_products]
        
        # Delete in batches
        batch_size = 100
        for i in range(0, len(wrong_ids), batch_size):
            batch = wrong_ids[i:i+batch_size]
            placeholders = ','.join(['%s'] * len(batch))
            
            cursor.execute(f"""
                DELETE FROM products
                WHERE id IN ({placeholders})
            """, batch)
            
            conn.commit()
            print(f"✅ Deleted {min(batch_size, len(wrong_ids) - i)} products")
        
        # Step 6: Verify
        cursor.execute("""
            SELECT COUNT(*) as count FROM products 
            WHERE category_id = %s AND is_active = true
        """, (giay_category_id,))
        final_count = cursor.fetchone()['count']
        
        print(f"\n✅ Cleanup complete!")
        print(f"   Before: {initial_count} products")
        print(f"   After:  {final_count} products")
        print(f"   Deleted: {initial_count - final_count} products")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("="*80)
    print("CLEANUP SCRIPT: Remove non-shoe products from 'Giày' category")
    print("="*80 + "\n")
    
    cleanup_giay_category()

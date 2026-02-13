#!/usr/bin/env python3
"""
Populate sku_attributes từ products.brand

Lấy brand từ products table và insert vào sku_attributes
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def populate_brand_attributes():
    """Populate brand attribute từ products.brand vào sku_attributes"""
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        return
    
    conn = psycopg2.connect(db_url)
    conn.set_client_encoding('UTF-8')
    cursor = conn.cursor()
    
    try:
        print("🔄 Populating brand attributes from products.brand...")
        
        # Insert brand từ products vào sku_attributes
        cursor.execute("""
            INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value)
            SELECT DISTINCT s.id, 'brand', p.brand
            FROM skus s
            JOIN products p ON p.id = s.product_id
            WHERE p.brand IS NOT NULL AND p.brand != ''
              AND NOT EXISTS (
                SELECT 1 FROM sku_attributes sa
                WHERE sa.sku_id = s.id AND sa.attribute_name = 'brand'
              )
        """)
        
        inserted = cursor.rowcount
        conn.commit()
        
        print(f"✅ Inserted {inserted} brand attributes")
        
        # Verify
        cursor.execute("""
            SELECT COUNT(*) as count FROM sku_attributes
            WHERE attribute_name = 'brand'
        """)
        total = cursor.fetchone()[0]
        print(f"✅ Total brand attributes now: {total}")
        
        # Show distribution
        cursor.execute("""
            SELECT attribute_value, COUNT(*) as count
            FROM sku_attributes
            WHERE attribute_name = 'brand'
            GROUP BY attribute_value
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\n📊 Top brands:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} SKUs")
        
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
    print("POPULATE: sku_attributes from products.brand")
    print("="*80 + "\n")
    
    populate_brand_attributes()

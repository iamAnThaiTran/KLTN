# demo_postgres_data.py
"""
Demo: Xem dữ liệu trong PostgreSQL category_suggestions table
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def show_database_structure():
    """Show table structure"""
    print("\n" + "="*70)
    print("📋 TABLE STRUCTURE: category_suggestions")
    print("="*70)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = 'category_suggestions'
        ORDER BY ordinal_position
    """)
    
    print(f"\n{'Column':<20} {'Type':<20} {'Nullable':<10}")
    print("-" * 70)
    for row in cursor.fetchall():
        col_name, data_type, max_len, nullable = row
        type_str = f"{data_type}({max_len})" if max_len else data_type
        print(f"{col_name:<20} {type_str:<20} {nullable:<10}")
    
    cursor.close()
    conn.close()


def insert_demo_data():
    """Insert demo data để show cấu trúc"""
    from app.core.category_cache import CategoryCache
    
    print("\n" + "="*70)
    print("💾 INSERTING DEMO DATA")
    print("="*70)
    
    cache = CategoryCache(backend="postgres", pg_url=DATABASE_URL)
    
    demo_suggestions = [
        {
            "name": "đồng hồ",
            "attributes": ["brand", "style", "price range", "gender"],
            "reason": "Classic gift symbolizing time and new beginnings",
            "confidence": 0.85
        },
        {
            "name": "tai nghe",
            "attributes": ["brand", "type", "wireless", "price range", "noise cancelling"],
            "reason": "Popular tech product for music lovers",
            "confidence": 0.92
        },
        {
            "name": "nước hoa",
            "attributes": ["brand", "scent type", "volume", "gender", "occasion"],
            "reason": "Elegant and personal gift choice",
            "confidence": 0.88
        },
        {
            "name": "laptop",
            "attributes": ["brand", "cpu", "ram", "storage", "screen size", "price range"],
            "reason": "Essential for work and study",
            "confidence": 0.90
        }
    ]
    
    for suggestion in demo_suggestions:
        cache.save_suggestion(suggestion)
    
    print(f"\n✅ Inserted {len(demo_suggestions)} demo categories")


def show_all_data():
    """Show all data in table"""
    print("\n" + "="*70)
    print("📊 ALL DATA IN category_suggestions")
    print("="*70)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT * FROM category_suggestions
        ORDER BY usage_count DESC, created_at DESC
    """)
    
    rows = cursor.fetchall()
    
    print(f"\nTotal records: {len(rows)}\n")
    
    for idx, row in enumerate(rows, 1):
        print(f"{'─'*70}")
        print(f"Record #{idx}: {row['category_name'].upper()}")
        print(f"{'─'*70}")
        print(f"  ID:              {row['id']}")
        print(f"  Category:        {row['category_name']}")
        print(f"  Attributes:      {json.dumps(row['attributes'], ensure_ascii=False)}")
        print(f"  Keywords:        {json.dumps(row['keywords'], ensure_ascii=False) if row['keywords'] else '[]'}")
        print(f"  Reason:          {row['reason'][:60]}..." if len(row['reason']) > 60 else f"  Reason:          {row['reason']}")
        print(f"  Confidence:      {float(row['confidence']):.2f}")
        print(f"  Usage Count:     {row['usage_count']} times")
        print(f"  Created:         {row['created_at']}")
        print(f"  Updated:         {row['updated_at']}")
    
    cursor.close()
    conn.close()


def show_raw_sql_data():
    """Show raw SQL format"""
    print("\n" + "="*70)
    print("💻 RAW SQL DATA (như trong database)")
    print("="*70)
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id,
            category_name,
            attributes::text,
            keywords::text,
            reason,
            confidence,
            usage_count,
            created_at,
            updated_at
        FROM category_suggestions
        LIMIT 3
    """)
    
    rows = cursor.fetchall()
    
    print("\nSample raw data (first 3 records):\n")
    
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"category_name: '{row[1]}'")
        print(f"attributes (JSONB): {row[2]}")
        print(f"keywords (JSONB): {row[3]}")
        print(f"reason: '{row[4]}'")
        print(f"confidence: {row[5]}")
        print(f"usage_count: {row[6]}")
        print(f"created_at: {row[7]}")
        print(f"updated_at: {row[8]}")
        print()
    
    cursor.close()
    conn.close()


def show_json_example():
    """Show ví dụ JSON structure"""
    print("\n" + "="*70)
    print("📝 JSON STRUCTURE EXAMPLE")
    print("="*70)
    
    example = {
        "id": 1,
        "category_name": "đồng hồ",
        "attributes": ["brand", "style", "price range", "gender"],
        "keywords": ["đồng hồ", "dongho", "đồnghồ"],
        "reason": "Classic gift symbolizing time and new beginnings",
        "confidence": 0.85,
        "usage_count": 5,
        "created_at": "2026-01-29T00:40:00",
        "updated_at": "2026-01-29T01:30:00"
    }
    
    print("\nDữ liệu trong Python/JSON format:")
    print(json.dumps(example, indent=2, ensure_ascii=False))
    
    print("\n" + "="*70)
    print("💡 Note:")
    print("="*70)
    print("• attributes: JSONB array - danh sách các thuộc tính")
    print("• keywords: JSONB array - từ khóa để detect category")
    print("• usage_count: Tăng mỗi khi category được dùng")
    print("• confidence: Độ tin cậy từ LLM (0.0 - 1.0)")


def show_sql_queries():
    """Show useful SQL queries"""
    print("\n" + "="*70)
    print("🔍 USEFUL SQL QUERIES")
    print("="*70)
    
    queries = {
        "1. Xem tất cả categories": """
SELECT 
    category_name, 
    usage_count, 
    confidence,
    array_length(attributes, 1) as num_attributes
FROM category_suggestions
ORDER BY usage_count DESC;
        """,
        
        "2. Top 5 categories phổ biến nhất": """
SELECT 
    category_name, 
    usage_count,
    attributes
FROM category_suggestions
ORDER BY usage_count DESC
LIMIT 5;
        """,
        
        "3. Categories mới trong 24h": """
SELECT 
    category_name,
    attributes,
    created_at
FROM category_suggestions
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
        """,
        
        "4. Search category by keyword": """
SELECT 
    category_name,
    attributes,
    usage_count
FROM category_suggestions
WHERE 
    category_name ILIKE '%đồng%'
    OR keywords::text ILIKE '%đồng%';
        """,
        
        "5. Categories with high confidence": """
SELECT 
    category_name,
    confidence,
    usage_count
FROM category_suggestions
WHERE confidence >= 0.85
ORDER BY confidence DESC;
        """
    }
    
    for title, query in queries.items():
        print(f"\n{title}:")
        print(query.strip())


if __name__ == "__main__":
    # Show everything
    show_database_structure()
    insert_demo_data()
    show_all_data()
    show_raw_sql_data()
    show_json_example()
    show_sql_queries()
    
    print("\n" + "="*70)
    print("✅ Demo completed!")
    print("="*70)
    print("\n💡 Để connect trực tiếp:")
    print(f"   docker exec -it product_postgres psql -U admin -d product_db")
    print("\n   Hoặc dùng tool như DBeaver, pgAdmin với:")
    print(f"   Host: localhost")
    print(f"   Port: 15432")
    print(f"   Database: product_db")
    print(f"   User: admin")
    print(f"   Password: your_password")

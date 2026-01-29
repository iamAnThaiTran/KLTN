#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix Vietnamese character encoding in sku_attributes"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.set_client_encoding('UTF-8')
cursor = conn.cursor()

# Manual fixes for known broken values
fixes = [
    ('??en', 'Đen'),        # Đen is correct
    ('Tr???ng', 'Trắng'),   # Trắng is correct
    ('Th??? thao', 'Thể thao'),  # Thể thao is correct
    ('kem', 'Kem'),         # Capitalize
    ('trắng', 'Trắng'),     # Capitalize for consistency
    ('XANH', 'Xanh'),       # Consistency
]

print("🔄 Fixing encoding issues in sku_attributes...")
print("=" * 60)

for broken, correct in fixes:
    cursor.execute(
        "SELECT COUNT(*) FROM sku_attributes WHERE attribute_value = %s",
        (broken,)
    )
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute(
            "UPDATE sku_attributes SET attribute_value = %s WHERE attribute_value = %s",
            (correct, broken)
        )
        print(f"✅ Updated {count} records: '{broken}' → '{correct}'")
    else:
        print(f"⏭️  No records found for '{broken}'")

conn.commit()

# Verify changes
print("\n📋 Updated color values in database:")
cursor.execute('''
    SELECT DISTINCT attribute_value 
    FROM sku_attributes 
    WHERE attribute_name = 'color'
    ORDER BY attribute_value
''')

for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

conn.close()
print("\n✅ SKU attributes encoding fixed!")

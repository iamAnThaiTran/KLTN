#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix Vietnamese character encoding in category_attributes"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.set_client_encoding('UTF-8')
cursor = conn.cursor()

# Fix display names with correct Vietnamese
fixes = [
    # Giày
    (1, 'Kích cỡ'),
    (2, 'Màu sắc'),
    (3, 'Giới tính'),
    (4, 'Loại giày'),
    # Đồng hồ
    (5, 'Phong cách'),
    (6, 'Giới tính'),
    (7, 'Chất liệu'),
    (8, 'Chống nước'),
]

print("🔄 Updating category_attributes with correct Vietnamese names...")
for attr_id, display_name in fixes:
    cursor.execute(
        "UPDATE category_attributes SET display_name = %s WHERE id = %s",
        (display_name, attr_id)
    )
    print(f"✅ Updated attribute {attr_id}: {display_name}")

conn.commit()

# Verify
print("\n📊 Category attributes after update:")
cursor.execute('''
    SELECT ca.id, c.name, ca.name, ca.display_name 
    FROM category_attributes ca 
    JOIN categories c ON ca.category_id = c.id 
    ORDER BY c.name, ca.name
''')
rows = cursor.fetchall()
for row in rows:
    print(f"  {row}")

conn.close()
print("\n✅ Category attributes fixed successfully!")

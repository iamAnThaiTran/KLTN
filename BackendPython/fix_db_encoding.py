#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix Vietnamese character encoding in database"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url)
conn.set_client_encoding('UTF-8')
cursor = conn.cursor()

# Update categories with correct Vietnamese names
updates = [
    (1, 'Giày', 'giay'),
    (2, 'Đồng hồ', 'dong-ho'),
]

print("🔄 Updating categories with correct Vietnamese names...")
for cat_id, name, slug in updates:
    cursor.execute(
        "UPDATE categories SET name = %s WHERE id = %s",
        (name, cat_id)
    )
    print(f"✅ Updated category {cat_id}: {name}")

conn.commit()

# Verify
print("\n📊 Categories after update:")
cursor.execute('SELECT id, name, slug FROM categories ORDER BY id')
rows = cursor.fetchall()
for row in rows:
    print(f"  {row}")

conn.close()
print("\n✅ Database fixed successfully!")

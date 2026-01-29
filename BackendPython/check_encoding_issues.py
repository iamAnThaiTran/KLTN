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

# Get all distinct attribute values for color that have encoding issues
cursor.execute('''
    SELECT DISTINCT attribute_value 
    FROM sku_attributes 
    WHERE attribute_name = 'color'
    ORDER BY attribute_value
''')

color_values = cursor.fetchall()

print("📊 Current color values in database:")
for val in color_values:
    print(f"  '{val[0]}'")

# Map broken values to correct values
fixes = {
    'Đen': '??en',  # If it exists as broken
    'Trắng': 'Tr???ng',  # If it exists as broken
}

print("\n🔄 Checking for broken encoding...")

cursor.execute('''
    SELECT DISTINCT attribute_value 
    FROM sku_attributes 
    WHERE attribute_name = 'color' AND (attribute_value LIKE '%?%' OR attribute_value ~ '[^\x00-\x7F]' = false)
''')

broken_values = cursor.fetchall()

if broken_values:
    print(f"\n⚠️  Found {len(broken_values)} broken values:")
    for val in broken_values:
        print(f"  Broken: '{val[0]}'")
else:
    print("\n✅ No obvious broken values found - encoding might be OK")

# Try to detect and list all unique values with detailed info
print("\n📋 All unique color values with byte analysis:")
cursor.execute('''
    SELECT DISTINCT attribute_value 
    FROM sku_attributes 
    WHERE attribute_name = 'color'
    ORDER BY attribute_value
''')

for row in cursor.fetchall():
    val = row[0]
    print(f"  '{val}' (length: {len(val)}, bytes: {val.encode('utf-8')})")

conn.close()
print("\n✅ Analysis complete!")

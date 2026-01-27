#!/usr/bin/env python3
"""Debug: Check available categories"""

from app.core.schema import get_all_categories

categories = get_all_categories()
print(f"Available categories ({len(categories)}):")
for i, cat in enumerate(categories, 1):
    print(f"  {i}. {cat}")

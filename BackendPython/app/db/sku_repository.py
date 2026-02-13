# app/db/sku_repository.py
"""
Repository for SKU-based product queries
Handles complex filtering across products, SKUs, and attributes
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
import os
from dotenv import load_dotenv

load_dotenv()


class SKURepository:
    """Database operations for SKU-based product system"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
    
    def _get_connection(self):
        """Get database connection with UTF-8 encoding"""
        conn = psycopg2.connect(self.db_url)
        # Ensure UTF-8 handling for Vietnamese characters
        conn.set_client_encoding('UTF-8')
        return conn
    
    def get_category_schema(self, category_slug: str) -> Dict[str, Any]:
        """
        Get the attribute schema for a category from database
        
        Returns:
            {
                "category_id": 1,
                "category_name": "Giày",
                "attributes": [
                    {
                        "name": "size",
                        "display_name": "Kích cỡ",
                        "data_type": "enum",
                        "possible_values": ["35", "36", ..., "45"],
                        "is_filterable": true
                    },
                    ...
                ]
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get category info
        cursor.execute("""
            SELECT id, name, slug FROM categories WHERE slug = %s
        """, (category_slug,))
        
        category = cursor.fetchone()
        if not category:
            cursor.close()
            conn.close()
            return {}
        
        # Get attributes for this category
        cursor.execute("""
            SELECT 
                id,
                name,
                display_name,
                data_type,
                possible_values,
                is_filterable,
                sort_order
            FROM category_attributes
            WHERE category_id = %s AND is_filterable = true
            ORDER BY sort_order, name
        """, (category['id'],))
        
        attributes = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "category_id": category['id'],
            "category_name": category['name'],
            "category_slug": category['slug'],
            "attributes": [dict(attr) for attr in attributes]
        }
    
    def get_category_slug_from_name(self, category_name: str) -> Optional[str]:
        """
        Get category slug by name (case-insensitive)
        
        Args:
            category_name: e.g., "Giày", "Đồng hồ"
        
        Returns:
            slug: e.g., "giay", "dong-ho"
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT slug FROM categories 
            WHERE LOWER(name) = LOWER(%s)
        """, (category_name,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    
    # ========================================================================
    # PRODUCT SEARCH WITH FILTERS
    # ========================================================================
    
    def search_products(
        self,
        category_slug: str,
        filters: Dict[str, List[str]],
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search products with flexible attribute filters
        
        Args:
            category_slug: Category slug (e.g., "giay")
            filters: {"size": ["42", "43"], "color": ["Đen", "Trắng"]}
            min_price: Minimum price filter
            max_price: Maximum price filter
            page: Page number (1-indexed)
            page_size: Items per page
        
        Returns:
            (products_list, total_count)
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build WHERE clause for filters
        filter_conditions = []
        params = {'category_slug': category_slug}
        
        # Add attribute filters using EXISTS subqueries
        for attr_idx, (attr_name, values) in enumerate(filters.items()):
            if not values:
                continue
            
            param_key = f'filter_{attr_idx}'
            # ✅ NORMALIZE: Convert values to lowercase for case-insensitive search
            normalized_values = [str(v).lower() for v in values]
            
            # ✅ NEW: Fallback logic for brand attribute
            # If attribute is 'brand', also check products.brand (for data coverage)
            if attr_name.lower() == 'brand':
                brand_param = f'brand_{attr_idx}'
                params[brand_param] = normalized_values
                filter_conditions.append(f"""
                    (
                        -- Try sku_attributes first
                        EXISTS (
                            SELECT 1 FROM sku_attributes sa{attr_idx}
                            WHERE sa{attr_idx}.sku_id = s.id
                              AND sa{attr_idx}.attribute_name = 'brand'
                              AND LOWER(sa{attr_idx}.attribute_value) = ANY(%({param_key})s)
                        )
                        OR
                        -- Fallback to products.brand if sku_attributes is empty
                        (
                            SELECT COUNT(*) FROM sku_attributes WHERE attribute_name = 'brand'
                        ) = 0
                        AND LOWER(p.brand) = ANY(%({brand_param})s)
                    )
                """)
                params[param_key] = normalized_values
            else:
                # Normal attribute search
                filter_conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM sku_attributes sa{attr_idx}
                        WHERE sa{attr_idx}.sku_id = s.id
                          AND sa{attr_idx}.attribute_name = '{attr_name}'
                          AND LOWER(sa{attr_idx}.attribute_value) = ANY(%({param_key})s)
                    )
                """)
                params[param_key] = normalized_values
        
        # Add price filters
        if min_price is not None:
            filter_conditions.append("s.price >= %(min_price)s")
            params['min_price'] = min_price
        
        if max_price is not None:
            filter_conditions.append("s.price <= %(max_price)s")
            params['max_price'] = max_price
        
        where_clause = " AND ".join(filter_conditions) if filter_conditions else "TRUE"
        
        # Log for debugging
        print(f"[SKURepository.search_products] DEBUG:")
        print(f"  category_slug: '{category_slug}'")
        print(f"  filters: {filters}")
        print(f"  where_clause: {where_clause}")
        
        # DEBUG: Check data in DB for this category
        if filters:  # Only debug when filters exist
            debug_cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check 1: Total products in category
            debug_cursor.execute("""
                SELECT COUNT(DISTINCT p.id) as count
                FROM products p
                JOIN categories c ON c.id = p.category_id
                WHERE c.slug = %s AND p.is_active = true
            """, (category_slug,))
            total_in_cat = debug_cursor.fetchone()['count']
            print(f"  [DEBUG] Total products in '{category_slug}': {total_in_cat}")
            
            # Check 2: SKUs with attributes
            debug_cursor.execute("""
                SELECT COUNT(DISTINCT sku_id) as count
                FROM sku_attributes
                WHERE attribute_name = %s
            """, (list(filters.keys())[0],))
            skus_with_attr = debug_cursor.fetchone()['count']
            print(f"  [DEBUG] SKUs with attribute '{list(filters.keys())[0]}': {skus_with_attr}")
            
            # Check 3: Actual values for this attribute
            debug_cursor.execute("""
                SELECT DISTINCT attribute_value
                FROM sku_attributes
                WHERE attribute_name = %s
                LIMIT 10
            """, (list(filters.keys())[0],))
            values = debug_cursor.fetchall()
            print(f"  [DEBUG] Sample values for '{list(filters.keys())[0]}': {[v['attribute_value'] for v in values]}")
            
            # Check 4: Check if filter value exists
            for filter_name, filter_values in filters.items():
                debug_cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM sku_attributes
                    WHERE attribute_name = %s AND attribute_value = ANY(%s)
                """, (filter_name, filter_values))
                match_count = debug_cursor.fetchone()['count']
                print(f"  [DEBUG] Matches for {filter_name}={filter_values}: {match_count}")
            
            debug_cursor.close()
        
        # Count total
        count_query = f"""
            SELECT COUNT(DISTINCT p.id)
            FROM products p
            JOIN categories c ON c.id = p.category_id
            JOIN skus s ON s.product_id = p.id
            WHERE c.slug = %(category_slug)s
              AND p.is_active = true
              AND s.is_available = true
              AND {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['count']
        
        # Get products with SKUs
        offset = (page - 1) * page_size
        params.update({'limit': page_size, 'offset': offset})
        
        products_query = f"""
            WITH filtered_products AS (
                SELECT DISTINCT p.id
                FROM products p
                JOIN categories c ON c.id = p.category_id
                JOIN skus s ON s.product_id = p.id
                WHERE c.slug = %(category_slug)s
                  AND p.is_active = true
                  AND s.is_available = true
                  AND {where_clause}
                LIMIT %(limit)s OFFSET %(offset)s
            )
            SELECT 
                p.id,
                p.category_id,
                p.title,
                p.brand,
                p.description,
                p.product_url,
                p.thumbnail,
                p.source,
                s.id as sku_id,
                s.sku_code,
                s.price,
                s.original_price,
                s.stock,
                s.is_available,
                (
                    SELECT json_object_agg(sa.attribute_name, sa.attribute_value)
                    FROM sku_attributes sa
                    WHERE sa.sku_id = s.id
                ) as sku_attributes
            FROM filtered_products fp
            JOIN products p ON p.id = fp.id
            JOIN skus s ON s.product_id = p.id
            ORDER BY p.id, s.price
        """
        
        cursor.execute(products_query, params)
        rows = cursor.fetchall()
        
        # Group SKUs by product
        products_dict = {}
        for row in rows:
            product_id = row['id']
            
            if product_id not in products_dict:
                products_dict[product_id] = {
                    'id': row['id'],
                    'category_id': row['category_id'],
                    'title': row['title'],
                    'brand': row['brand'],
                    'description': row['description'],
                    'product_url': row['product_url'],
                    'thumbnail': row['thumbnail'],
                    'source': row['source'],
                    'skus': [],
                    'min_price': None,
                    'max_price': None
                }
            
            sku = {
                'id': row['sku_id'],
                'product_id': product_id,
                'sku_code': row['sku_code'],
                'price': float(row['price']),
                'original_price': float(row['original_price']) if row['original_price'] else None,
                'stock': row['stock'],
                'is_available': row['is_available'],
                'attributes': row['sku_attributes'] or {}
            }
            
            products_dict[product_id]['skus'].append(sku)
            
            # Update min/max price
            price = float(row['price'])
            if products_dict[product_id]['min_price'] is None:
                products_dict[product_id]['min_price'] = price
                products_dict[product_id]['max_price'] = price
            else:
                products_dict[product_id]['min_price'] = min(products_dict[product_id]['min_price'], price)
                products_dict[product_id]['max_price'] = max(products_dict[product_id]['max_price'], price)
        
        # Add available_count
        for product in products_dict.values():
            product['available_count'] = sum(1 for sku in product['skus'] if sku['is_available'])
        
        cursor.close()
        conn.close()
        
        return list(products_dict.values()), total
    
    # ========================================================================
    # GET AVAILABLE FILTERS
    # ========================================================================
    
    def get_available_filters(self, category_slug: str) -> List[Dict[str, Any]]:
        """
        Get available filter options for a category
        Query from DB FIRST to ensure we use latest schema from category_attributes table
        
        Returns:
            [
                {
                    "attribute_name": "size",
                    "display_name": "Kích cỡ",
                    "data_type": "enum",
                    "options": [
                        {"attribute_value": "42", "product_count": 10},
                        {"attribute_value": "43", "product_count": 8}
                    ]
                }
            ]
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # STEP 1: Get category attributes from DB schema (category_attributes table)
        # This ensures we show all defined attributes with correct display_name
        category_attrs_query = """
            SELECT 
                ca.name as attribute_name,
                ca.display_name,
                ca.data_type,
                ca.possible_values,
                ca.sort_order
            FROM category_attributes ca
            JOIN categories c ON c.id = ca.category_id
            WHERE c.slug = %s
              AND ca.is_filterable = true
            ORDER BY ca.sort_order, ca.name
        """
        
        cursor.execute(category_attrs_query, (category_slug,))
        defined_attrs = cursor.fetchall()
        
        # STEP 2: For each defined attribute, get available values from actual SKU data
        filters_list = []
        for attr in defined_attrs:
            attr_name = attr['attribute_name']
            
            # Get actual values from SKU data in DB
            values_query = """
                SELECT 
                    sa.attribute_value,
                    COUNT(DISTINCT s.product_id) as product_count
                FROM sku_attributes sa
                JOIN skus s ON s.id = sa.sku_id
                JOIN products p ON p.id = s.product_id
                JOIN categories c ON c.id = p.category_id
                WHERE c.slug = %s
                  AND sa.attribute_name = %s
                  AND s.is_available = true
                  AND p.is_active = true
                GROUP BY sa.attribute_value
                ORDER BY product_count DESC, sa.attribute_value
            """
            
            cursor.execute(values_query, (category_slug, attr_name))
            values = cursor.fetchall()
            
            filters_list.append({
                'attribute_name': attr['attribute_name'],
                'display_name': attr['display_name'] or attr['attribute_name'],
                'data_type': attr['data_type'],
                'possible_values': attr.get('possible_values'),
                'options': [dict(v) for v in values] if values else []
            })
        
        cursor.close()
        conn.close()
        
        return filters_list
    
    # ========================================================================
    # GET SINGLE PRODUCT
    # ========================================================================
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product with all SKUs by ID"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                p.id,
                p.category_id,
                p.title,
                p.brand,
                p.description,
                p.product_url,
                p.thumbnail,
                p.source,
                s.id as sku_id,
                s.sku_code,
                s.price,
                s.original_price,
                s.stock,
                s.is_available,
                (
                    SELECT json_object_agg(sa.attribute_name, sa.attribute_value)
                    FROM sku_attributes sa
                    WHERE sa.sku_id = s.id
                ) as sku_attributes
            FROM products p
            JOIN skus s ON s.product_id = p.id
            WHERE p.id = %s
            ORDER BY s.price
        """
        
        cursor.execute(query, (product_id,))
        rows = cursor.fetchall()
        
        if not rows:
            cursor.close()
            conn.close()
            return None
        
        # Build product with SKUs
        first_row = rows[0]
        product = {
            'id': first_row['id'],
            'category_id': first_row['category_id'],
            'title': first_row['title'],
            'brand': first_row['brand'],
            'description': first_row['description'],
            'product_url': first_row['product_url'],
            'thumbnail': first_row['thumbnail'],
            'source': first_row['source'],
            'skus': []
        }
        
        for row in rows:
            product['skus'].append({
                'id': row['sku_id'],
                'product_id': product['id'],
                'sku_code': row['sku_code'],
                'price': float(row['price']),
                'original_price': float(row['original_price']) if row['original_price'] else None,
                'stock': row['stock'],
                'is_available': row['is_available'],
                'attributes': row['sku_attributes'] or {}
            })
        
        cursor.close()
        conn.close()
        
        return product

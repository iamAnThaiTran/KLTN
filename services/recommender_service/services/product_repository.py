# -*- coding: utf-8 -*-
# app/services/product_repository.py
"""
Product Repository Service - WRITE operations only

Save & manage products in database (new SKU-based schema):
1. Save single product
2. Save SKU variants
3. Batch save crawled products

For QUERIES → Use SKURepository instead!

Uses EXISTING TABLES (Dynamic DB Schema):
- products (id, category_id, product_id, name, brand, description, images[], ...)
- skus (sku_id, product_id, price, discount_percent, stock, ...)
- sku_attributes (sku_id, attribute_name, attribute_value)

REQUIRES:
    pip install python-dotenv psycopg2-binary
"""

import logging
import sys
from typing import Dict, Any, List, Optional
import json
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    raise ImportError("Please install: pip install psycopg2-binary")

try:
    from dotenv import load_dotenv
except ImportError:
    raise ImportError("Please install: pip install python-dotenv")

import os
from db.sku_repository import SKURepository  # ✅ LOCAL: Use local module (independent)

load_dotenv()
logger = logging.getLogger(__name__)


class ProductRepository:
    """Repository pattern for WRITE operations only
    
    Use SKURepository for queries!
    """
    
    def __init__(self):
        # Construct DATABASE_URL from environment variables if not already set
        self.db_url = os.getenv(
            "DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kltn')}"
        )
        self.sku_repo = SKURepository(self.db_url)
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    # ====================================================================================
    # QUERY ADAPTER (Wrapper around SKURepository)
    # ====================================================================================
    
    def query_by_category_and_attributes(
        self,
        category_id: int,
        attributes: Dict[str, Any],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query products by category + attributes
        
        ADAPTER: Wraps SKURepository.search_products()
        Converts category_id + attributes dict → category_slug + filters dict
        
        Args:
            category_id: Category ID
            attributes: {
                "brand": "Nike",
                "color": "đen",
                "size": "42",
                "price_min": 1000000,
                "price_max": 5000000,
                ...
            }
            limit: Max number of results (translates to page_size)
        
        Returns:
            List of matching products with SKUs
        """
        try:
            # Get category slug from ID
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT name FROM categories WHERE id = %s LIMIT 1", [category_id])
            cat_result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not cat_result:
                logger.warning(f"Category ID {category_id} not found")
                return []
            
            category_slug = cat_result['slug']
            
            # Extract price range & filter attributes
            min_price = attributes.get("price_min")
            max_price = attributes.get("price_max")
            
            # Handle price filter in dict format: 'gia': [{'min': X, 'max': Y}]
            for price_key in ["gia", "price", "price_range"]:
                if price_key in attributes:
                    price_value = attributes.get(price_key)
                    if isinstance(price_value, list) and price_value:
                        # Extract dict from list: [{'min': X, 'max': Y}]
                        if isinstance(price_value[0], dict):
                            min_price = price_value[0].get("min", min_price)
                            max_price = price_value[0].get("max", max_price)
                    elif isinstance(price_value, dict):
                        # Direct dict format: {'min': X, 'max': Y}
                        min_price = price_value.get("min", min_price)
                        max_price = price_value.get("max", max_price)
            
            # Convert attributes dict to filters dict (skip price filters)
            filters = {}
            for key, value in attributes.items():
                if key not in ["price_min", "price_max", "gia", "price", "price_range"] and value:
                    # Convert single value to list for SKURepository format
                    filters[key] = [value] if not isinstance(value, list) else value
            
            logger.info(f"🔍 Query products: category='{category_slug}', filters={filters}, price={min_price}-{max_price}")
            
            # Call SKURepository with transformed params
            products, total = self.sku_repo.search_products(
                category_slug=category_slug,
                filters=filters,
                min_price=min_price,
                max_price=max_price,
                page=1,
                page_size=limit
            )
            
            logger.info(f"✅ Found {len(products)} products in DB")
            return products
        
        except Exception as e:
            logger.error(f"Error querying products: {e}")
            return []
    
    # ====================================================================================
    # WRITE OPERATIONS (Create/Update)
    # ====================================================================================
    
    def save_product(
        self,
        category_id: int,
        title: str,
        brand: str,
        description: str = "",
        product_url: str = "",
        thumbnail: str = "",
        source: str = "",
        attributes: Dict[str, Any] = None
    ) -> str:
        """
        Save a single product to database
        
        Returns:
            Product ID (unique string identifier)
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Generate product_id from URL or title
            import hashlib
            unique_data = f"{product_url}{title}".encode('utf-8')
            product_id = hashlib.md5(unique_data).hexdigest()[:20]
            
            # Check if product already exists (by product_id or name)
            cursor.execute("""
                SELECT id FROM products 
                WHERE product_id = %s LIMIT 1
            """, [product_id])
            
            existing = cursor.fetchone()
            if existing:
                return product_id
            
            # Save new product using new schema
            cursor.execute("""
                INSERT INTO products 
                (category_id, product_id, name, brand, description, images, source, is_available, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, true, NOW())
                RETURNING product_id
            """, [
                category_id,
                product_id,
                title,
                brand or "",
                description or "",
                [thumbnail] if thumbnail else [],  # images as array
                source or ""
            ])
            
            result = cursor.fetchone()
            if result:
                saved_product_id = result[0]
                conn.commit()
                logger.info(f"✅ Saved product '{title}' (product_id={saved_product_id})")
                return saved_product_id
            else:
                conn.rollback()
                logger.error(f"Failed to save product '{title}'")
                return None
        
        except Exception as e:
            logger.error(f"Error saving product: {e}")
            conn.rollback()
            return None
        
        finally:
            conn.close()
    
    def save_sku(
        self,
        product_id: str,
        sku_code: str,
        price: float,
        original_price: float = None,
        stock: int = 0,
        attributes: Dict[str, Any] = None
    ) -> str:
        """
        Save SKU (product variant) to database
        Attributes are saved separately in sku_attributes table
        
        Returns:
            SKU ID
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if SKU exists
            cursor.execute("SELECT sku_id FROM skus WHERE sku_id = %s LIMIT 1", [sku_code])
            existing = cursor.fetchone()
            
            sku_id = None
            if existing:
                # Update existing SKU
                sku_id = existing[0]
                cursor.execute("""
                    UPDATE skus 
                    SET price = %s, discount_percent = %s, stock = %s, updated_at = NOW()
                    WHERE sku_id = %s
                """, [price, (original_price - price) if original_price and original_price > price else 0, stock, sku_id])
            else:
                # Create new SKU - using sku_code as sku_id
                sku_id = sku_code
                cursor.execute("""
                    INSERT INTO skus (sku_id, product_id, price, discount_percent, stock, is_available, created_at)
                    VALUES (%s, %s, %s, %s, %s, true, NOW())
                """, [sku_id, product_id, price, (original_price - price) if original_price and original_price > price else 0, stock])
            
            # Save attributes separately in sku_attributes table
            if attributes and sku_id:
                self._save_sku_attributes(sku_id, attributes)
            
            conn.commit()
            logger.info(f"✅ Saved SKU (sku_id={sku_id})")
            return sku_id
        
        except Exception as e:
            logger.error(f"Error saving SKU: {e}")
            conn.rollback()
            return None
        
        finally:
            conn.close()
    
    def _save_sku_attributes(
        self,
        sku_id: str,
        attributes: Dict[str, Any]
    ) -> None:
        """
        Save SKU attributes to sku_attributes table
        
        Args:
            sku_id: SKU ID
            attributes: Dictionary of attribute name-value pairs
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Delete existing attributes first
            cursor.execute("DELETE FROM sku_attributes WHERE sku_id = %s", [sku_id])
            
            # Insert new attributes
            for attr_name, attr_value in attributes.items():
                # Convert value to string if it's a list or dict
                if isinstance(attr_value, (list, dict)):
                    attr_value = json.dumps(attr_value)
                else:
                    attr_value = str(attr_value)
                
                cursor.execute("""
                    INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value)
                    VALUES (%s, %s, %s)
                """, [sku_id, str(attr_name), attr_value])
            
            conn.commit()
            logger.debug(f"✅ Saved {len(attributes)} attributes for SKU {sku_id}")
        
        except Exception as e:
            logger.error(f"Error saving SKU attributes: {e}")
            conn.rollback()
        
        finally:
            conn.close()
    
    def save_products_batch(
        self,
        category_id: int,
        products_data: List[Dict[str, Any]]
    ) -> int:
        """
        Batch save multiple products (from crawl results)
        
        Args:
            category_id: Category ID
            products_data: List of product dictionaries from crawler
        
        Returns:
            Number of products saved
        """
        if not products_data:
            return 0
        
        conn = self.get_connection()
        saved_count = 0
        
        try:
            for product_data in products_data:
                product_id = self.save_product(
                    category_id=category_id,
                    title=product_data.get("name") or product_data.get("title") or "",
                    brand=product_data.get("brand") or "",
                    description=product_data.get("description") or "",
                    product_url=product_data.get("url") or product_data.get("link") or "",
                    thumbnail=product_data.get("thumbnail") or product_data.get("image") or "",
                    source=product_data.get("platform") or product_data.get("source") or "",
                    attributes=product_data.get("attributes") or {}
                )
                
                if product_id:
                    # Save SKUs if available
                    if product_data.get("skus"):
                        for sku_data in product_data["skus"]:
                            self.save_sku(
                                product_id=product_id,
                                sku_code=sku_data.get("sku_code") or f"{product_id}-{sku_data.get('price', 0)}",
                                price=float(sku_data.get("price", 0)),
                                original_price=float(sku_data.get("original_price", sku_data.get("price", 0))),
                                stock=int(sku_data.get("stock", 0)),
                                attributes=sku_data.get("attributes") or {}
                            )
                    elif product_data.get("price"):
                        # Save default SKU with product price
                        self.save_sku(
                            product_id=product_id,
                            sku_code=f"{product_id}-default",
                            price=float(product_data.get("price", 0)),
                            original_price=float(product_data.get("original_price", product_data.get("price", 0))),
                            attributes=product_data.get("attributes") or {}
                        )
                    
                    saved_count += 1
        
        except Exception as e:
            logger.error(f"Error batch saving products: {e}")
        
        finally:
            conn.close()
        
        logger.info(f"✅ Batch saved {saved_count} products to DB")
        return saved_count
    
    def update_product_metrics(
        self,
        product_id: int,
        view_count: int = None,
        sale_count: int = None,
        rating_avg: float = None,
        rating_count: int = None
    ) -> bool:
        """Update product metrics (views, sales, ratings)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if view_count is not None:
                updates.append("view_count = %s")
                params.append(view_count)
            
            if sale_count is not None:
                updates.append("sale_count = %s")
                params.append(sale_count)
            
            if rating_avg is not None:
                updates.append("rating_avg = %s")
                params.append(rating_avg)
            
            if rating_count is not None:
                updates.append("rating_count = %s")
                params.append(rating_count)
            
            if not updates:
                return True
            
            updates.append("updated_at = NOW()")
            
            sql = f"UPDATE products SET {', '.join(updates)} WHERE id = %s"
            params.append(product_id)
            
            cursor.execute(sql, params)
            conn.commit()
            
            return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            conn.rollback()
            return False
        
        finally:
            conn.close()

# app/services/crawler_adapter.py
"""
Adapter để convert crawler data sang SKU-based format và lưu vào database
"""

import os
import re
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class CrawlerToSKUAdapter:
    """Convert crawler data to SKU format and save to database"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def get_category_id(self, category_name: str) -> Optional[int]:
        """Get category ID by name or slug with fallback matching"""
        # FIRST: Try exact match or direct slug match
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM categories 
                WHERE name = %s OR slug = %s
                LIMIT 1
            """, (category_name, self._slugify(category_name)))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # FALLBACK: Try matching with UNIVERSAL_KEYWORDS
            # This allows "giày thể thao nam" to match to "Giày" category
            try:
                from ..core.dynamic_schema import UNIVERSAL_KEYWORDS  # ✅ LOCAL: Independent from monolith
                category_lower = category_name.lower().strip()
                
                # Find base category from UNIVERSAL_KEYWORDS
                base_category = None
                for base_cat in UNIVERSAL_KEYWORDS.keys():
                    if base_cat.lower() == category_lower:
                        base_category = base_cat
                        break
                
                # If not exact match, check keywords
                if not base_category:
                    for base_cat, keywords in UNIVERSAL_KEYWORDS.items():
                        if category_lower in [kw.lower() for kw in keywords]:
                            base_category = base_cat
                            break
                
                # If still not found, try substring match
                if not base_category:
                    for base_cat, keywords in UNIVERSAL_KEYWORDS.items():
                        for keyword in keywords:
                            keyword_lower = keyword.lower()
                            if keyword_lower in category_lower or category_lower in keyword_lower:
                                if len(keyword_lower) > 2:  # Avoid false positives
                                    base_category = base_cat
                                    break
                        if base_category:
                            break
                
                # Try to find the base category in database
                if base_category:
                    cursor.execute("""
                        SELECT id FROM categories 
                        WHERE name = %s OR slug = %s
                        LIMIT 1
                    """, (base_category, self._slugify(base_category)))
                    
                    result = cursor.fetchone()
                    if result:
                        return result[0]
            except ImportError:
                pass  # UNIVERSAL_KEYWORDS not available, skip fallback
            
            # If still nothing found, return None
            return None
            
        finally:
            conn.close()
    
    def _slugify(self, text: str) -> str:
        """Convert text to slug"""
        # Remove Vietnamese accents (simplified)
        text = text.lower()
        text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
        text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
        text = re.sub(r'[ìíịỉĩ]', 'i', text)
        text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
        text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
        text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
        text = re.sub(r'đ', 'd', text)
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')
    
    def extract_attributes_from_title(self, title: str, category_name: str) -> Dict[str, str]:
        """Extract attributes from product title based on category"""
        attributes = {}
        title_lower = title.lower()
        
        # Extract common attributes based on category
        if category_name in ['giày', 'giay']:
            # Extract size
            size_match = re.search(r'size\s*(\d+)', title_lower)
            if size_match:
                attributes['size'] = size_match.group(1)
            
            # Extract color
            colors = ['đen', 'trắng', 'xanh', 'đỏ', 'vàng', 'nâu', 'xám']
            for color in colors:
                if color in title_lower:
                    attributes['color'] = color.capitalize()
                    break
            
            # Extract gender
            if 'nam' in title_lower:
                attributes['gender'] = 'Nam'
            elif any(w in title_lower for w in ['nữ', 'nu']):
                attributes['gender'] = 'Nữ'
            
            # Extract type
            if any(w in title_lower for w in ['thể thao', 'the thao', 'sport']):
                attributes['type'] = 'Thể thao'
            elif 'sneaker' in title_lower:
                attributes['type'] = 'Sneaker'
            elif 'sandal' in title_lower:
                attributes['type'] = 'Sandal'
                
        elif category_name in ['đồng hồ', 'dong ho', 'dong-ho']:
            # Extract gender
            if 'nam' in title_lower:
                attributes['gender'] = 'Nam'
            elif any(w in title_lower for w in ['nữ', 'nu']):
                attributes['gender'] = 'Nữ'
            
            # Extract material
            if 'da' in title_lower:
                attributes['material'] = 'Da'
            elif any(w in title_lower for w in ['kim loại', 'kim loai', 'stainless']):
                attributes['material'] = 'Kim loại'
            elif 'silicon' in title_lower:
                attributes['material'] = 'Silicon'
            
            # Extract style
            if 'sport' in title_lower:
                attributes['style'] = 'Sport'
            elif 'smartwatch' in title_lower:
                attributes['style'] = 'Smartwatch'
            elif 'luxury' in title_lower:
                attributes['style'] = 'Luxury'
            else:
                attributes['style'] = 'Casual'
        
        return attributes
    
    def save_crawled_products(
        self, 
        products: List[Dict[str, Any]], 
        category_name: str
    ) -> Dict[str, Any]:
        """
        Save crawled products to SKU database
        
        Args:
            products: List of products from crawler
                [
                    {
                        "title": "Nike Air Max",
                        "price": 2500000,
                        "brand": "Nike",
                        "link": "https://tiki.vn/...",
                        "image": "https://...",
                        "source": "tiki",
                        "discount": 10,
                        "sold": 100
                    }
                ]
            category_name: Category name (e.g., "giày", "đồng hồ")
        
        Returns:
            {
                "success": True,
                "products_saved": 5,
                "skus_saved": 5
            }
        """
        conn = self.get_connection()
        products_saved = 0
        skus_saved = 0
        
        try:
            # Get category ID
            category_id = self.get_category_id(category_name)
            if not category_id:
                logger.error(f"Category not found: {category_name}")
                return {
                    "success": False,
                    "error": f"Category '{category_name}' not found in database"
                }
            
            cursor = conn.cursor()
            
            for product_data in products:
                try:
                    # 1. Check if product exists, if not insert
                    cursor.execute("""
                        SELECT id FROM products WHERE product_url = %s LIMIT 1
                    """, (product_data.get('link', ''),))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        product_id = existing[0]
                        # Update existing product
                        cursor.execute("""
                            UPDATE products SET
                                title = %s,
                                thumbnail = %s,
                                tiki_product_id = %s,
                                tiki_spid = %s,
                                seller_id = %s,
                                updated_at = NOW()
                            WHERE id = %s
                            RETURNING id
                        """, (
                            product_data.get('title', 'Unknown Product'),
                            product_data.get('image', ''),
                            product_data.get('product_id', ''),
                            product_data.get('spid', ''),
                            product_data.get('seller_id', '1'),
                            product_id
                        ))
                        result = cursor.fetchone()
                        if result:
                            product_id = result[0]
                    else:
                        # Insert new product
                        cursor.execute("""
                            INSERT INTO products (
                                category_id, title, brand, description, 
                                product_url, source, thumbnail, 
                                tiki_product_id, tiki_spid, seller_id, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            RETURNING id
                        """, (
                            category_id,
                            product_data.get('title', 'Unknown Product'),
                            product_data.get('brand', 'Unknown'),
                            product_data.get('description', ''),
                            product_data.get('link', ''),
                            product_data.get('source', 'tiki'),
                            product_data.get('image', ''),
                            product_data.get('product_id', ''),
                            product_data.get('spid', ''),
                            product_data.get('seller_id', '1')
                        ))
                        
                        result = cursor.fetchone()
                        if result:
                            product_id = result[0]
                            products_saved += 1
                        else:
                            logger.error(f"Failed to get product_id for: {product_data.get('title')}")
                            continue
                    
                    # 2. Extract attributes - ƯU TIÊN dùng extracted_attributes nếu có
                    if 'extracted_attributes' in product_data and product_data['extracted_attributes']:
                        # Dùng attributes đã extract từ Tiki API
                        extracted = product_data['extracted_attributes']
                        attributes = {}
                        
                        # Lấy size đầu tiên nếu có
                        if extracted.get('sizes'):
                            attributes['size'] = extracted['sizes'][0]
                        
                        # Lấy color đầu tiên nếu có
                        if extracted.get('colors'):
                            attributes['color'] = extracted['colors'][0]
                        
                        # Lấy material đầu tiên nếu có
                        if extracted.get('materials'):
                            attributes['material'] = extracted['materials'][0]
                        
                        # logger.info(f"    Using extracted attributes: {attributes}")
                    else:
                        # Fallback: Extract từ title
                        attributes = self.extract_attributes_from_title(
                            product_data.get('title', ''),
                            category_name
                        )
                    
                    # 3. Create SKU code
                    brand_prefix = product_data.get('brand', 'UNK')[:4].upper()
                    attr_suffix = '-'.join([v[:3].upper() for v in attributes.values()][:2])
                    sku_code = f"{brand_prefix}-{attr_suffix}-{product_id}"
                    
                    # 4. Insert SKU
                    price = product_data.get('price', 0)
                    original_price = price
                    if product_data.get('discount', 0) > 0:
                        original_price = int(price / (1 - product_data.get('discount', 0) / 100))
                    
                    cursor.execute("""
                        INSERT INTO skus (
                            product_id, sku_code, price, original_price, 
                            stock, is_available
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (sku_code)
                        DO UPDATE SET
                            price = EXCLUDED.price,
                            original_price = EXCLUDED.original_price,
                            updated_at = NOW()
                        RETURNING id
                    """, (
                        product_id,
                        sku_code,
                        price,
                        original_price,
                        product_data.get('sold', 0),  # Use sold as stock estimate
                        True
                    ))
                    
                    sku_result = cursor.fetchone()
                    if not sku_result:
                        logger.error(f"Failed to get SKU_id for: {product_data.get('title')}")
                        continue
                    
                    sku_id = sku_result[0]
                    skus_saved += 1
                    
                    # 5. Insert SKU attributes
                    if attributes:
                        # Delete old attributes
                        cursor.execute("DELETE FROM sku_attributes WHERE sku_id = %s", (sku_id,))
                        
                        # Insert new attributes
                        attr_values = [
                            (sku_id, attr_name, attr_value)
                            for attr_name, attr_value in attributes.items()
                        ]
                        
                        if attr_values:
                            execute_values(
                                cursor,
                                """
                                INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value)
                                VALUES %s
                                """,
                                attr_values
                            )
                    
                    # logger.info(f"✅ Saved: {product_data.get('title')} → SKU: {sku_code}")
                    
                except Exception as e:
                    logger.error(f"Error saving product: {e}")
                    continue
            
            conn.commit()
            
            return {
                "success": True,
                "products_saved": products_saved,
                "skus_saved": skus_saved,
                "category_id": category_id
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()


# Convenience function
def save_tiki_products(products: List[Dict], category: str):
    """Quick function to save Tiki crawler results"""
    adapter = CrawlerToSKUAdapter()
    return adapter.save_crawled_products(products, category)

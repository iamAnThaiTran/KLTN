# app/services/schema_reconciler.py
"""
Schema Reconciliation Service

Giải quyết vấn đề: LLM dự đoán attribute structure khác với thực tế Tiki
Flow:
1. Extract actual attributes từ crawled products
2. Build actual schema từ crawled data
3. Reconcile với LLM predicted schema
4. Save final schema + products vào DB
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logger = logging.getLogger(__name__)

class SchemaReconciler:
    """Reconcile LLM predicted schema vs actual Tiki schema"""
    
    def __init__(self):
        # Construct DATABASE_URL from environment variables if not already set
        self.db_url = os.getenv(
            "DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kltn')}"
        )
    
    def extract_actual_schema(self, crawled_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract actual attribute schema từ crawled products
        
        Returns:
            {
                "brand": {
                    "type": "enum",
                    "values": ["durex", "trojan", ...],
                    "count": 15  # số products có attribute này
                },
                "loai": {
                    "type": "enum",
                    "values": ["có gân", "siêu mỏng", "có hương", ...],
                    "count": 20
                },
                ...
            }
        """
        actual_schema = defaultdict(lambda: {"type": "unknown", "values": set(), "count": 0})
        
        for product in crawled_products:
            if not product.get("attributes"):
                continue
            
            attrs = product["attributes"]
            if not isinstance(attrs, dict):
                continue
            
            for attr_name, attr_value in attrs.items():
                if attr_value is None:
                    continue
                
                # Track attribute value
                actual_schema[attr_name]["values"].add(str(attr_value))
                actual_schema[attr_name]["count"] += 1
                
                # Infer type
                if isinstance(attr_value, (int, float)):
                    actual_schema[attr_name]["type"] = "number"
                elif isinstance(attr_value, bool):
                    actual_schema[attr_name]["type"] = "boolean"
                else:
                    actual_schema[attr_name]["type"] = "enum"
        
        # Convert sets to lists
        final_schema = {}
        for attr_name, attr_info in actual_schema.items():
            final_schema[attr_name] = {
                "type": attr_info["type"],
                "values": sorted(list(attr_info["values"])),
                "product_count": attr_info["count"]
            }
        
        logger.info(f"✅ Extracted actual schema from {len(crawled_products)} products:")
        for attr_name, info in final_schema.items():
            logger.info(f"   - {attr_name}: {info['type']} ({len(info['values'])} values, {info['product_count']} products)")
        
        return final_schema
    
    def reconcile_schemas(
        self, 
        llm_predicted_schema: Dict[str, Any],
        actual_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconcile LLM predicted schema với actual schema từ Tiki
        
        Returns:
            Final reconciled schema để lưu vào DB
        """
        reconciled = {}
        
        logger.info(f"\n{'='*80}")
        logger.info("🔄 RECONCILING SCHEMAS")
        logger.info(f"{'='*80}")
        logger.info(f"LLM predicted attributes: {list(llm_predicted_schema.keys())}")
        logger.info(f"Actual Tiki attributes: {list(actual_schema.keys())}")
        
        # Use actual schema as baseline (vì nó từ real data)
        for attr_name, attr_info in actual_schema.items():
            reconciled[attr_name] = {
                "type": attr_info["type"],
                "values": attr_info["values"][:20],  # Keep top 20 values
                "source": "tiki",  # Từ Tiki, không từ LLM
                "confidence": 1.0
            }
            logger.info(f"✅ {attr_name} (from Tiki): {attr_info['type']}, {len(attr_info['values'])} values")
        
        # Add missing LLM predicted attributes (nếu Tiki không có)
        for attr_name, attr_info in llm_predicted_schema.items():
            if attr_name not in reconciled:
                logger.info(f"⚠️  {attr_name} (from LLM): not found in Tiki data, using LLM prediction")
                reconciled[attr_name] = {
                    "type": attr_info.get("type", "text"),
                    "values": attr_info.get("values", []),
                    "source": "llm",  # Từ LLM vì Tiki không có
                    "confidence": 0.7
                }
        
        logger.info(f"\n✅ Final reconciled schema: {len(reconciled)} attributes")
        logger.info(f"{'='*80}\n")
        
        return reconciled
    
    def save_products_to_db(
        self,
        category_name: str,
        category_id: int,
        crawled_products: List[Dict[str, Any]],
        final_schema: Dict[str, Any]
    ) -> int:
        """
        Save crawled products + final schema vào DB
        
        Returns:
            số products được save
        """
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            saved_count = 0
            
            logger.info(f"\n💾 SAVING {len(crawled_products)} PRODUCTS TO DB")
            
            for i, product in enumerate(crawled_products, 1):
                try:
                    # Insert product
                    cursor.execute("""
                        INSERT INTO products 
                        (category_id, title, brand, description, product_url, thumbnail, source, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                        ON CONFLICT (product_url) DO UPDATE SET 
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            thumbnail = EXCLUDED.thumbnail
                        RETURNING id
                    """, (
                        category_id,
                        product.get("title", "")[:200],
                        product.get("brand", "")[:100],
                        product.get("description", "")[:1000],
                        product.get("product_url", ""),
                        product.get("thumbnail", ""),
                        product.get("source", "tiki")
                    ))
                    
                    product_id = cursor.fetchone()[0]
                    
                    # Insert SKU (one per product for now)
                    price = product.get("price", 0)
                    cursor.execute("""
                        INSERT INTO skus 
                        (product_id, sku_code, price, original_price, stock, is_available)
                        VALUES (%s, %s, %s, %s, %s, true)
                        ON CONFLICT (sku_code) DO UPDATE SET
                            price = EXCLUDED.price
                        RETURNING id
                    """, (
                        product_id,
                        f"{category_name}_{product_id}",
                        price,
                        product.get("original_price", price),
                        100  # Default stock
                    ))
                    
                    sku_id = cursor.fetchone()[0]
                    
                    # Insert SKU attributes
                    if product.get("attributes") and isinstance(product["attributes"], dict):
                        for attr_name, attr_value in product["attributes"].items():
                            if attr_value and attr_name in final_schema:
                                cursor.execute("""
                                    INSERT INTO sku_attributes 
                                    (sku_id, attribute_name, attribute_value)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (sku_id, attribute_name) DO UPDATE SET
                                        attribute_value = EXCLUDED.attribute_value
                                """, (sku_id, attr_name, str(attr_value)[:100]))
                    
                    saved_count += 1
                    if i % 10 == 0:
                        logger.info(f"  Saved {i}/{len(crawled_products)} products...")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️  Failed to save product {i}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✅ Saved {saved_count}/{len(crawled_products)} products to DB")
            return saved_count
            
        except Exception as e:
            logger.error(f"❌ Error saving products: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def save_schema_to_db(
        self,
        category_id: int,
        category_name: str,
        schema: Dict[str, Any]
    ) -> bool:
        """
        Save reconciled schema attributes vào DB
        
        Returns:
            True nếu thành công
        """
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            
            logger.info(f"💾 Saving {len(schema)} attributes to DB...")
            
            for attr_name, attr_info in schema.items():
                # Insert category_attribute
                cursor.execute("""
                    INSERT INTO category_attributes 
                    (category_id, attribute_name, display_name, data_type, is_filterable)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (category_id, attribute_name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        data_type = EXCLUDED.data_type
                    RETURNING id
                """, (
                    category_id,
                    attr_name,
                    attr_name.replace("_", " ").title(),  # Display name
                    attr_info.get("type", "text")
                ))
                
                cat_attr_id = cursor.fetchone()[0]
                
                # Insert attribute values
                for value in attr_info.get("values", [])[:50]:  # Keep top 50 values
                    cursor.execute("""
                        INSERT INTO category_attribute_values 
                        (category_attribute_id, value, display_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (category_attribute_id, value) DO NOTHING
                    """, (cat_attr_id, str(value)[:100], str(value)[:100]))
            
            conn.commit()
            logger.info(f"✅ Schema saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving schema: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

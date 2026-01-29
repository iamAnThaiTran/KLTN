# -*- coding: utf-8 -*-
# app/services/category_validator.py
"""
Category Validator Service

Xác nhận category trước khi crawl:
1. Check category có trong DB không
2. Nếu không → Call LLM để xác định đúng category
3. Lưu category mới vào DB (nếu cần)
4. Return validated category cho crawler
"""

import logging
import sys

# Ensure UTF-8 output for Vietnamese characters
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import os
import re

load_dotenv()
logger = logging.getLogger(__name__)


class CategoryValidator:
    """Validate và normalize categories trước khi crawl"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        # Import khi cần để tránh circular import
        self._universal_keywords = None
        self._llm_utils = None
    
    @property
    def universal_keywords(self):
        """Lazy load UNIVERSAL_KEYWORDS"""
        if self._universal_keywords is None:
            from app.core.dynamic_schema import UNIVERSAL_KEYWORDS
            self._universal_keywords = UNIVERSAL_KEYWORDS
        return self._universal_keywords
    
    @property
    def llm_utils(self):
        """Lazy load LLM utils"""
        if self._llm_utils is None:
            from app.core.llm_utils import call_openai
            self._llm_utils = call_openai
        return self._llm_utils
    
    def get_db_categories(self) -> Dict[int, Dict[str, str]]:
        """
        Get tất cả categories từ database
        
        Returns:
            {
                1: {"name": "Giày", "slug": "giay"},
                2: {"name": "Đồng hồ", "slug": "dong-ho"},
                ...
            }
        """
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, slug FROM categories ORDER BY id")
            rows = cursor.fetchall()
            
            categories = {}
            for cat_id, name, slug in rows:
                categories[cat_id] = {"name": name, "slug": slug}
            
            return categories
        finally:
            conn.close()
    
    def _slugify(self, text: str) -> str:
        """Convert text to slug"""
        text = text.lower().strip()
        text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
        text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
        text = re.sub(r'[ìíịỉĩ]', 'i', text)
        text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
        text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
        text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
        text = re.sub(r'đ', 'd', text)
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')
    
    def validate_category(self, user_category: str) -> Dict[str, Any]:
        """
        Validate category từ user input
        
        Flow:
        1. Try exact match with DB categories
        2. Try flexible match với UNIVERSAL_KEYWORDS
        3. Nếu không match → call LLM để xác định category mới
        4. Return validated category info
        
        Returns:
            {
                "success": bool,
                "category": str,  # Category name tìm thấy hoặc tạo mới
                "category_id": int | None,  # ID trong DB (None nếu mới)
                "status": "found" | "normalized" | "created_from_llm",
                "reason": str
            }
        """
        db_categories = self.get_db_categories()
        db_names = {cat["name"].lower(): (cat_id, cat["name"]) for cat_id, cat in db_categories.items()}
        db_slugs = {cat["slug"]: (cat_id, cat["name"]) for cat_id, cat in db_categories.items()}
        
        user_cat_lower = user_category.lower().strip()
        user_slug = self._slugify(user_category)
        
        # STEP 1: Try exact match
        if user_cat_lower in db_names:
            cat_id, cat_name = db_names[user_cat_lower]
            logger.info(f"✅ Category '{user_category}' → exact match '{cat_name}' (id={cat_id})")
            return {
                "success": True,
                "category": cat_name,
                "category_id": cat_id,
                "status": "found",
                "reason": "Exact match with database category"
            }
        
        if user_slug in db_slugs:
            cat_id, cat_name = db_slugs[user_slug]
            logger.info(f"✅ Category '{user_category}' → slug match '{cat_name}' (id={cat_id})")
            return {
                "success": True,
                "category": cat_name,
                "category_id": cat_id,
                "status": "found",
                "reason": "Slug match with database category"
            }
        
        # STEP 2: Try UNIVERSAL_KEYWORDS match
        for base_cat, keywords in self.universal_keywords.items():
            # Check exact keyword match
            if user_cat_lower in [kw.lower() for kw in keywords]:
                # Find this base_cat in DB
                for cat_id, cat in db_categories.items():
                    if cat["name"].lower() == base_cat.lower():
                        logger.info(f"✅ Category '{user_category}' → keyword match '{base_cat}' (id={cat_id})")
                        return {
                            "success": True,
                            "category": cat["name"],
                            "category_id": cat_id,
                            "status": "normalized",
                            "reason": f"Matched via keyword '{base_cat}'"
                        }
            
            # Check substring match
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in user_cat_lower or user_cat_lower in keyword_lower:
                    if len(keyword_lower) > 2:
                        for cat_id, cat in db_categories.items():
                            if cat["name"].lower() == base_cat.lower():
                                logger.info(f"✅ Category '{user_category}' → substring match '{base_cat}' (id={cat_id})")
                                return {
                                    "success": True,
                                    "category": cat["name"],
                                    "category_id": cat_id,
                                    "status": "normalized",
                                    "reason": f"Matched via substring '{keyword}'"
                                }
        
        # STEP 3: Category not found in DB or keywords
        # Try LLM to determine if it's a valid category or should map to existing one
        logger.warning(f"⚠️ Category '{user_category}' not found in DB, calling LLM...")
        
        llm_result = self._validate_with_llm(user_category, db_categories)
        
        if llm_result["success"]:
            if llm_result["status"] == "map_to_existing":
                # LLM says it should map to existing category
                cat_id = llm_result["category_id"]
                cat_name = db_categories[cat_id]["name"]
                logger.info(f"✅ LLM mapped '{user_category}' → existing '{cat_name}' (id={cat_id})")
                return {
                    "success": True,
                    "category": cat_name,
                    "category_id": cat_id,
                    "status": "normalized",
                    "reason": f"LLM mapped to existing category '{cat_name}'"
                }
            
            elif llm_result["status"] == "create_new":
                # LLM says it's a new category
                new_cat_id = self._create_category(
                    user_category,
                    llm_result.get("description", ""),
                    llm_result.get("attributes", [])
                )
                logger.info(f"✅ Created new category '{user_category}' (id={new_cat_id})")
                return {
                    "success": True,
                    "category": user_category,
                    "category_id": new_cat_id,
                    "status": "created_from_llm",
                    "reason": f"LLM confirmed as new category: {llm_result.get('description', '')}"
                }
        
        # LLM validation failed
        logger.error(f"❌ Failed to validate category '{user_category}'")
        return {
            "success": False,
            "category": None,
            "category_id": None,
            "status": "failed",
            "reason": "Could not validate category with LLM"
        }
    
    def _validate_with_llm(self, user_category: str, db_categories: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        Call LLM để xác nhận category
        
        Hỏi LLM:
        1. Category này là sản phẩm gì?
        2. Nó có thể thuộc category nào trong DB không?
        3. Nếu không thuộc → có nên tạo category mới không?
        """
        db_cat_names = ", ".join([cat["name"] for cat in db_categories.values()])
        
        prompt = f"""Bạn là chuyên gia về phân loại sản phẩm. Cho một danh mục sản phẩm từ user input, 
hãy xác nhận nó là gì và có nên gắn vào category nào trong database.

Các category hiện có trong database: {db_cat_names}

User muốn tìm sản phẩm: "{user_category}"

Hãy trả lời với JSON có structure sau:
{{
  "product_name": "tên sản phẩm xác nhận",
  "description": "mô tả ngắn về sản phẩm này",
  "action": "map_to_existing" | "create_new",
  "mapped_to": "tên category trong DB nếu map" | null,
  "reason": "lý do chọn action này",
  "attributes": ["thuộc tính 1", "thuộc tính 2", ...]
}}

Chỉ trả lời JSON, không có text khác."""
        
        try:
            # Use call_openai which returns response text directly
            response_text = self.llm_utils(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.3
            )
            
            if not response_text:
                logger.error("LLM returned empty response")
                return {"success": False}
            
            import json
            
            # Try to extract JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text
            
            data = json.loads(json_str)
            
            if data["action"] == "map_to_existing":
                mapped_cat = data.get("mapped_to", "").lower().strip()
                # Find this base_cat in DB
                for cat_id, cat in db_categories.items():
                    if cat["name"].lower() == mapped_cat:
                        return {
                            "success": True,
                            "status": "map_to_existing",
                            "category_id": cat_id,
                            "reason": data.get("reason", "")
                        }
                logger.warning(f"LLM mapped to '{mapped_cat}' but not found in DB")
                return {"success": False}
            
            elif data["action"] == "create_new":
                return {
                    "success": True,
                    "status": "create_new",
                    "description": data.get("description", ""),
                    "attributes": data.get("attributes", []),
                    "reason": data.get("reason", "")
                }
        
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return {"success": False}
    
    def _create_category(self, category_name: str, description: str = "", attributes: list = None) -> Optional[int]:
        """
        Create new category trong database
        
        Returns:
            Category ID nếu thành công, None nếu fail
        """
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            slug = self._slugify(category_name)
            
            cursor.execute("""
                INSERT INTO categories (name, slug, description, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """, (category_name, slug, description or ""))
            
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                category_id = result[0]
                logger.info(f"✅ Created category '{category_name}' (id={category_id})")
                return category_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()


def validate_category_before_crawl(user_category: str) -> Tuple[bool, str, Optional[int]]:
    """
    Convenience function: Validate category before crawling
    
    Returns:
        (success, normalized_category_name, category_id)
    """
    validator = CategoryValidator()
    result = validator.validate_category(user_category)
    
    if result["success"]:
        return True, result["category"], result["category_id"]
    else:
        return False, None, None

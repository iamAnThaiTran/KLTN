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
    
    def __init__(self, product_service_client=None, schema_evolution_service=None, rabbitmq_producer=None):
        # Construct DATABASE_URL from environment variables if not already set
        self.db_url = os.getenv(
            "DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kltn')}"
        )
        # Import khi cần để tránh circular import
        self._universal_keywords = None
        self._llm_utils = None
        self._schema_evolution_service = None
        self.product_service_client = product_service_client  # HTTP client to ProductService
        self._product_service_client_for_evolution = product_service_client
        self._rabbitmq_producer = rabbitmq_producer
    
    @property
    def schema_evolution_service(self):
        """Lazy load CategorySchemaEvolution"""
        if self._schema_evolution_service is None:
            from services.category_schema_evolution import CategorySchemaEvolution
            self._schema_evolution_service = CategorySchemaEvolution(
                product_service_client=self._product_service_client_for_evolution
            )
        return self._schema_evolution_service
    
    @property
    def universal_keywords(self):
        """Lazy load UNIVERSAL_KEYWORDS"""
        if self._universal_keywords is None:
            from core.dynamic_schema import UNIVERSAL_KEYWORDS  # ✅ LOCAL: Use local module (independent)
            self._universal_keywords = UNIVERSAL_KEYWORDS
        return self._universal_keywords
    
    @property
    def llm_utils(self):
        """Lazy load LLM utils"""
        if self._llm_utils is None:
            from core.llm_utils import call_openai  # ✅ LOCAL: Use local module (independent)
            self._llm_utils = call_openai
        return self._llm_utils
    
    async def get_db_categories(self) -> Dict[int, Dict[str, str]]:
        """
        Get tất cả categories từ ProductService API
        
        Returns:
            {
                1: {"name": "Giày", "slug": "giay"},
                2: {"name": "Đồng hồ", "slug": "dong-ho"},
                ...
            }
        """
        if self.product_service_client is None:
            logger.error("❌ ProductServiceClient not available")
            return {}
        
        try:
            #logger.info("📤 Calling ProductService API to get all categories...")
            response = await self.product_service_client.list_categories()
            # #logger.info(f"📥 Received response from ProductService: {response}")
            
            categories = {}
            if response and isinstance(response, list):
                for cat in response:
                    cat_id = cat.get("id")
                    cat_name = cat.get("name")
                    if cat_id and cat_name:
                        categories[cat_id] = {
                            "name": cat_name,
                            "slug": self._slugify(cat_name)
                        }
            
            #logger.info(f"✅ Retrieved {len(categories)} categories from ProductService API")
            return categories
        
        except Exception as e:
            logger.error(f"❌ Failed to get categories from ProductService API: {str(e)}")
            return {}
    
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
    
    async def validate_category(self, user_category: str, detected_attributes: list = None) -> Dict[str, Any]:
        """
        Validate category từ user input
        
        Flow:
        1. Try exact match with DB categories
        2. Try flexible match với UNIVERSAL_KEYWORDS
        3. Nếu không match → tạo category mới với detected_attributes (nếu có)
           - Nếu có detected_attributes: dùng luôn, không cần call LLM
           - Nếu không: call LLM để xác định category mới
        4. Return validated category info
        
        Args:
            user_category: Tên category từ user
            detected_attributes: Danh sách attributes đã được detect từ Comprehensive Analysis
                                Format: ["ram", "cpu", "storage", ...] hoặc
                                       [{"name": "ram", ...}, {"name": "cpu", ...}, ...]
        
        Returns:
            {
                "success": bool,
                "category": str,  # Category name tìm thấy hoặc tạo mới
                "category_id": int | None,  # ID trong DB (None nếu mới)
                "status": "found" | "normalized" | "created_from_api",
                "reason": str
            }
        """
        db_categories = await self.get_db_categories()
        #logger.info(f"db_categories: {db_categories}")
        db_names = {cat["name"].lower(): (cat_id, cat["name"]) for cat_id, cat in db_categories.items()}
        db_slugs = {cat["slug"]: (cat_id, cat["name"]) for cat_id, cat in db_categories.items()}
        
        user_cat_lower = user_category.lower().strip()
        user_slug = self._slugify(user_category)
        
        # STEP 1: Try exact match
        if user_cat_lower in db_names:
            cat_id, cat_name = db_names[user_cat_lower]
            #logger.info(f"✅ Category '{user_category}' → exact match '{cat_name}' (id={cat_id})")
            
            # 🔄 Check nếu có new attributes để update schema
            await self._enqueue_schema_evolution_if_needed(
                category_id=cat_id,
                category_name=cat_name,
                detected_attributes=detected_attributes
            )
            
            return {
                "success": True,
                "category": cat_name,
                "category_id": cat_id,
                "status": "found",
                "reason": "Exact match with database category"
            }
        
        if user_slug in db_slugs:
            cat_id, cat_name = db_slugs[user_slug]
            #logger.info(f"✅ Category '{user_category}' → slug match '{cat_name}' (id={cat_id})")
            
            # 🔄 Check nếu có new attributes để update schema
            await self._enqueue_schema_evolution_if_needed(
                category_id=cat_id,
                category_name=cat_name,
                detected_attributes=detected_attributes
            )
            
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
                        #logger.info(f"✅ Category '{user_category}' → keyword match '{base_cat}' (id={cat_id})")
                        
                        # 🔄 Check nếu có new attributes để update schema
                        await self._enqueue_schema_evolution_if_needed(
                            category_id=cat_id,
                            category_name=cat["name"],
                            detected_attributes=detected_attributes
                        )
                        
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
                                #logger.info(f"✅ Category '{user_category}' → substring match '{base_cat}' (id={cat_id})")
                                
                                # 🔄 Check nếu có new attributes để update schema
                                await self._enqueue_schema_evolution_if_needed(
                                    category_id=cat_id,
                                    category_name=cat["name"],
                                    detected_attributes=detected_attributes
                                )
                                
                                return {
                                    "success": True,
                                    "category": cat["name"],
                                    "category_id": cat_id,
                                    "status": "normalized",
                                    "reason": f"Matched via substring '{keyword}'"
                                }
        
        # STEP 3: Category not found in DB or keywords
        # Check if we have pre-detected attributes from Comprehensive Analysis
        #logger.info(f"⚠️ Category '{user_category}' not found in DB")
        #logger.info(f"[validate_category] Detected attributes available: {detected_attributes is not None}")
        
        if detected_attributes:
            # ✅ USE DETECTED ATTRIBUTES - Don't need LLM extraction
            #logger.info(f"[validate_category] Using pre-detected attributes from Comprehensive Analysis")
            
            # Extract attribute names from detected_attributes
            # Handle both formats: list of strings or list of dicts
            attribute_names = []
            if detected_attributes and len(detected_attributes) > 0:
                first_item = detected_attributes[0]
                if isinstance(first_item, dict):
                    # Format: [{"name": "ram", ...}, {"name": "cpu", ...}]
                    attribute_names = [attr.get("name", attr) for attr in detected_attributes if isinstance(attr, dict)]
                else:
                    # Format: ["ram", "cpu", "storage", ...]
                    attribute_names = [str(attr).strip() for attr in detected_attributes]
            
            #logger.info(f"[validate_category] Extracted attribute names: {attribute_names}")
            
            if self.product_service_client is None:
                logger.error("⚠️ ProductServiceClient not available - cannot create category")
                return {
                    "success": False,
                    "category": user_category,
                    "category_id": None,
                    "status": "unknown_category",
                    "reason": "ProductService client not available. Cannot create category."
                }
            
            # Call ProductService API to create category with detected attributes
            try:
                #logger.info(f"📤 Calling ProductService to create category '{user_category}' with {len(attribute_names)} attributes...")
                
                result = await self.product_service_client.create_category(
                    name=user_category,
                    description=f"Auto-created from detected attributes",
                    category_type="general",
                    attributes=attribute_names
                )
                
                if result.get("success"):
                    category_id = result.get("id")
                    attributes_created = result.get("attributes_created", 0)
                    #logger.info(f"✅ Successfully created category '{user_category}' (id={category_id}, attributes={attributes_created})")
                    
                    return {
                        "success": True,
                        "category": user_category,
                        "category_id": category_id,
                        "status": "created_from_api",
                        "reason": f"Created via ProductService API with {attributes_created} detected attributes"
                    }
                else:
                    # Check if category already exists (not a failure!)
                    reason = result.get("reason", "Failed to create category")
                    if "already exists" in reason.lower():
                        category_id = result.get("id")
                        #logger.info(f"✅ Category '{user_category}' already exists (id={category_id})")
                        return {
                            "success": True,
                            "category": user_category,
                            "category_id": category_id,
                            "status": "existing",
                            "reason": "Category already exists in ProductService"
                        }
                    
                    logger.warning(f"⚠️ ProductService returned failure: {reason}")
                    return {
                        "success": False,
                        "category": user_category,
                        "category_id": None,
                        "status": "creation_failed",
                        "reason": reason
                    }
            
            except Exception as e:
                logger.error(f"❌ Failed to create category via ProductService: {str(e)}")
                return {
                    "success": False,
                    "category": user_category,
                    "category_id": None,
                    "status": "api_error",
                    "reason": f"ProductService API error: {str(e)}"
                }
        
        # FALLBACK: No detected attributes, try LLM to determine category
        #logger.info(f"⚠️ No detected attributes provided, calling LLM for validation...")
        
        
        llm_result = self._validate_with_llm(user_category, db_categories)
        
        if llm_result["success"]:
            if llm_result["status"] == "map_to_existing":
                # LLM says it should map to existing category
                cat_id = llm_result["category_id"]
                cat_name = db_categories[cat_id]["name"]
                #logger.info(f"✅ LLM mapped '{user_category}' → existing '{cat_name}' (id={cat_id})")
                return {
                    "success": True,
                    "category": cat_name,
                    "category_id": cat_id,
                    "status": "normalized",
                    "reason": f"LLM mapped to existing category '{cat_name}'"
                }
            
            elif llm_result["status"] == "create_new":
                # ✅ NEW CATEGORY DETECTED - Create via ProductService API
                llm_attributes = llm_result.get("attributes", [])
                #logger.info(f"[CREATE_NEW] LLM detected new category: '{user_category}'")
                #logger.info(f"[CREATE_NEW] LLM suggested attributes: {llm_attributes}")
                
                if self.product_service_client is None:
                    logger.error("⚠️ ProductServiceClient not available - cannot create category")
                    return {
                        "success": False,
                        "category": user_category,
                        "category_id": None,
                        "status": "unknown_category",
                        "reason": "ProductService client not available. Cannot create category."
                    }
                
                # Call ProductService API to create category
                try:
                    #logger.info(f"📤 Calling ProductService to create category '{user_category}'...")
                    # Use await instead of asyncio.run() since we're already in async context
                    result = await self.product_service_client.create_category(
                        name=user_category,
                        description=llm_result.get("description", ""),
                        category_type=llm_result.get("category_type", "general"),
                        attributes=llm_attributes
                    )
                    
                    if result.get("success"):
                        category_id = result.get("id")
                        attributes_created = result.get("attributes_created", 0)
                        #logger.info(f"✅ Successfully created category '{user_category}' (id={category_id}, attributes={attributes_created})")
                        
                        return {
                            "success": True,
                            "category": user_category,
                            "category_id": category_id,
                            "status": "created_via_api",
                            "reason": f"Created via ProductService API with {attributes_created} attributes"
                        }
                    else:
                        # Check if category already exists (not a failure!)
                        reason = result.get("reason", "Failed to create category")
                        if "already exists" in reason.lower():
                            category_id = result.get("id")
                            #logger.info(f"✅ Category '{user_category}' already exists (id={category_id})")
                            return {
                                "success": True,
                                "category": user_category,
                                "category_id": category_id,
                                "status": "existing",
                                "reason": "Category already exists in ProductService"
                            }
                        
                        logger.warning(f"⚠️ ProductService returned failure: {reason}")
                        return {
                            "success": False,
                            "category": user_category,
                            "category_id": None,
                            "status": "creation_failed",
                            "reason": reason
                        }
                
                except Exception as e:
                    logger.error(f"❌ Failed to create category via ProductService: {str(e)}")
                    return {
                        "success": False,
                        "category": user_category,
                        "category_id": None,
                        "status": "api_error",
                        "reason": f"ProductService API error: {str(e)}"
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
        
        prompt = f"""Bạn là chuyên gia về phân loại sản phẩm e-commerce. Với một danh mục sản phẩm từ user input, 
hãy xác nhận nó là gì và liệt kê các thuộc tính (attributes) quan trọng để lọc sản phẩm.

Các category hiện có trong database: {db_cat_names}

VÍ DỤ FEW-SHOT:

[Ví dụ 1 - Giày]
Input: "giày"
Output:
{{
  "product_name": "Giày",
  "description": "Tất cả loại giày: thể thao, tây, sandal, dép",
  "action": "create_new",
  "mapped_to": null,
  "reason": "Là category sản phẩm cơ bản, cần tạo mới",
  "attributes": ["brand", "size", "color", "type", "material", "gender", "price_range"]
}}

[Ví dụ 2 - Áo]
Input: "áo"
Output:
{{
  "product_name": "Áo",
  "description": "Tất cả loại áo: áo phông, áo sơ mi, áo hoodie, áo khoác",
  "action": "create_new",
  "mapped_to": null,
  "reason": "Là category sản phẩm cơ bản, cần tạo mới",
  "attributes": ["brand", "size", "color", "material", "sleeve_type", "gender", "season"]
}}

[Ví dụ 3 - Laptop]
Input: "laptop"
Output:
{{
  "product_name": "Laptop",
  "description": "Máy tính xách tay, laptop cho công việc và gaming",
  "action": "create_new",
  "mapped_to": null,
  "reason": "Là category sản phẩm cơ bản, cần tạo mới",
  "attributes": ["brand", "cpu", "ram", "storage", "gpu", "screen_size", "weight", "price_range"]
}}

[Ví dụ 4 - Điện thoại]
Input: "điện thoại"
Output:
{{
  "product_name": "Điện thoại",
  "description": "Smartphone, các loại điện thoại di động",
  "action": "create_new",
  "mapped_to": null,
  "reason": "Là category sản phẩm cơ bản, cần tạo mới",
  "attributes": ["brand", "price_range", "color", "storage", "ram", "screen_size", "operating_system"]
}}

[Ví dụ 5 - Bao cao su]
Input: "bao cao su"
Output:
{{
  "product_name": "Bao cao su",
  "description": "Tất cả loại bao cao su với các đặc tính khác nhau",
  "action": "create_new",
  "mapped_to": null,
  "reason": "Là category sản phẩm specific, cần tạo mới",
  "attributes": ["brand", "type", "quantity", "size", "material", "special_feature", "price_range"]
}}

---

HƯỚNG DẪN QUAN TRỌNG:
1. Attributes phải là những đặc tính filtering thực tế của sản phẩm
2. Mỗi attribute phải có thể được dùng để lọc sản phẩm (filterable)
3. Ưu tiên các thuộc tính phổ biến: brand, size, color, price_range, material
4. Thêm các attribute specific cho category (cpu cho laptop, sleeve_type cho áo, v.v.)
5. Suggest 5-8 attributes quan trọng nhất
6. Attributes phải viết theo snake_case (ví dụ: price_range, sleeve_type)
7. Sắp xếp attributes từ quan trọng nhất đến kém quan trọng

USER INPUT: "{user_category}"

Hãy trả lời với JSON có structure sau:
{{
  "product_name": "tên sản phẩm xác nhận",
  "description": "mô tả ngắn về sản phẩm (1-2 câu)",
  "action": "map_to_existing" | "create_new",
  "mapped_to": "tên category trong DB nếu map" | null,
  "reason": "lý do chọn action",
  "attributes": ["attribute_1", "attribute_2", "attribute_3", ...]
}}

NHẮC NHỜ:
- Chỉ trả lời JSON, không có text khác
- Attributes phải practical và commonly used để filter
- Không thêm attributes quá generic như "id", "name", "description"
- Prioritize filtering attributes, không metadata attributes"""
        
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
            
            # Log LLM detection result
            #logger.info(f"[LLM DETECTION] Product name: '{data.get('product_name', 'N/A')}'")
            #logger.info(f"[LLM DETECTION] Description: '{data.get('description', 'N/A')}'")
            #logger.info(f"[LLM DETECTION] Action: {data.get('action', 'N/A')}")
            
            if data["action"] == "map_to_existing":
                mapped_cat = data.get("mapped_to", "").lower().strip()
                #logger.info(f"[LLM DETECTION] Mapped to existing category: '{mapped_cat}'")
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
                attributes = data.get("attributes", [])
                #logger.info(f"[LLM DETECTION] ⭐ CREATE NEW CATEGORY")
                #logger.info(f"[LLM DETECTION] Category: '{user_category}'")
                #logger.info(f"[LLM DETECTION] Suggested Attributes: {attributes}")
                #logger.info(f"[LLM DETECTION] Attributes count: {len(attributes)}")
                # if attributes:
                #     for attr in attributes:
                #         #logger.info(f"[LLM DETECTION]   - {attr}")
                
                return {
                    "success": True,
                    "status": "create_new",
                    "description": data.get("description", ""),
                    "attributes": attributes,
                    "reason": data.get("reason", "")
                }
        
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return {"success": False}
    
    async def _enqueue_schema_evolution_if_needed(
        self,
        category_id: int,
        category_name: str,
        detected_attributes: list = None
    ) -> None:
        """
        Check nếu có new attributes so với category schema
        Nếu có → enqueue schema evolution job (non-blocking)
        
        Args:
            category_id: ID của category
            category_name: Tên category
            detected_attributes: Danh sách attributes detect được
        """
        if not detected_attributes:
            #logger.info(f"ℹ️  No detected attributes to check for schema evolution")
            return
        
        # Extract attribute names
        attribute_names = []
        if detected_attributes and len(detected_attributes) > 0:
            first_item = detected_attributes[0]
            if isinstance(first_item, dict):
                # Format: [{"name": "ram", ...}, {"name": "cpu", ...}]
                attribute_names = [attr.get("name", attr) for attr in detected_attributes if isinstance(attr, dict)]
            else:
                # Format: ["ram", "cpu", "storage", ...]
                attribute_names = [str(attr).strip() for attr in detected_attributes]
        
        if not attribute_names:
            #logger.info(f"ℹ️  No attributes to check for schema evolution")
            return
        
        #logger.info(f"🔍 Checking schema evolution for category '{category_name}' (id={category_id})")
        #logger.info(f"   Detected attributes: {attribute_names}")
        
        try:
            # Call schema evolution service (async, non-blocking)
            # This will enqueue enrichment jobs if needed
            result = await self.schema_evolution_service.evolve_category_schema(
                category_id=category_id,
                category_name=category_name,
                new_attributes=attribute_names
            )
            
            # if result.get("success"):
            #     if result.get("new_attributes_added"):
            #         #logger.info(f"✨ Schema evolved: {result}")
            #     else:
            #         #logger.info(f"ℹ️  No new attributes needed")
            # else:
            #     logger.warning(f"⚠️ Schema evolution warning: {result.get('reason')}")
        
        except Exception as e:
            logger.warning(f"⚠️ Error checking schema evolution: {str(e)}")
            # Don't fail the validation flow, just log warning

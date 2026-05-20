# -*- coding: utf-8 -*-
"""
Category Schema Evolution Service

Xử lý khi category đã tồn tại nhưng xuất hiện attribute mới:
1. Detect new attributes so với existing attributes
2. Update category schema vào ProductService
3. Sync product SKU attributes
4. Enqueue enrichment jobs qua RabbitMQ
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import os
import asyncio
from difflib import SequenceMatcher

load_dotenv()
logger = logging.getLogger(__name__)

# Constants for semantic validation
FUZZY_MATCH_THRESHOLD = 0.75  # ≥75% similarity = high confidence fuzzy match
EXACT_NORMALIZED_THRESHOLD = 0.85  # ≥85% for LLM validation (if no good fuzzy match)
COMMON_FEATURE_KEYWORDS = {
    "inverter", "ai dd", "oled", "amoled", "uhd", "4k", "8k",
    "smart", "wifi", "bluetooth", "nfc", "5g", "4g",
    "pro", "max", "plus", "lite", "ultra", "premium",
    "gen", "generation", "v1", "v2", "v3", "2024", "2025"
}  # Common product features that should NOT become attributes


class CategorySchemaEvolution:
    """Handle category schema updates và enrichment pipeline"""
    
    def __init__(self, product_service_client=None, crawl_service_client=None, llm_client=None):
        self.product_service_client = product_service_client
        self.crawl_service_client = crawl_service_client 
        self.llm_client = llm_client
        self._llm_validation_cache = {}  
    
    def _normalize_attribute_name(self, attr: str) -> str:
        """
        Normalize attribute name để compare
        
        Ví dụ:
        - "RAM" → "ram"
        - "khả năng chống nước" → "khả năng chống nước"
        - "dung lượng pin" → "dung lượng pin"
        """
        return str(attr).lower().strip()
    
    def _is_common_feature_value(self, attr: str) -> bool:
        """
        Check nếu attribute là common product feature/value thay vì true attribute
        
        Ví dụ:
        - "inverter" → True (feature)
        - "AI DD" → True (feature)
        - "4K OLED" → True (feature)
        - "khả năng chống nước" → False (attribute)
        
        Args:
            attr: Attribute name to check
        
        Returns:
            True nếu là common feature/value, False nếu là true attribute
        """
        normalized = self._normalize_attribute_name(attr)
        
        # Check exact match
        if any(keyword in normalized for keyword in COMMON_FEATURE_KEYWORDS):
            logger.debug(f"🏷️  '{attr}' detected as common feature/value")
            return True
        
        return False
    
    def _fuzzy_match_attribute(
        self,
        detected_attr: str,
        existing_attributes: List[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Fuzzy match detected attribute against existing attributes
        
        Uses SequenceMatcher for similarity calculation
        
        Args:
            detected_attr: Attribute to find match for
            existing_attributes: List of existing attributes
        
        Returns:
            (matched_attribute, similarity_score) hoặc None nếu không tìm được match
            - similarity_score ∈ [0, 1]
            - Returns match nếu similarity ≥ FUZZY_MATCH_THRESHOLD
        """
        detected_norm = self._normalize_attribute_name(detected_attr)
        best_match = None
        best_score = 0.0
        
        for existing_attr in existing_attributes:
            existing_norm = self._normalize_attribute_name(existing_attr)
            
            # Skip if exact normalized match (will be caught earlier)
            if detected_norm == existing_norm:
                continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, detected_norm, existing_norm).ratio()
            
            if similarity > best_score:
                best_score = similarity
                best_match = existing_attr
        
        # Return match nếu đạt ngưỡng
        if best_score >= FUZZY_MATCH_THRESHOLD:
            logger.info(f"✨ Fuzzy match: '{detected_attr}' ↔ '{best_match}' (score: {best_score:.2f})")
            return (best_match, best_score)
        
        logger.debug(f"❌ No fuzzy match for '{detected_attr}' (best score: {best_score:.2f})")
        return None
    
    async def validate_attribute_semantics(
        self,
        detected_attribute: str,
        existing_attributes: List[str],
        category_name: str
    ) -> Dict[str, Any]:
        """
        Validate attribute semantically using LLM
        
        Decision flow:
        1. Check nếu là common feature → ignore
        2. Check fuzzy match → reuse
        3. Call LLM để quyết định: reuse / ignore / new_attribute
        
        Args:
            detected_attribute: Attribute cần validate
            existing_attributes: Danh sách existing attributes của category
            category_name: Tên category (cho context)
        
        Returns:
            {
                "decision": "reuse" | "ignore" | "new_attribute",
                "mapped_to": Optional[str],  # Nếu reuse
                "confidence": float,  # ∈ [0, 1]
                "reason": str,
                "validation_method": "common_feature" | "fuzzy_match" | "llm"
            }
        """
        try:
            # STEP 1: Check nếu là common feature/value
            if self._is_common_feature_value(detected_attribute):
                return {
                    "decision": "ignore",
                    "mapped_to": None,
                    "confidence": 1.0,
                    "reason": f"'{detected_attribute}' is a common product feature/value, not an attribute",
                    "validation_method": "common_feature"
                }
            
            # STEP 2: Try fuzzy match
            fuzzy_result = self._fuzzy_match_attribute(detected_attribute, existing_attributes)
            if fuzzy_result:
                matched_attr, score = fuzzy_result
                return {
                    "decision": "reuse",
                    "mapped_to": matched_attr,
                    "confidence": score,
                    "reason": f"High fuzzy match similarity ({score:.2%}) with existing attribute",
                    "validation_method": "fuzzy_match"
                }
            
            # STEP 3: LLM semantic validation (only for unresolved)
            if self.llm_client is None:
                logger.warning(f"⚠️  LLM client not available, treating as new attribute: '{detected_attribute}'")
                return {
                    "decision": "new_attribute",
                    "mapped_to": None,
                    "confidence": 0.5,
                    "reason": "LLM client not available, defaulting to new_attribute",
                    "validation_method": "none"
                }
            
            # Build cache key
            cache_key = f"{detected_attribute}|{category_name}"
            if cache_key in self._llm_validation_cache:
                logger.debug(f"📦 Using cached LLM validation for '{detected_attribute}'")
                return self._llm_validation_cache[cache_key]
            
            logger.info(f"🤖 Calling LLM for semantic validation: '{detected_attribute}' (category: {category_name})")
            
            # Call LLM
            llm_response = await self._call_llm_for_attribute_validation(
                detected_attribute,
                existing_attributes,
                category_name
            )
            
            # Cache result
            self._llm_validation_cache[cache_key] = llm_response
            
            return llm_response
        
        except Exception as e:
            logger.error(f"❌ Semantic validation failed for '{detected_attribute}': {str(e)}")
            return {
                "decision": "new_attribute",
                "mapped_to": None,
                "confidence": 0.3,
                "reason": f"Validation error: {str(e)}",
                "validation_method": "none"
            }
    
    async def _call_llm_for_attribute_validation(
        self,
        detected_attribute: str,
        existing_attributes: List[str],
        category_name: str
    ) -> Dict[str, Any]:
        """
        Call LLM để quyết định attribute validation
        
        Args:
            detected_attribute: Attribute cần validate
            existing_attributes: Danh sách existing attributes
            category_name: Category name
        
        Returns:
            Validation decision dict
        """
        # Build prompt với strong bias về reuse schema
        prompt = f"""
Bạn là schema evolution expert cho ecommerce search system.

Category: {category_name}
Existing Attributes: {', '.join(existing_attributes)}
Detected Attribute: {detected_attribute}

Task: Quyết định xử lý detected attribute.

Quy tắc (ưu tiên từ cao đến thấp):
1. REUSE: Nếu detected attribute có CÙNG ý NGHĨA với existing attribute (chỉ khác wording)
   VÍ DỤ: "thương hiệu" vs "hãng" → REUSE "hãng"
           "kiểu cửa" vs "loại cửa" → REUSE "loại cửa"
   
2. IGNORE: Nếu detected attribute là product feature/value, KHÔNG phải true attribute
   VÍ DỤ: "inverter", "AI DD", "OLED", "4K", "smart", "WiFi" → IGNORE
   
3. NEW_ATTRIBUTE: Chỉ nếu thực sự mới và là true attribute
   VÍ DỤ: "độ ồn" (nếu category có type "washing machine") → NEW_ATTRIBUTE

Response format (JSON):
{{
    "decision": "reuse" | "ignore" | "new_attribute",
    "mapped_to": "existing_attr_name hoặc null",
    "confidence": 0.0-1.0,
    "reason": "short reason"
}}

Hãy STRONGLY BIAS về REUSE existing schema. Chỉ tạo attribute mới khi thực sự cần.
"""
        
        try:
            # Call LLM via client
            # Note: Adjust based on your actual LLM client implementation
            response = await self.llm_client.complete(
                prompt=prompt,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=200
            )
            
            # Parse response
            response_text = response.strip()
            logger.debug(f"📥 LLM response: {response_text}")
            
            # Try to extract JSON
            try:
                # If response is wrapped in markdown code block
                if "```json" in response_text:
                    json_start = response_text.index("{")
                    json_end = response_text.rindex("}") + 1
                    response_text = response_text[json_start:json_end]
                elif "```" in response_text:
                    json_start = response_text.index("{")
                    json_end = response_text.rindex("}") + 1
                    response_text = response_text[json_start:json_end]
                
                result = json.loads(response_text)
                
                # Validate keys
                if "decision" in result and "confidence" in result and "reason" in result:
                    result["validation_method"] = "llm"
                    if "mapped_to" not in result:
                        result["mapped_to"] = None
                    return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"⚠️  Failed to parse LLM JSON response: {e}")
            
            # Fallback if parsing fails
            return {
                "decision": "new_attribute",
                "mapped_to": None,
                "confidence": 0.5,
                "reason": "Failed to parse LLM response, defaulting to new_attribute",
                "validation_method": "llm"
            }
        
        except Exception as e:
            logger.error(f"❌ LLM call failed: {str(e)}")
            return {
                "decision": "new_attribute",
                "mapped_to": None,
                "confidence": 0.3,
                "reason": f"LLM error: {str(e)}",
                "validation_method": "none"
            }
    
    async def detect_new_attributes(
        self,
        existing_attributes: List[str],
        new_attributes: List[str],
        category_name: str = "unknown"
    ) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
        """
        Detect truly new attributes với semantic validation
        
        Flow:
        1. Exact normalized match
        2. Fuzzy/synonym match
        3. LLM semantic validation (for unresolved)
        
        Args:
            existing_attributes: Danh sách attributes hiện có của category
            new_attributes: Danh sách attributes detect được từ crawl/LLM
            category_name: Tên category (cho LLM context)
        
        Returns:
            (truly_new_attributes, validation_results)
            - truly_new_attributes: List các attributes thực sự mới
            - validation_results: Dict detailed validation info cho mỗi detected attribute
                {
                    "attribute_name": {
                        "decision": ...,
                        "mapped_to": ...,
                        "confidence": ...,
                        "reason": ...,
                        "validation_method": ...
                    }
                }
        
        Ví dụ:
        >>> existing = ["hãng", "loại cửa", "khối lượng giặt"]
        >>> detected = ["thương hiệu", "AI DD", "độ ồn"]
        >>> truly_new, details = await detect_new_attributes(existing, detected, "washing_machine")
        >>> truly_new
        ["độ ồn"]
        >>> details["thương hiệu"]["decision"]
        "reuse"
        >>> details["thương hiệu"]["mapped_to"]
        "hãng"
        """
        truly_new = []
        validation_results = {}
        
        logger.info(f"🔍 Detecting new attributes for category '{category_name}'")
        logger.info(f"   Existing: {existing_attributes}")
        logger.info(f"   Detected: {new_attributes}")
        
        # Normalize existing untuk quick lookups
        existing_normalized_set = {
            self._normalize_attribute_name(attr): attr
            for attr in existing_attributes
        }
        
        # Process mỗi detected attribute
        for detected_attr in new_attributes:
            # Skip empty/None
            if not detected_attr or not str(detected_attr).strip():
                continue
            
            # STEP 1: Exact normalized match
            normalized = self._normalize_attribute_name(detected_attr)
            if normalized in existing_normalized_set:
                matched = existing_normalized_set[normalized]
                logger.debug(f"✅ Exact match: '{detected_attr}' ↔ '{matched}'")
                validation_results[detected_attr] = {
                    "decision": "reuse",
                    "mapped_to": matched,
                    "confidence": 1.0,
                    "reason": "Exact normalized match",
                    "validation_method": "exact_match"
                }
                continue
            
            # STEP 2 + 3: Fuzzy match + LLM validation
            validation_result = await self.validate_attribute_semantics(
                detected_attr,
                existing_attributes,
                category_name
            )
            
            validation_results[detected_attr] = validation_result
            
            # Nếu truly new (sau cả fuzzy match và LLM)
            if validation_result["decision"] == "new_attribute":
                truly_new.append(detected_attr)
                logger.info(f"✨ NEW ATTRIBUTE: '{detected_attr}' (confidence: {validation_result['confidence']:.2%})")
            else:
                logger.info(f"↔️  RESOLVED: '{detected_attr}' → {validation_result['decision']} "
                           f"(mapped: {validation_result.get('mapped_to', 'N/A')}, "
                           f"confidence: {validation_result['confidence']:.2%})")
        
        logger.info(f"📊 Summary: {len(new_attributes)} detected, "
                   f"{len(truly_new)} truly new, "
                   f"{len(validation_results) - len(truly_new)} resolved/ignored")
        
        return truly_new, validation_results
    
    async def evolve_category_schema(
        self,
        category_id: int,
        category_name: str,
        new_attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Evolve category schema: thêm attributes mới vào category
        
        Flow:
        1. Get existing attributes từ ProductService
        2. Detect new attributes (với semantic validation)
        3. Nếu có new attributes:
           - Update category attributes qua ProductService
           - Sync product SKU attributes
           - Enqueue enrichment jobs
        
        Args:
            category_id: ID của category
            category_name: Tên category
            new_attributes: Danh sách attributes detect được
        
        Returns:
            {
                "success": bool,
                "category_id": int,
                "new_attributes_added": List[str],
                "products_synced": int,
                "enrichment_jobs_enqueued": int,
                "validation_details": Dict  # Validation results cho mỗi detected attribute
            }
        """
        if self.product_service_client is None:
            logger.error("❌ ProductServiceClient not available")
            return {
                "success": False,
                "category_id": category_id,
                "new_attributes_added": [],
                "products_synced": 0,
                "enrichment_jobs_enqueued": 0,
                "reason": "ProductService client not available"
            }
        
        try:
            # STEP 1: Get existing attributes
            logger.info(f"📤 Getting existing attributes for category '{category_name}' (id={category_id})...")
            
            category_details = await self.product_service_client.get_category_details(category_id)
            logger.info(f"📥 Category details: {category_details}")
            existing_attributes = []
            
            if category_details and category_details.get("attributes"):
                existing_attributes = [
                    attr.get("attribute_name", attr) 
                    for attr in category_details.get("attributes", [])
                ]
            
            logger.info(f"✅ Retrieved {len(existing_attributes)} existing attributes")
            logger.info(f"   Existing: {existing_attributes}")
            
            # STEP 2: Detect new attributes (with semantic validation)
            logger.info(f"🔍 Starting semantic validation for {len(new_attributes)} detected attributes...")
            truly_new_attrs, validation_details = await self.detect_new_attributes(
                existing_attributes,
                new_attributes,
                category_name
            )
            logger.info(f"✅ Semantic validation complete")
            
            if not truly_new_attrs:
                logger.info(f"ℹ️  No new attributes to add to category '{category_name}'")
                return {
                    "success": True,
                    "category_id": category_id,
                    "new_attributes_added": [],
                    "products_synced": 0,
                    "enrichment_jobs_enqueued": 0,
                    "reason": "No new attributes detected",
                    "validation_details": validation_details
                }
            
            logger.info(f"✨ New attributes to add: {truly_new_attrs}")
            
            # STEP 3: Update category schema vào ProductService
            logger.info(f"📤 Updating category schema with {len(truly_new_attrs)} new attributes...")
            
            update_result = await self.product_service_client.add_category_attributes(
                category_id=category_id,
                attributes=truly_new_attrs
            )
            
            if not update_result.get("success"):
                logger.error(f"❌ Failed to update category attributes: {update_result.get('reason')}")
                return {
                    "success": False,
                    "category_id": category_id,
                    "new_attributes_added": [],
                    "products_synced": 0,
                    "enrichment_jobs_enqueued": 0,
                    "reason": f"Failed to update category: {update_result.get('reason')}",
                    "validation_details": validation_details
                }
            
            logger.info(f"✅ Successfully added {len(truly_new_attrs)} attributes to category")
            
            # STEP 4: Sync product SKU attributes
            products_synced = await self._sync_product_sku_attributes(
                category_id=category_id,
                new_attributes=truly_new_attrs
            )
            
            # STEP 5: Enqueue enrichment jobs
            enrichment_jobs_enqueued = await self._enqueue_enrichment_jobs(
                category_id=category_id,
                category_name=category_name,
                new_attributes=truly_new_attrs,
                products_count=products_synced
            )
            
            return {
                "success": True,
                "category_id": category_id,
                "new_attributes_added": truly_new_attrs,
                "products_synced": products_synced,
                "enrichment_jobs_enqueued": enrichment_jobs_enqueued,
                "validation_details": validation_details
            }
        
        except Exception as e:
            logger.error(f"❌ Schema evolution failed: {str(e)}")
            return {
                "success": False,
                "category_id": category_id,
                "new_attributes_added": [],
                "products_synced": 0,
                "enrichment_jobs_enqueued": 0,
                "reason": str(e)
            }
    
    async def _sync_product_sku_attributes(
        self,
        category_id: int,
        new_attributes: List[str]
    ) -> int:
        """
        Sync SKU attributes cho tất cả products của category
        
        Thêm missing attributes = null vào sku_attributes
        Không overwrite existing values
        
        Args:
            category_id: ID của category
            new_attributes: Danh sách attributes mới
        
        Returns:
            Số products được sync
        """
        if self.product_service_client is None:
            logger.warning("⚠️ Cannot sync product SKU attributes: ProductService client not available")
            return 0
        
        try:
            logger.info(f"🔄 Syncing SKU attributes for {len(new_attributes)} new attributes...")
            
            # Call ProductService để sync SKU attributes
            result = await self.product_service_client.sync_product_sku_attributes(
                category_id=category_id,
                attributes=new_attributes
            )
            
            products_synced = result.get("products_synced", 0) if result else 0
            logger.info(f"✅ Synced {products_synced} products")
            
            return products_synced
        
        except Exception as e:
            logger.error(f"⚠️ Error syncing product SKU attributes: {str(e)}")
            return 0
    
    async def _enqueue_enrichment_jobs(
        self,
        category_id: int,
        category_name: str,
        new_attributes: List[str],
        products_count: int
    ) -> int:
        """
        Enqueue background enrichment jobs via CrawlService (like CASE 1 pattern)
        
        Uses CrawlServiceClient to enqueue enrichment tasks. Non-blocking.
        
        Args:
            category_id: ID của category
            category_name: Tên category
            new_attributes: Danh sách attributes cần enrich
            products_count: Số products cần enrich
        
        Returns:
            Số enrichment jobs được enqueue
        """
        if products_count == 0:
            logger.info("ℹ️  No products to enrich")
            return 0
        
        if self.crawl_service_client is None:
            logger.warning("⚠️ Cannot enqueue enrichment jobs: CrawlService client not available")
            return 0
        
        try:
            logger.info(f"📤 Enqueueing enrichment job via CrawlService for {len(new_attributes)} attributes...")
            
            enrichment_task = {
                "type": "enrichment",
                "category_id": category_id,
                "category_name": category_name,
                "attributes": new_attributes,
                "action": "recrawl_and_extract_attributes",
                "description": f"Enrichment for new attributes: {', '.join(new_attributes)}"
            }
            
            # Use CrawlService enqueue method (async, non-blocking like CASE 1)
            task_id = await self.crawl_service_client.enqueue_enrichment_task(
                task_data=enrichment_task,
                priority="normal"
            )
            
            logger.info(f"✅ Successfully enqueued enrichment job via CrawlService: {task_id}")
            return 1  # Enqueued 1 enrichment task
        
        except Exception as e:
            logger.error(f"⚠️ Error enqueueing enrichment job: {str(e)}")
            return 0


# Example usage
if __name__ == "__main__":
    # Test fuzzy matching and semantic validation
    async def test_detection():
        evolution_service = CategorySchemaEvolution()
        
        existing = ["hãng", "loại cửa", "khối lượng giặt"]
        detected = ["thương hiệu", "AI DD", "độ ồn"]
        
        # Test 1: Without LLM (fuzzy match only)
        print("\n=== TEST 1: Fuzzy matching only ===")
        truly_new, details = await evolution_service.detect_new_attributes(
            existing, detected, "washing_machine"
        )
        print(f"Truly new: {truly_new}")
        print(f"Details: {json.dumps(details, ensure_ascii=False, indent=2)}")
        
        # Expected output:
        # - "thương hiệu" → reuse "hãng" (high fuzzy match)
        # - "AI DD" → ignore (common feature)
        # - "độ ồn" → new_attribute (unresolved, no LLM)
    
    asyncio.run(test_detection())

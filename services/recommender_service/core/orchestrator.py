# app/core/orchestrator.py

from asyncio.log import logger
import re
from typing import Dict, Any, List
from .extractor import AttributeExtractor
from .dialogue import DialogueManager
from .matcher import ProductMatcher
from .ranker import ProductRanker
# 🚀 REMOVED: from app.crawler.multi_crawler import MultiCrawler
from services.crawl_service_client import CrawlServiceClient  # ✅ Use absolute import
from services.product_service_client import ProductServiceClient  # ✅ Use absolute import
from .schema import get_schema
from .intent import EnhancedIntentDetector
from .intent_mapper import IntentMapper
from .dynamic_schema import DynamicSchemaManager, AVAILABLE_CATEGORIES
from .llm_utils import call_openai
from .category_cache import CategoryCache
from services.category_validator import CategoryValidator  # ✅ Use absolute import
from services.product_repository import ProductRepository  # ✅ Use absolute import

class RecommendationOrchestrator:
    """
    Orchestrator cải tiến - xử lý intent phức tạp
    
    Sử dụng Dynamic Schema System để hỗ trợ ANY product category
    Implements 7-case routing logic for assisted shopping
    """
    
    def __init__(self):
        
        self.intent_detector = EnhancedIntentDetector()
        self.intent_mapper = IntentMapper()
        self.attribute_extractor = AttributeExtractor()
        self.schema_manager = DynamicSchemaManager()  # Add dynamic schema manager
        self.dialogue_manager = DialogueManager()
        self.product_matcher = ProductMatcher()
        self.product_ranker = ProductRanker()
        # 🚀 CHANGED: Use CrawlServiceClient instead of MultiCrawler
        self.crawl_service_client = CrawlServiceClient()  # ✅ HTTP client to Crawl Service (8003)
        self.product_service_client = ProductServiceClient()  # ✅ HTTP client to Product Service (8001)
        self.category_validator = CategoryValidator(product_service_client=self.product_service_client)  # ✅ Pass ProductServiceClient
        self.product_repository = ProductRepository()  # NEW: Query DB before crawl
        
        # Cache management (Lazada-style)
        self.enable_cache = True  # Set to False to disable caching
        
        # LLM suggestion cache - avoid repeated LLM calls
        self.llm_suggestion_cache = {}  # key: user_input hash, value: suggestions
        
        # Category cache - persistent storage for LLM suggestions
        # Dùng PostgreSQL (đã có sẵn DATABASE_URL trong .env)
        import os
        database_url = os.getenv(
            "DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kltn')}"
        )
        self.category_cache = CategoryCache(
            backend="postgres",
            pg_url=database_url
        )
        
        # Comparison keywords for Case 7 detection
        self.comparison_keywords = [
            "so sánh", "khác", "hơn", "tốt hơn", "bền hơn", "rẻ hơn", "đẹp hơn",
            "với", "hay", "or", "vs", "versus", "compare", "comparison",
            "nên chọn", "nên mua", "cái nào", "loại nào"
        ]
    
    # ====================================================================================
    # CENTRAL 7-CASE DISPATCHER SYSTEM
    # ====================================================================================
    
    def classify_request_case(
        self, 
        user_input: str, 
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify user request into one of 7 cases.
        
        Uses detected_intent from Intent Mapper - NO re-analysis!
        
        Flow:
        1. Get detected_intent from conversation_state (populated by STEP 0)
        2. Check for special conversation states (CASE 5, CASE 6)
        3. Classify based ONLY on intent_type + confidence + categories
        """
        
        # Get intent detection result (from STEP 0)
        detected_intent = conversation_state.get("detected_intent", {})
        intent_type = detected_intent.get("intent_type", "none")
        intent = detected_intent.get("intent")
        categories = detected_intent.get("categories", [])
        confidence = detected_intent.get("confidence", 0.0)
        is_new_category = detected_intent.get("is_new_category", False)
        
        logger.info(f"[classify_request_case] Classifying based on intent_type='{intent_type}', confidence={confidence:.2f}, categories={categories}, is_new={is_new_category}")
        
        # ===== PRIORITY 0: Dynamic Category Creation (NEW categories not in DB) =====
        if is_new_category and categories:
            logger.info(f"[classify_request_case] ✅ CASE 8: New category '{categories[0]}' needs schema creation")
            return {
                "case": 8,
                "case_name": "dynamic_category_creation",
                "reason": f"User requested new category '{categories[0]}' not in system",
                "data": {
                    "new_category": categories[0],
                    "intent": intent,
                    "should_create_schema": True,
                    "should_crawl": True
                }
            }
        
        # ===== PRIORITY 1: Special conversation states =====
        
        # CASE 7: Comparison/advisory request (NO immediate crawl)
        if intent_type == "comparison":
            logger.info(f"[classify_request_case] ✅ CASE 7: Comparison/advisory detected")
            return {
                "case": 7,
                "case_name": "comparison_advisory",
                "reason": "User asks for comparison or advice, not immediate purchase",
                "data": {
                    "needs_llm_response": True,
                    "should_crawl": False
                }
            }
        
        # CASE 5: Intent shift (context reset) - ONLY if in conversation and input changed
        if conversation_state.get("has_category"):
            last_input = conversation_state.get("last_user_input", "").strip().lower()
            current_input = user_input.strip().lower()
            
            if last_input != current_input:  # Only if input is DIFFERENT
                # Check if category changed
                old_category = conversation_state.get("category")
                new_categories = categories
                
                # Detect intent shift in 2 ways:
                # 1. Old category completely removed from new categories (clear shift)
                # 2. Category scope exploded (e.g., specific "quần áo" → 7 gift categories)
                
                category_removed = old_category and new_categories and old_category.lower() not in [c.lower() for c in new_categories]
                scope_exploded = (
                    old_category and 
                    new_categories and 
                    old_category.lower() in [c.lower() for c in new_categories] and  # Old category still present but...
                    len(new_categories) > 3  # ...suddenly many new categories appeared
                )
                
                if category_removed or scope_exploded:
                    reason = (
                        f"User switched from '{old_category}' to new category"
                        if category_removed
                        else f"User expanded scope: '{old_category}' → {len(new_categories)} gift categories"
                    )
                    logger.info(f"[classify_request_case] ✅ CASE 5: Intent shift detected - {reason}")
                    return {
                        "case": 5,
                        "case_name": "intent_shift",
                        "reason": reason,
                        "data": {
                            "old_category": old_category,
                            "new_category": new_categories[0] if new_categories else None,
                            "should_reset": True
                        }
                    }
        
        # CASE 6: Incremental refinement (context accumulation)
        if conversation_state.get("has_category") and conversation_state.get("extracted"):
            last_input = conversation_state.get("last_user_input", "").strip().lower()
            current_input = user_input.strip().lower()
            
            if last_input != current_input and intent_type == "specific":
                # User added more attributes to same category
                old_category = conversation_state.get("category")
                if old_category and categories and old_category in [c.lower() for c in categories]:
                    logger.info(f"[classify_request_case] ✅ CASE 6: Incremental refinement")
                    return {
                        "case": 6,
                        "case_name": "incremental_refinement",
                        "reason": "User adding or modifying attributes in same category",
                        "data": {
                            "intent_type": "refine",
                            "should_merge": True
                        }
                    }
        
        # ===== PRIORITY 2: Based on intent_type =====
        
        # CASE 4: Abstract intent (high-level need, no specific product)
        if intent_type == "abstract":
            logger.info(f"[classify_request_case] ✅ CASE 4: Abstract intent detected")
            return {
                "case": 4,
                "case_name": "abstract_intent",
                "reason": "User expresses high-level need or purpose without specific product",
                "data": {
                    "needs_llm": True,
                    "suggest_categories": True
                }
            }
        
        # CASE 1: Clear/Specific request (intent_type == "specific" + high confidence)
        if intent_type == "specific" and confidence >= 0.65 and categories:
            logger.info(f"[classify_request_case] ✅ CASE 1: Specific request with high confidence")
            return {
                "case": 1,
                "case_name": "clear_request",
                "reason": "Intent Mapper detected specific product/category with confidence >= 0.65",
                "data": {
                    "category": categories[0],
                    "confidence": confidence,
                    "should_use_llm": False,
                    "can_crawl_immediately": True
                }
            }
        
        # CASE 2: Specific intent but lower confidence OR missing attributes
        if intent_type == "specific" and 0.5 <= confidence < 0.65 and categories:
            logger.info(f"[classify_request_case] ✅ CASE 2: Specific but lower confidence")
            return {
                "case": 2,
                "case_name": "unclear_with_schema",
                "reason": "Intent detected but confidence or attributes are incomplete",
                "data": {
                    "category": categories[0],
                    "confidence": confidence,
                    "should_ask_attributes": True
                }
            }
        
        # CASE 3: Unclear/None intent (no category detected or confidence too low)
        logger.info(f"[classify_request_case] ✅ CASE 3: Unclear intent, need LLM inference")
        return {
            "case": 3,
            "case_name": "unclear_no_schema",
            "reason": f"Intent type '{intent_type}' or confidence {confidence:.2f} too low for direct action",
            "data": {
                "should_use_llm": True,
                "detected_intent": intent_type,
                "confidence": confidence
            }
        }
    
    def _is_comparison_request(self, user_input: str) -> bool:
        """
        ⚠️  DEPRECATED: Use intent_mapper.intent_type == "comparison" instead
        
        This function is kept for backward compatibility but no longer used by classify_request_case()
        """
        pass  # Logic moved to intent_mapper._infer_intent_type()
    
    def _is_abstract_intent(self, user_input: str) -> bool:
        """
        ⚠️  DEPRECATED: Use intent_mapper.intent_type == "abstract" instead
        
        This function is kept for backward compatibility but no longer used by classify_request_case()
        """
        pass  # Logic moved to intent_mapper._infer_intent_type()
    
    def _assess_query_clarity(self, user_input: str) -> float:
        """
        ⚠️  DEPRECATED: No longer used for Case classification
        
        Intent Mapper's intent_type + confidence replaces this logic.
        Kept for backward compatibility only.
        """
        return 0.5  # Default value for legacy code
    
    def _quick_category_detection(self, user_input: str) -> Dict[str, Any]:
        """
        ⚠️  DEPRECATED: No longer used for Case classification
        
        Intent Mapper handles all category detection (pattern + LLM).
        Kept for backward compatibility only.
        """
        return {"category": None, "confidence": 0.0}
    
    # ====================================================================================
    # CASE HANDLERS
    # ====================================================================================
    
    async def handle_case_1_clear_request(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 1: Clear request (NO LLM)
        
        Flow:
        1. Detect category
        2. VALIDATE category with DB (new!)
        3. Extract attributes
        4. Crawl with validated category
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 1] Processing clear request with rule-based extraction")
        
        category = case_data["category"]
        
        # NEW: Validate category before crawling
        logger.info(f"[CASE 1] Validating category: '{category}'")
        validation_result = await self.category_validator.validate_category(category)
        if not validation_result["success"]:
            logger.info(f"[CASE 1] ❌ Category validation failed: {validation_result['reason']}")
            return {
                "status": "error",
                "message": f"Không thể xác định danh mục sản phẩm '{category}'. {validation_result['reason']}",
                "case": 1,
                "state": conversation_state
            }
        
        # Use validated category
        validated_category = validation_result["category"]
        category_id = validation_result["category_id"]
        validation_status = validation_result["status"]
        
        logger.info(f"[CASE 1] ✅ Category validated: '{category}' → '{validated_category}' (id={category_id}, status={validation_status})")
        
        conversation_state["has_category"] = True
        conversation_state["category"] = validated_category
        conversation_state["category_id"] = category_id
        conversation_state["category_validation"] = {
            "original": category,
            "normalized": validated_category,
            "status": validation_status
        }
        
        # Extract attributes using rule-based extractor (NO LLM)
        extract_result = self.attribute_extractor.extract(
            user_input,
            validated_category,
            use_llm=False  # CRITICAL: No LLM for Case 1
        )
        
        conversation_state["extracted"] = extract_result["extracted"]
        
        logger.info(f"[CASE 1] Extracted attributes: {extract_result['extracted']}")
        
        # ⭐ FALLBACK: If attributes empty, use product_name from IntentMapper as search hint
        attributes_for_search = extract_result["extracted"].copy()
        if not attributes_for_search or len(attributes_for_search) == 0:
            product_name = conversation_state.get("detected_intent", {}).get("product_name", "").strip()
            if product_name and product_name.lower() != validated_category.lower():
                # Use product_name as "loai" (type) for better search
                attributes_for_search["loai"] = product_name
                logger.info(f"[CASE 1] 💡 No attributes extracted → Using product_name as search hint: '{product_name}'")
        
        # Query DB first before crawling
        logger.info(f"[CASE 1] 🔍 Querying database for products...")
        db_products = self.product_repository.query_by_category_and_attributes(
            category_id=category_id,
            attributes=attributes_for_search,
            limit=50
        )
        
        if db_products:
            # DB HIT: Found products in database
            logger.info(f"[CASE 1] ✅ DB HIT! Found {len(db_products)} products in database")
            return await self._process_crawl_results(db_products, conversation_state, case=1, source="db")
        
        # DB MISS: Products not in DB, crawl from external sources via Crawl Service (8003)
        logger.info(f"[CASE 1] ❌ DB MISS! Crawling from external sources (Lazada/Tiki/Shopee) via CrawlService...")
        crawled_products = await self.crawl_service_client.crawl(
            category=validated_category,
            category_id=category_id,
            attributes=attributes_for_search
        )
        
        if not crawled_products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": 1,
                "state": conversation_state
            }
        
        # ✅ Save crawled products to Product Service (not directly to DB)
        logger.info(f"[CASE 1] 💾 Saving {len(crawled_products)} crawled products via Product Service...")
        try:
            await self.product_service_client.save_products(crawled_products, source="tiki")
        except Exception as e:
            logger.warning(f"[CASE 1] ⚠️ Failed to save products via Product Service: {e}")
        
        # Return crawled products directly (already complete from CrawlService)
        return await self._process_crawl_results(crawled_products, conversation_state, case=1, source="crawl")
    
    def _ensure_state_structure(self, conversation_state: Dict[str, Any]):
        """Ensure conversation_state has all required keys for safety"""
        defaults = {
            "has_category": False,
            "category": None,
            "extracted": {},
            "missing_required": [],
            "search_history": [],
            "attributes_asked": [],
            "cached_products": None,
            "cached_filters": None,
            "last_crawl_params": None,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_user_input": ""  # Track previous user input to avoid false intent_shift detection
        }
        for key, value in defaults.items():
            if key not in conversation_state:
                conversation_state[key] = value if not isinstance(value, list) and not isinstance(value, dict) else (value.copy() if isinstance(value, (list, dict)) else value)
        return conversation_state
    
    async def handle_case_2_unclear_with_schema(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 2: request chưa rõ ràng nhưng đã detect được category với confidence khá cao, và category đó có schema
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 2] Request unclear but category '{case_data['category']}' detected")
        
        category = case_data["category"]
        
        # NEW: Validate category before proceeding
        logger.info(f"[CASE 2] Validating category: '{category}'")
        validation_result = await self.category_validator.validate_category(category)
        logger.info(f"[CASE 2] Category validation result: {validation_result}")
        
        if not validation_result["success"]:
            logger.error(f"[CASE 2] ❌ Category validation failed: {validation_result['reason']}")
            return {
                "status": "error",
                "message": f"Không thể xác định danh mục sản phẩm '{category}'. {validation_result['reason']}",
                "case": 2,
                "state": conversation_state
            }
        
        # Use validated category
        validated_category = validation_result["category"]
        category_id = validation_result["category_id"]
        
        logger.info(f"[CASE 2] ✅ Category validated: '{category}' → '{validated_category}'")
        
        conversation_state["has_category"] = True
        conversation_state["category"] = validated_category
        conversation_state["category_id"] = category_id
        conversation_state["category_validation"] = {
            "original": category,
            "normalized": validated_category,
            "status": validation_result["status"]
        }
        
        # Extract what we can from input (rule-based)
        extract_result = self.attribute_extractor.extract(
            user_input,
            validated_category,
            use_llm=False  # NO LLM
        )
        
        conversation_state["extracted"].update(extract_result["extracted"])
        
        # lấy schema và required attributes cho category đã được validate
        schema = get_schema(validated_category)
        schema_attrs = self.schema_manager.get_attributes_for_category(validated_category)
        
        # If no schema, we don't have required attributes list, so proceed to DB query
        if schema is None:
            logger.info(f"[CASE 2] No schema found for '{validated_category}', querying database...")
            db_products = self.product_repository.query_by_category_and_attributes(
                category_id=category_id,
                attributes=conversation_state["extracted"],
                limit=50
            )
            
            if db_products:
                logger.info(f"[CASE 2] ✅ Found {len(db_products)} products in DB")
                return await self._process_crawl_results(db_products, conversation_state, case=2, source="db")
            
            # No schema, no products in DB → Crawl via Crawl Service (8003)
            logger.info(f"[CASE 2] Crawling from external sources via CrawlService...")
            crawled_products = await self.crawl_service_client.crawl(
                category=validated_category,
                category_id=category_id,
                attributes=conversation_state["extracted"]
            )
            if not crawled_products:
                return {
                    "status": "no_results",
                    "message": "Không tìm thấy sản phẩm phù hợp.",
                    "case": 2,
                    "state": conversation_state
                }
            # ✅ Save crawled products to Product Service (not directly to DB)
            try:
                await self.product_service_client.save_products(crawled_products, source="tiki")
            except Exception as e:
                logger.warning(f"[CASE 2] ⚠️ Failed to save products via Product Service: {e}")
            return await self._process_crawl_results(crawled_products, conversation_state, case=2, source="crawl")
        
        required_attrs = [
            attr for attr, constraint in schema_attrs.items()
            if constraint.required
        ]
        
        missing = [
            attr for attr in required_attrs
            if attr not in conversation_state["extracted"]
            and attr not in conversation_state.get("attributes_asked", [])
        ]
        
        if not missing:
            # All required attributes provided → Query DB first
            logger.info(f"[CASE 2] All required attributes provided, querying database...")
            db_products = self.product_repository.query_by_category_and_attributes(
                category_id=category_id,
                attributes=conversation_state["extracted"],
                limit=50
            )
            
            if db_products:
                # DB HIT
                logger.info(f"[CASE 2] ✅ DB HIT! Found {len(db_products)} products")
                return await self._process_crawl_results(db_products, conversation_state, case=2, source="db")
            
            # DB MISS → Crawl via Crawl Service (8003)
            logger.info(f"[CASE 2] ❌ DB MISS! Crawling from external sources via CrawlService...")
            crawled_products = await self.crawl_service_client.crawl(
                category=validated_category,
                category_id=category_id,
                attributes=conversation_state["extracted"]
            )
            
            if not crawled_products:
                return {
                    "status": "no_results",
                    "message": "Không tìm thấy sản phẩm phù hợp.",
                    "case": 2,
                    "state": conversation_state
                }
            
            # ✅ Save crawled products to Product Service (not directly to DB)
            logger.info(f"[CASE 2] 💾 Saving crawled products via Product Service...")
            try:
                await self.product_service_client.save_products(crawled_products, source="tiki")
            except Exception as e:
                logger.warning(f"[CASE 2] ⚠️ Failed to save products via Product Service: {e}")
            
            # Return crawled products directly (already complete from CrawlService)
            return await self._process_crawl_results(crawled_products, conversation_state, case=2, source="crawl")
        
        # Ask for next missing attribute
        next_attr = missing[0]
        if "attributes_asked" not in conversation_state:
            conversation_state["attributes_asked"] = []
        conversation_state["attributes_asked"].append(next_attr)
        
        question = self.dialogue_manager.generate_question({
            "has_category": True,
            "category": validated_category,  # Use validated category
            "extracted": conversation_state["extracted"],
            "missing_required": [next_attr],
            "user_input": user_input
        })
        
        return {
            "status": "need_info",
            "question": question["question"],
            "options": question["options"],
            "attribute_name": question.get("attribute_name"),
            "case": 2,
            "state": conversation_state
        }
    
    async def handle_case_3_unclear_no_schema(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 3: Unclear request with no schema or low confidence
        Call LLM to infer category and generate attributes
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 3] Unclear request, using LLM for category inference")
        
        # Call LLM to detect category and suggest attributes
        llm_result = self._detect_category_with_llm(user_input)
        
        if not llm_result.get("suggested_categories"):
            return {
                "status": "need_info",
                "question": "Xin lỗi, tôi chưa hiểu rõ bạn muốn tìm sản phẩm gì. Bạn có thể nói rõ hơn không?",
                "case": 3,
                "state": conversation_state
            }
        
        best_match = llm_result.get("best_match")
        suggestions = llm_result.get("suggested_categories", [])
        
        # If single best match with high confidence, use it
        if best_match and len(suggestions) == 1:
            conversation_state["has_category"] = True
            conversation_state["category"] = best_match
            
            # Get suggested attributes from LLM
            attrs = suggestions[0].get("attributes", [])
            
            return {
                "status": "need_confirmation",
                "message": f"Có vẻ bạn muốn mua {best_match}, bạn muốn chọn sản phẩm theo tiêu chí nào?",
                "suggested_category": best_match,
                "suggested_attributes": attrs,
                "case": 3,
                "state": conversation_state
            }
        
        # Multiple suggestions, ask user to choose
        return {
            "status": "need_info",
            "question": "Tôi tìm thấy một số loại sản phẩm phù hợp. Bạn muốn xem loại nào?",
            "options": [{"label": s["name"], "value": s["name"], "reason": s.get("reason", "")} for s in suggestions],
            "case": 3,
            "state": conversation_state
        }
    
    async def handle_case_4_abstract_intent(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 4: Very vague/abstract intent
        LLM suggests possible product categories based on purpose
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 4] Abstract intent detected, using LLM for category suggestions")
        
        # Call LLM with purpose-oriented prompt
        import json
        prompt = f"""User expresses this need: "{user_input}"

This is an abstract or purpose-oriented request. Suggest 3-5 product categories that could fulfill this need.

Format response as JSON:
{{
  "suggestions": [
    {{"category": "category_name", "reason": "why this helps", "example_products": ["product1", "product2"]}},
    ...
  ]
}}

Be practical and culturally relevant for Vietnamese shopping."""
        
        try:
            response = call_openai(prompt, model="gpt-4o-mini", temperature=0.3, max_tokens=400)
            if not response:
                return {
                    "status": "need_info",
                    "question": "Tôi chưa hiểu rõ nhu cầu của bạn. Bạn có thể mô tả cụ thể hơn không?",
                    "case": 4,
                    "state": conversation_state
                }
            
            data = json.loads(response.strip().replace("```json", "").replace("```", ""))
            suggestions = data.get("suggestions", [])
            
            if not suggestions:
                return {
                    "status": "need_info",
                    "question": "Tôi chưa hiểu rõ nhu cầu của bạn. Bạn có thể mô tả cụ thể hơn không?",
                    "case": 4,
                    "state": conversation_state
                }
            
            return {
                "status": "need_info",
                "question": "Dựa trên nhu cầu của bạn, tôi gợi ý một số loại sản phẩm sau:",
                "options": [
                    {
                        "label": s["category"],
                        "value": s["category"],
                        "reason": s.get("reason", ""),
                        "examples": s.get("example_products", [])
                    }
                    for s in suggestions
                ],
                "case": 4,
                "state": conversation_state
            }
            
        except Exception as e:
            logger.info(f"[CASE 4] LLM error: {e}")
            return {
                "status": "error",
                "message": "Xin lỗi, tôi gặp khó khăn khi phân tích yêu cầu của bạn. Vui lòng thử lại.",
                "case": 4,
                "state": conversation_state
            }
    
    async def handle_case_5_intent_shift(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 5: Intent shift
        Detect conflict with previous intent, reset context, restart detection
        
        Flow:
        1. Save previous search in history
        2. Validate new category
        3. Extract from new category
        4. Query DB → crawl if needed
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 5] Intent shift from '{case_data['old_category']}' to '{case_data['new_category']}'")
        
        # Save history
        if conversation_state.get("category"):
            if "search_history" not in conversation_state:
                conversation_state["search_history"] = []
            conversation_state["search_history"].append({
                "category": conversation_state["category"],
                "extracted": conversation_state.get("extracted", {}).copy()
            })
        
        # Validate new category
        new_category = case_data["new_category"]
        logger.info(f"[CASE 5] Validating new category: '{new_category}'")
        validation_result = await self.category_validator.validate_category(new_category)
        
        if not validation_result["success"]:
            logger.info(f"[CASE 5] ❌ Category validation failed")
            return {
                "status": "error",
                "message": f"Không thể xác định danh mục '{new_category}'",
                "case": 5,
                "state": conversation_state
            }
        
        # Reset context with validated category
        validated_category = validation_result["category"]
        category_id = validation_result["category_id"]
        
        conversation_state = {
            "has_category": True,
            "category": validated_category,
            "category_id": category_id,
            "extracted": {},
            "missing_required": [],
            "search_history": conversation_state.get("search_history", []),
            "attributes_asked": []
        }
        
        # Restart detection for new category
        extract_result = self.attribute_extractor.extract(user_input, validated_category, use_llm=False)
        conversation_state["extracted"] = extract_result["extracted"]
        
        # Determine if we have enough to query/crawl or need to ask
        schema_attrs = self.schema_manager.get_attributes_for_category(validated_category)
        required_attrs = [attr for attr, constraint in schema_attrs.items() if constraint.required]
        missing = [attr for attr in required_attrs if attr not in conversation_state["extracted"]]
        
        if len(conversation_state["extracted"]) >= 2 or not missing:
            # Enough info → Query DB first
            logger.info(f"[CASE 5] Enough attributes, querying database...")
            db_products = self.product_repository.query_by_category_and_attributes(
                category_id=category_id,
                attributes=conversation_state["extracted"],
                limit=50
            )
            
            if db_products:
                # DB HIT
                logger.info(f"[CASE 5] ✅ Found {len(db_products)} products in DB")
                return await self._process_crawl_results(db_products, conversation_state, case=5, source="db")
            
            # DB MISS → Crawl via Crawl Service (8003)
            logger.info(f"[CASE 5] ❌ DB MISS, crawling via CrawlService...")
            crawled_products = await self.crawl_service_client.crawl(
                category=validated_category,
                category_id=category_id,
                attributes=conversation_state["extracted"]
            )
            
            if not crawled_products:
                return {
                    "status": "no_results",
                    "message": "Không tìm thấy sản phẩm phù hợp.",
                    "case": 5,
                    "state": conversation_state
                }
            
            # ✅ Save crawled products to Product Service (not directly to DB)
            logger.info(f"[CASE 5] 💾 Saving crawled products via Product Service...")
            try:
                await self.product_service_client.save_products(crawled_products, source="tiki")
            except Exception as e:
                logger.warning(f"[CASE 5] ⚠️ Failed to save products via Product Service: {e}")
            
            # Return crawled products directly (already complete from CrawlService)
            return await self._process_crawl_results(crawled_products, conversation_state, case=5, source="crawl")
        
        else:
            # Need more info
            next_attr = missing[0] if missing else None
            if next_attr:
                conversation_state["attributes_asked"].append(next_attr)
                question = self.dialogue_manager.generate_question({
                    "has_category": True,
                    "category": validated_category,
                    "extracted": conversation_state["extracted"],
                    "missing_required": [next_attr],
                    "user_input": user_input
                })
                return {
                    "status": "need_info",
                    "question": question["question"],
                    "options": question["options"],
                    "case": 5,
                    "state": conversation_state
                }
    
    async def handle_case_6_incremental_refinement(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 6: Incremental refinement
        Merge new attributes into existing context, avoid redundant questions
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 6] Incremental refinement in category '{conversation_state['category']}'")
        
        category = conversation_state["category"]
        
        # Extract new attributes
        new_attrs = self.attribute_extractor.extract(user_input, category, use_llm=False)
        
        if case_data["intent_type"] == "switch_attribute":
            # Replace conflicting attributes
            for attr, value in new_attrs["extracted"].items():
                if attr in conversation_state["extracted"]:
                    logger.info(f"[CASE 6] Replacing {attr}: '{conversation_state['extracted'][attr]}' → '{value}'")
                conversation_state["extracted"][attr] = value
        else:
            # Merge (refine) - don't overwrite existing
            for attr, value in new_attrs["extracted"].items():
                if attr not in conversation_state["extracted"]:
                    conversation_state["extracted"][attr] = value
                    logger.info(f"[CASE 6] Adding {attr}: '{value}'")
        
        # Use smart crawl with caching
        # Track cache state before crawl
        initial_cache_hits = conversation_state.get("cache_hits", 0)
        initial_cache_misses = conversation_state.get("cache_misses", 0)
        
        products = await self._smart_crawl(category, conversation_state["extracted"], conversation_state)
        
        # Determine if products came from DB cache or crawl
        db_hit = conversation_state.get("cache_hits", 0) > initial_cache_hits
        source = "db" if db_hit else "crawl"
        
        logger.info(f"[CASE 6] Source: {source} (db_hit={db_hit}, cache_hits={conversation_state.get('cache_hits')})")
        
        return await self._process_crawl_results(products, conversation_state, case=6, source=source)
    
    async def handle_case_7_comparison_advisory(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 7: Comparison/advisory request
        No immediate crawl, answer with LLM, then ask for purchase confirmation
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        logger.info(f"[CASE 7] Comparison/advisory request detected")
        
        # Use LLM to provide comparison or advice
        import json
        prompt = f"""User asks: "{user_input}"

This is a comparison or advisory question. Provide a helpful, brief answer (2-3 sentences).
Then ask if they want to see products to purchase.

Format response as JSON:
{{
  "answer": "your answer here",
  "follow_up_question": "do you want to see products?"
}}

Be concise and helpful."""
        
        try:
            response = call_openai(prompt, model="gpt-4o-mini", temperature=0.5, max_tokens=200)
            if not response:
                return {
                    "status": "error",
                    "answer": "Tôi xin lỗi, tôi không thể trả lời câu hỏi của bạn lúc này.",
                    "case": 3,
                    "state": conversation_state
                }
            
            data = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            return {
                "status": "advisory",
                "answer": data.get("answer", ""),
                "follow_up_question": data.get("follow_up_question", "Bạn muốn xem sản phẩm nào để mua không?"),
                "case": 7,
                "state": conversation_state
            }
            
        except Exception as e:
            logger.info(f"[CASE 7] LLM error: {e}")
            return {
                "status": "advisory",
                "answer": "Đây là câu hỏi hay. Để tư vấn tốt hơn, tôi cần biết bạn đang quan tâm đến sản phẩm nào cụ thể.",
                "follow_up_question": "Bạn muốn xem sản phẩm nào để mua không?",
                "case": 7,
                "state": conversation_state
            }
    
    async def handle_case_8_dynamic_category_creation(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 8: NEW category not in system
        
        Flow:
        1. LLM creates schema for new category (extract attributes)
        2. Crawl from external sources using new category name
        3. Create category in database
        4. Save products with new schema
        
        Example: User says "bột giặt" → System creates "bột giặt" category with schema
        """
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        new_category = case_data.get("new_category")
        intent_desc = case_data.get("intent", "")
        
        logger.info(f"[CASE 8] Creating new dynamic category: '{new_category}'")
        logger.info(f"[CASE 8] Intent: {intent_desc}")
        
        # ===== STEP 1: LLM creates schema for new category =====
        logger.info(f"[CASE 8] Using LLM to create schema for category '{new_category}'")
        
        import json
        schema_prompt = f"""Create a database schema for a new product category.

Category: "{new_category}"
User intent: "{intent_desc}"

Generate JSON with:
1. category_name: normalized category name
2. attributes: list of important filtering attributes (5-8)
3. keywords: Vietnamese keywords for searching
4. suggested_brands: popular brands in this category (if any)

Format:
{{
  "category_name": "normalized name",
  "display_name": "display name (Vietnamese)",
  "attributes": [
    {{"name": "attr1", "type": "text|select|range", "importance": "high|medium|low"}},
    ...
  ],
  "keywords": ["keyword1", "keyword2", ...],
  "suggested_brands": ["brand1", "brand2", ...]
}}"""
        
        try:
            schema_response = call_openai(
                schema_prompt, 
                model="gpt-4o-mini", 
                temperature=0.3, 
                max_tokens=500
            )
            if not schema_response:
                logger.warning(f"[_add_category] OpenAI returned None for schema")
                return False
            
            schema_data = json.loads(schema_response.strip().replace("```json", "").replace("```", ""))
            
            category_name = schema_data.get("category_name", new_category)
            display_name = schema_data.get("display_name", new_category)
            attributes = schema_data.get("attributes", [])
            keywords = schema_data.get("keywords", [new_category])
            
            logger.info(f"[CASE 8] ✅ Schema created: {category_name}")
            logger.info(f"[CASE 8] Attributes: {[a['name'] for a in attributes]}")
            
        except Exception as e:
            logger.error(f"[CASE 8] ❌ Failed to create schema: {e}")
            return {
                "status": "error",
                "message": f"Không thể tạo schema cho danh mục '{new_category}'. Vui lòng thử lại.",
                "case": 8,
                "state": conversation_state
            }
        
        # ===== STEP 2: Register new category in schema manager =====
        try:
            # Register category with attributes
            self.schema_manager.register_new_category(
                category_name=category_name,
                display_name=display_name,
                attributes=attributes,
                keywords=keywords
            )
            logger.info(f"[CASE 8] ✅ Registered new category in schema manager")
        except Exception as e:
            logger.error(f"[CASE 8] ⚠️  Warning: Failed to register in schema manager: {e}")
            # Don't fail - we can still crawl without schema registration
        
        # ===== STEP 3: Crawl from external sources =====
        logger.info(f"[CASE 8] 🔍 Crawling for products in category '{category_name}' via CrawlService...")
        
        try:
            # Crawl using the new category name via Crawl Service (8003)
            # Note: category_id will be created in STEP 4, so use placeholder for now
            crawled_products = await self.crawl_service_client.crawl(
                category=category_name,
                category_id=0,  # Will be assigned after category creation
                attributes={}
            )
            
            if not crawled_products:
                logger.warning(f"[CASE 8] No products found when crawling '{category_name}'")
                return {
                    "status": "no_results",
                    "message": f"Không tìm thấy sản phẩm trong danh mục '{display_name}'. Vui lòng thử lại sau.",
                    "case": 8,
                    "state": conversation_state
                }
            
            logger.info(f"[CASE 8] ✅ Crawled {len(crawled_products)} products")
            
        except Exception as e:
            logger.error(f"[CASE 8] ❌ Crawl failed: {e}")
            return {
                "status": "error",
                "message": "Lỗi khi tìm kiếm sản phẩm. Vui lòng thử lại.",
                "case": 8,
                "state": conversation_state
            }
        
        # ===== STEP 4: Save to database with new category =====
        try:
            # Create category record in DB
            category_id = self.product_repository.create_category(
                category_name=category_name,
                display_name=display_name,
                schema={"attributes": attributes}
            )
            logger.info(f"[CASE 8] ✅ Created category in DB: id={category_id}")
            
            # Save crawled products to Product Service
            try:
                await self.product_service_client.save_products(crawled_products, source="tiki")
                logger.info(f"[CASE 8] ✅ Saved {len(crawled_products)} products via Product Service")
            except Exception as e:
                logger.warning(f"[CASE 8] ⚠️ Failed to save products via Product Service: {e}")
            
        except Exception as e:
            logger.error(f"[CASE 8] ⚠️  Warning: Failed to save to DB: {e}")
            category_id = 0
            # Don't fail - we can still return results even if DB save failed
        
        # ===== STEP 5: Update conversation state =====
        conversation_state["has_category"] = True
        conversation_state["category"] = category_name
        conversation_state["category_id"] = category_id if category_id else None
        conversation_state["extracted"] = {}  # No attributes extracted yet
        
        # Return crawled products directly (already complete from CrawlService)
        return await self._process_crawl_results(crawled_products, conversation_state, case=8, source="crawl")
    
    async def _process_crawl_results(
        self,
        products: List[Dict[str, Any]],
        conversation_state: Dict[str, Any],
        case: int,
        source: str = "crawl"  # NEW: Track source (db, crawl)
    ) -> Dict[str, Any]:
        """
        Helper to process crawled/DB products and return formatted results
        
        Args:
            products: List of products
            conversation_state: Current conversation state
            case: Case number (1-7)
            source: Where products came from ("db" or "crawl")
        """
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": case,
                "state": conversation_state,
                "source": source
            }
        
        products = [self._normalize_product(p) for p in products]
        
        # 🎯 CRITICAL FIX: Skip matcher for DB products - they're already validated by category_id
        # Only match crawled products (they need validation)
        if source == "db":
            # DB products are pre-filtered by category_id → no need to re-validate
            matched_products = products
            logger.info(f"[_process_crawl_results] ✅ Using {len(products)} DB products (no re-validation needed)")
        else:
            # Crawled products need to be matched/validated
            matched_products = self.product_matcher.match_products(
                products,
                conversation_state["category"],
                conversation_state["extracted"]
            )
        
        if not matched_products:
            return {
                "status": "no_results",
                "message": "Không có sản phẩm nào phù hợp với yêu cầu.",
                "case": case,
                "state": conversation_state,
                "source": source
            }
        
        # Update cache
        conversation_state["cached_products"] = products
        conversation_state["cached_filters"] = self._extract_filters_from_products(products)
        conversation_state["last_crawl_params"] = {
            "category": conversation_state["category"],
            "brand": conversation_state["extracted"].get("brand")
        }
        
        ranked_products = self.product_ranker.rank(
            matched_products,
            conversation_state["extracted"],
            use_llm_explain=False  # Tắt LLM explanation để giảm API calls
        )
        
        comparison = self.product_ranker.generate_comparison(ranked_products, top_n=3)
        
        return {
            "status": "results",
            "products": ranked_products[:20],
            "comparison": comparison,
            "total_found": len(matched_products),
            "case": case,
            "state": conversation_state,
            "source": source  # Track whether from DB or crawl
        }
    
    def _extract_category_from_input(self, user_input: str) -> Dict[str, Any]:
        """
        Semantic extraction: LLM detects product type + attributes from user input
        NO hardcoded category matching!
        
        Returns:
            {
                "product_type": "nước ngọt cocacola",  # What user wants (semantic)
                "category": "nước ngọt",  # Best matching category
                "attributes": {"brand": "cocacola"},  # Extracted attributes
                "method": "llm_semantic",
                "confidence": 0.9
            }
        """
        import json
        from .dynamic_schema import UNIVERSAL_KEYWORDS
        
        prompt = f"""Analyze user's request and extract details.

User says: "{user_input}"

Extract in JSON format:
{{
  "product_type": "what product user wants (semantic description)",
  "inferred_category": "what category this likely is (e.g., 'nước ngọt', 'giày', 'áo')",
  "attributes": {{ ... extracted attributes ... }},
  "key_mention": "most important keyword they mentioned"
}}

Example input: "tôi muốn mua nước ngọt cocacola"
Example output:
{{
  "product_type": "cocacola soft drink",
  "inferred_category": "nước ngọt",
  "attributes": {{"brand": "cocacola", "type": "soft drink"}},
  "key_mention": "cocacola"
}}

Return ONLY valid JSON, no markdown."""
        
        try:
            response = call_openai(
                prompt,
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=200
            )
            
            # Parse JSON response
            if not response:
                logger.warning("[_extract_by_llm] OpenAI returned None")
                return {}
            
            data = json.loads(response.strip())
            inferred_cat = data.get("inferred_category", "").lower().strip()
            
            logger.info(f"DEBUG: LLM semantic analysis: {data}")
            
            # Match against UNIVERSAL_KEYWORDS - NOT hardcoded list!
            # LLM said "nước ngọt" → find "nước ngọt" in UNIVERSAL_KEYWORDS
            matched_category = None
            for cat_key in UNIVERSAL_KEYWORDS.keys():
                if inferred_cat == cat_key.lower():
                    matched_category = cat_key
                    break
            
            if not matched_category:
                # Try fuzzy match: if inferred_cat appears in any category name
                for cat_key in UNIVERSAL_KEYWORDS.keys():
                    if cat_key.lower() in inferred_cat or inferred_cat in cat_key.lower():
                        matched_category = cat_key
                        break
            
            return {
                "product_type": data.get("product_type", ""),
                "category": matched_category,
                "attributes": data.get("attributes", {}),
                "inferred_category": inferred_cat,
                "method": "llm_semantic",
                "confidence": 0.90
            }
        except json.JSONDecodeError as e:
            logger.info(f"DEBUG: JSON parse error: {e}, response: {response[:100]}")
            return {
                "product_type": user_input,
                "category": None,
                "attributes": {},
                "method": "llm_semantic",
                "confidence": 0.0
            }
        except Exception as e:
            logger.info(f"DEBUG: LLM semantic extraction error: {e}")
            return {
                "product_type": user_input,
                "category": None,
                "attributes": {},
                "method": "llm_semantic",
                "confidence": 0.0
            }
    
    def _detect_category_with_llm(self, user_input: str) -> Dict[str, Any]:
        """
        Semantic category detection using LLM
        LLM suggests 3-5 categories + attributes for filtering
        Results are cached to avoid repeated calls
        
        Returns:
            {
                "suggested_categories": [
                    {"name": str, "reason": str, "attributes": [str, ...]},
                    ...
                ],
                "best_match": str,
                "confidence": float,
                "method": "llm"
            }
        """
        # Check cache first
        cache_key = user_input.lower().strip()
        if cache_key in self.llm_suggestion_cache:
            logger.info(f"DEBUG: Using cached LLM suggestions for '{cache_key[:30]}...'")
            return self.llm_suggestion_cache[cache_key]
        
        categories_text = ", ".join(AVAILABLE_CATEGORIES)
        
        prompt = f"""User wants: "{user_input}"

Available categories: {categories_text}

Suggest 3-5 best matching categories with reasons and key attributes for filtering.

Format your response as JSON:
{{
  "suggestions": [
    {{"name": "category_name", "reason": "why this matches", "attributes": ["attr1", "attr2", ...]}},
    ...
  ],
  "best_match": "best_category"
}}

Be concise. Attributes should be practical filtering criteria."""
        
        try:
            response = call_openai(
                prompt,
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=300
            )
            
            if not response:
                logger.warning("[_suggest_categories_llm] OpenAI returned None")
                return []
            
            logger.info(f"DEBUG: LLM response:\n{response}")
            
            # Parse JSON response - handle markdown code blocks
            import json
            import re
            
            # Strip markdown code block if present
            json_text = response.strip()
            if json_text.startswith("```"):
                json_text = re.sub(r'^```(?:json)?\n', '', json_text)
                json_text = re.sub(r'\n```$', '', json_text)
            
            data = json.loads(json_text)
            
            best = data.get("best_match")
            suggestions = data.get("suggestions", [])
            
            # Validate that best_match is in available categories
            if best and best not in AVAILABLE_CATEGORIES:
                # Try to find closest match
                for cat in AVAILABLE_CATEGORIES:
                    if cat.lower() in best.lower() or best.lower() in cat.lower():
                        best = cat
                        break
            
            result = {
                "suggested_categories": suggestions,
                "best_match": best if best in AVAILABLE_CATEGORIES else (suggestions[0]["name"] if suggestions else None),
                "confidence": 0.85,
                "method": "llm"
            }
            
            # Cache the result in memory
            self.llm_suggestion_cache[cache_key] = result
            logger.info(f"DEBUG: Cached suggestions for reuse")
            
            # 💾 Save suggestions to persistent storage (DB/file)
            if suggestions:
                try:
                    saved_ids = self.category_cache.save_multiple(suggestions)
                    logger.info(f"💾 Saved {len(saved_ids)} categories to persistent cache")
                except Exception as e:
                    logger.info(f"⚠️  Failed to save to persistent cache: {e}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.info(f"DEBUG: LLM JSON parse error: {e}")
            return {"suggested_categories": [], "best_match": None, "confidence": 0.0, "method": "llm"}
        except Exception as e:
            logger.info(f"DEBUG: LLM detection error: {e}")
            return {"suggested_categories": [], "best_match": None, "confidence": 0.0, "method": "llm"}
        
    
    async def process_query(
        self,
        user_input: str,
        conversation_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        # Initialize state
        if conversation_state is None:
            conversation_state = {
                "has_category": False,
                "category": None,
                "extracted": {},
                "missing_required": [],
                "search_history": [],
                "attributes_asked": [],
                "cached_products": None,
                "cached_filters": None,
                "last_crawl_params": None,
                "cache_hits": 0,
                "cache_misses": 0
            }
        
        # STEP 0: ✅ ANALYZE INTENT - Enrich conversation_state with intent info BEFORE classification
        logger.info(f"\n[Orchestrator] 📊 Analyzing user intent from: '{user_input}'")
        intent_result = self.intent_mapper.map_intent(user_input)
        logger.info(f"[Orchestrator] ✅ Intent detected:")
        logger.info(f"  - Intent: {intent_result['intent']}")
        logger.info(f"  - Intent Type: {intent_result['intent_type']}")
        logger.info(f"  - Categories: {intent_result['categories']}")
        logger.info(f"  - Product Name: {intent_result.get('product_name', 'N/A')}")
        logger.info(f"  - Confidence: {intent_result['confidence']:.2f}")
        logger.info(f"  - Method: {intent_result['method']}")
        
        # Store intent analysis in conversation_state (for classify_request_case to use)
        # IMPORTANT: Always update if detected_intent is None (when category was reset) OR user input changed
        last_input = conversation_state.get("last_user_input", "").strip().lower()
        current_input = user_input.strip().lower()
        input_changed = last_input != current_input and last_input != ""  # Only if both non-empty
        
        if not conversation_state.get("detected_intent") or not conversation_state.get("has_category") or input_changed:
            if input_changed:
                logger.info(f"[Orchestrator] 🔄 User input changed ('{last_input}' → '{current_input}') → Re-analyzing intent")
            elif not conversation_state.get("detected_intent"):
                logger.info(f"[Orchestrator] 🔄 Detected intent was None → Updating with new analysis")
            conversation_state["detected_intent"] = intent_result
            conversation_state["last_user_input"] = user_input  # Track for intent shift detection
        else:
            logger.info(f"[Orchestrator] ℹ️  Using cached detected_intent (has_category=True)")
        
        # STEP 1: Classify request into one of 7 cases
        case_info = self.classify_request_case(user_input, conversation_state)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"CASE {case_info['case']}: {case_info['case_name']}")
        logger.info(f"Reason: {case_info['reason']}")
        logger.info(f"{'='*80}\n")
        
        # STEP 2: Route to appropriate handler
        handlers = {
            1: self.handle_case_1_clear_request,
            2: self.handle_case_2_unclear_with_schema,
            3: self.handle_case_3_unclear_no_schema,
            4: self.handle_case_4_abstract_intent,
            5: self.handle_case_5_intent_shift,
            6: self.handle_case_6_incremental_refinement,
            7: self.handle_case_7_comparison_advisory,
            8: self.handle_case_8_dynamic_category_creation  # ← NEW
        }
        
        handler = handlers.get(case_info["case"])
        if not handler:
            return {
                "status": "error",
                "message": f"Internal error: Unknown case {case_info['case']}",
                "state": conversation_state
            }
        
        # STEP 3: Execute handler
        result = await handler(user_input, case_info["data"], conversation_state)
        
        # STEP 4: Add routing metadata to result
        result["routing_info"] = {
            "case": case_info["case"],
            "case_name": case_info["case_name"],
            "reason": case_info["reason"]
        }
        
        # STEP 5: Save current user input for next call (to avoid false intent_shift detection)
        conversation_state["last_user_input"] = user_input
        
        return result
    
    # ====================================================================================
    # LEGACY COMPATIBILITY LAYER (for old code that might still reference these)
    # ====================================================================================
    
    async def _smart_crawl(
        self,
        category: str,
        attributes: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Smart crawl: Query DB first → in-memory filter → crawl if needed
        
        Flow:
        1. Query database with category + attributes
        2. If found → return (DB HIT, fast!)
        3. If not found → crawl from external sources
        4. Save crawled results to DB for future queries
        
        Returns:
            List of products (from DB or crawl)
        """
        
        category_id = conversation_state.get("category_id")
        
        # Step 1: Try DB first (fast!)
        if category_id:
            logger.info(f"[SMART_CRAWL] 🔍 Querying database (category_id={category_id})...")
            db_products = self.product_repository.query_by_category_and_attributes(
                category_id=category_id,
                attributes=attributes,
                limit=100
            )
            
            if db_products:
                logger.info(f"[SMART_CRAWL] ✅ DB HIT! Found {len(db_products)} products, filtering in-memory...")
                conversation_state["cache_hits"] = conversation_state.get("cache_hits", 0) + 1
                
                # Filter in-memory for additional refinement (Lazada style)
                filtered = self._filter_products_in_memory(db_products, attributes)
                logger.info(f"[SMART_CRAWL] After filtering: {len(filtered)} products")
                return filtered
        
        # Step 2: DB miss → crawl from external sources via Crawl Service (8003)
        logger.info(f"[SMART_CRAWL] ❌ DB MISS! Crawling from external sources via CrawlService...")
        conversation_state["cache_misses"] = conversation_state.get("cache_misses", 0) + 1
        
        crawled_products = await self.crawl_service_client.crawl(
            category=category,
            category_id=category_id if category_id else 0,
            attributes=attributes
        )
        
        if not crawled_products:
            return []
        
        # Step 3: Save crawled results to Product Service for future queries
        if category_id and crawled_products:
            logger.info(f"[SMART_CRAWL] 💾 Saving {len(crawled_products)} products via Product Service...")
            try:
                await self.product_service_client.save_products(crawled_products, source="tiki")
            except Exception as e:
                logger.warning(f"[SMART_CRAWL] ⚠️ Failed to save products via Product Service: {e}")
        
        return crawled_products
    
    def _filter_products_in_memory(
        self,
        products: List[Dict[str, Any]],
        attributes: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter products in-memory without making new crawl requests.
        Much faster than re-crawling (0.05s vs 5s).
        """
        filtered = products
        
        # Filter by price range
        if "gia" in attributes and isinstance(attributes["gia"], dict):
            min_price = attributes["gia"].get("min", 0)
            max_price = attributes["gia"].get("max", float('inf'))
            filtered = [
                p for p in filtered 
                if min_price <= p.get("price", 0) <= max_price
            ]
            logger.info(f"  💰 Filtered by price: {min_price}-{max_price} → {len(filtered)} products")
        
        # Filter by color
        if "mau" in attributes:
            color = str(attributes["mau"]).lower().strip()
            filtered = [
                p for p in filtered 
                if color in str(p.get("mau", "")).lower()
            ]
            logger.info(f"  🎨 Filtered by color: {color} → {len(filtered)} products")
        
        # Filter by size
        if "size" in attributes:
            size = str(attributes["size"]).strip()
            filtered = [
                p for p in filtered 
                if p.get("size") == size
            ]
            logger.info(f"  📏 Filtered by size: {size} → {len(filtered)} products")
        
        # Filter by type
        if "loai" in attributes:
            loai = attributes["loai"].lower().strip()
            filtered = [
                p for p in filtered 
                if loai in str(p.get("loai", "")).lower()
            ]
            logger.info(f"  🏷️ Filtered by type: {loai} → {len(filtered)} products")
        
        return filtered
    
    def _extract_filters_from_products(
        self,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract available filters from products (like Lazada/Shopee do).
        Used to display filter options in UI.
        """
        filters = {
            "colors": set(),
            "sizes": set(),
            "price_range": {"min": float('inf'), "max": 0},
            "brands": set(),
            "types": set()
        }
        
        for product in products:
            # Colors
            if "mau" in product:
                filters["colors"].add(str(product["mau"]).strip())
            
            # Sizes
            if "size" in product:
                filters["sizes"].add(str(product["size"]).strip())
            
            # Price range
            if "price" in product:
                price = product["price"]
                if isinstance(price, (int, float)):
                    filters["price_range"]["min"] = min(filters["price_range"]["min"], price)
                    filters["price_range"]["max"] = max(filters["price_range"]["max"], price)
            
            # Brands
            if "brand" in product:
                filters["brands"].add(str(product["brand"]).strip())
            
            # Types
            if "loai" in product:
                filters["types"].add(str(product["loai"]).strip())
        
        # Convert sets to sorted lists
        return {
            "colors": sorted(list(filters["colors"])),
            "sizes": sorted(list(filters["sizes"])),
            "price_range": filters["price_range"],
            "brands": sorted(list(filters["brands"])),
            "types": sorted(list(filters["types"]))
        }
    
    def _normalize_product(self, product: dict) -> dict:
        if "title" in product and "name" not in product:
            product["name"] = product["title"]
        return product
    
    def update_state(self, conversation_state: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update conversation state based on user response
        
        response = {
            "question_type": "category" | "attribute",
            "value": str,
            "attribute_name": str (optional, for attribute questions)
        }
        """
        if response["question_type"] == "category":
            # User chọn category
            conversation_state["has_category"] = True
            conversation_state["category"] = response["value"]
            conversation_state["extracted"] = {}
            conversation_state["missing_required"] = []
        
        elif response["question_type"] == "attribute":
            # User cung cấp attribute value
            if response.get("attribute_name"):
                conversation_state["extracted"][response["attribute_name"]] = response["value"]
        
        return conversation_state
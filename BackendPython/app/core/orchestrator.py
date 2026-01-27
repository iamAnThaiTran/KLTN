# app/core/orchestrator.py

import re
from typing import Dict, Any, List
from .extractor import AttributeExtractor
from .dialogue import DialogueManager
from .matcher import ProductMatcher
from .ranker import ProductRanker
from app.crawler.multi_crawler import MultiCrawler
from .schema import get_schema
from .intent import EnhancedIntentDetector
from .intent_mapper import IntentMapper
from .dynamic_schema import DynamicSchemaManager, AVAILABLE_CATEGORIES
from .llm_utils import call_openai

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
        self.crawler = MultiCrawler()
        
        # Cache management (Lazada-style)
        self.enable_cache = True  # Set to False to disable caching
        
        # LLM suggestion cache - avoid repeated LLM calls
        self.llm_suggestion_cache = {}  # key: user_input hash, value: suggestions
        
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
        Central dispatcher: Classifies user request into one of 7 cases
        
        Returns:
            {
                "case": int (1-7),
                "case_name": str,
                "reason": str,
                "data": Dict[str, Any]  # Case-specific data
            }
        """
        user_lower = user_input.lower().strip()
        
        # CASE 7: Comparison / advisory request (NO immediate crawl)
        # Check this first as it's most specific
        if self._is_comparison_request(user_input):
            return {
                "case": 7,
                "case_name": "comparison_advisory",
                "reason": "User asks for comparison or advice, not immediate purchase",
                "data": {
                    "needs_llm_response": True,
                    "should_crawl": False
                }
            }
        
        # CASE 5: Intent shift (context reset)
        if conversation_state.get("has_category"):
            intent_change = self.intent_detector.detect_intent_change(user_input, conversation_state)
            if intent_change["intent_type"] == "switch_category":
                return {
                    "case": 5,
                    "case_name": "intent_shift",
                    "reason": f"User switched from '{conversation_state.get('category')}' to '{intent_change.get('new_category')}'",
                    "data": {
                        "old_category": conversation_state.get("category"),
                        "new_category": intent_change.get("new_category"),
                        "should_reset": True
                    }
                }
        
        # CASE 6: Incremental refinement (context accumulation)
        if conversation_state.get("has_category") and conversation_state.get("extracted"):
            intent_change = self.intent_detector.detect_intent_change(user_input, conversation_state)
            if intent_change["intent_type"] in ["refine", "switch_attribute"]:
                return {
                    "case": 6,
                    "case_name": "incremental_refinement",
                    "reason": "User adding or modifying attributes in same category",
                    "data": {
                        "intent_type": intent_change["intent_type"],
                        "should_merge": True
                    }
                }
        
        # CASE 4: Very vague / abstract intent (CALL LLM)
        if self._is_abstract_intent(user_input):
            return {
                "case": 4,
                "case_name": "abstract_intent",
                "reason": "User expresses high-level need or purpose without specific product",
                "data": {
                    "needs_llm": True,
                    "suggest_categories": True
                }
            }
        
        # For remaining cases, analyze query clarity
        clarity_score = self._assess_query_clarity(user_input)
        category_result = self._quick_category_detection(user_input)
        
        # CASE 1: Clear request (NO LLM)
        if clarity_score >= 0.7 and category_result.get("confidence", 0) >= 0.7:
            return {
                "case": 1,
                "case_name": "clear_request",
                "reason": "Clear and specific request with detectable category and attributes",
                "data": {
                    "category": category_result.get("category"),
                    "confidence": clarity_score,
                    "should_use_llm": False,
                    "can_crawl_immediately": True
                }
            }
        
        # CASE 2: Unclear request but category is confidently detected (schema exists)
        if category_result.get("category") and category_result.get("confidence", 0) >= 0.5:
            # Check if schema exists
            schema = get_schema(category_result["category"])
            if schema:
                return {
                    "case": 2,
                    "case_name": "unclear_with_schema",
                    "reason": "Request missing attributes, but category detected and schema exists",
                    "data": {
                        "category": category_result["category"],
                        "confidence": category_result["confidence"],
                        "should_use_llm": False,
                        "should_ask_attributes": True
                    }
                }
        
        # CASE 3: Unclear request and schema is missing or confidence is low (CALL LLM)
        return {
            "case": 3,
            "case_name": "unclear_no_schema",
            "reason": "Request unclear and either no category detected or low confidence",
            "data": {
                "should_use_llm": True,
                "category": category_result.get("category"),
                "confidence": category_result.get("confidence", 0)
            }
        }
    
    def _is_comparison_request(self, user_input: str) -> bool:
        """Check if user is asking for comparison/advice rather than buying"""
        user_lower = user_input.lower()
        
        # Check for comparison keywords with word boundaries to avoid false positives
        # (e.g., "or" in "Force" should not match)
        comparison_patterns = [
            r'\bso sánh\b', r'\bkhác\b', r'\bhơn\b', r'\btốt hơn\b', r'\bbền hơn\b', 
            r'\brẻ hơn\b', r'\bđẹp hơn\b', r'\bvới\b', r'\bhay\b', r'\bor\b', 
            r'\bvs\b', r'\bversus\b', r'\bcompare\b', r'\bcomparison\b',
            r'\bnên chọn\b', r'\bnên mua\b', r'\bcái nào\b', r'\bloại nào\b'
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, user_lower):
                return True
        
        # Check for question patterns without purchase intent
        question_patterns = [
            r'(nên|có nên|nên không)\s+(mua|chọn|lấy)',
            r'(cái nào|loại nào|sản phẩm nào)\s+(tốt|bền|đẹp|rẻ)',
            r'(khác nhau|khác gì|giống nhau)',
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, user_lower):
                return True
        
        return False
    
    def _is_abstract_intent(self, user_input: str) -> bool:
        """Check if user expresses abstract/high-level need without specific product"""
        user_lower = user_input.lower()
        
        # Abstract intent patterns
        abstract_patterns = [
            r'mua quà.*cho',  # "mua quà cho bố"
            r'(muốn|cần)\s+(mua|tìm)\s+(thứ|cái|gì)\s+(gì|đó)',  # "muốn mua thứ gì đó..."
            r'(để|cho|phục vụ)\s+\w+',  # "để tránh thai", "cho việc..."
            r'giúp.*\b(vấn đề|việc|công việc)\b',  # "giúp vấn đề..."
        ]
        
        for pattern in abstract_patterns:
            if re.search(pattern, user_lower):
                return True
        
        return False
    
    def _assess_query_clarity(self, user_input: str) -> float:
        """
        Assess how clear and specific a query is
        Returns: clarity score 0.0 to 1.0
        """
        score = 0.0
        user_lower = user_input.lower()
        
        # Has brand mention (+0.3)
        brand_patterns = [
            r'\b(nike|adidas|puma|reebok|samsung|apple|sony|lg|dell|hp|asus|lenovo)\b',
            r'\b(cocacola|pepsi|uniqlo|zara|h&m|gucci|louis vuitton)\b'
        ]
        if any(re.search(p, user_lower) for p in brand_patterns):
            score += 0.3
        
        # Has specific model/line (+0.3)
        model_patterns = [
            r'\b(air force|pegasus|galaxy|iphone|xperia|wh-1000xm\d)\b',
            r'\b(xps|inspiron|thinkpad|macbook)\b'
        ]
        if any(re.search(p, user_lower) for p in model_patterns):
            score += 0.3
        
        # Has size/quantity/color (+0.2)
        if re.search(r'\b(size|cỡ|màu|số)\s+\d+', user_lower):
            score += 0.2
        if re.search(r'\b(đen|trắng|đỏ|xanh|black|white|red|blue)\b', user_lower):
            score += 0.1
        
        # Has price mention (+0.2)
        if re.search(r'(giá|price|đồng|triệu|nghìn|dưới|trên|từ.*đến)', user_lower):
            score += 0.2
        
        # Has specific product name format (Brand + Model + specs) (+0.2)
        # e.g., "Sony WH-1000XM5"
        if re.search(r'\b[A-Z][a-z]+\s+[A-Z0-9-]+', user_input):
            score += 0.2
        
        return min(score, 1.0)
    
    def _quick_category_detection(self, user_input: str) -> Dict[str, Any]:
        """Quick rule-based category detection without LLM"""
        # Use existing intent detector's keyword-based detection
        return self.intent_detector._detect_category(user_input)
    
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
        Direct extraction and crawling using rule-based logic
        """
        print(f"[CASE 1] Processing clear request with rule-based extraction")
        
        category = case_data["category"]
        conversation_state["has_category"] = True
        conversation_state["category"] = category
        
        # Extract attributes using rule-based extractor (NO LLM)
        extract_result = self.attribute_extractor.extract(
            user_input,
            category,
            use_llm=False  # CRITICAL: No LLM for Case 1
        )
        
        conversation_state["extracted"] = extract_result["extracted"]
        
        print(f"[CASE 1] Extracted attributes: {extract_result['extracted']}")
        print(f"[CASE 1] Triggering crawler directly...")
        
        # Directly trigger crawler
        products = await self.crawler.crawl(category, extract_result["extracted"])
        
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": 1,
                "state": conversation_state
            }
        
        # Process and return results
        return await self._process_crawl_results(products, conversation_state, case=1)
    
    async def handle_case_2_unclear_with_schema(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        CASE 2: Unclear request but category detected with schema
        Ask for missing mandatory attributes, NO LLM, NO crawl yet
        """
        print(f"[CASE 2] Request unclear but category '{case_data['category']}' detected")
        
        category = case_data["category"]
        conversation_state["has_category"] = True
        conversation_state["category"] = category
        
        # Extract what we can from input (rule-based)
        extract_result = self.attribute_extractor.extract(
            user_input,
            category,
            use_llm=False  # NO LLM
        )
        
        conversation_state["extracted"].update(extract_result["extracted"])
        
        # Load schema and identify missing required attributes
        schema = get_schema(category)
        schema_attrs = self.schema_manager.get_attributes_for_category(category)
        
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
            # All required attributes provided, proceed to crawl
            print(f"[CASE 2] All required attributes provided, proceeding to crawl")
            products = await self.crawler.crawl(category, conversation_state["extracted"])
            return await self._process_crawl_results(products, conversation_state, case=2)
        
        # Ask for next missing attribute
        next_attr = missing[0]
        if "attributes_asked" not in conversation_state:
            conversation_state["attributes_asked"] = []
        conversation_state["attributes_asked"].append(next_attr)
        
        question = self.dialogue_manager.generate_question({
            "has_category": True,
            "category": category,
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
        print(f"[CASE 3] Unclear request, using LLM for category inference")
        
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
        print(f"[CASE 4] Abstract intent detected, using LLM for category suggestions")
        
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
            print(f"[CASE 4] LLM error: {e}")
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
        """
        print(f"[CASE 5] Intent shift from '{case_data['old_category']}' to '{case_data['new_category']}'")
        
        # Save history
        if conversation_state.get("category"):
            if "search_history" not in conversation_state:
                conversation_state["search_history"] = []
            conversation_state["search_history"].append({
                "category": conversation_state["category"],
                "extracted": conversation_state["extracted"].copy()
            })
        
        # Reset context
        new_category = case_data["new_category"]
        conversation_state = {
            "has_category": True,
            "category": new_category,
            "extracted": {},
            "missing_required": [],
            "search_history": conversation_state.get("search_history", []),
            "attributes_asked": []
        }
        
        # Restart detection for new category - process as new search
        extract_result = self.attribute_extractor.extract(user_input, new_category, use_llm=False)
        conversation_state["extracted"] = extract_result["extracted"]
        
        # Determine if we have enough to crawl or need to ask
        schema_attrs = self.schema_manager.get_attributes_for_category(new_category)
        required_attrs = [attr for attr, constraint in schema_attrs.items() if constraint.required]
        missing = [attr for attr in required_attrs if attr not in conversation_state["extracted"]]
        
        if len(conversation_state["extracted"]) >= 2 or not missing:
            # Enough info, crawl
            products = await self.crawler.crawl(new_category, conversation_state["extracted"])
            return await self._process_crawl_results(products, conversation_state, case=5)
        else:
            # Need more info
            next_attr = missing[0] if missing else None
            if next_attr:
                conversation_state["attributes_asked"].append(next_attr)
                question = self.dialogue_manager.generate_question({
                    "has_category": True,
                    "category": new_category,
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
        print(f"[CASE 6] Incremental refinement in category '{conversation_state['category']}'")
        
        category = conversation_state["category"]
        
        # Extract new attributes
        new_attrs = self.attribute_extractor.extract(user_input, category, use_llm=False)
        
        if case_data["intent_type"] == "switch_attribute":
            # Replace conflicting attributes
            for attr, value in new_attrs["extracted"].items():
                if attr in conversation_state["extracted"]:
                    print(f"[CASE 6] Replacing {attr}: '{conversation_state['extracted'][attr]}' → '{value}'")
                conversation_state["extracted"][attr] = value
        else:
            # Merge (refine) - don't overwrite existing
            for attr, value in new_attrs["extracted"].items():
                if attr not in conversation_state["extracted"]:
                    conversation_state["extracted"][attr] = value
                    print(f"[CASE 6] Adding {attr}: '{value}'")
        
        # Use smart crawl with caching
        products = await self._smart_crawl(category, conversation_state["extracted"], conversation_state)
        
        return await self._process_crawl_results(products, conversation_state, case=6)
    
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
        print(f"[CASE 7] Comparison/advisory request detected")
        
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
            data = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            return {
                "status": "advisory",
                "answer": data.get("answer", ""),
                "follow_up_question": data.get("follow_up_question", "Bạn muốn xem sản phẩm nào để mua không?"),
                "case": 7,
                "state": conversation_state
            }
            
        except Exception as e:
            print(f"[CASE 7] LLM error: {e}")
            return {
                "status": "advisory",
                "answer": "Đây là câu hỏi hay. Để tư vấn tốt hơn, tôi cần biết bạn đang quan tâm đến sản phẩm nào cụ thể.",
                "follow_up_question": "Bạn muốn xem sản phẩm nào để mua không?",
                "case": 7,
                "state": conversation_state
            }
    
    async def _process_crawl_results(
        self,
        products: List[Dict[str, Any]],
        conversation_state: Dict[str, Any],
        case: int
    ) -> Dict[str, Any]:
        """Helper to process crawled products and return formatted results"""
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": case,
                "state": conversation_state
            }
        
        products = [self._normalize_product(p) for p in products]
        
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
                "state": conversation_state
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
            use_llm_explain=True
        )
        
        comparison = self.product_ranker.generate_comparison(ranked_products, top_n=3)
        
        return {
            "status": "results",
            "products": ranked_products[:20],
            "comparison": comparison,
            "total_found": len(matched_products),
            "case": case,
            "state": conversation_state
        }
    
        
        # Comparison keywords for Case 7 detection
        self.comparison_keywords = [
            "so sánh", "khác", "hơn", "tốt hơn", "bền hơn", "rẻ hơn", "đẹp hơn",
            "với", "hay", "or", "vs", "versus", "compare", "comparison",
            "nên chọn", "nên mua", "cái nào", "loại nào"
        ]
    
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
            data = json.loads(response.strip())
            inferred_cat = data.get("inferred_category", "").lower().strip()
            
            print(f"DEBUG: LLM semantic analysis: {data}")
            
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
            print(f"DEBUG: JSON parse error: {e}, response: {response[:100]}")
            return {
                "product_type": user_input,
                "category": None,
                "attributes": {},
                "method": "llm_semantic",
                "confidence": 0.0
            }
        except Exception as e:
            print(f"DEBUG: LLM semantic extraction error: {e}")
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
            print(f"DEBUG: Using cached LLM suggestions for '{cache_key[:30]}...'")
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
            
            print(f"DEBUG: LLM response:\n{response}")
            
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
            
            # Cache the result
            self.llm_suggestion_cache[cache_key] = result
            print(f"DEBUG: Cached suggestions for reuse")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"DEBUG: LLM JSON parse error: {e}")
            return {"suggested_categories": [], "best_match": None, "confidence": 0.0, "method": "llm"}
        except Exception as e:
            print(f"DEBUG: LLM detection error: {e}")
            return {"suggested_categories": [], "best_match": None, "confidence": 0.0, "method": "llm"}
            return {
                "category": None,
                "confidence": 0.0,
                "method": "llm",
                "error": str(e)
            }
        
    
    async def process_query(
        self,
        user_input: str,
        conversation_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - 7-case intelligent routing system
        
        This replaces the old complex process_query with a clean dispatcher pattern.
        Each case has its own dedicated handler for clarity and maintainability.
        """
        print(f"=" * 80)
        print(f"Orchestrator: Processing query: {user_input}")
        print(f"=" * 80)
        
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
        
        # STEP 1: Classify request into one of 7 cases
        case_info = self.classify_request_case(user_input, conversation_state)
        
        print(f"\n{'='*80}")
        print(f"CASE {case_info['case']}: {case_info['case_name']}")
        print(f"Reason: {case_info['reason']}")
        print(f"{'='*80}\n")
        
        # STEP 2: Route to appropriate handler
        handlers = {
            1: self.handle_case_1_clear_request,
            2: self.handle_case_2_unclear_with_schema,
            3: self.handle_case_3_unclear_no_schema,
            4: self.handle_case_4_abstract_intent,
            5: self.handle_case_5_intent_shift,
            6: self.handle_case_6_incremental_refinement,
            7: self.handle_case_7_comparison_advisory
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
        Smart crawl: Use cached products if possible, crawl again if needed.
        Implements Lazada-style in-memory filtering.
        
        Returns:
            List of products (from cache or fresh crawl)
        """
        
        if not self.enable_cache:
            print(f"🔍 Cache disabled, crawling fresh...")
            products = await self.crawler.crawl(category, attributes)
            conversation_state["cache_misses"] = conversation_state.get("cache_misses", 0) + 1
            return products
        
        # Check if we have cached products
        if conversation_state.get("cached_products"):
            last_params = conversation_state.get("last_crawl_params", {})
            
            # If category or brand changed → crawl again
            if (last_params.get("category") != category or 
                last_params.get("brand") != attributes.get("brand")):
                print(f"⚠️ Cache miss: category/brand changed, crawling...")
                products = await self.crawler.crawl(category, attributes)
                conversation_state["cache_misses"] = conversation_state.get("cache_misses", 0) + 1
                return products
            
            # Same category & brand → use cached products
            print(f"✅ Cache HIT! Using {len(conversation_state['cached_products'])} cached products")
            conversation_state["cache_hits"] = conversation_state.get("cache_hits", 0) + 1
            
            # Filter in-memory for better performance (Lazada style)
            products = self._filter_products_in_memory(
                conversation_state["cached_products"],
                attributes
            )
            return products
        
        # First time → crawl and cache
        print(f"🔍 First crawl for {category}, caching results...")
        products = await self.crawler.crawl(category, attributes)
        conversation_state["cache_misses"] = conversation_state.get("cache_misses", 0) + 1
        return products
    
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
            print(f"  💰 Filtered by price: {min_price}-{max_price} → {len(filtered)} products")
        
        # Filter by color
        if "mau" in attributes:
            color = str(attributes["mau"]).lower().strip()
            filtered = [
                p for p in filtered 
                if color in str(p.get("mau", "")).lower()
            ]
            print(f"  🎨 Filtered by color: {color} → {len(filtered)} products")
        
        # Filter by size
        if "size" in attributes:
            size = str(attributes["size"]).strip()
            filtered = [
                p for p in filtered 
                if p.get("size") == size
            ]
            print(f"  📏 Filtered by size: {size} → {len(filtered)} products")
        
        # Filter by type
        if "loai" in attributes:
            loai = attributes["loai"].lower().strip()
            filtered = [
                p for p in filtered 
                if loai in str(p.get("loai", "")).lower()
            ]
            print(f"  🏷️ Filtered by type: {loai} → {len(filtered)} products")
        
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
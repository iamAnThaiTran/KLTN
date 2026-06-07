# app/core/orchestrator.py

from asyncio.log import logger
import re
from typing import Dict, Any, List
from unittest import result
from .extractor import AttributeExtractor
from .dialogue import DialogueManager
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

class RecommendationOrchestrator:
    
    def __init__(self):
        
        self.intent_detector = EnhancedIntentDetector()
        self.intent_mapper = IntentMapper()
        self.attribute_extractor = AttributeExtractor()
        self.schema_manager = DynamicSchemaManager()  # Add dynamic schema manager
        self.dialogue_manager = DialogueManager()
        self.product_ranker = ProductRanker()
        self.crawl_service_client = CrawlServiceClient()  # ✅ HTTP client to Crawl Service (8003)
        self.product_service_client = ProductServiceClient()  # ✅ HTTP client to Product Service (8001)
        self.category_validator = CategoryValidator(
            product_service_client=self.product_service_client,
            crawl_service_client=self.crawl_service_client
        )  # ✅ Pass ProductServiceClient and CrawlServiceClient
        
        # Cache management (Lazada-style)
        self.enable_cache = True  # Set to False to disable caching
        
        # LLM suggestion cache - avoid repeated LLM calls
        self.llm_suggestion_cache = {}  # key: user_input hash, value: suggestions
        
        import os
        database_url = os.getenv(
            "DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'kltn')}"
        )
        self.category_cache = CategoryCache(
            backend="postgres",
            pg_url=database_url
        )
    
    def _sanitize_json_backslashes(self, json_text: str) -> str:
        """
        Fix unescaped backslashes in JSON strings (regex patterns).
        
        The LLM may generate JSON with patterns like:
        - "value_pattern": "[8-9][0-9]?\s?gb"
        
        But JSON requires:
        - "value_pattern": "[8-9][0-9]?\\s?gb"
        
        This function escapes unescaped backslashes in JSON string values.
        """
        # Strategy: Find all strings in the JSON and fix unescaped backslashes within them
        result = []
        i = 0
        
        while i < len(json_text):
            char = json_text[i]
            
            # Check if we're starting a string
            if char == '"':
                result.append(char)
                i += 1
                
                # Read until we find the closing quote
                string_content = []
                while i < len(json_text):
                    char = json_text[i]
                    
                    if char == '\\':
                        # Backslash found - check if it's already escaped
                        if i + 1 < len(json_text):
                            next_char = json_text[i + 1]
                            
                            # Already escaped? (\\, \", \/, \b, \f, \n, \r, \t, \u)
                            if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                                # Valid JSON escape - keep as is
                                string_content.append(char)
                                i += 1
                                string_content.append(json_text[i])
                                i += 1
                            else:
                                # Unescaped backslash (regex pattern) - escape it
                                string_content.append('\\\\')
                                i += 1
                        else:
                            string_content.append(char)
                            i += 1
                    
                    elif char == '"':
                        # End of string
                        result.extend(string_content)
                        result.append(char)
                        i += 1
                        break
                    
                    else:
                        string_content.append(char)
                        i += 1
            
            else:
                result.append(char)
                i += 1
        
        return ''.join(result)
    
    def _build_answer_response(
    self,
    category: str,
    extracted_attributes: Dict[str, Any],
    product_count: int,
    available_filters: Dict[str, Any] = None
) -> str:
        """
        Build a natural conversational shopping response.

        Example:
        - "Mình đang ưu tiên các mẫu giày với màu sắc trắng cho bạn nè.
        Bạn vẫn có thể lọc thêm theo thương hiệu hoặc mức giá."

        - "Có vẻ bạn đang tìm giày với size 40 đúng không 👀
        Ngoài ra vẫn có thể refine thêm theo màu sắc hoặc giá."
        """

        import random

        # ═══════════════════════════════════════════════════════════════
        # Helper: natural Vietnamese join
        # ═══════════════════════════════════════════════════════════════

        def natural_join(items):

            if not items:
                return ""

            if len(items) == 1:
                return items[0]

            return ", ".join(items[:-1]) + f" hoặc {items[-1]}"

        # ═══════════════════════════════════════════════════════════════
        # Build attribute description
        # Example:
        # {
        #   "màu sắc": "trắng",
        #   "size": "40"
        # }
        #
        # -> "màu sắc trắng và size 40"
        # ═══════════════════════════════════════════════════════════════

        attribute_parts = []

        if extracted_attributes:

            for attr_name, attr_value in extracted_attributes.items():

                if attr_value is None:
                    continue

                if attr_value == "":
                    continue

                # Handle list values
                if isinstance(attr_value, list):

                    cleaned_values = [
                        str(v).strip()
                        for v in attr_value
                        if str(v).strip()
                    ]

                    if not cleaned_values:
                        continue

                    value_str = ", ".join(cleaned_values)

                else:

                    value_str = str(attr_value).strip()

                    if not value_str:
                        continue

                attribute_parts.append(
                    f"{attr_name} {value_str}"
                )

        # ═══════════════════════════════════════════════════════════════
        # Build product description
        #
        # Example:
        # "giày với màu trắng và size 40"
        # ═══════════════════════════════════════════════════════════════

        product_desc = category

        if attribute_parts:

            if len(attribute_parts) == 1:

                attr_text = attribute_parts[0]

            else:

                attr_text = (
                    ", ".join(attribute_parts[:-1])
                    + f" và {attribute_parts[-1]}"
                )

            product_desc = (
                f"{category} với {attr_text}"
            )

        # ═══════════════════════════════════════════════════════════════
        # Build available filter suggestions dynamically
        #
        # Input:
        # {
        #   "Màu sắc": [...],
        #   "Thương hiệu": [...],
        #   "Kích cỡ": [...]
        # }
        # ═══════════════════════════════════════════════════════════════

        filter_suggestions = []

        if available_filters:

            for attr_name, options in available_filters.items():

                # Skip empty options
                if not options:
                    continue

                label = str(attr_name).strip()

                if not label:
                    continue

                filter_suggestions.append(label)

        # ═══════════════════════════════════════════════════════════════
        # Remove already-applied filters
        # ═══════════════════════════════════════════════════════════════

        normalized_attributes = [

            str(k).strip().lower()

            for k in extracted_attributes.keys()
        ]

        filter_suggestions = [

            f for f in filter_suggestions

            if str(f).strip().lower()
            not in normalized_attributes
        ]

        # Deduplicate
        filter_suggestions = list(
            dict.fromkeys(filter_suggestions)
        )

        # ═══════════════════════════════════════════════════════════════
        # Conversational templates
        # ═══════════════════════════════════════════════════════════════

        opening_templates = [

            "Mình đang ưu tiên các mẫu {product_desc} cho bạn nè.",

            "Có vẻ bạn đang tìm {product_desc} đúng không 👀",

            "Mình đã lọc thử các sản phẩm {product_desc}.",

            "Đây là những mẫu {product_desc} khá phù hợp với tìm kiếm hiện tại.",

            "Hiện tại mình đang focus vào các sản phẩm {product_desc}.",

            "Mình vừa refine kết quả sang nhóm {product_desc}.",

            "Các sản phẩm {product_desc} này đang khớp khá tốt với nhu cầu của bạn.",

            "Mình đang thử ưu tiên các mẫu {product_desc} xem có hợp với bạn không nhé.",

            "Mình đã ưu tiên hiển thị các sản phẩm {product_desc}.",

            "Mấy mẫu {product_desc} này đang khá sát với nhu cầu hiện tại của bạn.",
        ]

        followup_templates = [

            "Bạn vẫn có thể lọc thêm theo {filters}.",

            "Nếu muốn refine thêm thì mình còn hỗ trợ lọc theo {filters}.",

            "Ngoài ra vẫn có thể chọn thêm {filters}.",

            "Bạn muốn mình lọc tiếp theo {filters} không?",

            "Mình vẫn có thể thu hẹp kết quả hơn bằng {filters}.",

            "Bạn cũng có thể thử lọc thêm theo {filters}.",

            "Ngoài những tiêu chí hiện tại thì vẫn còn có thể refine theo {filters}.",

            "Nếu cần mình vẫn có thể lọc sâu hơn theo {filters}.",
        ]

        # ═══════════════════════════════════════════════════════════════
        # Build opening
        # ═══════════════════════════════════════════════════════════════

        opening = random.choice(
            opening_templates
        ).format(
            product_desc=product_desc
        )

        # ═══════════════════════════════════════════════════════════════
        # Build followup
        # ═══════════════════════════════════════════════════════════════

        if filter_suggestions:

            filter_text = natural_join(
                filter_suggestions[:3]
            )

            followup = random.choice(
                followup_templates
            ).format(
                filters=filter_text
            )

            return f"{opening} {followup}"

        return opening
    def _convert_comprehensive_attributes_to_dict(
        self,
        comprehensive_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert comprehensive LLM analysis to attributes dict.
        
        Returns ALL attributes (including null values) for ProductService crawling.
        
        Priority:
        1. user_value (explicit user input)
        2. expected_values[0] (LLM inferred value)
        3. null (schema hint for crawling, naturally skipped in ranking)
        
        Ranking automatically skips null values (_calculate_attribute_match_score returns 0.0).
        """
        attributes_dict = {}
        
        attributes_list = comprehensive_analysis.get("extracted_attributes") or comprehensive_analysis.get("attributes")
        if isinstance(attributes_list, list):
            for attr in attributes_list:
                attr_name = attr.get("name", "").strip()
                
                if not attr_name:
                    continue
                
                # Priority 1: user_value
                user_value = attr.get("user_value")
                if user_value is not None:
                    attributes_dict[attr_name] = user_value
                    continue
                
                # Priority 2: expected_values (use first value if available)
                expected_values = attr.get("expected_values")
                if expected_values and isinstance(expected_values, list) and len(expected_values) > 0:
                    value = expected_values[0]
                    if value is not None:
                        attributes_dict[attr_name] = value
                        continue
                
                # Priority 3: Include null as schema hint for crawling
                # Ranking will skip this (score=0.0) but ProductService can use it for crawling
                attributes_dict[attr_name] = None
        
        elif isinstance(attributes_list, dict):
            for name, attr_obj in attributes_list.items():
                if isinstance(attr_obj, dict):
                    user_value = attr_obj.get("user_value")
                    if user_value is not None:
                        attributes_dict[name] = user_value
                    else:
                        expected_values = attr_obj.get("expected_values")
                        if expected_values and isinstance(expected_values, list) and len(expected_values) > 0:
                            attributes_dict[name] = expected_values[0]
                        else:
                            attributes_dict[name] = None
                else:
                    attributes_dict[name] = attr_obj
        
        return attributes_dict
    
    def _calculate_attribute_match_score(self, expected_value: Any, product_value: Any) -> float:
        if not expected_value or product_value is None:
            return 0.0
        
        expected_str = str(expected_value).strip().lower()
        product_str = str(product_value).strip().lower()
        
        # 1. Exact match
        if expected_str == product_str:
            return 1.0
        
        # 2. Partial match (one contains the other)
        if expected_str in product_str or product_str in expected_str:
            return 0.85
        
        # 3. Numeric comparison (e.g., ">=16GB" vs "16GB")
        # Handle patterns like ">=16GB", "<=1000W", ">8", etc.
        try:
            import re
            comparison_pattern = r'^(>=|<=|>|<|=)?(.+?)(\s*(?:gb|mb|kb|w|watt|mah|inch|cm|mm|lít|ml))?$'
            
            expected_match = re.match(comparison_pattern, expected_str)
            product_match = re.match(comparison_pattern, product_str)
            
            if expected_match and product_match:
                exp_op = expected_match.group(1) or "="
                exp_num_str = expected_match.group(2).strip()
                prod_num_str = product_match.group(2).strip()
                
                # Try to extract numeric values
                exp_num_match = re.search(r'(\d+(?:\.\d+)?)', exp_num_str)
                prod_num_match = re.search(r'(\d+(?:\.\d+)?)', prod_num_str)
                
                if exp_num_match and prod_num_match:
                    exp_num = float(exp_num_match.group(1))
                    prod_num = float(prod_num_match.group(1))
                    
                    # Check numeric condition
                    if exp_op == ">=":
                        is_match = prod_num >= exp_num
                    elif exp_op == "<=":
                        is_match = prod_num <= exp_num
                    elif exp_op == ">":
                        is_match = prod_num > exp_num
                    elif exp_op == "<":
                        is_match = prod_num < exp_num
                    else:  # "="
                        is_match = abs(prod_num - exp_num) < 0.01  # Small tolerance for floats
                    
                    if is_match:
                        #logger.debug(f"[Rank] Numeric range match: '{expected_str}' matches '{product_str}'")
                        return 0.9
                    else:
                        #logger.debug(f"[Rank] Numeric range mismatch: '{expected_str}' vs '{product_str}'")
                        return 0.3  # Partial credit for trying
        except Exception as e:
            pass
            #logger.debug(f"[Rank] Error parsing numeric comparison: {e}")
        
        # 4. Fuzzy match using substring similarity
        try:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, expected_str, product_str).ratio()
            if similarity >= 0.7:
                #logger.debug(f"[Rank] Fuzzy match (similarity={similarity:.2f}): '{expected_str}' ~= '{product_str}'")
                return 0.7 + (similarity - 0.7) * 0.3  # Scale between 0.7 and 1.0
        except Exception as e:
            pass
            #logger.debug(f"[Rank] Error in fuzzy matching: {e}")
        
        # 5. No match
        #logger.debug(f"[Rank] No match: '{expected_str}' vs '{product_str}'")
        return 0.0
    
    def _rank_products_by_attributes(
        self,
        expected_attributes: Dict[str, Any],
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank products based on how well their attributes match expected values.
        
        Algorithm:
        1. For each product, calculate match score for each attribute
        2. Aggregate scores (weighted by importance if applicable)
        3. Sort products by total score (highest first)
        4. Return sorted list with scores attached
        
        Args:
            expected_attributes: Dict like {"ram": "16GB", "storage": "SSD", ...}
            products: List of product dicts from crawl service
            
        Returns:
            List of products sorted by match score (highest first)
        """
        if not products:
            #logger.warning("[Rank] No products to rank")
            return []
        
        if not expected_attributes:
            #logger.warning("[Rank] No expected attributes provided, returning products unsorted")
            return products
        
        #logger.info(f"[Rank] Starting ranking for {len(products)} products")
        logger.info(f"[Rank] Expected attributes: {expected_attributes}")
        
        # Calculate score for each product
        ranked_products = []
        
        for idx, product in enumerate(products):
            attribute_scores = []
            
            for attr_name, expected_value in expected_attributes.items():
                # Try to find product attribute in multiple places
                product_attr_value = None
                
                # 1. Check if product has direct field with attribute name
                if attr_name in product:
                    product_attr_value = product.get(attr_name)
                
                # 2. Check if product has "attributes" dict/list
                elif "attributes" in product:
                    attrs = product["attributes"]
                    if isinstance(attrs, dict):
                        product_attr_value = attrs.get(attr_name)
                    elif isinstance(attrs, list):
                        for attr in attrs:
                            if isinstance(attr, dict) and attr.get("name") == attr_name:
                                product_attr_value = attr.get("value")
                                break
                
                # 3. Check detailed_attributes (from product detail crawl)
                elif "detailed_attributes" in product:
                    detailed_attrs = product["detailed_attributes"]
                    if isinstance(detailed_attrs, dict):
                        product_attr_value = detailed_attrs.get(attr_name)
                    elif isinstance(detailed_attrs, list):
                        for attr in detailed_attrs:
                            if isinstance(attr, dict) and attr.get("name") == attr_name:
                                product_attr_value = attr.get("value")
                                break
                
                # Calculate match score
                score = self._calculate_attribute_match_score(expected_value, product_attr_value)
                attribute_scores.append({
                    "attribute": attr_name,
                    "expected": expected_value,
                    "actual": product_attr_value,
                    "score": score
                })
                
                #logger.debug(f"[Rank] Product {idx}: {attr_name} score={score:.2f} (expected='{expected_value}', actual='{product_attr_value}')")
            
            # Aggregate scores (simple average)
            total_score = sum(s["score"] for s in attribute_scores) / len(attribute_scores) if attribute_scores else 0.0
            
            # Attach score to product
            product_with_score = product.copy()
            product_with_score["_match_score"] = total_score
            product_with_score["_attribute_scores"] = attribute_scores
            
            ranked_products.append((total_score, product_with_score))
            #logger.info(f"[Rank] Product {idx} (ID: {product.get('product_id', 'N/A')}): total_score={total_score:.2f}")
        
        # Sort by score descending (highest score first)
        ranked_products.sort(key=lambda x: x[0], reverse=True)
        
        # Extract just the products
        sorted_products = [p for _, p in ranked_products]
        
        #logger.info(f"[Rank] ✅ Ranking complete. Top 3 scores: {[p['_match_score'] for p in sorted_products[:3]]}")
        
        return sorted_products
    
    def classify_request_case(
        self, 
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        # Get intent_type from detected_intent (from analyze_processor)
        detected_intent = conversation_state.get("detected_intent", {})
        intent_type = detected_intent.get("intent_type", "none")
        
        # 🔧 NORMALIZE to lowercase to avoid case sensitivity bugs
        # LLM may return "SPECIFIC"/"ABSTRACT" but we compare with lowercase
        intent_type = str(intent_type).strip().lower() if intent_type else "none"
        
        confidence = detected_intent.get("confidence", 0.0)
        
        # CASE 4: Abstract intent (user exploring new category)
        if intent_type == "abstract":
            #logger.info(f"[classify_request_case] ✅ CASE 4: Abstract intent detected")
            return {
                "case": 4,
                "case_name": "abstract_intent",
                "reason": "Intent Type is 'abstract' (user exploring new category)",
                "data": {
                    "needs_llm": True,
                    "suggest_categories": True
                }
            }
        
        # CASE 1: Specific intent (user refining search)
        if intent_type == "specific":
            #logger.info(f"[classify_request_case] ✅ CASE 1: Specific intent detected")
            return {
                "case": 1,
                "case_name": "clear_request",
                "reason": "Intent Type is 'specific' (user refining within category)",
                "data": {
                    "confidence": confidence,
                    "should_use_llm": False,
                    "can_crawl_immediately": True
                }
            }
        
        # Default: treat as abstract intent (LLM to clarify)
        #logger.info(f"[classify_request_case] ✅ DEFAULT: Unknown intent_type, treating as abstract")
        return {
            "case": 4,
            "case_name": "abstract_intent",
            "reason": f"Intent type '{intent_type}' is unclear, suggesting categories",
            "data": {
                "needs_llm": True,
                "suggest_categories": True
            }
        }

    
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
    
    async def handle_case_1_clear_request(
        self,
        user_input: str,
        case_data: Dict[str, Any],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Ensure state structure
        conversation_state = self._ensure_state_structure(conversation_state)
        
        #logger.info(f"[CASE 1] Processing clear request")
        
        # 🆕 STEP 1: Extract category + attributes (LLM call - ONLY for CASE 1)
        merged_intent = conversation_state.get("merged_intent", user_input)
        logger.info(f"\n[CASE 1] 🧠 Extracting category + attributes (LLM call)...")
        logger.info(f"[CASE 1] User input: '{merged_intent}'")
        comprehensive = self._comprehensive_intent_analysis(merged_intent, conversation_state)
        conversation_state["comprehensive_analysis"] = comprehensive
        logger.info(f"[CASE 1] ✅ Extraction done:")
        logger.info(f"[CASE 1] Full response: {comprehensive}")
        
        category = comprehensive.get("category", "")
        if not category:
            logger.error(
                f"[❌ CASE 1] Category is empty! Response was: {comprehensive}"
            )
            return {
                "status": "error",
                "message": "Không thể xác định danh mục sản phẩm. Vui lòng mô tả cụ thể hơn.",
                "case": 1,
                "state": conversation_state
            }
        
        # 🆕 Extract detected attributes from comprehensive analysis BEFORE validation
        comprehensive_analysis = conversation_state.get("comprehensive_analysis", {})
        # Check both 'extracted_attributes' and 'attributes' keys
        detected_attributes = comprehensive_analysis.get("extracted_attributes") or comprehensive_analysis.get("attributes", [])
        detected_attributes_names = [attr.get("name") if isinstance(attr, dict) else str(attr) for attr in detected_attributes] if detected_attributes else []
        #logger.info(f"[CASE 1] 📊 Detected attributes from analysis: {detected_attributes_names}")
        
        # STEP 2: Validate category before proceeding
        #logger.info(f"[CASE 1] Validating category: '{category}' with {len(detected_attributes_names)} detected attributes")
        validation_result = await self.category_validator.validate_category(
            user_category=category,
            detected_attributes=detected_attributes_names if detected_attributes_names else None
        )
        logger.info(f"[CASE 1] Category validation result: {validation_result}")
        if not validation_result["success"]:
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
        
        #logger.info(f"[CASE 1] ✅ Category validated: '{category}' → '{validated_category}' (id={category_id}, status={validation_status})")
        
        conversation_state["has_category"] = True
        conversation_state["category"] = validated_category
        conversation_state["category_id"] = category_id
        conversation_state["category_validation"] = {
            "original": category,
            "normalized": validated_category,
            "status": validation_status
        }
        
        # STEP 3: Extract attributes for search
        comprehensive_analysis = conversation_state.get("comprehensive_analysis", {})
        llm_attributes = self._convert_comprehensive_attributes_to_dict(comprehensive_analysis)
        
        # 🔄 Normalize LLM attribute names using mapping from schema evolution
        attribute_mapping = validation_result.get("attribute_mapping", {})
        attributes_for_search = {}
        
        for llm_attr_name, llm_attr_value in llm_attributes.items():
            # Use mapped name if available, otherwise keep LLM name
            db_attr_name = attribute_mapping.get(llm_attr_name, llm_attr_name)
            attributes_for_search[db_attr_name] = llm_attr_value
            
            if db_attr_name != llm_attr_name:
                logger.info(f"[CASE 1] 🔄 Normalized attribute: '{llm_attr_name}' → '{db_attr_name}'")
        
        logger.info(f"[CASE 1] ✨ Extracted attributes for search (normalized): {attributes_for_search}")
        
        # Store normalized attributes to state
        conversation_state["extracted"] = attributes_for_search.copy()
        
        # FALLBACK: If LLM attributes empty, use rule-based extraction
        if not attributes_for_search or len(attributes_for_search) == 0:
            logger.info(f"[CASE 1] 💡 LLM attributes empty → Using rule-based extraction")
            extract_result = self.attribute_extractor.extract(
                user_input,
                validated_category,
                use_llm=False  # CRITICAL: No LLM for Case 1
            )
            attributes_for_search = extract_result["extracted"].copy()
            conversation_state["extracted"] = extract_result["extracted"]
            
            if not attributes_for_search or len(attributes_for_search) == 0:
                product_name = conversation_state.get("detected_intent", {}).get("product_name", "").strip()
                if product_name and product_name.lower() != validated_category.lower():
                    attributes_for_search["loai"] = product_name
                    logger.info(f"[CASE 1] 💡 No attributes → Using product_name as search hint: '{product_name}'")
        
        # STEP 4: Get products - DB or crawl+detail if needed
        # ✅ ProductServiceClient handles ALL crawling logic internally
        # ✅ Full attribute schema (including null expected_values) stays in conversation_state["comprehensive_analysis"]
        # ✅ ProductService will use comprehensive_analysis from state for detailed crawling decisions
        
        logger.info(f"[CASE 1] 📤 Requesting products for category_id={category_id}, category_name='{validated_category}', attributes={attributes_for_search}, limit=50")
        
        products = await self.product_service_client.get_or_crawl_products(
            category_id=category_id,
            category_name=validated_category,
            attributes=attributes_for_search if attributes_for_search else None,
            limit=50
        )
        
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": 1,
                "state": conversation_state
            }
        
        #logger.info(f"[CASE 1] ✅ Got {len(products)} products")
        
        # STEP 5: RANK products by attribute match (now products have full attributes)
        #logger.info(f"[CASE 1] 🎯 Ranking {len(products)} products by attribute match...")
        ranked_products = self._rank_products_by_attributes(attributes_for_search, products)
        
        if ranked_products:
            pass
            #logger.info(f"[CASE 1] ✅ Ranking complete. Top product match score: {ranked_products[0].get('_match_score', 0):.2f}")
        
        # STEP 6: Return ranked products
        return await self._process_crawl_results(ranked_products, conversation_state, case=1)
    
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
        
        #logger.info(f"[CASE 4] Abstract intent detected, using LLM for category suggestions")
        
        # Call LLM with purpose-oriented prompt
        import json
        prompt = f"""
You are an advanced Vietnamese ecommerce shopping intent assistant.

The user has expressed an ABSTRACT shopping intent.

Your job is to transform vague emotional/lifestyle/gift/purpose intent
into CONCRETE, SEARCHABLE ecommerce shopping entities.

==================================================
USER INPUT
==================================================

"{user_input}"

==================================================
CORE OBJECTIVE
==================================================

Convert ABSTRACT intent into SPECIFIC shopping suggestions.

The suggestions must:
- be purchasable
- be searchable in ecommerce systems
- contain concrete product nouns
- help transition the user into product search flow

==================================================
CRITICAL HARD RULES
==================================================

1. EVERY suggestion MUST contain a purchasable noun.

GOOD:
- "tai nghe chống ồn"
- "nến thơm"
- "máy massage cổ"
- "đèn ngủ"
- "sách self-help"

BAD:
- "thư giãn"
- "giải trí"
- "chăm sóc sức khỏe"
- "phong cách sống"
- "minimalism"

--------------------------------------------------

2. NEVER suggest vague lifestyle concepts.

Do NOT return:
- emotions
- moods
- aesthetics
- abstract themes
without concrete purchasable products.

--------------------------------------------------

3. Suggestions MUST be searchable.

The user should be able to click the suggestion
and immediately search products.

--------------------------------------------------

4. Prefer practical Vietnamese ecommerce behavior.

Think like:
- Shopee
- Lazada
- Tiki

--------------------------------------------------

5. Prioritize:

- concrete products
- concrete categories
- common ecommerce keywords
- highly purchasable entities

--------------------------------------------------

6. Suggestions should feel NATURAL for Vietnamese users.

==================================================
SUGGESTION STRATEGY
==================================================

When users express:

- stress
→ suggest relaxation products

- gift intent
→ suggest giftable products

- productivity intent
→ suggest productivity tools

- aesthetics/vibes
→ suggest matching fashion/decor/accessories

- hobbies/interests
→ suggest related products

==================================================
GOOD VS BAD EXAMPLES
==================================================

--------------------------------------------------
USER:
"tôi đang stress"
--------------------------------------------------

GOOD:
- "tai nghe chống ồn"
- "nến thơm"
- "máy massage cổ"
- "trà ngủ ngon"
- "đèn ngủ"

BAD:
- "thư giãn"
- "giải trí"
- "self-care"

==================================================

--------------------------------------------------
USER:
"tôi cần quà cho bạn gái"
--------------------------------------------------

GOOD:
- "gấu bông"
- "nước hoa nữ"
- "son môi"
- "vòng cổ"
- "nến thơm"

BAD:
- "quà tặng"
- "lãng mạn"
- "tình yêu"

==================================================

--------------------------------------------------
USER:
"vibe hàn quốc"
--------------------------------------------------

GOOD:
- "áo cardigan hàn quốc"
- "đèn ngủ decor"
- "son tint"
- "túi tote"
- "nến thơm"

BAD:
- "phong cách hàn quốc"
- "korean aesthetic"

==================================================

--------------------------------------------------
USER:
"muốn setup góc học tập"
--------------------------------------------------

GOOD:
- "đèn bàn học"
- "bàn phím cơ"
- "giá đỡ laptop"
- "ghế công thái học"
- "kệ để bàn"

BAD:
- "productivity"
- "workspace"

==================================================

--------------------------------------------------
USER:
"đồ gì đó chill chill"
--------------------------------------------------

GOOD:
- "loa bluetooth"
- "đèn led decor"
- "máy khuếch tán tinh dầu"
- "nến thơm"
- "ghế lười"

BAD:
- "chill"
- "relaxation"

==================================================

--------------------------------------------------
USER:
"cho người thích gym"
--------------------------------------------------

GOOD:
- "bình nước thể thao"
- "găng tay tập gym"
- "tai nghe thể thao"
- "áo gym"
- "túi tập gym"

BAD:
- "fitness"
- "healthy lifestyle"

==================================================

--------------------------------------------------
USER:
"tôi muốn ngủ ngon hơn"
--------------------------------------------------

GOOD:
- "gối memory foam"
- "đèn ngủ"
- "máy tạo tiếng ồn trắng"
- "tinh dầu ngủ ngon"
- "trà thảo mộc"

BAD:
- "giấc ngủ"
- "wellness"

==================================================

--------------------------------------------------
USER:
"minimalist"
--------------------------------------------------

GOOD:
- "đồng hồ tối giản"
- "ví da tối giản"
- "áo thun basic"
- "bàn làm việc tối giản"
- "đèn bàn minimal"

BAD:
- "minimalism"
- "simple lifestyle"

==================================================

--------------------------------------------------
USER:
"tôi cần gì đó để học online"
--------------------------------------------------

GOOD:
- "webcam"
- "tai nghe có mic"
- "giá đỡ laptop"
- "bàn học"
- "đèn bàn"

BAD:
- "học tập"
- "study setup"

==================================================

--------------------------------------------------
USER:
"cho dân IT"
--------------------------------------------------

GOOD:
- "bàn phím cơ"
- "chuột không dây"
- "giá đỡ laptop"
- "màn hình phụ"
- "ghế công thái học"

BAD:
- "công nghệ"
- "productivity"

==================================================
EDGE CASE RULES
==================================================

If the user input is:
- emotion
- vibe
- lifestyle
- personality
- aesthetic
- purpose
- gift intent

You MUST map it into:
- concrete purchasable products
- searchable ecommerce entities

--------------------------------------------------

If uncertain:
prefer MORE CONCRETE suggestions.

--------------------------------------------------

Every suggestion MUST contain:
- a product noun
OR
- a searchable ecommerce category
==================================================
CONVERSATIONAL RESPONSE RULES
==================================================

Besides suggestions, generate a SHORT natural Vietnamese assistant message.

The message should:
- feel empathetic
- acknowledge the user's situation/intention
- sound conversational and human
- NOT sound robotic or repetitive
- NOT always start with:
  "Dựa trên nhu cầu của bạn"

GOOD:
- "Nghe có vẻ bạn đang muốn setup góc học tập thoải mái hơn."
- "Có vẻ bạn đang tìm thứ gì đó để thư giãn sau giờ làm."
- "Mình nghĩ bạn đang muốn tìm quà vừa dễ tặng vừa thực tế."
- "Nếu theo vibe này thì có vài món khá hợp với bạn."

BAD:
- "Dựa trên nhu cầu của bạn..."
- "Tôi đề xuất..."
- "Sau đây là các sản phẩm..."

Keep it:
- short
- natural
- warm
- Vietnamese conversational style
==================================================
OUTPUT RULES
==================================================

Return ONLY valid JSON.

Do NOT use markdown.

Do NOT explain outside JSON.

==================================================
OUTPUT FORMAT
==================================================

{{
"assistant_message": "natural conversational message",
  "suggestions": [
    {{
      "search_term": "concrete searchable product/category",
      "reason": "why this matches the user's intent",
      "example_products": [
        "example 1",
        "example 2"
      ]
    }}
  ]
}}
"""
        
        try:
            response = call_openai(prompt, model="gpt-4o-mini", temperature=0.3, max_tokens=1000)
            if not response:
                return {
                    "status": "need_info",
                    "question": "Tôi chưa hiểu rõ nhu cầu của bạn. Bạn có thể mô tả cụ thể hơn không?",
                    "case": 4,
                    "state": conversation_state
                }
            
            data = json.loads(response.strip().replace("```json", "").replace("```", ""))
            suggestions = data.get("suggestions", [])
            logger.info(f"[CASE 4] LLM returned {(suggestions)} suggestions")
            if not suggestions:
                return {
                    "status": "need_info",
                    "question": "Tôi chưa hiểu rõ nhu cầu của bạn. Bạn có thể mô tả cụ thể hơn không?",
                    "case": 4,
                    "state": conversation_state
                }
            
            return {
                "status": "need_info",
                "question": data.get("assistant_message", "Dựa trên nhu cầu của bạn, tôi gợi ý một số loại sản phẩm sau:"),
                "options": [
                    {
                        "label": s["search_term"],
                        "value": s["search_term"],
                        "reason": s.get("reason", ""),
                        "examples": s.get("example_products", [])
                    }
                    for s in suggestions
                ],
                "case": 4,
                "state": conversation_state
            }
            
        except Exception as e:
            #logger.info(f"[CASE 4] LLM error: {e}")
            return {
                "status": "error",
                "message": "Xin lỗi, tôi gặp khó khăn khi phân tích yêu cầu của bạn. Vui lòng thử lại.",
                "case": 4,
                "state": conversation_state
            }
    
    async def _process_crawl_results(
        self,
        products: List[Dict[str, Any]],
        conversation_state: Dict[str, Any],
        case: int
    ) -> Dict[str, Any]:
        """
        Helper to process products from DB and return formatted results
        
        All products come from DB (either directly or saved after crawling)
        
        Args:
            products: List of products from DB (already ranked)
            conversation_state: Current conversation state
            case: Case number (1 or 4)
        """
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "case": case,
                "state": conversation_state
            }
        
        # Normalize products
        products = [self._normalize_product(p) for p in products]
        
        # Update cache (will be set below after fetching filters)
        conversation_state["cached_products"] = products
        conversation_state["last_crawl_params"] = {
            "category": conversation_state["category"],
            "brand": conversation_state["extracted"].get("brand")
        }
        
        # ====== Fetch filters from ProductService (same as old flow) ======
        filter_groups = []
        category = conversation_state.get("category", "")
        
        if category:
            try:
                # 📤 Call ProductService to fetch filters
                available_filters = await self.product_service_client.get_filters(category)
                filter_groups = [
                    {
                        "attribute_name": f.get('name') or f.get('attribute_name'),
                        "display_name": f.get('display_name') or f.get('name') or f.get('attribute_name'),
                        "data_type": f.get('type') or f.get('data_type') or 'text',
                        "options": [
                            {
                                "attribute_value": val,
                                "product_count": 0
                            }
                            for val in f.get('values', [])
                        ] if f.get('values') else []
                    }
                    for f in available_filters
                ]
                logger.info(f"[Orchestrator] ✅ Fetched {len(filter_groups)} filters from ProductService")
            except Exception as e:
                logger.warning(f"[Orchestrator] ⚠️ Failed to fetch filters: {e}. Continuing without filters...")
        
        # Build friendly answer response for Case 1
        answer = None
        if case == 1:
            # Convert filter_groups to simple dict for _build_answer_response
            simple_filters = {}
            for fg in filter_groups:
                attr_name = fg.get('attribute_name', '')
                if attr_name:
                    simple_filters[attr_name] = fg.get('options', [])
            
            answer = self._build_answer_response(
                category=conversation_state.get("category", "sản phẩm"),
                extracted_attributes=conversation_state.get("extracted", {}),
                product_count=len(products),
                available_filters=simple_filters
            )
            
        result = {
            "status": "results",
            "products": products,
            "total_found": len(products),
            "filters": filter_groups,  # ✅ Include filter_groups directly
            "case": case,
            "state": conversation_state
        }
        
        # Cache the filters
        conversation_state["cached_filters"] = filter_groups
        
        # Add answer if case 1
        if answer:
            result["answer"] = answer
            
        return result
    
    def _comprehensive_intent_analysis(
    self,
    merged_intent: str,
    conversation_state: Dict[str, Any] = None
) -> Dict[str, Any]:
        """
        Single-pass comprehensive intent analysis.

        ONE LLM CALL ONLY:
        - Category classification
        - Attribute extraction
        - Confidence estimation

        Returns:
        {
            "merged_intent": str,
            "category": str,
            "extracted_attributes": list,
            "confidence": float,
            "category_changed": bool,
            "method": "comprehensive_llm"
        }
        """

        import json
        import re

        # #logger.info(
        #     f"[Orchestrator] 🧠 Comprehensive analysis for intent: '{merged_intent}'"
        # )

        categories_text = ", ".join(AVAILABLE_CATEGORIES)

        prompt = f"""
You are an AI system for:

* E-commerce query understanding
* Product category detection
* Retrieval-oriented attribute schema generation
* Semantic search intent analysis
* Product ranking signal generation

Your output schema will be used for:

* semantic product retrieval
* attribute extraction
* product filtering
* ranking
* recommendation
* search matching

==================================================
USER QUERY
==========

"{merged_intent}"

==================================================
KNOWN CATEGORIES (REFERENCE ONLY)
=================================

{categories_text}

IMPORTANT:

* KNOWN CATEGORIES are only references/examples
* You MAY create a NEW category if needed
* DO NOT force unrelated categories
* Prefer literal and concrete product types

==================================================
CATEGORY RULES
==============

If the query explicitly mentions a concrete product type,
the category MUST be that exact product type.

GOOD:

* "tai nghe bluetooth" -> "tai nghe"
* "iphone 15" -> "điện thoại"
* "macbook air" -> "laptop"
* "màn hình 144hz" -> "màn hình"

BAD:

* "tai nghe" -> "điện thoại"
* "tivi" -> "điện tử"

Use broad/general categories ONLY for abstract queries.

==================================================
IMPORTANT SYSTEM MINDSET
========================

This system is PRIMARILY for:

* semantic retrieval
* ranking
* product matching

NOT only regex extraction.

IMPORTANT:

* expected_values are MORE IMPORTANT than regex patterns
* Prefer semantic searchable values
* Prefer canonical retrieval values
* Regex patterns are OPTIONAL helpers only

GOOD:

* "wireless"
* "bluetooth"
* "oled"
* "144hz"
* "đen"

BAD:

* "(có|không có) bluetooth"
* boolean-style regex features
* vague yes/no patterns

==================================================
ATTRIBUTE GENERATION RULES
==========================

Generate ONLY attributes that satisfy ALL conditions:
IMPORTANT:

Even if the query is broad or generic,
you SHOULD still generate COMMON RETRIEVAL ATTRIBUTES
for the detected category.

For generic product queries:
- expected_values may be null
- but useful retrieval attributes should still exist

Examples:

Query:
"giày"

Possible attributes:
- brand
- size
- màu sắc
- chất liệu
- kiểu dáng
- giới tính

Query:
"điện thoại"

Possible attributes:
- brand
- ram
- storage
- pin
- màn hình
- màu sắc
1. Commonly written EXPLICITLY in Vietnamese e-commerce data

2. Useful for:

   * filtering
   * ranking
   * retrieval
   * comparison
   * semantic search

3. Usually appear in:

   * product specifications
   * titles
   * technical details
   * descriptions

4. Realistically searchable by users

IMPORTANT:

Also prioritize COMMON E-COMMERCE ATTRIBUTES when relevant:

* brand
* price
* budget range
* storage
* size
* color
* material

These attributes are highly valuable for:
* retrieval
* filtering
* ranking
* comparison

Prefer attributes with:

* finite enumerated values
* measurable values
* technical specifications
* physical properties
* compatibility information
* meaningful purchase intent

==================================================
RETRIEVAL INTENT RULES
======================

For EVERY attribute, infer:

* expected_values
* priority
* constraint_type

These fields are REQUIRED.

==================================================
EXPECTED VALUES RULES
=====================

expected_values represent what the user is likely searching for.

expected_values MUST:

* reflect user intent
* use searchable values
* use canonical semantic values whenever possible
* avoid unnecessary variations

GOOD:

* ["wireless"]
* ["bluetooth"]
* ["đen"]
* ["oled"]
* ["144hz"]
* ["16gb"]

BAD:

* ["có bluetooth"]
* ["hỗ trợ bluetooth"]
* hallucinated exact specs
* unsupported inferred models

If the query does not mention or imply a value:

* use null

==================================================
PRIORITY RULES
==============

Every attribute MUST declare priority.

Allowed values:

* "critical"
* "high"
* "medium"
* "low"

Meaning:

critical:

* core purchase intent
* strongly affects ranking
* often should filter results

high:

* very important preference
* major ranking signal

medium:

* relevant but not dominant

low:

* minor preference

GOOD examples:

Query:
"chuột gaming không dây logitech"

* connection_type -> critical
* brand -> high
* gaming_features -> high
* color -> low

Query:
"iphone 15 256gb"

* model -> critical
* storage -> high
* color -> low

==================================================
CONSTRAINT TYPE RULES
=====================

Every attribute MUST declare constraint_type.

Allowed values:

* "hard"
* "soft"

hard:

* products SHOULD strongly match
* mismatches should be heavily penalized

soft:

* preference only
* mismatch acceptable

GOOD examples:

Query:
"tai nghe bluetooth"

* connection_type -> hard

Query:
"màu đen"

* color -> soft

==================================================
ATTRIBUTE TYPE RULES
====================

Every attribute MUST declare attr_type.

Allowed values:

* "numeric"
* "enum"
* "multi_enum"
* "regex"

IMPORTANT:

* Prefer enum/multi_enum whenever possible
* regex should be RARE
* regex is ONLY for structured measurable patterns

==================================================
ATTR_TYPE DEFINITIONS
=====================

numeric:

* measurable numeric values
* MUST have value_pattern

GOOD:

* RAM
* battery capacity
* refresh rate
* storage
* DPI

enum:

* exactly ONE value from vocabulary
* MUST have vocabulary
* value_pattern must be null

GOOD:

* color
* skin type
* operating system

multi_enum:

* MULTIPLE possible values
* MUST have vocabulary
* value_pattern must be null

GOOD:

* connectivity
* features
* compatibility

regex:

* ONLY for structured text patterns
* MUST have specific pattern
* NEVER use broad unsafe patterns

GOOD:

* bluetooth version
* dimensions
* voltage

==================================================
REGEX SAFETY RULES
==================

NEVER use:

* ".*"
* ".+"
* "\w+"
* "\S+"

GOOD:
"[0-9]+\\s?gb"
"[0-9]+\\s?(mah|mAh)"
"[0-9]+\\s?(hz|Hz)"
"bluetooth\\s?[0-9]+\\.?[0-9]*"

==================================================
VOCABULARY RULES
================

Vocabulary MUST:

* be lowercase
* be realistic
* be searchable
* be category-specific
* contain canonical values

GOOD:
["đen", "trắng", "xanh", "silver"]
["bluetooth", "wifi", "wireless", "usb-c"]
["anc", "noise cancelling", "transparent mode"]

==================================================
OUTPUT FORMAT
=============

Return ONLY valid JSON.

{{
"category": "literal product category",

"attributes": [
{{
"name": "kết nối",

  "attr_type": "multi_enum",

  "keywords": [
    "bluetooth",
    "wifi",
    "wireless",
    "không dây"
  ],

  "vocabulary": [
    "bluetooth",
    "wifi",
    "wireless",
    "có dây",
    "usb-c"
  ],

  "value_pattern": null,

  "expected_values": [
    "bluetooth",
    "wireless"
  ],

  "priority": "critical",

  "constraint_type": "hard"
}},

{{
  "name": "màu sắc",

  "attr_type": "enum",

  "keywords": [
    "màu",
    "màu sắc",
    "color"
  ],

  "vocabulary": [
    "đen",
    "trắng",
    "xanh",
    "silver"
  ],

  "value_pattern": null,

  "expected_values": [
    "đen"
  ],

  "priority": "low",

  "constraint_type": "soft"
}}


],

"confidence": 0.95,

"category_changed": false,

"is_new_category": false
}}

==================================================
FINAL RULES
===========
* For concrete product categories, NEVER return an empty attributes list
* Return ONLY JSON

* No markdown

* No explanations

* IMPORTANT: For regex patterns in value_pattern, escape backslashes as JSON requires
  - CORRECT: "value_pattern": "[8-9][0-9]?\\s?gb"
  - WRONG: "value_pattern": "[8-9][0-9]?\s?gb"

* Every attribute MUST include:

  * attr_type
  * expected_values
  * priority
  * constraint_type

* enum and multi_enum MUST have vocabulary

* numeric and regex MUST have specific value_pattern

* vocabulary MUST be lowercase

* expected_values should reflect retrieval intent

* Prefer semantic searchable values over regex-style boolean extraction

* NEVER hallucinate unsupported product specifications


"""        
        try:
            response = call_openai(
                prompt,
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=1500  # 🔧 INCREASED from 500 to prevent JSON truncation
            )

            if not response:
                logger.warning(
                    "[❌ DEBUG] OpenAI returned EMPTY response!"
                )

                return {
                    "merged_intent": merged_intent,
                    "category": "",
                    "extracted_attributes": [],
                    "confidence": 0.0,
                    "category_changed": False,
                    "method": "comprehensive_llm"
                }

            response_text = response.strip()

            logger.info(
                f"[✅ DEBUG] Raw LLM Response:\n{response_text}"
            )

            # Remove markdown code block if exists
            json_text = response_text

            if json_text.startswith("```"):
                json_text = re.sub(
                    r"^```(?:json)?\n",
                    "",
                    json_text
                )

                json_text = re.sub(
                    r"\n```$",
                    "",
                    json_text
                )

            # 🔧 FIX: Handle truncated JSON by auto-completing if needed
            # If JSON looks truncated, try to complete it
            if not json_text.rstrip().endswith("}"):
                # Count open/close braces to estimate missing content
                open_braces = json_text.count("{")
                close_braces = json_text.count("}")
                
                if open_braces > close_braces:
                    missing_braces = open_braces - close_braces
                    json_text += "}" * missing_braces
                    logger.warning(
                        f"[⚠️ DEBUG] JSON was truncated. Added {missing_braces} closing braces"
                    )

            # 🔧 FIX: Sanitize JSON strings with unescaped backslashes (regex patterns)
            # The LLM may generate regex patterns like \s, \., \d without proper JSON escaping
            json_text_before = json_text
            json_text = self._sanitize_json_backslashes(json_text)
            
            if json_text != json_text_before:
                logger.info("[✅ DEBUG] JSON backslashes sanitized")

            data = json.loads(json_text)

            # ===== VALIDATION =====

            category = data.get("category", "").strip()
            confidence = float(data.get("confidence", 0.0))
            attributes = data.get("attributes", [])

            logger.info(f"[✅ DEBUG] Parsed category: '{category}'")
            logger.info(f"[✅ DEBUG] Parsed confidence: {confidence}")
            logger.info(f"[✅ DEBUG] Number of attributes: {len(attributes) if isinstance(attributes, list) else 'NOT_A_LIST'}")

            # Validate attributes structure
            valid_attributes = []

            if isinstance(attributes, list):
                for attr in attributes:

                    if not isinstance(attr, dict):
                        continue

                    name = attr.get("name")

                    if not name:
                        continue

                    valid_attributes.append({
                        "name": str(name).strip().lower(),
                        "keywords": attr.get("keywords", []),
                        "value_pattern": attr.get("value_pattern", ""),
                        "user_value": attr.get("user_value"),
                        "expected_values": attr.get("expected_values"),   # ← quan trọng nhất
                        "priority": attr.get("priority", "medium"),       # ← ranking signal
                        "constraint_type": attr.get("constraint_type", "soft"),
                        
                    })

            #logger.info("[Orchestrator] 📊 Parsed Analysis:")
            #logger.info(f"  - Category: {category}")
            #logger.info(f"  - Confidence: {confidence}")
            #logger.info(f"  - Attributes Count: {len(valid_attributes)}")

            # for attr in valid_attributes:
            #     # #logger.info(
            #     #     f"    • {attr['name']} = {attr.get('user_value')}"
            #     # )

            return {
                "merged_intent": merged_intent,
                "category": category,
                "extracted_attributes": valid_attributes,
                "confidence": confidence,
                "category_changed": bool(
                    data.get("category_changed", False)
                ),
                "method": "comprehensive_llm"
            }

        except json.JSONDecodeError as e:
            logger.error(
                f"[❌ DEBUG] JSON Parse Error: {str(e)}"
            )
            logger.error(
                f"[❌ DEBUG] Response text was: {response_text}"
            )

            return {
                "merged_intent": merged_intent,
                "category": "",
                "extracted_attributes": [],
                "confidence": 0.0,
                "category_changed": False,
                "method": "comprehensive_llm"
            }

        except Exception as e:
            logger.error(
                f"[❌ DEBUG] Unexpected error: {str(e)}",
                exc_info=True
            )

            return {
                "merged_intent": merged_intent,
                "category": "",
                "extracted_attributes": [],
                "confidence": 0.0,
                "category_changed": False,
                "method": "comprehensive_llm"
            }
    
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
        
        # STEP 0: ✅ ANALYZE INTENT - Use intent_type from analyze_processor (NO LLM re-call)
        logger.info(f"\n[Orchestrator] Processing user intent from: '{user_input}'")
        
        # 🆕 intent_type always available from analyze_processor (either map_intent or reconstruct_intent)
        intent_type_from_state = conversation_state.get("detected_intent", {}).get("intent_type", "specific")
        logger.info(f"[Orchestrator] ✅ Using intent_type from analyze_processor")
        logger.info(f"  - Intent Type: {intent_type_from_state}")
        
        # Create intent_result with intent_type for classify_request_case
        intent_result = {
            "intent": user_input,
            "intent_type": intent_type_from_state,
            "categories": [],
            "product_name": user_input,
            "confidence": 0.9 if intent_type_from_state == "specific" else 0.7,
            "method": "from_analyze_processor"
        }
        
        conversation_state["detected_intent"] = intent_result
        conversation_state["last_user_input"] = user_input  # Track for intent shift detection
            
        # STEP 1: Classify request into one of 2 cases
        case_info = self.classify_request_case(conversation_state)
        
        #logger.info(f"\n{'='*80}")
        #logger.info(f"CASE {case_info['case']}: {case_info['case_name']}")
        #logger.info(f"Reason: {case_info['reason']}")
        #logger.info(f"{'='*80}\n")
        
        # STEP 2: Route to appropriate handler
        handlers = {
            1: self.handle_case_1_clear_request,
            4: self.handle_case_4_abstract_intent
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
    

    def _normalize_product(self, product: dict) -> dict:
        if "title" in product and "name" not in product:
            product["name"] = product["title"]
        return product
    
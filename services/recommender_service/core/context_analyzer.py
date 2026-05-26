# app/core/context_analyzer.py
import json
import re
import logging
from typing import Dict, Any, Tuple
from .llm_utils import call_openai  # ✅ LOCAL

logger = logging.getLogger("context_analyzer")

# ═════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE - Rule-based layer (dùng để kiểm tra trước LLM)
# ═════════════════════════════════════════════════════════════════════════

# Known attributes và patterns
KNOWN_BRANDS = {
    'nike', 'adidas', 'puma', 'reebok', 'converse', 'vans',  # shoes
    'samsung', 'apple', 'xiaomi', 'oppo', 'vivo', 'nokia',   # phones
    'canon', 'nikon', 'sony', 'fujifilm',                    # cameras
    'lg', 'panasonic', 'bosch', 'philips', 'electrolux',     # appliances
    'gucci', 'louis vuitton', 'dior', 'chanel',              # luxury
}

KNOWN_COLORS = {
    'đen', 'trắng', 'xanh', 'đỏ', 'vàng', 'tím', 'cam', 'hồng',
    'xám', 'nâu', 'beige', 'navy', 'gold', 'silver', 'rose',
}

KNOWN_SIZES = {
    '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46',  # shoes
    'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl',                               # clothes
    '4gb', '6gb', '8gb', '12gb', '16gb', '32gb', '64gb', '128gb', '256gb',  # storage
}

KNOWN_PRICE_PATTERNS = [
    'dưới', 'trên', 'từ', 'đến', 'triệu', 'nghìn',
    'rẻ', 'mắc', 'giá rẻ', 'giá mắc',
]

# Simple category mapping
KNOWN_CATEGORIES = {
    'giày': 'shoe',
    'giày thể thao': 'shoe',
    'áo': 'clothing',
    'áo thun': 'clothing',
    'áo sơ mi': 'clothing',
    'điện thoại': 'phone',
    'máy tính': 'computer',
    'bột giặt': 'detergent',
    'sơ mi': 'clothing',
    'quần': 'clothing',
    'tai nghe': 'headphones',
    'tai nghe bluetooth': 'headphones',
    'đồng hồ': 'watch',
    'máy lọc không khí': 'air_purifier',
    'robot hút bụi': 'robot_vacuum',
    'nồi chiên không dầu': 'air_fryer',
    'máy pha cà phê': 'coffee_maker',
    'bàn phím cơ': 'mechanical_keyboard',
    'kem chống nắng': 'sunscreen',
    'sữa rửa mặt': 'facial_cleanser',
    'ghế gaming': 'gaming_chair',
    'ghế công thái học': 'ergonomic_chair',
    'ipad': 'tablet',
    'laptop gaming': 'gaming_laptop',
}

class ContextAnalyzer:
    
    def reconstruct_intent(
        self, 
        user_input: str, 
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        search_history = conversation_state.get("search_history", [])
        current_category = conversation_state.get("category")
        current_extracted = conversation_state.get("extracted", {})
        
        logger.info(f"[ContextAnalyzer] 📋 Input: '{user_input}' | History: {search_history} | Category: {current_category}")
        logger.info(f"[ContextAnalyzer] 🧠 Using LLM (rules disabled)")
        
        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 3: LLM-based reconstruction
        # ═══════════════════════════════════════════════════════════════════════
        prompt = self._build_reconstruction_prompt(
            user_input=user_input,
            search_history=search_history,
            current_category=current_category,
            current_extracted=current_extracted
        )
        
        try:
            response = call_openai(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=3000
            )
            
            # call_openai() already returns the string content directly
            if response is None:
                logger.warning("[ContextAnalyzer] OpenAI returned None, using fallback")
                response_text = ""
            else:
                response_text = response.strip()
            
            # 🔍 Parse JSON response from LLM
            result = self._parse_llm_response(response_text)
            
            # ═══════════════════════════════════════════════════════════════════════
            # LAYER 4: Post-validation (chặn hallucination)
            # ═══════════════════════════════════════════════════════════════════════
            validated_result = self._post_validate(result, user_input, current_category)
            logger.info(f"[ContextAnalyzer] ✅ Final result: {validated_result}")
            return validated_result
        
        except Exception as e: 
            logger.error(f"[ContextAnalyzer] ⚠️ LLM Error: {e}")
            # Fallback: return unknown safely
            return {
                "intent": user_input,
                "category_changed": False,
                "new_category": None,
                "intent_type": "specific"
            }
    
    def _try_rule_based_merge(
        self, 
        user_input: str, 
        current_category: str, 
        current_extracted: dict
    ) -> Dict[str, Any] | None:
        """
        Try to handle merge using simple rules first.
        Returns None if uncertain → fallback to LLM.
        """
        input_lower = user_input.lower().strip()
        
        # 🎯 Case 1: Known brand (simple merge)
        if self._is_brand_only(user_input):
            brand = input_lower
            if brand in KNOWN_BRANDS and current_category:
                # Safe merge: category + brand
                intent = self._merge_brand_with_category(current_category, brand)
                logger.info(f"[Rule] ✅ Known brand '{brand}' + category '{current_category}' → '{intent}'")
                return {
                    "intent": intent,
                    "category_changed": False,
                    "new_category": None
                }
        
        # 🎯 Case 2: Known color/size/price (simple refinement)
        category_type = self._classify_input(user_input)
        if category_type in ['color', 'size', 'price'] and current_category:
            # Build intent: category + previously extracted attributes + current input
            # Example: "Giày" + {brand: "nike"} + "màu đỏ thôi" → "Giày nike màu đỏ thôi"
            parts = [current_category]
            
            # 1. Add previously extracted brand (if exists)
            if current_extracted.get('brand'):
                parts.append(current_extracted['brand'])
            
            # 2. Add new attribute (color/size/price)
            parts.append(user_input)
            
            intent = " ".join(parts).strip()
            logger.info(f"[Rule] ✅ {category_type.upper()} refinement: Category='{current_category}' + Brand='{current_extracted.get('brand')}' + Input='{user_input}' → '{intent}'")
            return {
                "intent": intent,
                "category_changed": False,
                "new_category": None
            }
        
        # Uncertain → use LLM
        return None
    
    def _should_use_llm(self, user_input: str, current_category: str) -> bool:
        """
        Decide: should we call LLM or handle by rule?
        
        Return False: easy case → skip LLM
        Return True: complex case → need LLM
        """
        input_lower = user_input.lower().strip()
        
        # Only call LLM if input truly UNKNOWN
        classification = self._classify_input(user_input)
        
        # Known attributes → already handled by rule layer
        if classification in ['brand', 'color', 'size', 'price', 'category']:
            return False
        
        # Unknown or ambiguous → need LLM
        return True
    
    def _classify_input(self, user_input: str) -> str:
        """
        Classify input into: 'brand', 'color', 'size', 'price', 'category', 'unknown'
        Support variations like: "màu đen", "đen nhám", "size L", etc.
        
        ⚠️ IMPORTANT: Use word-boundary matching to avoid false positives
        e.g., "durex" should NOT match 'l' in KNOWN_SIZES
        """
        input_lower = user_input.lower().strip()
        words = input_lower.split()
        
        # Brand (exact match)
        if input_lower in KNOWN_BRANDS:
            return 'brand'
        
        # Color (word-level: "màu đen" or "đen nhám")
        for color in KNOWN_COLORS:
            if color in words or color in input_lower:
                # Extra check: ensure it's a meaningful color context, not substring
                # For Vietnamese: "màu X" pattern or standalone
                if len(color) > 2 or f" {color} " in f" {input_lower} ":
                    return 'color'
        
        # Size (word-level: exact word match, not substring)
        for size in KNOWN_SIZES:
            if size in words:  # Exact word match
                return 'size'
        
        # Price (check patterns)
        if any(pattern in input_lower for pattern in KNOWN_PRICE_PATTERNS):
            return 'price'
        
        # Category (contains category word)
        if any(cat in input_lower for cat in KNOWN_CATEGORIES.keys()):
            return 'category'
        
        return 'unknown'
    
    def _is_brand_only(self, user_input: str) -> bool:
        """Check if input is just a brand name (no other attributes)"""
        input_lower = user_input.lower().strip()
        # Support multi-word brands: "louis vuitton", "nike jordan"
        return any(input_lower == brand for brand in KNOWN_BRANDS)
    
    def _merge_brand_with_category(self, category: str, brand: str, current_intent: str = None) -> str:
        """
        Merge brand with category naturally.
        If brand already exists in current_intent, replace it.
        """
        # If already has brand, replace it
        if current_intent and "hiệu" in current_intent:
            # Remove old brand: "giày nike màu đen" → "giày màu đen"
            parts = current_intent.split("hiệu")
            base = parts[0].strip()
            return f"{base} hiệu {brand}"
        
        # Otherwise append: "giày" + "adidas" → "giày hiệu adidas"
        return f"{category} hiệu {brand}"
    
    def _is_incompatible(self, category: str, brand: str) -> bool:
        """
        Check if category + brand combination is incompatible.
        Generic logic → easy to maintain + extend.
        """
        # Define incompatible pairs
        incompatible_pairs = {
            ('bột giặt', 'nike'),
            ('bột giặt', 'adidas'),
            ('bột giặt', 'puma'),
            ('bột giặt', 'canon'),
            # Add more as needed, or load from config/DB later
        }
        
        return (category.lower(), brand.lower()) in incompatible_pairs
    
    def _post_validate(
        self, 
        result: Dict[str, Any], 
        user_input: str,
        current_category: str
    ) -> Dict[str, Any]:
        """
        Post-validation layer: catch LLM hallucinations
        Generic patterns that work long-term.
        """
        intent = result.get("intent", "").lower()
        
        # 🚫 Pattern 1: Incompatible category + brand
        if result.get("category_changed") == False and current_category:
            category_lower = current_category.lower()
            # Check against all known brands
            for brand in KNOWN_BRANDS:
                if brand in intent and self._is_incompatible(category_lower, brand):
                    logger.warning(f"[Validate] ⚠️ Incompatible merge detected: '{category_lower}' + '{brand}'")
                    # Treat as category change
                    return {
                        "intent": brand,
                        "category_changed": True,
                        "new_category": brand
                    }
        
        # 🚫 Pattern 2: Unknown brand forced into context (CONSERVATIVE CHECK ONLY)
        # ⚠️ IMPORTANT: This check should be VERY conservative to avoid overriding valid LLM decisions
        input_lower = user_input.lower().strip()
        
        # ONLY override if ALL conditions met:
        # 1. Input is truly unknown (not a known brand, color, size, etc.)
        # 2. Input is a single short word (likely a brand/term)
        # 3. LLM said category_changed=False (merge)
        # 4. There's a current category context
        if (result.get("category_changed") == False 
            and current_category
            and input_lower not in KNOWN_BRANDS 
            and self._classify_input(user_input) == 'unknown'):
            
            # Only treat as category change if it looks like a standalone brand/term
            words = input_lower.split()
            if len(words) == 1 and 2 < len(input_lower) < 20:  # Realistic brand/term length
                # Soft warning, not override
                logger.warning(f"[Validate] ⚠️ Unknown term '{input_lower}' in category '{current_category}' (LLM merged but term is unknown)")
                # Trust LLM's decision (category_changed=False) - only log the uncertainty
                # Don't force override unless very confident
                # This preserves LLM's semantic understanding
        
        # ✅ Looks good
        return result
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM.
        
        Expected format:
        {
            "intent": "giày màu đen size 42",
            "category_changed": false,
            "new_category": null,
            "intent_type": "specific"
        }
        
        If parsing fails, fallback to extracting intent only.
        """
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            logger.info(f"[ContextAnalyzer] LLM JSON response: {data}")
            # Validate required fields
            if "intent" not in data:
                raise ValueError("Missing 'intent' field")
            
            category_changed = data.get("category_changed", False)
            new_category = data.get("new_category", None)
            
            # ⚠️ CRITICAL: Handle field name mismatch
            # Prompt outputs "query_type", but we expect "intent_type"
            # Try both names for compatibility
            intent_type = data.get("intent_type") or data.get("query_type")
            
            # Only infer if LLM didn't provide it (true fallback, not override)
            if not intent_type:
                logger.warning(f"[ContextAnalyzer] ⚠️ LLM did not provide intent_type/query_type, inferring from category_changed")
                intent_type = self._infer_intent_type(category_changed, new_category)
            
            # 🔧 NORMALIZE to lowercase to avoid case sensitivity issues downstream
            # LLM returns "SPECIFIC"/"ABSTRACT" but orchestrator expects "specific"/"abstract"
            intent_type = str(intent_type).strip().lower() if intent_type else "specific"
            
            return {
                "intent": data.get("intent", response_text).strip(),
                "category_changed": category_changed,
                "new_category": new_category,
                "intent_type": intent_type
            }
        
        except json.JSONDecodeError:
            logger.warning(f"[ContextAnalyzer] ⚠️ Failed to parse JSON, attempting text extraction")
            # Fallback: try to extract from malformed response
            try:
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    category_changed = data.get("category_changed", False)
                    new_category = data.get("new_category", None)
                    # ⚠️ CRITICAL: Handle field name mismatch (query_type vs intent_type)
                    intent_type = data.get("intent_type") or data.get("query_type")
                    if not intent_type:
                        logger.warning(f"[ContextAnalyzer] ⚠️ Fallback parse: inferring intent_type")
                        intent_type = self._infer_intent_type(category_changed, new_category)
                    
                    # 🔧 NORMALIZE to lowercase to avoid case sensitivity issues downstream
                    intent_type = str(intent_type).strip().lower() if intent_type else "specific"
                    
                    return {
                        "intent": data.get("intent", response_text).strip(),
                        "category_changed": category_changed,
                        "new_category": new_category,
                        "intent_type": intent_type
                    }
            except:
                pass
            
            # Last resort: treat entire response as intent
            logger.warning(f"[ContextAnalyzer] ⚠️ Using fallback: treating response as intent")
            return {
                "intent": response_text.strip(),
                "category_changed": False,
                "new_category": None,
                "intent_type": "specific"
            }
    
    def _infer_intent_type(self, category_changed: bool, new_category: str = None) -> str:
        """
        Infer intent_type (specific | abstract) from context.
        
        ⚠️ IMPORTANT: This is a FALLBACK ONLY when LLM doesn't provide classification.
        The logic here is imperfect because it cannot understand semantic meaning.
        
        Fallback logic:
        - If category_changed=True, assume user is exploring → "abstract"
        - Otherwise → "specific" (most common case)
        
        NOTE: This can produce wrong results (e.g., user switches from "áo" to "robot hút bụi")
        That switch is SPECIFIC, not ABSTRACT. But this function can't know that.
        Real classification should come from LLM's semantic analysis.
        """
        if category_changed:
            # Conservative fallback: category switch might indicate exploration
            # But this is NOT guaranteed (e.g., "áo" -> "robot hút bụi" is still SPECIFIC)
            logger.debug(f"[ContextAnalyzer] Fallback: category_changed=True, assuming abstract")
            return "abstract"
        
        # Default fallback: most intents are specific (user knows what they want)
        return "specific"
    
    def _infer_category_from_history(self, search_history: list) -> str:
        """
        Extract category from most recent search query.
        
        Example:
        - "điện thoại samsung 8gb ram" → "điện thoại"
        - "giày nike màu đen" → "giày"
        """
        if not search_history:
            return None
        
        # Get first word(s) of last query
        last_query = search_history[-1]
        words = last_query.split()
        
        # Usually category is first word
        return words[0] if words else None
    
    def _build_reconstruction_prompt(
        self,
        user_input: str,
        search_history: list,
        current_category: str,
        current_extracted: dict
    ) -> str:
        """Build the LLM prompt for intent reconstruction with JSON output"""
        
        # 📝 Use full query history (not just category)
        history_text = ", ".join([str(item) for item in search_history[-5:]]) if search_history else "(empty)"
        
        # 🏷️ Format extracted attributes
        extracted_text = ""
        if current_extracted:
            extracted_text = ", ".join([f"{k}={v}" for k, v in current_extracted.items()])
            extracted_text = f"\nAlready extracted: {extracted_text}"
        
        # 📌 Current category context - infer từ history nếu không có
        if current_category:
            category_text = f"Current category: {current_category}"
        else:
            inferred_cat = self._infer_category_from_history(search_history)
            if inferred_cat:
                category_text = f"Current category (inferred from history): {inferred_cat}"
            else:
                category_text = "Category: Unknown (first request)"
        
        prompt = f"""
You are a Vietnamese ecommerce conversational intent merger.

Your task:
Merge the latest user input with previous shopping context
to reconstruct the user's CURRENT shopping intent.

The system supports ONLY TWO intent types:

- SPECIFIC
- ABSTRACT

==================================================
CONVERSATION CONTEXT
==================================================

Search history:
[{history_text}]

{extracted_text}

{category_text}

==================================================
LATEST USER INPUT
==================================================

"{user_input}"

==================================================
CORE PRINCIPLE
==================================================

The MOST IMPORTANT rule:

If the reconstructed intent contains ANY purchasable
commercial product, product category, brand,
or ecommerce item,
the intent MUST be classified as SPECIFIC.

This rule has ABSOLUTE PRIORITY over:
- mood
- vibe
- lifestyle
- activity
- purpose
- personality
- aesthetic
- adjectives
- specs
- attributes

==================================================
SPECIFIC
==================================================

A reconstructed intent is SPECIFIC if it contains
ANY purchasable product entity.

Product entities include:
- product categories
- commercial goods
- electronics
- appliances
- fashion items
- beauty products
- furniture
- household items
- brands
- model names

IMPORTANT:
Product entities may contain MULTIPLE WORDS.

Examples:
- máy lọc không khí
- robot hút bụi
- nồi chiên không dầu
- máy pha cà phê
- bàn phím cơ
- kem chống nắng
- tai nghe bluetooth
- ghế công thái học

A SINGLE product entity is enough for SPECIFIC.

Examples:
- "giày"
- "laptop"
- "iphone"
- "xiaomi"
- "máy lọc không khí"

→ ALL are SPECIFIC.

Brands ALWAYS imply SPECIFIC.

Examples:
- nike
- adidas
- apple
- samsung
- xiaomi
- asus

Specs, purposes, adjectives, and attributes
DO NOT change SPECIFIC into ABSTRACT.

Examples:
- "laptop gaming"
- "tai nghe chống ồn"
- "máy lọc không khí phòng 30m2"
- "máy lọc không khí xiaomi hepa độ ồn thấp"
- "ghế gaming cho dân IT"

→ ALL remain SPECIFIC.

==================================================
ABSTRACT
==================================================

ABSTRACT applies ONLY IF:
- there is NO product entity
- NO product category
- NO brand
- NO ecommerce item

AND the intent expresses ONLY:
- mood
- emotion
- vibe
- lifestyle
- activity
- purpose
- personality
- gift intent
- aesthetic

Examples:
- "tôi đang stress"
- "cute"
- "minimalist"
- "gaming"
- "vibe hàn quốc"
- "quà cho bạn gái"
- "để học online"

==================================================
INTENT MERGING RULES
==================================================

The latest user input may:

1. refine previous intent
2. add attributes/specs
3. switch product category
4. switch into abstract discovery intent

--------------------------------------------------
REFINEMENT
--------------------------------------------------

If the latest input logically modifies or extends
the previous product search,
merge them together.

Examples:

History: "áo nam"
Input: "đen"

→ merged:
"áo nam màu đen"

--------------------------------------------------

History: "laptop"
Input: "gaming"

→ merged:
"laptop gaming"

--------------------------------------------------

History: "máy lọc không khí"
Input: "xiaomi phòng 30m2"

→ merged:
"máy lọc không khí xiaomi phòng 30m2"

--------------------------------------------------
CATEGORY SWITCH
--------------------------------------------------

If the latest input introduces a completely different
product/topic unrelated to the previous one,
replace the old intent.

Examples:

History: "áo nam"
Input: "robot hút bụi"

→ new intent:
"robot hút bụi"

--------------------------------------------------

History: "laptop gaming"
Input: "kem chống nắng"

→ new intent:
"kem chống nắng"

--------------------------------------------------
ABSTRACT SWITCH
--------------------------------------------------

If the latest input contains NO product entity
and clearly expresses mood/lifestyle/emotion/purpose,
switch to ABSTRACT.

Examples:

History: "áo nam"
Input: "tôi đang stress"

→ ABSTRACT

--------------------------------------------------

History: "laptop"
Input: "minimalist"

→ ABSTRACT

==================================================
CATEGORY CHANGE RULE
==================================================

category_changed = true ONLY IF:
- the user switches to a different product/topic
- OR switches from SPECIFIC ↔ ABSTRACT

category_changed = false IF:
- the latest input only refines/modifies existing intent

When uncertain:
prefer false.

==================================================
IMPORTANT EDGE CASES
==================================================

History: "máy lọc không khí"
Input: "xiaomi hepa độ ồn thấp"

Output:
{{
  "intent": "máy lọc không khí xiaomi hepa độ ồn thấp",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History: ""
Input: "máy lọc không khí xiaomi phòng 30m2"

Output:
{{
  "intent": "máy lọc không khí xiaomi phòng 30m2",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History: "laptop"
Input: "gaming"

Output:
{{
  "intent": "laptop gaming",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History: ""
Input: "gaming"

Output:
{{
  "intent": "người dùng muốn sản phẩm phục vụ gaming",
  "query_type": "ABSTRACT",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History: "áo nam"
Input: "robot hút bụi"

Output:
{{
  "intent": "robot hút bụi",
  "query_type": "SPECIFIC",
  "category_changed": true,
  "new_category": "robot hút bụi"
}}

==================================================
OUTPUT RULES
==================================================

Return ONLY valid JSON.

Do NOT output markdown.
Do NOT explain outside JSON.

Format:

{{
  "intent": "merged/reconstructed intent",
  "query_type": "SPECIFIC or ABSTRACT",
  "category_changed": true or false,
  "new_category": "new category if changed, else null"
}}
"""
        return prompt

    def detect_first_query_intent_type(self, user_input: str) -> str:
        """
        Detect intent_type for FIRST QUERY only (no conversation history needed).
        
        Returns:
        - "specific": User knows what product/category they want
        - "abstract": User is exploring ideas/purposes, doesn't know exact category
        
        Examples:
        - "tai nghe bluetooth không dây" → "specific" (knows category)
        - "tôi cần gì đó để nghe nhạc" → "abstract" (exploring)
        - "điện thoại samsung 256gb" → "specific" (knows category)
        - "tôi muốn thứ gì đó sang trọng" → "abstract" (exploring)
        """
        
        import json
        
        prompt = f"""
You are a Vietnamese ecommerce intent classifier.

Your task is to classify the user's FIRST query into EXACTLY ONE type:

- SPECIFIC
- ABSTRACT

==================================================
USER QUERY
==================================================

"{user_input}"

==================================================
CORE CLASSIFICATION PRINCIPLE
==================================================

The MOST IMPORTANT rule:

If the query refers to ANY purchasable commercial product,
product category, brand, or ecommerce item,
the query MUST be classified as SPECIFIC.

This rule has ABSOLUTE PRIORITY over:
- mood
- purpose
- activity
- lifestyle
- aesthetic
- personality
- adjectives
- specs
- attributes
- vague modifiers

==================================================
SPECIFIC
==================================================

A query is SPECIFIC if it contains ANY purchasable product entity.

A purchasable product entity includes:
- product categories
- commercial goods
- appliances
- electronics
- beauty products
- household items
- fashion items
- furniture
- brands
- model names

IMPORTANT:
Product entities may contain MULTIPLE WORDS.

Examples of multi-word product entities:
- máy lọc không khí
- robot hút bụi
- nồi chiên không dầu
- máy pha cà phê
- kem chống nắng
- sữa rửa mặt
- bàn phím cơ
- tai nghe bluetooth
- điện thoại gaming
- ghế công thái học

A SINGLE product entity is already enough for SPECIFIC.

Examples:
- "giày" → SPECIFIC
- "laptop" → SPECIFIC
- "iphone" → SPECIFIC
- "xiaomi" → SPECIFIC
- "máy lọc không khí" → SPECIFIC

Brands ALWAYS imply SPECIFIC.

Examples:
- nike
- adidas
- apple
- samsung
- xiaomi
- asus
- oppo

Specs, attributes, purposes, and adjectives
DO NOT change SPECIFIC into ABSTRACT.

Examples:
- "laptop gaming" → SPECIFIC
- "tai nghe chống ồn" → SPECIFIC
- "máy lọc không khí phòng 30m2" → SPECIFIC
- "máy lọc không khí xiaomi hepa độ ồn thấp" → SPECIFIC
- "robot hút bụi lau nhà" → SPECIFIC
- "ipad ram 8gb 128gb" → SPECIFIC
- "ghế gaming cho dân IT" → SPECIFIC
- "đèn ngủ chill" → SPECIFIC

==================================================
ABSTRACT
==================================================

A query is ABSTRACT ONLY IF:
- it contains ZERO purchasable product entities
- ZERO brands
- ZERO product categories
- ZERO ecommerce goods

AND the query expresses ONLY:
- mood
- emotion
- vibe
- lifestyle
- purpose
- activity
- aesthetic
- personality
- gift intent

ABSTRACT examples:
- "tôi đang stress"
- "cute"
- "minimalist"
- "gaming"
- "vibe hàn quốc"
- "quà cho bạn gái"
- "cho dân IT"
- "để học online"
- "đồ chill chill"

==================================================
IMPORTANT EDGE CASES
==================================================

Input:
"máy lọc không khí xiaomi phòng 30m2 hepa độ ồn thấp"

Output:
{{
  "intent_type": "SPECIFIC",
  "reasoning": "Contains purchasable product entity: máy lọc không khí and brand: xiaomi."
}}

--------------------------------------------------

Input:
"robot hút bụi cho nhà nhỏ"

Output:
{{
  "intent_type": "SPECIFIC",
  "reasoning": "Contains purchasable product entity: robot hút bụi."
}}

--------------------------------------------------

Input:
"gaming"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Activity only. No purchasable product entity."
}}

--------------------------------------------------

Input:
"tôi đang stress"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Emotion only. No purchasable product entity."
}}

==================================================
DECISION PROCESS
==================================================

STEP 1:
Detect whether the query contains ANY purchasable product entity,
brand, product category, or ecommerce item.

If YES:
Return SPECIFIC immediately.

STEP 2:
Only if NO product entity exists,
check whether the query is purely emotional,
lifestyle-based, aesthetic, activity-based,
or purpose-only.

If YES:
Return ABSTRACT.

==================================================
OUTPUT RULES
==================================================

Return ONLY valid JSON.

Do NOT output markdown.
Do NOT explain outside JSON.

Format:

{{
  "intent_type": "SPECIFIC or ABSTRACT",
  "reasoning": "brief explanation"
}}
"""
        try:
            response = call_openai(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=1000
            )
            
            if not response:
                logger.warning("[ContextAnalyzer] Empty LLM response for first query intent")
                return "specific"  # Default fallback
            
            response_text = response.strip()
            
            # Remove markdown if present
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\n", "", response_text)
                response_text = re.sub(r"\n```$", "", response_text)
            
            data = json.loads(response_text)
            intent_type = data.get("intent_type", "specific").lower()
            
            # Normalize to "specific" or "abstract"
            if "abstract" in intent_type:
                return "abstract"
            else:
                return "specific"
                
        except json.JSONDecodeError as e:
            logger.warning(f"[ContextAnalyzer] JSON parse error: {e}")
            return "specific"
        except Exception as e:
            logger.warning(f"[ContextAnalyzer] Error detecting first query intent: {e}")
            return "specific"


_analyzer = None

def get_context_analyzer() -> ContextAnalyzer:
    """Get context analyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ContextAnalyzer()
    return _analyzer


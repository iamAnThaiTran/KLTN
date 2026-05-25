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
    'điện thoại': 'phone',
    'máy tính': 'computer',
    'bột giặt': 'detergent',
    'sơ mi': 'clothing',
    'quần': 'clothing',
    'tai nghe': 'headphones',
    'đồng hồ': 'watch',
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
                max_tokens=300
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
        
        # 🚫 Pattern 2: Unknown brand forced into context
        # If we're unsure → prefer treating as category change (safer)
        input_lower = user_input.lower().strip()
        if input_lower not in KNOWN_BRANDS and self._classify_input(user_input) == 'unknown':
            # Input is unknown and small → might be new brand or category
            # Be conservative: treat as potential category change
            if result.get("category_changed") == False and current_category:
                logger.warning(f"[Validate] ⚠️ Unknown term '{input_lower}' merged with '{current_category}'")
                # Check if it should be category change instead
                if len(input_lower.split()) == 1 and len(input_lower) > 2:
                    # Looks like new brand/term → mark as category change
                    return {
                        "intent": user_input,
                        "category_changed": True,
                        "new_category": user_input
                    }
        
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
            
            # Validate required fields
            if "intent" not in data:
                raise ValueError("Missing 'intent' field")
            
            category_changed = data.get("category_changed", False)
            new_category = data.get("new_category", None)
            
            # Infer intent_type if not provided by LLM
            intent_type = data.get("intent_type") or self._infer_intent_type(category_changed, new_category)
            
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
                    intent_type = data.get("intent_type") or self._infer_intent_type(category_changed, new_category)
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
        
        Logic:
        - If category_changed=True → "abstract" (user is exploring new category)
        - If category_changed=False → "specific" (user refining current category)
        """
        if category_changed:
            return "abstract"  # User exploring new category
        return "specific"  # User refining current category
    
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
You are a Vietnamese ecommerce shopping intent analyzer.

Your job:
Reconstruct the user's shopping intent using:
- previous conversation context
- latest user input

The system supports ONLY TWO query types:

- SPECIFIC
- ABSTRACT

==================================================
CONVERSATION STATE
==================================================

Search history:
[{history_text}]

{extracted_text}

{category_text}

==================================================
NEW USER INPUT
==================================================

"{user_input}"

==================================================
CORE DEFINITIONS
==================================================

--------------------------------------------------
SPECIFIC
--------------------------------------------------

A query is SPECIFIC ONLY IF it contains
a CONCRETE PURCHASABLE PRODUCT ENTITY.

This includes:
- products
- product categories
- brands
- concrete ecommerce items

Examples:
- laptop
- tai nghe
- iphone
- áo nam
- nike
- bàn học
- ghế gaming
- đèn ngủ

IMPORTANT:
Broad shopping queries are STILL SPECIFIC
IF they contain a product noun.

Examples:
- "áo cute"
- "tai nghe gaming"
- "đèn ngủ chill"
- "ghế công thái học"

--------------------------------------------------
ABSTRACT
--------------------------------------------------

A query is ABSTRACT IF:
- it does NOT contain a concrete product/category/brand
AND
- it expresses:
  - emotion
  - mood
  - vibe
  - lifestyle
  - purpose
  - personality
  - aesthetic
  - gift intent
  - exploratory shopping intent

Examples:
- "tôi đang stress"
- "quà cho bạn gái"
- "minimalist"
- "cho dân IT"
- "để học online"
- "vibe hàn quốc"

==================================================
CRITICAL HARD RULES
==================================================

1. Emotions are NOT products.

NOT purchasable:
- stress
- chill
- productive
- thư giãn

--------------------------------------------------

2. Activities are NOT products.

Examples:
- gaming
- đi học
- đi làm
- camping

These are ABSTRACT
unless product noun exists.

--------------------------------------------------

3. Aesthetics/adjectives are NOT products.

Examples:
- cute
- pastel
- minimalist
- vintage

These are ABSTRACT
unless product noun exists.

--------------------------------------------------

4. Purpose is NOT product.

Examples:
- để học online
- để ngủ ngon
- để thư giãn

These are ABSTRACT
unless product noun exists.

==================================================
CONVERSATION RECONSTRUCTION RULES
==================================================

The latest input may:

1. refine previous search
OR
2. switch to another category
OR
3. switch into ABSTRACT discovery intent

--------------------------------------------------
Examples:
--------------------------------------------------

History:
"áo nam"

Input:
"đen"

→ refine previous search

Output:
{{
  "intent": "áo nam màu đen",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History:
"áo nam"

Input:
"nike"

→ refine previous search

Output:
{{
  "intent": "áo nam nike",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History:
"áo nam"

Input:
"bột giặt"

→ new category

Output:
{{
  "intent": "bột giặt",
  "query_type": "SPECIFIC",
  "category_changed": true,
  "new_category": "bột giặt"
}}

--------------------------------------------------

History:
"áo nam"

Input:
"tôi đang stress"

→ switch into abstract discovery

Output:
{{
  "intent": "người dùng muốn giảm stress",
  "query_type": "ABSTRACT",
  "category_changed": true,
  "new_category": null
}}

--------------------------------------------------

History:
"áo"

Input:
"cute"

→ refine existing product

Output:
{{
  "intent": "áo cute",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History:
""

Input:
"cute"

→ no product noun exists

Output:
{{
  "intent": "người dùng muốn phong cách dễ thương",
  "query_type": "ABSTRACT",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History:
"laptop"

Input:
"gaming"

→ refine existing product

Output:
{{
  "intent": "laptop gaming",
  "query_type": "SPECIFIC",
  "category_changed": false,
  "new_category": null
}}

--------------------------------------------------

History:
""

Input:
"gaming"

→ no product noun

Output:
{{
  "intent": "người dùng muốn sản phẩm phục vụ gaming",
  "query_type": "ABSTRACT",
  "category_changed": false,
  "new_category": null
}}

==================================================
DECISION PROCESS
==================================================

STEP 1:
Check whether the FINAL reconstructed intent
contains a concrete product noun.

IF YES:
→ SPECIFIC

IF NO:
→ ABSTRACT

==================================================
CATEGORY CHANGE RULES
==================================================

category_changed refers ONLY to conversation flow.

Examples:
- áo → đen
  = false

- laptop → gaming
  = false

- áo → bột giặt
  = true

- laptop → tôi đang stress
  = true

When uncertain:
prefer category_changed=true.

==================================================
OUTPUT RULES
==================================================

Return ONLY valid JSON.

Required format:

{{
  "intent": "reconstructed intent",
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
You are a Vietnamese ecommerce shopping intent classifier.

Your task:
Classify the user's FIRST shopping query into ONLY ONE type:

- SPECIFIC
- ABSTRACT

==================================================
USER QUERY
==================================================

"{user_input}"

==================================================
CORE DEFINITIONS
==================================================

--------------------------------------------------
SPECIFIC
--------------------------------------------------

A query is SPECIFIC ONLY IF it contains
a CONCRETE PURCHASABLE PRODUCT ENTITY.

This includes:
- products
- product categories
- brands
- concrete ecommerce items

Examples:
- "laptop"
- "tai nghe"
- "iphone"
- "áo nam"
- "máy giặt"
- "nike"
- "airpods"
- "bàn học"
- "đèn ngủ"

IMPORTANT:
Broad shopping queries are STILL SPECIFIC
IF they contain a concrete product noun.

Examples:
- "áo cute"
- "đèn ngủ chill"
- "bàn học tối giản"
- "tai nghe gaming"

--------------------------------------------------
ABSTRACT
--------------------------------------------------

A query is ABSTRACT IF:
- it does NOT contain a concrete product/category/brand
AND
- it expresses:
  - emotion
  - mood
  - vibe
  - lifestyle
  - purpose
  - personality
  - aesthetic
  - gift intent
  - exploratory shopping intent

Examples:
- "tôi đang stress"
- "minimalist"
- "vibe hàn quốc"
- "quà cho bạn gái"
- "đồ gì đó chill chill"
- "cho dân IT"
- "để học online"

==================================================
CRITICAL HARD RULES
==================================================

1. Emotions are NOT products.

These are NOT purchasable entities:
- stress
- chill
- productive
- cute
- sang trọng
- minimalist
- vintage
- gaming
- học tập
- thư giãn

--------------------------------------------------

2. Activities are NOT products.

Examples:
- đi học
- đi làm
- đi biển
- gaming
- camping

These are ABSTRACT
UNLESS a concrete product noun exists.

--------------------------------------------------

3. Adjectives/aesthetics are NOT products.

Examples:
- cute
- basic
- vintage
- pastel
- minimalist

These are ABSTRACT
UNLESS a concrete product noun exists.

--------------------------------------------------

4. Purpose is NOT product.

Examples:
- để học online
- để thư giãn
- để ngủ ngon

These are ABSTRACT
UNLESS a product noun exists.

--------------------------------------------------

5. Brand-only queries are SPECIFIC.

Examples:
- nike
- adidas
- apple
- samsung

==================================================
DECISION PROCESS
==================================================

STEP 1:
Check whether the query contains a concrete purchasable product entity.

IF YES:
→ SPECIFIC

IF NO:
→ continue.

--------------------------------------------------

STEP 2:
Check whether the query expresses:
- emotion
- vibe
- lifestyle
- purpose
- gift intent
- personality
- aesthetic
without concrete product noun.

IF YES:
→ ABSTRACT

==================================================
EDGE CASE EXAMPLES
==================================================

Input:
"tôi đang stress quá"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Emotional intent without concrete product."
}}

--------------------------------------------------

Input:
"gaming"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Activity intent without product noun."
}}

--------------------------------------------------

Input:
"cute"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Aesthetic adjective without product noun."
}}

--------------------------------------------------

Input:
"để học online"

Output:
{{
  "intent_type": "ABSTRACT",
  "reasoning": "Purpose intent without concrete product."
}}

--------------------------------------------------

Input:
"laptop gaming"

Output:
{{
  "intent_type": "SPECIFIC",
  "reasoning": "Contains concrete product noun."
}}

--------------------------------------------------

Input:
"đèn ngủ cute"

Output:
{{
  "intent_type": "SPECIFIC",
  "reasoning": "Contains concrete product noun."
}}

--------------------------------------------------

Input:
"nike"

Output:
{{
  "intent_type": "SPECIFIC",
  "reasoning": "Brand is searchable ecommerce entity."
}}

==================================================
OUTPUT RULES
==================================================

Return ONLY valid JSON.

Format:

{{
  "intent_type": "SPECIFIC or ABSTRACT",
  "reasoning": "brief explanation"
}}
"""
        try:
            response = call_openai(
                prompt,
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=100
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


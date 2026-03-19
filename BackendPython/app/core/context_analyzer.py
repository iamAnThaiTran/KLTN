# app/core/context_analyzer.py
import json
import re
import logging
from typing import Dict, Any, Tuple
from app.core.llm_utils import call_openai

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
        
        # Nếu không có lịch sử, trả về input gốc
        if not search_history and not current_category:
            return {
                "intent": user_input,
                "category_changed": False,
                "new_category": None
            }
        
        logger.info(f"[ContextAnalyzer] 📋 Input: '{user_input}' | History: {search_history} | Category: {current_category}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 1: Rule-based detection (trước LLM)
        # ═══════════════════════════════════════════════════════════════════════
        rule_result = self._try_rule_based_merge(
            user_input=user_input,
            current_category=current_category,
            current_extracted=current_extracted
        )
        
        if rule_result:
            logger.info(f"[ContextAnalyzer] ✅ Rule-based result: {rule_result}")
            return rule_result
        
        # ═══════════════════════════════════════════════════════════════════════
        # LAYER 2: Decision layer - có nên dùng LLM không?
        # ═══════════════════════════════════════════════════════════════════════
        should_use_llm = self._should_use_llm(user_input, current_category)
        
        if not should_use_llm:
            logger.info(f"[ContextAnalyzer] 📌 No LLM needed, returning as-is")
            return {
                "intent": user_input,
                "category_changed": False,
                "new_category": None
            }
        
        logger.info(f"[ContextAnalyzer] 🧠 Using LLM for complex case")
        
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
                raise Exception("OpenAI returned None")
            
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
                "new_category": None
            }
    
    # ═════════════════════════════════════════════════════════════════════════
    # HELPER METHODS - Decision Layer & Validation
    # ═════════════════════════════════════════════════════════════════════════
    
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
            # Simple append
            intent = f"{current_category} {user_input}".strip()
            logger.info(f"[Rule] ✅ {category_type.upper()} refinement: '{intent}'")
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
            "new_category": null
        }
        
        If parsing fails, fallback to extracting intent only.
        """
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            
            # Validate required fields
            if "intent" not in data:
                raise ValueError("Missing 'intent' field")
            
            return {
                "intent": data.get("intent", response_text).strip(),
                "category_changed": data.get("category_changed", False),
                "new_category": data.get("new_category", None)
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
                    return {
                        "intent": data.get("intent", response_text).strip(),
                        "category_changed": data.get("category_changed", False),
                        "new_category": data.get("new_category", None)
                    }
            except:
                pass
            
            # Last resort: treat entire response as intent
            logger.warning(f"[ContextAnalyzer] ⚠️ Using fallback: treating response as intent")
            return {
                "intent": response_text.strip(),
                "category_changed": False,
                "new_category": None
            }
    
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
        
        prompt = f"""You are a Vietnamese shopping assistant reconstructing user intent.
IMPORTANT: This is a RULE-FIRST system. Prioritize safety over aggressive merging.

CONVERSATION STATE:
- Search history (previous queries): [{history_text}]{extracted_text}
- {category_text}

NEW USER INPUT: "{user_input}"

TASK: Reconstruct the complete user intent based on conversation history + new input.

GUIDELINES (prioritize certainty):
1. IDENTIFY INPUT TYPE:
   - CATEGORY: Completely different product (e.g., "áo thun", "điện thoại", "bột giặt")
   - ATTRIBUTE: Specification (brand, color, size, price, etc.)
   - UNKNOWN: New term you don't recognize

2. If ATTRIBUTE (color, size, price—safe to merge):
   Example 1: History="giày nike", Input="màu đen" → intent="giày nike màu đen"
   Example 2: History="giày", Input="size 42" → intent="giày size 42"

3. If BRAND:
   Example 1: History="giày", Input="adidas" → intent="giày hiệu adidas"
   Example 2: History="điện thoại", Input="samsung" → intent="điện thoại samsung"
   
   ⚠️ BUT: If brand seems incompatible with category (e.g., shoe brand + detergent):
   → Mark as CATEGORY CHANGE instead
   Example: History="bột giặt", Input="adidas" → category_changed=true, new_category="adidas"

4. If input is UNKNOWN (can't classify):
   → When uncertain, prefer CATEGORY CHANGE over forced merge
   Example 1: History="giày", Input="xyz123" → category_changed=true, new_category="xyz123"
   Example 2: History="bột giặt", Input="unknown_brand" → category_changed=true

5. If new input is clearly DIFFERENT CATEGORY:
   Example: History="giày nike", Input="bột giặt" → category_changed=true, new_category="bột giặt"

6. Create NATURAL queries:
   - Merge logically respecting Vietnamese grammar
   - When uncertain, treat as category change (safer)
   - Don't force incompatible merges

RESPONSE FORMAT: Return ONLY valid JSON, no other text:
{
  "intent": "reconstructed user intent string",
  "category_changed": true or false,
  "new_category": "new category if changed, else null"
}

Examples:
{"intent": "giày nike màu đen size 42", "category_changed": false, "new_category": null}
{"intent": "samsung", "category_changed": true, "new_category": "samsung"}
{"intent": "bột giặt", "category_changed": true, "new_category": "bột giặt"}

✅ Default to safety: when uncertain → category_changed=true
"""
        return prompt


_analyzer = None

def get_context_analyzer() -> ContextAnalyzer:
    """Get context analyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ContextAnalyzer()
    return _analyzer


# app/core/intent_mapper.py

from typing import List, Dict, Any
import re
import os
from dotenv import load_dotenv
from .llm_utils import call_openai
import logging

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

class IntentMapper:
    """
    Map usage intent → categories
    Ví dụ: "để giải khát" → ["nước", "nước ngọt", "cà phê"]
    """
    
    def __init__(self):
        self.intent_patterns = {
            # Pattern: (regex, categories)
            # Gift intent (hardcoded)
            r"quà cho bạn gái|tặng bạn gái|mua cho bạn gái": [
                "quần áo", "giày", "phụ kiện", "mỹ phẩm", "nước hoa", "túi xách", "dây chuyền"
            ],
            r"quà cho bạn trai|tặng bạn trai|mua cho bạn trai": [
                "quần áo", "giày", "phụ kiện", "dụng cụ", "công nghệ"
            ],
            r"quà tặng|quà|tặng|sinh nhật": ["quà tặng"],
            
            # Utility intents
            r"để giải khát|giải nước|uống": ["nước", "nước ngọt", "cà phê", "trà"],
            r"để mặc|mặc|quần|áo|trang phục": ["quần áo", "giày", "phụ kiện"],
            r"để tránh thai|tránh thai": ["thuốc tránh thai", "bao cao su"],
            r"để làm đẹp|làm đẹp|skincare|mỹ phẩm": ["mỹ phẩm", "skincare", "trang điểm"],
            r"để chơi game|chơi game|gaming": ["máy tính", "console", "monitor", "bàn phím"],
            r"để đi chơi|đi chơi|du lịch": ["quần áo", "giày", "ba lô", "túi xách"],
            r"để tập thể dục|tập gym|tập yoga": ["giày", "quần áo", "dụng cụ tập"],
            r"để nấu ăn|nấu ăn|nấu": ["nồi", "chảo", "dao", "cốc"],
            r"để học|học tập|sách": ["sách", "bút", "vở", "máy tính"],
            r"để ngủ|nệm|gối|chăn": ["nệm", "gối", "chăn", "ga trải giường"],
            
            # Cleaning products (NEW)
            r"bột giặt|giặt quần áo|nước xả|xà phòng giặt": ["bột giặt"],
            r"nước lau nhà|lau nhà|dọn nhà|vệ sinh": ["nước lau nhà"],
            r"xà phòng|xà bông": ["xà phòng"],
        }
        
        # Available categories (for LLM to map to)
        self.available_categories = [
            "quần áo", "giày", "phụ kiện", "mỹ phẩm", "nước hoa", "túi xách", "dây chuyền",
            "dụng cụ", "công nghệ", "quà tặng", "nước", "nước ngọt", "cà phê", "trà",
            "thuốc tránh thai", "bao cao su", "skincare", "trang điểm", "máy tính", "console", 
            "monitor", "bàn phím", "ba lô", "dụng cụ tập", "nồi", "chảo", "dao", "cốc",
            "sách", "bút", "vở", "nệm", "gối", "chăn", "ga trải giường",
            "bột giặt", "nước lau nhà", "xà phòng", "sản phẩm vệ sinh"  # ← ADD categories
        ]
        
        # LLM fallback enabled (set False to disable)
        self.enable_llm_fallback = True
    
    def map_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Detect usage intent từ user input
        
        Step 1: Try pattern matching (fast, regex)
        Step 2: If no match, try LLM semantic understanding (smart fallback)
        
        Returns:
            {
                "intent": str (usage intent, e.g., "gift for girlfriend"),
                "intent_type": str (specific | abstract | comparison | none),
                "categories": [cat1, cat2, ...],
                "confidence": float,
                "method": "pattern" | "llm" | "none"
            }
        """
        user_input_lower = user_input.lower()
        logger.info(f"Mapping intent for user input: '{user_input}'")
        
        # ===== STEP 1: Try pattern matching (FAST) =====
        for pattern, categories in self.intent_patterns.items():
            if re.search(pattern, user_input_lower):
                # Extract intent từ pattern
                intent_match = re.search(pattern, user_input_lower)
                intent = intent_match.group(0) if intent_match else pattern
                
                # Infer intent_type from pattern
                intent_type = self._infer_intent_type(intent, categories)
                
                return {
                    "intent": intent,
                    "intent_type": intent_type,
                    "categories": categories,
                    "confidence": 0.9,
                    "method": "pattern"
                }
        
        # ===== STEP 2: Pattern not matched → Try LLM fallback (SMART) =====
        if self.enable_llm_fallback and os.getenv("OPENAI_API_KEY"):
            logger.info(f"DEBUG: Pattern matching failed, trying LLM...")
            try:
                llm_result = self._map_intent_with_llm(user_input)
                if llm_result["intent"] and llm_result["categories"]:
                    logger.info(f"DEBUG: LLM mapped - {llm_result['intent']} → {llm_result['categories']}")
                    return llm_result
            except Exception as e:
                logger.info(f"DEBUG: LLM fallback failed: {e}")
                # Fall through to no-match case
        
        # ===== STEP 3: No match (pattern or LLM) =====
        return {
            "intent": None,
            "intent_type": "none",
            "categories": [],
            "confidence": 0.0,
            "method": "none"
        }
    
    def _infer_intent_type(self, intent: str, categories: List[str]) -> str:
        """
        Infer intent_type (specific | abstract | comparison | none)
        from intent string and categories
        
        PRIORITY ORDER:
        1. If comparison keywords → "comparison"
        2. If 1-2 categories (focused) → "specific"
        3. If 3+ categories OR abstract keywords → "abstract"
        4. Otherwise → "none"
        
        KEY INSIGHT: Multiple categories = scope explosion = abstract intent!
        Example: "mua quà cho bạn gái" → 7 gift categories = too many options = abstract
        """
        intent_lower = str(intent).lower()
        
        # ===== PRIORITY 1: COMPARISON intent =====
        if any(word in intent_lower for word in ["so sánh", "khác", "so", "compare", "vs"]):
            return "comparison"
        
        # ===== PRIORITY 2: SPECIFIC intent (1-2 focused categories) =====
        # If user mentioned specific product/category with narrow scope
        if categories and 1 <= len(categories) <= 2:
            return "specific"
        
        # ===== PRIORITY 3: ABSTRACT intent (3+ categories OR abstract keywords) =====
        # If scope exploded to multiple categories = user exploring many options = abstract
        # OR if abstract keywords present
        abstract_keywords = ["gì đó", "thứ", "cái", "để", "cho", "muốn", "cần"]
        
        if (categories and len(categories) >= 3) or any(word in intent_lower for word in abstract_keywords):
            return "abstract"
        
        # ===== FALLBACK: NONE =====
        return "none"
    
    def _map_intent_with_llm(self, user_input: str) -> Dict[str, Any]:
        """
        Use LLM (OpenAI) để semantic understand intent + map categories
        
        NEW: LLM can now suggest NEW categories if user input doesn't match available ones
        
        Example: "bột giặt" → LLM suggests creating new category "bột giặt" with attributes
                 instead of forcing to "dụng cụ"
        """
        # Get available category names
        categories_str = ", ".join(self.available_categories)
        
        prompt = f"""TASK: Analyze user's shopping request and classify as CLEAR or ABSTRACT, then map categories accordingly.

User input: "{user_input}"

Available categories: {categories_str}

CLASSIFICATION RULES:
===================

**CLEAR REQUEST (Specific):**
- User mentions EXACTLY 1 product category (e.g., "giày", "áo", "nước hoa")
- User input is SHORT and DIRECT (1-3 words)
- Action: Return ONLY 1 category with HIGH confidence (0.9-0.95)
- NOTE: If no available category matches, CREATE a NEW category specific to user needs!

**ABSTRACT REQUEST (Vague purpose):**
- User describes a PURPOSE/FEELING/NEED but NOT specific product (e.g., "tôi cần thứ ấm áp", "để tặng bạn gái")
- User input is LONG and DESCRIPTIVE (4+ words)
- User uses words like: "để", "cần", "muốn", "gì đó", "thứ"
- Action: Return MULTIPLE related categories (3-5) with MEDIUM confidence (0.6-0.7)

IMPORTANT RULES:
================
1. If user input EXACTLY MATCHES an available category → Use it
2. If user input is a SPECIFIC product NOT in available categories → CREATE NEW category!
   Example: "bột giặt" → NOT in available, so create category "bột giặt" (NEW)
   Example: "nước lau nhà" → NOT in available, so create category "nước lau nhà" (NEW)
3. If user input contains VAGUE keywords → Map to multiple available categories
4. OUTPUT ONLY valid JSON, nothing else

FORMAT:
{{
  "intent": "short description",
  "categories": ["cat1", "cat2"],  // Can be NEW categories!
  "is_new_category": false,        // NEW field: True if category was created, not from available list
  "clarity": "clear|abstract",
  "confidence": 0.9,
  "reasoning": "brief explanation"
}}

EXAMPLES:
=========
User: "giày" 
→ EXISTS in available categories
→ {{
    "intent": "purchase shoes",
    "categories": ["giày"],
    "is_new_category": false,
    "clarity": "clear",
    "confidence": 0.95,
    "reasoning": "Exact match with available 'giày'"
  }}

User: "bột giặt"
→ NOT in available categories, CREATE NEW
→ {{
    "intent": "purchase laundry detergent",
    "categories": ["bột giặt"],
    "is_new_category": true,
    "clarity": "clear",
    "confidence": 0.95,
    "reasoning": "User wants specific product 'bột giặt' (not in available), create new category"
  }}

User: "nước lau nhà"
→ NOT in available, CREATE NEW
→ {{
    "intent": "purchase floor cleaner",
    "categories": ["nước lau nhà"],
    "is_new_category": true,
    "clarity": "clear",
    "confidence": 0.90,
    "reasoning": "Specific product 'nước lau nhà' not in system, create new"
  }}

User: "tôi muốn gì đó ấm áp"
→ ABSTRACT, use available categories
→ {{
    "intent": "warmth/comfort",
    "categories": ["quần áo", "áo khoác", "nệm", "gối", "chăn"],
    "is_new_category": false,
    "clarity": "abstract",
    "confidence": 0.65,
    "reasoning": "Purpose-driven, map to existing categories"
  }}

User: "để tặng bạn gái"
→ ABSTRACT, use available categories
→ {{
    "intent": "gift for girlfriend",
    "categories": ["quần áo", "phụ kiện", "mỹ phẩm", "nước hoa"],
    "is_new_category": false,
    "clarity": "abstract",
    "confidence": 0.65,
    "reasoning": "Gift purpose, map to existing categories"
  }}
"""
        
        try:
            response = call_openai(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0.3  # Low temp for consistent mapping
            )
            
            # Parse LLM response
            import json
            response_text = response.strip()
            
            # Extract JSON from response (in case there's extra text)
            try:
                # Try direct JSON parse first
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re as regex
                json_match = regex.search(r'\{.*\}', response_text, regex.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    return {
                        "intent": None,
                        "categories": [],
                        "confidence": 0.0,
                        "method": "llm_failed",
                        "is_new_category": False
                    }
            
            # Check if LLM suggests a NEW category
            is_new_category = result.get("is_new_category", False)
            
            # Validate categories based on is_new_category flag
            if is_new_category:
                # Allow new categories! Don't filter against available_categories
                valid_categories = result.get("categories", [])
                logger.info(f"[LLM RESPONSE] NEW CATEGORY detected: {valid_categories}")
            else:
                # Only use existing/available categories
                valid_categories = [
                    cat for cat in result.get("categories", [])
                    if cat.lower() in [c.lower() for c in self.available_categories]
                ]
                logger.info(f"[LLM RESPONSE] Using available categories: {valid_categories}")
            
            # Get clarity from LLM response (clear or abstract)
            clarity = result.get("clarity", "abstract").lower()  # default to abstract if missing
            
            # Map clarity → intent_type
            intent_type = "specific" if clarity == "clear" else "abstract"
            
            # Use confidence from LLM response
            confidence = result.get("confidence", 0.65)  # default to 0.65
            
            logger.info(f"[LLM RESPONSE] clarity='{clarity}' → intent_type='{intent_type}', confidence={confidence}, is_new={is_new_category}")
            
            return {
                "intent": result.get("intent", ""),
                "intent_type": intent_type,
                "categories": valid_categories,
                "confidence": confidence,
                "method": "llm",
                "is_new_category": is_new_category  # ← NEW: Pass through flag
            }
            
        except Exception as e:
            print(f"ERROR in LLM intent mapping: {e}")
            return {
                "intent": None,
                "intent_type": "none",
                "categories": [],
                "confidence": 0.0,
                "method": "llm_error"
            }
    
    def get_fallback_question(self, intent: str, categories: List[str]) -> Dict[str, Any]:
        """
        Generate SMART question (like Lazada) confirming user intent with filtered options
        
        Instead of: "Bạn đang tìm loại sản phẩm nào?" + 50 categories
        Now: "Để mua quà cho bạn gái, bạn muốn chọn: Socola / Bánh / Hoa / Nước hoa?"
        """
        # Context-aware intent descriptions (confirm what user said)
        intent_labels = {
            "quà cho bạn gái": "Để mua quà ngọt ngào cho bạn gái",
            "quà cho bạn trai": "Để mua quà cho bạn trai",
            "để giải khát": "Để giải khát",
            "để mặc": "Để tìm quần áo",
            "để tránh thai": "Để tìm sản phẩm này",
            "để làm đẹp": "Để làm đẹp",
            "để chơi game": "Để chơi game",
            "để đi chơi": "Để chuẩn bị cho chuyến đi",
            "để tập thể dục": "Để tập luyện",
            "để nấu ăn": "Để nấu ăn",
            "để học": "Để học tập",
            "để ngủ": "Để ngủ ngon hơn",
        }
        
        # Get intent description (confirm, don't ask again)
        intent_desc = intent_labels.get(intent, f"Theo nhu cầu của bạn")
        
        # Build smart question with confirmed context
        question = f"{intent_desc}, bạn muốn chọn loại sản phẩm nào?"
        
        return {
            "question": question,
            "options": [
                {"label": cat.capitalize(), "value": cat}
                for cat in categories
            ],
            "question_type": "category"
        }

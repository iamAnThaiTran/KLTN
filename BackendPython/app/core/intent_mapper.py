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
        }
        
        # Available categories (for LLM to map to)
        self.available_categories = [
            "quần áo", "giày", "phụ kiện", "mỹ phẩm", "nước hoa", "túi xách", "dây chuyền",
            "dụng cụ", "công nghệ", "quà tặng", "nước", "nước ngọt", "cà phê", "trà",
            "thuốc tránh thai", "bao cao su", "skincare", "trang điểm", "máy tính", "console", 
            "monitor", "bàn phím", "ba lô", "dụng cụ tập", "nồi", "chảo", "dao", "cốc",
            "sách", "bút", "vở", "nệm", "gối", "chăn", "ga trải giường"
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
                "intent": str (usage intent),
                "categories": [cat1, cat2, ...],
                "confidence": float,
                "method": "pattern" | "llm"  # NEW: Track which method was used
            }
        """
        user_input_lower = user_input.lower()
        
        # ===== STEP 1: Try pattern matching (FAST) =====
        for pattern, categories in self.intent_patterns.items():
            if re.search(pattern, user_input_lower):
                # Extract intent từ pattern
                intent_match = re.search(pattern, user_input_lower)
                intent = intent_match.group(0) if intent_match else pattern
                
                return {
                    "intent": intent,
                    "categories": categories,
                    "confidence": 0.9,
                    "method": "pattern"  # NEW
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
            "categories": [],
            "confidence": 0.0,
            "method": "none"  # NEW
        }
    
    def _map_intent_with_llm(self, user_input: str) -> Dict[str, Any]:
        """
        Use LLM (OpenAI) để semantic understand intent + map categories
        
        Example: "tôi muốn mua gì đó ấm áp" → detect "warmth/comfort" need → 
                 map to [quần áo, áo khoác, nệm, gối]
        """
        # Get available category names
        categories_str = ", ".join(self.available_categories)
        
        prompt = f"""Analyze user's purchase intent and map to product categories.

User input: "{user_input}"

Available categories: {categories_str}

TASK: 
1. Understand what the user wants to buy (semantic meaning, not just keywords)
2. Identify the INTENT (reason/purpose)
3. Map to 2-5 most relevant categories

IMPORTANT: Output ONLY valid JSON, nothing else.

Format:
{{
  "intent": "short description of intent",
  "categories": ["category1", "category2"],
  "reasoning": "brief explanation"
}}

Examples:
- User: "tôi muốn gì đó ấm áp" → Intent: "warmth/comfort", Categories: ["quần áo", "nệm", "gối"]
- User: "chuẩn bị cho chuyến đi mưa" → Intent: "rain travel preparation", Categories: ["quần áo", "ba lô", "giày"]
- User: "tôi cần thứ bền để dùng lâu" → Intent: "durability", Categories: ["quần áo", "giày", "dụng cụ"]
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
                        "method": "llm_failed"
                    }
            
            # Validate categories (only use available ones)
            valid_categories = [
                cat for cat in result.get("categories", [])
                if cat.lower() in [c.lower() for c in self.available_categories]
            ]
            
            return {
                "intent": result.get("intent", ""),
                "categories": valid_categories,
                "confidence": 0.7,  # Lower confidence than pattern matching
                "method": "llm"
            }
            
        except Exception as e:
            print(f"ERROR in LLM intent mapping: {e}")
            return {
                "intent": None,
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

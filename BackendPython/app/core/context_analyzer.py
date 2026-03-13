# app/core/context_analyzer.py
import json
import re
import logging
from typing import Dict, Any
from app.core.llm_utils import call_openai

logger = logging.getLogger("context_analyzer")

class ContextAnalyzer:
    
    def reconstruct_intent(
        self, 
        user_input: str, 
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        # lấy ra lịch sử tìm kiếm, category hiện tại, và các thuộc tính đã trích xuất
        search_history = conversation_state.get("search_history", [])
        current_category = conversation_state.get("category")
        current_extracted = conversation_state.get("extracted", {})
        
        # Nếu không có lịch sử, trả về input gốc
        if not search_history and not current_category:
            logger.info(f"[ContextAnalyzer] No history, returning input as-is: '{user_input}'")
            return {
                "intent": user_input,
                "category_changed": False,
                "new_category": None
            }
        
        # Build context for LLM
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
            logger.info(f"[ContextAnalyzer] LLM response: {response_text}")
            
            # 🔍 Parse JSON response from LLM
            result = self._parse_llm_response(response_text)
            
            logger.info(f"[ContextAnalyzer] 🔄 INTENT RECONSTRUCTION:")
            logger.info(f"  History: {search_history}")
            logger.info(f"  Current input: '{user_input}'")
            logger.info(f"  Reconstructed: '{result['intent']}'")
            logger.info(f"  Category changed: {result['category_changed']} (old={current_category}, new={result['new_category']})")
            
            return result
        
        except Exception as e: 
            logger.error(f"[ContextAnalyzer] ⚠️ Error: {e}")
            # Fallback: concatenate history + input
            if search_history:
                fallback = " ".join(search_history + [user_input])
                return {
                    "intent": fallback,
                    "category_changed": False,
                    "new_category": None
                }
            return {
                "intent": user_input,
                "category_changed": False,
                "new_category": None
            }
    
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

CONVERSATION STATE:
- Search history (previous queries): [{history_text}]{extracted_text}
- {category_text}

NEW USER INPUT: "{user_input}"

TASK: Reconstruct the complete user intent based on conversation history + new input.

RULES:
1. If new input is an ATTRIBUTE (color, size, brand, etc.), MERGE it with current context
   Example: History="giày nike", Input="màu đen" → intent="giày nike màu đen"

2. If new input is a COMPLETELY DIFFERENT CATEGORY, declare category_changed=true
   Example: History="giày nike", Input="bột giặt" → category_changed=true, new_category="bột giặt"

3. When merging, INCLUDE already extracted attributes in the final intent
   Example: History="áo sơ mi", Extracted={{size=L}}, Input="màu xanh" → intent="áo sơ mi màu xanh size L"

4. If input already contains full details, use it as-is
   Example: History="giày", Input="giày thể thao màu trắng size 42" → intent="giày thể thao màu trắng size 42"

RESPONSE FORMAT: Return ONLY valid JSON, no other text:
{{
  "intent": "reconstructed user intent string",
  "category_changed": true or false,
  "new_category": "new category if changed, else null"
}}

Examples of valid responses:
{{"intent": "giày thể thao nike màu đen size 42", "category_changed": false, "new_category": null}}
{{"intent": "bột giặt", "category_changed": true, "new_category": "bột giặt"}}
{{"intent": "áo sơ mi nam màu trắng size L", "category_changed": false, "new_category": null}}
"""
        return prompt


_analyzer = None

def get_context_analyzer() -> ContextAnalyzer:
    """Get context analyzer singleton"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ContextAnalyzer()
    return _analyzer


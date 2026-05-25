# app/core/extractor.py

from typing import Dict, Any, List
import re
from .schema import get_schema
from .llm_utils import call_llm
from .dynamic_schema import DynamicAttributeExtractor, DynamicSchemaManager

class AttributeExtractor:
    """
    Trích xuất attributes từ user input
    
    Sử dụng DynamicAttributeExtractor để hỗ trợ ANY category,
    cũng như tương thích ngược với schema cũ
    """
    
    def __init__(self):
        self.dynamic_extractor = DynamicAttributeExtractor()
        self.schema_manager = DynamicSchemaManager()
    
    def extract(self, user_input: str, category: str, use_llm: bool = False) -> Dict[str, Any]:
        """
        Extract attributes cho category
        
        Sử dụng dynamic extraction - works for ANY category!
        
        Smart fallback: Nếu rule-based không tìm được attributes → auto LLM
        (không phụ thuộc vào use_llm parameter)
        
        Returns:
            {
                "extracted": {attr: value},
                "missing_required": [attr1, attr2],
                "confidence": float,
                "method": "rule-based" | "llm"
            }
        """
        # Step 1: Try dynamic extraction (rule-based first)
        result = self.dynamic_extractor.extract(
            user_input, 
            category,
            use_llm=False  # ← Always start with rule-based
        )
        
        # Step 2: Smart fallback - Nếu rule-based không tìm được gì → gọi LLM
        # Input quá short (e.g., "sagami") → rule-based fail → auto LLM
        if not result["extracted"] or len(result["extracted"]) == 0:
            # ✨ AUTO-FALLBACK: Rule-based found nothing, try LLM
            import logging
            logger = logging.getLogger(__name__)
            #logger.info(f"[AttributeExtractor] Rule-based extraction returned empty for '{user_input}' → Trying LLM fallback...")
            
            result = self.dynamic_extractor.extract(
                user_input, 
                category,
                use_llm=True  # ← Switch to LLM
            )
        
        # Step 3: Additional check - if still very low confidence + existing use_llm flag
        elif (result["confidence"] < 0.5 or len(result["missing_required"]) > 0) and use_llm:
            result = self.dynamic_extractor.extract(
                user_input, 
                category,
                use_llm=True
            )
        
        return result
    
    def _extract_attribute(self, text: str, attr_name: str, constraint) -> tuple:
        """
        Extract một attribute bằng rules
        
        DEPRECATED: Use DynamicAttributeExtractor instead
        Kept for backward compatibility
        """
        text = text.lower()
        
        if attr_name == "dong":
            # Trích xuất dòng sản phẩm (Air Force 1, Pegasus, etc.)
            patterns = [
                r'(?:dòng|model|series|line)\s+([a-z0-9\s]+?)(?:\s+size|\s+giá|\s+màu|$)',
                r'(air force one|air force 1|af1|air force)',
                r'(pegasus|revolution|cortez|blazer)',
                r'(jordan|max|zoom)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    return value, 0.9
            return None, 0.0
        
        if constraint.type == "enum":
            # Tìm value trong enum values
            for value in constraint.values:
                if value in text:
                    return value, 0.9
            return None, 0.0
        
        elif constraint.type == "range":
            # Tìm range (min-max) hoặc single value
            if attr_name == "gia":
                # Pattern: "200-300k", "200k-300k", "từ 200 đến 300k", etc.
                range_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)\s*(?:[-đến])\s*(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)',
                    r'(\d+(?:\.\d+)?)\s*(?:k|nghìn)\s*(?:[-đến])\s*(\d+(?:\.\d+)?)\s*(?:k|nghìn)',
                    r'(?:từ|from)\s+(\d+(?:\.\d+)?)\s*(?:triệu|tr|k|nghìn)\s+(?:đến|to)\s+(\d+(?:\.\d+)?)\s*(?:triệu|tr|k|nghìn)',
                ]
                
                for pattern in range_patterns:
                    match = re.search(pattern, text)
                    if match:
                        min_val = float(match.group(1))
                        max_val = float(match.group(2))
                        
                        # Convert to consistent unit (VND)
                        if "triệu" in text or "tr" in text:
                            min_val *= 1000000
                            max_val *= 1000000
                        elif "k" in text or "nghìn" in text:
                            min_val *= 1000
                            max_val *= 1000
                        
                        return {"min": min_val, "max": max_val}, 0.9
                
                # Single value patterns (fallback)
                single_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)',
                    r'(\d+(?:\.\d+)?)\s*(?:k|nghìn)',
                ]
                for pattern in single_patterns:
                    match = re.search(pattern, text)
                    if match:
                        value = float(match.group(1))
                        if "triệu" in text or "tr" in text:
                            value *= 1000000
                        elif "k" in text or "nghìn" in text:
                            value *= 1000
                        return value, 0.8
        
        elif constraint.type == "text":
            # Cho text type, dùng LLM
            return None, 0.0
        
        return None, 0.0
    
    def _llm_extract(self, text: str, schema) -> Dict[str, Any]:
        """
        Dùng LLM để extract attributes phức tạp
        
        DEPRECATED: Use DynamicAttributeExtractor instead
        Kept for backward compatibility
        """
        
        # Tạo prompt với schema
        attr_desc = []
        for attr, constraint in schema.attributes.items():
            if constraint.type == "enum":
                attr_desc.append(f"- {attr}: {', '.join(constraint.values)}")
        
        prompt = f"""Extract product attributes from the user query.

Available attributes:
{chr(10).join(attr_desc)}

Query: "{text}"

Respond in JSON format:
{{
  "attr_name": "value",
  ...
}}

Only include attributes that are CLEARLY mentioned. If not sure, don't include.
"""
        
        response = call_llm(prompt, max_tokens=200, json_mode=True)
        
        try:
            import json
            return json.loads(response)
        except:
            return {}
    
    def _extract_attribute(self, text: str, attr_name: str, constraint) -> tuple:
        """Extract một attribute bằng rules"""
        text = text.lower()
        
        if attr_name == "dong":
            # Trích xuất dòng sản phẩm (Air Force 1, Pegasus, etc.)
            patterns = [
                r'(?:dòng|model|series|line)\s+([a-z0-9\s]+?)(?:\s+size|\s+giá|\s+màu|$)',
                r'(air force one|air force 1|af1|air force)',
                r'(pegasus|revolution|cortez|blazer)',
                r'(jordan|max|zoom)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    return value, 0.9
            return None, 0.0
        
        if constraint.type == "enum":
            # Tìm value trong enum values
            for value in constraint.values:
                if value in text:
                    return value, 0.9
            return None, 0.0
        
        elif constraint.type == "range":
            # Tìm range (min-max) hoặc single value
            if attr_name == "gia":
                # Pattern: "200-300k", "200k-300k", "từ 200 đến 300k", etc.
                range_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)\s*(?:[-đến])\s*(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)',
                    r'(\d+(?:\.\d+)?)\s*(?:k|nghìn)\s*(?:[-đến])\s*(\d+(?:\.\d+)?)\s*(?:k|nghìn)',
                    r'(?:từ|from)\s+(\d+(?:\.\d+)?)\s*(?:triệu|tr|k|nghìn)\s+(?:đến|to)\s+(\d+(?:\.\d+)?)\s*(?:triệu|tr|k|nghìn)',
                ]
                
                for pattern in range_patterns:
                    match = re.search(pattern, text)
                    if match:
                        min_val = float(match.group(1))
                        max_val = float(match.group(2))
                        
                        # Convert to consistent unit (VND)
                        if "triệu" in text or "tr" in text:
                            min_val *= 1000000
                            max_val *= 1000000
                        elif "k" in text or "nghìn" in text:
                            min_val *= 1000
                            max_val *= 1000
                        
                        return {"min": min_val, "max": max_val}, 0.9
                
                # Single value patterns (fallback)
                single_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)',
                    r'(\d+(?:\.\d+)?)\s*(?:k|nghìn)',
                ]
                for pattern in single_patterns:
                    match = re.search(pattern, text)
                    if match:
                        value = float(match.group(1))
                        if "triệu" in text or "tr" in text:
                            value *= 1000000
                        elif "k" in text or "nghìn" in text:
                            value *= 1000
                        return value, 0.8
        
        elif constraint.type == "text":
            # Cho text type, dùng LLM
            return None, 0.0
        
        return None, 0.0
    
    def _llm_extract(self, text: str, schema) -> Dict[str, Any]:
        """Dùng LLM để extract attributes phức tạp"""
        
        # Tạo prompt với schema
        attr_desc = []
        for attr, constraint in schema.attributes.items():
            if constraint.type == "enum":
                attr_desc.append(f"- {attr}: {', '.join(constraint.values)}")
        
        prompt = f"""Extract product attributes from the user query.

Available attributes:
{chr(10).join(attr_desc)}

Query: "{text}"

Respond in JSON format:
{{
  "attr_name": "value",
  ...
}}

Only include attributes that are CLEARLY mentioned. If not sure, don't include.
"""
        
        response = call_llm(prompt, max_tokens=200, json_mode=True)
        
        try:
            import json
            return json.loads(response)
        except:
            return {}
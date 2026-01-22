# app/core/extractor.py

from typing import Dict, Any, List
import re
from .schema import get_schema
from .llm_utils import call_llm

class AttributeExtractor:
    """Trích xuất attributes từ user input theo schema"""
    
    def extract(self, user_input: str, category: str) -> Dict[str, Any]:
        """
        Extract attributes cho category đã biết
        
        Returns:
            {
                "extracted": {attr: value},
                "missing_required": [attr1, attr2],
                "confidence": float
            }
        """
        schema = get_schema(category)
        if not schema:
            raise ValueError(f"Unknown category: {category}")
        
        extracted = {}
        confidence_scores = []
        
        # Step 1: Rule-based extraction (nhanh)
        for attr_name, constraint in schema.attributes.items():
            value, conf = self._extract_attribute(
                user_input, attr_name, constraint
            )
            if value:
                extracted[attr_name] = value
                confidence_scores.append(conf)
        
        # Step 2: LLM extraction nếu rule-based không đủ
        if len(extracted) < 2:  # Quá ít thông tin
            llm_extracted = self._llm_extract(user_input, schema)
            extracted.update(llm_extracted)
        
        # Step 3: Tìm required attributes còn thiếu
        missing_required = [
            attr for attr, constraint in schema.attributes.items()
            if constraint.required and attr not in extracted
        ]
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "extracted": extracted,
            "missing_required": missing_required,
            "confidence": avg_confidence
        }
    
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
            # Tìm số trong text (ví dụ: giá)
            if attr_name == "gia":
                patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:triệu|tr|million)',
                    r'(\d+(?:\.\d+)?)\s*(?:k|nghìn)',
                ]
                for pattern in patterns:
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
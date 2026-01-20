# app/core/matcher.py

from typing import List, Dict, Any
from .schema import get_schema

class ProductMatcher:
    """
    Validate và match crawled products với expected category
    Xử lý trường hợp: category thiếu, thừa, sai
    """
    
    def match_products(
        self, 
        products: List[Dict[str, Any]], 
        expected_category: str,
        user_attributes: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter và validate products từ crawl
        
        Args:
            products: Danh sách sản phẩm từ crawler
            expected_category: Category user đang tìm
            user_attributes: Attributes user đã chọn
            
        Returns:
            Danh sách products đã validate, có thêm:
            - match_score: 0-100
            - match_reason: Lý do match/không match
        """
        
        schema = get_schema(expected_category)
        matched = []
        
        for product in products:
            result = self._validate_product(product, schema, user_attributes)
            
            if result["is_valid"]:
                product["match_score"] = result["score"]
                product["match_reasons"] = result["reasons"]
                matched.append(product)
        
        # Sort theo match_score
        matched.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matched
    
    def _validate_product(
        self, 
        product: Dict[str, Any],
        schema,
        user_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate một product
        
        Xử lý:
        1. Product thiếu category → dùng heuristics hoặc LLM
        2. Product có category sai → filter out
        3. Product có thừa/thiếu attributes → tính score
        """
        
        score = 0
        reasons = []
        
        # Step 1: Kiểm tra category
        product_category = self._infer_category(product, schema)
        
        if not product_category:
            # Thiếu category → dùng LLM classify
            product_category = self._llm_classify_product(product, schema.name)
        
        if product_category != schema.name:
            # Sai category
            return {
                "is_valid": False,
                "score": 0,
                "reasons": [f"Không phải {schema.name}"]
            }
        
        # Step 2: So sánh attributes
        for attr_name, user_value in user_attributes.items():
            product_value = self._extract_product_attribute(
                product, attr_name
            )
            
            if product_value == user_value:
                score += 20
                reasons.append(f"✓ {attr_name}: {user_value}")
            elif product_value:
                score += 5  # Có attribute nhưng không match
            else:
                # Thiếu attribute → không trừ điểm nếu là optional
                constraint = schema.attributes.get(attr_name)
                if constraint and constraint.required:
                    score -= 10
                    reasons.append(f"✗ Thiếu {attr_name}")
        
        # Step 3: Bonus cho completeness
        completeness = self._calculate_completeness(product, schema)
        score += completeness * 10
        
        return {
            "is_valid": score > 0,
            "score": max(0, min(100, score)),  # Clamp 0-100
            "reasons": reasons
        }
    
    def _infer_category(self, product: Dict[str, Any], schema) -> str:
        """
        Infer category từ product data
        Dùng keywords trong tên/mô tả
        """
        text = f"{product.get('name', '')} {product.get('description', '')}".lower()
        
        for keyword in schema.keywords:
            if keyword in text:
                return schema.name
        
        return None
    
    def _llm_classify_product(self, product: Dict[str, Any], expected_category: str) -> str:
        """
        Dùng LLM để classify product khi không chắc chắn
        """
        from .llm_utils import call_llm
        
        prompt = f"""Is this product a "{expected_category}"?

Product name: {product.get('name', 'N/A')}
Product description: {product.get('description', 'N/A')[:200]}

Respond ONLY with "yes" or "no".
"""
        
        response = call_llm(prompt, max_tokens=5).strip().lower()
        
        return expected_category if response == "yes" else "unknown"
    
    def _extract_product_attribute(self, product: Dict[str, Any], attr_name: str):
        """
        Extract attribute value từ product data
        Tùy thuộc vào crawler của bạn trả về gì
        """
        # Giả sử product có structure:
        # {"name": "", "price": 0, "attributes": {"size": "42", ...}}
        
        if "attributes" in product:
            return product["attributes"].get(attr_name)
        
        # Fallback: parse từ name/description
        return self._parse_from_text(product, attr_name)
    
    def _parse_from_text(self, product: Dict[str, Any], attr_name: str):
        """Parse attribute từ text (name, description)"""
        # Simple heuristics
        text = f"{product.get('name', '')} {product.get('description', '')}".lower()
        
        # Ví dụ cho size
        if attr_name == "size":
            import re
            match = re.search(r'size\s*(\d+)', text)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate_completeness(self, product: Dict[str, Any], schema) -> float:
        """
        Tính độ đầy đủ của product (có bao nhiêu % attributes)
        """
        total_attrs = len(schema.attributes)
        filled_attrs = sum(
            1 for attr in schema.attributes
            if self._extract_product_attribute(product, attr)
        )
        
        return filled_attrs / total_attrs if total_attrs > 0 else 0
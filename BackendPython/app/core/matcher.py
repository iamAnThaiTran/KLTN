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
        
        for idx, product in enumerate(products):
            result = self._validate_product(product, schema, user_attributes)
            
            print(f"DEBUG Match [{idx}]: {product.get('name', 'N/A')[:50]}")
            print(f"  Valid: {result['is_valid']}, Score: {result['score']}, Reasons: {result['reasons']}")
            
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
        
        Logic:
        1. Category sai → loại bỏ (is_valid = False)
        2. Attribute missing → CHẤP NHẬN (vẫn match, score cao)
        3. Attribute có nhưng MISMATCH → giảm điểm (nhưng không loại bỏ)
        """
        
        score = 100  # Start with 100
        reasons = []
        is_valid = True
        mismatch_count = 0
        
        # Step 1: Kiểm tra category
        product_category = self._infer_category(product, schema)
        
        if not product_category:
            # Thiếu category → dùng LLM classify
            product_category = self._llm_classify_product(product, schema.name)
        
        print(f"    Category check: inferred='{product_category}', expected='{schema.name}'")
        
        if product_category != schema.name:
            # Sai category → loại bỏ
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
            
            print(f"    Attr {attr_name}: user='{user_value}', product='{product_value}'")
            
            # Check if user_value is a range (dict with min/max)
            is_range = isinstance(user_value, dict) and "min" in user_value and "max" in user_value
            
            if is_range:
                # Range matching
                min_val = user_value["min"]
                max_val = user_value["max"]
                
                if product_value is None or product_value == "":
                    # Missing attribute
                    score -= 2
                    reasons.append(f"⊘ {attr_name}: không có thông tin")
                elif isinstance(product_value, (int, float)):
                    if min_val <= product_value <= max_val:
                        # Within range
                        reasons.append(f"✓ {attr_name}: {product_value} (trong {min_val}-{max_val})")
                    else:
                        # Outside range
                        score -= 30
                        mismatch_count += 1
                        reasons.append(f"✗ {attr_name}: {product_value} (mong đợi {min_val}-{max_val})")
                else:
                    # Cannot compare
                    score -= 2
                    reasons.append(f"⊘ {attr_name}: không thể so sánh")
            else:
                # Exact matching
                if product_value == user_value:
                    # Match tuyệt đối
                    reasons.append(f"✓ {attr_name}: {user_value}")
                elif product_value is None or product_value == "":
                    # Missing attribute
                    score -= 2
                    reasons.append(f"⊘ {attr_name}: không có thông tin")
                else:
                    # Attribute có nhưng MISMATCH
                    score -= 30
                    mismatch_count += 1
                    reasons.append(f"✗ {attr_name}: {product_value} (mong đợi {user_value})")
        
        # Step 3: Nếu quá nhiều mismatches → có thể loại bỏ
        # (Nếu > 50% attributes bị mismatch thì loại bỏ)
        if user_attributes and mismatch_count > len(user_attributes) * 0.5:
            return {
                "is_valid": False,
                "score": 0,
                "reasons": [f"Quá nhiều attributes không match"]
            }
        
        # Step 4: Bonus cho completeness (sản phẩm đầy đủ thông tin)
        completeness = self._calculate_completeness(product, schema)
        score += completeness * 10
        
        print(f"    Final score: {score}, mismatch_count: {mismatch_count}")
        
        return {
            "is_valid": True,  # Luôn True trừ khi category sai hoặc quá nhiều mismatch
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
        # Ưu tiên: attributes dict (crawl detail)
        if "attributes" in product and product["attributes"]:
            return product["attributes"].get(attr_name)
        
        # Nếu tìm brand, lấy trực tiếp từ product["brand"]
        if attr_name == "brand" and "brand" in product:
            return product["brand"]
        
        # Fallback: parse từ name/description
        return self._parse_from_text(product, attr_name)
    
    def _parse_from_text(self, product: Dict[str, Any], attr_name: str):
        """Parse attribute từ text (name, description)"""
        import re
        import unicodedata
        
        def normalize(s: str) -> str:
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return s.lower().strip()
        
        text = f"{product.get('name', '')} {product.get('description', '')}".lower()
        text_normalized = normalize(text)
        
        # Ví dụ cho size
        if attr_name == "size":
            # Tìm size như "size 42", "42", "L", "XL", v.v.
            patterns = [
                r'size\s*(\d+)',  # size 42
                r'(\d{2,3})',      # 42
                r'\b([SML]|XL|XXL)\b'  # S, M, L, XL, XXL
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
        
        # Ví dụ cho loai (type) - bột, nước, áo, quần, etc.
        if attr_name in ["loai", "type"]:
            types = {
                "bột": "bot",
                "nước": "nuoc",
                "chạy bộ": "chay bo",
                "bóng chuyền": "bong chuyen",
                "cầu lông": "cau long",
                "tennis": "tennis",
                "bóng rổ": "bong ro",
                "đá banh": "da banh"
            }
            for type_vn, type_en in types.items():
                norm_vn = normalize(type_vn)
                if norm_vn in text_normalized or type_en in text_normalized:
                    return type_vn
        
        # Ví dụ cho color/mau_sac
        if attr_name in ["mau_sac", "color", "colors"]:
            colors = {
                "đen": "den",
                "trắng": "trang",
                "đỏ": "do",
                "xanh": "xanh",
                "vàng": "vang",
                "hồng": "hong",
                "nâu": "nau",
                "xám": "xam"
            }
            for color_vn, color_en in colors.items():
                norm_vn = normalize(color_vn)
                if norm_vn in text_normalized or color_en in text_normalized:
                    return color_vn
        
        # Material/chất liệu
        if attr_name in ["chat_lieu", "material", "materials"]:
            materials = {
                "da": "leather",
                "vải": "fabric",
                "cotton": "cotton",
                "leather": "da"
            }
            for mat_vn, mat_en in materials.items():
                norm_vn = normalize(mat_vn)
                if norm_vn in text_normalized or mat_en in text_normalized:
                    return mat_vn
        
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
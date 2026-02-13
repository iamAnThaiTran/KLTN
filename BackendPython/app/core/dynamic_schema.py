# app/core/dynamic_schema.py
"""
Dynamic Schema System - Tự động detect và extract attributes 
cho ANY product type mà không cần hardcoding schema
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel


class AttributeConstraint(BaseModel):
    """Ràng buộc cho một attribute"""
    type: str  # "enum", "range", "text", "number"
    values: Optional[List[str]] = None  # cho enum
    min_val: Optional[float] = None  # cho range
    max_val: Optional[float] = None
    required: bool = False
    aliases: Optional[List[str]] = None  # Tên khác của attribute


class CategorySchema(BaseModel):
    """Schema cho một category sản phẩm"""
    name: str
    attributes: Dict[str, AttributeConstraint]
    keywords: List[str] = []  # Từ khóa để nhận dạng category


# ============================================
# UNIVERSAL ATTRIBUTES - Áp dụng cho ALL categories
# ============================================
UNIVERSAL_ATTRIBUTES = {
    "brand": AttributeConstraint(
        type="text",
        required=False,
        aliases=["thương hiệu", "hãng", "nhãn hiệu"]
    ),
    "mau": AttributeConstraint(
        type="enum",
        values=["đen", "trắng", "xanh", "đỏ", "vàng", "hồng", "nâu", "xám", "tím", "cam", "lam"],
        required=False,
        aliases=["màu", "color"]
    ),
    "size": AttributeConstraint(
        type="text",
        required=False,
        aliases=["kích cỡ", "cỡ", "kích thước"]
    ),
    "gia": AttributeConstraint(
        type="range",
        min_val=0,
        max_val=100000000,
        required=False,
        aliases=["giá", "giá tiền", "price", "giá cả"]
    ),
    "quality": AttributeConstraint(
        type="enum",
        values=["cao cấp", "bình thường", "rẻ tiền", "tốt", "kém"],
        required=False,
        aliases=["chất lượng", "quality"]
    ),
    "material": AttributeConstraint(
        type="text",
        required=False,
        aliases=["chất liệu", "material", "chất"]
    ),
}

# Category-specific attributes (stored separately, loaded as needed)
CATEGORY_SPECIFIC_ATTRS = {
    "giày": {
        "loai": AttributeConstraint(
            type="enum",
            values=["thể thao", "chạy bộ", "sneaker", "tây", "sandal", "dép", "boot"],
            required=False,
            aliases=["kiểu giày"]
        ),
        "gender": AttributeConstraint(
            type="enum",
            values=["nam", "nữ", "unisex"],
            required=False
        ),
    },
    "áo": {
        "loai_ao": AttributeConstraint(
            type="enum",
            values=["áo phông", "áo polo", "áo sơ mi", "áo hoodie", "áo len", "áo chống nắng"],
            required=False,
            aliases=["loại"]
        ),
        "tay_ao": AttributeConstraint(
            type="enum",
            values=["tay dài", "tay ngắn", "không tay"],
            required=False
        ),
    },
    "laptop": {
        "ram": AttributeConstraint(
            type="text",
            required=False,
            aliases=["bộ nhớ", "memory"]
        ),
        "storage": AttributeConstraint(
            type="text",
            required=False,
            aliases=["ổ cứng", "ssd", "lưu trữ"]
        ),
        "processor": AttributeConstraint(
            type="text",
            required=False,
            aliases=["cpu", "vi xử lý"]
        ),
        "gpu": AttributeConstraint(
            type="text",
            required=False,
            aliases=["card đồ họa", "graphic"]
        ),
    },
    "điện thoại": {
        "ram": AttributeConstraint(type="text", required=False),
        "storage": AttributeConstraint(type="text", required=False),
        "camera": AttributeConstraint(type="text", required=False),
        "pin": AttributeConstraint(type="text", required=False, aliases=["pin", "battery"]),
        "screen": AttributeConstraint(type="text", required=False, aliases=["màn hình", "screen"]),
    },
    "bao cao su": {
        "loai": AttributeConstraint(
            type="enum",
            values=["cơ bản", "siêu mỏng", "có hương", "có gân", "tự bôi trơn"],
            required=False
        ),
        "so_luong": AttributeConstraint(
            type="enum",
            values=["1 cái", "3 cái", "10 cái", "12 cái"],
            required=False
        ),
    },
}

# Universal keywords for common categories
UNIVERSAL_KEYWORDS = {
    "giày": ["giày", "giầy", "shoe", "sneaker", "sandal", "dép", "boots", "giày thể thao"],
    "áo": ["áo", "áo phông", "shirt", "t-shirt", "áo polo", "áo sơ mi", "áo hoodie"],
    "túi xách": ["túi", "túi xách", "balo", "backpack", "túi đeo", "va-li"],
    "mỹ phẩm": ["mỹ phẩm", "skincare", "makeup", "mỹ phẩm chăm sóc", "trang điểm"],
    "điện thoại": ["điện thoại", "phone", "smartphone", "mobile", "điện thoại di động"],
    "laptop": ["laptop", "máy tính xách tay", "macbook", "notebook", "máy tính"],
    "bao cao su": ["bao cao su", "condom", "bcs", "tránh thai"],
    "đồng hồ": ["đồng hồ", "watch", "smartwatch", "đồng hồ thông minh"],
    "nước ngọt": ["nước ngọt", "nước", "cola", "cocacola", "sprite", "fanta", "pepsi", "cà phê", "cafe", "nước mắm", "nước tương"],
    "trà": ["trà", "trà xanh", "trà đen", "tea", "trà oolong"],
}

# Global category list - for LLM category detection
AVAILABLE_CATEGORIES = list(UNIVERSAL_KEYWORDS.keys())


class DynamicSchemaManager:
    """
    Quản lý dynamic schemas - tự động cấp attributes cho ANY category
    
    universal_keywords property được DynamicCategoryDetector sử dụng
    """
    
    def __init__(self):
        self.universal_attrs = UNIVERSAL_ATTRIBUTES.copy()
        self.category_specific = CATEGORY_SPECIFIC_ATTRS.copy()
        self._universal_keywords = UNIVERSAL_KEYWORDS.copy()
    
    @property
    def universal_keywords(self):
        """Return UNIVERSAL_KEYWORDS for category detection"""
        return self._universal_keywords
    
    def get_attributes_for_category(self, category: str) -> Dict[str, AttributeConstraint]:
        """
        Get attributes cho bất kỳ category nào
        
        1. Bắt đầu với UNIVERSAL_ATTRIBUTES (brand, mau, gia, v.v.)
        2. Thêm category-specific nếu có
        3. Trả về đầy đủ schema
        """
        attrs = self.universal_attrs.copy()
        
        # Add category-specific if exists
        if category in self.category_specific:
            attrs.update(self.category_specific[category])
        
        return attrs
    
    def get_keywords_for_category(self, category: str) -> List[str]:
        """Get keywords để detect category"""
        return self.universal_keywords.get(category, [category])
    
    def add_category_specific_attrs(
        self, 
        category: str, 
        attributes: Dict[str, AttributeConstraint]
    ):
        """Dynamically add category-specific attributes (from DB)"""
        self.category_specific[category] = attributes
    
    def add_category_keywords(
        self, 
        category: str, 
        keywords: List[str]
    ):
        """Dynamically add keywords for category detection"""
        self.universal_keywords[category] = keywords


# ============================================
# RULE-BASED EXTRACTORS - Extract attributes mà không cần LLM
# ============================================

class RuleBasedExtractor:
    """Extract attributes từ text sử dụng regex patterns"""
    
    def __init__(self):
        self.schema_manager = DynamicSchemaManager()
    
    def extract_price(self, text: str) -> Optional[Dict[str, float]]:
        """
        Extract giá từ text
        Examples: "500k", "5 triệu", "5-10 triệu", "từ 5 tới 10 triệu"
        """
        # Pattern: number + unit (k, triệu, tr, vnd, đ)
        pattern = r'(\d+(?:\.\d+)?)\s*(?:k|K|triệu|tr|vnd|đ)?(?:\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:k|K|triệu|tr)?)?'
        
        matches = re.findall(pattern, text)
        if not matches:
            return None
        
        # Get last match (most likely the price mentioned)
        min_str, max_str = matches[-1]
        min_val = float(min_str)
        
        # Convert K to actual value
        if 'k' in text.lower() and min_val < 1000:
            min_val *= 1000
        elif 'triệu' in text.lower() or 'tr' in text.lower():
            if min_val < 1000:
                min_val *= 1000000
        
        max_val = min_val
        if max_str:
            max_val = float(max_str)
            if 'k' in text.lower() and max_val < 1000:
                max_val *= 1000
            elif 'triệu' in text.lower() or 'tr' in text.lower():
                if max_val < 1000:
                    max_val *= 1000000
        
        # If only one number, assume it's a single price
        if max_str:
            return {"min": min_val, "max": max_val}
        else:
            # Assume ±10% range for single price
            return {"min": min_val * 0.9, "max": min_val * 1.1}
    
    def extract_brand(self, text: str, known_brands: Optional[List[str]] = None) -> Optional[str]:
        """Extract thương hiệu"""
        text_lower = text.lower()
        
        # List of common brands
        common_brands = [
            "nike", "adidas", "puma", "reebok", "asics", "new balance",
            "converse", "vans", "gucci", "zara", "h&m", "uniqlo",
            "samsung", "apple", "xiaomi", "oppo", "vivo",
            "sony", "canon", "nikon", "lg", "dell", "lenovo",
            "durex", "trojan", "hhv",
        ]
        
        brands_to_check = known_brands or common_brands
        
        for brand in brands_to_check:
            if brand.lower() in text_lower:
                return brand.lower()
        
        return None
    
    def extract_color(self, text: str) -> Optional[str]:
        """Extract màu sắc"""
        colors = [
            "đen", "trắng", "xanh", "đỏ", "vàng", "hồng", "nâu", "xám", "tím", "cam", "lam"
        ]
        
        text_lower = text.lower()
        for color in colors:
            if color in text_lower:
                return color
        
        return None
    
    def extract_size(self, text: str) -> Optional[str]:
        """
        Extract size
        Examples: "size M", "kích cỡ 40", "size 35"
        """
        # Pattern: "size XS/S/M/L/XL/XXL" or "kích cỡ 35"
        patterns = [
            r'(?:size|kích cỡ|cỡ)\s*:?\s*([XS]+|M|L+|XL+|\d{1,3})',
            r'\b([XS]+|M|L+|XL+)\b',  # Standalone sizes like M, L, XL
            r'\b(\d{1,3})\b(?:\s*(?:size|cm|inch))',  # Numbers like 35, 40
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_ram_storage(self, text: str) -> Dict[str, Optional[str]]:
        """Extract RAM và storage (for electronics)"""
        result = {"ram": None, "storage": None}
        
        # RAM patterns: "8GB", "16GB", "32GB RAM"
        ram_pattern = r'(\d+)\s*(?:GB|gb)?\s*(?:ram|RAM|bộ nhớ)'
        ram_match = re.search(ram_pattern, text)
        if ram_match:
            result["ram"] = f"{ram_match.group(1)}GB"
        
        # Storage patterns: "256GB", "512GB SSD", "1TB"
        storage_pattern = r'(\d+)\s*(?:GB|TB|gb|tb)\s*(?:ssd|SSD|ổ cứng|storage)'
        storage_match = re.search(storage_pattern, text)
        if storage_match:
            result["storage"] = storage_match.group(1) + ("GB" if "gb" in storage_match.group() else "TB")
        
        return result
    
    def extract_processor(self, text: str) -> Optional[str]:
        """Extract processor (Intel, AMD, Apple Silicon)"""
        # Common processors
        processors = [
            "i3", "i5", "i7", "i9",  # Intel
            "ryzen 3", "ryzen 5", "ryzen 7", "ryzen 9",  # AMD
            "m1", "m2", "m3",  # Apple
            "intel core", "amd ryzen"
        ]
        
        text_lower = text.lower()
        for proc in processors:
            if proc in text_lower:
                # Extract the full term
                match = re.search(rf'{proc}\s*(?:ultra)?\s*(?:\d+)?', text_lower)
                if match:
                    return match.group().strip()
        
        return None


class DynamicAttributeExtractor:
    """
    Extract attributes từ text cho ANY category
    
    Strategy:
    1. Rule-based extraction (fast, <100ms)
    2. Pattern matching cho common attributes
    3. Qwen LLM fallback nếu cần (slower, nhưng accurate)
    """
    
    def __init__(self):
        self.schema_manager = DynamicSchemaManager()
        self.rule_extractor = RuleBasedExtractor()
    
    def extract(
        self, 
        user_input: str, 
        category: str,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Extract attributes cho category
        
        Returns:
            {
                "extracted": {attr: value},
                "missing_required": [attr1, attr2],
                "confidence": float,
                "method": "rule-based" | "qwen"
            }
        """
        attrs_schema = self.schema_manager.get_attributes_for_category(category)
        extracted = {}
        
        # Step 1: Rule-based extraction (áp dụng cho universal attributes)
        extracted.update(self._rule_extract(user_input, attrs_schema))
        
        # Step 2: Qwen LLM fallback nếu rule-based không đủ
        if use_llm and len(extracted) < 2:
            llm_extracted = self._qwen_extract(user_input, category, attrs_schema)
            extracted.update(llm_extracted)
            method = "qwen"
        else:
            method = "rule-based"
        
        # Step 3: Find missing required attributes
        missing_required = [
            attr for attr, constraint in attrs_schema.items()
            if constraint.required and attr not in extracted
        ]
        
        confidence = len(extracted) / len(attrs_schema) if attrs_schema else 0.0
        
        return {
            "extracted": extracted,
            "missing_required": missing_required,
            "confidence": confidence,
            "method": method,
            "schema": attrs_schema
        }
    
    def _rule_extract(
        self, 
        text: str, 
        attrs_schema: Dict[str, AttributeConstraint]
    ) -> Dict[str, Any]:
        """Rule-based extraction"""
        extracted = {}
        
        # Extract universal attributes using patterns
        if "brand" in attrs_schema:
            brand = self.rule_extractor.extract_brand(text)
            if brand:
                extracted["brand"] = brand
        
        if "mau" in attrs_schema:
            mau = self.rule_extractor.extract_color(text)
            if mau:
                extracted["mau"] = mau
        
        if "size" in attrs_schema:
            size = self.rule_extractor.extract_size(text)
            if size:
                extracted["size"] = size
        
        if "gia" in attrs_schema:
            gia = self.rule_extractor.extract_price(text)
            if gia:
                extracted["gia"] = gia
        
        # Extract category-specific attributes
        if "ram" in attrs_schema:
            ram_storage = self.rule_extractor.extract_ram_storage(text)
            if ram_storage["ram"]:
                extracted["ram"] = ram_storage["ram"]
        
        if "storage" in attrs_schema:
            ram_storage = self.rule_extractor.extract_ram_storage(text)
            if ram_storage["storage"]:
                extracted["storage"] = ram_storage["storage"]
        
        if "processor" in attrs_schema:
            processor = self.rule_extractor.extract_processor(text)
            if processor:
                extracted["processor"] = processor
        
        return extracted
    
    def _llm_extract(
        self, 
        text: str, 
        category: str,
        attrs_schema: Dict[str, AttributeConstraint]
    ) -> Dict[str, Any]:
        """LLM-based extraction (fallback) - Uses Qwen"""
        from .llm_utils import call_llm
        import json
        
        # Build attribute descriptions
        attr_desc = []
        for attr_name, constraint in attrs_schema.items():
            if constraint.type == "enum":
                values_str = ", ".join(constraint.values[:5])  # First 5 values
                attr_desc.append(f"- {attr_name}: {values_str}")
            else:
                attr_desc.append(f"- {attr_name} ({constraint.type})")
        
        # Build prompt for Qwen
        prompt = f"""Bạn là một trợ lý phân tích sản phẩm. Từ câu hỏi của người dùng, trích xuất các thuộc tính sản phẩm.

Danh mục sản phẩm: {category}

Các thuộc tính có sẵn:
{chr(10).join(attr_desc)}

Câu hỏi của người dùng: "{text}"

Trích xuất các thuộc tính tìm thấy. Chỉ bao gồm các thuộc tính được mention rõ ràng.

Trả về kết quả dưới dạng JSON:
{{
  "brand": "...",
  "mau": "...",
  "size": "...",
  ...
}}

Nếu không tìm thấy attribute nào, trả về {{}}.
"""
        
        try:
            # Call Qwen (or fallback LLM)
            response = call_llm(prompt, max_tokens=300)
            
            # Parse JSON response
            if response:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                    return extracted
        except Exception as e:
            print(f"Qwen extraction error: {e}")
        
        return {}
    
    def _qwen_extract(
        self, 
        text: str, 
        category: str,
        attrs_schema: Dict[str, AttributeConstraint]
    ) -> Dict[str, Any]:
        """Qwen-specific extraction"""
        return self._llm_extract(text, category, attrs_schema)


# ============================================
# CATEGORY DETECTOR - Detect category mà không cần hardcoding
# ============================================

class DynamicCategoryDetector:
    """
    Detect product category từ user input
    
    Strategy:
    1. Rule-based keyword matching (fast)
    2. Embedding-based similarity (accurate, slower)
    """
    
    def __init__(self):
        self.schema_manager = DynamicSchemaManager()
        self.embedding_model = None
        self.category_embeddings = None
    
    def detect_category(self, user_input: str) -> Tuple[Optional[str], float]:
        """
        Detect category từ user input
        
        Returns:
            (category_name, confidence)
        """
        # Step 1: Try keyword-based detection (fast)
        category, confidence = self._keyword_detect(user_input)
        if category and confidence > 0.7:
            return category, confidence
        
        # Step 2: Try embedding-based detection (slow but accurate)
        if confidence is None or confidence < 0.7:
            category, confidence = self._embedding_detect(user_input)
        
        return category, confidence if confidence else 0.0
    
    def _keyword_detect(self, text: str) -> Tuple[Optional[str], float]:
        """
        Keyword-based category detection
        
        Returns:
            (category, confidence)
        """
        text_lower = text.lower()
        best_match = None
        best_confidence = 0.0
        
        for category, keywords in self.schema_manager.universal_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Exact keyword match → high confidence
                    confidence = 1.0 if keyword.lower() == text_lower.strip() else 0.9
                    if confidence > best_confidence:
                        best_match = category
                        best_confidence = confidence
                    break
            
            # If found a good match, don't check others
            if best_confidence > 0.85:
                break
        
        return best_match, best_confidence
    
    def _embedding_detect(self, text: str) -> Tuple[Optional[str], float]:
        """
        Embedding-based detection (fallback)
        Requires sentence-transformers library
        """
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            
            if self.embedding_model is None:
                self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                
                # Pre-compute embeddings for all categories
                self.category_embeddings = {}
                for category, keywords in self.schema_manager.universal_keywords.items():
                    category_text = f"{category} {' '.join(keywords)}"
                    self.category_embeddings[category] = self.embedding_model.encode(category_text)
            
            # Encode user input
            user_embedding = self.embedding_model.encode(text)
            
            # Find most similar category
            best_match = None
            best_confidence = 0.0
            
            for category, cat_embedding in self.category_embeddings.items():
                similarity = cosine_similarity(
                    [user_embedding], 
                    [cat_embedding]
                )[0][0]
                
                if similarity > best_confidence:
                    best_match = category
                    best_confidence = float(similarity)
            
            return best_match, best_confidence
        
        except ImportError:
            return None, 0.0

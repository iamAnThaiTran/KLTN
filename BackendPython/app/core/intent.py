
from typing import Optional, Dict, Any, List
import re
from .schema import get_all_categories, get_schema

class EnhancedIntentDetector:
    """
    Phát hiện intent phức tạp:
    - Category switching (đổi sản phẩm)
    - Attribute refinement (chỉnh sửa tiêu chí)
    - Attribute conflict (tiêu chí mâu thuẫn)
    """
    
    def __init__(self):
        self.categories = get_all_categories()
        self._init_embedding_model()
        
        # Từ khóa chỉ sự thay đổi ý định
        self.change_signals = [
            "thôi", "khỏi", "không", "đổi", "thay", "chuyển",
            "hoặc", "hay là", "còn", "thế còn", "giờ",
            "instead", "or", "how about", "what about"
        ]
        
        # Từ khóa chỉ refinement (cùng category)
        self.refinement_signals = [
            "thêm", "và", "kèm", "có", "với", "thay vì",
            "also", "with", "plus", "and"
        ]
    
    def _init_embedding_model(self):
        self.embedding_model = None
        self.category_embeddings = None
    
    def _load_embedding_model(self):
        if self.embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2'
                )
                
                from .schema import get_schema
                category_texts = {}
                for cat in self.categories:
                    schema = get_schema(cat)
                    category_texts[cat] = f"{cat} {' '.join(schema.keywords)}"
                
                self.category_embeddings = {
                    cat: self.embedding_model.encode(text, convert_to_tensor=True)
                    for cat, text in category_texts.items()
                }
            except ImportError:
                self.embedding_model = "not_available"
    
    def detect_intent_change(
        self,
        user_input: str,
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phát hiện loại thay đổi intent:
        
        Returns:
            {
                "intent_type": "new_search" | "refine" | "switch_category" | "switch_attribute",
                "new_category": str | None,
                "should_reset": bool,
                "confidence": float,
                "reason": str  # Giải thích tại sao
            }
        """
        user_input_lower = user_input.lower().strip()
        
        # Case 1: Chưa có category → new search
        if not current_state.get("has_category"):
            category_result = self._detect_category(user_input)
            return {
                "intent_type": "new_search",
                "new_category": category_result.get("category"),
                "should_reset": True,
                "confidence": category_result.get("confidence", 0.0),
                "reason": "First query in conversation"
            }
        
        current_category = current_state.get("category")
        
        # Case 2: Detect change signals → có khả năng đổi intent
        has_change_signal = any(signal in user_input_lower for signal in self.change_signals)
        
        # Case 3: Detect category mention
        category_result = self._detect_category(user_input)
        mentioned_category = category_result.get("category")
        
        # DECISION TREE
        
        # Scenario A: Explicit category change (mention category khác)
        if mentioned_category and mentioned_category != current_category:
            return {
                "intent_type": "switch_category",
                "new_category": mentioned_category,
                "should_reset": True,
                "confidence": category_result["confidence"],
                "reason": f"User mentioned new category: '{mentioned_category}'"
            }
        
        # Scenario B: Change signal + no category mention
        # → Có thể là đổi attribute trong cùng category
        if has_change_signal and not mentioned_category:
            # Check xem có extract được attributes mới không
            from .extractor import AttributeExtractor
            extractor = AttributeExtractor()
            new_attrs = extractor.extract(user_input, current_category)
            
            if new_attrs["extracted"]:
                # Có attributes mới → đổi attribute
                conflicting = self._check_attribute_conflict(
                    current_state.get("extracted", {}),
                    new_attrs["extracted"]
                )
                
                if conflicting:
                    return {
                        "intent_type": "switch_attribute",
                        "new_category": current_category,  # Same category
                        "should_reset": False,  # Không reset toàn bộ
                        "should_replace_attributes": True,
                        "conflicting_attributes": conflicting,
                        "confidence": 0.8,
                        "reason": f"User wants to change attributes: {conflicting}"
                    }
        
        # Scenario C: Refinement (thêm điều kiện)
        has_refinement_signal = any(signal in user_input_lower for signal in self.refinement_signals)
        
        if has_refinement_signal or (not has_change_signal and not mentioned_category):
            # Đang refine trong cùng category
            return {
                "intent_type": "refine",
                "new_category": current_category,
                "should_reset": False,
                "confidence": 0.7,
                "reason": "User is refining current search"
            }
        
        # Default: tiếp tục search hiện tại
        return {
            "intent_type": "refine",
            "new_category": current_category,
            "should_reset": False,
            "confidence": 0.5,
            "reason": "Continuing current search"
        }
    
    def _detect_category(self, user_input: str) -> Dict[str, Any]:
        """Detect category từ input (giống code cũ)"""
        user_input = user_input.lower().strip()
        
        # Keyword matching
        result = self._keyword_match(user_input)
        if result["confidence"] >= 0.9:
            return result
        
        # Embedding
        result = self._embedding_classify(user_input)
        if result["confidence"] > 0.7:
            return result
        
        return {
            "has_category": False,
            "category": None,
            "confidence": 0.0
        }
    
    def _keyword_match(self, text: str) -> Dict[str, Any]:
        matches = []
        for cat_name in self.categories:
            schema = get_schema(cat_name)
            for keyword in schema.keywords:
                if keyword in text:
                    matches.append({
                        "category": cat_name,
                        "keyword": keyword,
                        "confidence": 0.9
                    })
        
        if not matches:
            return {"has_category": False, "category": None, "confidence": 0.0}
        
        best_match = max(matches, key=lambda x: len(x["keyword"]))
        return {
            "has_category": True,
            "category": best_match["category"],
            "confidence": best_match["confidence"]
        }
    
    def _embedding_classify(self, text: str) -> Dict[str, Any]:
        self._load_embedding_model()
        
        if self.embedding_model == "not_available":
            return {"has_category": False, "category": None, "confidence": 0.0}
        
        from sentence_transformers import util
        query_emb = self.embedding_model.encode(text, convert_to_tensor=True)
        
        scores = {}
        for cat, cat_emb in self.category_embeddings.items():
            similarity = util.cos_sim(query_emb, cat_emb).item()
            scores[cat] = similarity
        
        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]
        
        if best_score < 0.4:
            return {"has_category": False, "category": None, "confidence": best_score}
        
        return {
            "has_category": True,
            "category": best_cat,
            "confidence": best_score
        }
    
    def _check_attribute_conflict(
        self,
        old_attrs: Dict[str, Any],
        new_attrs: Dict[str, Any]
    ) -> List[str]:
        """
        Kiểm tra attributes có conflict không
        
        Ví dụ:
        - old: {"loai": "sneaker"}
        - new: {"loai": "chạy bộ"}
        → conflict vì cùng attribute nhưng khác value
        """
        conflicts = []
        for attr, new_value in new_attrs.items():
            if attr in old_attrs and old_attrs[attr] != new_value:
                conflicts.append(attr)
        return conflicts
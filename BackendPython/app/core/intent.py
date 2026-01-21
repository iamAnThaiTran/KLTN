# app/core/intent.py

from typing import Optional, Dict, Any
import re
from .schema import get_all_categories, get_schema

class IntentDetector:
    """Phát hiện category từ user input"""
    
    def __init__(self):
        self.categories = get_all_categories()
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """Initialize sentence embedding model (lazy loading)"""
        self.embedding_model = None
        self.category_embeddings = None
    
    def _load_embedding_model(self):
        """Load model khi cần (không load lúc init)"""
        if self.embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                # Model nhẹ, support tiếng Việt
                self.embedding_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2'
                )
                
                # Pre-encode category descriptions
                from .schema import get_schema
                category_texts = {}
                
                for cat in self.categories:
                    schema = get_schema(cat)
                    # Kết hợp tên + keywords
                    category_texts[cat] = f"{cat} {' '.join(schema.keywords)}"
                
                self.category_embeddings = {
                    cat: self.embedding_model.encode(text, convert_to_tensor=True)
                    for cat, text in category_texts.items()
                }
            except ImportError:
                print("Warning: sentence-transformers not installed. Falling back to keyword matching.")
                self.embedding_model = "not_available"
    
    def detect(self, user_input: str) -> Dict[str, Any]:
        """
        Detect category từ user input
        
        Returns:
            {
                "has_category": bool,
                "category": str hoặc None,
                "confidence": float,
                "method": "keyword" | "embedding" | "llm"
            }
        """
        user_input = user_input.lower().strip()
        
        # Method 1: Keyword matching (fastest)
        result = self._keyword_match(user_input)
        if result["confidence"] >= 0.9:
            return result
        
        # Method 2: Sentence embedding similarity (fast + accurate)
        result = self._embedding_classify(user_input)
        if result["confidence"] > 0.7:
            return result
        
        # Method 3: Zero-shot LLM (slowest, most expensive, last resort)
        return self._llm_classify(user_input)
    
    def _keyword_match(self, text: str) -> Dict[str, Any]:
        """Match bằng keywords trong schema"""
        matches = []
        
        for cat_name in self.categories:
            schema = get_schema(cat_name)
            for keyword in schema.keywords:
                if keyword in text:
                    matches.append({
                        "category": cat_name,
                        "keyword": keyword,
                        "confidence": 0.9  # Keyword match có độ tin cậy cao
                    })
        
        if not matches:
            return {
                "has_category": False,
                "category": None,
                "confidence": 0.0,
                "method": "keyword"
            }
        
        # Nếu có nhiều match, chọn cái có keyword dài nhất (cụ thể nhất)
        best_match = max(matches, key=lambda x: len(x["keyword"]))
        
        return {
            "has_category": True,
            "category": best_match["category"],
            "confidence": best_match["confidence"],
            "method": "keyword"
        }
    
    def _embedding_classify(self, text: str) -> Dict[str, Any]:
        """
        Classify bằng sentence embeddings
        Nhanh hơn LLM, chính xác hơn keyword
        """
        self._load_embedding_model()
        
        if self.embedding_model == "not_available":
            # Fallback to keyword
            return {"has_category": False, "category": None, "confidence": 0.0, "method": "embedding"}
        
        from sentence_transformers import util
        
        # Encode query
        query_emb = self.embedding_model.encode(text, convert_to_tensor=True)
        
        # Calculate similarities
        scores = {}
        for cat, cat_emb in self.category_embeddings.items():
            similarity = util.cos_sim(query_emb, cat_emb).item()
            scores[cat] = similarity
        
        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]
        
        # Threshold
        if best_score < 0.4:  # Too low confidence
            return {
                "has_category": False,
                "category": None,
                "confidence": best_score,
                "method": "embedding"
            }
        
        return {
            "has_category": True,
            "category": best_cat,
            "confidence": best_score,
            "method": "embedding"
        }
    
    def _llm_classify(self, text: str) -> Dict[str, Any]:
        """
        Zero-shot classification với LLM
        Chỉ dùng khi keyword matching thất bại
        """
        from .llm_utils import call_llm
        
        prompt = f"""Classify the user query into ONE of these categories:
{', '.join(self.categories)}

If the query doesn't match any category, respond with "UNKNOWN".

Query: "{text}"

Respond ONLY with the category name (lowercase) or "UNKNOWN".
"""
        
        response = call_llm(prompt, max_tokens=10)
        category = response.strip().lower()
        
        if category == "unknown" or category not in self.categories:
            return {
                "has_category": False,
                "category": None,
                "confidence": 0.0,
                "method": "llm"
            }
        
        return {
            "has_category": True,
            "category": category,
            "confidence": 0.7,  # LLM confidence thấp hơn keyword
            "method": "llm"
        }

# ============================================
# HELPER: Phát hiện ý định mua quà
# ============================================
def is_gift_intent(text: str) -> bool:
    """Kiểm tra có phải ý định mua quà không"""
    gift_keywords = [
        "quà", "tặng", "gift", "biếu", "sinh nhật",
        "kỷ niệm", "valentine", "noel", "tết"
    ]
    text = text.lower()
    return any(kw in text for kw in gift_keywords)
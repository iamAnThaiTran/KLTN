# app/core/ranker.py

from typing import List, Dict, Any
from .llm_utils import call_llm

class ProductRanker:
    """
    Rank products và generate explanations
    Kết hợp rule-based + LLM
    """
    
    def rank(
        self, 
        products: List[Dict[str, Any]],
        user_attributes: Dict[str, Any],
        use_llm_explain: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank products và thêm explanations
        
        Returns:
            Sorted products với thêm:
            - final_score: Điểm cuối cùng
            - explanation: Lý do gợi ý (từ LLM hoặc rules)
        """
        
        # Step 1: Score từ matcher đã có rồi (match_score)
        # Step 2: Thêm các factors khác
        for product in products:
            product["final_score"] = self._calculate_final_score(
                product, user_attributes
            )
        
        # Step 3: Sort
        products.sort(key=lambda x: x["final_score"], reverse=True)
        
        # Step 4: Generate explanations
        for i, product in enumerate(products[:10]):  # Top 10 only
            if use_llm_explain:
                product["explanation"] = self._llm_explain(
                    product, user_attributes, rank=i+1
                )
            else:
                product["explanation"] = self._rule_explain(
                    product, user_attributes
                )
        
        return products
    
    def _calculate_final_score(
        self, 
        product: Dict[str, Any],
        user_attributes: Dict[str, Any]
    ) -> float:
        """
        Tính final score từ nhiều factors
        
        Score = match_score (0-100)
              + popularity_bonus (0-20)
              + price_penalty (-10 to 0)
        """
        base_score = product.get("match_score", 50)
        
        # Popularity (nếu có)
        popularity = product.get("popularity", 0)  # 0-100
        popularity_bonus = popularity * 0.2
        
        # Price penalty (nếu quá ngân sách)
        price_penalty = 0
        if "gia" in user_attributes:
            user_price = user_attributes["gia"]
            product_price = product.get("price", 0)
            
            if product_price > user_price * 1.2:  # Quá 20%
                price_penalty = -10
        
        return base_score + popularity_bonus + price_penalty
    
    def _rule_explain(
        self, 
        product: Dict[str, Any],
        user_attributes: Dict[str, Any]
    ) -> str:
        """
        Generate explanation bằng rules (không tốn LLM)
        """
        reasons = product.get("match_reasons", [])
        
        if not reasons:
            return "Sản phẩm phù hợp với yêu cầu của bạn."
        
        # Format đẹp
        positive = [r for r in reasons if "✓" in r]
        negative = [r for r in reasons if "✗" in r]
        
        explanation = ""
        
        if positive:
            explanation += "Phù hợp: " + ", ".join(positive) + ". "
        
        if negative:
            explanation += "Lưu ý: " + ", ".join(negative) + "."
        
        return explanation.strip()
    
    def _llm_explain(
        self, 
        product: Dict[str, Any],
        user_attributes: Dict[str, Any],
        rank: int
    ) -> str:
        """
        Generate explanation bằng LLM (chi tiết hơn, tự nhiên hơn)
        """
        
        prompt = f"""You are a product recommendation assistant.

User is looking for:
{self._format_user_requirements(user_attributes)}

Recommended product (rank #{rank}):
- Name: {product.get('name', 'N/A')}
- Price: {product.get('price', 'N/A')} VND
- Key features: {', '.join(product.get('match_reasons', []))}

Write a BRIEF (1-2 sentences) explanation of why this product is recommended.
Focus on how it matches user's needs.
Be natural and helpful, not salesy.

Explanation:"""
        
        explanation = call_llm(prompt, max_tokens=100).strip()
        
        return explanation
    
    def _format_user_requirements(self, attributes: Dict[str, Any]) -> str:
        """Format user attributes thành text dễ đọc"""
        items = [f"{k}: {v}" for k, v in attributes.items()]
        return "\n".join(items)
    
    def generate_comparison(
        self, 
        products: List[Dict[str, Any]],
        top_n: int = 3
    ) -> str:
        """
        Generate comparison giữa top N products (dùng LLM)
        """
        if len(products) < 2:
            return ""
        
        top_products = products[:top_n]
        
        prompt = f"""Compare these {len(top_products)} products:

"""
        
        for i, p in enumerate(top_products, 1):
            prompt += f"{i}. {p.get('name', 'N/A')} - {p.get('price', 'N/A')} VND\n"
            prompt += f"   Features: {', '.join(p.get('match_reasons', []))}\n\n"
        
        prompt += "Write a brief comparison (2-3 sentences) highlighting:\n"
        prompt += "- Main differences\n"
        prompt += "- Which product is best for which user\n\n"
        prompt += "Comparison:"
        
        comparison = call_llm(prompt, max_tokens=200).strip()
        
        return comparison
# app/core/orchestrator.py

from typing import Dict, Any, List
from .extractor import AttributeExtractor
from .dialogue import DialogueManager
from .matcher import ProductMatcher
from .ranker import ProductRanker
from app.crawler.multi_crawler import MultiCrawler
from .schema import get_schema
from .intent import EnhancedIntentDetector

class RecommendationOrchestrator:
    """
    Orchestrator cải tiến - xử lý intent phức tạp
    """
    
    def __init__(self):
        
        self.intent_detector = EnhancedIntentDetector()
        self.attribute_extractor = AttributeExtractor()
        self.dialogue_manager = DialogueManager()
        self.product_matcher = ProductMatcher()
        self.product_ranker = ProductRanker()
        self.crawler = MultiCrawler()
    
    async def process_query(
        self,
        user_input: str,
        conversation_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - xử lý intent phức tạp
        """
        print(f"Orchestrator: Processing user input: {user_input}")
        
        # Initialize state
        if conversation_state is None:
            conversation_state = {
                "has_category": False,
                "category": None,
                "extracted": {},
                "missing_required": [],
                "search_history": []  # Track lịch sử search
            }
        
        # ===== STEP 1: DETECT INTENT CHANGE =====
        intent_change = self.intent_detector.detect_intent_change(
            user_input,
            conversation_state
        )
        
        print(f"DEBUG: Intent detected: {intent_change['intent_type']} - {intent_change['reason']}")
        
        # ===== STEP 2: HANDLE BASED ON INTENT TYPE =====
        
        if intent_change["intent_type"] == "switch_category":
            # User đổi sang category khác → reset toàn bộ
            print(f"DEBUG: Switching from '{conversation_state.get('category')}' to '{intent_change['new_category']}'")
            
            # Save history
            if conversation_state.get("category"):
                conversation_state["search_history"].append({
                    "category": conversation_state["category"],
                    "extracted": conversation_state["extracted"].copy()
                })
            
            # Reset state
            conversation_state = {
                "has_category": True,
                "category": intent_change["new_category"],
                "extracted": {},
                "missing_required": [],
                "search_history": conversation_state["search_history"]
            }
        
        elif intent_change["intent_type"] == "switch_attribute":
            # User đổi attribute (cùng category) → replace conflicting attrs
            print(f"DEBUG: Switching attributes: {intent_change.get('conflicting_attributes')}")
            
            # Extract new attributes
            new_attrs = self.attribute_extractor.extract(
                user_input,
                conversation_state["category"]
            )
            
            # Replace conflicting attributes
            for attr in intent_change.get("conflicting_attributes", []):
                if attr in new_attrs["extracted"]:
                    old_value = conversation_state["extracted"].get(attr)
                    new_value = new_attrs["extracted"][attr]
                    print(f"DEBUG: Replacing {attr}: '{old_value}' → '{new_value}'")
                    conversation_state["extracted"][attr] = new_value
        
        elif intent_change["intent_type"] == "refine":
            # User refine (thêm điều kiện) → merge attributes
            print(f"DEBUG: Refining search in category '{conversation_state['category']}'")
            
            new_attrs = self.attribute_extractor.extract(
                user_input,
                conversation_state["category"]
            )
            
            # Merge (không overwrite)
            for attr, value in new_attrs["extracted"].items():
                if attr not in conversation_state["extracted"]:
                    conversation_state["extracted"][attr] = value
                    print(f"DEBUG: Adding attribute {attr}: '{value}'")
        
        elif intent_change["intent_type"] == "new_search":
            # First search
            if intent_change["new_category"]:
                conversation_state["has_category"] = True
                conversation_state["category"] = intent_change["new_category"]
        
        # ===== STEP 3: EXTRACT ATTRIBUTES (nếu chưa extract ở trên) =====
        if intent_change["intent_type"] not in ["switch_attribute", "refine"]:
            if conversation_state.get("has_category"):
                extract_result = self.attribute_extractor.extract(
                    user_input,
                    conversation_state["category"]
                )
                conversation_state["extracted"].update(extract_result["extracted"])
        
        # ===== STEP 4: CHECK MISSING REQUIRED =====
        if not conversation_state.get("has_category"):
            # Chưa có category
            question = self.dialogue_manager.generate_question({
                "has_category": False,
                "user_input": user_input
            })
            return {
                "status": "need_info",
                "question": question["question"],
                "options": question["options"],
                "state": conversation_state
            }
        
        schema = get_schema(conversation_state["category"])
        conversation_state["missing_required"] = [
            attr for attr, constraint in schema.attributes.items()
            if constraint.required and attr not in conversation_state["extracted"]
        ]
        
        if conversation_state["missing_required"]:
            question = self.dialogue_manager.generate_question(conversation_state)
            return {
                "status": "need_info",
                "question": question["question"],
                "options": question["options"],
                "attribute_name": question.get("attribute_name"),
                "state": conversation_state
            }
        
        # ===== STEP 5: CRAWL & MATCH & RANK =====
        products = await self.crawler.crawl(
            category=conversation_state["category"],
            attributes=conversation_state["extracted"]
        )
        
        if not products:
            return {
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp.",
                "state": conversation_state
            }
        
        products = [self._normalize_product(p) for p in products]
        
        matched_products = self.product_matcher.match_products(
            products,
            conversation_state["category"],
            conversation_state["extracted"]
        )
        
        if not matched_products:
            return {
                "status": "no_results",
                "message": "Không có sản phẩm nào phù hợp với yêu cầu.",
                "state": conversation_state
            }
        
        ranked_products = self.product_ranker.rank(
            matched_products,
            conversation_state["extracted"],
            use_llm_explain=True
        )
        
        comparison = self.product_ranker.generate_comparison(ranked_products, top_n=3)
        
        return {
            "status": "results",
            "products": ranked_products[:20],
            "comparison": comparison,
            "total_found": len(matched_products),
            "intent_info": {  # Thêm thông tin về intent để UI có thể hiển thị
                "type": intent_change["intent_type"],
                "reason": intent_change["reason"]
            },
            "state": conversation_state
        }
    
    def _normalize_product(self, product: dict) -> dict:
        if "title" in product and "name" not in product:
            product["name"] = product["title"]
        return product
    """
    Main orchestrator - điều phối toàn bộ pipeline
    """
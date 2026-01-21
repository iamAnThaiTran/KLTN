# app/core/orchestrator.py

from typing import Dict, Any, List
from .intent import IntentDetector
from .extractor import AttributeExtractor
from .dialogue import DialogueManager
from .matcher import ProductMatcher
from .ranker import ProductRanker
from app.crawler.crawler import TikiCrawler
from .schema import get_schema

class RecommendationOrchestrator:
    """
    Main orchestrator - điều phối toàn bộ pipeline
    """
    
    
    def __init__(self):
        """
        Args:
            crawler: Your existing crawler instance
                     Phải có method: crawler.crawl(category, attributes)
        """
        self.intent_detector = IntentDetector()
        self.attribute_extractor = AttributeExtractor()
        self.dialogue_manager = DialogueManager()
        self.product_matcher = ProductMatcher()
        self.product_ranker = ProductRanker()
        self.crawler = TikiCrawler()
    
    async def process_query(
        self, 
        user_input: str,
        conversation_state: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process user query - MAIN ENTRY POINT
        
        Args:
            user_input: User's message
            conversation_state: State từ turn trước (nếu có)
            
        Returns:
            {
                "status": "need_info" | "searching" | "results",
                "question": str (nếu cần hỏi),
                "options": [...] (nếu cần hỏi),
                "products": [...] (nếu có kết quả),
                "state": {...} (để lưu cho turn sau)
            }
        """
        print('conversation state: ', conversation_state)
        # Initialize state
        if conversation_state is None:
            conversation_state = {
                "has_category": False,
                "category": None,
                "extracted": {},
                "missing_required": []
            }
        
        # ===== STEP 1: INTENT DETECTION =====
        # LUÔN detect intent - để nhận diện category mới nếu user thay đổi
        intent_result = self.intent_detector.detect(user_input)
        
        if not intent_result["has_category"]:
            # User không mention category → dùng category cũ nếu có
            if not conversation_state.get("has_category"):
                # Lần đầu không có category
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
            # Nếu có category cũ, tiếp tục dùng
        else:
            # User mention category mới
            new_category = intent_result["category"]
            
            # Nếu category khác với cũ → reset state
            if conversation_state.get("has_category") and conversation_state.get("category") != new_category:
                print(f"DEBUG: Category thay đổi từ '{conversation_state['category']}' sang '{new_category}' - reset state")
                conversation_state = {
                    "has_category": True,
                    "category": new_category,
                    "extracted": {},
                    "missing_required": []
                }
            else:
                # Category mới hoặc không thay đổi
                conversation_state["has_category"] = True
                conversation_state["category"] = new_category
        
        # ===== STEP 2: ATTRIBUTE EXTRACTION =====
        # Extract attributes từ user input hiện tại
        extract_result = self.attribute_extractor.extract(
            user_input,
            conversation_state["category"]
        )
        
        # Nếu user extract được attributes mới, thay thế (không merge)
        # Ví dụ: lần 1 "giày sneaker", lần 2 "giày chạy bộ" → loai thay từ sneaker thành chạy bộ
        if extract_result["extracted"]:
            conversation_state["extracted"] = extract_result["extracted"]
            print(f"DEBUG: Updated attributes: {conversation_state['extracted']}")
        
        schema = get_schema(conversation_state["category"])
        conversation_state["missing_required"] = [
            attr for attr, constraint in schema.attributes.items()
            if constraint.required and attr not in conversation_state["extracted"]
        ]
        
        # ===== STEP 3: CHECK COMPLETENESS =====
        if conversation_state.get("missing_required"):
            # Thiếu required attributes
            question = self.dialogue_manager.generate_question(conversation_state)
            
            return {
                "status": "need_info",
                "question": question["question"],
                "options": question["options"],
                "attribute_name": question.get("attribute_name"),
                "state": conversation_state
            }
        
        # ===== STEP 4: CRAWL =====
        # Đủ thông tin rồi, bắt đầu crawl
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
        
        # ===== STEP 5: PRODUCT MATCHING =====
        products = [self.normalize_product(p) for p in products]
        print(f"DEBUG: Products sau normalize: {len(products)}")
        print(f"DEBUG: Sample product: {products[0] if products else 'NO PRODUCTS'}")
        
        matched_products = self.product_matcher.match_products(
            products,
            conversation_state["category"],
            conversation_state["extracted"]
        )
        
        print(f"DEBUG: Matched products: {len(matched_products)}")
        print(f"DEBUG: Extracted attributes: {conversation_state['extracted']}")
        
        if not matched_products:
            return {
                "status": "no_results",
                "message": "Không có sản phẩm nào phù hợp với yêu cầu.",
                "state": conversation_state
            }
        
        # ===== STEP 6: RANKING + EXPLAIN =====
        ranked_products = self.product_ranker.rank(
            matched_products,
            conversation_state["extracted"],
            use_llm_explain=True  # Set False nếu muốn nhanh hơn
        )
        
        # Generate comparison cho top 3
        comparison = self.product_ranker.generate_comparison(ranked_products, top_n=3)
        
        # ===== STEP 7: RETURN RESULTS =====
        return {
            "status": "results",
            "products": ranked_products[:20],  # Top 20
            "comparison": comparison,
            "total_found": len(matched_products),
            "state": conversation_state
        }
    
    def normalize_product(self, product: dict) -> dict:
        if "title" in product and "name" not in product:
            product["name"] = product["title"]
        return product

    
    def update_state(
        self, 
        conversation_state: Dict[str, Any],
        user_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update state khi user trả lời câu hỏi
        
        Args:
            conversation_state: State hiện tại
            user_response: {
                "question_type": "category" | "attribute",
                "value": str,
                "attribute_name": str (nếu là attribute)
            }
        """
        
        if user_response["question_type"] == "category":
            conversation_state["has_category"] = True
            conversation_state["category"] = user_response["value"]
        
        elif user_response["question_type"] == "attribute":
            attr_name = user_response["attribute_name"]
            value = user_response["value"]
            
            if value != "skip":  # User không bỏ qua
                conversation_state["extracted"][attr_name] = value
            
            # Remove từ missing_required
            if attr_name in conversation_state.get("missing_required", []):
                conversation_state["missing_required"].remove(attr_name)
        
        return conversation_state
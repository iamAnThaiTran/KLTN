# app/services/recommender_service.py
"""
RecommendatorService - Microservice for intent analysis & ranking
Responsibilities:
- Intent type detection (specific/abstract/comparison)
- Request classification (7-case routing)
- Dialogue question generation
- Product ranking and filtering
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from app.services.base_service import BaseService
from app.core.intent_mapper import IntentMapper
from app.core.dialogue import DialogueManager
from app.core.ranker import ProductRanker

logger = logging.getLogger(__name__)

class RecommendatorService(BaseService):
    """
    Recommender Service - Intent analysis & request routing
    
    Provides unified interface for:
    - Intent detection from user input
    - Request classification (7 cases)
    - Dialogue question generation
    - Product ranking and filtering
    """
    
    SERVICE_NAME = "RecommendatorService"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TIMEOUT = 10
    
    # Case definitions
    CASE_NAMES = {
        1: "clear_request",
        2: "specific_with_schema",
        3: "unclear_no_schema",
        4: "abstract_intent",
        5: "intent_shift",
        6: "incremental_refinement",
        7: "comparison_advisory",
        8: "dynamic_category_creation"
    }
    
    def __init__(self):
        super().__init__()
        
        # Initialize dependencies
        self.intent_mapper = IntentMapper()
        self.dialogue_manager = DialogueManager()
        self.product_ranker = ProductRanker()
        
        self.log_operation("initialized", "info")
    
    # ========================================================================
    # INTENT DETECTION
    # ========================================================================
    
    def detect_intent(
        self,
        user_input: str,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect intent from user input
        
        Args:
            user_input: User's message
            conversation_state: Current conversation context
        
        Returns:
        {
            "intent_type": "specific|abstract|comparison|none",
            "confidence": 0.85,
            "categories": ["Giày"],
            "product_name": "Nike",
            "intent": {...},
            "is_new_category": False
        }
        """
        self.track_request("detect_intent")
        
        try:
            self.log_operation(
                "detect_intent_start",
                "info",
                input_length=len(user_input)
            )
            
            # Use IntentMapper to detect
            intent_result = self.intent_mapper.map_intent(
                user_input,
                conversation_state
            )
            
            intent_type = intent_result.get("intent_type", "none")
            confidence = intent_result.get("confidence", 0.0)
            
            self.log_operation(
                "detect_intent_success",
                "info",
                intent_type=intent_type,
                confidence=f"{confidence:.2f}"
            )
            
            return intent_result
            
        except Exception as e:
            return self.handle_service_error(
                "detect_intent",
                e,
                context={"input_length": len(user_input)},
                raise_error=False
            )
    
    # ========================================================================
    # REQUEST CLASSIFICATION
    # ========================================================================
    
    def classify_request(
        self,
        user_input: str,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify request into one of 8 cases
        
        Args:
            user_input: User's input
            conversation_state: Conversation context
        
        Returns:
        {
            "case": 1..8,
            "case_name": "clear_request",
            "reason": "High confidence specific request",
            "action": "crawl|refine|clarify|compare",
            "data": {...}
        }
        """
        self.track_request("classify_request")
        
        try:
            # Get detected intent (from STEP 0 of orchestrator)
            detected_intent = conversation_state.get("detected_intent", {})
            intent_type = detected_intent.get("intent_type", "none")
            confidence = detected_intent.get("confidence", 0.0)
            categories = detected_intent.get("categories", [])
            is_new_category = detected_intent.get("is_new_category", False)
            
            self.log_operation(
                "classify_request_start",
                "info",
                intent_type=intent_type,
                confidence=f"{confidence:.2f}",
                has_category=bool(categories)
            )
            
            # Classification logic (simplified)
            case = self._classify_case(
                intent_type,
                confidence,
                categories,
                is_new_category,
                conversation_state
            )
            
            case_name = self.CASE_NAMES.get(case, "unknown")
            action = self._get_action_for_case(case)
            
            self.log_operation(
                "classify_request_success",
                "info",
                case=case,
                case_name=case_name,
                action=action
            )
            
            return {
                "case": case,
                "case_name": case_name,
                "action": action,
                "reason": self._get_reason_for_case(case, intent_type, confidence),
                "data": self._get_case_data(
                    case,
                    intent_type,
                    categories,
                    conversation_state
                )
            }
            
        except Exception as e:
            return self.handle_service_error(
                "classify_request",
                e,
                raise_error=False
            )
    
    # ========================================================================
    # DIALOGUE QUESTION GENERATION
    # ========================================================================
    
    def generate_questions(
        self,
        category: str,
        extracted_attributes: Dict[str, Any],
        missing_attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Generate clarifying questions for user
        
        Args:
            category: Product category
            extracted_attributes: Already extracted attributes
            missing_attributes: Required attributes still needed
        
        Returns:
        {
            "questions": [
                {
                    "type": "category|attribute",
                    "attribute_name": "size",
                    "display_name": "Kích cỡ",
                    "text": "Bạn cần size mấy?",
                    "options": ["35", "36", "37", "38", "39", "40"]
                }
            ]
        }
        """
        self.track_request("generate_questions")
        
        try:
            self.log_operation(
                "generate_questions_start",
                "info",
                category=category,
                missing_count=len(missing_attributes)
            )
            
            questions = self.dialogue_manager.generate_questions(
                category=category,
                extracted_attributes=extracted_attributes,
                missing_attributes=missing_attributes
            )
            
            self.log_operation(
                "generate_questions_success",
                "info",
                question_count=len(questions)
            )
            
            return {
                "success": True,
                "questions": questions,
                "question_count": len(questions)
            }
            
        except Exception as e:
            return self.handle_service_error(
                "generate_questions",
                e,
                context={"category": category},
                raise_error=False
            )
    
    # ========================================================================
    # PRODUCT RANKING & FILTERING
    # ========================================================================
    
    def rank_products(
        self,
        products: List[Dict[str, Any]],
        extracted_attributes: Dict[str, Any],
        user_input: str
    ) -> Dict[str, Any]:
        """
        Rank and filter products based on extracted attributes
        
        Args:
            products: List of products to rank
            extracted_attributes: Extracted attributes for scoring
            user_input: Original user input for semantic matching
        
        Returns:
        {
            "ranked_products": [
                {
                    "id": 1,
                    "title": "Nike Air Force 1",
                    "price": 1200000,
                    "score": 0.92,
                    "match_reasons": ["Đúng hãng", "Đúng size"]
                }
            ],
            "total_count": 24,
            "filtered_count": 18
        }
        """
        self.track_request("rank_products")
        
        if not products:
            return {
                "success": True,
                "ranked_products": [],
                "total_count": 0,
                "filtered_count": 0
            }
        
        try:
            self.log_operation(
                "rank_products_start",
                "info",
                product_count=len(products),
                attribute_count=len(extracted_attributes)
            )
            
            # Rank using ProductRanker
            ranked = self.product_ranker.rank_products(
                products=products,
                attributes=extracted_attributes,
                query=user_input
            )
            
            # Filter out low-scoring products
            threshold = 0.3  # Minimum score
            filtered = [p for p in ranked if p.get("score", 0) >= threshold]
            
            self.log_operation(
                "rank_products_success",
                "info",
                ranked_count=len(ranked),
                filtered_count=len(filtered),
                top_score=ranked[0].get("score", 0) if ranked else 0
            )
            
            return {
                "success": True,
                "ranked_products": filtered,
                "total_count": len(products),
                "filtered_count": len(filtered),
                "top_match_score": ranked[0].get("score", 0) if ranked else 0
            }
            
        except Exception as e:
            return self.handle_service_error(
                "rank_products",
                e,
                context={"product_count": len(products)},
                raise_error=False
            )
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _classify_case(
        self,
        intent_type: str,
        confidence: float,
        categories: List[str],
        is_new_category: bool,
        conversation_state: Dict[str, Any]
    ) -> int:
        """Determine which case (1-8) the request falls into"""
        
        # CASE 8: Dynamic category (new category not in DB)
        if is_new_category and categories:
            return 8
        
        # CASE 7: Comparison/advisory
        if intent_type == "comparison":
            return 7
        
        # CASE 5: Intent shift (context reset)
        if conversation_state.get("has_category"):
            last_input = conversation_state.get("last_user_input", "").strip().lower()
            current_intent = intent_type
            if last_input and current_intent != conversation_state.get("last_intent_type"):
                return 5
        
        # CASE 6: Incremental refinement
        if conversation_state.get("has_category") and conversation_state.get("extracted"):
            return 6
        
        # CASE 4: Abstract intent
        if intent_type == "abstract":
            return 4
        
        # CASE 1: Clear/Specific (high confidence)
        if intent_type == "specific" and confidence >= 0.65 and categories:
            return 1
        
        # CASE 2: Specific but lower confidence (0.5 - 0.65)
        if intent_type == "specific" and 0.5 <= confidence < 0.65 and categories:
            return 2
        
        # DEFAULT: CASE 3 - Unclear intent
        return 3
    
    def _get_action_for_case(self, case: int) -> str:
        """Get action name for case"""
        actions = {
            1: "crawl",
            2: "refine",
            3: "clarify",
            4: "clarify",
            5: "reset_and_crawl",
            6: "refine",
            7: "advise",
            8: "create_category_and_crawl"
        }
        return actions.get(case, "clarify")
    
    def _get_reason_for_case(
        self,
        case: int,
        intent_type: str,
        confidence: float
    ) -> str:
        """Get human-readable reason for case classification"""
        reasons = {
            1: f"Clear request with {confidence:.0%} confidence",
            2: f"Specific request but {confidence:.0%} confidence (need refinement)",
            3: "Unclear intent or low confidence",
            4: "Abstract intent (high-level need)",
            5: "Intent shift detected",
            6: "Incremental refinement of previous search",
            7: "Comparison or advisory request",
            8: "New category needs schema creation"
        }
        return reasons.get(case, "General request")
    
    def _get_case_data(
        self,
        case: int,
        intent_type: str,
        categories: List[str],
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get case-specific data"""
        data = {
            "intent_type": intent_type,
            "categories": categories,
            "should_crawl": case in [1, 2, 5, 8]
        }
        
        if case == 8:  # New category
            data["new_category"] = categories[0] if categories else None
            data["should_create_schema"] = True
        
        if case in [2, 3]:  # Need refinement
            data["should_ask_questions"] = True
        
        return data
    
    def validate_inputs(self, **kwargs) -> bool:
        """Validate service inputs"""
        return True

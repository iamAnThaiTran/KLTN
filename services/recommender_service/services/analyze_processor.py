# services/analyze_processor.py
"""
Background processor for async analyze jobs
Handles long-running intent analysis and product search
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.orchestrator import RecommendationOrchestrator
from core.context_analyzer import get_context_analyzer
from services.session_manager_factory import get_session_manager
from db.sku_repository import SKURepository
from config.database_orm import get_db
from services.user_service_client import UserServiceClient
from .job_manager import get_job_manager
from services.product_service_client import ProductServiceClient

logger = logging.getLogger("analyze_processor")


class AnalyzeProcessor:
    """Processes analyze jobs asynchronously"""
    
    def __init__(self):
        self.orchestrator = RecommendationOrchestrator()
        self.context_analyzer = get_context_analyzer()
        self.session_manager = get_session_manager()
        self.sku_repo = SKURepository()
        self.job_manager = get_job_manager()
        self.user_service_client = UserServiceClient()
        self.product_service_client = ProductServiceClient()
    
    async def process_analyze_job(
        self,
        job_id: str,
        user_input: str,
        conversation_id: Optional[str] = None,
        current_user_id: Optional[int] = None
    ) -> None:
        try:
            
            # ====== STEP 1: Create or fetch session ======
            logger.info(f"[Job {job_id}] STEP 1: conversation_id input = {conversation_id}")
            if not conversation_id:
                conversation_id = self.session_manager.create_session()
                conversation_state = None
                logger.info(f"[Job {job_id}] Created NEW session: {conversation_id}")
            else:
                logger.info(f"[Job {job_id}] Using existing conversation_id: {conversation_id}")
                if not self.session_manager.session_exists(conversation_id):
                    error_msg = f"Session {conversation_id} not found"
                    logger.error(f"[Job {job_id}] {error_msg}")
                    self.job_manager.set_job_error(job_id, error_msg)
                    return
                
                conversation_state = self.session_manager.get_session_dict(conversation_id)
                # logger.info(f"[Job {job_id}] Fetched existing session state: {conversation_state}")
            
            # Initialize state if needed
            if conversation_state is None:
                conversation_state = {
                    "has_category": False,
                    "category": None,
                    "extracted": {},
                    "missing_required": [],
                    "search_history": [],
                    "attributes_asked": [],
                    "last_crawl_params": None,
                }
            
            logger.info(f"[Job {job_id}] Session state after loading: search_history = {conversation_state.get('search_history')}, category = {conversation_state.get('category')}")
            
            # ====== STEP 2: Reconstruct intent if follow-up, or detect intent if first query ======
            user_input_to_process = user_input
            has_search_history = conversation_state.get("search_history") and len(conversation_state.get("search_history", [])) > 0
            logger.info(f"[Job {job_id}] has_search_history = {has_search_history}")
            
            if has_search_history:
                # Follow-up query: reconstruct from context
                logger.info(f"[Job {job_id}] 🔄 FOLLOW-UP QUERY detected. Previous searches: {conversation_state.get('search_history')}")
                result_dict = self.context_analyzer.reconstruct_intent(
                    user_input=user_input,
                    conversation_state=conversation_state
                )
                merged_intent = result_dict["intent"]
                intent_type = result_dict.get("intent_type", "specific")
                user_input_to_process = merged_intent
                logger.info(f"[Job {job_id}] Merged intent: '{merged_intent}'")
                
                conversation_state["merged_intent"] = merged_intent
                
                # Store intent_type for orchestrator
                conversation_state["detected_intent"] = {
                    "intent_type": intent_type
                }
                
                if result_dict.get("category_changed"):
                    conversation_state["search_history"] = [user_input]
                    conversation_state["extracted"] = {}
                    conversation_state["category"] = None
                    conversation_state["has_category"] = False
            else:
                # 🆕 First query: detect intent_type via LLM (no history needed)
                logger.info(f"[Job {job_id}] 🆕 FIRST QUERY detected")
                intent_type = self.context_analyzer.detect_first_query_intent_type(user_input)
                logger.info(f"[Job {job_id}] First query - no merged intent, using raw input: '{user_input}'")
                
                # Store intent_type for orchestrator
                conversation_state["detected_intent"] = {
                    "intent_type": intent_type
                }
            
            logger.info(f"[Job {job_id}] Processing input: '{user_input}' → '{user_input_to_process}' (Intent type: {conversation_state['detected_intent']['intent_type']})")
            logger.info(f"[Job {job_id}] Current category: {conversation_state.get('category')}, extracted: {conversation_state.get('extracted')}")
            orch_result = await self.orchestrator.process_query(
                user_input=user_input_to_process,
                conversation_state=conversation_state
            )
            
            if "state" in orch_result:
                conversation_state = orch_result["state"]
                self.session_manager.set_session(conversation_id, conversation_state)
            
            # ====== STEP 4: Update search history ======
            if "search_history" not in conversation_state:
                conversation_state["search_history"] = []
            
            conversation_state["search_history"] = self._update_search_history(
                conversation_state["search_history"],
                user_input
            )
            logger.info(f"[Job {job_id}] Updated search history: {conversation_state['search_history']}")
            self.session_manager.set_session(conversation_id, conversation_state)
            logger.info(f"[Job {job_id}] Session saved to session_manager")
            
            # ====== STEP 5: Extract results from orchestrator (needed for save logic) ======
            orch_status = orch_result.get("status")
            products = orch_result.get("products", [])
            results_count = len(products) if products else 0
            
            # ====== STEP 6: Save to DB if authenticated ======
            if current_user_id:
                try:
                    category_for_db = conversation_state.get("category")
                    await self.user_service_client.record_search(
                        user_id=str(current_user_id),
                        query=user_input,
                        category=category_for_db,
                        results_count=results_count
                    )
                    logger.info(f"[Job {job_id}] ✅ Saved search history for user {current_user_id} to UserService")
                except Exception as e:
                    logger.warning(f"[Job {job_id}] ⚠️ Failed to save search history to UserService: {e}")
            
            # ====== STEP 7: Handle orchestrator response ======
            
            # Handle special statuses (need_info, no_results, error)
            if orch_status in ["need_info", "no_results", "error"]:
                if orch_status == "need_info":
                    logger.info(f"[Job {job_id}] 💬 Needs clarification")
                    result = {
                        "status": "need_info",
                        "question": orch_result.get("question"),
                        "options": orch_result.get("options", []),
                        "case": orch_result.get("case"),
                        "conversation_id": conversation_id,
                        "search_history": conversation_state.get("search_history", [])
                    }
                elif orch_status == "no_results":
                    logger.info(f"[Job {job_id}] 🔍 No products found")
                    result = {
                        "status": "no_results",
                        "message": "Không tìm thấy sản phẩm phù hợp",
                        "conversation_id": conversation_id,
                        "search_history": conversation_state.get("search_history", [])
                    }
                else:  # error
                    logger.error(f"[Job {job_id}] ❌ Error")
                    error_msg = orch_result.get("message", "Lỗi xử lý")
                    self.job_manager.set_job_error(job_id, error_msg)
                    return
                
                self.job_manager.set_job_result(job_id, result)
                return
            
            # ====== STEP 7: Build final response from orchestrator results ======
            # Orchestrator already processed everything and built answer
            products = orch_result.get("products", [])
            total_products = orch_result.get("total_found", len(products))
            category = conversation_state.get("category", "")
            filters = orch_result.get("filters", [])  # ✅ Get filters from orchestrator
            
            result = {
                "success": True,
                "category": category,
                "answer": orch_result.get("answer"),  # ✅ Include descriptive answer from orchestrator
                "filters": filters,  # ✅ Include filters
                "products": products,
                "total": total_products,
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
            
            logger.info(f"[Job {job_id}] ✅ Completed: {len(products)} products found")
            logger.info(f"[Job {job_id}] 📝 Answer: {result.get('answer', 'N/A')}")
            logger.info(f"[Job {job_id}] 🏷️ Filters: {len(filters)} filter groups")
            self.job_manager.set_job_result(job_id, result)
            
        except Exception as e:
            logger.error(f"[Job {job_id}] ❌ Error: {e}")
            logger.exception("Error details")
            self.job_manager.set_job_error(job_id, str(e))
    
    def _update_search_history(self, history: list, new_input: str) -> list:
        """Add to search history, keep last 10"""
        if new_input not in history:
            history.append(new_input)
        return history[-10:]
    
    def _generate_hints_from_filters(self, category: str, filter_groups: list) -> list:
        """Generate user-friendly filter hints"""
        hints = []
        if not filter_groups:
            return hints
        
        enum_filters = [f for f in filter_groups if f.get('data_type') == 'enum']
        if enum_filters:
            filter_names = ", ".join([f['display_name'] for f in enum_filters[:3]])
            hints.append(f"Bạn có thể lọc theo {filter_names}")
        
        return hints


# Global instance
_processor = None


def get_analyze_processor() -> AnalyzeProcessor:
    """Get or create processor singleton"""
    global _processor
    if _processor is None:
        _processor = AnalyzeProcessor()
    return _processor

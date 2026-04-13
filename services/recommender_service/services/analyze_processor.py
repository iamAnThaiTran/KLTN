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
from services.user_service import UserService
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
        self.user_service = UserService()
        self.product_service_client = ProductServiceClient()
    
    async def process_analyze_job(
        self,
        job_id: str,
        user_input: str,
        conversation_id: Optional[str] = None,
        current_user_id: Optional[int] = None
    ) -> None:
        """
        Process analyze job in background
        
        Args:
            job_id: Job ID for tracking
            user_input: User's search input
            conversation_id: Optional conversation context
            current_user_id: Optional authenticated user ID
        """
        try:
            logger.info(f"[Job {job_id}] 🔄 Processing: {user_input}")
            
            # ====== STEP 1: Create or fetch session ======
            if not conversation_id:
                conversation_id = self.session_manager.create_session()
                conversation_state = None
                logger.info(f"[Job {job_id}] 🆕 NEW CONVERSATION: {conversation_id}")
            else:
                if not self.session_manager.session_exists(conversation_id):
                    error_msg = f"Session {conversation_id} not found"
                    logger.error(f"[Job {job_id}] {error_msg}")
                    self.job_manager.set_job_error(job_id, error_msg)
                    return
                
                conversation_state = self.session_manager.get_session_dict(conversation_id)
                logger.info(f"[Job {job_id}] 📝 EXISTING CONVERSATION: {conversation_id}")
            
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
            
            # ====== STEP 2: Reconstruct intent if follow-up ======
            user_input_to_process = user_input
            is_new_query = not conversation_id or "search_history" not in conversation_state
            
            if not is_new_query and conversation_state.get("search_history"):
                logger.info(f"[Job {job_id}] 🔄 RECONSTRUCTING INTENT")
                result_dict = self.context_analyzer.reconstruct_intent(
                    user_input=user_input,
                    conversation_state=conversation_state
                )
                user_input_to_process = result_dict["intent"]
                
                if result_dict.get("category_changed"):
                    logger.info(f"[Job {job_id}] 🔄 CATEGORY CHANGE DETECTED")
                    conversation_state["search_history"] = [user_input]
                    conversation_state["extracted"] = {}
                    conversation_state["category"] = None
                    conversation_state["has_category"] = False
            
            # ====== STEP 3: Process with orchestrator ======
            logger.info(f"[Job {job_id}] Processing: '{user_input_to_process}'")
            
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
            self.session_manager.set_session(conversation_id, conversation_state)
            
            # ====== STEP 5: Save to DB if authenticated ======
            if current_user_id:
                try:
                    category_for_db = conversation_state.get("category")
                    self.user_service.save_search_query(
                        user_id=current_user_id,
                        query=user_input,
                        category_name=category_for_db,
                        session_id=conversation_id
                    )
                    logger.info(f"[Job {job_id}] ✅ Saved search history for user {current_user_id}")
                except Exception as e:
                    logger.warning(f"[Job {job_id}] ⚠️ Failed to save search history: {e}")
            
            # ====== STEP 6: Handle special status ======
            products = orch_result.get("products", [])
            orch_status = orch_result.get("status")
            
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
                self.job_manager.set_job_result(job_id, result)
                return
            
            if orch_status == "no_results":
                logger.info(f"[Job {job_id}] 🔍 No products found")
                result = {
                    "status": "no_results",
                    "message": "Không tìm thấy sản phẩm phù hợp",
                    "conversation_id": conversation_id,
                    "search_history": conversation_state.get("search_history", [])
                }
                self.job_manager.set_job_result(job_id, result)
                return
            
            if orch_status == "error":
                logger.error(f"[Job {job_id}] ❌ Error")
                error_msg = orch_result.get("message", "Lỗi xử lý")
                self.job_manager.set_job_error(job_id, error_msg)
                return
            
            # ====== STEP 7: Fetch filters ======
            filter_groups = []
            category = conversation_state.get("category", "")
            
            if category:
                try:
                    # 📤 Call ProductService to fetch filters (not direct DB)
                    available_filters = await self.product_service_client.get_filters(category)
                    filter_groups = [
                        {
                            "attribute_name": f.get('name') or f.get('attribute_name'),
                            "display_name": f.get('display_name') or f.get('name') or f.get('attribute_name'),
                            "data_type": f.get('type') or f.get('data_type') or 'text',
                            "options": [
                                {
                                    "attribute_value": val,
                                    "product_count": 0  # ProductService doesn't return counts
                                }
                                for val in f.get('values', [])
                            ] if f.get('values') else []
                        }
                        for f in available_filters
                    ]
                    logger.info(f"[Job {job_id}] ✅ Fetched {len(filter_groups)} filters from ProductService")
                except Exception as e:
                    logger.warning(f"[Job {job_id}] ⚠️ Failed to fetch filters: {e}. Continuing without filters...")
                    # Don't fail - filters are optional, continue with results
            
            # ====== Build final response ======
            total_products = orch_result.get("total_found", len(products))
            
            result = {
                "success": True,
                "category": category,
                "clarifying_hints": self._generate_hints_from_filters(category, filter_groups),
                "filters": filter_groups,
                "products": products,
                "total": total_products,
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
            
            logger.info(f"[Job {job_id}] ✅ Completed: {len(products)} products found")
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

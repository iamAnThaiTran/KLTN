"""
RecommendatorService - Microservice for intent analysis and product recommendation
Port: 8002

Handles:
- User intent detection and analysis via /api/analyze
- Context management and conversation sessions  
- Classification into 7 cases
- Clarification questions
- Product recommendation orchestration
"""

import asyncio
import logging
import traceback
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logger = logging.getLogger("recommender")

# ============================================================================
# Import local modules (independent service)
# ============================================================================
from core.orchestrator import RecommendationOrchestrator
from core.context_analyzer import get_context_analyzer
from services.session_manager_factory import get_session_manager
from db.sku_repository import SKURepository
from config.database_orm import Base, engine, get_db
from config.auth_middleware import get_current_user_optional
from services.user_service import UserService
from models.user_models import User

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="RecommendatorService",
    description="Microservice for intent analysis and product recommendation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        traceback.print_exc()

# ============================================================================
# Initialize Components
# ============================================================================

session_manager = get_session_manager()
orchestrator = RecommendationOrchestrator()
context_analyzer = get_context_analyzer()
sku_repo = SKURepository()

logger.info(f"[Recommender] Session storage: {session_manager.get_storage_type()}")
logger.info(f"[Recommender] Orchestrator initialized")

# ============================================================================
# Models
# ============================================================================

class QueryRequest(BaseModel):
    """Query request model"""
    user_input: str
    conversation_id: Optional[str] = None

class ResponseUpdate(BaseModel):
    """User response to clarification question"""
    conversation_id: str
    question_type: str
    value: str
    attribute_name: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

async def _save_search_history_if_user(
    current_user: Optional[User],
    db: Session,
    user_input: str,
    category_name: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Save search history if user authenticated"""
    if not current_user:
        return None
    
    try:
        search_record = UserService.save_search_query(
            db=db,
            user_id=current_user.id,
            query=user_input,
            category_name=category_name,
            session_id=session_id
        )
        logger.info(f"✅ Saved search history for user {current_user.id}")
        return search_record.id
    except Exception as e:
        logger.warning(f"⚠️ Failed to save search history: {e}")
        return None

def _generate_hints_from_filters(category: str, filter_groups: List[Dict]) -> List[str]:
    """Generate user-friendly filter hints"""
    hints = []
    if not filter_groups:
        return hints
    
    enum_filters = [f for f in filter_groups if f.get('data_type') == 'enum']
    if enum_filters:
        filter_names = ", ".join([f['display_name'] for f in enum_filters[:3]])
        hints.append(f"Bạn có thể lọc theo {filter_names}")
    
    return hints

def _update_search_history(history: List[str], new_input: str) -> List[str]:
    """Add to search history, keep last 10"""
    if new_input not in history:
        history.append(new_input)
    return history[-10:]

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "RecommendatorService",
        "timestamp": datetime.utcnow().isoformat(),
        "session_storage": session_manager.get_storage_type()
    }

@app.post("/api/analyze")
async def analyze_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Main endpoint: Analyze user intent and retrieve products
    
    Flow:
    1. Create/get session
    2. Reconstruct intent if follow-up
    3. Process with orchestrator
    4. Return results with filters
    """
    try:
        if not request.user_input or not request.user_input.strip():
            return {"success": False, "error": "user_input required"}
        
        is_new_query = not request.conversation_id
        conversation_id = request.conversation_id
        
        # ====== STEP 1: Create or fetch session ======
        if not conversation_id:
            conversation_id = session_manager.create_session()
            conversation_state = None
            logger.info(f"[/api/analyze] 🆕 NEW CONVERSATION: {conversation_id}")
        else:
            if not session_manager.session_exists(conversation_id):
                return {"success": False, "error": "Session not found"}
            conversation_state = session_manager.get_session(conversation_id)
            logger.info(f"[/api/analyze] 📝 EXISTING CONVERSATION: {conversation_id}")
        
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
        user_input_to_process = request.user_input
        
        if not is_new_query and conversation_state.get("search_history"):
            logger.info("[/api/analyze] 🔄 RECONSTRUCTING INTENT")
            result_dict = context_analyzer.reconstruct_intent(
                user_input=request.user_input,
                conversation_state=conversation_state
            )
            user_input_to_process = result_dict["intent"]
            
            if result_dict.get("category_changed"):
                logger.info("[/api/analyze] 🔄 CATEGORY CHANGE DETECTED")
                conversation_state["search_history"] = [request.user_input]
                conversation_state["extracted"] = {}
                conversation_state["category"] = None
                conversation_state["has_category"] = False
        
        # ====== STEP 3: Process with orchestrator ======
        logger.info(f"[/api/analyze] Processing: '{user_input_to_process}'")
        
        orch_result = await orchestrator.process_query(
            user_input=user_input_to_process,
            conversation_state=conversation_state
        )
        
        if "state" in orch_result:
            conversation_state = orch_result["state"]
            session_manager.set_session(conversation_id, conversation_state)
        
        # ====== STEP 4: Update search history ======
        if "search_history" not in conversation_state:
            conversation_state["search_history"] = []
        
        conversation_state["search_history"] = _update_search_history(
            conversation_state["search_history"],
            request.user_input
        )
        session_manager.set_session(conversation_id, conversation_state)
        
        # ====== STEP 5: Save to DB if authenticated ======
        category_for_db = conversation_state.get("category")
        await _save_search_history_if_user(
            current_user=current_user,
            db=db,
            user_input=request.user_input,
            category_name=category_for_db,
            session_id=conversation_id
        )
        
        # ====== STEP 6: Handle special status ======
        products = orch_result.get("products", [])
        orch_status = orch_result.get("status")
        
        if orch_status == "need_info":
            logger.info("[/api/analyze] 💬 Returning clarification question")
            return {
                "success": True,
                "status": "need_info",
                "question": orch_result.get("question"),
                "options": orch_result.get("options", []),
                "case": orch_result.get("case"),
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
        
        if orch_status == "no_results":
            logger.info("[/api/analyze] 🔍 No products found")
            return {
                "success": True,
                "status": "no_results",
                "message": "Không tìm thấy sản phẩm phù hợp",
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
        
        if orch_status == "error":
            logger.error("[/api/analyze] ❌ Error")
            return {
                "success": False,
                "status": "error",
                "message": orch_result.get("message", "Lỗi xử lý"),
                "conversation_id": conversation_id
            }
        
        # ====== STEP 7: Fetch filters ======
        filter_groups = []
        category = conversation_state.get("category", "")
        
        if category:
            try:
                category_slug = sku_repo.get_category_slug_from_name(category)
                if category_slug:
                    available_filters = sku_repo.get_available_filters(category_slug)
                    filter_groups = [
                        {
                            "attribute_name": f['attribute_name'],
                            "display_name": f['display_name'] or f['attribute_name'],
                            "data_type": f['data_type'],
                            "options": [
                                {"attribute_value": opt.get('attribute_value'), "product_count": opt.get('product_count')}
                                for opt in f['options']
                                if opt.get('attribute_value') is not None
                            ]
                        }
                        for f in available_filters
                    ]
                    logger.info(f"✅ Fetched {len(filter_groups)} filters")
            except Exception as e:
                logger.error(f"Error fetching filters: {e}")
        
        # ====== Return response ======
        total_products = orch_result.get("total_found", len(products))
        
        return {
            "success": True,
            "category": category,
            "clarifying_hints": _generate_hints_from_filters(category, filter_groups),
            "filters": filter_groups,
            "products": products,
            "total": total_products,
            "conversation_id": conversation_id,
            "search_history": conversation_state.get("search_history", [])
        }
        
    except Exception as e:
        logger.error(f"[/api/analyze] ❌ Error: {e}")
        logger.exception("Error details")
        return {
            "success": False,
            "error": str(e),
            "conversation_id": request.conversation_id or "unknown"
        }

@app.post("/api/query")
async def process_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Process user query"""
    logger.info(f"[/api/query] Processing: {request.user_input}")
    
    conversation_id = request.conversation_id or session_manager.create_session()
    conversation_state = session_manager.get_session(conversation_id)
    
    result = await orchestrator.process_query(
        user_input=request.user_input,
        conversation_state=conversation_state
    )
    
    session_manager.set_session(conversation_id, result.get("state"))
    result["conversation_id"] = conversation_id
    
    return result

@app.post("/api/respond")
async def respond_to_question(request: ResponseUpdate):
    """User responds to clarification question"""
    if not session_manager.session_exists(request.conversation_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    conversation_state = session_manager.get_session(request.conversation_id)
    
    updated_state = orchestrator.update_state(
        conversation_state,
        {
            "question_type": request.question_type,
            "value": request.value,
            "attribute_name": request.attribute_name
        }
    )
    
    session_manager.set_session(request.conversation_id, updated_state)
    
    result = await orchestrator.process_query(
        user_input="",
        conversation_state=updated_state
    )
    
    result["conversation_id"] = request.conversation_id
    return result

@app.get("/api/session/{conversation_id}")
async def get_session(conversation_id: str):
    """Get session state (debug)"""
    if not session_manager.session_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "conversation_id": conversation_id,
        "state": session_manager.get_session(conversation_id)
    }

@app.delete("/api/session/{conversation_id}")
async def clear_session(conversation_id: str):
    """Clear session"""
    session_manager.delete_session(conversation_id)
    return {"message": "Session cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )

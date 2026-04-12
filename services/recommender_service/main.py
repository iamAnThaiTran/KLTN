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
from services.job_manager import get_job_manager
from services.analyze_processor import get_analyze_processor
from config.database_orm import Base, engine, get_db

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
job_manager = get_job_manager()
processor = get_analyze_processor()
orchestrator = RecommendationOrchestrator()
context_analyzer = get_context_analyzer()

logger.info(f"[Recommender] Session storage: {session_manager.get_storage_type()}")
logger.info(f"[Recommender] Job storage: {job_manager.use_redis and 'Redis' or 'In-Memory'}")
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
    db: Session = Depends(get_db)
):
    """
    Async endpoint: Create analyze job and return jobId immediately
    
    Response: { "jobId": "uuid", "status": "pending" }
    
    Client should poll GET /api/analyze/:jobId/status to get results
    
    NOTE: User auth is handled at API Gateway level
    """
    try:
        if not request.user_input or not request.user_input.strip():
            return {"success": False, "error": "user_input required"}
        
        # Create job
        job_id = job_manager.create_job(
            user_input=request.user_input,
            conversation_id=request.conversation_id
        )
        
        # Start background processing (fire and forget)
        asyncio.create_task(
            processor.process_analyze_job(
                job_id=job_id,
                user_input=request.user_input,
                conversation_id=request.conversation_id,
                current_user_id=None
            )
        )
        
        logger.info(f"[/api/analyze] 📤 Created job {job_id}")
        
        return {
            "success": True,
            "jobId": job_id,
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"[/api/analyze] ❌ Error creating job: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/analyze/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Poll job status
    
    Returns:
    {
      "status": "pending" | "done" | "error",
      "result": {...} (if done),
      "error": "..." (if error),
      "created_at": timestamp
    }
    """
    try:
        job = job_manager.get_job(job_id)
        
        if not job:
            return {
                "success": False,
                "error": "Job not found",
                "status": "unknown"
            }
        
        response = {
            "success": True,
            "jobId": job_id,
            "status": job["status"],
            "created_at": job.get("created_at")
        }
        
        if job["status"] == "done":
            response["result"] = job.get("result")
        elif job["status"] == "error":
            response["error"] = job.get("error")
        
        return response
        
    except Exception as e:
        logger.error(f"[/api/analyze/:status] ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "unknown"
        }

@app.post("/api/query")
async def process_query(
    request: QueryRequest,
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

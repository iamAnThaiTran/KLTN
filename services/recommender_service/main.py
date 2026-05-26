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
from fastapi import FastAPI, HTTPException, Depends, Request
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
from services.crawl_service_client import CrawlServiceClient
from services.llm_client import LLMClient
from services.product_comparison_service import ProductComparisonService
from models.comparison_schemas import CompareProductsRequest, CompareProductsResponse
from config.database_orm import Base, engine, get_db

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="RecommendatorService",
    description="Microservice for intent analysis and product recommendation",
    version="2.0.0"
)

# CORS is handled by API Gateway (nginx)
# Don't add CORS middleware here to avoid duplicate headers

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

# Initialize Crawl Service Client and Comparison Service
try:
    crawl_service_client = CrawlServiceClient(
        base_url="http://crawl-service:8003",
        timeout=60.0,
        max_retries=3
    )
    llm_client = LLMClient()
    comparison_service = ProductComparisonService(
        crawl_service_client=crawl_service_client,
        llm_utils=llm_client
    )
    logger.info("✅ ProductComparisonService initialized")
except Exception as e:
    logger.error(f"⚠️ Failed to initialize ProductComparisonService: {e}")
    comparison_service = None

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
    request: Request,
    payload: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Async endpoint: Create analyze job and return jobId immediately
    
    Response: { "jobId": "uuid", "status": "pending" }
    
    Client should poll GET /api/analyze/:jobId/status to get results
    
    NOTE: User auth is handled at API Gateway level
    """
    try:
        # Extract user_id from Authorization header
        current_user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                import jwt
                import os
                # Use same JWT_SECRET as auth_routes.py for consistency
                jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
                decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
                current_user_id = decoded.get("user_id") or decoded.get("sub")
                logger.info(f"[/api/analyze] 👤 Authenticated user: {current_user_id}")
            except Exception as e:
                pass
                # logger.warning(f"[/api/analyze] ⚠️ Failed to decode JWT: {e}")
                # Continue without user_id
        
        if not payload.user_input or not payload.user_input.strip():
            return {"success": False, "error": "user_input required"}
        
        # Create job
        job_id = job_manager.create_job(
            user_input=payload.user_input,
            conversation_id=payload.conversation_id
        )
        
        # Start background processing (fire and forget)
        asyncio.create_task(
            processor.process_analyze_job(
                job_id=job_id,
                user_input=payload.user_input,
                conversation_id=payload.conversation_id,
                current_user_id=current_user_id
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

# ============================================================================
# PRODUCT COMPARISON ENDPOINT
# ============================================================================

@app.post("/api/products/compare", response_model=CompareProductsResponse)
async def compare_products(
    request: CompareProductsRequest,
    db: Session = Depends(get_db)
):
    """
    Compare multiple products
    
    Flow:
    1. Frontend sends product IDs
    2. Recommender enqueues crawl tasks via CrawlService (RabbitMQ)
    3. CrawlWorker processes crawl tasks and stores results
    4. Recommender polls for results
    5. Recommender calls LLM for comparison analysis
    6. Returns comparison result to frontend
    
    Request: {"product_ids": [id1, id2, ...], "llm_model": "gpt-4o-mini"}
    Response: {"status": "success", "snapshots": [...], "comparison": "..."}
    """
    try:
        logger.info(f"🔍 [/api/products/compare] Comparing products: {request.product_ids}")
        
        if not comparison_service:
            raise HTTPException(
                status_code=503,
                detail="ProductComparisonService not available"
            )
        
        # Validate input
        if len(request.product_ids) < 2 or len(request.product_ids) > 4:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 2-4 product IDs, got {len(request.product_ids)}"
            )
        
        # Call comparison service
        result = await comparison_service.compare_products(
            product_ids=request.product_ids,
            llm_model=request.llm_model,
            seller_id=request.seller_id
        )
        
        if result["status"] == "error":
            logger.error(f"❌ Comparison failed: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Comparison failed: {result.get('error')}"
            )
        
        # Convert snapshots array to snapshot_a/b/c/d for UI compatibility
        snapshots = result.get("snapshots", [])
        if snapshots:
            result["snapshot_a"] = snapshots[0] if len(snapshots) > 0 else None
            result["snapshot_b"] = snapshots[1] if len(snapshots) > 1 else None
            result["snapshot_c"] = snapshots[2] if len(snapshots) > 2 else None
            result["snapshot_d"] = snapshots[3] if len(snapshots) > 3 else None
        
        logger.info("✅ Comparison completed successfully")
        return CompareProductsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [/api/products/compare] Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )

# app/api/progressive_search_routes.py
"""
Progressive Search API Routes

Implements the progressive search workflow:
1. User submits query → GET immediate category + filter suggestions
2. Backend starts background crawl
3. Frontend polls for product results
4. User applies filters → refine results (no re-crawl)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any, List
import asyncio

from app.models.progressive_search_models import (
    ProgressiveSearchRequest,
    ImmediateSuggestionsResponse,
    ProgressiveSearchResultsResponse,
    UpdateFiltersRequest,
    SessionStatusResponse,
    SearchStateEnum,
    FilterSuggestion,
)
from app.services.search_progress_service import SearchProgressService
from app.services.search_models import SearchState
from app.services.session_manager_factory import get_session_manager

# Initialize service and session manager
search_service = SearchProgressService()
session_manager = get_session_manager()

router = APIRouter(prefix="/api/v1/search", tags=["progressive-search"])


# ===== ENDPOINTS =====

@router.post("/progressive/start", response_model=ImmediateSuggestionsResponse)
async def start_progressive_search(
    request: ProgressiveSearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new progressive search session.
    
    1. IMMEDIATELY returns detected category + filter suggestions
    2. Starts background crawl task
    3. Frontend should poll /progressive/results to get products
    
    Example request:
    ```json
    {
      "query": "giày thể thao cho bé trai",
      "sources": ["tiki", "lazada"]
    }
    ```
    
    Example response (immediate):
    ```json
    {
      "session_id": "uuid-xxx",
      "detected_category": "Giày",
      "category_slug": "giay",
      "intent_confidence": 0.95,
      "suggested_filters": {
        "size": {
          "attribute_name": "size",
          "display_name": "Size",
          "data_type": "enum",
          "options": [
            {"attribute_value": "30", "product_count": 25},
            {"attribute_value": "31", "product_count": 18}
          ]
        },
        "color": { ... }
      },
      "state": "initial",
      "message": "Category detected. Crawling started in background."
    }
    ```
    """
    try:
        # Create session and detect category (FAST)
        session = search_service.create_session(request.query)
        
        # Save to session manager
        session_manager.save_session(session)
        
        # Start background crawl (DON'T WAIT)
        sources = request.sources or ["tiki", "lazada"]
        background_tasks.add_task(
            search_service.start_background_crawl,
            session.session_id,
            sources
        )
        
        # Build response with immediate suggestions
        response = ImmediateSuggestionsResponse(
            session_id=session.session_id,
            detected_category=session.detected_category,
            category_slug=session.category_slug,
            intent_confidence=session.intent_confidence,
            suggested_filters={
                name: FilterSuggestion(**data)
                for name, data in session.suggested_filters.items()
            },
            state=SearchStateEnum.INITIAL,
            message="Category detected. Crawling started in background."
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting search: {str(e)}")


@router.get("/progressive/results/{session_id}", response_model=ProgressiveSearchResultsResponse)
async def get_search_results(session_id: str):
    """
    Poll for search results and crawl progress.
    
    Returns different responses based on state:
    - INITIAL/CRAWLING: products=[], crawl_progress updated
    - READY/REFINED: products=[...], crawl complete
    
    Frontend should keep polling until state is READY.
    
    Example response (while crawling):
    ```json
    {
      "session_id": "uuid-xxx",
      "state": "crawling",
      "crawl_progress": {"tiki": 45, "lazada": 30},
      "products": [],
      "is_crawling": true
    }
    ```
    
    Example response (crawling done):
    ```json
    {
      "session_id": "uuid-xxx",
      "state": "ready",
      "products": [...],
      "total_products": 150,
      "crawl_progress": {"tiki": 100, "lazada": 100},
      "is_crawling": false
    }
    ```
    """
    try:
        # Get session from manager
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Build response
        response = ProgressiveSearchResultsResponse(
            session_id=session_id,
            state=SearchStateEnum(session.state.value),
            detected_category=session.detected_category,
            category_slug=session.category_slug,
            crawl_progress=session.crawl_progress,
            crawl_sources=session.crawl_sources,
            crawl_error=session.crawl_error,
            is_crawling=session.state == SearchState.CRAWLING,
            products=session.filtered_products,  # Returns filtered products
            total_products=session.total_products,
            filtered_products_count=len(session.filtered_products),
            user_selected_filters=session.user_selected_filters,
            suggested_filters={
                name: FilterSuggestion(**data)
                for name, data in session.suggested_filters.items()
            },
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")


@router.post("/progressive/filters/{session_id}", response_model=ProgressiveSearchResultsResponse)
async def apply_filters(session_id: str, request: UpdateFiltersRequest):
    """
    Apply/update filters to existing search results.
    
    This does NOT re-crawl. It filters the already-crawled products.
    If user refines filters again, it filters from the original raw results.
    
    Example request:
    ```json
    {
      "session_id": "uuid-xxx",
      "filters": {
        "size": ["40", "41", "42"],
        "color": ["Đen", "Trắng"]
      }
    }
    ```
    
    Example response: same as /progressive/results
    """
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Apply filters
        search_service.apply_filters(session_id, request.filters)
        
        # Get updated session
        session = session_manager.get_session(session_id)
        
        # Return updated results
        response = ProgressiveSearchResultsResponse(
            session_id=session_id,
            state=SearchStateEnum(session.state.value),
            detected_category=session.detected_category,
            category_slug=session.category_slug,
            crawl_progress=session.crawl_progress,
            crawl_sources=session.crawl_sources,
            crawl_error=session.crawl_error,
            is_crawling=False,
            products=session.filtered_products,
            total_products=session.total_products,
            filtered_products_count=len(session.filtered_products),
            user_selected_filters=session.user_selected_filters,
            suggested_filters={
                name: FilterSuggestion(**data)
                for name, data in session.suggested_filters.items()
            },
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying filters: {str(e)}")


@router.get("/progressive/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Quick check of session status without full product data.
    
    Useful for checking if crawling is still in progress.
    """
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        response = SessionStatusResponse(
            session_id=session_id,
            state=SearchStateEnum(session.state.value),
            detected_category=session.detected_category,
            category_slug=session.category_slug,
            crawl_sources=session.crawl_sources,
            crawl_progress=session.crawl_progress,
            crawl_error=session.crawl_error,
            is_crawling=session.state == SearchState.CRAWLING,
            total_products=session.total_products,
            filtered_products_count=len(session.filtered_products),
            user_selected_filters=session.user_selected_filters,
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching status: {str(e)}")


@router.delete("/progressive/session/{session_id}")
async def delete_session(session_id: str):
    """
    Cleanup a search session.
    """
    try:
        session_manager.delete_session(session_id)
        return {
            "status": "deleted",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@router.get("/progressive/sessions")
async def list_active_sessions():
    """
    List all active search sessions.
    (For debugging/monitoring)
    """
    try:
        session_ids = session_manager.list_active_sessions()
        return {
            "active_sessions": session_ids,
            "count": len(session_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")


@router.post("/progressive/cleanup")
async def cleanup_expired_sessions():
    """
    Cleanup expired sessions from manager.
    Can be called periodically or on-demand.
    """
    try:
        count = session_manager.cleanup_expired_sessions()
        return {
            "status": "cleaned",
            "sessions_removed": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

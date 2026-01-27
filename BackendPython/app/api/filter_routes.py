# BackendPython/app/api/filter_routes.py
"""
Filter API Routes - Cung cấp filters cho frontend
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Any, Optional
import json

from app.crawler.filter_manager import FilterManager

router = APIRouter(prefix="/filters", tags=["filters"])

# Initialize filter manager (có thể convert thành Singleton)
filter_manager = FilterManager(ttl_minutes=60)

# Store page references (nếu muốn reuse browser)
active_sessions: Dict[str, Any] = {}


@router.get("/lazada/{query}")
async def get_lazada_filters(
    query: str,
    category: str = Query("giày", description="Category sản phẩm"),
    force_refresh: bool = Query(False, description="Force refresh từ Lazada")
) -> Dict[str, Any]:
    """
    Get filters từ Lazada cho query
    
    Query Parameters:
    - query: Keyword search (ví dụ: "giày nike")
    - category: Category sản phẩm (ví dụ: "giày", "áo", ...)
    - force_refresh: Force crawl lại thay vì dùng cache
    
    Response:
    {
        "raw": {Filter names từ Lazada},
        "mapped": {Filter names mapped sang schema},
        "cache_hit": bool
    }
    """
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set user agent
            await page.set_user_agent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Navigate to Lazada
            url = f"https://www.lazada.vn/search?q={query}"
            await page.goto(url, wait_until="networkidle")
            
            # Get filters
            result = await filter_manager.get_filters(
                platform="lazada",
                query=query,
                category=category,
                page=page,
                force_refresh=force_refresh
            )
            
            await browser.close()
            
            return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-filters")
async def apply_filters(
    platform: str = Query("lazada"),
    query: str = Query(""),
    category: str = Query("giày"),
    user_attributes: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Apply user's attribute preferences lên available filters
    
    Request:
    {
        "platform": "lazada",
        "query": "giày nike",
        "category": "giày",
        "user_attributes": {
            "brand": "nike",
            "size": "40",
            "mau": "đen"
        }
    }
    
    Response:
    {
        "available_filters": {...},
        "suggested_values": {
            "brand": ["nike"],
            "size": ["40"],
            ...
        },
        "suggested_filter_params": {
            "brand=nike&size=40&..."
        }
    }
    """
    try:
        # Get cached filters
        cached = filter_manager.cache.get(platform, category, query)
        
        if not cached:
            raise HTTPException(
                status_code=404,
                detail="Filters not cached. Call /filters/lazada/{query} first"
            )
        
        filters = cached["mapped"]
        
        if not user_attributes:
            user_attributes = {}
        
        # Get suggestions
        suggestions = filter_manager.get_filter_suggestions(filters, user_attributes)
        
        # Build filter params (cho Lazada URL)
        filter_params = _build_filter_params(platform, suggestions)
        
        return {
            "available_filters": filters,
            "suggested_values": suggestions,
            "suggested_filter_params": filter_params,
            "lazada_url": f"https://www.lazada.vn/search?q={query}&{filter_params}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache-stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    cache_size = len(filter_manager.cache.cache)
    
    stats = {
        "total_cached_entries": cache_size,
        "ttl_minutes": filter_manager.cache.ttl.total_seconds() / 60,
        "entries": []
    }
    
    for key, entry in filter_manager.cache.cache.items():
        stats["entries"].append({
            "key": key,
            "created_at": entry["created_at"].isoformat(),
            "expires_at": entry["expires_at"].isoformat(),
            "filter_count": len(entry["filters"].get("raw", {}))
        })
    
    return stats


@router.delete("/cache/{platform}/{category}/{query}")
async def clear_cache_entry(
    platform: str,
    category: str,
    query: str
) -> Dict[str, str]:
    """Clear specific cache entry"""
    key = filter_manager.cache._get_key(platform, category, query)
    
    if key in filter_manager.cache.cache:
        del filter_manager.cache.cache[key]
        return {"status": "success", "message": f"Cleared: {platform}/{category}/{query}"}
    
    return {"status": "not_found", "message": "Cache entry not found"}


@router.post("/cache/clear-expired")
async def clear_expired_cache() -> Dict[str, Any]:
    """Clear all expired cache entries"""
    cleared_count = filter_manager.cache.clear_expired()
    return {
        "status": "success",
        "cleared_count": cleared_count,
        "remaining_entries": len(filter_manager.cache.cache)
    }


# ============================================
# HELPER FUNCTIONS
# ============================================

def _build_filter_params(platform: str, suggestions: Dict[str, List[str]]) -> str:
    """
    Build URL filter parameters từ suggestions
    
    Ví dụ:
    {
        "brand": ["nike"],
        "size": ["40"],
        "mau": ["đen"]
    }
    →
    "facet[100008523]=Nike&facet[100004148]=40&facet[100003957]=Đen"
    
    Note: Lazada có hardcoded facet IDs cho từng filter
    """
    
    if platform.lower() == "lazada":
        # Lazada facet IDs (thường phải scrape từ page)
        # Đây là examples, cần update dựa trên actual Lazada structure
        facet_mapping = {
            "brand": "100008523",
            "gia": "100003957",
            "mau": "100003957",
            "size": "100004148",
        }
        
        params = []
        for filter_name, values in suggestions.items():
            facet_id = facet_mapping.get(filter_name)
            if facet_id and values:
                # Lazada format: facet[id]=value1&facet[id]=value2
                for val in values:
                    params.append(f"facet[{facet_id}]={val}")
        
        return "&".join(params)
    
    # Default format
    params = []
    for filter_name, values in suggestions.items():
        for val in values:
            params.append(f"{filter_name}={val}")
    return "&".join(params)


# ============================================
# INTEGRATION WITH EXISTING API
# ============================================
# Thêm vào app/api/routes.py:
# 
# from .filter_routes import router as filter_router
# app.include_router(filter_router)

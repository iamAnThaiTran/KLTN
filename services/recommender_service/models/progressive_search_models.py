# app/models/progressive_search_models.py
"""
Pydantic models for progressive search API responses.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SearchStateEnum(str, Enum):
    """Search session state"""
    INITIAL = "initial"  # Category detected, filters suggested
    CRAWLING = "crawling"  # Background crawl in progress
    READY = "ready"  # Products ready
    REFINED = "refined"  # Filters applied
    ERROR = "error"  # Error occurred


class ProgressiveSearchRequest(BaseModel):
    """Request to start a new progressive search"""
    query: str = Field(..., description="User's search query")
    sources: Optional[List[str]] = Field(
        default=None,
        description="Crawl sources: ['tiki', 'lazada'] or null for all"
    )


class FilterSuggestion(BaseModel):
    """A suggested filter for the user"""
    attribute_name: str
    display_name: str
    data_type: str  # "text", "enum", "number", "range"
    options: List[Dict[str, Any]]  # [{"attribute_value": "40", "product_count": 15}, ...]


class ImmediateSuggestionsResponse(BaseModel):
    """
    Immediate response with category + filter suggestions.
    Returned BEFORE crawling finishes.
    """
    session_id: str = Field(..., description="Session ID for polling")
    detected_category: Optional[str] = Field(None, description="e.g., 'Giày'")
    category_slug: Optional[str] = Field(None, description="e.g., 'giay'")
    intent_confidence: float = Field(0.0, description="Confidence 0-1 of category detection")
    
    # Filter suggestions (from DB, not crawl results)
    suggested_filters: Dict[str, FilterSuggestion] = Field(
        default_factory=dict,
        description="Immediate filter suggestions from DB"
    )
    
    state: SearchStateEnum = Field(SearchStateEnum.INITIAL)
    message: str = "Category detected. Crawling started in background."


class CrawlProgressUpdate(BaseModel):
    """Progress update during crawling"""
    session_id: str
    state: SearchStateEnum
    crawl_progress: Dict[str, int]  # {"tiki": 45, "lazada": 30}
    crawl_error: Optional[str] = None
    estimated_products: int = 0


class ProgressiveSearchResultsResponse(BaseModel):
    """
    Complete response with products + remaining filters.
    Returned after crawl completes or on polling.
    """
    session_id: str
    state: SearchStateEnum
    detected_category: Optional[str]
    category_slug: Optional[str]
    
    # Crawl status
    crawl_progress: Dict[str, int] = {}
    crawl_sources: List[str] = []
    crawl_error: Optional[str] = None
    is_crawling: bool = False
    
    # Results (filtered by user selections if any)
    products: List[Dict[str, Any]] = []
    total_products: int = 0
    filtered_products_count: int = 0
    
    # User's applied filters
    user_selected_filters: Dict[str, List[str]] = {}
    
    # Available filters (updated based on crawl results)
    suggested_filters: Dict[str, FilterSuggestion] = {}


class UpdateFiltersRequest(BaseModel):
    """Request to apply/update filters on existing search"""
    session_id: str
    filters: Dict[str, List[str]] = Field(
        default_factory=dict,
        description='e.g., {"size": ["42", "43"], "color": ["Đen"]}'
    )


class SessionStatusResponse(BaseModel):
    """Response for checking session status"""
    session_id: str
    state: SearchStateEnum
    detected_category: Optional[str]
    category_slug: Optional[str]
    
    # Crawl info
    crawl_sources: List[str]
    crawl_progress: Dict[str, int]
    crawl_error: Optional[str]
    is_crawling: bool
    
    # Results count
    total_products: int
    filtered_products_count: int
    
    user_selected_filters: Dict[str, List[str]]

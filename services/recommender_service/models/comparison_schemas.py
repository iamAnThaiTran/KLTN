"""
Pydantic schemas for product comparison history
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ComparisonHistoryBase(BaseModel):
    """Base schema for comparison history"""
    product_id_1: int
    product_id_2: int
    product_name_1: str
    product_name_2: str
    comparison_type: str = "detailed"
    llm_model: str = "gpt-4"
    notes: Optional[str] = None
    is_starred: bool = False


class ComparisonHistorySave(ComparisonHistoryBase):
    """Schema to save a new comparison"""
    snapshot_a: Dict[str, Any]
    snapshot_b: Dict[str, Any]
    comparison_result: str  # Markdown text
    summary_json: Optional[Dict[str, Any]] = None
    api_request: Optional[Dict[str, Any]] = None


class ComparisonHistoryResponse(ComparisonHistoryBase):
    """Schema for returning comparison from database"""
    id: int
    user_id: int
    snapshot_a: Dict[str, Any]
    snapshot_b: Dict[str, Any]
    comparison_result: str
    summary_json: Optional[Dict[str, Any]] = None
    api_request: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComparisonHistoryList(BaseModel):
    """Schema for listing comparisons (minimal data)"""
    id: int
    product_name_1: str
    product_name_2: str
    product_id_1: int
    product_id_2: int
    created_at: datetime
    is_starred: bool = False
    comparison_type: str = "detailed"


class ComparisonHistoryListResponse(BaseModel):
    """Response for list comparisons endpoint"""
    total: int
    limit: int
    offset: int
    comparisons: List[ComparisonHistoryList]


class ComparisonHistoryUpdate(BaseModel):
    """Schema to update comparison metadata"""
    notes: Optional[str] = None
    is_starred: Optional[bool] = None


class SaveComparisonRequest(BaseModel):
    """Request to save a comparison result"""
    product_id_1: int
    product_id_2: int
    product_name_1: str
    product_name_2: str
    snapshot_a: Dict[str, Any]
    snapshot_b: Dict[str, Any]
    comparison_result: str  # Markdown
    summary_json: Optional[Dict[str, Any]] = None
    api_request: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    comparison_type: str = "detailed"
    llm_model: str = "gpt-4"


class GetComparisonHistoryRequest(BaseModel):
    """Request to get comparison history"""
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    starred_only: bool = False


# ============================================================================
# COMPARE PRODUCTS ENDPOINT MODELS
# ============================================================================

class CompareProductsRequest(BaseModel):
    """Request to compare multiple products"""
    product_ids: List[int] = Field(..., min_items=2, max_items=4)
    llm_model: str = Field(default="gpt-4o-mini")
    seller_id: Optional[str] = None
    save_history: bool = True


class ProductSnapshot(BaseModel):
    """Snapshot of a single product"""
    product_id: int
    spid: str
    name: str
    brand: Optional[str] = None
    price: float
    rating_avg: float
    rating_count: int
    reviews: List[Dict[str, Any]]
    rating_breakdown: Dict[str, Any]
    specs: Optional[List[Dict[str, Any]]] = None
    image: Optional[str] = None
    seller_id: str
    
    class Config:
        extra = "allow"


class CompareProductsResponse(BaseModel):
    """Response with product comparison analysis - compatible with monolith and microservice"""
    status: str  # "success" | "error"
    
    # For 2-4 products - compatible with monolith UI
    snapshot_a: Optional[ProductSnapshot] = None
    snapshot_b: Optional[ProductSnapshot] = None
    snapshot_c: Optional[ProductSnapshot] = None
    snapshot_d: Optional[ProductSnapshot] = None
    
    # Generic access for any number of products
    snapshots: List[ProductSnapshot] = []
    product_ids: List[int] = []
    
    # Comparison and analysis
    comparison: Optional[str] = None  # LLM comparison in Markdown
    prompt: Optional[str] = None  # For debugging
    llm_model: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    class Config:
        extra = "allow"

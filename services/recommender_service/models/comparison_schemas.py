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

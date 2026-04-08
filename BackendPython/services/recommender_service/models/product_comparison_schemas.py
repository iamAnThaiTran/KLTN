"""
Pydantic models for product comparison API
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ProductIdentifier(BaseModel):
    """Product identifier from Tiki"""

    product_id: str = Field(..., description="Tiki product ID")
    spid: str = Field(..., description="Tiki seller product ID (SKU)")
    seller_id: str = Field(default="1", description="Seller ID (1 = Tiki official)")


class CompareProductsRequest(BaseModel):
    """
    DEPRECATED: Use CompareProductsByIdsRequest instead.
    
    Old format - kept for backward compatibility only.
    Request to compare 2 products by Tiki IDs directly.
    """

    product_a: ProductIdentifier = Field(..., description="First product to compare")
    product_b: ProductIdentifier = Field(..., description="Second product to compare")
    include_llm_analysis: Optional[bool] = Field(
        default=True,
        description="DEPRECATED: Ignored. LLM analysis is always enabled.",
    )
    llm_model: Optional[str] = Field(
        default="gpt-4o-mini",
        description="LLM model to use for analysis (OpenAI: gpt-4o-mini, gpt-4o)",
    )
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class RatingBreakdown(BaseModel):
    """Rating breakdown by stars"""

    count: int = Field(..., description="Number of reviews with this rating")
    percent: float = Field(..., description="Percentage of total reviews")


class ReviewItem(BaseModel):
    """Single review from product"""

    id: Optional[int] = None
    rating: int = Field(..., description="Rating 1-5")
    title: str = Field(default="", description="Review title")
    content: str = Field(default="", description="Review content")
    author: str = Field(default="", description="Reviewer name")
    is_purchased: bool = Field(default=False, description="Whether reviewer actually purchased")
    used_duration: str = Field(default="", description="How long used product")
    total_reviews_by_author: int = Field(default=0, description="Total reviews by this author")
    thank_count: int = Field(default=0, description="Number of thanks")
    has_image: bool = Field(default=False, description="Whether review has images")
    created_at: Optional[str] = None
    seller_reply: str = Field(default="", description="Seller's reply if any")
    attributes: List[str] = Field(default_factory=list, description="Review attributes/tags")


class SpecificationGroup(BaseModel):
    """Group of specifications (e.g., 'Dimensions', 'Features')"""

    group: str = Field(..., description="Group name")
    attrs: List[Dict[str, str]] = Field(..., description="[{name, value}, ...]")


class ProductSnapshot(BaseModel):
    """Complete product snapshot with details + reviews"""

    # Identifiers
    product_id: str
    spid: str
    seller_id: str

    # Basic info
    name: str
    brand: str
    category: str
    price: int
    original_price: int
    discount_pct: float
    url: str
    thumbnail: str

    # Ratings
    rating_avg: float
    rating_count: int
    rating_breakdown: Dict[str, RatingBreakdown] = Field(default_factory=dict)

    # Options
    sizes: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)

    # Technical specs
    specifications: List[SpecificationGroup] = Field(default_factory=list)

    # Reviews
    reviews: List[ReviewItem] = Field(default_factory=list)

    # Meta
    crawl_ok: bool = Field(default=False)
    error: str = Field(default="")


class ProductComparisonResult(BaseModel):
    """Result of product comparison"""

    status: str = Field(..., description="'success' or 'error'")
    snapshot_a: Optional[ProductSnapshot] = Field(None, description="First product snapshot")
    snapshot_b: Optional[ProductSnapshot] = Field(None, description="Second product snapshot")
    prompt: Optional[str] = Field(
        None,
        description="Formatted comparison prompt (for debugging/transparency)",
    )
    comparison: Optional[str] = Field(
        None,
        description="LLM response with detailed comparison in Markdown format",
    )
    error: Optional[str] = Field(None, description="Error message if status == 'error'")


class CompareProductsByIdsRequest(BaseModel):
    """Alternative request format: Accept product IDs directly from frontend"""

    product_ids: List[int] = Field(
        ..., 
        description="List of 2 product IDs [product_a_id, product_b_id]"
    )
    spids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of seller product IDs (spids). If not provided, defaults to product_ids"
    )
    seller_id: Optional[str] = Field(
        default="1",
        description="Seller ID (default: 1 = Tiki official)"
    )
    llm_model: Optional[str] = Field(
        default="gpt-4o-mini",
        description="LLM model to use for analysis (OpenAI: gpt-4o-mini, gpt-4o)",
    )

    def validate(self):
        """Validate that we have exactly 2 products"""
        if len(self.product_ids) != 2:
            raise ValueError(f"Expected 2 product IDs, got {len(self.product_ids)}")
        if self.spids and len(self.spids) != 2:
            raise ValueError(f"Expected 2 spids, got {len(self.spids)}")


class SingleProductAnalysisRequest(BaseModel):
    """Request for single product analysis"""

    product_id: str = Field(..., description="Tiki product ID")
    spid: str = Field(..., description="Tiki seller product ID (SKU)")
    seller_id: str = Field(default="1", description="Seller ID (1 = Tiki official)")
    label: Optional[str] = Field(None, description="Optional label for logging")


class SingleProductAnalysisResult(BaseModel):
    """Result of single product analysis"""

    status: str = Field(..., description="'success' or 'error'")
    snapshot: Optional[ProductSnapshot] = Field(None, description="Product snapshot")
    error: Optional[str] = Field(None, description="Error message if status == 'error'")


# Summary format for API responses (without full reviews text)
class ProductSummaryForDisplay(BaseModel):
    """Lightweight product summary for API responses"""

    product_id: str
    name: str
    brand: str
    category: str
    price: int
    original_price: int
    discount_pct: float
    url: str
    thumbnail: str
    rating_avg: float
    rating_count: int
    rating_breakdown: Dict[str, RatingBreakdown]
    sizes: List[str]  # First 10 only
    colors: List[str]  # First 10 only
    specifications: List[SpecificationGroup]  # First 5 groups only
    review_count: int  # Total reviews crawled
    review_summary: Dict[str, Any]  # {"total": int, "avg_rating": float, ...}

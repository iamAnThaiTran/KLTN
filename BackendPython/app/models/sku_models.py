# app/models/sku_models.py
"""
Pydantic models for SKU-based product system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Category(BaseModel):
    """Product category"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CategoryAttribute(BaseModel):
    """Attribute definition for a category"""
    id: int
    category_id: int
    name: str
    display_name: Optional[str] = None
    data_type: str = "text"  # text, number, enum, range
    possible_values: Optional[List[str]] = None
    is_required: bool = False
    is_filterable: bool = True
    sort_order: int = 0


class Product(BaseModel):
    """Generic product without variant attributes"""
    id: int
    category_id: int
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    product_url: Optional[str] = None
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class SKU(BaseModel):
    """Product variant with specific attributes"""
    id: int
    product_id: int
    sku_code: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    stock: int = 0
    is_available: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    attributes: Dict[str, str] = {}  # Loaded from sku_attributes


class ProductWithSKUs(BaseModel):
    """Product with all its SKUs"""
    id: int
    category_id: int
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    product_url: Optional[str] = None
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    skus: List[SKU] = []
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    available_count: int = 0


class FilterOption(BaseModel):
    """Available filter option for UI"""
    attribute_value: str
    product_count: int


class FilterGroup(BaseModel):
    """Grouped filters for UI checkboxes"""
    attribute_name: str
    display_name: str
    data_type: str
    options: List[FilterOption]


class ProductSearchRequest(BaseModel):
    """Request for product search"""
    category_slug: str
    filters: Dict[str, List[str]] = Field(default_factory=dict)
    # filters = {"size": ["42", "43"], "color": ["Đen"]}
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class FavoriteBase(BaseModel):
    """Base favorite model"""
    product_id: int


class FavoriteCreate(FavoriteBase):
    """Create favorite request"""
    pass


class FavoriteResponse(FavoriteBase):
    """Favorite response"""
    id: int
    user_id: int
    added_at: datetime

    class Config:
        from_attributes = True


class FavoriteProductResponse(BaseModel):
    """Favorite with product details"""
    id: int
    user_id: int
    product_id: int
    added_at: datetime
    product: Optional["ProductWithSKUs"] = None

    class Config:
        from_attributes = True


class UserFavoritesResponse(BaseModel):
    """User favorites list response"""
    user_id: int
    count: int
    favorites: List[FavoriteProductResponse]

    class Config:
        from_attributes = True
    page: int = 1
    page_size: int = 20


class ProductSearchResponse(BaseModel):
    """Response for product search"""
    products: List[ProductWithSKUs]
    total: int
    page: int
    page_size: int
    total_pages: int
    filters: List[FilterGroup]  # Available filters for UI
    selected_attributes: Optional[Dict[str, Any]] = None  # ✅ NEW: Attributes selected by backend for pre-ticking filters

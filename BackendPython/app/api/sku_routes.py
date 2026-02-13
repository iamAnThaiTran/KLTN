# app/api/sku_routes.py
"""
API endpoints for SKU-based product search
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.models.sku_models import (
    ProductSearchRequest,
    ProductSearchResponse,
    ProductWithSKUs,
    FilterGroup,
    FilterOption
)
from app.db.sku_repository import SKURepository
from app.services.category_validator import CategoryValidator
import math

router = APIRouter(prefix="/api/v1", tags=["products"])

# Initialize repository
sku_repo = SKURepository()


class CrawlRequest(BaseModel):
    """Request to crawl and filter products by category"""
    category_name: str  # e.g., "giày", "đồng hồ"
    user_input: Optional[str] = None  # ✅ NEW: Original user input for attribute extraction
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    selected_filters: Dict[str, List[str]] = Field(default_factory=dict)
    page: int = 1
    page_size: int = 20


@router.post("/products/fetch-and-filter", response_model=ProductSearchResponse)
async def fetch_products_with_attributes(request: ProductSearchRequest):
    """
    Fetch products from DB + return available attributes for UI filtering
    
    This endpoint combines:
    1. Search products from DB first (DB-first approach)
    2. Get available filter attributes for UI
    3. Return both in one response
    
    Request:
    ```json
    {
      "category_slug": "giay",
      "filters": {},  // Start with empty, UI will populate after seeing available filters
      "page": 1,
      "page_size": 20
    }
    ```
    
    Response includes:
    - products: List of products with SKUs
    - filters: All available attributes UI can use to refine search
      - Each filter has attribute_name, display_name (for UI), and available options
      - UI can use these to build checkboxes/dropdowns
    
    Flow for UI:
    1. Call this endpoint with empty filters
    2. Display available filters based on response.filters
    3. User selects filters
    4. Call again with selected filters in request.filters
    """
    try:
        # STEP 1: Search products from DB first
        products, total = sku_repo.search_products(
            category_slug=request.category_slug,
            filters=request.filters,
            min_price=request.min_price,
            max_price=request.max_price,
            page=request.page,
            page_size=request.page_size
        )
        
        # STEP 2: Get available filters from DB schema (not hardcoded)
        available_filters = sku_repo.get_available_filters(request.category_slug)
        
        # STEP 3: Convert to response format
        filter_groups = []
        for f in available_filters:
            filter_groups.append(FilterGroup(
                attribute_name=f['attribute_name'],
                display_name=f['display_name'] or f['attribute_name'],
                data_type=f['data_type'],
                options=[
                    FilterOption(**opt) for opt in f['options']
                    if opt.get('attribute_value') is not None
                ]
            ))
        
        total_pages = math.ceil(total / request.page_size)
        
        return ProductSearchResponse(
            products=[ProductWithSKUs(**p) for p in products],
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            filters=filter_groups
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl-products", response_model=ProductSearchResponse)
async def crawl_and_get_filters(request: CrawlRequest):
    """
    Crawl products by category name + return available filters for UI
    """
    try:
        print(f"✅ crawl-products endpoint called")
        print(f"📦 Request: {request}")
        
        # Validate category name and get slug
        category_validator = CategoryValidator()
        validation = category_validator.validate_category(request.category_name)
        
        print(f"✅ Category validation: {validation}")
        
        if not validation["success"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Category '{request.category_name}' not found"
            )
        
        category_slug = sku_repo.get_category_slug_from_name(validation["category"])
        if not category_slug:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot find category slug for '{validation['category']}'"
            )
        
        print(f"✅ Category slug: {category_slug}")
        
        # ✅ NEW: Extract attributes from user input if provided
        extracted_attributes = {}
        if request.user_input:
            from app.core.extractor import AttributeExtractor
            extractor = AttributeExtractor()
            extraction_result = extractor.extract(
                request.user_input,
                validation["category"],
                use_llm=False
            )
            extracted_attributes = extraction_result.get("extracted", {})
            print(f"✅ Extracted attributes from '{request.user_input}': {extracted_attributes}")
        
        # Search products from DB
        products, total = sku_repo.search_products(
            category_slug=category_slug,
            filters=request.selected_filters,
            min_price=request.min_price,
            max_price=request.max_price,
            page=request.page,
            page_size=request.page_size
        )
        
        print(f"✅ Found {total} products")
        
        # Get available filters from DB
        available_filters = sku_repo.get_available_filters(category_slug)
        
        print(f"✅ Found {len(available_filters)} filters")
        
        # Build filter groups
        filter_groups = []
        for f in available_filters:
            filter_groups.append(FilterGroup(
                attribute_name=f['attribute_name'],
                display_name=f['display_name'] or f['attribute_name'],
                data_type=f['data_type'],
                options=[
                    FilterOption(**opt) for opt in f['options']
                    if opt.get('attribute_value') is not None
                ]
            ))
        
        total_pages = math.ceil(total / request.page_size) if request.page_size > 0 else 0
        
        print(f"✅ Response ready with {len(products)} products and {len(filter_groups)} filter groups")
        
        return ProductSearchResponse(
            products=[ProductWithSKUs(**p) for p in products],
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            filters=filter_groups,
            selected_attributes=extracted_attributes  # ✅ NEW: Return extracted attributes
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ ERROR in crawl_and_get_filters:")
        print(error_traceback)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/products/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest):
    """
    Search products with filters
    
    Example request:
    ```json
    {
      "category_slug": "giay",
      "filters": {
        "size": ["42", "43"],
        "color": ["Đen"]
      },
      "min_price": 1000000,
      "max_price": 3000000,
      "page": 1,
      "page_size": 20
    }
    ```
    
    Returns:
    - products: List of products with SKUs
    - filters: Available filter options for UI
    - pagination info
    """
    try:
        # Search products
        products, total = sku_repo.search_products(
            category_slug=request.category_slug,
            filters=request.filters,
            min_price=request.min_price,
            max_price=request.max_price,
            page=request.page,
            page_size=request.page_size
        )
        
        # Get available filters
        available_filters = sku_repo.get_available_filters(request.category_slug)
        
        # Convert to response format
        filter_groups = []
        for f in available_filters:
            if f['options']:  # Only include if has options
                filter_groups.append(FilterGroup(
                    attribute_name=f['attribute_name'],
                    display_name=f['display_name'] or f['attribute_name'],
                    data_type=f['data_type'],
                    options=[
                        FilterOption(**opt) for opt in f['options']
                        if opt['attribute_value'] is not None
                    ]
                ))
        
        total_pages = math.ceil(total / request.page_size)
        
        return ProductSearchResponse(
            products=[ProductWithSKUs(**p) for p in products],
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            filters=filter_groups
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}", response_model=ProductWithSKUs)
async def get_product(product_id: int):
    """
    Get single product with all SKUs
    
    Example: GET /api/v1/products/1
    """
    product = sku_repo.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductWithSKUs(**product)


@router.get("/categories/{category_slug}/attributes", response_model=List[FilterGroup])
async def get_category_attributes(category_slug: str):
    """
    Get attribute schema for a category (for UI to know what to filter)
    
    Returns attributes from DB with display names for UI
    
    Example: GET /api/v1/categories/giay/attributes
    
    Response:
    ```json
    [
        {
            "attribute_name": "size",
            "display_name": "Kích cỡ",
            "data_type": "enum",
            "options": [
                {"attribute_value": "42", "product_count": 10},
                {"attribute_value": "43", "product_count": 8}
            ]
        },
        {
            "attribute_name": "color",
            "display_name": "Màu sắc",
            "data_type": "enum",
            "options": [
                {"attribute_value": "Đen", "product_count": 15},
                {"attribute_value": "Trắng", "product_count": 12}
            ]
        }
    ]
    ```
    """
    try:
        available_filters = sku_repo.get_available_filters(category_slug)
        
        filter_groups = []
        for f in available_filters:
            filter_groups.append(FilterGroup(
                attribute_name=f['attribute_name'],
                display_name=f['display_name'] or f['attribute_name'],
                data_type=f['data_type'],
                options=[
                    FilterOption(**opt) for opt in f['options']
                    if opt.get('attribute_value') is not None
                ]
            ))
        
        return filter_groups
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category_slug}/filters", response_model=List[FilterGroup])
async def get_category_filters(category_slug: str):
    """
    Get available filters for a category (for building UI)
    
    Example: GET /api/v1/categories/giay/filters
    
    Returns filter groups with available options and product counts
    """
    try:
        available_filters = sku_repo.get_available_filters(category_slug)
        
        filter_groups = []
        for f in available_filters:
            if f['options']:
                filter_groups.append(FilterGroup(
                    attribute_name=f['attribute_name'],
                    display_name=f['display_name'] or f['attribute_name'],
                    data_type=f['data_type'],
                    options=[
                        FilterOption(**opt) for opt in f['options']
                        if opt['attribute_value'] is not None
                    ]
                ))
        
        return filter_groups
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/search/simple")
async def search_products_simple(
    category: str = Query(..., description="Category slug (giay, dong-ho, etc)"),
    size: Optional[List[str]] = Query(None, description="Size filter"),
    color: Optional[List[str]] = Query(None, description="Color filter"),
    gender: Optional[List[str]] = Query(None, description="Gender filter"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Simple GET endpoint for product search
    
    Example: 
    GET /api/v1/products/search/simple?category=giay&size=42&size=43&color=Đen&min_price=1000000
    """
    # Build filters dict
    filters = {}
    if size:
        filters['size'] = size
    if color:
        filters['color'] = color
    if gender:
        filters['gender'] = gender
    
    request = ProductSearchRequest(
        category_slug=category,
        filters=filters,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size
    )
    
    return await search_products(request)

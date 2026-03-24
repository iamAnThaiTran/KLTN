# app/api/product_comparison_routes.py
"""
Product Comparison Routes
Handles product comparison requests with Tiki crawler + LLM analysis
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database_orm import get_db
from app.api.auth_middleware import get_current_user_optional
from app.services.product_comparison_service import ProductComparisonService
from app.db.sku_repository import SKURepository
from app.models.product_comparison_schemas import (
    CompareProductsRequest,
    CompareProductsByIdsRequest,
    ProductComparisonResult,
    SingleProductAnalysisRequest,
    SingleProductAnalysisResult,
    ProductIdentifier,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/products", tags=["product-comparison"])

# Initialize service
comparison_service = ProductComparisonService()



@router.post("/compare", response_model=ProductComparisonResult)
async def compare_products_by_ids(
    request: CompareProductsByIdsRequest,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Compare 2 Tiki products by IDs (simplified format for frontend).

    Frontend sends: {"product_ids": [46, 47]}
    Backend converts to: ProductIdentifier objects and calls comparison

    Args:
        request: CompareProductsByIdsRequest with product_ids list
        user: Current user (optional - for logging)
        db: Database session

    Returns:
        ProductComparisonResult with snapshots and comparison analysis
    """
    try:
        logger.info(f"📊 Compare by IDs request from user: {user.id if user else 'Anonymous'}")

        # Validate
        if len(request.product_ids) != 2:
            raise HTTPException(
                status_code=400, 
                detail=f"Expected 2 product IDs, got {len(request.product_ids)}"
            )

        # Lookup Tiki IDs from database
        sku_repo = SKURepository()
        tiki_ids_map = sku_repo.get_tiki_ids(request.product_ids)
        
        if len(tiki_ids_map) != 2:
            missing_ids = set(request.product_ids) - set(tiki_ids_map.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Products not found in database: {missing_ids}. "
                       f"Make sure tiki_product_id and tiki_spid are set."
            )
        
        # Get Tiki IDs
        tiki_info_a = tiki_ids_map[request.product_ids[0]]
        tiki_info_b = tiki_ids_map[request.product_ids[1]]
        
        logger.info(
            f"  📦 Product {request.product_ids[0]}: {tiki_info_a['title']}"
        )
        logger.info(
            f"     Tiki ID: {tiki_info_a['tiki_product_id']}, "
            f"spid: {tiki_info_a['tiki_spid']}"
        )
        logger.info(
            f"  📦 Product {request.product_ids[1]}: {tiki_info_b['title']}"
        )
        logger.info(
            f"     Tiki ID: {tiki_info_b['tiki_product_id']}, "
            f"spid: {tiki_info_b['tiki_spid']}"
        )
        
        # Convert to ProductIdentifier objects
        product_a = ProductIdentifier(
            product_id=tiki_info_a['tiki_product_id'],
            spid=tiki_info_a['tiki_spid'],
            seller_id=request.seller_id or "1",
        )
        
        product_b = ProductIdentifier(
            product_id=tiki_info_b['tiki_product_id'],
            spid=tiki_info_b['tiki_spid'],
            seller_id=request.seller_id or "1",
        )

        # Run comparison
        result = await comparison_service.compare_tiki_products(
            product_a=product_a.dict(),
            product_b=product_b.dict(),
            llm_model=request.llm_model,
        )

        # Log to database if user logged in
        if user and result["status"] == "success":
            logger.info(
                f"✅ Comparison completed for user {user.id}: "
                f"{request.product_ids[0]} vs {request.product_ids[1]} "
                f"(Tiki: {product_a.product_id} vs {product_b.product_id})"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in compare_products_by_ids: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing products: {str(e)}",
        )


@router.post("/analyze-single", response_model=SingleProductAnalysisResult)
async def analyze_single_product(
    request: SingleProductAnalysisRequest,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get detailed analysis of a single product.

    Crawls product details + reviews and returns complete snapshot.
    Useful for individual product pages or caching.

    Args:
        request: SingleProductAnalysisRequest with product identifiers
        user: Current user (optional - for logging)
        db: Database session

    Returns:
        SingleProductAnalysisResult with product snapshot
    """
    try:
        logger.info(f"📦 Analyze single product: {request.product_id}")

        result = await comparison_service.get_single_product_analysis(
            product_id=request.product_id,
            spid=request.spid,
            seller_id=request.seller_id,
            label=request.label,
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error in analyze_single_product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing product: {str(e)}",
        )


@router.get("/compare/status/{comparison_id}")
async def get_comparison_status(
    comparison_id: str,
    user=Depends(get_current_user_optional),
):
    """
    Check status of a comparison (for async operations).

    Note: Current implementation is synchronous.
    This endpoint is for future async support.

    Args:
        comparison_id: ID of comparison session
        user: Current user (optional)

    Returns:
        Status info
    """
    return {
        "message": "Comparison status check not yet implemented for async operations",
        "comparison_id": comparison_id,
    }


@router.post("/compare/with-prompt")
async def compare_with_custom_prompt(
    request: CompareProductsRequest,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get comparison prompt without calling LLM.

    Useful for:
    - Debugging/transparency
    - Sending to different LLM service
    - Custom LLM prompting

    Args:
        request: CompareProductsRequest
        user: Current user (optional)
        db: Database session

    Returns:
        {
            "status": "success",
            "snapshot_a": {...},
            "snapshot_b": {...},
            "prompt": "..."  # Full comparison prompt
        }
    """
    try:
        # Validate product identifiers
        is_valid, error_msg = comparison_service.validate_product_ids(
            request.product_a.dict(), request.product_b.dict()
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Run comparison WITHOUT LLM
        result = await comparison_service.compare_tiki_products(
            product_a=request.product_a.dict(),
            product_b=request.product_b.dict(),
            llm_client=None,  # No LLM
            llm_model=request.llm_model,
        )

        return {
            "status": result["status"],
            "snapshot_a": result["snapshot_a"],
            "snapshot_b": result["snapshot_b"],
            "prompt": result["prompt"],
            # Note: comparison is empty since we didn't call LLM
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in compare_with_prompt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating prompt: {str(e)}",
        )

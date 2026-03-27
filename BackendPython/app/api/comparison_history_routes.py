"""
Comparison History Routes
Handles saving, retrieving, updating comparison history
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database_orm import get_db
from app.api.auth_middleware import get_current_user
from app.db.comparison_history_repository import ComparisonHistoryRepository
from app.models.comparison_schemas import (
    ComparisonHistoryResponse,
    ComparisonHistoryList,
    ComparisonHistoryListResponse,
    ComparisonHistoryUpdate,
    SaveComparisonRequest,
    GetComparisonHistoryRequest,
)
from app.models.user_models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


@router.post("/save", response_model=ComparisonHistoryResponse)
async def save_comparison(
    request: SaveComparisonRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save a product comparison result to history
    
    Args:
        request: Comparison data to save
        user: Current authenticated user
        db: Database session
        
    Returns:
        Saved comparison record
    """
    try:
        logger.info(
            f"💾 Saving comparison for user {user.id}: "
            f"{request.product_name_1} vs {request.product_name_2}"
        )

        comparison = ComparisonHistoryRepository.save_comparison(
            db=db,
            user_id=user.id,
            product_id_1=request.product_id_1,
            product_id_2=request.product_id_2,
            product_name_1=request.product_name_1,
            product_name_2=request.product_name_2,
            snapshot_a=request.snapshot_a,
            snapshot_b=request.snapshot_b,
            comparison_result=request.comparison_result,
            summary_json=request.summary_json,
            api_request=request.api_request,
            notes=request.notes,
            comparison_type=request.comparison_type,
            llm_model=request.llm_model,
        )

        logger.info(f"✅ Comparison saved with ID {comparison.id}")
        
        return ComparisonHistoryResponse.model_validate(comparison)

    except Exception as e:
        logger.error(f"❌ Error saving comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error saving comparison: {str(e)}",
        )


@router.get("/history", response_model=ComparisonHistoryListResponse)
async def get_comparison_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    starred_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get comparison history for the current user
    
    Args:
        limit: Number of comparisons to return
        offset: Number of comparisons to skip (for pagination)
        starred_only: Only return starred comparisons
        user: Current authenticated user
        db: Database session
        
    Returns:
        List of comparisons with pagination info
    """
    try:
        logger.info(
            f"📋 Fetching comparison history for user {user.id} "
            f"(limit={limit}, offset={offset}, starred_only={starred_only})"
        )

        comparisons, total = ComparisonHistoryRepository.get_user_comparisons(
            db=db,
            user_id=user.id,
            limit=limit,
            offset=offset,
            starred_only=starred_only,
        )

        # Convert to list response
        comparison_list = [
            ComparisonHistoryList(
                id=c.id,
                product_name_1=c.product_name_1,
                product_name_2=c.product_name_2,
                product_id_1=c.product_id_1,
                product_id_2=c.product_id_2,
                created_at=c.created_at,
                is_starred=c.is_starred,
                comparison_type=c.comparison_type,
            )
            for c in comparisons
        ]

        logger.info(f"✅ Retrieved {len(comparison_list)} comparisons")

        return ComparisonHistoryListResponse(
            total=total,
            limit=limit,
            offset=offset,
            comparisons=comparison_list,
        )

    except Exception as e:
        logger.error(f"❌ Error getting comparison history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving comparison history: {str(e)}",
        )


@router.get("/{comparison_id}", response_model=ComparisonHistoryResponse)
async def get_comparison_detail(
    comparison_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed view of a specific comparison
    
    Args:
        comparison_id: ID of the comparison to retrieve
        user: Current authenticated user
        db: Database session
        
    Returns:
        Full comparison record with all details
    """
    try:
        logger.info(f"🔍 Fetching comparison {comparison_id} for user {user.id}")

        comparison = ComparisonHistoryRepository.get_comparison(
            db=db,
            comparison_id=comparison_id,
            user_id=user.id,
        )

        if not comparison:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison {comparison_id} not found",
            )

        logger.info(f"✅ Retrieved comparison {comparison_id}")
        
        return ComparisonHistoryResponse.model_validate(comparison)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting comparison detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving comparison: {str(e)}",
        )


@router.patch("/{comparison_id}", response_model=ComparisonHistoryResponse)
async def update_comparison(
    comparison_id: int,
    update_data: ComparisonHistoryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update comparison metadata (notes, starred status)
    
    Args:
        comparison_id: ID of the comparison to update
        update_data: Fields to update
        user: Current authenticated user
        db: Database session
        
    Returns:
        Updated comparison record
    """
    try:
        logger.info(f"✏️ Updating comparison {comparison_id} for user {user.id}")

        comparison = ComparisonHistoryRepository.update_comparison(
            db=db,
            comparison_id=comparison_id,
            user_id=user.id,
            notes=update_data.notes,
            is_starred=update_data.is_starred,
        )

        if not comparison:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison {comparison_id} not found",
            )

        logger.info(f"✅ Updated comparison {comparison_id}")
        
        return ComparisonHistoryResponse.model_validate(comparison)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error updating comparison: {str(e)}",
        )


@router.delete("/{comparison_id}")
async def delete_comparison(
    comparison_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a comparison from history
    
    Args:
        comparison_id: ID of the comparison to delete
        user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        logger.info(f"🗑️ Deleting comparison {comparison_id} for user {user.id}")

        success = ComparisonHistoryRepository.delete_comparison(
            db=db,
            comparison_id=comparison_id,
            user_id=user.id,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison {comparison_id} not found",
            )

        logger.info(f"✅ Deleted comparison {comparison_id}")

        return {
            "status": "success",
            "message": f"Comparison {comparison_id} deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting comparison: {str(e)}",
        )


@router.get("/stats/overview")
async def get_comparison_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get comparison statistics for the current user
    
    Returns:
        Statistics about user's comparisons
    """
    try:
        logger.info(f"📊 Getting comparison stats for user {user.id}")

        stats = ComparisonHistoryRepository.get_comparison_stats(
            db=db,
            user_id=user.id,
        )

        return {
            "status": "success",
            "data": stats,
        }

    except Exception as e:
        logger.error(f"❌ Error getting comparison stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}",
        )

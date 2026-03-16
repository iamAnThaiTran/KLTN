# app/api/user_routes.py
"""
User routes for personalization and recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.config.database_orm import get_db
from app.models.user_models import User, SearchHistory
from app.api.auth_middleware import get_current_user
from app.services.user_service import UserService

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user profile and personalization data
    """
    recommendations = UserService.get_personalized_recommendations(db, current_user.id)
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login
        },
        "recommendations": recommendations
    }


@router.get("/search-history")
async def get_search_history(
    limit: int = 20,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's search history
    
    - **limit**: Maximum number of records (default 20)
    - **days**: Only return searches from last N days (default 30)
    """
    history = UserService.get_user_search_history(db, current_user.id, limit=limit, days=days)
    
    return {
        "user_id": current_user.id,
        "search_count": len(history),
        "searches": [
            {
                "id": h.id,
                "query": h.query,
                "category": h.category_name,
                "result_count": h.result_count,
                "clicked_product_id": h.clicked_product_id,
                "searched_at": h.searched_at
            }
            for h in history
        ]
    }


@router.get("/interests")
async def get_user_interests(
    limit: int = 10,
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user's detected interests based on search history
    
    - **limit**: Maximum categories/keywords to return
    - **days**: Only analyze searches from last N days
    """
    categories = UserService.get_user_interested_categories(db, current_user.id, limit=limit, days=days)
    keywords = UserService.get_user_preferred_keywords(db, current_user.id, limit=limit, days=days)
    
    return {
        "user_id": current_user.id,
        "top_categories": categories,
        "popular_keywords": keywords
    }


@router.get("/preferences")
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get user preferences (categories, brands, price range)
    """
    prefs = UserService.get_user_preferences(db, current_user.id)
    
    if not prefs:
        return {
            "user_id": current_user.id,
            "preferred_categories": [],
            "preferred_brands": [],
            "price_range": {"min": None, "max": None}
        }
    
    return {
        "user_id": current_user.id,
        "preferred_categories": prefs.preferred_categories,
        "preferred_brands": prefs.preferred_brands,
        "price_range": {
            "min": float(prefs.price_range_min) if prefs.price_range_min else None,
            "max": float(prefs.price_range_max) if prefs.price_range_max else None
        }
    }


@router.post("/preferences")
async def update_user_preferences(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user preferences
    
    Body can contain:
    - **preferred_categories**: List of category names/slugs
    - **preferred_brands**: List of brand names
    - **price_range_min**: Minimum price
    - **price_range_max**: Maximum price
    """
    prefs = UserService.update_user_preferences(
        db,
        current_user.id,
        preferred_categories=data.get("preferred_categories"),
        preferred_brands=data.get("preferred_brands"),
        price_range_min=data.get("price_range_min"),
        price_range_max=data.get("price_range_max")
    )
    
    return {
        "success": True,
        "user_id": current_user.id,
        "preferred_categories": prefs.preferred_categories,
        "preferred_brands": prefs.preferred_brands,
        "price_range": {
            "min": float(prefs.price_range_min) if prefs.price_range_min else None,
            "max": float(prefs.price_range_max) if prefs.price_range_max else None
        }
    }

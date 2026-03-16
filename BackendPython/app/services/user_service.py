# app/services/user_service.py
"""
User service for personalization and recommendations based on search history
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models.user_models import User, SearchHistory, UserPreferences


class UserService:
    """Service for user-related operations"""

    @staticmethod
    def save_search_query(
        db: Session,
        user_id: Optional[int],
        query: str,
        category_name: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> SearchHistory:
        """
        Save user search query to history
        """
        search = SearchHistory(
            user_id=user_id,
            query=query,
            category_name=category_name,
            session_id=session_id,
            searched_at=datetime.utcnow()
        )
        db.add(search)
        db.commit()
        db.refresh(search)
        return search

    @staticmethod
    def update_search_result_count(
        db: Session,
        search_id: int,
        result_count: int
    ):
        """Update result count for a search"""
        search = db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
        if search:
            search.result_count = result_count
            db.commit()

    @staticmethod
    def update_search_click(
        db: Session,
        search_id: int,
        clicked_product_id: int
    ):
        """Record that user clicked on a product from search results"""
        search = db.query(SearchHistory).filter(SearchHistory.id == search_id).first()
        if search:
            search.clicked_product_id = clicked_product_id
            db.commit()

    @staticmethod
    def get_user_search_history(
        db: Session,
        user_id: int,
        limit: int = 20,
        days: int = 30
    ) -> List[SearchHistory]:
        """
        Get user's search history
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            days: Only return searches from last N days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        history = db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.searched_at >= cutoff_date
        ).order_by(SearchHistory.searched_at.desc()).limit(limit).all()
        
        return history

    @staticmethod
    def get_user_interested_categories(
        db: Session,
        user_id: int,
        limit: int = 10,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get categories the user frequently searches for
        
        Returns list of {category_name, search_count}
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        categories = db.query(
            SearchHistory.category_name,
            func.count(SearchHistory.id).label('search_count')
        ).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.category_name.isnot(None),
            SearchHistory.searched_at >= cutoff_date
        ).group_by(SearchHistory.category_name).order_by(
            func.count(SearchHistory.id).desc()
        ).limit(limit).all()
        
        return [
            {
                "category": cat[0],
                "search_count": cat[1]
            }
            for cat in categories
        ]

    @staticmethod
    def get_user_preferred_keywords(
        db: Session,
        user_id: int,
        limit: int = 20,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Extract keywords from user's search history
        
        Returns list of common search terms
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        searches = db.query(SearchHistory.query).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.searched_at >= cutoff_date
        ).all()
        
        # Simple keyword extraction - just return the queries as-is
        keywords = {}
        for (query,) in searches:
            if query in keywords:
                keywords[query] += 1
            else:
                keywords[query] = 1
        
        # Sort by frequency
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                "keyword": kw[0],
                "frequency": kw[1]
            }
            for kw in sorted_keywords[:limit]
        ]

    @staticmethod
    def update_user_preferences(
        db: Session,
        user_id: int,
        preferred_categories: Optional[List[str]] = None,
        preferred_brands: Optional[List[str]] = None,
        price_range_min: Optional[float] = None,
        price_range_max: Optional[float] = None
    ) -> UserPreferences:
        """
        Update user preferences
        """
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        
        if not prefs:
            prefs = UserPreferences(user_id=user_id)
            db.add(prefs)
        
        if preferred_categories is not None:
            prefs.preferred_categories = preferred_categories
        if preferred_brands is not None:
            prefs.preferred_brands = preferred_brands
        if price_range_min is not None:
            prefs.price_range_min = price_range_min
        if price_range_max is not None:
            prefs.price_range_max = price_range_max
        
        prefs.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(prefs)
        
        return prefs

    @staticmethod
    def get_user_preferences(db: Session, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences"""
        return db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()

    @staticmethod
    def get_personalized_recommendations(
        db: Session,
        user_id: int,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Generate personalization recommendations based on user's history
        """
        prefs = UserService.get_user_preferences(db, user_id)
        categories = UserService.get_user_interested_categories(db, user_id, days=days)
        keywords = UserService.get_user_preferred_keywords(db, user_id, days=days)
        
        return {
            "user_id": user_id,
            "preferences": {
                "preferred_categories": prefs.preferred_categories if prefs else [],
                "preferred_brands": prefs.preferred_brands if prefs else [],
                "price_range": {
                    "min": float(prefs.price_range_min) if prefs and prefs.price_range_min else None,
                    "max": float(prefs.price_range_max) if prefs and prefs.price_range_max else None
                }
            },
            "detected_interests": {
                "top_categories": categories,
                "popular_keywords": keywords
            }
        }

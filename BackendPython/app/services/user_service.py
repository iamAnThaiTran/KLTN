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
    def update_preferences_from_search(
        db: Session,
        user_id: int,
        search_query: str,
        category_name: Optional[str] = None,
        extracted_brands: Optional[List[str]] = None
    ) -> UserPreferences:
        """
        Update user preferences realtime after each search.
        Called every time user performs a search.
        
        Args:
            db: Database session
            user_id: User ID
            search_query: The search query (to extract brands/keywords)
            category_name: Detected category from query
            extracted_brands: Already extracted brands (optional)
        
        Returns:
            Updated UserPreferences
        """
        from app.db.sku_repository import SKURepository
        from app.models.user_models import Category
        
        # Get/create user preferences
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
        if not prefs:
            prefs = UserPreferences(user_id=user_id)
            db.add(prefs)
        
        # 1. Update preferred categories
        if category_name:
            # Get category ID from name
            sku_repo = SKURepository()
            category_slug = sku_repo.get_category_slug_from_name(category_name)
            if category_slug:
                category_obj = db.query(Category).filter(Category.slug == category_slug).first()
                if category_obj:
                    if not prefs.preferred_categories:
                        prefs.preferred_categories = []
                    # Add if not already there, keep top 5
                    if category_obj.id not in prefs.preferred_categories:
                        prefs.preferred_categories = [category_obj.id] + prefs.preferred_categories
                        prefs.preferred_categories = prefs.preferred_categories[:5]
        
        # 2. Update preferred brands
        if extracted_brands:
            if not prefs.preferred_brands:
                prefs.preferred_brands = []
            # Add brands and keep top 10
            for brand in extracted_brands:
                if brand.lower() not in [b.lower() for b in prefs.preferred_brands]:
                    prefs.preferred_brands.append(brand)
            prefs.preferred_brands = prefs.preferred_brands[:10]
        
        prefs.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(prefs)
        
        return prefs

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
    
    @staticmethod
    def get_recommended_products_for_homepage(
        db: Session,
        user_id: int,
        limit: int = 20,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get recommended products for homepage based on user's search history.
        
        Strategy:
        1. Get user's top searched categories
        2. Get user's preferred brands from search queries
        3. Get price range from search history
        4. Query products matching these criteria
        5. Sort by relevance (recency + popularity)
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of products to return
            days: Look back period for search history
        
        Returns:
            List of recommended products with SKUs
        """
        from app.db.sku_repository import SKURepository
        from sqlalchemy import and_
        
        sku_repo = SKURepository()
        
        # 1. Get user's top categories
        top_categories = UserService.get_user_interested_categories(
            db, user_id, limit=3, days=days
        )
        
        if not top_categories:
            return []  # No search history yet
        
        # Get first category for initial recommendation
        primary_category = top_categories[0]["category"]
        
        # 2. Extract brands from search history
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        search_queries = db.query(SearchHistory.query).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.searched_at >= cutoff_date
        ).all()
        
        # Simple brand extraction from queries
        brand_keywords = set()
        popular_brands = ["Nike", "Adidas", "Apple", "Samsung", "Sony", "Puma", 
                         "Reebok", "Vans", "Converse", "Timberland", "Canon", "LG"]
        
        for (query,) in search_queries:
            query_lower = query.lower()
            for brand in popular_brands:
                if brand.lower() in query_lower:
                    brand_keywords.add(brand)
        
        # 3. Get price range from user preferences or search history
        user_prefs = UserService.get_user_preferences(db, user_id)
        min_price = user_prefs.price_range_min if user_prefs and user_prefs.price_range_min else 0
        max_price = user_prefs.price_range_max if user_prefs and user_prefs.price_range_max else 100000000
        
        # 4. Search products matching criteria
        try:
            # Build filters for SKU repository
            filters = {}
            
            # Add brand filter if brands were detected
            if brand_keywords:
                filters['brand'] = list(brand_keywords)
            
            # Search with filters
            category_slug = sku_repo.get_category_slug_from_name(primary_category)
            if not category_slug:
                return []
            
            products, total = sku_repo.search_products(
                category_slug=category_slug,
                filters=filters,
                min_price=float(min_price),
                max_price=float(max_price),
                page=1,
                page_size=limit
            )
            
            return products
        except Exception as e:
            print(f"[get_recommended_products_for_homepage] Error: {e}")
            return []

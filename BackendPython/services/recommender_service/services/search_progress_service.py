# app/services/search_progress_service.py
"""
Progressive search service for immediate attribute suggestions + parallel crawling.

Workflow:
1. User submits search query
2. Instantly detect category + return filter suggestions
3. In parallel, start background crawl
4. Frontend polls for product results
5. If user refines filters, apply them to existing results (no re-crawl)
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..core.intent_mapper import IntentMapper  # ✅ LOCAL
from ..db.sku_repository import SKURepository  # ✅ LOCAL
from ..crawler.crawler import TikiCrawler  # ✅ LOCAL
from .session_manager_factory import get_session_manager  # ✅ LOCAL
from .search_models import SearchSession, SearchState  # ✅ LOCAL


class SearchProgressService:
    """
    Core service for progressive search:
    - Immediate category detection
    - Quick filter suggestions from DB
    - Parallel background crawling
    - Progressive filtering on results
    """
    
    def __init__(self):
        self.intent_mapper = IntentMapper()
        self.sku_repo = SKURepository()
        self.tiki_crawler = TikiCrawler()
        
        # Use session manager (Redis or in-memory based on availability)
        self.session_manager = get_session_manager()
    
    def create_session(self, user_query: str, session_id: Optional[str] = None) -> SearchSession:
        """
        Create a new search session.
        
        Returns: SearchSession with immediate category + filters
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = SearchSession(session_id)
        session.original_query = user_query
        
        # Step 1: Detect category from query (IMMEDIATE - no waiting)
        intent_result = self.intent_mapper.map_intent(user_query)
        
        if intent_result["categories"]:
            # Use first category as primary
            category_name = intent_result["categories"][0]
            session.detected_category = category_name
            session.category_slug = self._category_to_slug(category_name)
            session.product_name = intent_result.get("product_name")  # ← NEW: Store brand/product name
            session.intent_confidence = intent_result["confidence"]
            session.intent_method = intent_result.get("method", "unknown")
        
        # Step 2: Get filter suggestions from DB (IMMEDIATE - pre-computed)
        if session.category_slug:
            session.suggested_filters = self._get_filter_suggestions(session.category_slug)
        
        # Step 3: Store session using session manager (Redis or in-memory)
        session.state = SearchState.INITIAL
        self.session_manager.save_session(session)
        
        return session
    
    async def start_background_crawl(self, session_id: str, sources: Optional[List[str]] = None):
        """
        Start background crawl for a session.
        This runs in parallel and doesn't block the API response.
        
        sources: ["tiki", "lazada"] or None for all
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if not session.category_slug:
            raise ValueError("Category not detected, cannot crawl")
        
        session.state = SearchState.CRAWLING
        session.crawl_sources = sources or ["tiki", "lazada"]
        self.session_manager.save_session(session)
        
        # Run crawl in background
        asyncio.create_task(
            self._background_crawl(session_id)
        )
    
    async def _background_crawl(self, session_id: str):
        """
        Background crawl task (runs independently).
        Updates session as data arrives.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return
        
        try:
            all_products = []
            
            if "tiki" in session.crawl_sources:
                try:
                    tiki_products = await self._crawl_tiki(
                        session.detected_category,
                        session_id
                    )
                    all_products.extend(tiki_products)
                    session.crawl_progress["tiki"] = 100
                except Exception as e:
                    session.crawl_error = f"Tiki crawl failed: {str(e)}"
                    session.crawl_progress["tiki"] = -1
            
            if "lazada" in session.crawl_sources:
                try:
                    lazada_products = await self._crawl_lazada(
                        session.detected_category,
                        session_id
                    )
                    all_products.extend(lazada_products)
                    session.crawl_progress["lazada"] = 100
                except Exception as e:
                    session.crawl_error = f"Lazada crawl failed: {str(e)}"
                    session.crawl_progress["lazada"] = -1
            
            # Store raw results
            session.raw_products = all_products
            session.total_products = len(all_products)
            session.filtered_products = all_products  # Initially unfiltered
            session.state = SearchState.READY
            session.last_updated_at = datetime.utcnow()
            
            # Save updated session to manager
            self.session_manager.save_session(session)
            
        except Exception as e:
            session = self.session_manager.get_session(session_id)
            if session:
                session.state = SearchState.ERROR
                session.crawl_error = str(e)
                session.last_updated_at = datetime.utcnow()
                self.session_manager.save_session(session)
    
    async def _crawl_tiki(self, category: str, session_id: str) -> List[Dict[str, Any]]:
        """Crawl Tiki for category products"""
        # TODO: Implement actual crawling
        # For now, return mock data or empty
        return []
    
    async def _crawl_lazada(self, category: str, session_id: str) -> List[Dict[str, Any]]:
        """Crawl Lazada for category products"""
        # TODO: Implement actual crawling
        # For now, return mock data or empty
        return []
    
    def apply_filters(self, session_id: str, filters: Dict[str, List[str]]):
        """
        Apply user-selected filters to existing results.
        NO CRAWL - just filter from raw_products.
        
        filters: {"size": ["42", "43"], "color": ["Đen"]}
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Store user's filter choices
        session.user_selected_filters = filters
        
        # Apply filters to raw products
        filtered = self._apply_filters_to_products(
            session.raw_products,
            filters
        )
        
        session.filtered_products = filtered
        session.state = SearchState.REFINED
        session.last_updated_at = datetime.utcnow()
        
        # Save updated session
        self.session_manager.save_session(session)
    
    def _apply_filters_to_products(
        self,
        products: List[Dict[str, Any]],
        filters: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Filter products by user-selected attributes.
        
        filters = {
            "size": ["42", "43"],
            "color": ["Đen", "Trắng"]
        }
        """
        if not filters:
            return products
        
        filtered = []
        for product in products:
            if self._product_matches_filters(product, filters):
                filtered.append(product)
        
        return filtered
    
    def _product_matches_filters(
        self,
        product: Dict[str, Any],
        filters: Dict[str, List[str]]
    ) -> bool:
        """Check if product matches all filter criteria"""
        attributes = product.get("attributes", {})
        
        for attr_name, filter_values in filters.items():
            # Product must have this attribute with one of the filter values
            product_attr_value = attributes.get(attr_name)
            if not product_attr_value or product_attr_value not in filter_values:
                return False
        
        return True
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get current session state.
        Returns progressively as crawl completes.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            "session_id": session_id,
            "state": session.state.value,
            "detected_category": session.detected_category,
            "category_slug": session.category_slug,
            "intent_confidence": session.intent_confidence,
            "suggested_filters": session.suggested_filters,
            "user_selected_filters": session.user_selected_filters,
            "products": session.filtered_products,
            "total_products": session.total_products,
            "filtered_products_count": len(session.filtered_products),
            "crawl_progress": session.crawl_progress,
            "crawl_sources": session.crawl_sources,
            "crawl_error": session.crawl_error,
            "is_crawling": session.state == SearchState.CRAWLING,
        }
    
    def _get_filter_suggestions(self, category_slug: str) -> Dict[str, Any]:
        """
        Get filter suggestions from DB for this category.
        These are computed ahead of time - no waiting for crawl.
        
        Returns: {
            "size": {
                "attribute_name": "size",
                "display_name": "Size",
                "data_type": "enum",
                "options": [
                    {"attribute_value": "40", "product_count": 15},
                    ...
                ]
            },
            ...
        }
        """
        try:
            filters = self.sku_repo.get_available_filters(category_slug)
            
            result = {}
            for f in filters:
                if f['options']:  # Only include if has options
                    result[f['attribute_name']] = {
                        'attribute_name': f['attribute_name'],
                        'display_name': f['display_name'] or f['attribute_name'],
                        'data_type': f['data_type'],
                        'options': f['options']
                    }
            
            return result
        except Exception as e:
            print(f"Error getting filter suggestions: {e}")
            return {}
    
    def _category_to_slug(self, category_name: str) -> str:
        """
        Convert category name to slug.
        e.g., "Quần áo" -> "quan-ao"
        """
        import unicodedata
        
        # Normalize and remove accents
        slug = unicodedata.normalize('NFKD', category_name)
        slug = slug.encode('ASCII', 'ignore').decode('ASCII')
        
        # Convert to lowercase and replace spaces with hyphens
        slug = slug.lower().strip()
        slug = slug.replace(' ', '-')
        
        return slug
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        return self.session_manager.cleanup_expired_sessions()

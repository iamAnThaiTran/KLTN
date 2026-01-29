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
from enum import Enum
import json

from app.core.intent_mapper import IntentMapper
from app.db.sku_repository import SKURepository
from app.crawler.crawler import TikiCrawler


class SearchState(str, Enum):
    """Search session state"""
    INITIAL = "initial"  # Category detected, filters suggested
    CRAWLING = "crawling"  # Background crawl in progress
    READY = "ready"  # Products ready
    REFINED = "refined"  # Filters applied to results
    ERROR = "error"  # Error occurred


class SearchSession:
    """
    Represents a user's search session with progressive updates.
    Stored in Redis for persistence.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.last_updated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Search state
        self.state = SearchState.INITIAL
        self.original_query = None
        
        # Detected intent
        self.detected_category = None
        self.category_slug = None
        self.intent_confidence = 0.0
        self.intent_method = None  # "pattern" or "llm"
        
        # Filter suggestions (immediate)
        self.suggested_filters: Dict[str, Any] = {}  # attribute_name -> FilterGroup
        self.user_selected_filters: Dict[str, List[str]] = {}  # User's filter choices
        
        # Crawl results (background)
        self.raw_products: List[Dict[str, Any]] = []
        self.total_products: int = 0
        self.filtered_products: List[Dict[str, Any]] = []  # After user filters applied
        
        # Progress tracking
        self.crawl_sources = []  # ["tiki", "lazada", etc.]
        self.crawl_progress = {}  # {"tiki": 45, "lazada": 20, ...}
        self.crawl_error = None
        self.crawl_task_id = None  # For tracking background task
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for Redis storage"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "state": self.state.value,
            "original_query": self.original_query,
            "detected_category": self.detected_category,
            "category_slug": self.category_slug,
            "intent_confidence": self.intent_confidence,
            "intent_method": self.intent_method,
            "suggested_filters": {
                k: {
                    "attribute_name": v.get("attribute_name"),
                    "display_name": v.get("display_name"),
                    "data_type": v.get("data_type"),
                    "options": v.get("options", [])
                }
                for k, v in self.suggested_filters.items()
            },
            "user_selected_filters": self.user_selected_filters,
            "raw_products_count": len(self.raw_products),
            "total_products": self.total_products,
            "filtered_products_count": len(self.filtered_products),
            "crawl_sources": self.crawl_sources,
            "crawl_progress": self.crawl_progress,
            "crawl_error": self.crawl_error,
            "crawl_task_id": self.crawl_task_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchSession":
        """Deserialize from Redis storage"""
        session = cls(data["session_id"])
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_updated_at = datetime.fromisoformat(data["last_updated_at"])
        session.expires_at = datetime.fromisoformat(data["expires_at"])
        session.state = SearchState(data["state"])
        session.original_query = data["original_query"]
        session.detected_category = data["detected_category"]
        session.category_slug = data["category_slug"]
        session.intent_confidence = data["intent_confidence"]
        session.intent_method = data["intent_method"]
        session.suggested_filters = data.get("suggested_filters", {})
        session.user_selected_filters = data.get("user_selected_filters", {})
        session.total_products = data.get("total_products", 0)
        session.crawl_sources = data.get("crawl_sources", [])
        session.crawl_progress = data.get("crawl_progress", {})
        session.crawl_error = data.get("crawl_error")
        session.crawl_task_id = data.get("crawl_task_id")
        return session


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
        
        # In production, use Redis
        # For now, use in-memory storage
        self._sessions: Dict[str, SearchSession] = {}
    
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
            session.intent_confidence = intent_result["confidence"]
            session.intent_method = intent_result.get("method", "unknown")
        
        # Step 2: Get filter suggestions from DB (IMMEDIATE - pre-computed)
        if session.category_slug:
            session.suggested_filters = self._get_filter_suggestions(session.category_slug)
        
        # Step 3: Store session
        self._sessions[session_id] = session
        session.state = SearchState.INITIAL
        
        return session
    
    async def start_background_crawl(self, session_id: str, sources: Optional[List[str]] = None):
        """
        Start background crawl for a session.
        This runs in parallel and doesn't block the API response.
        
        sources: ["tiki", "lazada"] or None for all
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if not session.category_slug:
            raise ValueError("Category not detected, cannot crawl")
        
        session.state = SearchState.CRAWLING
        session.crawl_sources = sources or ["tiki", "lazada"]
        
        # Run crawl in background
        asyncio.create_task(
            self._background_crawl(session_id)
        )
    
    async def _background_crawl(self, session_id: str):
        """
        Background crawl task (runs independently).
        Updates session as data arrives.
        """
        session = self._sessions.get(session_id)
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
            
        except Exception as e:
            session.state = SearchState.ERROR
            session.crawl_error = str(e)
            session.last_updated_at = datetime.utcnow()
    
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
        session = self._sessions.get(session_id)
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
        session = self._sessions.get(session_id)
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
        now = datetime.utcnow()
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < now
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

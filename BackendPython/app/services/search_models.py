# app/services/search_models.py
"""
Search session models - separated to avoid circular imports.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum


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
        self.product_name = None  # ← NEW: Brand or product name from intent mapping (e.g., "sagami", "bột giặt")
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
            "product_name": self.product_name,  # ← NEW
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
        session.product_name = data.get("product_name")  # ← NEW
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

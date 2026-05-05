"""
app/services/user_service_client.py
HTTP Client for User Service inter-service communication
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
import httpx

logger = logging.getLogger(__name__)


class UserServiceClient:
    """
    HTTP client for communicating with UserService.
    Handles user authentication, preferences, history, and alerts.
    
    UserService runs on port 8004
    """
    
    def __init__(
        self,
        base_url: str = "http://user-service:8004",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute HTTP request with automatic retry on failure
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional httpx parameters
        
        Returns:
            Response JSON
        
        Raises:
            httpx.HTTPError: If request fails after retries
        """
        url = f"{self.base_url}{endpoint}"
        client = await self._get_client()
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"UserServiceClient: {method} {url}")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"UserServiceClient request failed: {method} {url} - {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        
        logger.error(f"UserServiceClient: Failed after {self.max_retries} retries")
        raise last_error or Exception("Request failed")
    
    # ========================================================================
    # User Profile APIs
    # ========================================================================
    
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information
        
        Returns:
            {
                "user_id": str,
                "email": str,
                "full_name": str,
                "provider": str,
                "created_at": datetime
            }
        """
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}"
        )
    
    async def create_user(
        self,
        email: str,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
        provider: str = "local",
        provider_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user account"""
        payload = {
            "email": email,
            "provider": provider
        }
        if full_name:
            payload["full_name"] = full_name
        if password:
            payload["password"] = password
        if provider_id:
            payload["provider_id"] = provider_id
        
        return await self._request_with_retry(
            "POST",
            "/api/users",
            json=payload
        )
    
    async def update_user(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user profile"""
        return await self._request_with_retry(
            "PUT",
            f"/api/users/{user_id}",
            json=update_data
        )
    
    # ========================================================================
    # User Preferences APIs
    # ========================================================================
    
    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences and settings
        
        Returns:
            {
                "language": str,
                "currency": str,
                "categories": [...],
                "brands": [...],
                "notifications": {...}
            }
        """
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/preferences"
        )
    
    async def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user preferences"""
        return await self._request_with_retry(
            "PUT",
            f"/api/users/{user_id}/preferences",
            json=preferences
        )
    
    # ========================================================================
    # Search History APIs
    # ========================================================================
    
    async def record_search(
        self,
        user_id: str,
        query: str, 
        category: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        results_count: int = 0
    ) -> Dict[str, Any]:
        """Record a search in user history"""
        payload = {
            "query": query,
            "results_count": results_count
        }
        if category:
            payload["category"] = category
        if filters:
            payload["filters"] = filters
        
        return await self._request_with_retry(
            "POST",
            f"/api/users/{user_id}/search-history",
            json=payload
        )
    
    async def get_search_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's search history"""
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/search-history",
            params={"limit": limit, "offset": offset}
        )
    
    # ========================================================================
    # Favorites / Wishlist APIs
    # ========================================================================
    
    async def add_favorite(
        self,
        user_id: str,
        product_id: str,
        sku_id: Optional[str] = None,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Add product to user's wishlist"""
        payload = {"product_id": product_id}
        if sku_id:
            payload["sku_id"] = sku_id
        if price:
            payload["price"] = price
        
        return await self._request_with_retry(
            "POST",
            f"/api/users/{user_id}/favorites",
            json=payload
        )
    
    async def remove_favorite(
        self,
        user_id: str,
        product_id: str
    ) -> Dict[str, Any]:
        """Remove product from favorites"""
        return await self._request_with_retry(
            "DELETE",
            f"/api/users/{user_id}/favorites/{product_id}"
        )
    
    async def get_favorites(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's favorite products"""
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/favorites",
            params={"limit": limit, "offset": offset}
        )
    
    # ========================================================================
    # Price Alerts APIs
    # ========================================================================
    
    async def create_price_alert(
        self,
        user_id: str,
        product_id: str,
        target_price: float,
        alert_type: str = "price_drop"
    ) -> Dict[str, Any]:
        """Create a price alert for a product"""
        return await self._request_with_retry(
            "POST",
            f"/api/users/{user_id}/alerts",
            json={
                "product_id": product_id,
                "target_price": target_price,
                "alert_type": alert_type
            }
        )
    
    async def get_price_alerts(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get user's price alerts"""
        response = await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/alerts",
            params={"active_only": active_only}
        )
        return response.get("alerts", [])
    
    async def delete_price_alert(
        self,
        user_id: str,
        alert_id: int
    ) -> Dict[str, Any]:
        """Delete a price alert"""
        return await self._request_with_retry(
            "DELETE",
            f"/api/users/{user_id}/alerts/{alert_id}"
        )
    
    # ========================================================================
    # Review APIs
    # ========================================================================
    
    async def submit_review(
        self,
        user_id: str,
        product_id: str,
        rating: int,
        review_text: Optional[str] = None,
        images: Optional[List[str]] = None,
        sku_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a product review"""
        payload = {
            "product_id": product_id,
            "rating": rating
        }
        if review_text:
            payload["review_text"] = review_text
        if images:
            payload["images"] = images
        if sku_id:
            payload["sku_id"] = sku_id
        
        return await self._request_with_retry(
            "POST",
            f"/api/users/{user_id}/reviews",
            json=payload
        )
    
    async def get_user_reviews(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get reviews submitted by user"""
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/reviews",
            params={"limit": limit, "offset": offset}
        )
    
    # ========================================================================
    # Comparison History APIs
    # ========================================================================
    
    async def record_comparison(
        self,
        user_id: str,
        comparison_id: str,
        product_ids: List[str],
        winning_product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a product comparison"""
        return await self._request_with_retry(
            "POST",
            f"/api/users/{user_id}/comparisons",
            json={
                "comparison_id": comparison_id,
                "product_ids": product_ids,
                "winning_product_id": winning_product_id
            }
        )
    
    async def get_comparison_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's comparison history"""
        return await self._request_with_retry(
            "GET",
            f"/api/users/{user_id}/comparisons",
            params={"limit": limit, "offset": offset}
        )
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            response = await self._request_with_retry(
                "GET",
                "/api/health"
            )
            return response.get("status") == "healthy"
        except Exception as e:
            logger.error(f"UserService health check failed: {e}")
            return False


# Singleton instance for global access
_user_service_client: Optional[UserServiceClient] = None


async def get_user_service_client() -> UserServiceClient:
    """Get singleton UserServiceClient instance"""
    global _user_service_client
    if _user_service_client is None:
        _user_service_client = UserServiceClient()
    return _user_service_client


async def close_user_service_client():
    """Close the singleton client"""
    global _user_service_client
    if _user_service_client:
        await _user_service_client.close()
        _user_service_client = None

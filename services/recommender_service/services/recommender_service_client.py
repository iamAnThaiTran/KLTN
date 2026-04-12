"""
app/services/recommender_service_client.py
HTTP Client for Recommender Service inter-service communication
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
import httpx

logger = logging.getLogger(__name__)


class RecommendatorServiceClient:
    """
    HTTP client for communicating with RecommendatorService.
    Handles intent detection, ranking, classification, and dialog.
    
    RecommendatorService runs on port 8002
    """
    
    def __init__(
        self,
        base_url: str = "http://recommender-service:8002",
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
                logger.debug(f"RecommendatorServiceClient: {method} {url}")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"RecommendatorServiceClient request failed: {method} {url} - {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        
        logger.error(f"RecommendatorServiceClient: Failed after {self.max_retries} retries")
        raise last_error or Exception("Request failed")
    
    # ========================================================================
    # Intent Detection APIs
    # ========================================================================
    
    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect user intent from natural language
        
        Args:
            user_input: User's input text (e.g., "I want a laptop under 500")
            context: Optional context (previous intents, category, etc.)
        
        Returns:
            {
                "intent_type": str,
                "confidence": float,
                "categories": [str],
                "attributes": {...},
                "cached": bool
            }
        """
        payload = {"input": user_input}
        if context:
            payload["context"] = context
        
        return await self._request_with_retry(
            "POST",
            "/api/intent/detect",
            json=payload
        )
    
    async def classify_intent(
        self,
        user_input: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify user input into 7 cases for routing
        
        Returns:
            {
                "case": int (1-7),
                "case_name": str,
                "attributes": {...},
                "confidence": float
            }
        """
        payload = {"input": user_input}
        if category:
            payload["category"] = category
        
        return await self._request_with_retry(
            "POST",
            "/api/classify",
            json=payload
        )
    
    # ========================================================================
    # Ranking and Recommendation APIs
    # ========================================================================
    
    async def rank_products(
        self,
        products: List[Dict[str, Any]],
        category: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank products by relevance to user intent
        
        Args:
            products: List of products to rank
            category: Product category
            user_preferences: Optional user preference weights
            weights: Optional custom ranking weights
        
        Returns:
            Ranked products list with relevance scores
        """
        payload = {
            "products": products,
            "category": category
        }
        if user_preferences:
            payload["user_preferences"] = user_preferences
        if weights:
            payload["weights"] = weights
        
        response = await self._request_with_retry(
            "POST",
            "/api/rank",
            json=payload
        )
        return response.get("ranked_products", [])
    
    async def score_product(
        self,
        product: Dict[str, Any],
        category: str,
        criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score a single product against criteria
        
        Returns:
            {
                "product_id": str,
                "score": float,
                "component_scores": {...}
            }
        """
        payload = {
            "product": product,
            "category": category
        }
        if criteria:
            payload["criteria"] = criteria
        
        return await self._request_with_retry(
            "POST",
            "/api/score",
            json=payload
        )
    
    # ========================================================================
    # Question/Dialog APIs
    # ========================================================================
    
    async def get_clarification_questions(
        self,
        intent: str,
        category: str,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get clarification questions to refine user intent
        
        Args:
            intent: Detected intent type
            category: Product category
            count: Number of questions to retrieve
        
        Returns:
            List of {
                "question": str,
                "question_type": str (e.g., "multiple_choice"),
                "options": [...]
            }
        """
        return await self._request_with_retry(
            "GET",
            "/api/questions",
            params={
                "intent": intent,
                "category": category,
                "limit": count
            }
        )
    
    async def get_ranking_weights(
        self,
        category: str
    ) -> Dict[str, float]:
        """Get current ranking weights for a category"""
        response = await self._request_with_retry(
            "GET",
            f"/api/weights/{category}"
        )
        return response.get("weights", {})
    
    async def update_ranking_weights(
        self,
        category: str,
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """Update ranking weights (admin operation)"""
        return await self._request_with_retry(
            "PUT",
            f"/api/weights/{category}",
            json={"weights": weights}
        )
    
    # ========================================================================
    # Cache Management APIs
    # ========================================================================
    
    async def get_cache_hit_rate(self) -> Dict[str, Any]:
        """Get intent detection cache statistics"""
        return await self._request_with_retry(
            "GET",
            "/api/cache/stats"
        )
    
    async def clear_intent_cache(
        self,
        older_than_hours: int = 24
    ) -> Dict[str, Any]:
        """Clear expired intent cache entries"""
        return await self._request_with_retry(
            "DELETE",
            "/api/cache/intent",
            params={"older_than_hours": older_than_hours}
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
            logger.error(f"RecommendatorService health check failed: {e}")
            return False


# Singleton instance for global access
_recommender_service_client: Optional[RecommendatorServiceClient] = None


async def get_recommender_service_client() -> RecommendatorServiceClient:
    """Get singleton RecommendatorServiceClient instance"""
    global _recommender_service_client
    if _recommender_service_client is None:
        _recommender_service_client = RecommendatorServiceClient()
    return _recommender_service_client


async def close_recommender_service_client():
    """Close the singleton client"""
    global _recommender_service_client
    if _recommender_service_client:
        await _recommender_service_client.close()
        _recommender_service_client = None

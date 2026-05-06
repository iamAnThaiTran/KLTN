"""
app/services/crawl_service_client.py
HTTP Client for Crawl Service inter-service communication
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
import httpx

logger = logging.getLogger(__name__)


class CrawlServiceClient:
    """
    HTTP client for communicating with CrawlService.
    Enqueue crawl tasks and track their status via RabbitMQ integration.
    
    CrawlService runs on port 8003
    """
    
    def __init__(
        self,
        base_url: str = "http://crawl-service:8003",
        timeout: float = 30.0,
        max_retries: int = 5,
        retry_delay: float = 2.0
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
                logger.debug(f"CrawlServiceClient: {method} {url}")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"CrawlServiceClient request failed: {method} {url} - {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        
        logger.error(f"CrawlServiceClient: Failed after {self.max_retries} retries")
        raise last_error or Exception("Request failed")
    
    # ========================================================================
    # Crawl Task APIs
    # ========================================================================
    
    async def enqueue_crawl(
        self,
        category: str,
        category_id: int,
        sources: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Enqueue a new crawl task to RabbitMQ
        
        Args:
            category: Product category (e.g., "smartphone")
            category_id: Category ID from products_db
            sources: Which sources to crawl (tiki, lazada, shopee)
            attributes: Specific attributes to filter by
            priority: Task priority (high, normal, low)
            max_retries: Maximum retry attempts
        
        Returns:
            {
                "task_id": str,
                "status": "pending",
                "estimated_completion": datetime
            }
        """
        payload = {
            "category": category,
            "category_id": category_id,
            "priority": priority,
            "max_retries": max_retries
        }
        if sources:
            payload["sources"] = sources
        if attributes:
            payload["attributes"] = attributes
        
        return await self._request_with_retry(
            "POST",
            "/api/crawl/enqueue",
            json=payload
        )
    
    async def enqueue_single_crawl(
        self,
        product_id: int,
        seller_id: str = "1",
        priority: str = "normal",
        max_retries: int = 3
    ) -> str:
        """
        Enqueue a single product crawl task (for comparison/details)
        
        Args:
            product_id: Product ID from products_db
            seller_id: Seller ID (default: "1" for Tiki)
            priority: Task priority (high, normal, low)
            max_retries: Maximum retry attempts
        
        Returns:
            task_id (str)
        """
        payload = {
            "product_id": product_id,
            "seller_id": seller_id,
            "priority": priority,
            "max_retries": max_retries,
            "crawl_reviews": True,  # Always crawl reviews for comparison
        }
        
        result = await self._request_with_retry(
            "POST",
            "/api/crawl/enqueue-single",
            json=payload
        )
        
        return result.get("task_id") or result.get("id")
    
    async def enqueue_product_detail_crawl(
        self,
        product_ids: List[str],
        schema: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 3,
        priority: str = "normal",
        max_retries: int = 3
    ) -> str:
        """
        Enqueue product details crawl task with attribute extraction via RabbitMQ
        
        🆕 Replaces direct ProductDetailCrawler usage - offloads to CrawlService
        
        Args:
            product_ids: List of Tiki product IDs to crawl details for
            schema: Optional dynamic schema for attribute extraction
            max_concurrent: Max concurrent crawls
            priority: Task priority (high, normal, low)
            max_retries: Maximum retry attempts
        
        Returns:
            task_id (str) - Use get_task_result() to poll for completion
        """
        payload = {
            "product_ids": product_ids,
            "schema": schema,
            "max_concurrent": max_concurrent,
            "priority": priority,
            "max_retries": max_retries
        }
        
        result = await self._request_with_retry(
            "POST",
            "/api/crawl/enqueue-product-details",
            json=payload
        )
        
        return result.get("task_id")
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl task
        
        Returns:
            {
                "task_id": str,
                "status": str,
                "progress": {...},
                "error": str (if failed)
            }
        """
        return await self._request_with_retry(
            "GET",
            f"/api/crawl/status/{task_id}"
        )
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get result of a crawl task (polling-safe - doesn't throw on 4xx)
        
        Returns:
            {
                "task_id": str,
                "status": "pending" | "running" | "completed" | "failed",
                "snapshot": {...} or None,
                "error": str or None
            }
        """
        url = f"{self.base_url}/api/crawl/result/{task_id}"
        client = await self._get_client()
        
        try:
            logger.debug(f"CrawlServiceClient: GET {url}")
            response = await client.get(url)
            # Don't raise on 4xx - task might not be completed yet
            return response.json()
        except Exception as e:
            logger.error(f"CrawlServiceClient.get_task_result failed: {e}")
            return None
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a pending or running crawl task"""
        return await self._request_with_retry(
            "POST",
            f"/api/crawl/cancel/{task_id}"
        )
    
    # ========================================================================
    # Task History and Monitoring
    # ========================================================================
    
    async def get_task_history(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get history of crawl tasks"""
        params = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if status:
            params["status"] = status
        
        return await self._request_with_retry(
            "GET",
            "/api/crawl/history",
            params=params
        )
    
    async def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get overall crawl statistics"""
        return await self._request_with_retry(
            "GET",
            "/api/crawl/statistics"
        )
    
    # ========================================================================
    # Dead Letter Queue (DLQ) Management
    # ========================================================================
    
    async def get_dlq_messages(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get messages from Dead Letter Queue (failed tasks)
        
        Returns:
            {
                "total": int,
                "messages": [{
                    "task_id": str,
                    "error": str,
                    "timestamp": datetime,
                    "retry_count": int
                }]
            }
        """
        return await self._request_with_retry(
            "GET",
            "/api/dlq/messages",
            params={"limit": limit, "offset": offset}
        )
    
    async def retry_dlq_message(self, task_id: str) -> Dict[str, Any]:
        """Requeue a failed task from DLQ"""
        return await self._request_with_retry(
            "POST",
            f"/api/dlq/retry/{task_id}"
        )
    
    async def discard_dlq_message(self, task_id: str) -> Dict[str, Any]:
        """Permanently discard a DLQ message"""
        return await self._request_with_retry(
            "DELETE",
            f"/api/dlq/messages/{task_id}"
        )
    
    # ========================================================================
    # Crawler Configuration
    # ========================================================================
    
    async def get_crawler_config(self, source: str) -> Dict[str, Any]:
        """Get configuration for a specific crawler (tiki, lazada, etc.)"""
        return await self._request_with_retry(
            "GET",
            f"/api/crawler/config/{source}"
        )
    
    async def update_crawler_config(
        self,
        source: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update crawler configuration"""
        return await self._request_with_retry(
            "PUT",
            f"/api/crawler/config/{source}",
            json=config
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
            logger.error(f"CrawlService health check failed: {e}")
            return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get RabbitMQ queue status"""
        return await self._request_with_retry(
            "GET",
            "/api/queue/status"
        )
    
    # ========================================================================
    # Blocking Crawl (Synchronous API for direct use)
    # ========================================================================
    
    async def crawl(
        self,
        category: str,
        category_id: int,
        attributes: Optional[Dict[str, Any]] = None,
        sources: Optional[List[str]] = None,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        BLOCKING crawl operation - enqueue task and wait for completion
        
        This method provides a synchronous-like interface for orchestrator compatibility.
        
        Args:
            category: Product category name
            category_id: Category ID from database
            attributes: Optional filtering attributes
            sources: Optional list of sources (tiki, lazada, shopee)
            timeout_seconds: Maximum wait time (default: 5 minutes)
            poll_interval: How often to check status (seconds)
        
        Returns:
            List of products found
        
        Raises:
            TimeoutError: If task takes too long
            Exception: If crawl task fails
        
        Example:
            products = await crawl_client.crawl(
                category="giày",
                category_id=1,
                attributes={"brand": "Nike", "size": "40"}
            )
        """
        logger.info(f"[CrawlServiceClient] 🚀 Starting blocking crawl: {category}")
        
        # STEP 1: Enqueue crawl task
        try:
            enqueue_result = await self.enqueue_crawl(
                category=category,
                category_id=category_id,
                attributes=attributes,
                sources=sources,
                priority="high"  # Use high priority for direct crawls
            )
            task_id = enqueue_result["task_id"]
            logger.info(f"[CrawlServiceClient] ✅ Task enqueued: {task_id}")
        except Exception as e:
            logger.error(f"[CrawlServiceClient] ❌ Failed to enqueue crawl: {e}")
            raise
        
        # STEP 2: Poll for task completion
        elapsed = 0.0
        while elapsed < timeout_seconds:
            try:
                status_result = await self.get_task_status(task_id)
                task_status = status_result.get("status")
                
                logger.info(f"[CrawlServiceClient] ⏳ Task {task_id} status: {task_status}")
                
                if task_status == "completed":
                    logger.info(f"[CrawlServiceClient] ✅ Task completed: {task_id}")
                    break
                
                elif task_status == "failed":
                    error_msg = status_result.get("error", "Unknown error")
                    logger.error(f"[CrawlServiceClient] ❌ Task failed: {error_msg}")
                    raise Exception(f"Crawl task failed: {error_msg}")
                
                elif task_status == "cancelled":
                    logger.warning(f"[CrawlServiceClient] ⚠️  Task cancelled: {task_id}")
                    raise Exception("Crawl task was cancelled")
                
                # Task still running - wait and retry
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
            except Exception as e:
                if "failed" in str(e).lower() or "cancel" in str(e).lower():
                    raise
                logger.warning(f"[CrawlServiceClient] ⚠️  Error checking status: {e}, retrying...")
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
        
        if elapsed >= timeout_seconds:
            logger.error(f"[CrawlServiceClient] ❌ Crawl timeout after {timeout_seconds}s")
            await self.cancel_task(task_id)
            raise TimeoutError(f"Crawl task did not complete within {timeout_seconds} seconds")
        
        # STEP 3: Fetch results with products
        try:
            result = await self.get_task_result(task_id)
            
            # ✅ Extract products from result
            products = result.get("products", [])
            products_found = result.get("products_found", 0)
            products_saved = result.get("products_saved", 0)
            
            logger.info(
                f"[CrawlServiceClient] ✅ Crawl complete: "
                f"{products_found} found, {products_saved} saved, {len(products)} returned"
            )
            
            # Return products list (not metadata)
            return products
            
        except Exception as e:
            logger.error(f"[CrawlServiceClient] ❌ Failed to get task result: {e}")
            raise Exception(f"Failed to retrieve crawl results: {e}")


# Singleton instance for global access
_crawl_service_client: Optional[CrawlServiceClient] = None


async def get_crawl_service_client() -> CrawlServiceClient:
    """Get singleton CrawlServiceClient instance"""
    global _crawl_service_client
    if _crawl_service_client is None:
        _crawl_service_client = CrawlServiceClient()
    return _crawl_service_client


async def close_crawl_service_client():
    """Close the singleton client"""
    global _crawl_service_client
    if _crawl_service_client:
        await _crawl_service_client.close()
        _crawl_service_client = None

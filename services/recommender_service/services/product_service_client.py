"""
app/services/product_service_client.py
HTTP Client for Product Service inter-service communication
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
import httpx
from datetime import datetime
import unicodedata
import re

logger = logging.getLogger(__name__)

# ============================================================================
# Helper Functions
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug
    Removes Vietnamese diacritics: à→a, ư→u, etc.
    """
    # Normalize Vietnamese characters (NFD decomposition)
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Remove combining marks (diacritics)
    ascii_form = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Convert to lowercase
    slug = ascii_form.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


class ProductServiceClient:
    """
    HTTP client for communicating with ProductService.
    Handles retries, timeouts, and error conversion.
    
    ProductService runs on port 8001
    """
    
    def __init__(
        self,
        base_url: str = "http://product-service:8001",
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
                logger.debug(f"ProductServiceClient: {method} {url} (attempt {attempt + 1})")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"ProductServiceClient request failed: {method} {url} - {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        
        logger.error(f"ProductServiceClient: Failed after {self.max_retries} retries: {url}")
        raise last_error or Exception("Request failed")
    
    # ========================================================================
    # Product Query APIs
    # ========================================================================
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search products by keyword and optional filters
        
        Args:
            query: Search keyword
            category: Product category (optional)
            filters: Additional filters (price_min, price_max, brand, etc.)
            limit: Number of results
            offset: Pagination offset
        
        Returns:
            {
                "total": int,
                "limit": int,
                "offset": int,
                "products": [...]
            }
        """
        payload = {
            "query": query,
            "limit": limit,
            "offset": offset
        }
        if category:
            payload["category"] = category
        if filters:
            payload["filters"] = filters
        
        return await self._request_with_retry(
            "POST",
            "/api/products/search",
            json=payload
        )
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product details by ID"""
        return await self._request_with_retry(
            "GET",
            f"/api/products/{product_id}"
        )
    
    async def get_sku(self, sku_id: str) -> Dict[str, Any]:
        """Get SKU details by ID"""
        return await self._request_with_retry(
            "GET",
            f"/api/skus/{sku_id}"
        )
    
    async def get_category(self, category_id: int) -> Dict[str, Any]:
        """Get category details with attributes"""
        return await self._request_with_retry(
            "GET",
            f"/api/categories/{category_id}"
        )
    
    async def list_categories(self) -> List[Dict[str, Any]]:
        """List all product categories"""
        response = await self._request_with_retry(
            "GET",
            "/api/categories"
        )
        return response.get("categories", [])
    
    # ========================================================================
    # Product Save APIs (from crawlers)
    # ========================================================================
    
    async def save_products(
        self,
        products: List[Dict[str, Any]],
        source: str = "crawler"
    ) -> Dict[str, Any]:
        """
        Save/update products from crawler
        
        Args:
            products: List of product data to save
            source: Data source (tiki, lazada, shopee)
        
        Returns:
            {
                "saved": int,
                "updated": int,
                "errors": [...]
            }
        """
        return await self._request_with_retry(
            "POST",
            "/api/products/batch",
            json={
                "products": products,
                "source": source
            }
        )
    
    async def update_product(
        self,
        product_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update single product"""
        return await self._request_with_retry(
            "PUT",
            f"/api/products/{product_id}",
            json=update_data
        )
    
    async def update_sku_price(
        self,
        sku_id: str,
        price: float,
        stock: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update SKU price and optional stock"""
        payload = {"price": price}
        if stock is not None:
            payload["stock"] = stock
        
        return await self._request_with_retry(
            "PUT",
            f"/api/skus/{sku_id}/price",
            json=payload
        )
    
    # ========================================================================
    # Filter/Attribute APIs
    # ========================================================================
    
    async def get_category_attributes(
        self,
        category_id: int
    ) -> Dict[str, Any]:
        """Get filterable attributes for a category"""
        return await self._request_with_retry(
            "GET",
            f"/api/categories/{category_id}/attributes"
        )
    
    async def apply_filters(
        self,
        category_id: int,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply attribute filters to category products"""
        return await self._request_with_retry(
            "POST",
            f"/api/categories/{category_id}/filter",
            json=filters
        )
    
    async def get_filters(self, category_name: str) -> List[Dict[str, Any]]:
        """
        Get available filters for a category by name
        
        Args:
            category_name: Category name (e.g., "Giày", "Đồng hồ")
        
        Returns:
            List of filter objects with options
        """
        try:
            # Convert category name to slug (removes diacritics, lowercase, hyphenated)
            category_slug = slugify(category_name)
            
            # Get filters from ProductService
            response = await self._request_with_retry(
                "GET",
                f"/api/categories/{category_slug}/filters"
            )
            return response.get("filters", [])
        
        except Exception as e:
            logger.error(f"Error fetching filters for category '{category_name}': {e}")
            return []
    
    async def create_category(
        self,
        name: str,
        description: str = "",
        category_type: str = "general",
        attributes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create new product category with attributes
        
        Args:
            name: Category name (e.g., "Giày")
            description: Category description
            category_type: Category type (e.g., "footwear")
            attributes: List of attribute names to create
        
        Returns:
            {
                "success": True,
                "id": 1,
                "name": "Giày",
                "attributes_created": 7
            }
        """
        payload = {
            "name": name,
            "description": description,
            "category_type": category_type
        }
        if attributes:
            payload["attributes"] = attributes
        
        return await self._request_with_retry(
            "POST",
            "/api/categories",
            json=payload
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
            logger.error(f"ProductService health check failed: {e}")
            return False


# Singleton instance for global access
_product_service_client: Optional[ProductServiceClient] = None


async def get_product_service_client() -> ProductServiceClient:
    """Get singleton ProductServiceClient instance"""
    global _product_service_client
    if _product_service_client is None:
        _product_service_client = ProductServiceClient()
    return _product_service_client


async def close_product_service_client():
    """Close the singleton client"""
    global _product_service_client
    if _product_service_client:
        await _product_service_client.close()
        _product_service_client = None

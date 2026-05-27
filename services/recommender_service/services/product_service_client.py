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

#logger = logging.get#logger(__name__)

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


def normalize_crawled_product(product: Dict[str, Any], source: str = None) -> Dict[str, Any]:
    """
    Normalize product data from different sources (Tiki, Lazada, Shopee)
    to a consistent schema for ProcessService.
    
    Args:
        product: Product data from crawler (different formats per source)
        source: Data source (tiki, lazada, shopee)
    
    Returns:
        Normalized product with consistent field names:
        {
            "product_id": str,      # Tiki: product_id, Lazada: extracted from url
            "product_url": str,     # Tiki: product_url, Lazada: url
            "spid": str,            # Tiki: spid, Lazada: null
            "title": str,
            "name": str,
            "price": str,
            "image": str,
            "source": str,
            ...other fields
        }
    """
    normalized = product.copy()
    
    # Auto-detect source if not provided
    if not source:
        source = product.get("source", "unknown")
    
    if source.lower() == "lazada":
        # Lazada: url → product_url
        if "url" in product and "product_url" not in product:
            normalized["product_url"] = product["url"]
        
        # Lazada: extract product_id from URL
        # https://www.lazada.vn/products/pdp-i3086978477.html → 3086978477
        if "url" in product and "product_id" not in product:
            match = re.search(r'pdp-i(\d+)', product["url"])
            if match:
                normalized["product_id"] = match.group(1)
        
        # Lazada: name or title
        if "name" in product and "title" not in product:
            normalized["title"] = product["name"]
        
        # Ensure product_id exists even if extraction failed
        if "product_id" not in normalized or not normalized.get("product_id"):
            # Fallback: use URL as product_id
            normalized["product_id"] = product.get("url", "").split("/")[-1] if product.get("url") else None
    
    elif source.lower() == "tiki":
        # Tiki: ensure product_url exists
        if "url" in product and "product_url" not in product:
            normalized["product_url"] = product["url"]
        
        # Tiki: ensure product_id exists
        if "product_id" not in normalized:
            normalized["product_id"] = product.get("id") or product.get("product_id")
    
    # Shopee: similar to Lazada but different URL format
    elif source.lower() == "shopee":
        if "url" in product and "product_url" not in product:
            normalized["product_url"] = product["url"]
        
        # Shopee: extract product_id from URL
        # https://shopee.vn/.../i... → extract id
        if "url" in product and "product_id" not in product:
            match = re.search(r'/i(\d+)', product["url"])
            if match:
                normalized["product_id"] = match.group(1)
    
    # Ensure essential fields exist
    normalized.setdefault("source", source)
    normalized.setdefault("title", product.get("name") or product.get("title") or "")
    normalized.setdefault("name", product.get("title") or product.get("name") or "")
    
    return normalized


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
                #logger.debug(f"ProductServiceClient: {method} {url} (attempt {attempt + 1})")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                # #logger.warning(
                #     f"ProductServiceClient request failed: {method} {url} - {str(e)}"
                # )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                continue
        
        #logger.error(f"ProductServiceClient: Failed after {self.max_retries} retries: {url}")
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
        source: str = "crawler",
        category_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save/update products from crawler
        
        Args:
            products: List of product data to save
            source: Data source (tiki, lazada, shopee)
            category_id: Category ID for the products (REQUIRED)
        
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
                "source": source,
                "category_id": category_id  # ✅ IMPORTANT: Include category_id
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
    
    async def save_sku_attributes(
        self,
        sku_code: str,
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save/update attributes for a specific SKU
        
        Args:
            sku_code: SKU code/ID (e.g., spid from Tiki)
            attributes: Dictionary of attribute name-value pairs
            Example: {"RAM": "8GB", "CPU": "Intel i5", "Storage": "512GB SSD"}
        
        Returns:
            {
                "status": "saved",
                "sku_code": "...",
                "attributes_count": 3
            }
        """
        return await self._request_with_retry(
            "POST",
            f"/api/skus/{sku_code}/attributes",
            json={"attributes": attributes}
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
    
    async def get_products_by_category_and_attributes(
        self,
        category_id: int,
        attributes: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Query products by category_id + optional attributes/filters
        
        ✅ RECOMMENDED: Use this instead of direct DB queries
        Properly integrates with Product Service via HTTP
        
        Args:
            category_id: Category ID from database
            attributes: Filter attributes (brand, color, size, price_min, price_max, etc.)
            limit: Max results (default 50)
        
        Returns:
            List of matching products with SKU details and attributes:
            [
                {
                    "id": 123,
                    "product_id": "276183351",
                    "spid": "276183355",
                    "title": "Giày thể thao nam...",
                    "brand": "Nike",
                    "price": 620000,
                    "original_price": 1000000,
                    "stock": 10,
                    "rating": 4.5,
                    "search_count": 150,
                    "attributes": [  # ✅ NOW INCLUDED
                        {"name": "color", "value": "đen"},
                        {"name": "size", "value": "42"},
                        {"name": "material", "value": "da"}
                    ]
                }
            ]
        
        Example:
            products = await client.get_products_by_category_and_attributes(
                category_id=5,
                attributes={"brand": "Nike", "color": "đen", "price_max": 5000000},
                limit=50
            )
            # Now you can access product attributes for ranking/filtering:
            for product in products:
                attrs_dict = {attr["name"]: attr["value"] for attr in product.get("attributes", [])}
                print(f"Color: {attrs_dict.get('color')}, Size: {attrs_dict.get('size')}")
        """
        if attributes is None:
            attributes = {}
        
        payload = {
            "category_id": category_id,
            "attributes": attributes,
            "limit": limit
        }
        
        response = await self._request_with_retry(
            "POST",
            "/api/products/query-by-category",
            json=payload
        )
        
        # Extract products list from response
        # Products now include "attributes" field with list of {"name": str, "value": str}
        return response.get("products", [])
    
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
            #logger.error(f"Error fetching filters for category '{category_name}': {e}")
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
    
    async def get_category_details(self, category_id: int) -> Dict[str, Any]:
        """
        Get category details with attributes
        
        Returns:
            {
                "id": 5,
                "name": "Laptop",
                "attributes": [
                    {"id": 1, "attribute_name": "brand", ...},
                    {"id": 2, "attribute_name": "cpu", ...}
                ]
            }
        """
        try:
            response = await self._request_with_retry(
                "GET",
                f"/api/categories/{category_id}/details"
            )
            return response if response else {}
        except Exception as e:
            #logger.error(f"Failed to get category details: {e}")
            return {}
    
    async def add_category_attributes(
        self,
        category_id: int,
        attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Add (append) attributes to existing category
        
        Request:
        {
            "attributes": ["khả năng chống nước", "tính năng mới"]
        }
        
        Response:
        {
            "success": true,
            "category_id": 5,
            "attributes_added": ["khả năng chống nước", "tính năng mới"],
            "attributes_count": 5,
            "schema_version": 3
        }
        """
        try:
            payload = {
                "attributes": attributes
            }
            
            response = await self._request_with_retry(
                "PUT",
                f"/api/categories/{category_id}/attributes",
                json=payload
            )
            
            if response and response.get("success"):
                #logger.info(f"✅ Added {len(attributes)} attributes to category {category_id}")
                return response
            else:
                #logger.warning(f"⚠️ Failed to add attributes: {response}")
                return {"success": False}
        
        except Exception as e:
            #logger.error(f"Error adding category attributes: {e}")
            return {"success": False}
    
    async def sync_product_sku_attributes(
        self,
        category_id: int,
        attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Sync SKU attributes for products in category
        
        Request:
        {
            "attributes": ["khả năng chống nước"],
            "only_missing": true
        }
        
        Response:
        {
            "success": true,
            "category_id": 5,
            "products_synced": 1250,
            "sku_attributes_added": 1250
        }
        """
        try:
            payload = {
                "attributes": attributes,
                "only_missing": True
            }
            
            response = await self._request_with_retry(
                "POST",
                f"/api/categories/{category_id}/sync-sku-attributes",
                json=payload
            )
            
            if response and response.get("success"):
                #logger.info(f"✅ Synced SKU attributes for {response.get('products_synced', 0)} products")
                return response
            else:
                #logger.warning(f"⚠️ Failed to sync SKU attributes: {response}")
                return {"success": False}
        
        except Exception as e:
            #logger.error(f"Error syncing SKU attributes: {e}")
            return {"success": False}

    async def get_or_crawl_products(
        self,
        category_id: int,
        category_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get products from DB, or crawl + detail crawl if not available
        
        IMPORTANT: This method is responsible for ALL crawling logic.
        Orchestrator only needs to call this and rank the results.
        
        Flow:
        1. Query DB first
        2. If miss → Crawl shallow + detail crawl (SYNCHRONIZED, not async)
        3. Save crawled products with full details
        4. Return products with complete attributes for ranking
        
        Args:
            category_id: Category ID from database
            category_name: Category name for crawling
            attributes: Filter attributes (brand, color, size, etc.)
            limit: Max results
        
        Returns:
            List of products with FULL attributes (detailed_attributes populated)
        """
        # 1. Query DB first
        #logger.info(f"[ProductServiceClient.get_or_crawl_products] Querying DB for category_id={category_id}")
        db_products = await self.get_products_by_category_and_attributes(
            category_id=category_id,
            attributes=attributes,
            limit=limit
        )
        
        if db_products and len(db_products) >= 0:
            # DB HIT - sufficient products found
            #logger.info(f"[ProductServiceClient] ✅ DB HIT: Found {len(db_products)} products in database")
            return db_products
        
        # 2. DB MISS - Crawl from external sources
        #logger.info(f"[ProductServiceClient] ❌ DB MISS - Crawling products from external sources...")
        
        try:
            from .crawl_service_client import CrawlServiceClient
            crawl_client = CrawlServiceClient()
            
            # Crawl shallow products
            #logger.info(f"[ProductServiceClient] 🔄 Step 1: Crawling shallow products...")
            crawled_products = await crawl_client.crawl(
                category=category_name,
                category_id=category_id,
                attributes=attributes
            )
            
            if not crawled_products:
                #logger.warning(f"[ProductServiceClient] No products crawled for category '{category_name}'")
                return []
            
            #logger.info(f"[ProductServiceClient] ✅ Crawled {len(crawled_products)} shallow products")
            
            # ⭐ NORMALIZE DATA: Map fields from different sources (Lazada, Tiki, Shopee)
            # Ensures product_id and product_url are present for detail crawl
            #logger.info(f"[ProductServiceClient] 🔄 Normalizing product data from mixed sources...")
            crawled_products = [
                normalize_crawled_product(p, source=p.get("source"))
                for p in crawled_products
            ]
            
            # Log normalized data for debugging
            if crawled_products:
                sample = crawled_products[0]
                #logger.info(f"[ProductServiceClient] Normalized sample: product_id={sample.get('product_id')}, product_url={sample.get('product_url')}, source={sample.get('source')}")
                
                # Count products with valid IDs/URLs for detail crawl
                with_product_id = len([p for p in crawled_products if p.get("product_id")])
                with_product_url = len([p for p in crawled_products if p.get("product_url")])
                #logger.info(f"[ProductServiceClient] After normalization: {with_product_id} with product_id, {with_product_url} with product_url")
            
            # 3. Save shallow products to DB FIRST (before detail crawl)
            #logger.info(f"[ProductServiceClient] 💾 Step 2: Saving {len(crawled_products)} shallow products to database...")
            try:
                # Detect primary source from crawled products
                sources = set([p.get("source") for p in crawled_products if p.get("source")])
                primary_source = list(sources)[0] if sources else "unknown"
                #logger.debug(f"[ProductServiceClient] Detected sources: {sources}, using primary: {primary_source}")
                
                await self.save_products(
                    crawled_products,
                    source=primary_source,
                    category_id=category_id
                )
                #logger.info(f"[ProductServiceClient] ✅ Saved {len(crawled_products)} shallow products to DB")
            except Exception as e:
                pass
                #logger.warning(f"[ProductServiceClient] ⚠️ Failed to save shallow products: {e}")
                # Don't fail - continue with detail crawl anyway
            
            # 4. Crawl product DETAILS (SYNCHRONIZED - wait for completion, not async RabbitMQ)
            #logger.info(f"[ProductServiceClient] 🔄 Step 3: Crawling product details for {len(crawled_products)} products...")
            product_ids = [p.get("product_id") for p in crawled_products if p.get("product_id")]
            product_spids = [p.get("spid") for p in crawled_products if p.get("spid")]
            product_urls = [p.get("product_url") for p in crawled_products if p.get("product_url")]
            #logger.info(f"[ProductServiceClient] DEBUG: product_ids={len(product_ids)}, product_spids={len(product_spids)}, product_urls={len(product_urls)}")
            
            if product_ids or product_urls:
                # Build schema from detected attributes (if available)
                crawl_schema = None
                if attributes:
                    # Convert attributes to schema-like structure
                    crawl_schema = {
                        "category": category_name,
                        "attributes": [
                            {
                                "name": attr_name,
                                "keywords": [attr_name],
                                "value_pattern": None
                            }
                            for attr_name in attributes.keys()
                        ]
                    }
                
                # Detect sources from crawled products
                sources = set()
                for p in crawled_products:
                    if p.get("source"):
                        sources.add(p.get("source"))
                sources_list = list(sources) if sources else None
                
                try:
                    # ⭐ IMPORTANT: Wait for detail crawl to COMPLETE (synchronized)
                    # Support both Tiki (product_ids) and Lazada/Shopee (product_urls with Playwright)
                    #logger.debug(f"[ProductServiceClient] DEBUG: Starting sync crawl with sources={sources_list}...")
                    await crawl_client.crawl_product_details_sync(
                        product_ids=product_ids if product_ids else None,
                        spids=product_spids if product_spids else None,
                        product_urls=product_urls if product_urls else None,
                        sources=sources_list,
                        category_id=category_id,
                        schema=crawl_schema,
                        max_concurrent=5,
                        wait_for_completion=True  # ✅ WAIT for completion
                    )
                    #logger.info(f"[ProductServiceClient] ✅ Detail crawl completed")
                    
                    # ⭐ Query DB again to get products with updated attributes
                    #logger.info(f"[ProductServiceClient] 🔄 Step 4: Re-querying DB to fetch products with new attributes...")
                    crawled_products = await self.get_products_by_category_and_attributes(
                        category_id=category_id,
                        attributes=attributes,
                        limit=limit
                    )
                    #logger.info(f"[ProductServiceClient] ✅ Got {len(crawled_products)} products with detailed attributes from DB")
                except Exception as e:
                    #logger.error(f"[ProductServiceClient] ❌ Detail crawl error: {type(e).__name__}: {str(e)}", exc_info=True)
                    #logger.warning(f"[ProductServiceClient] ⚠️ Detail crawl failed, returning shallow products from DB")
                    # Continue with shallow products if detail crawl fails
                    crawled_products = await self.get_products_by_category_and_attributes(
                        category_id=category_id,
                        attributes=attributes,
                        limit=limit
                    )
            else:
                pass
                #logger.warning(f"[ProductServiceClient] ⚠️ No product_ids or product_urls found to crawl details. Using shallow products only.")
            
            # 5. Return products with full attributes ready for ranking
            #logger.info(f"[ProductServiceClient] ✅ Returning {len(crawled_products)} products with full attributes")
            return crawled_products
        
        except Exception as e:
            #logger.error(f"[ProductServiceClient] ❌ Error in get_or_crawl_products: {e}", exc_info=True)
            # Fallback: return DB results if crawling fails
            return db_products if db_products else []

    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            response = await self._request_with_retry(
                "GET",
                "/api/health"
            )
            return response.get("status") == "healthy"
        except Exception as e:
            #logger.error(f"ProductService health check failed: {e}")
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

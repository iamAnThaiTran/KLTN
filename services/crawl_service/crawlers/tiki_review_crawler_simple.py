"""
Tiki Review Crawler Simple (httpx version)
Crawls product details + reviews from Tiki without Playwright
Uses httpx for better performance and compatibility

Ported from: BackendPython/app/crawler/tiki_review_crawler_simple.py
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TikiReviewCrawlerSimple:
    """Simple Tiki crawler using httpx (no browser automation)"""
    
    def __init__(self):
        self.base_url = "https://tiki.vn/api/v2"
        self.timeout = 30
        self.session = None
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create httpx session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.aclose()
            self.session = None
    
    async def get_product_snapshot(
        self,
        product_id: str,
        spid: str = "",
        seller_id: str = "1",
        label: str = "",
    ) -> Dict[str, Any]:
        """
        Fetch complete product snapshot (details + reviews)
        
        Args:
            product_id: Tiki product ID
            spid: Seller product ID (optional)
            seller_id: Seller ID
            label: Label for logging
        
        Returns:
            Product snapshot dict
        """
        try:
            logger.info(f"📥 Fetching product: {label or product_id}")
            
            session = await self._get_session()
            
            # Fetch product details
            detail = await self._fetch_product_detail(session, product_id, spid)
            snapshot = self._parse_product_detail(detail or {})
            snapshot["product_id"] = product_id
            snapshot["spid"] = spid
            snapshot["seller_id"] = seller_id
            
            # Fetch reviews
            reviews, rating_bd = await self._crawl_reviews(session, product_id, spid, seller_id)
            snapshot["reviews"] = reviews
            snapshot["rating_breakdown"] = rating_bd
            
            logger.info(
                f"✅ Snapshot: {snapshot.get('name', 'Unknown')[:50]} | "
                f"⭐ {snapshot.get('rating_avg', 0)} | "
                f"💬 {len(reviews)} reviews"
            )
            
            return snapshot
        
        except Exception as e:
            logger.error(f"❌ Error fetching snapshot: {e}")
            raise
    
    async def _fetch_product_detail(
        self,
        session: httpx.AsyncClient,
        product_id: str,
        spid: str
    ) -> Dict:
        """Fetch product details from Tiki API"""
        try:
            # Endpoint: /products/{product_id}
            url = f"{self.base_url}/products/{product_id}"
            
            response = await session.get(url, params={"include": "attributes,rating_summary,seller"})
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch product details: {e}")
            return {}
    
    def _parse_product_detail(self, detail: Dict) -> Dict:
        """Parse product detail API response"""
        return {
            "name": detail.get("name", ""),
            "brand": detail.get("brand", {}).get("name", ""),
            "price": detail.get("price", 0),
            "original_price": detail.get("original_price", 0),
            "rating_avg": detail.get("rating_average", 0),
            "rating_count": detail.get("review_count", 0),
            "thumbnail": detail.get("thumbnail_url", ""),
            "url": detail.get("url", ""),
            "description": detail.get("description", ""),
            "category": detail.get("category", {}).get("name", ""),
            "specs": self._extract_specs(detail.get("specifications", [])),
        }
    
    def _extract_specs(self, specs: List[Dict]) -> List[Dict]:
        """Extract specifications from detail"""
        result = []
        for group in specs:
            result.append({
                "group": group.get("name", ""),
                "attrs": [
                    {
                        "name": attr.get("name", ""),
                        "value": attr.get("value", "")
                    }
                    for attr in group.get("attributes", [])
                ]
            })
        return result
    
    async def _crawl_reviews(
        self,
        session: httpx.AsyncClient,
        product_id: str,
        spid: str,
        seller_id: str
    ) -> tuple[List[Dict], Dict]:
        """Fetch reviews from Tiki"""
        try:
            url = f"{self.base_url}/reviews"
            params = {
                "product_id": product_id,
                "limit": 50,
                "offset": 0,
                "sort": "helpful"
            }
            
            response = await session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            reviews = []
            for review in data.get("data", [])[:20]:  # Limit to 20 reviews
                reviews.append({
                    "rating": review.get("rating", 0),
                    "title": review.get("title", ""),
                    "content": review.get("content", ""),
                    "is_purchased": review.get("purchased", False),
                    "used_duration": review.get("days_used", ""),
                    "helpful_count": review.get("helpful_count", 0),
                })
            
            # Build rating breakdown
            rating_bd = await self._get_rating_breakdown(session, product_id)
            
            logger.info(f"✅ Fetched {len(reviews)} reviews")
            return reviews, rating_bd
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch reviews: {e}")
            return [], {}
    
    async def _get_rating_breakdown(
        self,
        session: httpx.AsyncClient,
        product_id: str
    ) -> Dict:
        """Get rating breakdown"""
        try:
            url = f"{self.base_url}/products/{product_id}/rating-summary"
            response = await session.get(url)
            response.raise_for_status()
            data = response.json()
            
            breakdown = {}
            for star in ["1", "2", "3", "4", "5"]:
                star_data = data.get(star, {})
                breakdown[star] = {
                    "count": star_data.get("total", 0),
                    "percent": star_data.get("percent", 0)
                }
            
            return breakdown
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to get rating breakdown: {e}")
            return {str(i): {"count": 0, "percent": 0} for i in range(1, 6)}
    
    async def compare_products(
        self,
        product_a: Dict,
        product_b: Dict,
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        Compare 2 products (not used in microservice version)
        Kept for backward compatibility
        """
        logger.warning("compare_products() not implemented in microservice version")
        return {
            "status": "error",
            "error": "compare_products() not implemented - use recommender service endpoint"
        }

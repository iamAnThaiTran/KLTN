"""
Multi-Source Crawler for CrawlService (ported from monolith)
Aggregates results from multiple sources (Tiki, Lazada, etc.)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import unicodedata

from .tiki_crawler import TikiCrawler

logger = logging.getLogger(__name__)


class MultiCrawler:
    """Multi-source Crawler - aggregates results from Tiki and other sources"""
    
    def __init__(self):
        self.tiki_crawler = TikiCrawler()
    
    async def crawl(
        self,
        category: str,
        attributes: Optional[Dict[str, Any]] = None,
        sources: Optional[List[str]] = None,
        max_products_per_source: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Crawl from multiple sources and aggregate results
        
        Args:
            category: Product category (e.g., "smartphone", "giày")
            attributes: Product attributes (brand, price range, etc.)
            sources: List of sources to crawl (default: ["tiki"])
            max_products_per_source: Max products per source
        
        Returns:
            List of combined and deduplicated products
        """
        attributes = attributes or {}
        sources = sources or ["tiki"]
        
        logger.info(f"🔍 MultiCrawler: category='{category}', sources={sources}")
        logger.info(f"📋 Attributes: {attributes}")
        
        all_products = []
        
        # Build search query
        search_query = self._build_search_query(category, attributes)
        logger.info(f"🔎 Search query: {search_query}")
        
        # Crawl from each source
        tasks = []
        
        if "tiki" in sources:
            tasks.append(self._crawl_tiki(search_query, max_products_per_source))
        
        # Run crawls in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_products.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Crawler error: {result}")
        
        # Deduplicate
        deduped = self._deduplicate_products(all_products)
        
        logger.info(f"📊 Total found: {len(all_products)}, after dedup: {len(deduped)}")
        
        return deduped
    
    async def _crawl_tiki(self, query: str, max_products: int) -> List[Dict[str, Any]]:
        """Crawl from Tiki"""
        try:
            crawler = TikiCrawler()
            products = await crawler.crawl(query, max_products)
            logger.info(f"✅ Tiki: {len(products)} products")
            return products
        except Exception as e:
            logger.error(f"❌ Tiki error: {e}")
            return []
    
    def _build_search_query(self, category: str, attributes: Dict) -> str:
        """Build search query from category and attributes"""
        query_parts = [category]
        
        if "brand" in attributes and attributes["brand"]:
            query_parts.append(str(attributes["brand"]))
        
        if "dong" in attributes and attributes["dong"]:
            query_parts.append(str(attributes["dong"]))
        
        if "loai" in attributes and attributes["loai"]:
            query_parts.append(str(attributes["loai"]))
        
        if "price_range" in attributes and attributes["price_range"]:
            query_parts.append(str(attributes["price_range"]))
        
        return " ".join(query_parts)
    
    def _deduplicate_products(self, products: List[Dict]) -> List[Dict]:
        """Deduplicate products based on title/name"""
        if not products:
            return []
        
        seen = {}
        deduped = []
        
        for product in products:
            # Use normalized name as key
            name = product.get("title") or product.get("name", "")
            key = self._normalize_name(name)
            
            if key not in seen:
                seen[key] = True
                deduped.append(product)
        
        return deduped
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        # Normalize unicode
        name = unicodedata.normalize("NFD", name.lower())
        name = "".join(c for c in name if unicodedata.category(c) != "Mn")
        
        # Keep only alphanumeric and spaces
        name = "".join(c for c in name if c.isalnum() or c.isspace())
        
        # Collapse whitespace
        return " ".join(name.split())

import asyncio
import json
from typing import Dict, List, Optional, Any
import logging
from .crawler import TikiCrawler
from .lazada_crawler import crawl_lazada_full

logger = logging.getLogger(__name__)


class MultiCrawler:
    """Multi-source Crawler - gộp kết quả từ Tiki và Lazada"""

    def __init__(self):
        self.tiki_crawler = TikiCrawler()

    async def crawl(
        self,
        category: str,
        attributes: Optional[Dict[str, Any]] = None,
        get_details: bool = True,
        sources: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Crawl từ nhiều nguồn và gộp kết quả"""
        attributes = attributes or {}
        sources = sources or ["tiki", "lazada"]

        logger.info("=" * 70)
        logger.info(f"🔍 Multi-Crawler: Crawling '{category}'")
        logger.info(f"📋 Attributes: {json.dumps(attributes, ensure_ascii=False)}")
        logger.info(f"📦 Sources: {', '.join(sources)}")
        logger.info("=" * 70)

        all_products = []

        # Crawl từ Tiki
        if "tiki" in sources:
            try:
                logger.info("🟦 Crawling Tiki...")
                tiki_products = await self.tiki_crawler.crawl(
                    category=category,
                    attributes=attributes,
                    get_details=get_details
                )
                logger.info(f"✅ Tiki: Found {len(tiki_products)} products")
                all_products.extend(tiki_products)
            except Exception as e:
                logger.error(f"❌ Tiki crawl error: {str(e)}")

        # Crawl từ Lazada - TEMPORARILY DISABLED
        # if "lazada" in sources:
        #     try:
        #         logger.info("🟥 Crawling Lazada...")
        #         search_query = self._build_search_query(category, attributes)
        #         lazada_products = await crawl_lazada_full(search_query)
        #         lazada_products = [self._normalize_lazada_product(p) for p in lazada_products]
        #         logger.info(f"✅ Lazada: Found {len(lazada_products)} products")
        #         all_products.extend(lazada_products)
        #     except Exception as e:
        #         logger.warning(f"⚠️ Lazada crawl skipped: {type(e).__name__}")

        logger.info(f"📊 Total products: {len(all_products)}")
        merged_products = self._deduplicate_products(all_products)
        logger.info(f"📊 After dedup: {len(merged_products)} products")

        return merged_products

    def _build_search_query(self, category: str, attributes: Dict) -> str:
        """Build search query từ category và attributes"""
        query_parts = [category]
        if "brand" in attributes and attributes["brand"]:
            query_parts.append(str(attributes["brand"]))
        if "dong" in attributes and attributes["dong"]:
            query_parts.append(str(attributes["dong"]))
        if "loai" in attributes and attributes["loai"]:
            query_parts.append(str(attributes["loai"]))
        return " ".join(query_parts)

    def _normalize_lazada_product(self, product: Dict) -> Dict:
        """Normalize Lazada product để match với Tiki format"""
        normalized = {
            "id": product.get("id"),
            "name": product.get("title", ""),
            "title": product.get("title", ""),
            "price": self._parse_price(product.get("price", 0)),
            "image": product.get("image"),
            "link": product.get("link"),
            "source": "lazada"
        }
        if "attributes" in product:
            attrs = product["attributes"]
            if "brand" in attrs:
                normalized["brand"] = attrs["brand"].lower()
        return normalized

    def _parse_price(self, price) -> int:
        """Convert price to int"""
        try:
            if isinstance(price, (int, float)):
                return int(price)
            if isinstance(price, str):
                import re
                numbers = re.findall(r'\d+', price.replace(',', '').replace('.', ''))
                if numbers:
                    return int(numbers[0])
        except:
            pass
        return 0

    def _deduplicate_products(self, products: List[Dict]) -> List[Dict]:
        """Deduplicate products dựa trên tên"""
        if not products:
            return []
        seen = {}
        deduped = []
        for product in products:
            # Use 'title' (from Tiki) or 'name' (from other sources)
            product_name = product.get("title") or product.get("name", "")
            key = self._normalize_name(product_name)
            if key not in seen:
                seen[key] = True
                deduped.append(product)
        return deduped

    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison"""
        import unicodedata
        name = unicodedata.normalize("NFD", name.lower())
        name = "".join(c for c in name if unicodedata.category(c) != "Mn")
        name = "".join(c for c in name if c.isalnum() or c.isspace())
        return " ".join(name.split())

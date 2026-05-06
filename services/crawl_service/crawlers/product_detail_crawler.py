"""
ProductDetailCrawler - Service for crawling and extracting detailed product information
Uses httpx for high-performance async requests (no browser automation)
Extracts product attributes based on dynamic schemas

Fixed: Removed hallucinated endpoints. Tiki only exposes:
  GET /api/v2/products/{product_id}  →  name, brand, price, specs, description, ...
All attribute mapping is done from that single response.
"""

import asyncio
import httpx
import json
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ProductDetailCrawler:
    """Crawl and extract detailed product information from Tiki"""

    def __init__(self, timeout: float = 30.0):
        self.base_url_tiki = "https://tiki.vn/api/v2"
        self.timeout = timeout
        self.session = None

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def _get_session(self) -> httpx.AsyncClient:
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    )
                },
            )
        return self.session

    async def close(self):
        if self.session:
            await self.session.aclose()
            self.session = None

    # ------------------------------------------------------------------
    # Core fetch — chỉ 1 endpoint thực sự tồn tại
    # ------------------------------------------------------------------

    async def _fetch_product_detail(
        self,
        session: httpx.AsyncClient,
        product_id: str,
    ) -> Dict:
        """GET /api/v2/products/{product_id}"""
        try:
            url = f"{self.base_url_tiki}/products/{product_id}"
            response = await session.get(
                url,
                params={"include": "attributes,rating_summary,seller"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch product {product_id}: {e}")
            return {}

    def _parse_product_detail(self, detail: Dict) -> Dict:
        """Parse product detail — tất cả thông tin cần thiết đều nằm ở đây"""
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
        result = []
        for group in specs:
            result.append({
                "group": group.get("name", ""),
                "attrs": [
                    {
                        "name": attr.get("name", ""),
                        "value": attr.get("value", ""),
                    }
                    for attr in group.get("attributes", [])
                ],
            })
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def crawl_tiki_product_details(
        self,
        product_id: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl một sản phẩm Tiki và extract attributes theo schema.

        Args:
            product_id: Tiki product ID
            schema: Dynamic schema for attribute extraction (optional)

        Returns:
            {
                "status": "success" | "error",
                "product": {...},               # parsed product info
                "extracted_attributes": {...},  # mapped từ schema
            }
        """
        try:
            logger.info(f"📥 Crawling Tiki product: {product_id}")

            session = await self._get_session()

            raw = await self._fetch_product_detail(session, product_id)
            if not raw:
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": "Failed to fetch product details",
                }

            product = self._parse_product_detail(raw)
            product["product_id"] = product_id

            logger.info(f"✅ Fetched: {product.get('name', 'Unknown')[:60]}")

            extracted_attributes = {}
            if schema:
                extracted_attributes = self.extract_attributes_from_schema(product, schema)
                logger.info(f"📊 Extracted attributes: {list(extracted_attributes.keys())}")

            return {
                "status": "success",
                "product": product,
                "extracted_attributes": extracted_attributes,
            }

        except Exception as e:
            logger.error(f"❌ Error crawling product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "error": str(e),
            }

    async def crawl_multiple_products(
        self,
        product_ids: List[str],
        schema: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """Crawl nhiều sản phẩm đồng thời"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl(product_id: str):
            async with semaphore:
                return await self.crawl_tiki_product_details(
                    product_id=product_id,
                    schema=schema,
                )

        logger.info(
            f"📥 Crawling {len(product_ids)} products "
            f"(max_concurrent={max_concurrent})"
        )
        results = await asyncio.gather(
            *[_crawl(pid) for pid in product_ids],
            return_exceptions=False,
        )
        logger.info(f"✅ Done: {len(results)} products crawled")
        return list(results)

    # ------------------------------------------------------------------
    # Schema-based attribute extraction
    # ------------------------------------------------------------------

    def extract_attributes_from_schema(
        self,
        product: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract product attributes using dynamic schema.

        Schema format:
            {
                "category": "laptop",
                "attributes": [
                    {
                        "name": "ram",
                        "keywords": ["ram", "bộ nhớ", "ddr"],
                        "value_pattern": r"(\\d+)\\s*(?:gb|ddr)"
                    },
                    ...
                ]
            }

        Returns:
            {
                "ram": {"raw_value": "8", "keywords_found": ["ram", ...]},
                ...
            }
        """
        import re  # guard — đảm bảo available kể cả khi gọi standalone

        extracted = {}

        description = (product.get("description") or "").lower()
        specs_text = self._specs_to_text(product.get("specs", [])).lower()
        all_text = f"{description} {specs_text}"

        for attr_spec in schema.get("attributes", []):
            attr_name = attr_spec.get("name", "").lower()
            keywords = [k.lower() for k in attr_spec.get("keywords", [])]
            value_pattern = attr_spec.get("value_pattern", "")

            if not attr_name or not keywords:
                logger.warning(f"⚠️ Invalid attribute spec (missing name/keywords): {attr_spec}")
                continue

            found_value = self._extract_attribute_by_keywords(
                all_text, keywords, value_pattern
            )

            extracted[attr_name] = {
                "raw_value": found_value,
                "keywords_found": keywords if found_value else [],
            }

        return extracted

    def _extract_attribute_by_keywords(
        self,
        text: str,
        keywords: List[str],
        value_pattern: str,
    ) -> Optional[str]:
        """
        Tìm keyword trong text, rồi apply regex pattern trong vùng lân cận (±100 ký tự).
        Nếu không tìm thấy keyword, fallback search toàn bộ text.
        """
        import re

        if not value_pattern:
            return None

        try:
            pattern = re.compile(value_pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"❌ Invalid regex pattern '{value_pattern}': {e}")
            return None

        for keyword in keywords:
            kw_pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)

            for kw_match in kw_pattern.finditer(text):
                start = max(0, kw_match.start() - 100)
                end = min(len(text), kw_match.end() + 100)
                context = text[start:end]

                val_match = pattern.search(context)
                if val_match:
                    try:
                        return val_match.group(1).strip()
                    except (IndexError, AttributeError):
                        return val_match.group(0).strip()

        # Fallback: search toàn bộ text nếu không gặp keyword nào
        val_match = pattern.search(text)
        if val_match:
            try:
                return val_match.group(1).strip()
            except (IndexError, AttributeError):
                return val_match.group(0).strip()

        return None

    def _specs_to_text(self, specs: List[Dict]) -> str:
        """Flatten specs list thành plain text để search"""
        parts = []
        for group in specs:
            parts.append(group.get("group", ""))
            for attr in group.get("attrs", []):
                parts.append(f"{attr.get('name', '')} {attr.get('value', '')}")
        return " ".join(parts)
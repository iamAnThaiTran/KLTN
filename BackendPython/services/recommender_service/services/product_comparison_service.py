"""
Product Comparison Service
Service to manage product comparison logic using TikiReviewCrawler (httpx) and LLM

Note: Uses TikiReviewCrawlerSimple (httpx version) instead of Playwright for:
- Better compatibility with Python 3.14
- Faster execution (3-5s vs 30-60s)
- Lower resource usage
- Simpler code
"""

import logging
from typing import Dict
from app.crawler.tiki_review_crawler_simple import TikiReviewCrawlerSimple as TikiReviewCrawler

logger = logging.getLogger(__name__)


class ProductComparisonService:
    """
    Service để quản lý logic so sánh sản phẩm.
    - Crawl product details + reviews từ Tiki
    - Build comparison payload
    - Call LLM để có phân tích chi tiết
    """

    def __init__(self):
        self.crawler = TikiReviewCrawler()

    async def compare_tiki_products(
        self,
        product_a: Dict[str, str],
        product_b: Dict[str, str],
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        So sánh 2 sản phẩm từ Tiki với LLM (OpenAI).

        Args:
            product_a: {"product_id": "16268021", "spid": "16268022", "seller_id": "1"}
            product_b: {"product_id": "11111111", "spid": "22222222", "seller_id": "1"}
            llm_model: LLM model to use (default: gpt-4o-mini)

        Returns:
            {
                "status": "success" | "error",
                "snapshot_a": {...},           # Full product A snapshot
                "snapshot_b": {...},           # Full product B snapshot
                "prompt": "...",               # Formatted comparison prompt (for debugging)
                "comparison": "...",           # LLM response in Markdown
                "error": "..." (if status == "error")
            }
        """
        try:
            logger.info(
                f"🔍 Starting comparison: {product_a['product_id']} vs {product_b['product_id']}"
            )

            # Crawl both products with reviews (LLM is called inside crawler with OpenAI)
            result = await self.crawler.compare_products(
                product_a=product_a,
                product_b=product_b,
                llm_model=llm_model,
            )

            return {
                "status": "success",
                "snapshot_a": result["snapshot_a"],
                "snapshot_b": result["snapshot_b"],
                "prompt": result["prompt"],
                "comparison": result["comparison"],
            }

        except Exception as e:
            logger.error(f"❌ Comparison error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "snapshot_a": None,
                "snapshot_b": None,
                "prompt": None,
                "comparison": None,
            }

    async def get_single_product_analysis(
        self,
        product_id: str,
        spid: str,
        seller_id: str = "1",
        label: str = "",
    ) -> Dict:
        """
        Lấy phân tích chi tiết của 1 sản phẩm (details + reviews).
        Hữu ích để hiển thị riêng lẻ hoặc cache.

        Args:
            product_id: Tiki product ID
            spid: Tiki seller product ID (SKU)
            seller_id: Seller ID (default: 1 = Tiki official)
            label: Optional label for logging

        Returns:
            {
                "status": "success" | "error",
                "snapshot": {...},      # Full product snapshot
                "error": "..." (if status == "error")
            }
        """
        try:
            logger.info(f"📦 Fetching product snapshot: {product_id}")

            snapshot = await self.crawler.get_product_snapshot(
                product_id=product_id,
                spid=spid,
                seller_id=seller_id,
                label=label,
            )

            return {
                "status": "success",
                "snapshot": snapshot,
            }

        except Exception as e:
            logger.error(f"❌ Product analysis error: {e}")
            return {
                "status": "error",
                "snapshot": None,
                "error": str(e),
            }

    def validate_product_ids(
        self, product_a: Dict[str, str], product_b: Dict[str, str]
    ) -> tuple[bool, str]:
        """
        Validate product IDs before comparison.

        Returns:
            (is_valid, error_message)
        """
        required_fields = ["product_id", "spid", "seller_id"]

        for product_dict, label in [(product_a, "Product A"), (product_b, "Product B")]:
            for field in required_fields:
                if field not in product_dict or not product_dict[field]:
                    return False, f"{label} missing required field: {field}"

        # Check nếu 2 sản phẩm là giống nhau
        if (
            product_a["product_id"] == product_b["product_id"]
            and product_a["spid"] == product_b["spid"]
        ):
            return False, "Cannot compare same product with itself"

        return True, ""

    def format_product_info_for_display(self, snapshot: Dict) -> Dict:
        """
        Format product snapshot cho display/API response.
        Strip ra những field chỉ dùng internally.

        Args:
            snapshot: Full product snapshot from crawler

        Returns:
            Formatted product info suitable for API response
        """
        return {
            "product_id": snapshot.get("product_id"),
            "name": snapshot.get("name"),
            "brand": snapshot.get("brand"),
            "category": snapshot.get("category"),
            "price": snapshot.get("price"),
            "original_price": snapshot.get("original_price"),
            "discount_pct": snapshot.get("discount_pct"),
            "url": snapshot.get("url"),
            "thumbnail": snapshot.get("thumbnail"),
            "rating_avg": snapshot.get("rating_avg"),
            "rating_count": snapshot.get("rating_count"),
            "rating_breakdown": snapshot.get("rating_breakdown"),
            "sizes": snapshot.get("sizes", [])[:10],  # Limit to 10
            "colors": snapshot.get("colors", [])[:10],  # Limit to 10
            "specifications": snapshot.get("specifications", [])[:5],  # Limit to 5 groups
            "review_count": len(snapshot.get("reviews", [])),
            "review_summary": self._summarize_reviews(snapshot.get("reviews", [])),
        }

    def _summarize_reviews(self, reviews: list) -> Dict:
        """
        Create a quick summary of reviews without including full text.

        Args:
            reviews: List of review dicts

        Returns:
            {
                "total": int,
                "avg_rating": float,
                "purchased_count": int,
                "verified_count": int,
            }
        """
        if not reviews:
            return {"total": 0, "avg_rating": 0, "purchased_count": 0, "verified_count": 0}

        total = len(reviews)
        avg_rating = sum(r.get("rating", 0) for r in reviews) / total if total > 0 else 0
        purchased = sum(1 for r in reviews if r.get("is_purchased")) 
        verified = sum(1 for r in reviews if r.get("is_purchased"))

        return {
            "total": total,
            "avg_rating": round(avg_rating, 2),
            "purchased_count": purchased,
            "verified_count": verified,
        }

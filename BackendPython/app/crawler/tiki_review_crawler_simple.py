"""
TikiReviewCrawler - Simplified Version (without Playwright)
Chỉ dùng httpx để gọi API trực tiếp - nhanh hơn và đơn giản hơn

Sự khác biệt:
- Crawler gốc: Dùng Playwright → Chậm hơn, nhưng an toàn hơn với anti-bot
- Phiên bản này: Dùng httpx → Nhanh hơn, nhưng có thể bị chặn nếu Tiki có anti-bot
"""

import asyncio
import json
import re
import sys
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode
import httpx
import logging

from app.core.llm_utils import call_openai

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

REVIEWS_API = "https://tiki.vn/api/v2/reviews"
PRODUCTS_API = "https://tiki.vn/api/v2/products/{product_id}"
MAX_REVIEW_PAGES = 5
REVIEWS_PER_PAGE = 5
REVIEW_SORT = "score|desc,id|desc,stars|all"
REVIEW_INCLUDE = "comments,contribute_info,attribute_vote_summary"

# Headers để giả lập request từ trình duyệt
BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def empty_product_snapshot() -> Dict:
    """Schema của 1 snapshot sản phẩm."""
    return {
        "product_id": "",
        "spid": "",
        "seller_id": "",
        "name": "",
        "brand": "",
        "category": "",
        "price": 0,
        "original_price": 0,
        "discount_pct": 0,
        "url": "",
        "thumbnail": "",
        "rating_avg": 0.0,
        "rating_count": 0,
        "rating_breakdown": {},
        "specifications": [],
        "sizes": [],
        "colors": [],
        "reviews": [],
        "crawl_ok": False,
        "error": "",
    }

# Chuẩn hoá 1 review object từ API response thành định dạng mình dùng trong snapshot. Giúp tách biệt phần parsing và phần logic xử lý sau này.
def _parse_review(raw: Dict) -> Dict:
    """Chuẩn hoá 1 review object."""
    created_by = raw.get("created_by", {})
    contribute = created_by.get("contribute_info", {}).get("summary", {})
    return {
        "id": raw.get("id"),
        "rating": raw.get("rating"),
        "title": raw.get("title", ""),
        "content": raw.get("content", ""),
        "author": created_by.get("full_name", ""),
        "is_purchased": created_by.get("purchased", False),
        "used_duration": raw.get("timeline", {}).get("content", ""),
        "total_reviews_by_author": contribute.get("total_review", 0),
        "thank_count": raw.get("thank_count", 0),
        "has_image": raw.get("is_photo", False),
        "created_at": raw.get("created_at"),
        "seller_reply": (
            raw.get("comments", [{}])[0].get("content", "")
            if raw.get("comments")
            else ""
        ),
        "attributes": raw.get("attributes", []),
    }


# ──────────────────────────────────────────────────────────────────────────────
# SIMPLIFIED CRAWLER - Không Dùng Playwright
# ──────────────────────────────────────────────────────────────────────────────

class TikiReviewCrawlerSimple:
    """
    Phiên bản đơn giản - dùng httpx để gọi API trực tiếp.
    
    Ưu điểm:
    ✅ Nhanh hơn (không cần khởi động browser)
    ✅ Dùng ít tài nguyên hơn
    ✅ Code đơn giản hơn
    
    Nhược điểm:
    ❌ Có thể bị chặn bởi anti-bot của Tiki
    ❌ Cần xử lý rate limiting
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout  # Timeout mỗi request (seconds)
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lấy hoặc tạo HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=self.timeout)
        return self.client

    async def close(self):
        """Đóng HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def _fetch_json(self, url: str) -> Optional[Dict]:
        """
        Fetch JSON từ URL.
        
        Đơn giản hơn Playwright - chỉ là HTTP request thường
        """
        try:
            client = await self._get_client()
            logger.info(f"  📡 Fetching: {url[:80]}...")
            
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(
                    f"  ⚠️  HTTP {response.status_code}: {url[:80]}"
                )
                # Nếu status 429, có thể bị rate limit
                if response.status_code == 429:
                    logger.warning("  ⏱️  Rate limited! Vui lòng chờ...")
                return None
            
            return response.json()
            
        except httpx.TimeoutException:
            logger.warning(f"  ⏱️  Timeout: {url[:80]}")
            return None
        except httpx.RequestError as e:
            logger.warning(f"  ❌ Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"  ❌ JSON decode error: {e}")
            return None

    # ── Các method giống hệt phiên bản gốc ──

    async def _fetch_product_detail(
        self, product_id: str, spid: str
    ) -> Optional[Dict]:
        """Fetch product detail."""
        params = {"platform": "web", "version": "3"}
        if spid:
            params["spid"] = spid
        url = PRODUCTS_API.format(product_id=product_id) + "?" + urlencode(params)
        logger.info(f"  🔍 Product detail: {url}")
        return await self._fetch_json(url)

    def _parse_product_detail(self, data: Dict) -> Dict:
        """Parse product detail response."""

        def norm(s: str) -> str:
            import unicodedata

            s = unicodedata.normalize("NFD", s)
            return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()

        snapshot = empty_product_snapshot()
        if not data:
            snapshot["error"] = "Empty API response"
            return snapshot

        snapshot["product_id"] = str(data.get("id", ""))
        snapshot["name"] = data.get("name", "")
        snapshot["brand"] = data.get("brand", {}).get("name", "")
        snapshot["category"] = data.get("categories", {}).get("name", "")
        snapshot["price"] = data.get("price", 0)
        snapshot["original_price"] = data.get("original_price", 0)
        snapshot["discount_pct"] = data.get("discount_rate", 0)
        snapshot["url"] = data.get("short_url", "")
        snapshot["thumbnail"] = data.get("thumbnail_url", "")

        rating = data.get("rating_average", 0)
        snapshot["rating_avg"] = round(float(rating), 2)
        snapshot["rating_count"] = data.get("review_count", 0)

        for opt in data.get("configurable_options", []):
            label = norm(opt.get("name", ""))
            values = [v.get("label") for v in opt.get("values", []) if v.get("label")]
            if re.search(r"size|kich co|kich thuoc", label):
                snapshot["sizes"] = values
            elif re.search(r"mau|color|colour", label):
                snapshot["colors"] = values

        for group in data.get("specifications", []):
            grp_name = group.get("name", "")
            attrs = []
            for attr in group.get("attributes", []):
                raw_val = str(attr.get("value", "")).strip()
                clean_val = re.sub(r"<[^>]+>", " ", raw_val).strip()
                clean_val = re.sub(r"\s+", " ", clean_val)
                attrs.append({"name": attr.get("name", ""), "value": clean_val})
            if attrs:
                snapshot["specifications"].append({"group": grp_name, "attrs": attrs})

        snapshot["crawl_ok"] = True
        return snapshot

    async def _crawl_reviews(
        self,
        product_id: str,
        spid: str,
        seller_id: str,
        max_pages: int = MAX_REVIEW_PAGES,
    ) -> Tuple[List[Dict], Dict]:
        """Crawl reviews từ multiple pages."""
        all_reviews: List[Dict] = []
        rating_breakdown: Dict = {}

        for page_num in range(1, max_pages + 1):
            params = {
                "limit": REVIEWS_PER_PAGE,
                "include": REVIEW_INCLUDE,
                "sort": REVIEW_SORT,
                "page": page_num,
                "spid": spid,
                "product_id": product_id,
                "seller_id": seller_id,
            }
            url = REVIEWS_API + "?" + urlencode(params)
            logger.info(f"    📝 Reviews page {page_num}")

            data = await self._fetch_json(url)
            if not data:
                break

            if page_num == 1 and "stars" in data:
                rating_breakdown = data["stars"]

            reviews_raw = data.get("data", [])
            if not reviews_raw:
                break

            for r in reviews_raw:
                all_reviews.append(_parse_review(r))

            paging = data.get("paging", {})
            last_page = paging.get("last_page", 1)
            current_pg = paging.get("current_page", page_num)
            if current_pg >= last_page:
                break

        logger.info(f"    ✅ Total reviews: {len(all_reviews)}")
        return all_reviews, rating_breakdown

    async def _build_product_snapshot(
        self,
        product_id: str,
        spid: str,
        seller_id: str,
        label: str = "",
    ) -> Dict:
        """Build complete product snapshot."""
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Building snapshot for: {label or product_id}")

        raw_detail = await self._fetch_product_detail(product_id, spid)
        snapshot = self._parse_product_detail(raw_detail or {})
        snapshot["product_id"] = product_id
        snapshot["spid"] = spid
        snapshot["seller_id"] = seller_id

        reviews, rating_bd = await self._crawl_reviews(
            product_id, spid, seller_id
        )
        snapshot["reviews"] = reviews
        snapshot["rating_breakdown"] = rating_bd

        if not snapshot["rating_count"] and rating_bd:
            total = sum(v.get("count", 0) for v in rating_bd.values())
            snapshot["rating_count"] = total

        logger.info(
            f"  ✅ Done: {snapshot['name'][:50] if snapshot['name'] else 'Unknown'} | "
            f"⭐ {snapshot['rating_avg']} | 💬 {len(reviews)} reviews"
        )
        return snapshot

    def _build_comparison_payload(
        self,
        snapshot_a: Dict,
        snapshot_b: Dict,
    ) -> str:
        """Build LLM comparison prompt."""

        def _fmt_rating(s: Dict) -> str:
            lines = []
            for star in ["5", "4", "3", "2", "1"]:
                info = s.get(star, {})
                lines.append(
                    f"  {'⭐' * int(star)}: {info.get('count', 0)} lượt ({info.get('percent', 0)}%)"
                )
            return "\n".join(lines)

        def _fmt_specs(specs: List[Dict]) -> str:
            lines = []
            for group in specs:
                lines.append(f"[{group['group']}]")
                for a in group["attrs"]:
                    if a["value"]:
                        lines.append(f"  • {a['name']}: {a['value']}")
            return "\n".join(lines) if lines else "Không có thông tin"

        def _fmt_reviews(reviews: List[Dict], max_show: int = 10) -> str:
            if not reviews:
                return "Chưa có đánh giá."
            lines = []
            for i, rv in enumerate(reviews[:max_show], 1):
                purchased_tag = "[Đã mua]" if rv["is_purchased"] else "[Chưa xác nhận]"
                used = f" | {rv['used_duration']}" if rv["used_duration"] else ""
                content = rv["content"].strip() or "(Không có nội dung)"
                lines.append(
                    f"{i}. ⭐{rv['rating']} {purchased_tag}{used}\n"
                    f"   Tiêu đề: {rv['title']}\n"
                    f"   Nội dung: {content}\n"
                    + (f"   Phản hồi shop: {rv['seller_reply']}\n" if rv["seller_reply"] else "")
                )
            return "\n".join(lines)

        def _product_block(snap: Dict, label: str) -> str:
            price_info = (
                f"{snap['price']:,}đ"
                + (
                    f" (giảm {snap['discount_pct']}% từ {snap['original_price']:,}đ)"
                    if snap["discount_pct"] > 0
                    else ""
                )
            )
            return f"""
=== {label}: {snap['name']} ===
Thương hiệu : {snap['brand']}
Danh mục    : {snap['category']}
Giá         : {price_info}
Link        : {snap['url']}

--- Đánh giá tổng hợp ---
Trung bình  : {snap['rating_avg']} ⭐ ({snap['rating_count']} lượt)
Phân bố sao :
{_fmt_rating(snap['rating_breakdown'])}

--- Sizes có sẵn ---
{', '.join(snap['sizes']) if snap['sizes'] else 'Không phân size'}

--- Màu có sẵn ---
{', '.join(snap['colors']) if snap['colors'] else 'Không có lựa chọn màu'}

--- Thông số kỹ thuật ---
{_fmt_specs(snap['specifications'])}

--- Đánh giá của khách hàng (top {min(10, len(snap['reviews']))} reviews) ---
{_fmt_reviews(snap['reviews'])}
""".strip()

        product_a_block = _product_block(snapshot_a, "SẢN PHẨM A")
        product_b_block = _product_block(snapshot_b, "SẢN PHẨM B")

        prompt = f"""
Bạn là chuyên gia tư vấn mua sắm. Dưới đây là thông tin chi tiết của 2 sản phẩm trên Tiki.
Hãy so sánh 2 sản phẩm này và đưa ra khuyến nghị mua hàng rõ ràng.

Yêu cầu phân tích:
1. **Tổng quan** – Mô tả ngắn gọn 2 sản phẩm
2. **So sánh giá** – Giá trị/chất lượng so với giá tiền
3. **Thông số kỹ thuật** – Điểm mạnh/yếu từng sản phẩm
4. **Đánh giá của người mua** – Phân tích sentiment từ reviews
5. **Khuyến nghị** – Sản phẩm nào phù hợp với đối tượng nào
6. **Kết luận** – Nên mua sản phẩm nào nếu chỉ chọn 1

Trả lời bằng tiếng Việt, dùng markdown để format rõ ràng.

{'-'*60}
{product_a_block}

{'-'*60}
{product_b_block}
{'-'*60}
""".strip()

        return prompt

    async def compare_products(
        self,
        product_a: Dict,
        product_b: Dict,
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        Compare 2 products with LLM analysis (OpenAI).
        
        Args:
            product_a, product_b: {"product_id": "...", "spid": "...", "seller_id": "1"}
            llm_model: LLM model name (default: gpt-4o-mini)
            
        Returns:
            {"snapshot_a": {...}, "snapshot_b": {...}, "prompt": "...", "comparison": "..."}
        """
        try:
            logger.info("🚀 Bắt đầu crawl song song 2 sản phẩm...")
            
            # Crawl 2 sản phẩm song song
            snapshot_a, snapshot_b = await asyncio.gather(
                self._build_product_snapshot(
                    product_a["product_id"],
                    product_a.get("spid", ""),
                    product_a.get("seller_id", "1"),
                    label="Sản phẩm A",
                ),
                self._build_product_snapshot(
                    product_b["product_id"],
                    product_b.get("spid", ""),
                    product_b.get("seller_id", "1"),
                    label="Sản phẩm B",
                ),
            )

            prompt = self._build_comparison_payload(snapshot_a, snapshot_b)
            logger.info(f"\n📝 Prompt length: {len(prompt)} chars")

            # Gọi LLM
            comparison = ""
            logger.info("🤖 Gọi LLM...")
            try:
                comparison = call_openai(
                    prompt=prompt,
                    model=llm_model,
                    max_tokens=2048,
                    temperature=0.7,
                )
                if not comparison:
                    comparison = "[LLM error: No response]"
                logger.info("✅ LLM đã phản hồi")
            except Exception as e:
                logger.error(f"❌ LLM error: {e}")
                comparison = f"[LLM error: {e}]"

            return {
                "snapshot_a": snapshot_a,
                "snapshot_b": snapshot_b,
                "prompt": prompt,
                "comparison": comparison,
            }

        finally:
            await self.close()

    async def get_product_snapshot(
        self,
        product_id: str,
        spid: str,
        seller_id: str = "1",
        label: str = "",
    ) -> Dict:
        """Get snapshot của 1 sản phẩm."""
        try:
            return await self._build_product_snapshot(
                product_id, spid, seller_id, label
            )
        finally:
            await self.close()


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE USAGE
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    """Demo sử dụng phiên bản đơn giản."""
    crawler = TikiReviewCrawlerSimple()

    print("\n" + "=" * 70)
    print("TikiReviewCrawler - Simplified (httpx version)")
    print("=" * 70)

    # Get single product
    print("\n[1] Fetching single product...")
    snapshot = await crawler.get_product_snapshot(
        product_id="16268021",
        spid="16268022",
        seller_id="1",
    )

    print(f"\n✅ Product: {snapshot['name']}")
    print(f"   💰 Price: {snapshot['price']:,}đ (discount: {snapshot['discount_pct']}%)")
    print(f"   ⭐ Rating: {snapshot['rating_avg']} ({snapshot['rating_count']} reviews)")
    print(f"   💬 Reviews crawled: {len(snapshot['reviews'])}")

    if snapshot["reviews"]:
        print(f"\n   Sample review:")
        rv = snapshot["reviews"][0]
        print(f"   ⭐{rv['rating']} - {rv['title']}")
        print(f"   {rv['content'][:100]}...")

    # Compare 2 products
    print("\n" + "=" * 70)
    print("[2] Comparing 2 products...")
    result = await crawler.compare_products(
        product_a={
            "product_id": "16268021",
            "spid": "16268022",
            "seller_id": "1",
        },
        product_b={
            "product_id": "16268021",
            "spid": "16268022",
            "seller_id": "1",
        },
    )

    print(f"\n✅ Comparison complete")
    print(f"   Product A: {result['snapshot_a']['name']}")
    print(f"   Product B: {result['snapshot_b']['name']}")
    print(f"   Prompt size: {len(result['prompt'])} chars")

    print("\n✅ All done!")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

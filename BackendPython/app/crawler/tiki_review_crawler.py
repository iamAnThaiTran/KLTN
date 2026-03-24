"""
TikiReviewCrawler - Crawl product details + reviews để so sánh 2 sản phẩm qua LLM

Luồng hoạt động:
1. _extract_product_detail()  → Lấy info cơ bản + specs từ API /v2/products/{id}
2. _crawl_reviews()           → Lấy toàn bộ reviews (multi-page) từ API /v2/reviews
3. _build_comparison_payload()→ Format data gọn gàng gửi LLM
4. compare_products()         → Gọi LLM so sánh 2 sản phẩm, trả về kết quả

Cách sử dụng:
    crawler = TikiReviewCrawler()
    result  = await crawler.compare_products(
        product_a={"product_id": "16268021", "spid": "16268022", "seller_id": "1"},
        product_b={"product_id": "11111111", "spid": "22222222", "seller_id": "1"},
    )
    print(result["comparison"])   # Markdown từ LLM
"""

import asyncio
import json
import re
import sys
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode
from playwright.async_api import async_playwright, Browser
import logging

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

REVIEWS_API = "https://tiki.vn/api/v2/reviews"
PRODUCTS_API = "https://tiki.vn/api/v2/products/{product_id}"
MAX_REVIEW_PAGES = 5  # Tối đa 5 trang × 5 reviews = 25 reviews/sản phẩm
REVIEWS_PER_PAGE = 5
REVIEW_SORT = "score|desc,id|desc,stars|all"
REVIEW_INCLUDE = "comments,contribute_info,attribute_vote_summary"

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
# DATA MODELS (plain dicts, no external deps)
# ──────────────────────────────────────────────────────────────────────────────


def empty_product_snapshot() -> Dict:
    """Schema của 1 snapshot sản phẩm đã được chuẩn hoá."""
    return {
        # Định danh
        "product_id": "",
        "spid": "",
        "seller_id": "",
        # Thông tin cơ bản
        "name": "",
        "brand": "",
        "category": "",
        "price": 0,
        "original_price": 0,
        "discount_pct": 0,
        "url": "",
        "thumbnail": "",
        # Đánh giá tổng hợp
        "rating_avg": 0.0,
        "rating_count": 0,
        "rating_breakdown": {},  # {"5": {"count":N,"percent":P}, ...}
        # Thông số kỹ thuật (từ specifications)
        "specifications": [],  # [{"group":"...", "attrs":[{"name":"...","value":"..."}]}]
        # Size / Color options
        "sizes": [],
        "colors": [],
        # Reviews đã làm sạch
        "reviews": [],  # List[ReviewItem]  (xem _parse_review)
        # Meta
        "crawl_ok": False,
        "error": "",
    }


def _parse_review(raw: Dict) -> Dict:
    """Chuẩn hoá 1 review object từ API response."""
    created_by = raw.get("created_by", {})
    contribute = created_by.get("contribute_info", {}).get("summary", {})
    return {
        "id": raw.get("id"),
        "rating": raw.get("rating"),
        "title": raw.get("title", ""),
        "content": raw.get("content", ""),
        "author": created_by.get("full_name", ""),
        "is_purchased": created_by.get("purchased", False),
        "used_duration": raw.get("timeline", {}).get("content", ""),  # "Đã dùng 2 tháng"
        "total_reviews_by_author": contribute.get("total_review", 0),
        "thank_count": raw.get("thank_count", 0),
        "has_image": raw.get("is_photo", False),
        "created_at": raw.get("created_at"),
        "seller_reply": (
            raw.get("comments", [{}])[0].get("content", "")
            if raw.get("comments")
            else ""
        ),
        "attributes": raw.get("attributes", []),  # ["Mua từ nhà bán Tiki Trading"]
    }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN CRAWLER CLASS
# ──────────────────────────────────────────────────────────────────────────────


class TikiReviewCrawler:
    """
    Crawl product details + reviews từ Tiki.vn để so sánh 2 sản phẩm qua LLM.
    """

    # ── Browser helpers ───────────────────────────────────────────────────────

    async def _make_browser(self, playwright):
        return await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

    async def _fetch_json(self, browser: Browser, url: str) -> Optional[Dict]:
        """Fetch 1 URL JSON qua Playwright, trả về dict hoặc None."""
        page = None
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers(BROWSER_HEADERS)
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if not resp or not resp.ok:
                logger.warning(f"HTTP {resp and resp.status} for {url}")
                return None
            text = await resp.text()
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Fetch error [{url}]: {e}")
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    # ── Product detail ────────────────────────────────────────────────────────

    async def _fetch_product_detail(
        self, browser: Browser, product_id: str, spid: str
    ) -> Optional[Dict]:
        """Gọi /api/v2/products/{id} và trả về raw dict."""
        params = {"platform": "web", "version": "3"}
        if spid:
            params["spid"] = spid
        url = PRODUCTS_API.format(product_id=product_id) + "?" + urlencode(params)
        logger.info(f"  🔍 Product detail: {url}")
        return await self._fetch_json(browser, url)

    def _parse_product_detail(self, data: Dict) -> Dict:
        """Chuẩn hoá raw product API response."""

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

        # Rating summary (nếu có sẵn trong product API)
        rating = data.get("rating_average", 0)
        snapshot["rating_avg"] = round(float(rating), 2)
        snapshot["rating_count"] = data.get("review_count", 0)

        # Sizes & Colors từ configurable_options
        for opt in data.get("configurable_options", []):
            label = norm(opt.get("name", ""))
            values = [v.get("label") for v in opt.get("values", []) if v.get("label")]
            if re.search(r"size|kich co|kich thuoc", label):
                snapshot["sizes"] = values
            elif re.search(r"mau|color|colour", label):
                snapshot["colors"] = values

        # Specifications
        for group in data.get("specifications", []):
            grp_name = group.get("name", "")
            attrs = []
            for attr in group.get("attributes", []):
                raw_val = str(attr.get("value", "")).strip()
                # Strip HTML tags nếu có
                clean_val = re.sub(r"<[^>]+>", " ", raw_val).strip()
                clean_val = re.sub(r"\s+", " ", clean_val)
                attrs.append({"name": attr.get("name", ""), "value": clean_val})
            if attrs:
                snapshot["specifications"].append({"group": grp_name, "attrs": attrs})

        snapshot["crawl_ok"] = True
        return snapshot

    # ── Reviews ───────────────────────────────────────────────────────────────

    async def _crawl_reviews(
        self,
        browser: Browser,
        product_id: str,
        spid: str,
        seller_id: str,
        max_pages: int = MAX_REVIEW_PAGES,
    ) -> Tuple[List[Dict], Dict]:
        """
        Crawl tất cả reviews (nhiều trang).

        Returns:
            (reviews_list, rating_breakdown)
        """
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
            logger.info(f"    📝 Reviews page {page_num}: {url}")

            data = await self._fetch_json(browser, url)
            if not data:
                break

            # Lần đầu lấy rating_breakdown
            if page_num == 1 and "stars" in data:
                rating_breakdown = data["stars"]

            reviews_raw = data.get("data", [])
            if not reviews_raw:
                break

            for r in reviews_raw:
                all_reviews.append(_parse_review(r))

            # Kiểm tra có trang tiếp theo không
            paging = data.get("paging", {})
            last_page = paging.get("last_page", 1)
            current_pg = paging.get("current_page", page_num)
            if current_pg >= last_page:
                break

        logger.info(f"    ✅ Total reviews crawled: {len(all_reviews)}")
        return all_reviews, rating_breakdown

    # ── Full product snapshot ─────────────────────────────────────────────────

    async def _build_product_snapshot(
        self,
        browser: Browser,
        product_id: str,
        spid: str,
        seller_id: str,
        label: str = "",
    ) -> Dict:
        """
        Kết hợp product detail + reviews thành 1 snapshot hoàn chỉnh.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Building snapshot for: {label or product_id}")

        # 1. Product detail
        raw_detail = await self._fetch_product_detail(browser, product_id, spid)
        snapshot = self._parse_product_detail(raw_detail or {})
        snapshot["product_id"] = product_id
        snapshot["spid"] = spid
        snapshot["seller_id"] = seller_id

        # 2. Reviews (nhiều trang)
        reviews, rating_bd = await self._crawl_reviews(
            browser, product_id, spid, seller_id
        )
        snapshot["reviews"] = reviews
        snapshot["rating_breakdown"] = rating_bd

        # Cập nhật rating_count từ reviews API nếu product API thiếu
        if not snapshot["rating_count"] and rating_bd:
            total = sum(v.get("count", 0) for v in rating_bd.values())
            snapshot["rating_count"] = total

        logger.info(
            f"  ✅ Snapshot done: {snapshot['name'][:50] if snapshot['name'] else 'Unknown'} | "
            f"⭐ {snapshot['rating_avg']} | "
            f"💬 {len(reviews)} reviews"
        )
        return snapshot

    # ── LLM Payload builder ───────────────────────────────────────────────────

    def _build_comparison_payload(
        self,
        snapshot_a: Dict,
        snapshot_b: Dict,
    ) -> str:
        """
        Tạo prompt text gửi LLM để so sánh 2 sản phẩm.
        Format gọn nhưng đủ thông tin để LLM phân tích.
        """

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
4. **Đánh giá của người mua** – Phân tích sentiment từ reviews, điểm nổi bật
5. **Khuyến nghị** – Sản phẩm nào phù hợp với đối tượng nào (dùng thường ngày / tặng quà / thể thao, v.v.)
6. **Kết luận** – Nên mua sản phẩm nào nếu chỉ chọn 1

Trả lời bằng tiếng Việt, dùng markdown để format rõ ràng.

{'-'*60}
{product_a_block}

{'-'*60}
{product_b_block}
{'-'*60}
""".strip()

        return prompt

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_product_snapshot(
        self,
        product_id: str,
        spid: str,
        seller_id: str = "1",
        label: str = "",
    ) -> Dict:
        """
        Lấy snapshot đầy đủ của 1 sản phẩm (product detail + reviews).
        Hữu ích để cache hoặc hiển thị riêng lẻ.
        """
        playwright = None
        browser = None
        try:
            playwright = await async_playwright().start()
            browser = await self._make_browser(playwright)
            return await self._build_product_snapshot(
                browser, product_id, spid, seller_id, label
            )
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

    async def compare_products(
        self,
        product_a: Dict,  # {"product_id": "...", "spid": "...", "seller_id": "..."}
        product_b: Dict,
        llm_client=None,  # Optional: truyền LLM client vào; nếu None trả về prompt text
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        Crawl 2 sản phẩm song song, build prompt, (tuỳ chọn) gửi LLM.

        Args:
            product_a / product_b: dict có keys product_id, spid, seller_id
            llm_client: Nếu truyền vào Anthropic client, sẽ gọi LLM tự động
            llm_model: Model ID để gọi LLM

        Returns:
            {
                "snapshot_a"  : Dict,   # full snapshot sản phẩm A
                "snapshot_b"  : Dict,   # full snapshot sản phẩm B
                "prompt"      : str,    # prompt text đã format
                "comparison"  : str,    # LLM response (hoặc "" nếu không truyền llm_client)
            }
        """
        playwright = None
        browser = None

        try:
            playwright = await async_playwright().start()
            browser = await self._make_browser(playwright)

            # Crawl 2 sản phẩm song song để tiết kiệm thời gian
            logger.info("🚀 Bắt đầu crawl song song 2 sản phẩm...")
            snapshot_a, snapshot_b = await asyncio.gather(
                self._build_product_snapshot(
                    browser,
                    product_a["product_id"],
                    product_a.get("spid", ""),
                    product_a.get("seller_id", "1"),
                    label="Sản phẩm A",
                ),
                self._build_product_snapshot(
                    browser,
                    product_b["product_id"],
                    product_b.get("spid", ""),
                    product_b.get("seller_id", "1"),
                    label="Sản phẩm B",
                ),
            )

            # Build prompt
            prompt = self._build_comparison_payload(snapshot_a, snapshot_b)
            logger.info(f"\n📝 Prompt length: {len(prompt)} chars")

            # Gọi LLM nếu có client
            comparison = ""
            if llm_client:
                logger.info("🤖 Gọi LLM để so sánh...")
                try:
                    response = llm_client.messages.create(
                        model=llm_model,
                        max_tokens=2048,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    comparison = response.content[0].text
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
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

    def save_snapshots_json(self, result: Dict, path: str = "tiki_comparison.json"):
        """Lưu kết quả ra file JSON để debug hoặc cache."""
        output = {
            "snapshot_a": result["snapshot_a"],
            "snapshot_b": result["snapshot_b"],
            "prompt": result["prompt"],
            "comparison": result["comparison"],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Saved to {path}")

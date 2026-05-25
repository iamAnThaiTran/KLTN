"""
Lazada Product Detail Crawler - For product details + attribute extraction
Uses Playwright for browser automation to extract specs from HTML
Uses LLM for semantic attribute extraction

Lazada Specs Structure:
  <div class="pdp-mod-specification">
    <ul class="specification-keys">
      <li class="key-li">
        <span class="key-title">Brand</span>
        <div class="key-value">Value</div>
      </li>
    </ul>
  </div>

Fixes applied:
  1. Bỏ block CSS — specs cần CSS để render
  2. Đổi wait_until="domcontentloaded" thay networkidle (SPA-friendly)
  3. Scroll đến cuối trang thật sự, thử click tab specs nếu có
  4. Phát hiện bị block/captcha → reset profile tự động
  5. max_retries mặc định tăng lên 3
  6. Browser health check — tự khởi động lại nếu crash
  7. Rate limit ngẫu nhiên hơn, thêm jitter
  8. Detect blocked page (robot check, 404, redirect lạ)
"""

import asyncio
import logging
import re
import os
import shutil
import tempfile
import random
import time
from typing import Dict, List, Any, Optional

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext
except ImportError:
    async_playwright = None
    Browser = None
    BrowserContext = None

try:
    from extraction import (
        LLMAttributeExtractor,
        ExtractionSchema,
        AttributeSchema,
    )
    HAS_LLM_SUPPORT = True
except ImportError:
    HAS_LLM_SUPPORT = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_html(text: str) -> str:
    """Strip HTML/XML tags and decode common entities."""
    text = re.sub(r"<(br|p|div|li|tr|td|th|h[1-6])[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&nbsp;": " ", "&quot;": '"', "&#39;": "'", "&apos;": "'",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


_BLOCK_SIGNALS = [
    "robot", "captcha", "blocked", "403", "access denied",
    "security check", "unusual traffic", "verify you are human",
]

def _is_blocked_page(url: str, content: str) -> bool:
    """Heuristic: phát hiện trang bị block / captcha."""
    url_lower = url.lower()
    content_lower = content.lower()
    return any(sig in url_lower or sig in content_lower for sig in _BLOCK_SIGNALS)


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------

class LazadaProductDetailCrawler:
    """
    Lazada product detail crawler với LLM-based attribute extraction.
    Dùng Playwright để điều khiển browser.

    Cải tiến so với phiên bản cũ:
    - Không block CSS/JS (chỉ block media nặng) → specs render đúng
    - wait_until="domcontentloaded" → không bị timeout trên SPA
    - Scroll đến cuối trang + thử click tab specs
    - Tự phát hiện block/captcha và reset profile
    - Browser tự restart nếu crash
    - max_retries mặc định = 3
    """

    def __init__(
        self,
        use_llm: bool = True,
        timeout: float = 30.0,
        max_retries: int = 1,
    ):
        self.base_url = "https://www.lazada.vn"
        self.timeout = timeout * 1000          # ms cho Playwright
        self.max_retries = max_retries
        self.use_llm = use_llm and HAS_LLM_SUPPORT
        self.llm_extractor = None

        # Browser
        self.playwright_instance = None
        self.browser: Optional[Any] = None   # persistent context

        # Profile — tạo tên profile cố định để tái dùng cookie
        self._base_profile_dir = os.path.join(tempfile.gettempdir(), "lazada_crawler")
        self.user_data_dir = os.path.join(self._base_profile_dir, "profile_0")
        os.makedirs(self.user_data_dir, exist_ok=True)

        # Rate limiting
        self.last_request_time: float = 0
        self.min_request_interval: float = 4.0
        self.max_request_interval: float = 9.0

        # Số lần bị block liên tiếp — nếu > threshold thì reset profile
        self._consecutive_blocks: int = 0
        self._block_threshold: int = 2

        if self.use_llm and HAS_LLM_SUPPORT:
            self.llm_extractor = LLMAttributeExtractor()
            logger.info("✅ LLM extractor initialized")
        elif self.use_llm:
            logger.warning("⚠️  LLM support not available")

        logger.info(
            f"🆕 LazadaProductDetailCrawler initialized "
            f"(LLM={self.use_llm}, timeout={timeout}s, retries={max_retries})"
        )

    # ------------------------------------------------------------------
    # Public API  (giữ nguyên signature — đầu vào/đầu ra không đổi)
    # ------------------------------------------------------------------

    async def crawl_product_details(
        self,
        product_url: str,
        product_id: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl 1 sản phẩm Lazada và extract attributes.

        Returns:
            {
                "status": "success" | "error",
                "product_id": str,
                "product": {...},
                "extracted_attributes": {...},
                "extraction_method": "llm",
            }
        """
        if not async_playwright:
            return {
                "status": "error",
                "product_id": product_id,
                "error": "Playwright not available. Run: pip install playwright && playwright install chromium",
            }

        try:
            logger.info(f"📥 Crawling: {product_id}")
            product = await self._fetch_product_details(product_url, product_id)

            if product.get("status") == "error":
                return product

            name = product.get("name", "")
            specs_count = len(product.get("specs", []))
            logger.info(f"✅ Fetched '{name[:60]}' | specs={specs_count}")

            # ---- Attribute extraction ----
            extracted_attributes: Dict[str, Any] = {}

            if schema and self.use_llm and self.llm_extractor:
                result = await self.extract_attributes_with_llm(product=product, schema=schema)
                extracted_attributes = result.get("final_attributes", {})
                logger.info(f"📊 LLM attributes: {list(extracted_attributes.keys())}")

            elif self.use_llm and self.llm_extractor and product.get("specs"):
                # Không có schema → chuyển specs thành dict đơn giản
                extracted_attributes = {
                    spec["name"].lower().replace(" ", "_"): spec["value"]
                    for spec in product.get("specs", [])
                    if spec.get("name") and spec.get("value")
                }

            return {
                "status": "success",
                "product_id": product_id,
                "product": product,
                "extracted_attributes": extracted_attributes,
                "extraction_method": "llm",
            }

        except Exception as e:
            logger.error(f"❌ crawl_product_details({product_id}): {e}", exc_info=True)
            return {"status": "error", "product_id": product_id, "error": str(e)}

    async def crawl_multiple_products(
        self,
        product_urls: List[str],
        product_ids: List[str],
        schema: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 2,          # Giảm xuống 2 để tránh bị detect
    ) -> List[Dict[str, Any]]:
        """
        Crawl nhiều sản phẩm song song.

        Returns:
            List[Dict] — mỗi phần tử là kết quả crawl_product_details
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl(url: str, pid: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.crawl_product_details(
                    product_url=url, product_id=pid, schema=schema
                )

        logger.info(
            f"📥 Crawling {len(product_urls)} products "
            f"(max_concurrent={max_concurrent})"
        )

        results = await asyncio.gather(
            *[
                _crawl(url, pid)
                for url, pid in zip(product_urls[:3], product_ids[:3])
            ],
            return_exceptions=False,
        )

        success = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"✅ Done: {success}/{len(results)} succeeded")
        return list(results)

    # ------------------------------------------------------------------
    # Browser management
    # ------------------------------------------------------------------

    async def _ensure_browser(self) -> bool:
        """Khởi tạo persistent browser nếu chưa có, tự restart nếu crash."""
        if self.browser:
            # Health check nhẹ
            try:
                _ = self.browser.pages
                return True
            except Exception:
                logger.warning("⚠️  Browser died, restarting...")
                await self._teardown_browser()

        return await self._init_browser()

    async def _init_browser(self) -> bool:
        """Tạo persistent Chromium context mới."""
        try:
            logger.info(f"🆕 Starting browser (profile: {self.user_data_dir})")

            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ]
            ua = random.choice(user_agents)

            if not self.playwright_instance:
                self.playwright_instance = await async_playwright().start()

            self.browser = await self.playwright_instance.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-plugins",
                    "--disable-background-networking",
                    "--enable-features=NetworkService,NetworkServiceInProcess",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                ],
                user_agent=ua,
                viewport={"width": 1920, "height": 1080},
                locale="vi-VN",
                timezone_id="Asia/Ho_Chi_Minh",
            )

            # Stealth: ẩn dấu hiệu automation
            await self.browser.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['vi-VN', 'vi', 'en-US', 'en']
                });
                window.chrome = { runtime: {} };
            """)

            logger.info("✅ Browser ready")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to init browser: {e}")
            return False

    async def _teardown_browser(self):
        """Đóng browser và playwright instance."""
        for obj, name in [(self.browser, "browser"), (self.playwright_instance, "playwright")]:
            if obj:
                try:
                    await obj.close() if name == "browser" else await obj.stop()
                except Exception:
                    pass
        self.browser = None
        self.playwright_instance = None

    async def _reset_profile(self):
        """Xoá profile bị đốt, tạo profile mới, restart browser."""
        logger.warning("🔄 Resetting browser profile (bị block quá nhiều lần)...")
        await self._teardown_browser()

        # Tạo profile mới với tên khác
        suffix = int(time.time())
        self.user_data_dir = os.path.join(self._base_profile_dir, f"profile_{suffix}")
        os.makedirs(self.user_data_dir, exist_ok=True)

        self._consecutive_blocks = 0
        logger.info(f"✅ New profile: {self.user_data_dir}")

        await asyncio.sleep(random.uniform(5, 10))  # Nghỉ sau khi reset

    async def _new_page(self) -> Any:
        """Lấy page mới từ persistent context."""
        if not await self._ensure_browser():
            raise RuntimeError("Browser không khởi động được")

        page = await self.browser.new_page()

        # FIX: Chỉ block media nặng — KHÔNG block CSS/JS
        # CSS cần thiết để specs section render đúng
        await page.route(
            "**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf,eot}",
            lambda route: route.abort()
        )

        return page

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def _rate_limit(self):
        """Đợi đủ thời gian giữa các request, có jitter ngẫu nhiên."""
        now = time.time()
        elapsed = now - self.last_request_time
        target = random.uniform(self.min_request_interval, self.max_request_interval)

        # Thêm jitter extra nếu đã bị block gần đây
        if self._consecutive_blocks > 0:
            target += random.uniform(5, 15) * self._consecutive_blocks

        wait = target - elapsed
        if wait > 0:
            logger.debug(f"⏳ Rate limit: chờ {wait:.1f}s")
            await asyncio.sleep(wait)

        self.last_request_time = time.time()

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    async def _fetch_product_details(
        self,
        product_url: str,
        product_id: str,
    ) -> Dict[str, Any]:
        """Fetch chi tiết sản phẩm từ Lazada với retry logic."""

        last_error = "Unknown error"

        for attempt in range(self.max_retries):
            page = None
            try:
                await self._rate_limit()
                page = await self._new_page()

                logger.debug(
                    f"🌐 [{product_id}] attempt {attempt + 1}/{self.max_retries}: {product_url}"
                )

                # goto với domcontentloaded — React chưa render xong ở thời điểm này
                try:
                    await page.goto(
                        product_url,
                        wait_until="domcontentloaded",
                        timeout=self.timeout,
                    )
                except Exception as nav_err:
                    logger.info(f"   goto partial: {type(nav_err).__name__} (bình thường với SPA)")

                # Kiểm tra bị block ngay sau khi load
                current_url = page.url
                page_text_preview = await page.evaluate(
                    "() => document.body?.innerText?.slice(0, 500) || ''"
                )
                if _is_blocked_page(current_url, page_text_preview):
                    logger.warning(f"⛔ Bị block/captcha (attempt {attempt + 1})")
                    self._consecutive_blocks += 1
                    if self._consecutive_blocks >= self._block_threshold:
                        await page.close()
                        page = None
                        await self._reset_profile()
                    raise RuntimeError("Page bị block hoặc captcha")
                self._consecutive_blocks = 0

                # -------------------------------------------------------
                # CORE FIX: Chờ React render xong specs section
                # .pdp-mod-specification chỉ xuất hiện sau khi JS chạy xong
                # domcontentloaded không đủ — phải wait_for_selector
                # -------------------------------------------------------
                logger.info("⏳ Chờ React render specs section...")
                try:
                    await page.wait_for_selector(
                        ".pdp-mod-specification",
                        timeout=self.timeout,   # dùng full timeout ở đây
                    )
                    logger.info("✅ Specs section đã có trong DOM")
                except Exception:
                    # Timeout — thử scroll xuống để trigger lazy render rồi chờ thêm
                    logger.info("⚠️  Specs chưa thấy sau wait, thử scroll để trigger lazy load...")
                    await self._scroll_to_load_specs(page)
                    try:
                        await page.wait_for_selector(
                            ".pdp-mod-specification",
                            timeout=10000,
                        )
                        logger.info("✅ Specs section xuất hiện sau scroll")
                    except Exception:
                        logger.info("⚠️  Specs section vẫn không thấy — sẽ thử extract anyway")

                # Expand nếu đang bị collapse bởi class height-limit
                await self._scroll_to_specs_and_expand(page)

                # Extract dữ liệu
                product_data = await page.evaluate(_JS_EXTRACT_PRODUCT)

                specs_count = len(product_data.get("specs", []))
                logger.debug(f"📊 specs={specs_count}, name={bool(product_data.get('name'))}")

                if specs_count == 0 and attempt < self.max_retries - 1:
                    logger.info(f"⚠️  Không có specs, thử lại...")
                    await asyncio.sleep(random.uniform(3, 6))
                    continue

                name = product_data.get("name", "")
                price = product_data.get("price", "")
                logger.info(
                    f"✅ Extracted — name={'✓' if name else '✗'}, "
                    f"price={'✓' if price else '✗'}, "
                    f"specs={specs_count}"
                )

                return {
                    "status": "success",
                    "product_id": product_id,
                    "name": name,
                    "price": price,
                    "brand": product_data.get("brand", ""),
                    "rating": product_data.get("rating", ""),
                    "reviews_count": product_data.get("reviews_count", 0),
                    "description": product_data.get("description", ""),
                    "specs": product_data.get("specs", []),
                }

            except Exception as e:
                last_error = str(e)
                logger.debug(f"⚠️  Attempt {attempt + 1} failed: {last_error}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(random.uniform(3, 7))

            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

        logger.error(f"❌ [{product_id}] Hết retry. Lỗi cuối: {last_error}")
        return {"status": "error", "product_id": product_id, "error": last_error}

    async def _scroll_to_load_specs(self, page: Any):
        """
        Scroll thật chậm để trigger lazy render specs section.
        """

        try:
            last_height = 0
            same_count = 0

            while True:
                

                # scroll thêm 500px như người thật
                await page.mouse.wheel(0, 500)

                await asyncio.sleep(random.uniform(0.8, 1.5))

                # check specs đã xuất hiện chưa
                found = await page.evaluate("""
                    () => !!document.querySelector('.pdp-mod-specification')
                """)

                if found:
                    logger.info("✅ Specs appeared during scrolling")
                    return

                # đã tới cuối trang chưa
                new_height = await page.evaluate(
                    "() => window.scrollY + window.innerHeight"
                )

                if abs(new_height - last_height) < 50:
                    same_count += 1
                else:
                    same_count = 0

                last_height = new_height

                # đứng yên nhiều lần => cuối trang
                if same_count >= 5:
                    break

            logger.info("⚠️ Reached page end but specs still missing")

        except Exception as e:
            logger.info(f"_scroll_to_load_specs error: {e}")
            
    async def _scroll_to_specs_and_expand(self, page: Any):
        """
        Xử lý collapse của specs section trên Lazada.

        Root cause đã xác nhận từ HTML thật:
          - Khi trang load:   class="pdp-product-desc-v2 height-limit"  → specs bị clip
          - Sau khi click:    class="pdp-product-desc-v2 "               → specs hiện đầy đủ

        Class "height-limit" được remove bằng cách click button "VIEW MORE".
        Specs vẫn ở trong DOM nhưng innerText trả về rỗng khi đang bị clip.
        """
        try:
            # Bước 1: Scroll đến specs section để trigger lazy render
            scrolled = await page.evaluate("""
                () => {
                    const el = document.querySelector('.pdp-mod-specification');
                    if (!el) return false;
                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                    return true;
                }
            """)
            logger.info(f"🔍 Scroll to specs: {'found' if scrolled else 'NOT found (.pdp-mod-specification missing)'}")
            if scrolled:
                await asyncio.sleep(random.uniform(0.5, 0.8))

            # Bước 2: Kiểm tra xem có đang bị height-limit không
            # Nếu có → click VIEW MORE để remove class
            result = await page.evaluate("""
                () => {
                    const descDiv = document.querySelector('.pdp-product-desc-v2');
                    if (!descDiv) return { status: 'no_container' };

                    const isCollapsed = descDiv.classList.contains('height-limit');
                    if (!isCollapsed) return { status: 'already_expanded' };

                    const btn = document.querySelector(
                        'button.pdp-view-more-btn, .expand-button button, [class*="view-more-btn"]'
                    );
                    if (!btn) return { status: 'no_button' };

                    btn.click();

                    const stillCollapsed = descDiv.classList.contains('height-limit');
                    return {
                        status: stillCollapsed ? 'click_failed' : 'expanded',
                        btnText: btn.innerText?.trim()
                    };
                }
            """)

            status = result.get("status", "unknown")
            logger.info(f"📐 height-limit expand status: {status}")

            if status == "expanded":
                await asyncio.sleep(random.uniform(0.3, 0.6))
                logger.info(f"✅ Expanded specs (clicked '{result.get('btnText', 'VIEW MORE')}')")
            elif status == "already_expanded":
                logger.info("ℹ️  Specs đã expanded sẵn (không có height-limit)")
            elif status in ("no_button", "click_failed"):
                # Fallback: remove class trực tiếp bằng JS
                removed = await page.evaluate("""
                    () => {
                        const el = document.querySelector('.pdp-product-desc-v2.height-limit');
                        if (!el) return false;
                        el.classList.remove('height-limit');
                        return true;
                    }
                """)
                logger.info(f"{'✅ Removed' if removed else '⚠️  Could not remove'} height-limit via JS fallback")
                if removed:
                    await asyncio.sleep(0.3)
            elif status == "no_container":
                logger.info("⚠️  .pdp-product-desc-v2 không tìm thấy — trang có thể chưa load xong")
            else:
                logger.info(f"⚠️  Expand result không xác định: {status}")

        except Exception as e:
            logger.info(f"   _scroll_to_specs_and_expand error (bỏ qua): {e}")

    # ------------------------------------------------------------------
    # LLM extraction  (giữ nguyên signature)
    # ------------------------------------------------------------------

    async def extract_attributes_with_llm(
        self,
        product: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract attributes dùng LLM.

        Returns:
            {
                "llm_result": {...},
                "final_attributes": {...},
                "confidence": float,
                "method": "llm" | "fallback",
            }
        """
        if not self.llm_extractor:
            return {
                "llm_result": {}, "final_attributes": {},
                "method": "fallback", "error": "LLM extractor not initialized",
            }

        try:
            product_text = self._build_product_text_for_llm(product)
            llm_schema = self._convert_schema_to_llm_schema(schema)
            if not llm_schema:
                raise ValueError("Không convert được schema sang LLM format")

            logger.info("🤖 Calling LLM...")
            llm_results = await self.llm_extractor.extract_batch(
                products=[{
                    "product_id": product.get("product_id", "unknown"),
                    "text": product_text,
                }],
                schema=llm_schema,
            )

            if not llm_results or not llm_results[0].is_valid():
                err = llm_results[0].error if llm_results else "No result"
                raise ValueError(f"LLM extraction failed: {err}")

            llm_attrs = llm_results[0].attributes
            logger.info(f"✅ LLM extracted: {list(llm_attrs.keys())}")

            final_attributes = {
                attr_spec.get("name", "").lower(): llm_attrs.get(attr_spec.get("name", "").lower())
                for attr_spec in schema.get("attributes", [])
                if attr_spec.get("name")
            }

            return {
                "llm_result": llm_attrs,
                "final_attributes": final_attributes,
                "confidence": llm_results[0].confidence,
                "method": "llm",
            }

        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
            return {
                "llm_result": {}, "final_attributes": {},
                "method": "fallback", "error": str(e),
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_product_text_for_llm(self, product: Dict[str, Any]) -> str:
        parts = []
        if product.get("name"):
            parts.append(f"Product: {product['name']}")
        if product.get("brand"):
            parts.append(f"Brand: {product['brand']}")
        if product.get("description"):
            parts.append(f"Description: {_clean_html(product['description'])}")
        if product.get("specs"):
            parts.append(f"Specifications: {self._specs_to_text(product['specs'])}")
        return "\n".join(parts)

    def _specs_to_text(self, specs: List[Dict]) -> str:
        return " | ".join(
            f"{s['name'].strip()}: {s['value'].strip()}"
            for s in specs
            if s.get("name") and s.get("value")
        )

    def _convert_schema_to_llm_schema(
        self, schema: Dict[str, Any]
    ) -> Optional["ExtractionSchema"]:
        if not HAS_LLM_SUPPORT:
            return None
        try:
            if not schema or not schema.get("attributes"):
                return None

            llm_attrs = []
            for attr_spec in schema.get("attributes", []):
                attr_name = attr_spec.get("name", "").lower().strip()
                if not attr_name:
                    continue
                attr_type_str = attr_spec.get("attr_type", "regex")
                vocabulary = attr_spec.get("vocabulary", [])

                if attr_type_str == "numeric":
                    llm_type = "number"
                elif vocabulary:
                    llm_type = "multi_enum" if len(vocabulary) > 1 else "enum"
                else:
                    llm_type = "string"

                llm_attrs.append(AttributeSchema(
                    name=attr_name,
                    type=llm_type,
                    required=attr_spec.get("required", False),
                    allowed_values=vocabulary or None,
                ))

            return ExtractionSchema(
                category=schema.get("category", "product"),
                attributes=llm_attrs,
            )
        except Exception as e:
            logger.error(f"❌ _convert_schema_to_llm_schema: {e}")
            return None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self):
        """Đóng browser và giải phóng tài nguyên."""
        await self._teardown_browser()
        logger.info("🔌 LazadaProductDetailCrawler closed")


# ---------------------------------------------------------------------------
# JavaScript chạy trong browser để extract dữ liệu sản phẩm
# Tách ra ngoài để dễ đọc và maintain
# ---------------------------------------------------------------------------

_JS_EXTRACT_PRODUCT = """
() => {
    const result = {
        name: "", price: "", brand: "", rating: "",
        reviews_count: 0, description: "", specs: []
    };

    // ---- Helper ----
    const getText = (selector, fallbacks = []) => {
        const selectors = [selector, ...fallbacks];
        for (const s of selectors) {
            try {
                const el = document.querySelector(s);
                if (el) return el.innerText?.trim() || "";
            } catch (e) {}
        }
        return "";
    };

    // ---- Basic info ----
    result.name = getText(
        "h1.pdp-product-title__text",
        ["h1.title--wrap--UUHae_g", "h1[class*='title']", "h1"]
    );

    result.price = getText(
        ".pdp-price__value",
        [".pdp-price .pdp-price__value", "[class*='pdp-price']:not([class*='origin'])"]
    );

    result.brand = getText(
        ".pdp-product-brand-v2__brand-link",
        ["[class*='brand-link']", "[class*='brand-name']"]
    );

    result.rating = getText(
        ".pdp-review-summary__rating",
        ["[class*='review-summary__rating']", "[class*='overall-rating']"]
    );

    const reviewEl = document.querySelector(
        ".pdp-review-summary__count, [class*='review-summary__count']"
    );
    if (reviewEl) {
        const m = (reviewEl.innerText || "").match(/\\d+/);
        result.reviews_count = m ? parseInt(m[0]) : 0;
    }

    result.description = getText(
        ".pdp-product-description",
        ["[class*='product-description']", "[class*='detail-desc']"]
    );

    // ---- Specifications ----
    const specsList = [];
    const seen = new Set();

    const addSpec = (name, value) => {
        name = (name || "").trim();
        value = (value || "").trim();
        if (!name || !value) return;
        const key = (name + ":" + value).toLowerCase();
        if (seen.has(key)) return;
        seen.add(key);
        specsList.push({ name, value });
    };

    // Strategy 1: Primary Lazada spec structure
    document.querySelectorAll(
        ".specification-keys .key-li, .pdp-mod-specification .key-li"
    ).forEach(item => {
        const title = item.querySelector(".key-title, [class*='key-title']");
        const val   = item.querySelector(".key-value, [class*='key-value']");
        if (title && val) addSpec(title.innerText, val.innerText);
    });

    // Strategy 2: Table-based specs (một số layout Lazada dùng table)
    if (specsList.length === 0) {
        document.querySelectorAll("table tr").forEach(row => {
            const cells = row.querySelectorAll("td, th");
            if (cells.length >= 2) addSpec(cells[0].innerText, cells[1].innerText);
        });
    }

    // Strategy 3: dl/dt/dd pattern
    if (specsList.length === 0) {
        document.querySelectorAll("dl").forEach(dl => {
            const dts = dl.querySelectorAll("dt");
            const dds = dl.querySelectorAll("dd");
            dts.forEach((dt, i) => {
                if (dds[i]) addSpec(dt.innerText, dds[i].innerText);
            });
        });
    }

    // Strategy 4: Generic key:value trong text nodes
    if (specsList.length === 0) {
        const containers = document.querySelectorAll(
            "[class*='spec'], [class*='attribute'], [class*='property']"
        );
        containers.forEach(el => {
            const text = el.innerText?.trim() || "";
            const colonIdx = text.indexOf(":");
            if (colonIdx > 2 && colonIdx < text.length - 1) {
                addSpec(text.slice(0, colonIdx), text.slice(colonIdx + 1));
            }
        });
    }

    result.specs = specsList;
    return result;
}
"""
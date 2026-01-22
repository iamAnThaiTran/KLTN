import asyncio
import json
import re
import sys
from typing import List, Dict
from playwright.async_api import async_playwright

# UTF-8 for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ================= CONFIG =================
MAX_PAGES = 2
SCROLL_DELAY = 1.0

PRODUCT_SELECTOR = 'div[data-qa-locator="product-item"]'
NEXT_BUTTON_SELECTOR = 'li.ant-pagination-next a'


# ================= UTILS =================
async def auto_scroll(page):
    await page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let total = 0;
                const distance = 800;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    total += distance;
                    if (total >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 800);
            });
        }
    """)
    await page.wait_for_timeout(1500)


def normalize(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()


# ================= LIST CRAWL =================
async def crawl_lazada_list(page, query: str) -> List[Dict]:
    url = f"https://www.lazada.vn/catalog/?q={query}"
    await page.goto(url, wait_until="networkidle")

    products = []

    for page_index in range(1, MAX_PAGES + 1):
        print(f"\n🌐 Trang {page_index}")
        await auto_scroll(page)

        items = await page.query_selector_all(PRODUCT_SELECTOR)
        print(f"  → {len(items)} sản phẩm")

        for item in items:
            data = await item.evaluate("""
                el => {
                    const a = el.querySelector("a");
                    const title = el.querySelector(".RfADt a")?.innerText?.trim();
                    const price = el.querySelector(".aBrP0 .ooOxS")?.innerText?.trim();
                    const img =
                        el.querySelector("img")?.getAttribute("data-src") ||
                        el.querySelector("img")?.src;

                    return {
                        title,
                        price,
                        link: a?.href,
                        image: img
                    };
                }
            """)

            if data["title"] and data["link"]:
                products.append(data)

        next_btn = await page.query_selector(NEXT_BUTTON_SELECTOR)
        if not next_btn:
            break

        await asyncio.gather(
            next_btn.click(),
            page.wait_for_navigation(wait_until="networkidle")
        )

    return products


# ================= DETAIL CRAWL =================
async def crawl_lazada_detail(browser, product_url: str) -> Dict:
    page = await browser.new_page()
    await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)


    detail = await page.evaluate("""
        () => {
            const uniq = arr => [...new Set(arr)];

            const result = {
                brand: "",
                sizes: [],
                colors: [],
                materials: []
            };

            // ===== BRAND =====
            const brandEl = document.querySelector(
                ".pdp-product-brand-v2__brand-link"
            );
            if (brandEl) {
                result.brand = brandEl.innerText.trim();
            }

            // ===== SIZES =====
            document
                .querySelectorAll(".sku-variable-img-name")
                .forEach(el => {
                    const size = el.innerText.trim();
                    if (size) result.sizes.push(size);
                });

            // ===== COLORS (SKU CODE) =====
            document
                .querySelectorAll(".sku-variable-name-text")
                .forEach(el => {
                    const code = el.innerText.trim();
                    if (code) result.colors.push(code);
                });

            result.sizes = uniq(result.sizes);
            result.colors = uniq(result.colors);

            return result;
        }
        """)

    await page.close()
    return detail


# ================= PIPELINE =================
async def crawl_lazada_full(query: str) -> List[Dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"🔍 Crawl Lazada: {query}")
        products = await crawl_lazada_list(page, query)

        print(f"\n📦 Crawl chi tiết {len(products)} sản phẩm")
        for i, product in enumerate(products, 1):
            print(f"  [{i}/{len(products)}] {product['title'][:50]}...")
            product["attributes"] = await crawl_lazada_detail(
                browser, product["link"]
            )

        await browser.close()
        return products


# ================= MAIN =================
if __name__ == "__main__":
    query = "giày nike air force 1"
    result = asyncio.run(crawl_lazada_full(query))

    print("\n================ RESULT SAMPLE ================")
    print(json.dumps(result[:2], indent=2, ensure_ascii=False))

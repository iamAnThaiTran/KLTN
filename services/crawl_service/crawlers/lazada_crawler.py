"""
Lazada Crawler for CrawlService
Crawls products from Lazada.vn using Playwright (browser automation)
Handles JavaScript-rendered content

Adapted from user's Lazada crawler script
"""

import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
import logging

logger = logging.getLogger(__name__)


class LazadaCrawler:
    """Lazada crawler using Playwright (browser automation)"""
    
    def __init__(self):
        self.base_url = "https://www.lazada.vn/catalog/"
        self.timeout = 30000  # 30 seconds in milliseconds
        self.max_pages = 2
    
    async def crawl(self, query: str, max_products: int = 20) -> List[Dict[str, Any]]:
        """
        Crawl products from Lazada using Playwright
        
        Args:
            query: Search query (e.g., "giày thể thao")
            max_products: Maximum number of products to crawl
        
        Returns:
            List of products with source="lazada"
        """
        logger.info(f"🟦 Lazada: Crawling for query: {query}")
        
        playwright = None
        browser = None
        
        try:
            # Launch Playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security'
                ]
            )
            
            # Crawl products
            products = await self._crawl_product_list(browser, query, max_products)
            logger.info(f"✅ Lazada: Extracted {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"❌ Lazada crawl error: {e}", exc_info=True)
            return []
            
        finally:
            # Cleanup
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
            
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
    
    async def _crawl_product_list(self, browser: Browser, query: str, max_products: int) -> List[Dict]:
        """Crawl product list from Lazada search results"""
        page = None
        try:
            page = await browser.new_page()
            url = f"{self.base_url}?q={query}"
            
            logger.info(f"🌐 Lazada: Navigating to {url}")
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            all_products = []
            page_index = 1
            
            while len(all_products) < max_products and page_index <= self.max_pages:
                logger.info(f"📄 Lazada: Scraping page {page_index}")
                
                # Scroll để load toàn bộ sản phẩm trên page
                await self._auto_scroll(page)
                
                # Extract products
                items = await page.query_selector_all('div[data-qa-locator="product-item"]')
                logger.info(f"   Found {len(items)} product items on page {page_index}")
                
                for item in items:
                    if len(all_products) >= max_products:
                        break
                    
                    try:
                        product_data = await item.evaluate("""
                            el => {
                                const a = el.querySelector("a");
                                const title = el.querySelector(".RfADt a")?.innerText?.trim();
                                const price = el.querySelector(".aBrP0 .ooOxS")?.innerText?.trim();
                                const img = el.querySelector("img")?.getAttribute("data-src") || el.querySelector("img")?.src;
                                
                                return {
                                    title,
                                    price,
                                    url: a?.href,
                                    image: img
                                };
                            }
                        """)
                        
                        # Validate product data
                        if product_data.get("title") and product_data.get("url"):
                            # Normalize and add source
                            product = {
                                "title": product_data["title"],
                                "price": product_data.get("price", ""),
                                "url": product_data["url"],
                                "image": product_data.get("image", ""),
                                "source": "lazada",  # ⚠️ IMPORTANT: Mark source
                                "name": product_data["title"]  # For compatibility
                            }
                            all_products.append(product)
                            logger.debug(f"   ✓ Added: {product['title'][:50]}")
                    
                    except Exception as e:
                        logger.warning(f"   ⚠️  Error extracting product: {e}")
                        continue
                
                # Try to go to next page
                if len(all_products) < max_products:
                    next_btn = await page.query_selector('li.ant-pagination-next a')
                    
                    if next_btn:
                        try:
                            logger.info(f"   Navigating to next page...")
                            await asyncio.gather(
                                next_btn.click(),
                                page.wait_for_navigation(wait_until="networkidle", timeout=self.timeout)
                            )
                            page_index += 1
                        except Exception as e:
                            logger.warning(f"   ⚠️  Could not navigate to next page: {e}")
                            break
                    else:
                        logger.info(f"   No next button found, stopping pagination")
                        break
            
            logger.info(f"✅ Lazada: Total products collected: {len(all_products)}")
            return all_products[:max_products]
        
        except Exception as e:
            logger.error(f"❌ Error crawling product list: {e}", exc_info=True)
            return []
        
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
    
    async def _auto_scroll(self, page: Page):
        """Auto-scroll page to load all products"""
        try:
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
        except Exception as e:
            logger.warning(f"Auto-scroll error: {e}")

"""
Tiki Crawler for CrawlService (ported from monolith)
Crawls products from Tiki.vn using Playwright (browser automation)
Handles JavaScript-rendered content
"""

import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
from urllib.parse import urlparse, parse_qs
import re
import logging

logger = logging.getLogger(__name__)


class TikiCrawler:
    """Tiki crawler using Playwright (browser automation)"""
    
    def __init__(self):
        self.base_url = "https://tiki.vn/search"
        self.timeout = 30000  # 30 seconds in milliseconds
    
    async def crawl(self, query: str, max_products: int = 20) -> List[Dict[str, Any]]:
        """
        Crawl products from Tiki using Playwright
        
        Args:
            query: Search query (e.g., "giày thể thao")
            max_products: Maximum number of products to crawl
        
        Returns:
            List of products
        """
        logger.info(f"🟦 Tiki: Crawling for query: {query}")
        
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
            logger.info(f"✅ Tiki: Extracted {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"❌ Tiki crawl error: {e}", exc_info=True)
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
        """Crawl product list from Tiki search results"""
        page = None
        
        try:
            page = await browser.new_page()
            
            # Set viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Set headers to look like real browser
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })
            
            # Navigate to search page
            url = f"{self.base_url}?q={query}"
            logger.info(f"🌐 Navigating to: {url}")
            
            # Wait for domcontentloaded, not networkidle (faster)
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            
            # Wait extra for JavaScript to render products
            await asyncio.sleep(2)
            
            # Wait for product selector to appear
            try:
                await page.wait_for_selector("a.product-item", timeout=10000)
                logger.info("✓ Product items found")
            except Exception as e:
                logger.warning(f"⚠️  No products found: {str(e)}")
                return []
            
            # Check if products exist before extraction
            has_products = await page.evaluate("""
                () => document.querySelectorAll('a.product-item').length > 0
            """)
            
            if not has_products:
                logger.warning("⚠️  No products on page")
                return []
            
            # Extract product data using JavaScript
            try:
                products = await page.evaluate(f"""
                    () => {{
                        const items = document.querySelectorAll('a.product-item');
                        const result = [];
                        const maxProducts = {max_products};
                        
                        for (let i = 0; i < Math.min(items.length, maxProducts); i++) {{
                            const item = items[i];
                            try {{
                                const link = item.href || '';
                                if (!link) continue;
                                
                                // Extract product_id and spid from URL
                                const urlObj = new URL(link);
                                let product_id = null;
                                let spid = null;
                                
                                // Extract product_id from path (e.g., /...p279078759.html)
                                const pathMatch = urlObj.pathname.match(/p(\\d+)/);
                                if (pathMatch) {{
                                    product_id = pathMatch[1];
                                }}
                                
                                // Extract spid from query params
                                spid = urlObj.searchParams.get('spid');
                                
                                const titleEl = item.querySelector('h3.dDeapS');
                                const title = titleEl?.innerText?.trim() || '';
                                if (!title) continue;
                                
                                const priceEl = item.querySelector('div.price-discount__price');
                                let price = priceEl?.innerText?.trim() || '0';
                                price = price.replace(/[^\\d]/g, '');
                                if (!price || price === '0') continue;
                                
                                const discountEl = item.querySelector('div.price-discount__percent');
                                let discount = discountEl?.innerText?.trim() || '0';
                                discount = discount.replace(/[^\\d]/g, '');
                                
                                const brandEl = item.querySelector('div.cUhrxa span');
                                const brand = brandEl?.innerText?.trim() || 'Unknown';
                                
                                let image = '';
                                const pictureImg = item.querySelector('picture img') || item.querySelector('img.hFEtiz');
                                if (pictureImg) {{
                                    const srcset = pictureImg.getAttribute('srcset');
                                    if (srcset) {{
                                        image = srcset.split(',')[0].split(' ')[0].trim();
                                    }} else {{
                                        image = pictureImg.src || '';
                                    }}
                                }}
                                
                                const soldEl = item.querySelector('span.quantity.has-border');
                                let sold = '0';
                                if (soldEl) {{
                                    const match = soldEl.innerText.match(/\\d+/);
                                    if (match) sold = match[0];
                                }}
                                
                                result.push({{
                                    title: title,
                                    price: parseInt(price, 10),
                                    discount: parseInt(discount, 10),
                                    brand: brand,
                                    link: link,
                                    image: image,
                                    sold: parseInt(sold, 10),
                                    source: 'tiki',
                                    product_id: product_id,
                                    spid: spid
                                }});
                            }} catch (e) {{
                                console.error('Error parsing item:', e);
                            }}
                        }}
                        
                        return result;
                    }}
                """)
                
                logger.info(f"Tiki: Extracted {len(products)} products from page")
                return products
                
            except Exception as e:
                logger.error(f"❌ Error evaluating products: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Error crawling product list: {str(e)}")
            return []
            
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")


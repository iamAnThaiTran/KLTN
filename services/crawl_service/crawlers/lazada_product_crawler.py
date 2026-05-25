"""
Lazada Product/Review Crawler - Simple version for single product crawl
Used for product comparison feature
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from datetime import datetime

logger = logging.getLogger(__name__)


class LazadaProductCrawler:
    """Lazada product crawler for single product details and reviews"""
    
    def __init__(self):
        self.base_url = "https://www.lazada.vn"
        self.timeout = 30000
    
    async def get_product_snapshot(
        self,
        product_id: str,
        product_url: Optional[str] = None,
        label: str = None
    ) -> Dict[str, Any]:
        """
        Get product snapshot (details + reviews)
        
        Args:
            product_id: Product ID
            product_url: Full product URL
            label: Product label for logging
        
        Returns:
            Product snapshot dictionary
        """
        logger.info(f"📦 Lazada: Getting snapshot for {label or product_id}")
        
        playwright = None
        browser = None
        
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage'
                ]
            )
            
            snapshot = await self._get_product_details(browser, product_url)
            logger.info(f"✅ Lazada: Snapshot created for {snapshot.get('name', 'Unknown')[:50]}")
            return snapshot
        
        except Exception as e:
            logger.error(f"❌ Lazada product crawl error: {e}", exc_info=True)
            return {
                "name": label or f"Product {product_id}",
                "source": "lazada",
                "product_id": product_id,
                "error": str(e),
                "status": "error"
            }
        
        finally:
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
    
    async def _get_product_details(self, browser, product_url: str) -> Dict[str, Any]:
        """Get product details from Lazada"""
        page = None
        
        try:
            page = await browser.new_page()
            
            logger.info(f"🌐 Navigating to {product_url}")
            await page.goto(product_url, wait_until="domcontentloaded", timeout=self.timeout)
            
            # Extract product details
            details = await page.evaluate("""
                () => {
                    const result = {
                        name: "",
                        price: "",
                        brand: "",
                        rating: "",
                        reviews_count: 0,
                        description: "",
                        images: [],
                        sizes: [],
                        colors: [],
                        availability: "unknown"
                    };
                    
                    // Product name
                    const nameEl = document.querySelector("h1.pdp-product-title__text");
                    if (nameEl) {
                        result.name = nameEl.innerText?.trim() || "";
                    }
                    
                    // Price
                    const priceEl = document.querySelector(".pdp-price__value");
                    if (priceEl) {
                        result.price = priceEl.innerText?.trim() || "";
                    }
                    
                    // Brand
                    const brandEl = document.querySelector(".pdp-product-brand-v2__brand-link");
                    if (brandEl) {
                        result.brand = brandEl.innerText?.trim() || "";
                    }
                    
                    // Rating
                    const ratingEl = document.querySelector(".pdp-review-summary__rating");
                    if (ratingEl) {
                        result.rating = ratingEl.innerText?.trim() || "";
                    }
                    
                    // Review count
                    const reviewsEl = document.querySelector(".pdp-review-summary__count");
                    if (reviewsEl) {
                        const text = reviewsEl.innerText?.trim() || "0";
                        const match = text.match(/\\d+/);
                        result.reviews_count = match ? parseInt(match[0]) : 0;
                    }
                    
                    // Images
                    document.querySelectorAll(".pdp-image-container img").forEach(img => {
                        const src = img.src || img.getAttribute("data-src");
                        if (src && !src.includes("placeholder")) {
                            result.images.push(src);
                        }
                    });
                    
                    // Availability
                    const stockEl = document.querySelector(".stock-info");
                    if (stockEl) {
                        const text = stockEl.innerText?.toLowerCase() || "";
                        result.availability = text.includes("available") ? "in_stock" : "out_of_stock";
                    }
                    
                    return result;
                }
            """)
            
            return {
                "name": details.get("name", "Unknown"),
                "source": "lazada",
                "price": details.get("price", ""),
                "brand": details.get("brand", ""),
                "rating": details.get("rating", ""),
                "reviews_count": details.get("reviews_count", 0),
                "description": details.get("description", ""),
                "images": details.get("images", []),
                "attributes": {
                    "sizes": details.get("sizes", []),
                    "colors": details.get("colors", [])
                },
                "availability": details.get("availability", "unknown"),
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error getting product details: {e}", exc_info=True)
            raise
        
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")


# Singleton instance
_lazada_crawler: Optional[LazadaProductCrawler] = None


async def get_lazada_crawler() -> LazadaProductCrawler:
    """Get singleton LazadaProductCrawler instance"""
    global _lazada_crawler
    if _lazada_crawler is None:
        _lazada_crawler = LazadaProductCrawler()
    return _lazada_crawler


async def close_lazada_crawler():
    """Close the singleton crawler"""
    global _lazada_crawler
    _lazada_crawler = None

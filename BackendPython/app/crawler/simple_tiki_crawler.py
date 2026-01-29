"""
Simple Tiki Crawler using httpx (không cần Playwright)
Lightweight alternative for Python 3.14
"""

import httpx
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class SimpleTikiCrawler:
    """Tiki crawler using httpx + BeautifulSoup (no Playwright needed)"""
    
    def __init__(self):
        self.base_url = "https://tiki.vn/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    
    def crawl(self, query: str, max_products: int = 20) -> List[Dict[str, Any]]:
        """
        Crawl products from Tiki
        
        Args:
            query: Search query (e.g., "giày thể thao")
            max_products: Maximum number of products to crawl
        
        Returns:
            List of products
        """
        logger.info(f"🔍 Crawling Tiki for: {query}")
        
        try:
            # Build URL
            params = {"q": query}
            
            # Make request
            with httpx.Client(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find product items
                products = []
                product_items = soup.select('a[data-view-id="product_list_container"]')
                
                if not product_items:
                    # Try alternative selectors
                    product_items = soup.select('a.product-item')
                
                logger.info(f"Found {len(product_items)} product elements")
                
                for item in product_items[:max_products]:
                    try:
                        product = self._extract_product(item)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Error extracting product: {e}")
                        continue
                
                logger.info(f"✅ Successfully extracted {len(products)} products")
                return products
                
        except Exception as e:
            logger.error(f"❌ Crawl error: {e}")
            return []
    
    def _extract_product(self, item) -> Optional[Dict[str, Any]]:
        """Extract product data from HTML element"""
        try:
            # Get link
            link = item.get('href', '')
            if link and not link.startswith('http'):
                link = 'https://tiki.vn' + link
            
            if not link:
                return None
            
            # Get title
            title_el = item.select_one('h3, div[class*="title"], span[class*="name"]')
            title = title_el.get_text(strip=True) if title_el else ''
            
            if not title:
                return None
            
            # Get price
            price_el = item.select_one('div[class*="price"], span[class*="price"]')
            price_text = price_el.get_text(strip=True) if price_el else '0'
            
            # Extract numbers only
            price_numbers = re.sub(r'[^\d]', '', price_text)
            price = int(price_numbers) if price_numbers else 0
            
            if price == 0:
                return None
            
            # Get brand
            brand_el = item.select_one('span[class*="brand"], div[class*="brand"]')
            brand = brand_el.get_text(strip=True) if brand_el else 'Unknown'
            
            # Get image
            img_el = item.select_one('img')
            image = ''
            if img_el:
                # Try srcset first
                srcset = img_el.get('srcset', '')
                if srcset:
                    image = srcset.split(',')[0].split(' ')[0].strip()
                else:
                    image = img_el.get('src', '')
            
            # Get discount
            discount_el = item.select_one('div[class*="discount"], span[class*="discount"]')
            discount_text = discount_el.get_text(strip=True) if discount_el else '0'
            discount_numbers = re.sub(r'[^\d]', '', discount_text)
            discount = int(discount_numbers) if discount_numbers else 0
            
            # Get sold count
            sold_el = item.select_one('span[class*="sold"], div[class*="quantity"]')
            sold_text = sold_el.get_text(strip=True) if sold_el else '0'
            sold_numbers = re.sub(r'[^\d]', '', sold_text)
            sold = int(sold_numbers) if sold_numbers else 0
            
            return {
                'title': title,
                'price': price,
                'brand': brand,
                'link': link,
                'image': image,
                'source': 'tiki',
                'discount': discount,
                'sold': sold
            }
            
        except Exception as e:
            logger.error(f"Extract error: {e}")
            return None


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    crawler = SimpleTikiCrawler()
    products = crawler.crawl("giày thể thao", max_products=5)
    
    print(f"\n✅ Crawled {len(products)} products:")
    for i, p in enumerate(products, 1):
        print(f"\n{i}. {p['title'][:60]}...")
        print(f"   Price: {p['price']:,} VNĐ")
        print(f"   Brand: {p['brand']}")
        print(f"   Link: {p['link'][:50]}...")

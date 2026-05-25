"""
Lazada Product Detail Crawler - Pure API approach with real cookies

This version doesn't need browser interception.
Just use real cookies from your browser to call the API directly.

Steps:
1. Get cookies from your browser DevTools
2. Create API instance with those cookies
3. Call the API directly to get product details

Much faster and simpler!
"""

import asyncio
import logging
import json
import time
import random
import httpx
import hashlib
import urllib.parse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LazadaAPIConfig:
    """Configuration for Lazada API calls."""
    cookies_str: str  # Cookie string from browser (separated by ";")
    user_agent: Optional[str] = None
    timeout: float = 30.0
    base_api_url: str = "https://acs-m.lazada.vn/h5/mtop.global.detail.web.getdetailinfo/1.0/"


class LazadaAPIPureCrawler:
    """
    Pure API-based Lazada crawler - no browser needed!
    Just use cookies from your browser to call Lazada API directly.
    """

    def __init__(self, config: LazadaAPIConfig):
        self.config = config
        self.timeout = config.timeout
        self.api_url = config.base_api_url
        
        # Default user agent if not provided
        if not config.user_agent:
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
        else:
            self.user_agent = config.user_agent
        
        # Parse cookies string into dict
        self.cookies = self._parse_cookies(config.cookies_str)
        
        # Rate limiting
        self.last_request_time: float = 0
        self.min_request_interval: float = 2.0
        self.max_request_interval: float = 5.0
        
        logger.info(f"🆕 LazadaAPIPureCrawler initialized")
        logger.debug(f"   Cookies: {len(self.cookies)} parsed")
        logger.debug(f"   User-Agent: {self.user_agent[:60]}...")

    @staticmethod
    def _parse_cookies(cookie_str: str) -> Dict[str, str]:
        """Parse cookie string into dictionary."""
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                cookies[key.strip()] = value.strip()
        return cookies

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        target = random.uniform(self.min_request_interval, self.max_request_interval)
        wait = target - elapsed
        
        if wait > 0:
            logger.debug(f"⏳ Rate limit: wait {wait:.1f}s")
            await asyncio.sleep(wait)
        
        self.last_request_time = time.time()

    def _calculate_signature(self, data_str: str, timestamp: str) -> str:
        """
        Calculate MD5 signature for Lazada API.
        
        Formula: sign = md5(token&t&appKey&data)
        
        Args:
            data_str: JSON data string (URL encoded)
            timestamp: Current timestamp in milliseconds
        
        Returns:
            MD5 hash string
        """
        try:
            # Extract token from _m_h5_tk cookie
            if "_m_h5_tk" not in self.cookies:
                logger.warning("⚠️  _m_h5_tk cookie not found, using default token")
                token = "defaulttoken"
            else:
                token = self.cookies["_m_h5_tk"].split("_")[0]
            
            app_key = "24677475"
            
            # Build raw string: token&t&appKey&data
            raw = f"{token}&{timestamp}&{app_key}&{data_str}"
            logger.debug(f"🔐 Raw signature string: {raw[:100]}...")
            
            # Calculate MD5
            signature = hashlib.md5(raw.encode()).hexdigest()
            logger.debug(f"🔐 Signature: {signature}")
            
            return signature
        except Exception as e:
            logger.error(f"❌ Error calculating signature: {e}")
            return ""

    async def _get_product_detail_api(self, item_id: str, product_url: str = "") -> Dict[str, Any]:
        """
        Call Lazada detail API to get product information.
        
        Args:
            item_id: The product item ID (numeric)
            product_url: The product page URL
        
        Returns:
            API response or error dict
        """
        await self._rate_limit()

        try:
            # Generate timestamp in milliseconds
            timestamp = str(int(time.time() * 1000))
            
            # Build data payload
            data_payload = {
                "deviceType": "pc",
                "path": product_url or f"https://www.lazada.vn/products/{item_id}.html",
                "uri": f"pdp-i{item_id}",
                "headerParams": json.dumps({
                    "user-agent": self.user_agent
                }),
                "cookieParams": json.dumps({
                    key: value for key, value in self.cookies.items()
                }),
                "requestParams": json.dumps({})
            }
            
            # Convert data to JSON string
            data_str = json.dumps(data_payload, ensure_ascii=False)
            logger.debug(f"📦 Data payload: {data_str[:200]}...")
            
            # Calculate signature
            signature = self._calculate_signature(data_str, timestamp)
            
            # Build request headers
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.lazada.vn",
                "Referer": "https://www.lazada.vn/",
                "Cookie": "; ".join([f"{k}={v}" for k, v in self.cookies.items()]),
            }

            # Build request parameters
            params = {
                "jsv": "2.6.1",
                "appKey": "24677475",
                "t": timestamp,
                "sign": signature,
                "api": "mtop.global.detail.web.getDetailInfo",
                "v": "1.0",
                "type": "originaljson",
                "isSec": "1",
                "AntiCreep": "true",
                "timeout": "20000",
                "dataType": "json",
                "sessionOption": "AutoLoginOnly",
                "x-i18n-language": "en",
                "x-i18n-regionID": "VN",
                "data": data_str,
                "appkey": "24677475",
            }

            logger.debug(f"🌐 Calling API for item_id={item_id} with timestamp={timestamp}...")
            logger.debug(f"   Sign: {signature}")

            # Make request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    data=params,
                    headers=headers,
                    follow_redirects=True,
                )

            logger.debug(f"   Response status: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"⚠️  API returned {response.status_code}")
                return {"status": "error", "error": f"HTTP {response.status_code}"}

            # Try to parse JSON
            try:
                data = response.json()
                logger.debug(f"✅ API response received")
                return {"status": "success", "data": data}
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse JSON: {e}")
                logger.debug(f"   Response preview: {response.text[:200]}")
                return {"status": "error", "error": f"Failed to parse: {str(e)}"}

        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            return {"status": "error", "error": str(e)}

    def _parse_api_response(self, api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse API response and extract product data."""
        try:
            if not isinstance(api_data, dict):
                logger.warning("⚠️  API data is not a dict")
                return None

            # Get response status
            ret = api_data.get("ret", [])
            if ret and "SUCCESS" not in ret[0]:
                logger.warning(f"⚠️  API returned error: {ret}")
                return None

            # Parse module data (it's a JSON string)
            module_str = api_data.get("data", {}).get("module", "{}")
            try:
                module_data = json.loads(module_str)
            except:
                logger.warning("⚠️  Failed to parse module JSON")
                return None

            # Extract product info
            product_info = module_data.get("product", {})
            if not product_info:
                logger.warning("⚠️  No 'product' found in module")
                return None

            # Extract specifications
            specs = {}
            specifications = module_data.get("specifications", {})
            if specifications:
                # Get first SKU's specs (all SKUs should have similar specs)
                first_sku_specs = next(iter(specifications.values()), {})
                specs = first_sku_specs.get("features", {})

            # Extract basic product info
            product_data = {
                "name": product_info.get("title", ""),
                "brand": product_info.get("brand", {}).get("name", ""),
                "description": product_info.get("desc", ""),
                "rating": product_info.get("rating", {}).get("score", ""),
                "reviews_count": product_info.get("rating", {}).get("total", 0),
                "specifications": specs,
            }

            # Extract SKU info (prices, availability, etc.)
            sku_infos = module_data.get("skuInfos", {})
            if sku_infos:
                sku_list = []
                for sku_id, sku_data in sku_infos.items():
                    price_info = sku_data.get("price", {})
                    sku_list.append({
                        "sku_id": sku_id,
                        "price": price_info.get("salePrice", {}).get("value", 0),
                        "original_price": price_info.get("originalPrice", {}).get("value", 0),
                        "discount": price_info.get("discount", ""),
                        "seller_id": sku_data.get("sellerId", ""),
                        "item_id": sku_data.get("itemId", ""),
                    })
                product_data["skus"] = sku_list

            # Extract seller info
            seller_data = module_data.get("seller", {})
            if seller_data:
                product_data["seller"] = {
                    "name": seller_data.get("name", ""),
                    "seller_id": seller_data.get("sellerId", ""),
                    "shop_id": seller_data.get("shopId", ""),
                    "rating": seller_data.get("positiveSellerRating", {}).get("value", ""),
                }

            logger.info(f"✅ Successfully parsed product data")
            return product_data

        except Exception as e:
            logger.error(f"❌ Error parsing API response: {e}", exc_info=True)
            return None

    def _extract_attributes(self, product_data: Dict[str, Any]) -> Dict[str, str]:
        """Convert specs to attribute dictionary."""
        attributes = {}
        for spec in product_data.get("specs", []):
            key = spec.get("name", "").lower().replace(" ", "_")
            value = spec.get("value", "")
            if key and value:
                attributes[key] = value
        return attributes

    async def crawl_product_details(
        self,
        product_url: str,
        product_id: str,
    ) -> Dict[str, Any]:
        """
        Crawl product details using pure API approach.
        
        Args:
            product_url: Product URL (used to extract item_id if not in product_id)
            product_id: Product identifier
        
        Returns:
            Result dictionary with product data
        """
        try:
            # Extract item_id from URL or use product_id if it's numeric
            import re
            if product_id.isdigit():
                item_id = product_id
            else:
                # Try to extract from URL: /products/pdp-i{ITEM_ID}-s{SKU_ID}.html
                # First try the pdp-i pattern
                match = re.search(r"pdp-i(\d+)", product_url)
                if match:
                    item_id = match.group(1)
                else:
                    # Fallback: try to extract just numbers
                    match = re.search(r"/products/(\d+)", product_url)
                    if match:
                        item_id = match.group(1)
                    else:
                        return {
                            "status": "error",
                            "product_id": product_id,
                            "error": f"Cannot extract item_id from: {product_url}"
                        }

            logger.info(f"📥 Crawling: {product_id} (item_id={item_id})")

            # Call API with URL
            result = await self._get_product_detail_api(item_id, product_url)

            if result["status"] == "error":
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": result["error"]
                }

            # Parse response
            api_data = result.get("data", {})
            product_data = self._parse_api_response(api_data)

            if not product_data:
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": "Failed to parse API response"
                }

            logger.info(f"✅ Success: {product_data.get('name', 'N/A')[:60]}")

            return {
                "status": "success",
                "product_id": product_id,
                "product": product_data,
                "extracted_attributes": self._extract_attributes(product_data),
                "extraction_method": "api_pure",
            }

        except Exception as e:
            logger.error(f"❌ crawl_product_details failed: {e}", exc_info=True)
            return {
                "status": "error",
                "product_id": product_id,
                "error": str(e)
            }

    async def crawl_multiple_products(
        self,
        product_urls: List[str],
        product_ids: List[str],
        max_concurrent: int = 2,
    ) -> List[Dict[str, Any]]:
        """Crawl multiple products with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl(url: str, pid: str):
            async with semaphore:
                return await self.crawl_product_details(url, pid)

        logger.info(f"📥 Crawling {len(product_urls)} products (concurrent={max_concurrent})")

        results = await asyncio.gather(
            *[_crawl(url, pid) for url, pid in zip(product_urls, product_ids)],
            return_exceptions=False,
        )

        success = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"✅ Done: {success}/{len(results)} succeeded")

        return list(results)


# ============================================================================
# Standalone function
# ============================================================================

async def crawl_with_cookies(
    product_url: str,
    product_id: str,
    cookies_str: str,
) -> Dict[str, Any]:
    """
    Crawl product using provided cookies.
    
    Args:
        product_url: Product URL
        product_id: Product ID
        cookies_str: Cookies string from browser (name=value; name=value; ...)
    
    Returns:
        Result dictionary
    """
    config = LazadaAPIConfig(cookies_str=cookies_str)
    crawler = LazadaAPIPureCrawler(config)
    return await crawler.crawl_product_details(product_url, product_id)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("""
🚀 Lazada Pure API Crawler

Usage:
    python lazada_api_pure_crawler.py <product_url> <cookies_string>

Example:
    python lazada_api_pure_crawler.py \\
        "https://www.lazada.vn/products/123456-shop.html" \\
        "cookie1=value1; cookie2=value2; ..."

How to get cookies from browser:
    1. Open https://www.lazada.vn/products/YOUR_PRODUCT_ID.html
    2. Open DevTools (F12) → Application → Cookies
    3. Copy all cookies and paste them here
    """)

    if len(sys.argv) < 3:
        print("❌ Missing arguments. See usage above.")
        sys.exit(1)

    product_url = sys.argv[1]
    cookies_str = sys.argv[2]
    product_id = product_url.split("/")[-1].split(".")[0]

    result = asyncio.run(crawl_with_cookies(product_url, product_id, cookies_str))
    print(json.dumps(result, indent=2, ensure_ascii=False))

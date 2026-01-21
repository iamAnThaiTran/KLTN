import asyncio
import json
import re
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urlparse, parse_qs
from playwright.async_api import async_playwright, Page, Browser
import logging

# FIX cho Windows event loop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TikiCrawler:
    """
    Tiki Platform Crawler với khả năng filter theo attributes
    Crawls product data from Tiki.vn with attribute filtering
    """

    def __init__(self):
        self.base_url = "https://tiki.vn/search?q="
        self.config = {
            "timeout": 15000,
            "max_products": 30,  # Số sản phẩm tối đa để crawl detail
            "concurrent_details": 3,  # Số sản phẩm crawl detail đồng thời
        }

    async def crawl(
        self, 
        category: str, 
        attributes: Optional[Dict[str, Any]] = None,
        get_details: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Crawl sản phẩm với filter theo attributes
        
        Args:
            category: Tên danh mục/sản phẩm cần tìm (vd: "giày thể thao", "bột giặt")
            attributes: Dict chứa các thuộc tính cần filter
                {
                    "size": ["39", "40", "41"],
                    "mau_sac": ["đen", "trắng"],
                    "chat_lieu": ["da", "vải"],
                    "loai": "bột"  # Cho trường hợp đơn giản như bột giặt
                }
            get_details: Có crawl chi tiết hay không (mặc định True nếu có attributes phức tạp)
        
        Returns:
            List các sản phẩm đã được filter
        """
        attributes = attributes or {}
        browser = None
        playwright = None
        
        try:
            # Tự động quyết định có cần crawl detail không
            needs_detail = self._needs_detail_crawl(attributes)
            if not needs_detail:
                get_details = False
            
            logger.info("=" * 60)
            logger.info(f"🔍 Bắt đầu crawl: '{category}'")
            logger.info(f"📋 Attributes: {json.dumps(attributes, ensure_ascii=False)}")
            logger.info(f"🔧 Get details: {get_details}")
            logger.info("=" * 60)
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',  # Tránh phát hiện bot
                    '--disable-dev-shm-usage',
                    '--disable-web-security'
                ]
            )
            
            # Bước 1: Tối ưu search query
            search_query = self._build_search_query(category, attributes)
            logger.info(f"🔎 Search query: '{search_query}'")
            
            # Bước 2: Crawl danh sách sản phẩm
            products = await self._crawl_product_list(browser, search_query)
            logger.info(f"✅ Tìm thấy {len(products)} sản phẩm\n")
            
            if len(products) == 0:
                return []
            
            # Bước 3: Filter đơn giản từ title (cho các attributes đơn giản)
            if not get_details:
                filtered = self._filter_by_title(products, attributes)
                logger.info(f"✅ Sau khi filter từ title: {len(filtered)} sản phẩm")
                return filtered
            
            # Bước 4: Crawl chi tiết và filter (cho attributes phức tạp)
            detailed_products = await self._crawl_product_details(
                browser, products, attributes
            )
            
            # Bước 5: Filter theo attributes
            filtered = self._filter_by_attributes(detailed_products, attributes)
            
            logger.info("\n" + "=" * 60)
            logger.info(f"✅ Hoàn thành!")
            logger.info(f"📊 Tổng sản phẩm tìm thấy: {len(products)}")
            logger.info(f"✔️  Sản phẩm đạt yêu cầu: {len(filtered)}")
            logger.info(f"❌ Sản phẩm không đạt: {len(products) - len(filtered)}")
            logger.info("=" * 60 + "\n")
            
            return filtered
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi crawl: {str(e)}", exc_info=True)
            return []
            
        finally:
            # Đảm bảo đóng browser và playwright
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logger.warning(f"Lỗi khi đóng browser: {e}")
            
            if playwright:
                try:
                    await playwright.stop()
                except Exception as e:
                    logger.warning(f"Lỗi khi stop playwright: {e}")

    def _needs_detail_crawl(self, attributes: Dict) -> bool:
        """Kiểm tra có cần crawl detail không"""
        # Các attributes phức tạp cần crawl detail
        complex_attrs = ["size", "mau_sac", "chat_lieu", "sizes", "colors", "materials"]
        return any(key in attributes for key in complex_attrs)

    def _build_search_query(self, category: str, attributes: Dict) -> str:
        """
        Build search query tối ưu
        - Nếu user mention brand → thêm vào query
        - Nếu user mention loai → thêm vào query
        - Category luôn có
        """
        query_parts = [category]
        
        # Thêm brand nếu user specify (ví dụ: "giày nike")
        if "brand" in attributes and attributes["brand"]:
            query_parts.append(str(attributes["brand"]))
        
        # Thêm loai/type nếu có (ví dụ: "giày chạy bộ")
        if "loai" in attributes and attributes["loai"]:
            query_parts.append(str(attributes["loai"]))
        
        return " ".join(query_parts)

    def _filter_by_title(self, products: List[Dict], attributes: Dict) -> List[Dict]:
        """Filter đơn giản dựa trên title (cho bột giặt, nước giặt, etc)"""
        if not attributes:
            return products
        
        filtered = []
        for product in products:
            title_lower = product["title"].lower()
            
            # Check "loai" attribute
            if "loai" in attributes:
                loai = str(attributes["loai"]).lower()
                if loai in title_lower:
                    filtered.append(product)
                    continue
            
            # Nếu không có filter đặc biệt, giữ lại
            if not any(k in attributes for k in ["loai", "kieu", "dang"]):
                filtered.append(product)
        
        return filtered if filtered else products

    async def _crawl_product_list(self, browser: Browser, query: str) -> List[Dict]:
        """Crawl danh sách sản phẩm (không chi tiết)"""
        page = None
        
        try:
            page = await browser.new_page()
            
            # Set viewport để giống real browser
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Set nhiều headers để tránh bị block
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })
            
            url = f"https://tiki.vn/search?q={query}"
            logger.info(f"🌐 Truy cập: {url}")
            
            # QUAN TRỌNG: Đổi wait_until từ "networkidle" sang "domcontentloaded"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Đợi thêm 2 giây cho JS render
            await asyncio.sleep(2)
            
            try:
                await page.wait_for_selector("a.product-item", timeout=10000)
                logger.info("✓ Đã tìm thấy product items")
            except Exception as e:
                logger.warning(f"⚠️  Không tìm thấy sản phẩm: {str(e)}")
                # Screenshot để debug
                try:
                    await page.screenshot(path="debug_tiki.png")
                    logger.info("📸 Đã lưu screenshot debug_tiki.png")
                except:
                    pass
                return []
            
            # Kiểm tra xem có sản phẩm không trước khi evaluate
            has_products = await page.evaluate("""
                () => document.querySelectorAll('a.product-item').length > 0
            """)
            
            if not has_products:
                logger.warning("⚠️  Không có sản phẩm nào trên trang")
                return []
            
            # Extract products với error handling tốt hơn
            try:
                products = await page.evaluate("""
                    () => {
                        try {
                            const items = document.querySelectorAll('a.product-item');
                            const result = [];
                            
                            items.forEach((item, index) => {
                                try {
                                    const link = item.href || '';
                                    if (!link) return;
                                    
                                    const titleEl = item.querySelector('h3.dDeapS');
                                    const title = titleEl?.innerText?.trim() || '';
                                    if (!title) return;
                                    
                                    const priceEl = item.querySelector('div.price-discount__price');
                                    let price = priceEl?.innerText?.trim() || '0';
                                    price = price.replace(/[^\\d]/g, '');
                                    if (!price || price === '0') return;
                                    
                                    const discountEl = item.querySelector('div.price-discount__percent');
                                    let discount = discountEl?.innerText?.trim() || '0';
                                    discount = discount.replace(/[^\\d]/g, '');
                                    
                                    const brandEl = item.querySelector('div.cUhrxa span');
                                    const brand = brandEl?.innerText?.trim() || 'Unknown';
                                    
                                    let image = '';
                                    const pictureImg = item.querySelector('picture img') || item.querySelector('img.hFEtiz');
                                    if (pictureImg) {
                                        const srcset = pictureImg.getAttribute('srcset');
                                        if (srcset) {
                                            image = srcset.split(',')[0].split(' ')[0].trim();
                                        } else {
                                            image = pictureImg.src || '';
                                        }
                                    }
                                    
                                    const soldEl = item.querySelector('span.quantity.has-border');
                                    let sold = '0';
                                    if (soldEl) {
                                        const match = soldEl.innerText.match(/\\d+/);
                                        if (match) sold = match[0];
                                    }
                                    
                                    result.push({
                                        title: title,
                                        price: parseInt(price, 10),
                                        discount: parseInt(discount, 10),
                                        brand: brand,
                                        link: link,
                                        image: image,
                                        sold: parseInt(sold, 10),
                                        source: 'tiki'
                                    });
                                } catch (itemErr) {
                                    console.error('Error parsing item:', itemErr);
                                }
                            });
                            
                            return result;
                        } catch (err) {
                            console.error('Error in evaluate:', err);
                            return [];
                        }
                    }
                """)
                
                logger.info(f"✅ Đã extract {len(products)} sản phẩm")
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi evaluate: {str(e)}")
                return []
            
            return products[:self.config["max_products"]]
            
        except Exception as e:
            logger.error(f"❌ Lỗi crawl product list: {str(e)}")
            # Thử screenshot nếu có thể
            if page:
                try:
                    await page.screenshot(path="debug_error.png")
                    logger.info("📸 Đã lưu screenshot lỗi: debug_error.png")
                except:
                    pass
            return []
            
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Lỗi đóng page: {e}")

    async def _crawl_product_details(
        self, 
        browser: Browser, 
        products: List[Dict],
        attributes: Dict
    ) -> List[Dict]:
        """Crawl chi tiết từng sản phẩm (parallel processing)"""
        logger.info(f"📦 Bắt đầu crawl chi tiết {len(products)} sản phẩm...")
        
        results = []
        concurrent = self.config["concurrent_details"]
        
        # Xử lý theo batch
        for i in range(0, len(products), concurrent):
            batch = products[i:i + concurrent]
            
            tasks = []
            for idx, product in enumerate(batch):
                product_num = i + idx + 1
                tasks.append(
                    self._extract_single_product_detail(
                        browser, product, product_num, len(products), attributes
                    )
                )
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
        
        logger.info(f"✅ Đã crawl chi tiết xong {len(results)} sản phẩm\n")
        return results

    async def _extract_single_product_detail(
        self,
        browser: Browser,
        product: Dict,
        product_num: int,
        total: int,
        attributes: Dict
    ) -> Dict:
        """Extract chi tiết 1 sản phẩm"""
        logger.info(f"  [{product_num}/{total}] Crawling: {product['title'][:50]}...")
        
        detail = await self._extract_product_detail(browser, product)
        
        if detail:
            match_info = self._check_attribute_match(detail, attributes)
            logger.info(f"    ✓ {match_info['emoji']} {match_info['summary']}")
            
            return {
                **product,
                "attributes": detail,
                "match_info": match_info
            }
        
        logger.info(f"    ⚠️  Không lấy được chi tiết")
        return {
            **product,
            "attributes": None,
            "match_info": {"matched": False, "reason": "No details available"}
        }

    async def _extract_product_detail(self, browser: Browser, product: Dict) -> Optional[Dict]:
        """Extract chi tiết sản phẩm từ API"""
        page = None
        
        try:
            page = await browser.new_page()
            
            # Lấy productId từ URL
            product_id = None
            spid = None
            
            try:
                parsed = urlparse(product["link"])
                query_params = parse_qs(parsed.query)
                spid = query_params.get("spid", [None])[0]
                
                match = re.search(r'p(\d+)', parsed.path)
                if match:
                    product_id = match.group(1)
            except:
                pass
            
            if not product_id:
                return None
            
            # Gọi Tiki API
            api_params = {
                "platform": "web",
                "version": "3"
            }
            if spid:
                api_params["spid"] = spid
            
            api_url = f"https://tiki.vn/api/v2/products/{product_id}?{urlencode(api_params)}"
            
            await page.set_extra_http_headers({
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            # Đổi wait_until để tránh timeout
            response = await page.goto(api_url, wait_until="domcontentloaded", timeout=30000)
            
            if not response or not response.ok:
                return None
            
            raw = await response.text()
            data = json.loads(raw)
            
            result = self._parse_product_attributes(data)
            
            return result
            
        except Exception as e:
            logger.warning(f"Lỗi extract detail: {str(e)}")
            return None
            
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Lỗi đóng page detail: {e}")

    def _parse_product_attributes(self, data: Dict) -> Dict:
        """Parse attributes từ API response"""
        def normalize(s: str) -> str:
            import unicodedata
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return s.lower().strip()
        
        result = {
            "sizes": [],
            "colors": [],
            "materials": [],
            "brand": data.get("brand", {}).get("name", "Unknown"),
            "category": data.get("categories", {}).get("name", ""),
            "stock": data.get("inventory_status") == "available"
        }
        
        # DEBUG: In ra configurable_options
        config_opts = data.get("configurable_options", [])
        if config_opts:
            logger.info(f"    DEBUG configurable_options: {[opt.get('name') for opt in config_opts]}")
        
        # Lấy từ configurable_options (Size, Color)
        for opt in config_opts:
            label = normalize(opt.get("name", ""))
            values = [v.get("label") for v in opt.get("values", []) if v.get("label")]
            
            if re.search(r"size|kich co|kich thuoc", label):
                result["sizes"] = values
            if re.search(r"mau|mau sac|color|colour", label):
                result["colors"] = values
        
        # DEBUG: In ra specifications
        specs = data.get("specifications", [])
        if specs:
            logger.info(f"    DEBUG specifications count: {len(specs)}")
            for group in specs[:1]:  # In chi group đầu tiên
                attrs = group.get("attributes", [])
                logger.info(f"      Group: {group.get('name')} - attrs: {[(a.get('name'), a.get('value')) for a in attrs[:3]]}")
        
        # Lấy từ specifications (Material)
        for group in specs:
            for attr in group.get("attributes", []):
                key = normalize(attr.get("code", "") or attr.get("name", ""))
                value = str(attr.get("value", "")).strip()
                
                if value and re.search(r"chat lieu|material|vat lieu", key):
                    result["materials"].append(value)
        
        # Loại trùng
        result["sizes"] = list(set(result["sizes"]))
        result["colors"] = list(set(result["colors"]))
        result["materials"] = list(set(result["materials"]))
        
        return result

    def _check_attribute_match(self, product_attrs: Dict, filter_attrs: Dict) -> Dict:
        """Kiểm tra sản phẩm có match với filters không"""
        matches = []
        mismatches = []
        
        def normalize(s: str) -> str:
            import unicodedata
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return s.lower().strip()
        
        # Check sizes
        filter_sizes = filter_attrs.get("size") or filter_attrs.get("sizes") or []
        if filter_sizes:
            if not isinstance(filter_sizes, list):
                filter_sizes = [filter_sizes]
            
            has_size = any(
                any(str(size).lower() in s.lower() for s in product_attrs["sizes"])
                for size in filter_sizes
            )
            
            if has_size:
                matches.append(f"Size: {', '.join(map(str, filter_sizes))}")
            else:
                mismatches.append(f"Size không có: {', '.join(map(str, filter_sizes))}")
        
        # Check colors
        filter_colors = filter_attrs.get("mau_sac") or filter_attrs.get("colors") or []
        if filter_colors:
            if not isinstance(filter_colors, list):
                filter_colors = [filter_colors]
            
            has_color = any(
                any(normalize(color) in normalize(c) for c in product_attrs["colors"])
                for color in filter_colors
            )
            
            if has_color:
                matches.append(f"Màu: {', '.join(filter_colors)}")
            else:
                mismatches.append(f"Màu không có: {', '.join(filter_colors)}")
        
        # Check materials
        filter_materials = filter_attrs.get("chat_lieu") or filter_attrs.get("materials") or []
        if filter_materials:
            if not isinstance(filter_materials, list):
                filter_materials = [filter_materials]
            
            has_material = any(
                any(normalize(mat) in normalize(m) for m in product_attrs["materials"])
                for mat in filter_materials
            )
            
            if has_material:
                matches.append(f"Chất liệu: {', '.join(filter_materials)}")
            else:
                mismatches.append(f"Chất liệu không có: {', '.join(filter_materials)}")
        
        matched = len(mismatches) == 0 and len(matches) > 0
        
        return {
            "matched": matched,
            "matches": matches,
            "mismatches": mismatches,
            "emoji": "✅" if matched else "❌",
            "summary": f"Đạt: {' | '.join(matches)}" if matched else f"Không đạt: {' | '.join(mismatches)}"
        }

    def _filter_by_attributes(self, products: List[Dict], attributes: Dict) -> List[Dict]:
        """Filter products theo attributes"""
        # Nếu không có filter phức tạp, trả về tất cả
        if not any(k in attributes for k in ["size", "sizes", "mau_sac", "colors", "chat_lieu", "materials"]):
            return products
        
        return [
            p for p in products 
            if p.get("attributes") and p.get("match_info", {}).get("matched", False)
        ]


# ===== CÁCH SỬ DỤNG =====

async def main():
    """Example usage"""
    crawler = TikiCrawler()
    
    # Example 1: Giày thể thao size 39-40, màu đen/trắng
    print("\n" + "="*60)
    print("Example 1: Giày thể thao")
    print("="*60)
    products1 = await crawler.crawl(
        category="giày thể thao nam",
        attributes={
            "size": ["39", "40"],
            "mau_sac": ["đen", "trắng"]
        }
    )
    
    for i, p in enumerate(products1[:5], 1):
        print(f"\n{i}. {p['title']}")
        print(f"   💰 Giá: {p['price']:,}đ")
        if p.get('attributes'):
            print(f"   👟 Sizes: {', '.join(p['attributes']['sizes'])}")
            print(f"   🎨 Màu: {', '.join(p['attributes']['colors'])}")
    
    # Example 2: Bột giặt (không cần crawl detail)
    print("\n" + "="*60)
    print("Example 2: Bột giặt")
    print("="*60)
    products2 = await crawler.crawl(
        category="bột giặt",
        attributes={
            "loai": "bột"  # Filter đơn giản từ title
        }
    )
    
    for i, p in enumerate(products2[:5], 1):
        print(f"\n{i}. {p['title']}")
        print(f"   💰 Giá: {p['price']:,}đ")
    
    # Example 3: Áo khoác da
    print("\n" + "="*60)
    print("Example 3: Áo khoác da")
    print("="*60)
    products3 = await crawler.crawl(
        category="áo khoác nam",
        attributes={
            "chat_lieu": ["da", "da thật"],
            "size": ["L", "XL"]
        }
    )
    
    for i, p in enumerate(products3[:3], 1):
        print(f"\n{i}. {p['title']}")
        print(f"   💰 Giá: {p['price']:,}đ")
        if p.get('attributes'):
            print(f"   📏 Sizes: {', '.join(p['attributes']['sizes'])}")
            print(f"   🧵 Chất liệu: {', '.join(p['attributes']['materials'])}")


if __name__ == "__main__":
    asyncio.run(main())
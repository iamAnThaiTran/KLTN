"""
Tiki Review Crawler Simple (httpx version)
Crawls product details + reviews from Tiki without Playwright
Uses httpx for better performance and compatibility

Ported from: BackendPython/app/crawler/tiki_review_crawler_simple.py
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TikiReviewCrawlerSimple:
    """Simple Tiki crawler using httpx (no browser automation)"""
    
    def __init__(self):
        self.base_url = "https://tiki.vn/api/v2"
        self.timeout = 30
        self.session = None
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create httpx session"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
            )
        return self.session
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.aclose()
            self.session = None
    
    async def get_product_snapshot(
        self,
        product_id: str,
        spid: str = "",
        seller_id: str = "1",
        label: str = "",
    ) -> Dict[str, Any]:
        """
        Fetch complete product snapshot (details + reviews)
        
        Args:
            product_id: Tiki product ID
            spid: Seller product ID (optional)
            seller_id: Seller ID
            label: Label for logging
        
        Returns:
            Product snapshot dict
        """
        try:
            logger.info(f"📥 Fetching product: {label or product_id}")
            
            session = await self._get_session()
            
            # Fetch product details
            detail = await self._fetch_product_detail(session, product_id, spid)
            snapshot = self._parse_product_detail(detail or {})
            snapshot["product_id"] = product_id
            snapshot["spid"] = spid
            snapshot["seller_id"] = seller_id
            
            # Fetch reviews
            reviews, rating_bd = await self._crawl_reviews(session, product_id, spid, seller_id)
            snapshot["reviews"] = reviews
            snapshot["rating_breakdown"] = rating_bd
            
            logger.info(
                f"✅ Snapshot: {snapshot.get('name', 'Unknown')[:50]} | "
                f"⭐ {snapshot.get('rating_avg', 0)} | "
                f"💬 {len(reviews)} reviews"
            )
            
            return snapshot
        
        except Exception as e:
            logger.error(f"❌ Error fetching snapshot: {e}")
            raise
    
    async def _fetch_product_detail(
        self,
        session: httpx.AsyncClient,
        product_id: str,
        spid: str
    ) -> Dict:
        """Fetch product details from Tiki API"""
        try:
            # Endpoint: /products/{product_id}
            url = f"{self.base_url}/products/{product_id}"
            
            response = await session.get(url, params={"include": "attributes,rating_summary,seller"})
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch product details: {e}")
            return {}
    
    def _parse_product_detail(self, detail: Dict) -> Dict:
        """Parse product detail API response"""
        return {
            "name": detail.get("name", ""),
            "brand": detail.get("brand", {}).get("name", ""),
            "price": detail.get("price", 0),
            "original_price": detail.get("original_price", 0),
            "rating_avg": detail.get("rating_average", 0),
            "rating_count": detail.get("review_count", 0),
            "thumbnail": detail.get("thumbnail_url", ""),
            "url": detail.get("url", ""),
            "description": detail.get("description", ""),
            "category": detail.get("category", {}).get("name", ""),
            "specs": self._extract_specs(detail.get("specifications", [])),
        }
    
    def _extract_specs(self, specs: List[Dict]) -> List[Dict]:
        """Extract specifications from detail"""
        result = []
        for group in specs:
            result.append({
                "group": group.get("name", ""),
                "attrs": [
                    {
                        "name": attr.get("name", ""),
                        "value": attr.get("value", "")
                    }
                    for attr in group.get("attributes", [])
                ]
            })
        return result
    
    async def _crawl_reviews(
        self,
        session: httpx.AsyncClient,
        product_id: str,
        spid: str,
        seller_id: str
    ) -> tuple[List[Dict], Dict]:
        """Fetch reviews from Tiki"""
        try:
            url = f"{self.base_url}/reviews"
            params = {
                "product_id": product_id,
                "limit": 50,
                "offset": 0,
                "sort": "helpful"
            }
            
            response = await session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            reviews = []
            for review in data.get("data", [])[:20]:  # Limit to 20 reviews
                reviews.append({
                    "rating": review.get("rating", 0),
                    "title": review.get("title", ""),
                    "content": review.get("content", ""),
                    "is_purchased": review.get("purchased", False),
                    "used_duration": review.get("days_used", ""),
                    "helpful_count": review.get("helpful_count", 0),
                })
            
            # Build rating breakdown
            rating_bd = await self._get_rating_breakdown(session, product_id)
            
            logger.info(f"✅ Fetched {len(reviews)} reviews")
            return reviews, rating_bd
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch reviews: {e}")
            return [], {}
    
    async def _get_rating_breakdown(
        self,
        session: httpx.AsyncClient,
        product_id: str
    ) -> Dict:
        """Get rating breakdown"""
        try:
            url = f"{self.base_url}/products/{product_id}/rating-summary"
            response = await session.get(url)
            response.raise_for_status()
            data = response.json()
            
            breakdown = {}
            for star in ["1", "2", "3", "4", "5"]:
                star_data = data.get(star, {})
                breakdown[star] = {
                    "count": star_data.get("total", 0),
                    "percent": star_data.get("percent", 0)
                }
            
            return breakdown
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to get rating breakdown: {e}")
            return {str(i): {"count": 0, "percent": 0} for i in range(1, 6)}
    
    def extract_attributes_from_schema(
        self,
        product: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract product attributes using dynamic schema
        
        Args:
            product: Product dict with description, specs, price
            schema: Dynamic schema with structure:
                {
                    "category": "laptop",
                    "attributes": [
                        {
                            "name": "ram",
                            "keywords": ["ram", "bộ nhớ"],
                            "value_pattern": "\\d+\\s?gb"
                        },
                        {
                            "name": "cpu",
                            "keywords": ["cpu", "chip"],
                            "value_pattern": "(intel|amd|ryzen)"
                        }
                    ]
                }
        
        Returns:
            {
                "attribute_name": {"raw_value": "...", "keywords_found": [...]},
                ...
            }
        """
        import re
        
        extracted = {}
        
        # Combine all text để search
        description = (product.get("description") or "").lower()
        specs_text = self._specs_to_text(product.get("specs", [])).lower()
        all_text = f"{description} {specs_text}"
        
        # Extract each attribute from schema
        for attr_spec in schema.get("attributes", []):
            attr_name = attr_spec.get("name", "").lower()
            keywords = [k.lower() for k in attr_spec.get("keywords", [])]
            value_pattern = attr_spec.get("value_pattern", "")
            
            if not attr_name or not keywords:
                logger.warning(f"⚠️ Invalid attribute spec: {attr_spec}")
                continue
            
            # Find value using keywords + pattern
            found_value = self._extract_attribute_by_keywords(
                all_text,
                keywords,
                value_pattern
            )
            
            extracted[attr_name] = {
                "raw_value": found_value,
                "keywords_found": keywords if found_value else []
            }
        
        return extracted
    
    def _extract_attribute_by_keywords(
        self,
        text: str,
        keywords: List[str],
        value_pattern: str
    ) -> Optional[str]:
        """
        Extract attribute value by searching keywords + applying regex pattern
        
        Args:
            text: Text to search in (description + specs)
            keywords: List of keywords to look for (e.g., ["ram", "bộ nhớ"])
            value_pattern: Regex pattern to extract value
        
        Returns:
            Extracted value or None
        """
        import re
        
        if not value_pattern:
            return None
        
        try:
            # Compile pattern
            pattern = re.compile(value_pattern, re.IGNORECASE)
        except re.error as e:
            logger.error(f"❌ Invalid regex pattern '{value_pattern}': {e}")
            return None
        
        # First, try to find keyword in text
        for keyword in keywords:
            # Find all occurrences of keyword
            keyword_pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
            
            for keyword_match in keyword_pattern.finditer(text):
                # Search for value pattern around this keyword
                # Look before and after keyword (within 100 chars)
                start = max(0, keyword_match.start() - 100)
                end = min(len(text), keyword_match.end() + 100)
                context = text[start:end]
                
                # Try to find pattern in context
                value_match = pattern.search(context)
                if value_match:
                    try:
                        # Try to get first capturing group
                        return value_match.group(1).strip()
                    except (IndexError, AttributeError):
                        # If no group, return full match
                        return value_match.group(0).strip()
        
        # If no keyword found, just search for pattern in all text
        value_match = pattern.search(text)
        if value_match:
            try:
                return value_match.group(1).strip()
            except (IndexError, AttributeError):
                return value_match.group(0).strip()
        
        return None
    

    
    def _specs_to_text(self, specs: List[Dict]) -> str:
        """Convert specs list to searchable text"""
        text_parts = []
        for spec_group in specs:
            group_name = spec_group.get("group", "")
            text_parts.append(group_name)
            
            for attr in spec_group.get("attrs", []):
                attr_name = attr.get("name", "")
                attr_value = attr.get("value", "")
                text_parts.append(f"{attr_name} {attr_value}")
        
        return " ".join(text_parts)
    
    
    
    async def compare_products(
        self,
        product_a: Dict,
        product_b: Dict,
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        Compare 2 products (not used in microservice version)
        Kept for backward compatibility
        """
        logger.warning("compare_products() not implemented in microservice version")
        return {
            "status": "error",
            "error": "compare_products() not implemented - use recommender service endpoint"
        }


# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_crawl_and_extract_attributes(product_id: str = None, schema: Dict = None):
    """
    Test crawling a product and extracting attributes using DYNAMIC SCHEMA
    
    Args:
        product_id: Specific Tiki product ID to test. If None, searches for products.
        schema: Optional dynamic schema. If None, uses default laptop schema.
    
    Example: Test with a product using dynamic schema (no hardcoding!)
    """
    
    print("\n" + "="*80)
    print("🧪 TEST: Crawl Product Detail + Extract with Dynamic Schema")
    print("="*80)
    
    crawler = TikiReviewCrawlerSimple()
    
    # Default schema if not provided (still dynamic - can be changed anytime!)
    if schema is None:
        schema = {
            "category": "product",
            "attributes": [
                {
                    "name": "RAM",
                    "keywords": ["ram", "bộ nhớ", "ddr", "memory"],
                    "value_pattern": r"(\d+)\s*(?:gb|ddr)"
                },
                {
                    "name": "CPU",
                    "keywords": ["cpu", "core", "processor", "xử lý", "chip"],
                    "value_pattern": r"(intel|amd|ryzen|apple\s+m).*?(?=\s|$)"
                },
                {
                    "name": "storage",
                    "keywords": ["ổ cứng", "ssd", "storage", "hdd", "nvme"],
                    "value_pattern": r"(\d+)\s*(?:gb|tb)\s*(?:ssd|hdd|nvme)?"
                },
                {
                    "name": "battery",
                    "keywords": ["pin", "thời lượng", "battery", "dung lượng"],
                    "value_pattern": r"(\d+)\s*(?:giờ|hour|h|mah)\b"
                },
                {
                    "name": "weight",
                    "keywords": ["khối lượng", "nặng", "weight"],
                    "value_pattern": r"(\d+(?:\.\d+)?)\s*kg"
                }
            ]
        }
    
    try:
        if product_id:
            # Test with specific product ID
            print(f"\n📥 Fetching product ID: {product_id}")
            
            try:
                snapshot = await crawler.get_product_snapshot(
                    product_id=str(product_id),
                    label=f"Product {product_id}"
                )
                
                product_name = snapshot.get("name", "Unknown")
                print(f"\n{'─'*80}")
                print(f"📦 Product: {product_name[:70]}")
                print(f"   ID: {product_id}")
                
                # Extract with dynamic schema
                print(f"\n📊 Using Dynamic Schema:")
                print(json.dumps(schema, indent=2, ensure_ascii=False)[:200] + "...")
                
                extracted_attrs = crawler.extract_attributes_from_schema(snapshot, schema)
                
                # Display extracted attributes
                print(f"\n✅ Extracted Attributes:")
                print(json.dumps(extracted_attrs, indent=2, ensure_ascii=False))
                
                
                # Check coverage
                filled = sum(1 for attr in extracted_attrs.values() if attr.get("raw_value"))
                total = len(extracted_attrs)
                coverage = (filled / total * 100) if total > 0 else 0
                print(f"\n📈 Coverage: {filled}/{total} attributes ({coverage:.1f}%)")
                
                # Show raw product info
                print(f"\n📋 Product Info:")
                print(f"   Brand: {snapshot.get('brand', 'N/A')}")
                print(f"   Price: {snapshot.get('price', 'N/A'):,} VND")
                print(f"   Rating: {snapshot.get('rating_avg', 'N/A')} ⭐")
                print(f"   Description: {(snapshot.get('description') or 'N/A')[:100]}...")
                
                # Show specs structure
                if snapshot.get("specs"):
                    print(f"\n📋 Specs Groups:")
                    for spec_group in snapshot["specs"]:
                        group_name = spec_group.get("group")
                        attrs_count = len(spec_group.get("attrs", []))
                        print(f"   - {group_name}: {attrs_count} attributes")
                        for attr in spec_group.get("attrs", [])[:3]:
                            print(f"     • {attr.get('name')}: {attr.get('value')}")
                        if attrs_count > 3:
                            print(f"     ... and {attrs_count - 3} more")
                
            except Exception as e:
                logger.error(f"❌ Error fetching product {product_id}: {e}")
        
        else:
            # Search for laptops
            print("\n📥 Searching for laptop products on Tiki...")
            
            session = await crawler._get_session()
            
            # Search for laptops
            search_url = f"{crawler.base_url}/search"
            search_params = {
                "q": "laptop",
                "limit": 5,
                "include": "badge,specifications,rating_summary"
            }
            
            response = await session.get(search_url, params=search_params)
            response.raise_for_status()
            search_data = response.json()
            
            products_in_search = search_data.get("data", [])
            
            if products_in_search:
                print(f"✅ Found {len(products_in_search)} laptop products")
                
                # Test with first 2 products
                for idx, prod in enumerate(products_in_search[:2], 1):
                    product_id = prod.get("id")
                    product_name = prod.get("name", "Unknown")
                    
                    print(f"\n{'─'*80}")
                    print(f"📦 Product {idx}: {product_name[:60]}")
                    print(f"   ID: {product_id}")
                    
                    try:
                        # Get full product snapshot
                        snapshot = await crawler.get_product_snapshot(
                            product_id=str(product_id),
                            label=product_name
                        )
                        
                        # Extract attributes with dynamic schema
                        print(f"\n   📊 Extracting with Dynamic Schema...")
                        extracted_attrs = crawler.extract_attributes_from_schema(snapshot, schema)
                        
                        # Display extracted attributes
                        print(f"\n   ✅ Extracted Attributes:")
                        print(f"   {json.dumps(extracted_attrs, indent=6, ensure_ascii=False)}")
                        
                        # Check coverage
                        filled = sum(1 for attr in extracted_attrs.values() if attr.get("raw_value"))
                        total = len(extracted_attrs)
                        coverage = (filled / total * 100) if total > 0 else 0
                        print(f"\n   📈 Coverage: {filled}/{total} attributes ({coverage:.1f}%)")
                        
                        # Show raw specs for reference
                        print(f"\n   📋 Raw Specs (for reference):")
                        if snapshot.get("specs"):
                            for spec_group in snapshot["specs"][:3]:  # Show first 3 groups
                                print(f"      {spec_group.get('group')}:")
                                for attr in spec_group.get("attrs", [])[:3]:  # Show first 3 attrs per group
                                    print(f"        - {attr.get('name')}: {attr.get('value')}")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Error processing product: {e}")
            
            else:
                print("⚠️ No products found in search result")
    
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
    
    finally:
        await crawler.close()
    
    print("\n" + "="*80)
    print("✅ Test Complete!")
    print("="*80 + "\n")


async def test_extract_attributes_simple():
    """
    Simple test with hardcoded product data using DYNAMIC SCHEMA
    """
    print("\n" + "="*80)
    print("🧪 TEST: Attribute Extraction with Dynamic Schema")
    print("="*80)
    
    crawler = TikiReviewCrawlerSimple()
    
    # Create test product
    test_product = {
        "name": "ASUS VivoBook 15 OLED - Intel i5 12th Gen, 8GB RAM, 512GB SSD",
        "brand": "ASUS",
        "description": "Laptop ASUS VivoBook 15 OLED với xử lý Intel Core i5 thế hệ 12, 8GB bộ nhớ RAM, ổ cứng SSD 512GB, pin 8 giờ, nặng 1.5kg",
        "specs": [
            {
                "group": "Bộ xử lý",
                "attrs": [
                    {"name": "CPU", "value": "Intel Core i5-12500H"},
                    {"name": "Tốc độ", "value": "2.3 GHz - 4.5 GHz"}
                ]
            },
            {
                "group": "Bộ nhớ",
                "attrs": [
                    {"name": "RAM", "value": "8GB DDR5"},
                    {"name": "Storage", "value": "512GB SSD NVMe"}
                ]
            },
            {
                "group": "Pin",
                "attrs": [
                    {"name": "Dung lượng", "value": "63Wh"},
                    {"name": "Thời lượng", "value": "8 giờ"}
                ]
            },
            {
                "group": "Thiết kế",
                "attrs": [
                    {"name": "Khối lượng", "value": "1.5kg"},
                    {"name": "Giá", "value": "15 triệu VND"}
                ]
            }
        ],
        "price": 15000000
    }
    
    # Dynamic schema - NO HARDCODING!
    laptop_schema = {
        "category": "laptop",
        "attributes": [
            {
                "name": "RAM",
                "keywords": ["ram", "bộ nhớ", "ddr"],
                "value_pattern": r"(\d+)\s*(?:gb|ddr)"
            },
            {
                "name": "CPU",
                "keywords": ["cpu", "core", "processor", "xử lý"],
                "value_pattern": r"(intel|amd|ryzen|apple\s+m).*?(?=\s|$)"
            },
            {
                "name": "storage",
                "keywords": ["ổ cứng", "ssd", "storage", "hdd"],
                "value_pattern": r"(\d+)\s*(?:gb|tb)\s*(?:ssd|hdd)"
            },
            {
                "name": "battery",
                "keywords": ["pin", "thời lượng", "battery"],
                "value_pattern": r"(\d+)\s*(?:giờ|hour|h)\b"
            },
            {
                "name": "weight",
                "keywords": ["khối lượng", "nặng", "weight"],
                "value_pattern": r"(\d+(?:\.\d+)?)\s*kg"
            }
        ]
    }
    
    print(f"\n📦 Test Product: {test_product['name']}")
    print(f"\n📋 Schema:")
    print(json.dumps(laptop_schema, indent=2, ensure_ascii=False))
    
    # Extract with dynamic schema
    extracted = crawler.extract_attributes_from_schema(test_product, laptop_schema)
    
    print(f"\n✅ Extracted Attributes:")
    print(json.dumps(extracted, indent=2, ensure_ascii=False))
    
    # Verify extraction
    print(f"\n📊 Verification:")
    for attr_name, attr_data in extracted.items():
        raw_value = attr_data.get("raw_value")
        status = "✅" if raw_value else "⚠️"
        print(f"   {status} {attr_name}: {raw_value or 'NOT FOUND'}")
    
    print("\n" + "="*80 + "\n")


def test_extract_attributes_with_dynamic_schema():
    """
    Demo: Extract attributes using DYNAMIC SCHEMA (no hardcoding!)
    
    Schema định nghĩa:
    - Category là gì
    - Từng attribute có name, keywords, value_pattern
    - Không cần code mới, chỉ cần update schema JSON
    """
    print("\n" + "="*80)
    print("🧪 TEST: Dynamic Schema-Based Extraction (NO HARDCODING!)")
    print("="*80)
    
    crawler = TikiReviewCrawlerSimple()
    
    # Test Product
    test_product = {
        "name": "ASUS VivoBook 15 OLED",
        "brand": "ASUS",
        "description": "Laptop ASUS với Intel Core i5, 8GB RAM, 512GB SSD, pin 8 giờ, nặng 1.5kg",
        "specs": [
            {
                "group": "Bộ xử lý",
                "attrs": [
                    {"name": "CPU", "value": "Intel Core i5-12500H"},
                    {"name": "Tốc độ", "value": "2.3 GHz"}
                ]
            },
            {
                "group": "Bộ nhớ",
                "attrs": [
                    {"name": "RAM", "value": "8GB DDR5"},
                    {"name": "Storage", "value": "512GB SSD NVMe"}
                ]
            },
            {
                "group": "Pin",
                "attrs": [
                    {"name": "Thời lượng", "value": "8 giờ"}
                ]
            },
            {
                "group": "Thiết kế",
                "attrs": [
                    {"name": "Khối lượng", "value": "1.5kg"}
                ]
            }
        ],
        "price": 15000000
    }
    
    # Schema 1: LAPTOP (dynamic - bỏ hardcode)
    laptop_schema = {
        "category": "laptop",
        "attributes": [
            {
                "name": "RAM",
                "keywords": ["ram", "bộ nhớ", "ddr"],
                "value_pattern": r"(\d+)\s*(?:gb|ddr)"
            },
            {
                "name": "CPU",
                "keywords": ["cpu", "core", "processor", "xử lý"],
                "value_pattern": r"(intel|amd|ryzen|apple\s+m).*?(?=\s|$)"
            },
            {
                "name": "storage",
                "keywords": ["ổ cứng", "ssd", "storage", "hdd"],
                "value_pattern": r"(\d+)\s*(?:gb|tb)\s*(?:ssd|hdd)"
            },
            {
                "name": "battery",
                "keywords": ["pin", "thời lượng", "battery"],
                "value_pattern": r"(\d+)\s*(?:giờ|hour|h)\b"
            },
            {
                "name": "weight",
                "keywords": ["khối lượng", "nặng", "weight"],
                "value_pattern": r"(\d+(?:\.\d+)?)\s*kg"
            }
        ]
    }
    
    # Schema 2: GIÀY (khác hoàn toàn - dynamic!)
    shoe_schema = {
        "category": "giày",
        "attributes": [
            {
                "name": "size",
                "keywords": ["size", "kích cỡ", "cỡ"],
                "value_pattern": r"(\d{1,3})\b"
            },
            {
                "name": "color",
                "keywords": ["màu", "color"],
                "value_pattern": r"(đen|trắng|xanh|đỏ|vàng|hồng)"
            },
            {
                "name": "material",
                "keywords": ["chất liệu", "material"],
                "value_pattern": r"(da|vải|cotton|leather)"
            },
            {
                "name": "brand",
                "keywords": ["thương hiệu", "brand"],
                "value_pattern": r"(nike|adidas|puma|reebok)"
            }
        ]
    }
    
    # Schema 3: ĐIỆN THOẠI (khác nữa!)
    phone_schema = {
        "category": "điện thoại",
        "attributes": [
            {
                "name": "RAM",
                "keywords": ["ram", "bộ nhớ"],
                "value_pattern": r"(\d+)\s*gb"
            },
            {
                "name": "battery",
                "keywords": ["pin", "dung lượng", "battery"],
                "value_pattern": r"(\d+)\s*(?:mah|milli)"
            },
            {
                "name": "screen",
                "keywords": ["màn hình", "display", "screen"],
                "value_pattern": r"(\d+(?:\.\d+)?)\s*(?:inch|\")"
            }
        ]
    }
    
    print(f"\n📦 Test Product: {test_product['name']}")
    
    # Test with laptop schema
    print(f"\n{'─'*80}")
    print("\n🚀 Test 1: Laptop Schema")
    print(json.dumps(laptop_schema, indent=2, ensure_ascii=False))
    
    result = crawler.extract_attributes_from_schema(test_product, laptop_schema)
    print(f"\n✅ Extracted with Laptop Schema:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test with shoe schema (different product)
    print(f"\n{'─'*80}")
    print("\n🚀 Test 2: Shoe Schema (same product, different schema)")
    print(json.dumps(shoe_schema, indent=2, ensure_ascii=False))
    
    result = crawler.extract_attributes_from_schema(test_product, shoe_schema)
    print(f"\n✅ Extracted with Shoe Schema:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test with phone schema
    print(f"\n{'─'*80}")
    print("\n🚀 Test 3: Phone Schema (same product, different schema)")
    print(json.dumps(phone_schema, indent=2, ensure_ascii=False))
    
    result = crawler.extract_attributes_from_schema(test_product, phone_schema)
    print(f"\n✅ Extracted with Phone Schema:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print(f"\n{'─'*80}")
    print(f"\n✨ Key Takeaway:")
    print("   ✅ Không hardcode attributes cho từng category")
    print("   ✅ Schema có thể thay đổi runtime")
    print("   ✅ Cùng 1 product, khác schema -> khác attributes")
    print("   ✅ Tương lai: load schemas từ database/API")
    
    print("\n" + "="*80 + "\n")


# Main entry point
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "simple":
            asyncio.run(test_extract_attributes_simple())
        elif arg == "schema":
            test_extract_attributes_with_dynamic_schema()
        elif arg == "crawl":
            asyncio.run(test_crawl_and_extract_attributes())
        else:
            try:
                product_id = int(arg)
                asyncio.run(test_crawl_and_extract_attributes(product_id=product_id))
            except ValueError:
                print("Usage: python testCrawlDetail.py [simple|schema|crawl|<id>]")
    else:
        print("🚀 Tiki Crawler - Schema-Based Extraction")
        print("Options: simple | schema | crawl | <product_id>")
        asyncio.run(test_extract_attributes_simple())

# app/crawler/filter_manager.py
"""
Filter Manager - Quản lý bộ filter từ các platform khác nhau
Chức năng:
- Extract filters từ Lazada/Tiki/Shopee
- Cache filters để không request lại
- Map platform filters → App schema
"""

import json
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import unicodedata


class FilterCache:
    """In-memory cache cho filters (có thể extend thành Redis)"""
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Args:
            ttl_minutes: Time-to-live cho cache entry (tính bằng phút)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _get_key(self, platform: str, category: str, query: str) -> str:
        """Tạo cache key từ platform + category + query"""
        key_str = f"{platform}:{category}:{query}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, platform: str, category: str, query: str) -> Optional[Dict]:
        """Lấy filters từ cache"""
        key = self._get_key(platform, category, query)
        
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check TTL
        if datetime.now() > entry["expires_at"]:
            del self.cache[key]
            return None
        
        return entry["filters"]
    
    def set(self, platform: str, category: str, query: str, filters: Dict) -> None:
        """Lưu filters vào cache"""
        key = self._get_key(platform, category, query)
        self.cache[key] = {
            "filters": filters,
            "expires_at": datetime.now() + self.ttl,
            "created_at": datetime.now()
        }
    
    def clear_expired(self) -> int:
        """Xóa cache entries hết hạn"""
        expired_keys = [
            k for k, v in self.cache.items()
            if datetime.now() > v["expires_at"]
        ]
        for k in expired_keys:
            del self.cache[k]
        return len(expired_keys)


class FilterMapper:
    """Map filters từ platform → App schema"""
    
    def __init__(self):
        self.mappings = {
            "lazada": {
                "Brand": "brand",
                "brand": "brand",
                "Thương hiệu": "brand",
                
                "Price": "gia",
                "price": "gia",
                "Giá": "gia",
                
                "Color": "mau",
                "color": "mau",
                "Màu": "mau",
                "Màu sắc": "mau",
                
                "Size": "size",
                "size": "size",
                "Kích thước": "size",
                
                "Gender": "gender",
                "Giới tính": "gender",
                
                "Material": "chat_lieu",
                "material": "chat_lieu",
                "Chất liệu": "chat_lieu",
                
                "Type": "loai",
                "Category": "loai",
                "Loại": "loai",
                
                "Usage": "muc_dich",
                "Mục đích": "muc_dich",
            },
            "tiki": {
                # Similar mappings for Tiki
                "Brand": "brand",
                "brand": "brand",
                "Thương hiệu": "brand",
                
                "Price": "gia",
                "Giá": "gia",
                
                "Color": "mau",
                "Màu": "mau",
                
                "Size": "size",
                "Kích thước": "size",
            },
            "shopee": {
                # Similar mappings for Shopee
                "Brand": "brand",
                "Thương hiệu": "brand",
                
                "Price": "gia",
                "Giá": "gia",
                
                "Color": "mau",
                "Màu": "mau",
                
                "Size": "size",
                "Kích thước": "size",
            }
        }
    
    def map_filter_name(self, platform: str, filter_name: str) -> Optional[str]:
        """Map tên filter từ platform sang app schema"""
        platform_lower = platform.lower()
        
        if platform_lower not in self.mappings:
            return None
        
        mapping = self.mappings[platform_lower]
        
        # Exact match
        if filter_name in mapping:
            return mapping[filter_name]
        
        # Case-insensitive match
        for key, value in mapping.items():
            if key.lower() == filter_name.lower():
                return value
        
        return None
    
    def map_filter_values(
        self, 
        platform: str, 
        filter_name: str, 
        values: List[str]
    ) -> Dict[str, Any]:
        """
        Map filter values từ platform format sang app format
        
        Ví dụ:
        - Lazada "40-60k" → app {"min": 40000, "max": 60000}
        - Lazada "Nike" → app "nike" (normalize)
        """
        platform_lower = platform.lower()
        app_filter_name = self.map_filter_name(platform, filter_name)
        
        if not app_filter_name:
            return {"original": filter_name, "values": values}
        
        # Handle price range
        if app_filter_name == "gia" and platform_lower == "lazada":
            return self._map_price_range(values)
        
        # Normalize text values
        normalized_values = [self._normalize_value(v) for v in values]
        
        return {
            "app_name": app_filter_name,
            "original_name": filter_name,
            "values": normalized_values,
            "original_values": values
        }
    
    def _map_price_range(self, values: List[str]) -> Dict[str, Any]:
        """Map Lazada price format (ví dụ: "40K - 60K") sang app format"""
        normalized = []
        
        for val in values:
            # Pattern: "40K - 60K" hoặc "40-60K"
            match = re.search(r'(\d+)\s*(?:K|,)?\s*[-–]\s*(\d+)\s*(?:K|,)?', val)
            if match:
                min_val = int(match.group(1)) * 1000  # Convert K to actual price
                max_val = int(match.group(2)) * 1000
                normalized.append({
                    "min": min_val,
                    "max": max_val,
                    "original": val
                })
            else:
                normalized.append({"original": val})
        
        return {
            "app_name": "gia",
            "type": "range",
            "values": normalized
        }
    
    @staticmethod
    def _normalize_value(value: str) -> str:
        """Normalize filter value (lowercase, remove diacritics)"""
        # Remove diacritics
        value = unicodedata.normalize("NFD", value)
        value = "".join(c for c in value if unicodedata.category(c) != "Mn")
        return value.lower().strip()


class LazadaFilterExtractor:
    """Extract filters từ Lazada page"""
    
    @staticmethod
    def extract_from_html(page_html: str) -> Dict[str, List[str]]:
        """
        Extract filters từ Lazada HTML
        
        Lazada filter structure:
        <div class="ant-checkbox-group">
            <label class="ant-checkbox-wrapper">
                <input type="checkbox">
                <span>Filter Name</span>
            </label>
        </div>
        
        Returns: {
            "Brand": ["Nike", "Adidas", ...],
            "Price": ["40K - 60K", ...],
            ...
        }
        """
        filters = {}
        
        # Pattern to match filter groups
        # Tìm tất cả filter sections
        filter_section_pattern = r'<div[^>]*class="[^"]*filter[^"]*"[^>]*>(.*?)</div>'
        
        sections = re.findall(filter_section_pattern, page_html, re.DOTALL | re.IGNORECASE)
        
        for section in sections:
            # Extract filter title
            title_match = re.search(r'<span[^>]*>([^<]+)</span>', section)
            if not title_match:
                continue
            
            filter_name = title_match.group(1).strip()
            
            # Extract checkbox values
            values = re.findall(r'<label[^>]*class="ant-checkbox-wrapper"[^>]*>.*?<span>([^<]+)</span>', section)
            
            if values:
                filters[filter_name] = values
        
        return filters
    
    @staticmethod
    async def extract_from_page(page) -> Dict[str, List[str]]:
        """
        Extract filters từ Lazada page (using Playwright)
        
        Lấy từ filter panel (sidebar)
        """
        filters = {}
        
        try:
            # Wait for filter panel
            await page.wait_for_selector('.ant-checkbox-group', timeout=5000)
        except:
            print("⚠️ Filter panel not found")
            return filters
        
        # Evaluate filters trong browser
        filter_data = await page.evaluate("""
            () => {
                const filters = {};
                
                // Find all filter groups
                const filterGroups = document.querySelectorAll(
                    'div[class*="filter"], div[class*="Filter"]'
                );
                
                filterGroups.forEach(group => {
                    // Get filter name (title)
                    const titleEl = group.querySelector('h4, [class*="title"]');
                    if (!titleEl) return;
                    
                    const filterName = titleEl.innerText.trim();
                    
                    // Get filter values
                    const checkboxes = group.querySelectorAll(
                        'label.ant-checkbox-wrapper'
                    );
                    
                    const values = [];
                    checkboxes.forEach(checkbox => {
                        const label = checkbox.querySelector('span:last-child')?.innerText?.trim();
                        if (label) values.push(label);
                    });
                    
                    if (values.length > 0) {
                        filters[filterName] = values;
                    }
                });
                
                return filters;
            }
        """)
        
        return filter_data


class FilterManager:
    """Main filter manager - orchestrate caching & mapping"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache = FilterCache(ttl_minutes=ttl_minutes)
        self.mapper = FilterMapper()
        self.lazada_extractor = LazadaFilterExtractor()
    
    async def get_filters(
        self,
        platform: str,
        query: str,
        category: str,
        page=None,  # Playwright page object
        force_refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get filters cho query + category
        
        1. Check cache
        2. Nếu không có hoặc force_refresh → extract từ page
        3. Map sang schema
        4. Cache lại
        
        Returns:
            {
                "raw": {Lazada filters},
                "mapped": {Mapped filters theo schema},
                "cache_hit": bool
            }
        """
        # Step 1: Check cache
        if not force_refresh:
            cached = self.cache.get(platform, category, query)
            if cached:
                print(f"✅ Cache hit: {platform}/{category}/{query}")
                return {
                    "raw": cached["raw"],
                    "mapped": cached["mapped"],
                    "cache_hit": True
                }
        
        # Step 2: Extract filters từ page
        if platform.lower() == "lazada" and page:
            raw_filters = await self.lazada_extractor.extract_from_page(page)
        else:
            print(f"⚠️ Unsupported platform or no page: {platform}")
            return {"raw": {}, "mapped": {}, "cache_hit": False}
        
        # Step 3: Map filters
        mapped_filters = {}
        for filter_name, values in raw_filters.items():
            mapped = self.mapper.map_filter_values(platform, filter_name, values)
            app_name = mapped.get("app_name", filter_name)
            mapped_filters[app_name] = mapped
        
        # Step 4: Cache
        result = {
            "raw": raw_filters,
            "mapped": mapped_filters
        }
        self.cache.set(platform, category, query, result)
        
        print(f"💾 Cached filters: {platform}/{category}/{query}")
        
        return {
            **result,
            "cache_hit": False
        }
    
    def get_filter_suggestions(
        self,
        filters: Dict[str, Dict[str, Any]],
        user_attributes: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Suggest filter values dựa trên user attributes
        
        Ví dụ:
        user_attributes = {"brand": "nike", "size": "40"}
        filters = {
            "brand": {"values": ["nike", "adidas", ...]},
            "size": {"values": ["35", "40", "45", ...]},
        }
        
        Returns:
        {
            "brand": ["nike"],
            "size": ["40"]
        }
        """
        suggestions = {}
        
        for attr_name, attr_value in user_attributes.items():
            if attr_name not in filters:
                continue
            
            filter_info = filters[attr_name]
            available_values = filter_info.get("values", [])
            
            # Exact match hoặc contain match
            matching = [v for v in available_values 
                       if v.lower() == str(attr_value).lower() or
                          str(attr_value).lower() in v.lower()]
            
            if matching:
                suggestions[attr_name] = matching
        
        return suggestions


# ============================================
# USAGE EXAMPLE
# ============================================

if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright
    
    async def example():
        manager = FilterManager(ttl_minutes=60)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Example: Search giày Nike
            await page.goto(
                "https://www.lazada.vn/search?q=giay%20nike",
                wait_until="networkidle"
            )
            
            # Get và cache filters
            result = await manager.get_filters(
                platform="lazada",
                query="giay nike",
                category="giày",
                page=page
            )
            
            print("\n=== Raw Filters ===")
            print(json.dumps(result["raw"], indent=2, ensure_ascii=False))
            
            print("\n=== Mapped Filters ===")
            print(json.dumps(result["mapped"], indent=2, ensure_ascii=False, default=str))
            
            # Example: Get suggestions
            user_attrs = {"brand": "nike", "size": "40"}
            suggestions = manager.get_filter_suggestions(result["mapped"], user_attrs)
            print("\n=== Suggestions ===")
            print(json.dumps(suggestions, indent=2, ensure_ascii=False))
            
            await browser.close()
    
    asyncio.run(example())

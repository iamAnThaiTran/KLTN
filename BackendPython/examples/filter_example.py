# BackendPython/examples/filter_example.py
"""
Ví dụ sử dụng Filter Manager
"""

import asyncio
import json
from app.crawler.filter_manager import FilterManager


async def example_1_basic_filter_extraction():
    """
    Example 1: Extract & cache filters từ Lazada (Turn 1)
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Extract & Cache Filters")
    print("="*80)
    
    manager = FilterManager(ttl_minutes=60)
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        query = "giay nike"
        category = "giày"
        
        # Simulate Lazada navigation
        print(f"\n🌐 Navigating to Lazada: {query}")
        await page.goto(
            f"https://www.lazada.vn/search?q={query}",
            wait_until="networkidle",
            timeout=30000
        )
        
        # Get filters (first time = extract from page)
        print(f"\n📥 Extracting filters...")
        result = await manager.get_filters(
            platform="lazada",
            query=query,
            category=category,
            page=page,
            force_refresh=False
        )
        
        print(f"\n✅ Cache hit: {result['cache_hit']}")
        print(f"\n📊 Raw filters ({len(result['raw'])} groups):")
        for filter_name, values in result["raw"].items():
            print(f"  - {filter_name}: {values[:3]}..." if len(values) > 3 else f"  - {filter_name}: {values}")
        
        print(f"\n🔄 Mapped filters ({len(result['mapped'])} groups):")
        for app_name, info in result["mapped"].items():
            if info.get("type") == "range":
                print(f"  - {app_name}: RANGE filter")
            else:
                values = info.get("values", [])
                print(f"  - {app_name}: {len(values)} values")
        
        await browser.close()


async def example_2_filter_reuse():
    """
    Example 2: Reuse cached filters (Turn 2, 3, ...)
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Reuse Cached Filters")
    print("="*80)
    
    manager = FilterManager(ttl_minutes=60)
    
    # Simulate previous query being cached
    # (In real scenario, this would be done in Example 1)
    
    # For demo, let's manually set cache
    demo_filters = {
        "raw": {
            "Brand": ["Nike", "Adidas", "Puma", "Reebok"],
            "Price": ["20K - 40K", "40K - 60K", "60K - 100K", "100K+"],
            "Color": ["Black", "White", "Blue", "Red"],
            "Size": ["35", "36", "37", "38", "39", "40", "41", "42"],
        },
        "mapped": {
            "brand": {
                "values": ["nike", "adidas", "puma", "reebok"]
            },
            "gia": {
                "type": "range",
                "values": [
                    {"min": 20000, "max": 40000},
                    {"min": 40000, "max": 60000},
                    {"min": 60000, "max": 100000},
                ]
            },
            "mau": {
                "values": ["black", "white", "blue", "red"]
            },
            "size": {
                "values": ["35", "36", "37", "38", "39", "40", "41", "42"]
            }
        }
    }
    
    # Manual cache set
    manager.cache.set("lazada", "giày", "giay nike", demo_filters)
    
    # Turn 2: User selects brand "Nike" and size "40"
    print("\n👤 User selects: brand=nike, size=40")
    
    user_attributes = {
        "brand": "nike",
        "size": "40"
    }
    
    # Get cached filters
    cached = manager.cache.get("lazada", "giày", "giay nike")
    print(f"\n✅ Cache hit: {cached is not None}")
    
    if cached:
        filters = cached["mapped"]
        
        # Get suggestions
        suggestions = manager.get_filter_suggestions(filters, user_attributes)
        
        print(f"\n✅ Matching values found:")
        for attr, values in suggestions.items():
            print(f"  - {attr}: {values}")
        
        # Build Lazada URL
        print(f"\n🔗 Building Lazada URL...")
        params = "brand=nike&size=40"  # Simplified
        url = f"https://www.lazada.vn/search?q=giay%20nike&{params}"
        print(f"  {url}")


async def example_3_filter_mapping():
    """
    Example 3: Filter name mapping (Lazada → App schema)
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Filter Mapping")
    print("="*80)
    
    from app.crawler.filter_manager import FilterMapper
    
    mapper = FilterMapper()
    
    # Test mapping
    test_cases = [
        ("lazada", "Brand", ["Nike", "Adidas"]),
        ("lazada", "Price", ["40K - 60K", "60K - 100K"]),
        ("lazada", "Color", ["Đen", "Trắng"]),
        ("lazada", "Size", ["40", "42"]),
        ("tiki", "Thương hiệu", ["Canon", "Sony"]),
    ]
    
    print("\n🔄 Filter Mapping Tests:\n")
    for platform, filter_name, values in test_cases:
        result = mapper.map_filter_values(platform, filter_name, values)
        
        print(f"Platform: {platform}")
        print(f"  Original: {filter_name} = {values}")
        print(f"  Mapped: {result}")
        print()


async def example_4_price_extraction():
    """
    Example 4: Price range extraction & normalization
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Price Range Extraction")
    print("="*80)
    
    from app.crawler.filter_manager import FilterMapper
    
    mapper = FilterMapper()
    
    # Test price formats
    price_formats = [
        "20K - 40K",
        "100,000 - 200,000",
        "1M - 2M",
        "40K-60K",
        "từ 100K đến 300K"
    ]
    
    print("\n💰 Price Format Tests:\n")
    for price_str in price_formats:
        result = mapper._map_price_range([price_str])
        print(f"Input: '{price_str}'")
        print(f"Output: {result}")
        print()


async def example_5_full_workflow():
    """
    Example 5: Full workflow - From query to filtered results
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Full Workflow")
    print("="*80)
    
    manager = FilterManager(ttl_minutes=60)
    
    print("\n" + "-"*80)
    print("SCENARIO: User searches and filters products")
    print("-"*80)
    
    # Setup demo filters
    demo_filters = {
        "raw": {
            "Brand": ["Nike", "Adidas", "Puma"],
            "Price": ["20K - 40K", "40K - 60K", "60K - 100K"],
            "Color": ["Đen", "Trắng", "Xanh"],
            "Size": ["38", "39", "40", "41", "42"],
        },
        "mapped": {
            "brand": {
                "values": ["nike", "adidas", "puma"]
            },
            "gia": {
                "type": "range",
                "values": [
                    {"min": 20000, "max": 40000},
                    {"min": 40000, "max": 60000},
                    {"min": 60000, "max": 100000},
                ]
            },
            "mau": {
                "values": ["đen", "trắng", "xanh"]
            },
            "size": {
                "values": ["38", "39", "40", "41", "42"]
            }
        }
    }
    
    query = "giay nike"
    manager.cache.set("lazada", "giày", query, demo_filters)
    
    # Turn 1: Show available filters
    print("\n📊 Turn 1: Available Filters")
    cached = manager.cache.get("lazada", "giày", query)
    
    print(f"  Brand options: {cached['mapped']['brand']['values']}")
    print(f"  Price options: 20-40K, 40-60K, 60-100K")
    print(f"  Color options: {cached['mapped']['mau']['values']}")
    print(f"  Size options: {cached['mapped']['size']['values']}")
    
    # Turn 2: User selects brand
    print("\n👤 Turn 2: User selects brand=nike")
    
    user_attrs = {"brand": "nike"}
    suggestions = manager.get_filter_suggestions(cached["mapped"], user_attrs)
    print(f"  ✅ Suggestion: {suggestions}")
    
    # Turn 3: User adds size filter
    print("\n👤 Turn 3: User adds size=40")
    
    user_attrs = {"brand": "nike", "size": "40"}
    suggestions = manager.get_filter_suggestions(cached["mapped"], user_attrs)
    print(f"  ✅ Suggestions: {suggestions}")
    
    # Turn 4: User adds price filter
    print("\n👤 Turn 4: User adds price filter (40K-60K)")
    
    # Note: Price filtering is more complex due to ranges
    print(f"  ✅ Available price ranges:")
    for pr in cached["mapped"]["gia"]["values"]:
        print(f"     - {pr['min']:,} - {pr['max']:,} VND")
    
    # Final filter result
    print("\n🎯 Final Filter Combination:")
    print(f"  - Brand: Nike")
    print(f"  - Size: 40")
    print(f"  - Price: 40,000 - 60,000 VND")
    print(f"\n✅ No additional Lazada requests needed!")
    print(f"   (All filters served from cache)")


async def example_6_cache_management():
    """
    Example 6: Cache management & stats
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Cache Management")
    print("="*80)
    
    manager = FilterManager(ttl_minutes=60)
    
    # Add multiple entries
    demo_filters = {
        "raw": {"Brand": ["Nike", "Adidas"]},
        "mapped": {"brand": {"values": ["nike", "adidas"]}}
    }
    
    queries = [
        ("giay nike", "giày"),
        ("ao adidas", "áo"),
        ("tui coach", "túi xách"),
    ]
    
    print("\n📥 Adding filters to cache:")
    for query, category in queries:
        manager.cache.set("lazada", category, query, demo_filters)
        print(f"  ✅ {category} - {query}")
    
    # Check stats
    print(f"\n📊 Cache Stats:")
    print(f"  Total entries: {len(manager.cache.cache)}")
    print(f"  TTL: {manager.cache.ttl.total_seconds() / 60} minutes")
    
    # Clear specific entry
    print(f"\n🗑️  Clearing cache entry: tui coach")
    key = manager.cache._get_key("lazada", "túi xách", "tui coach")
    del manager.cache.cache[key]
    print(f"  Remaining entries: {len(manager.cache.cache)}")


# ============================================
# MAIN
# ============================================

async def main():
    """Run all examples"""
    
    try:
        # Basic examples (no Playwright needed)
        await example_3_filter_mapping()
        await example_4_price_extraction()
        await example_5_full_workflow()
        await example_6_cache_management()
        
        # Skip examples requiring Lazada connection
        # (Uncomment if you have working Lazada access)
        # await example_1_basic_filter_extraction()
        # await example_2_filter_reuse()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

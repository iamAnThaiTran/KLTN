# test_category_cache.py
"""
Test Category Cache System - Lưu và tái sử dụng LLM suggestions
"""

from app.core.category_cache import CategoryCache
import json


def test_basic_operations():
    """Test basic save/retrieve operations"""
    print("\n" + "="*60)
    print("TEST: Basic Category Cache Operations")
    print("="*60)
    
    # Initialize cache (SQLite)
    cache = CategoryCache(backend="sqlite", db_path="data/test_cache.db")
    
    # Simulate LLM response
    llm_suggestions = [
        {
            "name": "đồng hồ",
            "reason": "Classic gift symbolizing time and new beginnings",
            "attributes": ["brand", "style", "price range"],
            "confidence": 0.85
        },
        {
            "name": "nước hoa",
            "reason": "Elegant and personal gift",
            "attributes": ["brand", "scent type", "volume", "gender"],
            "confidence": 0.82
        },
        {
            "name": "tai nghe",
            "reason": "Modern tech gift for music lovers",
            "attributes": ["brand", "type", "wireless", "price range"],
            "confidence": 0.88
        }
    ]
    
    # Test 1: Save suggestions
    print("\n📝 Test 1: Saving LLM suggestions...")
    ids = cache.save_multiple(llm_suggestions)
    print(f"✓ Saved {len(ids)} suggestions with IDs: {ids}")
    
    # Test 2: Retrieve specific category
    print("\n📖 Test 2: Retrieving 'đồng hồ'...")
    dong_ho = cache.get_suggestion("đồng hồ")
    if dong_ho:
        print(f"✓ Found: {dong_ho['category_name']}")
        print(f"  Attributes: {dong_ho['attributes']}")
        print(f"  Reason: {dong_ho['reason']}")
        print(f"  Usage count: {dong_ho['usage_count']}")
        print(f"  Confidence: {dong_ho['confidence']}")
    else:
        print("❌ Not found!")
    
    # Test 3: Re-save to increment usage
    print("\n🔄 Test 3: Re-saving 'đồng hồ' to increment usage...")
    cache.save_suggestion(llm_suggestions[0])
    
    dong_ho_updated = cache.get_suggestion("đồng hồ")
    print(f"✓ Usage count updated: {dong_ho['usage_count']} → {dong_ho_updated['usage_count']}")
    
    # Test 4: Get all suggestions
    print("\n📋 Test 4: Getting all cached suggestions...")
    all_suggestions = cache.get_all_suggestions()
    print(f"✓ Total cached: {len(all_suggestions)} categories")
    for s in all_suggestions:
        print(f"  - {s['category_name']:20s} | Uses: {s['usage_count']} | Confidence: {s['confidence']}")
    
    return cache


def test_json_backend():
    """Test JSON file backend"""
    print("\n" + "="*60)
    print("TEST: JSON File Backend")
    print("="*60)
    
    # Initialize JSON cache
    cache = CategoryCache(backend="json", db_path="data/test_cache.json")
    
    suggestions = [
        {
            "name": "laptop",
            "reason": "Essential for work and study",
            "attributes": ["brand", "ram", "cpu", "screen size", "price range"]
        },
        {
            "name": "điện thoại",
            "reason": "Most popular tech device",
            "attributes": ["brand", "storage", "ram", "camera", "price range"]
        }
    ]
    
    print("\n📝 Saving to JSON...")
    cache.save_multiple(suggestions)
    
    print("\n📖 Reading from JSON...")
    laptop = cache.get_suggestion("laptop")
    print(f"✓ Found: {laptop['category_name']}")
    print(f"  Attributes: {laptop['attributes']}")
    
    print("\n📋 JSON file content preview:")
    with open("data/test_cache.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")


def test_cache_lookup_integration():
    """Test sử dụng cache để tránh gọi LLM lại"""
    print("\n" + "="*60)
    print("TEST: Cache Lookup Integration")
    print("="*60)
    
    cache = CategoryCache(backend="sqlite", db_path="data/test_cache.db")
    
    # Scenario: User query "tìm đồng hồ"
    category_query = "đồng hồ"
    
    print(f"\n🔍 User query: 'tìm {category_query}'")
    
    # Check cache first
    print(f"\n1️⃣ Check persistent cache...")
    cached = cache.get_suggestion(category_query)
    
    if cached:
        print(f"✅ Found in cache! (Saved LLM call)")
        print(f"   Category: {cached['category_name']}")
        print(f"   Attributes: {cached['attributes']}")
        print(f"   Reason: {cached['reason']}")
        print(f"   Previous uses: {cached['usage_count']}")
        print(f"\n→ Can directly use these attributes without calling LLM!")
    else:
        print(f"❌ Not in cache")
        print(f"→ Need to call LLM to get category attributes")
    
    # Simulate user choosing this category
    if cached:
        print(f"\n2️⃣ User chose '{category_query}', incrementing usage...")
        cache.save_suggestion({
            "name": category_query,
            "attributes": cached['attributes'],
            "reason": cached['reason']
        })
        
        updated = cache.get_suggestion(category_query)
        print(f"✓ Usage count: {cached['usage_count']} → {updated['usage_count']}")


def test_migrate_to_schema_registry():
    """Test migrate cached categories to static schema registry"""
    print("\n" + "="*60)
    print("TEST: Export Cache to Schema Registry")
    print("="*60)
    
    cache = CategoryCache(backend="sqlite", db_path="data/test_cache.db")
    
    # Get all cached suggestions
    all_cached = cache.get_all_suggestions()
    
    print(f"\n📊 Found {len(all_cached)} cached categories")
    print("\n💡 Suggestion: Add frequently used categories to static schema:")
    print("-" * 60)
    
    # Filter: Only show categories used >= 2 times
    frequent = [s for s in all_cached if s['usage_count'] >= 2]
    
    for s in frequent:
        print(f"\nCategory: {s['category_name']} ({s['usage_count']} uses)")
        print(f"  Attributes: {s['attributes']}")
        print(f"  Reason: {s['reason']}")
        print(f"\n  # Add to schema.py:")
        print(f"  {s['category_name'].upper().replace(' ', '_')}_SCHEMA = CategorySchema(")
        print(f"      name=\"{s['category_name']}\",")
        print(f"      keywords=[\"{s['category_name']}\", ...],")
        print(f"      attributes={{")
        for attr in s['attributes']:
            print(f"          \"{attr}\": AttributeConstraint(type=\"text\", required=False),")
        print(f"      }}")
        print(f"  )")


if __name__ == "__main__":
    # Run tests
    test_basic_operations()
    test_json_backend()
    test_cache_lookup_integration()
    test_migrate_to_schema_registry()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)

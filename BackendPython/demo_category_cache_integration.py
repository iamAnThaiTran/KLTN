# demo_category_cache_integration.py
"""
Demo: Category Cache Integration với Orchestrator
Mô phỏng việc LLM suggestions được tự động lưu và tái sử dụng
"""

import asyncio
from app.core.category_cache import CategoryCache


def simulate_llm_response(user_query: str):
    """Simulate LLM trả về category suggestions"""
    
    # Giả lập LLM parse user query và trả về suggestions
    if "quà" in user_query or "tặng" in user_query:
        return {
            "suggestions": [
                {
                    "name": "mỹ phẩm",
                    "reason": "Phổ biến cho quà tặng nữ",
                    "attributes": ["brand", "type", "price range"],
                    "confidence": 0.9
                },
                {
                    "name": "đồng hồ",
                    "reason": "Quà tặng sang trọng",
                    "attributes": ["brand", "style", "price range"],
                    "confidence": 0.85
                },
                {
                    "name": "túi xách",
                    "reason": "Quà tặng thực dụng",
                    "attributes": ["brand", "material", "size"],
                    "confidence": 0.88
                }
            ],
            "best_match": "mỹ phẩm"
        }
    elif "điện tử" in user_query or "tech" in user_query:
        return {
            "suggestions": [
                {
                    "name": "tai nghe",
                    "reason": "Sản phẩm tech phổ biến",
                    "attributes": ["brand", "type", "wireless", "price range"],
                    "confidence": 0.92
                },
                {
                    "name": "chuột không dây",
                    "reason": "Phụ kiện máy tính",
                    "attributes": ["brand", "dpi", "wireless", "price range"],
                    "confidence": 0.87
                }
            ],
            "best_match": "tai nghe"
        }
    else:
        return {
            "suggestions": [
                {
                    "name": user_query,
                    "reason": "Exact match",
                    "attributes": ["brand", "price range"],
                    "confidence": 0.95
                }
            ],
            "best_match": user_query
        }


async def demo_workflow():
    """Demo workflow: Query → Check cache → LLM (if needed) → Save"""
    
    print("\n" + "="*70)
    print("DEMO: Category Cache Integration Workflow")
    print("="*70)
    
    # Initialize cache
    cache = CategoryCache(backend="sqlite", db_path="data/demo_cache.db")
    
    # Scenarios
    queries = [
        "tìm quà tặng cho bạn gái",
        "mua đồng hồ",  # Same category as first query
        "tìm sản phẩm điện tử",
        "mua tai nghe",  # Same category as previous
        "tìm quà tặng"   # Repeat first query
    ]
    
    for idx, query in enumerate(queries, 1):
        print(f"\n{'─'*70}")
        print(f"Query {idx}: '{query}'")
        print(f"{'─'*70}")
        
        # Step 1: Extract potential category from query
        category_keywords = query.replace("tìm", "").replace("mua", "").strip().split()[0]
        
        # Step 2: Check cache first
        print(f"\n🔍 Step 1: Check cache for similar categories...")
        
        # Check exact match
        cached = cache.get_suggestion(category_keywords)
        
        if cached:
            print(f"✅ CACHE HIT! Found '{cached['category_name']}'")
            print(f"   Attributes: {cached['attributes']}")
            print(f"   Usage: {cached['usage_count']} times")
            print(f"   💰 Saved 1 LLM API call!")
            
            # Increment usage
            cache.save_suggestion({
                "name": cached['category_name'],
                "attributes": cached['attributes'],
                "reason": cached['reason']
            })
            
        else:
            print(f"❌ CACHE MISS for '{category_keywords}'")
            print(f"   → Need to call LLM")
            
            # Step 3: Call LLM
            print(f"\n🤖 Step 2: Calling LLM for suggestions...")
            llm_response = simulate_llm_response(query)
            
            suggestions = llm_response['suggestions']
            best_match = llm_response['best_match']
            
            print(f"   LLM returned {len(suggestions)} suggestions:")
            for s in suggestions:
                print(f"     - {s['name']}: {s['reason']}")
            print(f"   Best match: {best_match}")
            
            # Step 4: Save to cache
            print(f"\n💾 Step 3: Saving to cache for future use...")
            saved_ids = cache.save_multiple(suggestions)
            print(f"   ✓ Saved {len(saved_ids)} categories")
            
            # Update cached for next steps
            cached = cache.get_suggestion(best_match)
        
        # Step 5: Use attributes for product search
        print(f"\n🎯 Step 4: Using attributes for product search...")
        print(f"   Category: {cached['category_name']}")
        print(f"   Attributes to extract: {cached['attributes']}")
        print(f"   → Ready to crawl & match products!")
        
        # Show cache stats
        await asyncio.sleep(0.1)  # Small delay for readability
    
    # Final statistics
    print(f"\n\n{'='*70}")
    print("📊 FINAL CACHE STATISTICS")
    print(f"{'='*70}")
    
    all_suggestions = cache.get_all_suggestions()
    print(f"\nTotal cached categories: {len(all_suggestions)}")
    print("\nTop categories by usage:")
    
    for s in sorted(all_suggestions, key=lambda x: x['usage_count'], reverse=True):
        print(f"  {s['category_name']:20s} | {s['usage_count']:2d} uses | Confidence: {s['confidence']:.2f}")
    
    # Calculate savings
    total_queries = len(queries)
    llm_calls_made = len([q for q in queries if "quà" in q or "điện tử" in q])
    llm_calls_saved = total_queries - llm_calls_made
    
    print(f"\n💰 Cost Savings:")
    print(f"   Total queries: {total_queries}")
    print(f"   LLM calls made: {llm_calls_made}")
    print(f"   LLM calls saved: {llm_calls_saved}")
    print(f"   Savings rate: {llm_calls_saved/total_queries*100:.1f}%")
    
    print(f"\n{'='*70}")


def demo_migration_to_static_schema():
    """Demo migrate frequently used categories to static schema"""
    
    print("\n" + "="*70)
    print("DEMO: Migration to Static Schema")
    print("="*70)
    
    cache = CategoryCache(backend="sqlite", db_path="data/demo_cache.db")
    
    # Simulate more usage
    print("\n🔄 Simulating more queries to build usage data...")
    
    # Add more fake usage
    categories_to_boost = [
        ("đồng hồ", 8),
        ("tai nghe", 6),
        ("mỹ phẩm", 5),
        ("túi xách", 3)
    ]
    
    for cat_name, times in categories_to_boost:
        cached = cache.get_suggestion(cat_name)
        if cached:
            for _ in range(times):
                cache.save_suggestion({
                    "name": cat_name,
                    "attributes": cached['attributes'],
                    "reason": cached['reason']
                })
    
    print("✓ Usage data updated")
    
    # Find candidates for migration
    print("\n📈 Categories recommended for static schema (usage >= 5):")
    print("-" * 70)
    
    all_suggestions = cache.get_all_suggestions()
    candidates = [s for s in all_suggestions if s['usage_count'] >= 5]
    
    for s in candidates:
        print(f"\n🎯 {s['category_name'].upper()} ({s['usage_count']} uses)")
        print(f"   Attributes: {s['attributes']}")
        
        # Generate schema code
        schema_name = s['category_name'].upper().replace(' ', '_').replace('Ồ', 'O').replace('Ư', 'U')
        print(f"\n   📝 Add to schema.py:")
        print(f"   ```python")
        print(f"   {schema_name}_SCHEMA = CategorySchema(")
        print(f"       name=\"{s['category_name']}\",")
        print(f"       keywords=[\"{s['category_name']}\"],  # Add more keywords")
        print(f"       attributes={{")
        
        for attr in s['attributes']:
            attr_clean = attr.replace(' ', '_').lower()
            print(f"           \"{attr_clean}\": AttributeConstraint(")
            print(f"               type=\"text\",  # Adjust type as needed")
            print(f"               required=False")
            print(f"           ),")
        
        print(f"       }}")
        print(f"   )")
        print(f"   ```")
    
    print(f"\n{'='*70}")


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_workflow())
    demo_migration_to_static_schema()
    
    print("\n✅ Demo completed! Check data/demo_cache.db for saved data.")

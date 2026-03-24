"""
Test & Example  for Product Comparison API
Demonstrates how to use the comparison endpoints
"""

import asyncio
import json
import sys

# Add parent directory to path for imports
sys.path.insert(0, "/home/user/Code/KLTN/BackendPython")

from app.crawler.tiki_review_crawler import TikiReviewCrawler
from app.services.product_comparison_service import ProductComparisonService


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE 1: Direct crawler usage (without FastAPI)
# ──────────────────────────────────────────────────────────────────────────────

async def example_1_direct_crawler():
    """
    Direct usage of TikiReviewCrawler to get product snapshots.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Direct Crawler Usage")
    print("=" * 70)

    crawler = TikiReviewCrawler()

    # Get single product analysis
    print("\n[1.1] Fetching single product snapshot...")
    snapshot = await crawler.get_product_snapshot(
        product_id="16268021",
        spid="16268022",
        seller_id="1",
        label="Test Product",
    )

    print(f"\n✅ Product: {snapshot['name']}")
    print(f"   💰 Price: {snapshot['price']:,}đ (discount: {snapshot['discount_pct']}%)")
    print(f"   ⭐ Rating: {snapshot['rating_avg']} ({snapshot['rating_count']} reviews)")
    print(f"   📏 Sizes: {len(snapshot['sizes'])} available")
    print(f"   🎨 Colors: {len(snapshot['colors'])} available")
    print(f"   📋 Specs: {len(snapshot['specifications'])} groups")
    print(f"   💬 Reviews crawled: {len(snapshot['reviews'])}")

    # Show first 2 reviews
    print("\n[1.2] Sample reviews:")
    for i, review in enumerate(snapshot["reviews"][:2], 1):
        print(f"\n   Review {i}:")
        print(f"   ⭐ {review['rating']} - {review['title']}")
        print(f"   📝 {review['content'][:80]}...")
        print(f"   👤 {review['author']} ({'Verified' if review['is_purchased'] else 'Unverified'})")


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE 2: Compare 2 products (without LLM)
# ──────────────────────────────────────────────────────────────────────────────

async def example_2_compare_without_llm():
    """
    Compare 2 products and get the comparison prompt (without LLM).
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Compare 2 Products (Prompt Only, No LLM)")
    print("=" * 70)

    crawler = TikiReviewCrawler()

    print("\n[2.1] Crawling 2 products in parallel...")
    result = await crawler.compare_products(
        product_a={
            "product_id": "16268021",
            "spid": "16268022",
            "seller_id": "1",
        },
        product_b={
            # Usually you'd use a different product, but for demo using same
            "product_id": "16268021",
            "spid": "16268022",
            "seller_id": "1",
        },
        llm_client=None,  # No LLM call
    )

    print(f"\n✅ Comparison complete")
    print(f"   Product A: {result['snapshot_a']['name']}")
    print(f"   Product B: {result['snapshot_b']['name']}")
    print(f"   Prompt size: {len(result['prompt'])} characters")

    # Save prompt for review
    print(f"\n[2.2] Comparison prompt (first 1000 chars):")
    print("-" * 70)
    print(result["prompt"][:1000])
    print("...")
    print("-" * 70)

    # Optionally save to file
    output = {
        "comparison_type": "without_llm",
        "product_a": result["snapshot_a"],
        "product_b": result["snapshot_b"],
        "prompt": result["prompt"],
    }
    with open("comparison_prompt_example.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved prompt to comparison_prompt_example.json")


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE 3: Using ProductComparisonService
# ──────────────────────────────────────────────────────────────────────────────

async def example_3_service_usage():
    """
    Using ProductComparisonService (higher-level API).
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: ProductComparisonService (Higher-level API)")
    print("=" * 70)

    service = ProductComparisonService()

    # Validate product IDs
    print("\n[3.1] Validating product IDs...")
    product_a = {
        "product_id": "16268021",
        "spid": "16268022",
        "seller_id": "1",
    }
    product_b = {
        "product_id": "16268021",
        "spid": "16268022",
        "seller_id": "1",
    }

    is_valid, error_msg = service.validate_product_ids(product_a, product_b)
    if not is_valid:
        print(f"❌ Validation failed: {error_msg}")
        return

    print(f"✅ Validation passed")

    # Get single product analysis
    print("\n[3.2] Getting single product analysis...")
    analysis_result = await service.get_single_product_analysis(
        product_id="16268021",
        spid="16268022",
        seller_id="1",
        label="Example Product",
    )

    if analysis_result["status"] == "success":
        snapshot = analysis_result["snapshot"]
        display = service.format_product_info_for_display(snapshot)
        print(f"\n✅ Product: {display['name']}")
        print(f"   Price: {display['price']:,}đ")
        print(f"   Rating: {display['rating_avg']} ⭐")
        print(f"   Reviews: {display['review_count']}")

    # Compare products
    print("\n[3.3] Comparing 2 products...")
    compare_result = await service.compare_tiki_products(
        product_a=product_a,
        product_b=product_b,
        llm_model="gpt-4o-mini",
    )

    if compare_result["status"] == "success":
        print(f"✅ Comparison successful")
        print(f"   Product A: {compare_result['snapshot_a']['name']}")
        print(f"   Product B: {compare_result['snapshot_b']['name']}")
        # Note: comparison text is empty since we didn't use LLM
    else:
        print(f"❌ Comparison failed: {compare_result.get('error')}")


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE 4: How to integrate with LLM (OpenAI)
# ──────────────────────────────────────────────────────────────────────────────

async def example_4_with_llm():
    """
    Compare products WITH LLM analysis.
    Requires: OPENAI_API_KEY environment variable
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: With LLM Analysis (Automatic OpenAI)")
    print("=" * 70)

    print("""
LLM (OpenAI gpt-4o-mini) comparison analysis is AUTOMATIC!

1. Set your API key:
   export OPENAI_API_KEY="sk-proj-..."

2. Get key from: https://platform.openai.com/api/keys

3. Call compare_tiki_products - LLM is invoked automatically:
   
   result = await service.compare_tiki_products(
       product_a={...},
       product_b={...},
       llm_model="gpt-4o-mini"  # Can also use gpt-4o
   )
   
   print(result["comparison"])  # Markdown output from OpenAI

The LLM will analyze the products on:
- Price vs Quality
- Technical specifications
- Customer reviews sentiment
- Recommendations based on use case
- Overall winner

Note: LLM is called inside the crawler using call_openai() function
""")


# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE 5: FastAPI integration
# ──────────────────────────────────────────────────────────────────────────────

async def example_5_fastapi_integration():
    """
    Show how to call the comparison API endpoints.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: FastAPI Integration")
    print("=" * 70)

    print("""
# Start the server:
cd /path/to/BackendPython
python main.py

# Then call the comparison endpoints:

## 1. Compare 2 products (LLM analysis is automatic with OpenAI):
curl -X POST http://localhost:8000/api/products/compare \\
  -H "Content-Type: application/json" \\
  -d '{
    "product_a": {
      "product_id": "16268021",
      "spid": "16268022",
      "seller_id": "1"
    },
    "product_b": {
      "product_id": "11111111",
      "spid": "22222222",
      "seller_id": "1"
    },
    "llm_model": "gpt-4o-mini"
  }'

## 2. Analyze single product:
curl -X POST http://localhost:8000/api/products/analyze-single \\
  -H "Content-Type: application/json" \\
  -d '{
    "product_id": "16268021",
    "spid": "16268022",
    "seller_id": "1",
    "label": "My Product"
  }'

## 3. Get comparison prompt (without LLM):
curl -X POST http://localhost:8000/api/products/compare/with-prompt \\
  -H "Content-Type: application/json" \\
  -d '{
    "product_a": {
      "product_id": "16268021",
      "spid": "16268022",
      "seller_id": "1"
    },
    "product_b": {
      "product_id": "11111111",
      "spid": "22222222",
      "seller_id": "1"
    }
  }'

## Response format:
{
  "status": "success",
  "snapshot_a": {
    "product_id": "16268021",
    "name": "Product name",
    "brand": "Brand",
    "price": 150000,
    "rating_avg": 4.5,
    "rating_count": 100,
    "reviews": [...],
    "specifications": [...]
  },
  "snapshot_b": {...},
  "prompt": "Comparison prompt text...",
  "comparison": "LLM analysis (if include_llm_analysis=true)"
}
""")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    """Run all examples"""
    try:
        # Example 1: Direct crawler
        await example_1_direct_crawler()

        # Example 2: Compare without LLM
        await example_2_compare_without_llm()

        # Example 3: Service usage
        await example_3_service_usage()

        # Example 4: With LLM (info only)
        await example_4_with_llm()

        # Example 5: FastAPI integration (info only)
        await example_5_fastapi_integration()

        print("\n" + "=" * 70)
        print("✅ All examples completed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

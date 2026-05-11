"""
Example: Using ProductDetailCrawler with LLM-Assisted Extraction

Demonstrates:
1. Creating LLM extractor
2. Initializing crawler with LLM support
3. Extracting attributes from single product
4. Batch processing multiple products
5. Falling back to regex when LLM fails
6. Validating and canonicalizing results

Prerequisites:
- Set OPENAI_API_KEY environment variable
- pip install openai
"""

import asyncio
import logging
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from crawlers.tiki.product_detail_crawler import ProductDetailCrawler
from extraction import (
    LLMAttributeExtractor,
    ExtractionSchema,
    AttributeSchema,
)


# ---------------------------------------------------------------------------
# DEFINE SCHEMA
# ---------------------------------------------------------------------------

def create_computer_mouse_schema() -> ExtractionSchema:
    """Define schema for computer mouse product category"""
    return ExtractionSchema(
        category="computer_mouse",
        attributes=[
            AttributeSchema(
                name="dpi",
                type="number",
                required=False,
                min_value=400,
                max_value=16000,
            ),
            AttributeSchema(
                name="connection_type",
                type="enum",
                required=False,
                allowed_values=["wired", "wireless", "bluetooth"],
            ),
            AttributeSchema(
                name="buttons",
                type="number",
                required=False,
                min_value=2,
                max_value=20,
            ),
            AttributeSchema(
                name="sensor_type",
                type="enum",
                required=False,
                allowed_values=["optical", "laser", "infrared"],
            ),
            AttributeSchema(
                name="weight",
                type="number",
                required=False,
                min_value=50,
                max_value=500,
            ),
            AttributeSchema(
                name="color",
                type="string",
                required=False,
            ),
            AttributeSchema(
                name="material",
                type="enum",
                required=False,
                allowed_values=["plastic", "rubber", "metal", "aluminum"],
            ),
        ],
    )


# Convert to old-style schema for backward compatibility
def create_old_style_schema() -> Dict[str, Any]:
    """Old schema format for regex extraction fallback"""
    return {
        "category": "computer_mouse",
        "attributes": [
            {
                "name": "dpi",
                "keywords": ["dpi", "dots per inch", "resolution"],
                "attr_type": "numeric",
                "value_pattern": r"\d+",
            },
            {
                "name": "connection_type",
                "keywords": ["connection", "wireless", "bluetooth", "wired"],
                "attr_type": "enum",
                "vocabulary": ["wired", "wireless", "bluetooth"],
            },
            {
                "name": "buttons",
                "keywords": ["buttons", "button", "keys"],
                "attr_type": "numeric",
                "value_pattern": r"\d+",
            },
        ],
    }


# ---------------------------------------------------------------------------
# EXAMPLE 1: Single Product with LLM Extraction
# ---------------------------------------------------------------------------

async def example_single_product_llm() -> None:
    """Extract attributes from a single product using LLM"""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 1: Single Product with LLM Extraction")
    logger.info("=" * 60)
    
    try:
        # Initialize crawler with LLM support
        crawler = ProductDetailCrawler(
            timeout=30.0,
            use_llm=True,  # Enable LLM mode
        )
        
        # Define schema
        schema = create_computer_mouse_schema()
        
        # Crawl and extract
        product_id = "100023456"  # Example Tiki product ID
        
        result = await crawler.crawl_tiki_product_details_with_llm(
            product_id=product_id,
            schema=schema,
            fallback_to_regex=True,
        )
        
        if result["status"] == "success":
            logger.info(f"✅ Success! Extraction method: {result['extraction_method']}")
            logger.info(f"📦 Product: {result['product']['name']}")
            logger.info(f"🏷️ Extracted attributes:")
            for attr_name, value in result["extracted_attributes"].items():
                logger.info(f"   - {attr_name}: {value}")
        else:
            logger.error(f"❌ Failed: {result['error']}")
        
        await crawler.close()
    
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


# ---------------------------------------------------------------------------
# EXAMPLE 2: Batch Processing with Old-Style Schema
# ---------------------------------------------------------------------------

async def example_batch_extraction() -> None:
    """Extract attributes from multiple products"""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 2: Batch Processing with LLM")
    logger.info("=" * 60)
    
    try:
        # Initialize crawler
        crawler = ProductDetailCrawler(use_llm=True)
        
        # Old-style schema (for backward compatibility)
        schema = create_old_style_schema()
        
        # List of product IDs to extract
        product_ids = [
            "100023456",
            "100023457",
            "100023458",
        ]
        
        # Crawl multiple products
        results = await crawler.crawl_multiple_products_with_llm(
            product_ids=product_ids,
            schema=schema,
            max_concurrent=3,
            fallback_to_regex=True,
        )
        
        # Print results
        logger.info(f"📊 Processed {len(results)} products:")
        for result in results:
            if result["status"] == "success":
                logger.info(
                    f"✅ {result['product']['product_id']}: "
                    f"{result['product']['name'][:40]}"
                )
            else:
                logger.error(f"❌ {result.get('product_id')}: {result['error']}")
        
        await crawler.close()
    
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


# ---------------------------------------------------------------------------
# EXAMPLE 3: Using LLM Extractor Directly (for advanced use)
# ---------------------------------------------------------------------------

async def example_direct_llm_usage() -> None:
    """Use LLMAttributeExtractor directly for custom workflows"""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 3: Direct LLM Extractor Usage")
    logger.info("=" * 60)
    
    try:
        # Initialize LLM extractor
        extractor = LLMAttributeExtractor(
            model="gpt-4o-mini",
            temperature=0.2,
            batch_size=5,
        )
        
        # Define schema
        schema = create_computer_mouse_schema()
        
        # Prepare products (with compact text for extraction)
        products = [
            {
                "product_id": "001",
                "text": """
                Gaming Mouse Pro - Ultra-precise 3200 DPI optical sensor.
                Wireless connection with Bluetooth 5.0.
                8 programmable buttons, lightweight 85g design.
                Premium rubber grip, matte black finish.
                """,
            },
            {
                "product_id": "002",
                "text": """
                Wired Office Mouse - Simple and reliable.
                USB connection, 2 buttons + scroll wheel.
                1000 DPI fixed resolution optical sensor.
                Affordable option for office work.
                """,
            },
        ]
        
        # Extract batch
        results = await extractor.extract_batch(products, schema)
        
        # Print results
        for result in results:
            logger.info(f"Product {result.product_id}:")
            logger.info(f"  Status: {'✅ Valid' if result.is_valid() else '❌ Invalid'}")
            logger.info(f"  Confidence: {result.confidence:.1%}")
            logger.info(f"  Attributes: {result.attributes}")
            if result.validation_errors:
                logger.warning(f"  Errors: {result.validation_errors}")
        
        # Print statistics
        extractor.print_stats()
    
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


# ---------------------------------------------------------------------------
# EXAMPLE 4: Fallback Behavior Demo
# ---------------------------------------------------------------------------

async def example_fallback_behavior() -> None:
    """Demonstrate fallback to regex when LLM extraction fails"""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 4: Fallback to Regex Behavior")
    logger.info("=" * 60)
    
    try:
        # Initialize with LLM
        crawler = ProductDetailCrawler(use_llm=True)
        
        schema = create_old_style_schema()
        
        product_id = "100023456"
        
        # Try with LLM and fallback enabled
        result = await crawler.crawl_tiki_product_details_with_llm(
            product_id=product_id,
            schema=schema,
            fallback_to_regex=True,  # Enable fallback
        )
        
        if result["status"] == "success":
            method = result.get("extraction_method", "unknown")
            logger.info(f"Extraction method used: {method}")
            
            if method == "llm":
                logger.info("✅ LLM extraction successful")
            elif method == "regex":
                logger.info("🔄 Fell back to regex extraction")
        
        await crawler.close()
    
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


# ---------------------------------------------------------------------------
# EXAMPLE 5: Cost Tracking
# ---------------------------------------------------------------------------

async def example_cost_tracking() -> None:
    """Track API costs and token usage"""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 5: API Cost Tracking")
    logger.info("=" * 60)
    
    try:
        extractor = LLMAttributeExtractor(batch_size=5)
        schema = create_computer_mouse_schema()
        
        # Simulate some extractions
        products = [
            {"product_id": str(i), "text": f"Sample product {i} text"}
            for i in range(10)
        ]
        
        batches = [products[i:i+5] for i in range(0, len(products), 5)]
        
        for batch in batches:
            await extractor.extract_batch(batch, schema)
        
        # Print statistics
        logger.info("\n📊 Extraction Statistics:")
        extractor.print_stats()
    
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

async def main():
    """Run all examples"""
    logger.info("🚀 Starting LLM Extraction Examples...")
    
    # Uncomment the examples you want to run
    
    # await example_single_product_llm()
    # await example_batch_extraction()
    # await example_direct_llm_usage()
    # await example_fallback_behavior()
    # await example_cost_tracking()
    
    # For now, just show schema definitions
    logger.info("\n📋 Available Schema Examples:")
    logger.info("- create_computer_mouse_schema() - LLM-compatible schema")
    logger.info("- create_old_style_schema() - Old regex-based schema")
    
    logger.info("\n✅ Run examples by uncommenting in main()")


if __name__ == "__main__":
    asyncio.run(main())

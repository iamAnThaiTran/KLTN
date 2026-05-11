# LLM-Assisted Attribute Extraction System

## Overview

This system implements a **hybrid approach** to ecommerce product attribute extraction, combining:

- **LLM-Assisted Semantic Extraction** (GPT-4o-mini) - primary method
- **Deterministic Validation** (regex/enum/numeric) - fallback & validation
- **Structured Data Extraction** (specifications lookup) - highest priority

### Architecture

```
Product Data
    ↓
[1] Structured Specs Extraction (priority 0 - highest)
    ↓ (if found, use directly)
[2] LLM Semantic Extraction (GPT-4o-mini)
    ↓ (normalizes and validates)
[3] Value Canonicalization & Validation
    ↓ (ensures schema compliance)
[4] Fallback to Regex [Optional]
    ↓ (if LLM fails and enabled)
Final Enriched Attributes
```

## Key Features

### ✅ What's New

1. **LLM-First Extraction**: GPT-4o-mini as primary semantic extractor
   - Understands context and meaning
   - Handles complex product descriptions
   - No need for keyword lists or regex patterns
   - Semantic understanding of attributes

2. **Schema-Constrained Output**: Strict enforcement
   - Only schema-defined attributes allowed
   - Unknown/hallucinated attributes rejected
   - Type validation (numbers, enums, text)
   - No free-form extraction

3. **Batch Processing**: Efficient API usage
   - Process 5-10 products per request
   - Automatic batching
   - Cost-effective API calls

4. **Fallback Support**: Graceful degradation
   - Automatic fallback to regex if LLM fails
   - Optional fallback mode
   - Configurable behavior

### ✨ What's Preserved

1. **Normalization Functions** (kept as-is)
   - Value normalization (`_normalize_value()`)
   - HTML cleaning (`_clean_html()`)
   - Unicode normalization (`_normalize_unicode()`)

2. **Structured Specs Extraction** (priority 0)
   - Direct lookup in product specifications
   - Highest priority - always used first
   - `_build_spec_lookup()` and `_lookup_in_specs()`

3. **Regex/Enum Extraction** (as fallback)
   - All original regex extraction logic
   - Enum/multi_enum support
   - Numeric pattern matching

4. **Backward Compatibility**
   - Old schema format still works
   - Existing code not broken
   - Can mix old and new approaches

## Installation & Setup

### 1. Install Dependencies

```bash
pip install openai>=1.0.0 httpx
```

### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

Or in code:
```python
from extraction import LLMAttributeExtractor
extractor = LLMAttributeExtractor(api_key="sk-...")
```

### 3. Verify Installation

```python
from extraction import LLMAttributeExtractor, ExtractionSchema
print("✅ LLM extraction module loaded")
```

## Usage Guide

### Schema Definition

#### New LLM-Compatible Schema

```python
from extraction import ExtractionSchema, AttributeSchema

schema = ExtractionSchema(
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
            allowed_values=["wired", "wireless", "bluetooth"],
        ),
        AttributeSchema(
            name="color",
            type="string",
        ),
    ],
)
```

#### Supported Types

| Type | Description | Example |
|------|-------------|---------|
| `number` | Numeric values with optional bounds | `{"type": "number", "min_value": 0, "max_value": 100}` |
| `enum` | Single value from allowed list | `{"type": "enum", "allowed_values": ["a", "b", "c"]}` |
| `multi_enum` | Multiple values from allowed list | `{"type": "multi_enum", "allowed_values": [...]}` |
| `string` | Short text with optional regex | `{"type": "string", "pattern": "..."}` |
| `text` | Long-form text | `{"type": "text"}` |

### Single Product Extraction

```python
import asyncio
from crawlers.tiki.product_detail_crawler import ProductDetailCrawler

async def extract_single():
    # Create crawler with LLM support
    crawler = ProductDetailCrawler(
        timeout=30.0,
        use_llm=True,  # Enable LLM mode
    )
    
    # Crawl and extract
    result = await crawler.crawl_tiki_product_details_with_llm(
        product_id="100023456",
        schema=schema,
        fallback_to_regex=True,  # Enable regex fallback
    )
    
    if result["status"] == "success":
        print(f"✅ Extracted: {result['extracted_attributes']}")
        print(f"📊 Method: {result['extraction_method']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    await crawler.close()

# Run
asyncio.run(extract_single())
```

### Batch Processing

```python
async def batch_extraction():
    crawler = ProductDetailCrawler(use_llm=True)
    
    # Extract multiple products
    results = await crawler.crawl_multiple_products_with_llm(
        product_ids=["100023456", "100023457", "100023458"],
        schema=schema,
        max_concurrent=3,
        fallback_to_regex=True,
    )
    
    # Process results
    for result in results:
        if result["status"] == "success":
            print(f"✅ {result['product']['product_id']}: Success")
            print(f"   Attributes: {result['extracted_attributes']}")
        else:
            print(f"❌ {result['product_id']}: {result['error']}")
    
    await crawler.close()

asyncio.run(batch_extraction())
```

### Direct LLM Extractor Usage

```python
from extraction import LLMAttributeExtractor

async def direct_usage():
    # Initialize extractor
    extractor = LLMAttributeExtractor(
        model="gpt-4o-mini",
        temperature=0.2,  # Low temperature for consistency
        batch_size=5,
    )
    
    # Prepare products
    products = [
        {
            "product_id": "001",
            "text": "Product description and specs..."
        },
        {
            "product_id": "002",
            "text": "Another product..."
        },
    ]
    
    # Extract batch
    results = await extractor.extract_batch(products, schema)
    
    # Process results
    for result in results:
        print(f"Product: {result.product_id}")
        print(f"  Valid: {result.is_valid()}")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Attributes: {result.attributes}")
    
    # Print statistics
    extractor.print_stats()

asyncio.run(direct_usage())
```

## Fallback Behavior

### When Fallback is Enabled

```python
result = await crawler.crawl_tiki_product_details_with_llm(
    product_id="100023456",
    schema=schema,
    fallback_to_regex=True,  # ← Enable fallback
)

# Check which method was used
if result["extraction_method"] == "llm":
    print("✅ LLM extraction successful")
elif result["extraction_method"] == "regex":
    print("🔄 Fell back to regex (LLM failed)")
```

### When Fallback is Disabled

```python
result = await crawler.crawl_tiki_product_details_with_llm(
    product_id="100023456",
    schema=schema,
    fallback_to_regex=False,  # ← Disable fallback
)

# If LLM fails, error is raised
if result["status"] == "error":
    print(f"❌ Extraction failed: {result['error']}")
```

## Validation & Canonicalization

### Schema Validation

```python
from extraction import validate_extraction

# Validate extracted attributes
valid_attrs, errors = validate_extraction(
    extracted_attrs={
        "dpi": 1600,
        "connection_type": "WIRELESS",  # ← Will be canonicalized
        "unknown_field": "value",  # ← Will be rejected
    },
    schema=schema,
    strict=True,  # Reject unknown attributes
)

print(f"✅ Valid: {valid_attrs}")
print(f"⚠️ Errors: {errors}")
# Output:
# ✅ Valid: {"dpi": 1600, "connection_type": "wireless", ...}
# ⚠️ Errors: {"unknown_field": "Unknown attribute (rejected): ..."}
```

### Value Canonicalization

The system automatically:

1. **Enum Matching** (fuzzy + exact)
   - "WIRELESS" → "wireless" (case-insensitive)
   - "blue-tooth" → "bluetooth" (fuzzy matching)

2. **Number Validation**
   - "1600 dpi" → 1600.0
   - Checks min/max bounds
   - Rejects out-of-range values

3. **String Normalization**
   - Trims whitespace
   - Validates regex patterns
   - Enforces length limits

## API Reference

### ProductDetailCrawler

#### Initialize with LLM

```python
crawler = ProductDetailCrawler(
    timeout=30.0,          # Request timeout
    use_llm=True,          # Enable LLM mode
    llm_extractor=None,    # Auto-create if None
)
```

#### Methods

```python
# Single product with LLM
result = await crawler.crawl_tiki_product_details_with_llm(
    product_id: str,
    schema: Dict[str, Any],
    fallback_to_regex: bool = True,
) -> Dict[str, Any]

# Multiple products with LLM
results = await crawler.crawl_multiple_products_with_llm(
    product_ids: List[str],
    schema: Dict[str, Any],
    max_concurrent: int = 5,
    fallback_to_regex: bool = True,
) -> List[Dict[str, Any]]

# Old methods still work (regex-only)
result = await crawler.crawl_tiki_product_details(
    product_id: str,
    schema: Dict[str, Any],
) -> Dict[str, Any]
```

### LLMAttributeExtractor

```python
extractor = LLMAttributeExtractor(
    api_key: Optional[str] = None,      # OpenAI API key
    model: str = "gpt-4o-mini",         # LLM model
    temperature: float = 0.2,            # Creativity (0=deterministic)
    max_tokens: int = 4096,             # Max response tokens
    batch_size: int = 5,                # Products per batch
    max_retries: int = 3,               # Retry attempts
)

# Extract batch
results = await extractor.extract_batch(
    products: List[Dict[str, str]],
    schema: ExtractionSchema,
) -> List[ExtractionResult]

# Extract multiple (auto-batches)
results = await extractor.extract_multiple(
    products: List[Dict[str, str]],
    schema: ExtractionSchema,
) -> List[ExtractionResult]

# Get statistics
stats = extractor.get_stats() -> Dict[str, Any]
extractor.print_stats()  # Pretty print
```

### ExtractionSchema

```python
from extraction import ExtractionSchema, AttributeSchema

schema = ExtractionSchema(
    category: str,              # Product category
    attributes: List[AttributeSchema],
)

# Or validate/batch validate
from extraction import validate_extraction, batch_validate_extraction

valid, errors = validate_extraction(attrs, schema)
validated = batch_validate_extraction(batch_results, schema)
```

## Cost Estimation

### Pricing (GPT-4o-mini)

- **Input**: $0.15 / 1M tokens
- **Output**: $0.60 / 1M tokens

### Typical Costs

| Scenario | Tokens | Cost |
|----------|--------|------|
| Single product | 500 input + 100 output | $0.00015 |
| Batch of 5 products | 2500 input + 400 output | $0.00063 |
| 1000 products (200 batches) | 500K input + 80K output | $0.123 |

Enable cost tracking:

```python
extractor.print_stats()
# Output:
# ╔════════════════════════════════════════════╗
# ║     LLM Extraction Statistics              ║
# ╠════════════════════════════════════════════╣
# ║ Batches:              10                   ║
# ║ Products:             50                   ║
# ║ Successful:           49 (98.0%)          ║
# ║ Failed:                1                   ║
# ║ Total Tokens:       2500                   ║
# ║ Estimated Cost:    $0.0045                 ║
# ╚════════════════════════════════════════════╝
```

## Error Handling

### Common Errors

```python
# Error: API key not set
# Solution: export OPENAI_API_KEY="sk-..." or pass api_key param

# Error: Rate limited (429)
# Solution: Auto-retry with exponential backoff (up to 3 attempts)

# Error: LLM extraction failed
# Solution: Automatic fallback to regex (if enabled)

# Error: Invalid schema
# Solution: Validate schema before passing to extractor
```

### Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Check detailed extraction info
result = await extractor.extract_batch(products, schema)
for r in result:
    if not r.is_valid():
        print(f"❌ {r.product_id}:")
        print(f"   Error: {r.error}")
        print(f"   Validation Errors: {r.validation_errors}")
        print(f"   Raw Response: {r.raw_response}")
```

## Performance Tuning

### Temperature

- **Low (0.0-0.3)**: Deterministic, consistent results
- **Default (0.2)**: Good balance
- **High (0.7-1.0)**: More creative, variable results

```python
# For strict attribute extraction (recommended)
extractor = LLMAttributeExtractor(temperature=0.2)
```

### Batch Size

- **Small (1-2)**: Slower, more flexible
- **Medium (5-10)**: Recommended, good throughput
- **Large (20+)**: Fast but may reduce accuracy

```python
# Optimal balance
extractor = LLMAttributeExtractor(batch_size=5)
```

### Concurrency

```python
# Process 3 crawls simultaneously
results = await crawler.crawl_multiple_products_with_llm(
    product_ids=product_ids,
    schema=schema,
    max_concurrent=3,  # Balance between speed and rate limits
)
```

## Backward Compatibility

### Old Schema Still Works

```python
# Old-style schema (regex-based)
old_schema = {
    "category": "computer_mouse",
    "attributes": [
        {
            "name": "dpi",
            "keywords": ["dpi", "resolution"],
            "attr_type": "numeric",
            "value_pattern": r"\d+",
        },
    ],
}

# Still works with regex extraction
result = await crawler.crawl_tiki_product_details(
    product_id="100023456",
    schema=old_schema,
)
```

### Migration Path

1. **Phase 1**: Keep existing regex extraction
   - Works as-is, no changes needed
   - Set `use_llm=False` (default)

2. **Phase 2**: Enable LLM with fallback
   - Try LLM first, fall back to regex
   - `use_llm=True`, `fallback_to_regex=True`

3. **Phase 3**: Full LLM migration
   - Use new schema format
   - Monitor quality, tune as needed

## Best Practices

### ✅ Do's

1. **Use new schema format** for LLM extraction
2. **Set temperature low** (0.2) for consistency
3. **Batch process** products for efficiency
4. **Monitor confidence scores** to assess quality
5. **Validate schema** before production use
6. **Enable logging** for debugging
7. **Cache results** to avoid re-extraction

### ❌ Don'ts

1. **Don't use high temperature** (>0.5) for attributes
2. **Don't submit invalid schema** to LLM
3. **Don't disable fallback** without testing
4. **Don't over-batch** (batch_size > 20)
5. **Don't skip validation** on LLM output

## Troubleshooting

### "LLM extraction not available"

```python
# Solution: Install openai package
pip install openai>=1.0.0
```

### "Failed after 3 retries"

```python
# Solution: Check API key, rate limits, network
# Enable logging for more details
logging.basicConfig(level=logging.DEBUG)
```

### "Confidence too low"

```python
# Check validation errors
result = await extractor.extract_batch(products, schema)
for r in result:
    print(f"Confidence: {r.confidence}")
    print(f"Errors: {r.validation_errors}")
    # Adjust schema constraints if too strict
```

## Advanced Usage

### Custom Prompt Building

```python
from extraction import build_extraction_prompt, build_system_prompt

system = build_system_prompt()
user = build_extraction_prompt(products, schema)

# Use with custom API client
response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ],
)
```

### Few-Shot Prompting

```python
from extraction import create_few_shot_examples

examples = create_few_shot_examples(schema, num_examples=2)

# Pass to API with few-shot context
messages = [
    {"role": "system", "content": system},
] + examples + [
    {"role": "user", "content": user},
]
```

## Support & Contribution

For issues, questions, or contributions:
- Check logs with `logging.DEBUG`
- Review examples in `extraction/example_usage.py`
- Validate schema against `ExtractionSchema` definition
- Test with small batches first

---

**Last Updated**: 2024-05-11
**Version**: 1.0.0
**Status**: Production Ready ✅

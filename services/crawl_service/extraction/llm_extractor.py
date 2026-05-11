"""
LLM Attribute Extractor Service

Orchestrates GPT-4o-mini calls for semantic product attribute extraction.
Handles batching, JSON parsing, error recovery, and schema validation.

Features:
- Batch processing (5-10 products per request)
- Automatic retry with backoff
- JSON parsing with fallback
- Schema-constrained validation
- Confidence scoring
- Cost tracking
"""

import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re

try:
    from openai import AsyncOpenAI, APIError, RateLimitError
except ImportError:
    AsyncOpenAI = None
    APIError = Exception
    RateLimitError = Exception

from .schema_validator import ExtractionSchema, validate_extraction
from .prompt_builder import build_system_prompt, build_extraction_prompt

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096
DEFAULT_BATCH_SIZE = 5
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds


@dataclass
class ExtractionResult:
    """Result of LLM extraction for a single product"""
    product_id: str
    attributes: Dict[str, Any]
    raw_response: Optional[str] = None
    validation_errors: Optional[Dict[str, str]] = None
    confidence: float = 0.0
    tokens_used: Optional[int] = None
    extraction_method: str = "llm"  # "llm", "fallback", "error"
    error: Optional[str] = None
    
    def is_valid(self) -> bool:
        """Check if extraction succeeded"""
        return self.error is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return asdict(self)


class LLMAttributeExtractor:
    """
    Extract product attributes using GPT-4o-mini with schema enforcement.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        Initialize LLM extractor.
        
        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: Model name (default: gpt-4o-mini)
            temperature: Creativity (0.0=deterministic, 1.0=creative)
            max_tokens: Maximum response tokens
            batch_size: Products per batch (default 5)
            max_retries: Number of retry attempts
        """
        if not AsyncOpenAI:
            raise RuntimeError(
                "openai package not installed. "
                "Install with: pip install openai"
            )
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.batch_size = batch_size
        self.max_retries = max_retries
        
        self.stats = {
            "batches_processed": 0,
            "products_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
        }
    
    # =====================================================================
    # BATCH PROCESSING
    # =====================================================================
    
    def _chunk_products(
        self,
        products: List[Dict[str, str]],
    ) -> List[List[Dict[str, str]]]:
        """Split products into batches"""
        batches = []
        for i in range(0, len(products), self.batch_size):
            batches.append(products[i:i + self.batch_size])
        return batches
    
    async def extract_batch(
        self,
        products: List[Dict[str, str]],
        schema: ExtractionSchema,
    ) -> List[ExtractionResult]:
        """
        Extract attributes from a batch of products.
        
        Args:
            products: List of {"product_id": str, "text": str}
            schema: ExtractionSchema defining valid attributes
        
        Returns:
            List of ExtractionResult objects
        """
        logger.info(f"📊 Processing batch of {len(products)} products")
        
        try:
            # Call LLM with retry logic
            response_text = await self._call_llm_with_retry(products, schema)
            
            # Parse JSON response
            extracted_list = self._parse_json_response(response_text)
            if not extracted_list:
                logger.error("❌ Failed to parse LLM response")
                return [
                    ExtractionResult(
                        product_id=p.get("product_id", "unknown"),
                        attributes={},
                        error="Failed to parse LLM response",
                        extraction_method="error",
                    )
                    for p in products
                ]
            
            # Validate and canonicalize results
            results = []
            for item in extracted_list:
                result = self._process_extraction_item(item, schema)
                results.append(result)
            
            self.stats["batches_processed"] += 1
            self.stats["products_processed"] += len(products)
            self.stats["successful_extractions"] += sum(
                1 for r in results if r.is_valid()
            )
            self.stats["failed_extractions"] += sum(
                1 for r in results if not r.is_valid()
            )
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Batch extraction failed: {e}")
            return [
                ExtractionResult(
                    product_id=p.get("product_id", "unknown"),
                    attributes={},
                    error=str(e),
                    extraction_method="error",
                )
                for p in products
            ]
    
    async def extract_multiple(
        self,
        products: List[Dict[str, str]],
        schema: ExtractionSchema,
    ) -> List[ExtractionResult]:
        """
        Extract attributes from multiple products (auto-batches).
        
        Args:
            products: List of {"product_id": str, "text": str}
            schema: ExtractionSchema
        
        Returns:
            List of ExtractionResult objects
        """
        batches = self._chunk_products(products)
        all_results = []
        
        for batch in batches:
            batch_results = await self.extract_batch(batch, schema)
            all_results.extend(batch_results)
            
            # Small delay between batches to avoid rate limits
            if len(batches) > 1:
                await asyncio.sleep(0.5)
        
        return all_results
    
    # =====================================================================
    # LLM COMMUNICATION
    # =====================================================================
    
    async def _call_llm_with_retry(
        self,
        products: List[Dict[str, str]],
        schema: ExtractionSchema,
    ) -> str:
        """
        Call LLM with automatic retry and exponential backoff.
        
        Returns:
            Response text from LLM
        """
        system_prompt = build_system_prompt()
        user_prompt = build_extraction_prompt(products, schema)
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"🔄 LLM call (attempt {attempt + 1}/{self.max_retries})")
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                
                # Extract token usage
                if response.usage:
                    tokens = response.usage.prompt_tokens + response.usage.completion_tokens
                    self.stats["total_tokens"] += tokens
                    # Rough cost estimate for gpt-4o-mini
                    # Input: $0.15/1M tokens, Output: $0.60/1M tokens
                    cost = (response.usage.prompt_tokens * 0.15 + 
                           response.usage.completion_tokens * 0.60) / 1_000_000
                    self.stats["total_cost_usd"] += cost
                    logger.debug(f"💰 Tokens: {tokens}, Est. cost: ${cost:.6f}")
                
                response_text = response.choices[0].message.content
                logger.debug(f"✅ LLM response received ({len(response_text)} chars)")
                return response_text
            
            except RateLimitError as e:
                wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    f"⚠️ Rate limited (attempt {attempt + 1}). "
                    f"Waiting {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            
            except APIError as e:
                if attempt < self.max_retries - 1:
                    wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"⚠️ API error (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        raise RuntimeError(f"Failed after {self.max_retries} retries")
    
    # =====================================================================
    # JSON PARSING & VALIDATION
    # =====================================================================
    
    def _parse_json_response(self, response_text: str) -> Optional[List[Dict]]:
        """
        Parse JSON from LLM response with fallback strategies.
        
        Handles:
        - JSON wrapped in markdown code blocks
        - Trailing/leading text
        - Malformed JSON
        """
        text = response_text.strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try extracting JSON array directly
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.error(f"❌ Could not parse JSON from response: {text[:200]}")
        return None
    
    def _process_extraction_item(
        self,
        item: Dict[str, Any],
        schema: ExtractionSchema,
    ) -> ExtractionResult:
        """
        Validate and canonicalize a single extracted item.
        
        Returns:
            ExtractionResult with validation applied
        """
        product_id = item.get("product_id", "unknown")
        raw_attrs = item.get("attributes", {})
        
        # Validate against schema
        valid_attrs, errors = validate_extraction(raw_attrs, schema, strict=True)
        
        # Compute confidence (simple: no errors = high confidence)
        confidence = 1.0 if not errors else max(0.0, 1.0 - len(errors) * 0.2)
        
        return ExtractionResult(
            product_id=product_id,
            attributes=valid_attrs,
            raw_response=json.dumps(raw_attrs),
            validation_errors=errors if errors else None,
            confidence=confidence,
            extraction_method="llm",
            error=None if not errors else "; ".join(errors.values()),
        )
    
    # =====================================================================
    # STATISTICS
    # =====================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_extractions"] / 
                max(self.stats["products_processed"], 1)
                if self.stats["products_processed"] > 0
                else 0.0
            ),
        }
    
    def print_stats(self):
        """Print extraction statistics"""
        stats = self.get_stats()
        print(f"""
╔════════════════════════════════════════════╗
║     LLM Extraction Statistics              ║
╠════════════════════════════════════════════╣
║ Batches:              {stats['batches_processed']:>6}           ║
║ Products:             {stats['products_processed']:>6}           ║
║ Successful:           {stats['successful_extractions']:>6} ({stats['success_rate']:.1%})     ║
║ Failed:               {stats['failed_extractions']:>6}           ║
║ Total Tokens:         {stats['total_tokens']:>6}           ║
║ Estimated Cost:       ${stats['total_cost_usd']:>6.4f}        ║
╚════════════════════════════════════════════╝
        """)

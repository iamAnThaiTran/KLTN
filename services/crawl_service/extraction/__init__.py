"""
Extraction Module - LLM-Assisted Attribute Extraction

Combines semantic LLM extraction with deterministic validation and normalization.
"""

from .schema_validator import (
    AttributeSchema,
    ExtractionSchema,
    validate_attribute_value,
    validate_extraction,
    batch_validate_extraction,
)
from .prompt_builder import (
    build_schema_json_schema,
    build_system_prompt,
    build_extraction_prompt,
    build_batch_extraction_request,
)
from .llm_extractor import (
    LLMAttributeExtractor,
    ExtractionResult,
)

__all__ = [
    # Schema
    "AttributeSchema",
    "ExtractionSchema",
    # Validation
    "validate_attribute_value",
    "validate_extraction",
    "batch_validate_extraction",
    # Prompts
    "build_schema_json_schema",
    "build_system_prompt",
    "build_extraction_prompt",
    "build_batch_extraction_request",
    # LLM Extractor
    "LLMAttributeExtractor",
    "ExtractionResult",
]

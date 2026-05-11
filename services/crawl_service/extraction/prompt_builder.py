"""
Prompt Builder for LLM-Based Attribute Extraction

Constructs structured, schema-aware prompts for GPT-4o-mini to extract product
attributes with guaranteed JSON output and schema compliance.

Key principles:
- Clear, instruction-following format
- JSON Schema definition embedded
- Examples provided
- Strict output format enforcement
"""

import json
from typing import Dict, List, Any, Optional
from .schema_validator import ExtractionSchema, AttributeSchema


def build_schema_json_schema(
    schema: ExtractionSchema,
) -> Dict[str, Any]:
    """
    Convert ExtractionSchema to JSON Schema format for LLM clarity.
    
    Returns JSON Schema describing the expected output structure.
    """
    properties: Dict[str, Any] = {}
    required_attrs: List[str] = []
    
    for attr in schema.attributes:
        prop: Dict[str, Any] = {}
        
        if attr.type == "number":
            prop["type"] = "number"
            if attr.min_value is not None:
                prop["minimum"] = attr.min_value
            if attr.max_value is not None:
                prop["maximum"] = attr.max_value
        
        elif attr.type == "enum":
            prop["type"] = "string"
            if attr.allowed_values:
                prop["enum"] = attr.allowed_values
        
        elif attr.type == "multi_enum":
            prop["type"] = "array"
            prop["items"] = {"type": "string"}
            if attr.allowed_values:
                prop["enum"] = attr.allowed_values
        
        elif attr.type == "string":
            prop["type"] = "string"
            if attr.pattern:
                prop["pattern"] = attr.pattern
        
        elif attr.type == "text":
            prop["type"] = "string"
        
        prop["description"] = f"Attribute: {attr.name} (type: {attr.type})"
        properties[attr.name] = prop
        
        if attr.required:
            required_attrs.append(attr.name)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required_attrs,
        "additionalProperties": False,  # STRICT: no hallucinated fields
    }


def build_system_prompt() -> str:
    """
    Build system prompt for LLM extraction role.
    """
    return """You are a precise product attribute extraction system.

Your task:
- Extract product attributes from text descriptions and specifications
- Return ONLY valid schema-defined attributes
- Output MUST be valid JSON
- Unknown attributes should be null/omitted
- NO hallucinated or invented attributes
- NO free-form extraction outside schema

Important:
- Follow the schema exactly
- Use exact enum values provided
- Convert values to correct types (number, enum, text, etc.)
- If attribute value cannot be found/extracted, use null
- If enum value doesn't match, return null instead of inventing
"""


def build_extraction_prompt(
    products: List[Dict[str, str]],
    schema: ExtractionSchema,
) -> str:
    """
    Build user prompt for batch attribute extraction.
    
    Args:
        products: List of product dicts with 'product_id' and 'text' keys
        schema: ExtractionSchema
    
    Returns:
        Formatted prompt string
    """
    json_schema = build_schema_json_schema(schema)
    
    # Build attribute definitions section
    attr_defs = []
    for attr in schema.attributes:
        line = f"- {attr.name}: {attr.type}"
        if attr.required:
            line += " [REQUIRED]"
        if attr.allowed_values:
            line += f" → allowed: {', '.join(attr.allowed_values)}"
        attr_defs.append(line)
    
    attr_section = "\n".join(attr_defs)
    
    # Build products section
    products_text = "\n\n".join(
        f"Product ID: {p.get('product_id', 'unknown')}\nText:\n{p.get('text', '')}"
        for p in products
    )
    
    prompt = f"""Extract product attributes from the following product descriptions.

Category: {schema.category}

Attribute Definitions:
{attr_section}

JSON Schema (strict compliance required):
{json.dumps(json_schema, indent=2)}

Products to extract:
{products_text}

Instructions:
1. For each product, extract all attributes present in the text
2. Return attributes in the exact schema format
3. Use exact enum values only - no variations or synonyms
4. If an attribute cannot be found or is ambiguous, use null
5. Do NOT invent or hallucinate values
6. Do NOT add attributes not in the schema
7. Return valid JSON array with one object per product

Output Format (REQUIRED - must be valid JSON):
[
  {{
    "product_id": "123",
    "attributes": {{
      "attr_name": value,
      ...
    }}
  }}
]

Output (JSON only, no explanation):
"""
    
    return prompt


def build_batch_extraction_request(
    products: List[Dict[str, str]],
    schema: ExtractionSchema,
) -> Dict[str, Any]:
    """
    Build complete OpenAI API request for batch extraction.
    
    Returns:
        Dict ready to pass to OpenAI API client.messages.create()
    """
    system_prompt = build_system_prompt()
    user_prompt = build_extraction_prompt(products, schema)
    
    return {
        "system": system_prompt,
        "user": user_prompt,
    }


def _build_extraction_example(
    schema: ExtractionSchema,
) -> str:
    """
    Build a JSON example for the given schema.
    Useful for few-shot prompting.
    """
    example = {}
    for attr in schema.attributes:
        if attr.type == "number":
            example[attr.name] = 123.45
        elif attr.type == "enum" and attr.allowed_values:
            example[attr.name] = attr.allowed_values[0]
        elif attr.type == "multi_enum" and attr.allowed_values:
            example[attr.name] = [attr.allowed_values[0]]
        else:
            example[attr.name] = "example_value"
    
    return json.dumps({"product_id": "example_123", "attributes": example}, indent=2)


def create_few_shot_examples(
    schema: ExtractionSchema,
    num_examples: int = 2,
) -> List[Dict[str, Any]]:
    """
    Create few-shot example messages for better LLM performance.
    
    Returns:
        List of {"role": "assistant", "content": ...} messages
    """
    # For now, single templated example
    # In production, could load from database of good extractions
    
    example_json = _build_extraction_example(schema)
    
    return [
        {
            "role": "assistant",
            "content": f"""[
  {example_json}
]""",
        }
    ]

"""
Schema Validator for Attribute Extraction

Validates and canonicalizes LLM-extracted attributes against a schema definition.
Ensures:
- Only schema-defined attributes are returned
- Type constraints are enforced (number, enum, string, etc.)
- Enum values match allowed_values
- Unknown attributes return None
- No hallucinated fields
"""

from typing import Dict, List, Any, Optional, Literal, Tuple
import logging
import re
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TYPE DEFINITIONS
# ---------------------------------------------------------------------------

AttrTypeConstraint = Literal["number", "enum", "multi_enum", "string", "text"]


@dataclass
class AttributeSchema:
    """Single attribute schema definition"""
    name: str
    type: AttrTypeConstraint
    required: bool = False
    allowed_values: Optional[List[str]] = None  # For enum/multi_enum
    min_value: Optional[float] = None  # For number
    max_value: Optional[float] = None  # For number
    pattern: Optional[str] = None  # For string validation


@dataclass
class ExtractionSchema:
    """Complete schema for a category"""
    category: str
    attributes: List[AttributeSchema]
    
    def get_attribute(self, name: str) -> Optional[AttributeSchema]:
        """Get attribute schema by name"""
        return next((a for a in self.attributes if a.name == name), None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON/API"""
        return {
            "category": self.category,
            "attributes": [asdict(a) for a in self.attributes],
        }


# ---------------------------------------------------------------------------
# CANONICALIZATION LOGIC
# ---------------------------------------------------------------------------


def _normalize_enum_value(
    raw_value: str,
    allowed_values: List[str],
    fuzzy_match: bool = True,
) -> Optional[str]:
    """
    Canonicalize enum value to exact schema value.
    
    Strategy:
    1. Exact match (case-insensitive)
    2. Fuzzy match if enabled (levenshtein-like logic)
    3. Return None if no match found
    """
    if not raw_value:
        return None
    
    raw_lower = raw_value.lower().strip()
    
    # Try exact match first (case-insensitive)
    for allowed in allowed_values:
        if allowed.lower().strip() == raw_lower:
            return allowed  # Return the canonical form
    
    # Try fuzzy match (simple substring + similarity)
    if fuzzy_match:
        best_match = None
        best_score = 0.0
        
        for allowed in allowed_values:
            allowed_lower = allowed.lower().strip()
            
            # Substring match
            if allowed_lower in raw_lower or raw_lower in allowed_lower:
                return allowed
            
            # Simple similarity: common prefix length
            common = 0
            for i, (c1, c2) in enumerate(zip(raw_lower, allowed_lower)):
                if c1 == c2:
                    common += 1
                else:
                    break
            
            similarity = common / max(len(raw_lower), len(allowed_lower))
            if similarity > best_score and similarity > 0.6:
                best_score = similarity
                best_match = allowed
        
        if best_match:
            logger.debug(
                f"ℹ️ Fuzzy matched '{raw_value}' → '{best_match}' "
                f"(score: {best_score:.2f})"
            )
            return best_match
    
    return None


def _normalize_number(
    raw_value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Optional[float]:
    """
    Parse and validate number within bounds.
    
    Accepts: int, float, str representations of numbers
    Returns: float or None if invalid/out of bounds
    """
    try:
        if isinstance(raw_value, (int, float)):
            num = float(raw_value)
        elif isinstance(raw_value, str):
            # Remove whitespace and try parse
            cleaned = raw_value.strip()
            # Try to extract number from string (e.g., "50mm" → 50)
            match = re.search(r"[-+]?(\d+\.?\d*|\.\d+)", cleaned)
            if not match:
                return None
            num = float(match.group(0))
        else:
            return None
        
        # Validate bounds
        if min_value is not None and num < min_value:
            logger.warning(f"⚠️ Number {num} below minimum {min_value}")
            return None
        if max_value is not None and num > max_value:
            logger.warning(f"⚠️ Number {num} above maximum {max_value}")
            return None
        
        return num
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse number from '{raw_value}': {e}")
        return None


def _normalize_string(
    raw_value: str,
    pattern: Optional[str] = None,
    max_length: int = 500,
) -> Optional[str]:
    """
    Validate and normalize string value.
    
    Checks:
    - Non-empty after strip
    - Matches regex pattern if provided
    - Length reasonable
    """
    if not isinstance(raw_value, str):
        return None
    
    normalized = raw_value.strip()
    
    if not normalized:
        return None
    
    if len(normalized) > max_length:
        logger.warning(
            f"⚠️ String too long ({len(normalized)} > {max_length}): "
            f"{normalized[:50]}..."
        )
        return None
    
    if pattern:
        try:
            if not re.match(pattern, normalized):
                logger.debug(f"String '{normalized}' doesn't match pattern '{pattern}'")
                return None
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
    
    return normalized


# ---------------------------------------------------------------------------
# VALIDATION FUNCTIONS
# ---------------------------------------------------------------------------


def validate_attribute_value(
    attr_name: str,
    raw_value: Any,
    attr_schema: AttributeSchema,
) -> Tuple[bool, Any, Optional[str]]:
    """
    Validate and canonicalize a single attribute value.
    
    Args:
        attr_name: Attribute name
        raw_value: Raw value from LLM
        attr_schema: Attribute schema definition
    
    Returns:
        (is_valid, canonical_value, error_message)
        - is_valid: bool
        - canonical_value: properly typed value or None
        - error_message: reason for failure if invalid
    """
    if raw_value is None:
        return True, None, None  # None is always valid (missing attribute)
    
    try:
        if attr_schema.type == "number":
            num = _normalize_number(
                raw_value,
                min_value=attr_schema.min_value,
                max_value=attr_schema.max_value,
            )
            if num is None:
                return False, None, f"Invalid number: {raw_value}"
            return True, num, None
        
        elif attr_schema.type in ("enum", "multi_enum"):
            if not attr_schema.allowed_values:
                return False, None, "Enum has no allowed_values defined"
            
            if attr_schema.type == "enum":
                # Single value
                if isinstance(raw_value, (list, tuple)):
                    raw_value = raw_value[0] if raw_value else None
                
                canonical = _normalize_enum_value(
                    str(raw_value) if raw_value is not None else "",
                    attr_schema.allowed_values,
                    fuzzy_match=True,
                )
                if canonical is None:
                    return False, None, (
                        f"Value '{raw_value}' not in allowed values: "
                        f"{attr_schema.allowed_values}"
                    )
                return True, canonical, None
            
            else:  # multi_enum
                # Multiple values - keep as list
                if not isinstance(raw_value, (list, tuple)):
                    raw_value = [raw_value]
                
                canonical_values = []
                for v in raw_value:
                    canonical = _normalize_enum_value(
                        str(v),
                        attr_schema.allowed_values,
                        fuzzy_match=True,
                    )
                    if canonical:
                        canonical_values.append(canonical)
                
                if not canonical_values:
                    return False, None, (
                        f"None of values {raw_value} found in "
                        f"allowed values: {attr_schema.allowed_values}"
                    )
                return True, canonical_values, None
        
        elif attr_schema.type == "string":
            normalized = _normalize_string(
                str(raw_value),
                pattern=attr_schema.pattern,
            )
            if normalized is None:
                return False, None, f"Invalid string: {raw_value}"
            return True, normalized, None
        
        elif attr_schema.type == "text":
            # Long-form text, minimal validation
            if not isinstance(raw_value, str):
                return False, None, f"Expected string, got {type(raw_value).__name__}"
            normalized = raw_value.strip()
            if not normalized:
                return False, None, "Empty text"
            return True, normalized, None
        
        else:
            return False, None, f"Unknown type: {attr_schema.type}"
    
    except Exception as e:
        logger.error(f"Error validating {attr_name}: {e}")
        return False, None, str(e)


def validate_extraction(
    extracted_attrs: Dict[str, Any],
    schema: ExtractionSchema,
    strict: bool = True,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Validate full extraction result against schema.
    
    Args:
        extracted_attrs: Extracted attributes dict from LLM
        schema: ExtractionSchema
        strict: If True, reject unknown attributes; if False, ignore them
    
    Returns:
        (valid_attrs, errors_dict)
        - valid_attrs: {attr_name: canonical_value, ...} with None for missing
        - errors_dict: {attr_name: error_message, ...} for failures
    """
    valid_attrs: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    
    for attr_schema in schema.attributes:
        raw_value = extracted_attrs.get(attr_schema.name)
        
        is_valid, canonical, error_msg = validate_attribute_value(
            attr_schema.name,
            raw_value,
            attr_schema,
        )
        
        if is_valid:
            valid_attrs[attr_schema.name] = canonical
        else:
            errors[attr_schema.name] = error_msg or "Validation failed"
            valid_attrs[attr_schema.name] = None
            if attr_schema.required:
                logger.warning(
                    f"⚠️ Required attribute '{attr_schema.name}' failed: {error_msg}"
                )
    
    # Check for unknown attributes
    known_names = {a.name for a in schema.attributes}
    for key in extracted_attrs.keys():
        if key not in known_names:
            if strict:
                logger.warning(f"⚠️ Unknown attribute (rejected): '{key}'")
            else:
                logger.debug(f"ℹ️ Unknown attribute (ignored): '{key}'")
    
    return valid_attrs, errors


def batch_validate_extraction(
    batch_results: List[Dict[str, Any]],
    schema: ExtractionSchema,
) -> List[Tuple[str, Dict[str, Any], Dict[str, str]]]:
    """
    Validate a batch of extraction results.
    
    Returns:
        List of (product_id, valid_attrs, errors)
    """
    validated = []
    for result in batch_results:
        product_id = result.get("product_id", "unknown")
        extracted = result.get("attributes", {})
        
        valid_attrs, errors = validate_extraction(extracted, schema)
        validated.append((product_id, valid_attrs, errors))
    
    return validated

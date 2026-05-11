"""
ProductDetailCrawler - Service for crawling and extracting detailed product information
Uses httpx for high-performance async requests (no browser automation)
Extracts product attributes based on dynamic schemas

Fixed: Removed hallucinated endpoints. Tiki only exposes:
  GET /api/v2/products/{product_id}  →  name, brand, price, specs, description, ...
All attribute mapping is done from that single response.

HYBRID EXTRACTION:
- Structured specs extraction (priority 0)
- LLM-assisted extraction (GPT-4o-mini) as primary semantic extractor
- Deterministic regex/enum extraction as fallback
"""
from __future__ import annotations

import asyncio
import httpx
import json
import logging
import re
from typing import Dict, List, Any, Optional, Literal

import unicodedata
from typing import Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AttrType = Literal["numeric", "enum", "multi_enum", "regex"]

_FALLBACK_CAP = 20

# Patterns that are dangerously over-broad.
# We check the *stripped* pattern (after removing anchors/groups) so that
# variants like  ^(\d+)$  or  (?:\w+)  are also caught.
_DANGEROUS_BARE = frozenset({
    ".*", ".+", ".", r"\d+", r"\w+", r"\s+", r"\S+",
    "[0-9]+", "[a-z]+", "[a-zA-Z]+", "[a-z0-9]+",
})


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS (module-level, not class methods)
# ---------------------------------------------------------------------------


def _infer_attr_type(
    attr_name: str,
    value_pattern: str,
    vocabulary: List[str],
) -> AttrType:
    """
    Heuristic đoán attr_type khi schema cũ không khai báo.

    Priority:
      1. Có vocabulary → multi_enum
      2. value_pattern là wildcard → enum (sẽ degrade nếu không có vocab)
      3. value_pattern chứa \\d hoặc [0-9] → numeric
      4. Còn lại → regex
    """
    if vocabulary:
        return "multi_enum"
    if value_pattern in (".*", ".+", r"\S+", r"\w+", r"\d+", ""):
        return "enum"
    if re.search(r"\\d|\[0-9\]", value_pattern):
        return "numeric"
    return "regex"


def _build_spec_lookup(specifications: List[Dict]) -> Dict[str, str]:
    """
    Flatten structured spec list → dict (code/name → value).

    Input (Tiki API raw):
      [{"name": "Content", "attributes": [
          {"code": "hair_type", "name": "Loại tóc", "value": "Mọi loại tóc"},
          ...
      ]}, ...]

    Output:
      {"hair_type": "Mọi loại tóc", "loại tóc": "Mọi loại tóc", ...}
    """
    lookup: Dict[str, str] = {}
    for section in specifications:
        for attr in section.get("attributes", []):
            value = (attr.get("value") or "").strip()
            if not value:
                continue
            code = (attr.get("code") or "").lower().strip()
            name = (attr.get("name") or "").lower().strip()
            if code:
                lookup[code] = value
            if name:
                lookup[name] = value
    return lookup


def _lookup_in_specs(
    attr_name: str,
    keywords: List[str],
    spec_lookup: Dict[str, str],
) -> Optional[str]:
    """
    Tìm value trực tiếp trong structured spec (priority cao nhất).
    Thử attr_name trước, sau đó từng keyword.
    """
    if attr_name in spec_lookup:
        return spec_lookup[attr_name]
    for kw in keywords:
        if kw in spec_lookup:
            return spec_lookup[kw]
    return None

def _clean_html(text: str) -> str:
    """
    Strip HTML/XML tags and decode common entities.

    Keeps all text content; collapses runs of whitespace to single space.
    No external deps — pure regex.

    Examples
    --------
    "<div>Vitamin <b>C</b> 500mg</div>"  →  "Vitamin C 500mg"
    "&amp;nbsp; niacinamide&nbsp;"       →  "niacinamide"
    """
    # 1. Replace block-level tags with a space so words don't merge.
    text = re.sub(r"<(br|p|div|li|tr|td|th|h[1-6])[^>]*>", " ", text, flags=re.IGNORECASE)
    # 2. Strip remaining tags.
    text = re.sub(r"<[^>]+>", "", text)
    # 3. Decode the most common HTML entities.
    entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&nbsp;": " ", "&quot;": '"', "&#39;": "'",
        "&apos;": "'",
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    # 4. Collapse whitespace.
    return re.sub(r"\s+", " ", text).strip()


def _is_safe_pattern(pattern: str) -> bool:
    """
    Return False for patterns so generic they flood extraction with noise.

    Rules (applied in order):
    1. Empty string → reject.
    2. Strip anchors (^, $) and outer grouping then check against
        a hard-coded set of known-bad bare patterns.
    3. A pattern consisting *only* of character-class wildcards and
        quantifiers with no literal characters → reject.

    Note: length check removed — short but specific patterns like
    r"\\d+ml" or r"kg" are perfectly valid.
    """
    stripped = pattern.strip()
    if not stripped:
        return False

    # Simplify: remove anchors, non-capturing groups, word boundaries.
    simplified = re.sub(r"[\^$\\b]", "", stripped)
    simplified = re.sub(r"\(\?:|\(|\)", "", simplified)
    simplified = simplified.strip()

    if simplified in _DANGEROUS_BARE:
        return False

    # Reject if the pattern has zero literal characters — only metachar soup.
    # e.g.  [\w\s]+  or  [^\d]+  → no fixed chars → too broad.
    literal_chars = re.sub(r"\\[wWdDsS]|\[[^\]]*\]|[.+*?{}()|^$\\]", "", stripped)
    if not literal_chars.strip():
        return False

    return True


def _normalize_unicode(text: str) -> str:
    """NFC-normalise and fold typographic variants (hyphens, spaces)."""
    text = unicodedata.normalize("NFC", text)
    # Typographic hyphens → ASCII hyphen.
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    # Non-breaking / thin / hair spaces → regular space.
    text = re.sub(r"[\u00a0\u202f\u200b\u2009\u2008]", " ", text)
    return text


def _normalize_value(raw: str, attr_type: Optional[AttrType] = None) -> str:
    """
    Normalise a single extracted string value.

    Common pipeline (all types):
    1. HTML-clean residual tags
    2. Unicode normalise
    3. Strip  →  lowercase
    4. Hyphen-to-space  (Vitamin-C  →  vitamin c)
    5. Collapse internal whitespace

    Numeric extras:
    6. Strip leading unit prefix  (SPF50  →  50,  pH6.5  →  6.5)
    7. Strip trailing '+' after digit  (50+  →  50)
    8. Strip trailing unit suffix  (50ml  →  50,  200mg  →  200)
        returning the bare numeric string for easy comparison/sorting.

    Returns str always.  Caller decides whether to cast to float/int.
    """
    # 1. Residual HTML
    value = _clean_html(raw)
    # 2. Unicode
    value = _normalize_unicode(value)
    # 3-4-5.
    value = value.strip().lower().replace("-", " ")
    value = re.sub(r"\s+", " ", value).strip()

    if attr_type == "numeric":
        # 6. Strip leading alphabetic prefix (SPF50 → 50, pH6 → 6).
        value = re.sub(r"^[a-z\s]+(?=[\d.])", "", value).strip()
        # 7. Strip trailing '+' when preceded by digit.
        value = re.sub(r"(\d)\+$", r"\1", value)
        # 8. Strip trailing unit suffix (keep the number).
        #    Handles: 50ml, 200mg, 30g, 100w, 5%, 50spf etc.
        value = re.sub(
            r"(\d+(?:\.\d+)?)\s*(?:ml|mg|g|kg|l|w|watt|watts|%|spf|pa\+*|uv)$",
            r"\1",
            value,
        ).strip()

    return value


def _extract_numeric(
    text: str,
    keywords: List[str],
    value_pattern: str,
) -> Tuple[List[str], List[str], str]:
    """
    Numeric extraction.

    Strategy: regex findall inside keyword context windows.
    Falls back to capped full-text scan only if context yields nothing.
    Returns (raw_values, matched_keywords, match_type).
    """
    try:
        pattern = re.compile(value_pattern, re.IGNORECASE)
    except re.error as e:
        logger.error(f"❌ Bad numeric pattern '{value_pattern}': {e}")
        return [], [], "error"

    found: List[str] = []
    matched_kw: set = set()
    match_type = "contextual"

    for keyword in keywords:
        kw_re = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        for m in kw_re.finditer(text):
            matched_kw.add(keyword)
            start = max(0, m.start() - 120)
            end = min(len(text), m.end() + 120)
            for hit in pattern.findall(text[start:end]):
                raw = hit if isinstance(hit, str) else " ".join(x for x in hit if x)
                found.append(raw)

    if not found:
        match_type = "fallback"
        for hit in pattern.findall(text)[:_FALLBACK_CAP]:
            raw = hit if isinstance(hit, str) else " ".join(x for x in hit if x)
            found.append(raw)

    return found, list(matched_kw), match_type


def _extract_enum(
    text: str,
    keywords: List[str],           # keyword context triggers
    vocabulary: List[str],          # controlled vocabulary to match against
    multi: bool = False,
) -> Tuple[List[str], List[str], str]:
    """
    Enum / multi_enum extraction via controlled-vocabulary substring matching.

    Strategy:
    1. Find keyword context windows (±120 chars).
    2. For each window, check which vocabulary terms appear as
        word-boundary substrings.
    3. If multi=False, the first found term per window wins (enum).
        If multi=True, all found terms per window are collected (multi_enum).
    4. Fallback: scan full text for vocabulary terms (capped).

    Much more precise than regex for ingredient lists, skin-type tags, etc.
    """
    if not vocabulary:
        return [], [], "empty_vocab"

    # Pre-compile vocabulary patterns once.
    vocab_patterns = [
        (term, re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE))
        for term in vocabulary
    ]

    found: List[str] = []
    matched_kw: set = set()
    match_type = "contextual"

    for keyword in keywords:
        kw_re = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        for m in kw_re.finditer(text):
            matched_kw.add(keyword)
            start = max(0, m.start() - 120)
            end = min(len(text), m.end() + 120)
            context = text[start:end]

            window_hits: List[str] = []
            for term, pat in vocab_patterns:
                if pat.search(context):
                    window_hits.append(term)
                    if not multi:
                        break  # enum: first match per window is enough

            found.extend(window_hits)

    if not found:
        match_type = "fallback"
        for term, pat in vocab_patterns:
            if pat.search(text):
                found.append(term)
                if not multi and len(found) >= 1:
                    break
            if len(found) >= _FALLBACK_CAP:
                break

    return found, list(matched_kw), match_type


def _extract_regex(
    text: str,
    keywords: List[str],
    value_pattern: str,
) -> Tuple[List[str], List[str], str]:
    """
    Generic regex extraction — same strategy as before, cleaned up.

    Returns (raw_values, matched_keywords, match_type).
    """
    try:
        pattern = re.compile(value_pattern, re.IGNORECASE)
    except re.error as e:
        logger.error(f"❌ Bad regex pattern '{value_pattern}': {e}")
        return [], [], "error"

    found: List[str] = []
    matched_kw: set = set()
    match_type = "contextual"

    for keyword in keywords:
        kw_re = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        for m in kw_re.finditer(text):
            matched_kw.add(keyword)
            start = max(0, m.start() - 120)
            end = min(len(text), m.end() + 120)
            for hit in pattern.findall(text[start:end]):
                raw = hit if isinstance(hit, str) else " ".join(x for x in hit if x)
                found.append(raw)

    if not found:
        match_type = "fallback"
        logger.debug(f"ℹ️ Regex fallback triggered for pattern '{value_pattern}'")
        for hit in pattern.findall(text)[:_FALLBACK_CAP]:
            raw = hit if isinstance(hit, str) else " ".join(x for x in hit if x)
            found.append(raw)

    return found, list(matched_kw), match_type


def _compute_confidence(
    match_type: str,
    match_count: int,
    keywords_hit: int,
    keywords_total: int,
) -> float:
    """
    Lightweight confidence heuristic.  Range: 0.0 – 1.0.

    Signals used:
    • contextual match  > fallback match
    • at least one keyword triggered  > none triggered
    • multiple distinct values found  → slight boost
    • error / skipped              → 0.0

    This is intentionally simple — no ML, no external deps.
    Tune the weights as you build up ground-truth data.
    """
    if match_type in ("error", "skipped", "empty_vocab"):
        return 0.0

    base = 0.85 if match_type == "contextual" else 0.45

    # Keyword coverage boost (up to +0.10).
    kw_ratio = keywords_hit / max(keywords_total, 1)
    base += kw_ratio * 0.10

    # Multi-value slight boost (up to +0.05).
    if match_count >= 3:
        base += 0.05
    elif match_count >= 1:
        base += 0.02

    return round(min(base, 1.0), 2)


class ProductDetailCrawler:
    """Crawl and extract detailed product information from Tiki"""

    def __init__(
        self,
        timeout: float = 30.0,
        llm_extractor: Optional[Any] = None,
        use_llm: bool = False,
    ):
        self.base_url_tiki = "https://tiki.vn/api/v2"
        self.timeout = timeout
        self.session = None
        self.llm_extractor = llm_extractor
        self.use_llm = use_llm and HAS_LLM_SUPPORT
        
        if self.use_llm and not self.llm_extractor:
            # Auto-initialize if not provided
            if HAS_LLM_SUPPORT:
                self.llm_extractor = LLMAttributeExtractor()
                logger.info("✅ LLM extractor initialized")
        
        if self.use_llm and self.llm_extractor:
            logger.info("🤖 LLM extraction mode enabled")

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    async def _get_session(self) -> httpx.AsyncClient:
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36"
                    )
                },
            )
        return self.session

    async def close(self):
        if self.session:
            await self.session.aclose()
            self.session = None

    # ------------------------------------------------------------------
    # Core fetch — chỉ 1 endpoint thực sự tồn tại
    # ------------------------------------------------------------------

    async def _fetch_product_detail(
        self,
        session: httpx.AsyncClient,
        product_id: str,
    ) -> Dict:
        """GET /api/v2/products/{product_id}"""
        try:
            url = f"{self.base_url_tiki}/products/{product_id}"
            response = await session.get(
                url,
                params={"include": "attributes,rating_summary,seller"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch product {product_id}: {e}")
            return {}

    def _parse_product_detail(self, detail: Dict) -> Dict:
        """Parse product detail — tất cả thông tin cần thiết đều nằm ở đây"""
        return {
            "name": detail.get("name", ""),
            "brand": detail.get("brand", {}).get("name", ""),
            "price": detail.get("price", 0),
            "original_price": detail.get("original_price", 0),
            "rating_avg": detail.get("rating_average", 0),
            "rating_count": detail.get("review_count", 0),
            "thumbnail": detail.get("thumbnail_url", ""),
            "url": detail.get("url", ""),
            "description": detail.get("description", ""),
            "category": detail.get("category", {}).get("name", ""),
            "specs": self._extract_specs(detail.get("specifications", [])),
            "_raw_specifications": detail.get("specifications", []),    
        }

    def _extract_specs(self, specs: List[Dict]) -> List[Dict]:
        result = []
        for group in specs:
            result.append({
                "group": group.get("name", ""),
                "attrs": [
                    {
                        "name": attr.get("name", ""),
                        "value": attr.get("value", ""),
                    }
                    for attr in group.get("attributes", [])
                ],
            })
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def crawl_tiki_product_details(
        self,
        product_id: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crawl một sản phẩm Tiki và extract attributes theo schema.

        Args:
            product_id: Tiki product ID
            schema: Dynamic schema for attribute extraction (optional)

        Returns:
            {
                "status": "success" | "error",
                "product": {...},               # parsed product info
                "extracted_attributes": {...},  # mapped từ schema
            }
        """
        try:
            logger.info(f"📥 Crawling Tiki product: {product_id}")

            session = await self._get_session()

            raw = await self._fetch_product_detail(session, product_id)
            if not raw:
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": "Failed to fetch product details",
                }

            product = self._parse_product_detail(raw)
            product["product_id"] = product_id

            logger.info(f"✅ Fetched: {product.get('name', 'Unknown')[:60]}")

            extracted_attributes = {}
            if schema:
                extracted_attributes = self.extract_attributes_from_schema(product, schema)
                logger.info(f"📊 Extracted attributes: {list(extracted_attributes.keys())}")

            return {
                "status": "success",
                "product": product,
                "extracted_attributes": extracted_attributes,
            }

        except Exception as e:
            logger.error(f"❌ Error crawling product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "error": str(e),
            }

    async def crawl_multiple_products(
        self,
        product_ids: List[str],
        schema: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """Crawl nhiều sản phẩm đồng thời"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl(product_id: str):
            async with semaphore:
                return await self.crawl_tiki_product_details(
                    product_id=product_id,
                    schema=schema,
                )

        logger.info(
            f"📥 Crawling {len(product_ids)} products "
            f"(max_concurrent={max_concurrent})"
        )
        results = await asyncio.gather(
            *[_crawl(pid) for pid in product_ids],
            return_exceptions=False,
        )
        logger.info(f"✅ Done: {len(results)} products crawled")
        return list(results)

    async def crawl_tiki_product_details_with_llm(
        self,
        product_id: str,
        schema: Optional[Dict[str, Any]] = None,
        fallback_to_regex: bool = True,
    ) -> Dict[str, Any]:
        """
        Crawl product and extract attributes using LLM.
        
        Args:
            product_id: Tiki product ID
            schema: Dynamic schema for attribute extraction
            fallback_to_regex: If True, fall back to regex on LLM failure
        
        Returns:
            {
                "status": "success" | "error",
                "product": {...},
                "extracted_attributes": {...},  # LLM + normalized
                "extraction_method": "llm" | "regex",
            }
        """
        try:
            logger.info(f"📥 Crawling Tiki product (LLM mode): {product_id}")
            
            session = await self._get_session()
            
            raw = await self._fetch_product_detail(session, product_id)
            if not raw:
                return {
                    "status": "error",
                    "product_id": product_id,
                    "error": "Failed to fetch product details",
                }
            
            product = self._parse_product_detail(raw)
            product["product_id"] = product_id
            
            logger.info(f"✅ Fetched: {product.get('name', 'Unknown')[:60]}")
            
            extracted_attributes = {}
            extraction_method = "regex"
            
            if schema and self.use_llm:
                result = await self.extract_attributes_with_llm(
                    product=product,
                    schema=schema,
                    fallback_to_regex=fallback_to_regex,
                )
                
                extracted_attributes = result.get("final_attributes", {})
                extraction_method = result.get("method", "regex")
                
                logger.info(
                    f"📊 Extracted attributes ({extraction_method}): "
                    f"{list(extracted_attributes.keys())}"
                )
            
            return {
                "status": "success",
                "product": product,
                "extracted_attributes": extracted_attributes,
                "extraction_method": extraction_method,
            }
        
        except Exception as e:
            logger.error(f"❌ Error crawling product {product_id}: {e}")
            return {
                "status": "error",
                "product_id": product_id,
                "error": str(e),
            }

    async def crawl_multiple_products_with_llm(
        self,
        product_ids: List[str],
        schema: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5,
        fallback_to_regex: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple products with LLM extraction.
        
        Args:
            product_ids: List of Tiki product IDs
            schema: Dynamic schema for attribute extraction
            max_concurrent: Maximum concurrent crawls
            fallback_to_regex: If True, fall back to regex on LLM failure
        
        Returns:
            List of crawl results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _crawl(product_id: str):
            async with semaphore:
                return await self.crawl_tiki_product_details_with_llm(
                    product_id=product_id,
                    schema=schema,
                    fallback_to_regex=fallback_to_regex,
                )

        logger.info(
            f"📥 Crawling {len(product_ids)} products (LLM mode, "
            f"max_concurrent={max_concurrent})"
        )
        results = await asyncio.gather(
            *[_crawl(pid) for pid in product_ids],
            return_exceptions=False,
        )
        logger.info(f"✅ Done: {len(results)} products crawled with LLM")
        
        # Print stats
        success_count = sum(1 for r in results if r.get("status") == "success")
        llm_count = sum(1 for r in results if r.get("extraction_method") == "llm")
        logger.info(
            f"📊 Results: {success_count} successful, "
            f"{llm_count} via LLM, {len(results) - llm_count} fallback"
        )
        
        return list(results)

    def extract_attributes_from_schema(
        self,
        product: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        # STEP 2: clean HTML once
        description = _clean_html(product.get("description") or "").lower()
        specs_text = _clean_html(
            self._specs_to_text(product.get("specs", []))
        ).lower()
        all_text = f"{description} {specs_text}"

        # NEW: build spec lookup từ raw specifications (nếu có)
        # product cần được pass raw specs — xem note bên dưới
        raw_specs = product.get("_raw_specifications", [])
        spec_lookup = _build_spec_lookup(raw_specs)

        for attr_spec in schema.get("attributes", []):
            attr_name = attr_spec.get("name", "").lower()
            keywords = [k.lower() for k in attr_spec.get("keywords", [])]
            value_pattern = attr_spec.get("value_pattern") or ""
            vocabulary: List[str] = [
                v.lower() for v in (attr_spec.get("vocabulary") or [])
            ]

            # NEW: infer attr_type nếu schema cũ không khai báo
            attr_type: AttrType = attr_spec.get("attr_type") or _infer_attr_type(
                attr_name=attr_name,
                value_pattern=value_pattern,
                vocabulary=vocabulary,
            )

            _empty = {
                "raw_values": [], "keywords_found": [],
                "match_count": 0, "match_type": "skipped", "confidence": 0.0,
            }

            if not attr_name or not keywords:
                logger.warning(f"⚠️ Invalid attr spec (missing name/keywords): {attr_spec}")
                if attr_name:
                    extracted[attr_name] = _empty
                continue

            # NEW — PRIORITY 0: tìm trực tiếp trong structured spec
            spec_hit = _lookup_in_specs(attr_name, keywords, spec_lookup)
            if spec_hit:
                normalized_hit = _normalize_value(spec_hit, attr_type=attr_type)
                if normalized_hit:
                    extracted[attr_name] = {
                        "raw_values":     [normalized_hit],
                        "keywords_found": [],
                        "match_count":    1,
                        "match_type":     "spec_direct",
                        "confidence":     1.0,
                    }
                    logger.debug(f"✅ spec_direct hit for '{attr_name}': '{normalized_hit}'")
                    continue

            # Safety gate — chỉ apply cho pattern-based types
            if attr_type in ("numeric", "regex") and value_pattern:
                if not _is_safe_pattern(value_pattern):
                    # NEW: thay vì skip hoàn toàn, thử degrade
                    if vocabulary:
                        logger.info(
                            f"ℹ️ Unsafe pattern for '{attr_name}', "
                            "degrading to multi_enum (vocabulary available)."
                        )
                        attr_type = "multi_enum"
                    else:
                        logger.warning(
                            f"⚠️ Unsafe pattern rejected for '{attr_name}': "
                            f"'{value_pattern}' — no vocabulary to fall back to."
                        )
                        extracted[attr_name] = _empty
                        continue

            # Enum/multi_enum không có vocabulary → degrade sang regex
            if attr_type in ("enum", "multi_enum") and not vocabulary:
                logger.warning(
                    f"⚠️ Enum attr '{attr_name}' has no vocabulary; "
                    "falling back to regex extraction."
                )
                attr_type = "regex"
                # Nếu regex cũng không có pattern safe → skip
                if not value_pattern or not _is_safe_pattern(value_pattern):
                    logger.warning(
                        f"⚠️ '{attr_name}' has no vocabulary and no safe pattern — skipping."
                    )
                    extracted[attr_name] = _empty
                    continue

            extraction_result = self._extract_attribute_by_keywords(
                text=all_text,
                keywords=keywords,
                value_pattern=value_pattern,
                attr_type=attr_type,
                vocabulary=vocabulary,
            )
            extracted[attr_name] = extraction_result

        return extracted

    # ------------------------------------------------------------------
    # LLM EXTRACTION METHODS
    # ------------------------------------------------------------------

    def _build_product_text_for_llm(self, product: Dict[str, Any]) -> str:
        """
        Build compact product text for LLM extraction.
        
        Combines: name + brand + description + specs
        Returns concise but information-rich text.
        """
        parts = []
        
        if product.get("name"):
            parts.append(f"Product: {product['name']}")
        
        if product.get("brand"):
            parts.append(f"Brand: {product['brand']}")
        
        if product.get("category"):
            parts.append(f"Category: {product['category']}")
        
        if product.get("description"):
            desc = _clean_html(product["description"])
            parts.append(f"Description: {desc}")
        
        if product.get("specs"):
            specs_text = self._specs_to_text(product["specs"])
            if specs_text:
                parts.append(f"Specifications: {specs_text}")
        
        return "\n".join(parts)

    def _convert_schema_to_llm_schema(
        self,
        schema: Dict[str, Any],
    ) -> Optional[ExtractionSchema]:
        """
        Convert old-style schema to LLM-compatible schema.
        
        Old schema format (keywords/patterns):
        {
            "attributes": [
                {
                    "name": "dpi",
                    "keywords": ["dpi", "dots per inch"],
                    "attr_type": "numeric",
                    "value_pattern": r"\d+"
                }
            ]
        }
        
        New schema format (types/constraints):
        {
            "category": "computer_mouse",
            "attributes": [
                {
                    "name": "dpi",
                    "type": "number",
                    "min_value": 400,
                    "max_value": 16000
                }
            ]
        }
        """
        try:
            if not schema or not schema.get("attributes"):
                return None
            
            # Try to infer type from old-style schema
            llm_attrs = []
            for attr_spec in schema.get("attributes", []):
                attr_name = attr_spec.get("name", "").lower().strip()
                if not attr_name:
                    continue
                
                # Determine LLM-compatible type
                attr_type_str = attr_spec.get("attr_type", "regex")
                vocabulary = attr_spec.get("vocabulary", [])
                
                if attr_type_str == "numeric":
                    llm_type = "number"
                elif vocabulary:
                    llm_type = "multi_enum" if len(vocabulary) > 1 else "enum"
                else:
                    llm_type = "string"
                
                llm_attr = AttributeSchema(
                    name=attr_name,
                    type=llm_type,
                    required=attr_spec.get("required", False),
                    allowed_values=vocabulary if vocabulary else None,
                )
                llm_attrs.append(llm_attr)
            
            return ExtractionSchema(
                category=schema.get("category", "product"),
                attributes=llm_attrs,
            )
        
        except Exception as e:
            logger.error(f"❌ Failed to convert schema to LLM format: {e}")
            return None

    async def extract_attributes_with_llm(
        self,
        product: Dict[str, Any],
        schema: Dict[str, Any],
        fallback_to_regex: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract attributes using LLM as primary extractor.
        
        Pipeline:
        1. Structured specs extraction (highest priority)
        2. LLM semantic extraction (GPT-4o-mini)
        3. Normalize values
        4. [Optional] Fallback to regex if LLM fails
        
        Args:
            product: Product dict with name, description, specs, etc.
            schema: Dynamic schema for attribute extraction
            fallback_to_regex: If True, fall back to regex on LLM failure
        
        Returns:
            {
                "llm_result": {...},          # LLM extraction result
                "structured_specs": {...},    # Direct structured spec hits
                "final_attributes": {...},    # Combined final result
                "method": "llm" | "regex" | "fallback",
            }
        """
        if not self.llm_extractor:
            logger.warning("⚠️ LLM extractor not available, falling back to regex")
            if fallback_to_regex:
                regex_result = self.extract_attributes_from_schema(product, schema)
                return {
                    "llm_result": {},
                    "final_attributes": regex_result,
                    "method": "regex",
                    "error": "LLM extractor not initialized",
                }
            return {"error": "LLM extractor not available"}
        
        try:
            # STEP 1: Structured specs extraction (priority 0)
            raw_specs = product.get("_raw_specifications", [])
            spec_lookup = _build_spec_lookup(raw_specs)
            structured_specs = {}
            
            for attr_spec in schema.get("attributes", []):
                attr_name = attr_spec.get("name", "").lower()
                keywords = [k.lower() for k in attr_spec.get("keywords", [])]
                
                spec_hit = _lookup_in_specs(attr_name, keywords, spec_lookup)
                if spec_hit:
                    attr_type = attr_spec.get("attr_type", "regex")
                    normalized = _normalize_value(spec_hit, attr_type=attr_type)
                    if normalized:
                        structured_specs[attr_name] = normalized
            
            logger.debug(f"📊 Structured spec hits: {list(structured_specs.keys())}")
            
            # STEP 2: LLM extraction
            llm_schema = self._convert_schema_to_llm_schema(schema)
            if not llm_schema:
                raise ValueError("Failed to convert schema to LLM format")
            
            # Build compact product text
            product_text = self._build_product_text_for_llm(product)
            
            # Call LLM
            logger.info("🤖 Calling LLM for attribute extraction...")
            llm_results = await self.llm_extractor.extract_batch(
                products=[
                    {
                        "product_id": product.get("product_id", "unknown"),
                        "text": product_text,
                    }
                ],
                schema=llm_schema,
            )
            
            if not llm_results or not llm_results[0].is_valid():
                error_msg = (
                    llm_results[0].error
                    if llm_results and llm_results[0].error
                    else "Unknown LLM error"
                )
                logger.warning(f"⚠️ LLM extraction failed: {error_msg}")
                
                if fallback_to_regex:
                    logger.info("🔄 Falling back to regex extraction...")
                    regex_result = self.extract_attributes_from_schema(product, schema)
                    return {
                        "llm_result": {},
                        "structured_specs": structured_specs,
                        "final_attributes": regex_result,
                        "method": "regex",
                        "llm_error": error_msg,
                    }
                raise ValueError(f"LLM extraction failed: {error_msg}")
            
            llm_attrs = llm_results[0].attributes
            logger.info(f"✅ LLM extracted: {list(llm_attrs.keys())}")
            
            # STEP 3: Merge structured specs (priority) + LLM results
            final_attributes = {}
            for attr_spec in schema.get("attributes", []):
                attr_name = attr_spec.get("name", "").lower()
                
                # Priority: structured specs > LLM > None
                if attr_name in structured_specs:
                    final_attributes[attr_name] = structured_specs[attr_name]
                elif attr_name in llm_attrs:
                    final_attributes[attr_name] = llm_attrs[attr_name]
                else:
                    final_attributes[attr_name] = None
            
            return {
                "llm_result": llm_attrs,
                "structured_specs": structured_specs,
                "final_attributes": final_attributes,
                "confidence": llm_results[0].confidence,
                "method": "llm",
            }
        
        except Exception as e:
            logger.error(f"❌ LLM extraction error: {e}")
            if fallback_to_regex:
                logger.info("🔄 Falling back to regex extraction...")
                regex_result = self.extract_attributes_from_schema(product, schema)
                return {
                    "llm_result": {},
                    "structured_specs": {},
                    "final_attributes": regex_result,
                    "method": "regex",
                    "error": str(e),
                }
            raise

    def _extract_attribute_by_keywords(
        self,
        text: str,
        keywords: List[str],
        value_pattern: str,
        attr_type: AttrType = "regex",
        vocabulary: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract ALL matching values from text using a strategy chosen by attr_type.

        attr_type routing:
        "numeric"    → _extract_numeric  → numeric normalize (strips units)
        "enum"       → _extract_enum     → single vocab match per context
        "multi_enum" → _extract_enum     → all vocab matches per context
        "regex"      → _extract_regex    → generic contextual findall

        Output format (always):
        {
            "raw_values":     List[str],   # normalized, deduplicated
            "keywords_found": List[str],
            "match_count":    int,
            "match_type":     str,         # "contextual" | "fallback" | "error" | "skipped"
            "confidence":     float,       # 0.0 – 1.0  (heuristic)
        }
        """
        vocabulary = vocabulary or []

        # Route to the right strategy.
        if attr_type == "numeric":
            if not value_pattern:
                return {
                    "raw_values": [], "keywords_found": [],
                    "match_count": 0, "match_type": "skipped", "confidence": 0.0,
                }
            raw_values, matched_kw, match_type = _extract_numeric(
                text, keywords, value_pattern
            )

        elif attr_type in ("enum", "multi_enum"):
            raw_values, matched_kw, match_type = _extract_enum(
                text, keywords, vocabulary, multi=(attr_type == "multi_enum")
            )

        else:  # "regex" or unknown
            if not value_pattern:
                return {
                    "raw_values": [], "keywords_found": [],
                    "match_count": 0, "match_type": "skipped", "confidence": 0.0,
                }
            raw_values, matched_kw, match_type = _extract_regex(
                text, keywords, value_pattern
            )

        # STEP 5: type-aware normalisation.
        normalized: List[str] = []
        for v in raw_values:
            n = _normalize_value(v, attr_type=attr_type)
            if n:
                normalized.append(n)

        # STEP 3 (dedup): order-preserving.
        seen: set = set()
        unique: List[str] = []
        for v in normalized:
            if v not in seen:
                seen.add(v)
                unique.append(v)

        # Heuristic confidence score.
        confidence = _compute_confidence(
            match_type=match_type,
            match_count=len(unique),
            keywords_hit=len(matched_kw),
            keywords_total=len(keywords),
        )

        return {
            "raw_values":     unique,
            "keywords_found": list(matched_kw),
            "match_count":    len(unique),
            "match_type":     match_type,
            "confidence":     confidence,
        }

    def _specs_to_text(self, specs: List[Dict]) -> str:
        """Flatten specs list thành plain text để search"""
        parts = []
        for group in specs:
            parts.append(group.get("group", ""))
            for attr in group.get("attrs", []):
                parts.append(f"{attr.get('name', '')} {attr.get('value', '')}")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# LLM EXTRACTION INTEGRATION
# ---------------------------------------------------------------------------

try:
    from extraction import (
        LLMAttributeExtractor,
        ExtractionSchema,
        AttributeSchema,
    )
    HAS_LLM_SUPPORT = True
except ImportError as e:   
    HAS_LLM_SUPPORT = False
    logger.warning(f"⚠️ LLM extraction not available: {e}")

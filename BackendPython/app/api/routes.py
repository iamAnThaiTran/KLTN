# app/api/routes.py

import asyncio
import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.core.orchestrator import RecommendationOrchestrator
from app.api.sku_routes import router as sku_router
from app.api.progressive_search_routes import router as progressive_search_router
from app.crawler.crawler import TikiCrawler
from app.db.sku_repository import SKURepository
# from app.core.crawler import YourCrawler  # Import your crawler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(name)s] %(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger("routes")

def log_analyze(msg):
    """Helper để log messages từ /api/analyze"""
    print(msg, flush=True)  # Also print for console
    logger.info(msg)  # And log it

app = FastAPI(title="Smart Product Recommendation API")

# Register routers
app.include_router(sku_router)
app.include_router(progressive_search_router)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== MODELS =====

class QueryRequest(BaseModel):
    """Initial query từ user"""
    user_input: str
    conversation_id: Optional[str] = None

class ResponseUpdate(BaseModel):
    """User response to a question"""
    conversation_id: str
    question_type: str  # "category" | "attribute"
    value: str
    attribute_name: Optional[str] = None

# ===== IN-MEMORY SESSION STORAGE =====
# Trong production, dùng Redis
sessions = {}

# ===== INITIALIZE ORCHESTRATOR =====
# Giả sử bạn có YourCrawler class
# crawler = YourCrawler()
# orchestrator = RecommendationOrchestrator(crawler)

# Mock crawler cho demo
class MockCrawler:
    def crawl(self, category, attributes):
        # Mock data
        return [
            {
                "name": "Nike Air Max 90",
                "price": 1800000,
                "description": "Giày thể thao cao cấp",
                "attributes": {
                    "loai": "thể thao",
                    "size": "42",
                    "mau": "trắng"
                }
            },
            {
                "name": "Adidas Ultraboost",
                "price": 2100000,
                "description": "Giày chạy bộ",
                "attributes": {
                    "loai": "chạy bộ",
                    "size": "42"
                }
            }
        ]

orchestrator = RecommendationOrchestrator()
sku_repo = SKURepository()  # Initialize SKU repository for filters

# ===== ENDPOINTS =====

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """
    Process user query
    
    Response types:
    1. need_info: Cần hỏi thêm thông tin
    2. searching: Đang crawl
    3. results: Có kết quả + filters
    """
    
    # Get or create session
    conversation_id = request.conversation_id
    if not conversation_id:
        import uuid
        conversation_id = str(uuid.uuid4())
        sessions[conversation_id] = None
    
    conversation_state = sessions.get(conversation_id)
    
    # Process
    result = await orchestrator.process_query(
        user_input=request.user_input,
        conversation_state=conversation_state
    )
    
    # Save state
    sessions[conversation_id] = result.get("state")
    
    # Add conversation_id to response
    result["conversation_id"] = conversation_id
    
    # NEW: If we have results and a category, fetch filters from DB
    if result.get("status") == "results" and result.get("state", {}).get("category"):
        try:
            category_name = result["state"]["category"]
            # Get category slug from category name
            from app.services.category_validator import CategoryValidator
            validator = CategoryValidator()
            validation = validator.validate_category(category_name)
            
            if validation["success"]:
                category_slug = sku_repo.get_category_slug_from_name(validation["category"])
                if category_slug:
                    # Fetch filters from DB
                    available_filters = sku_repo.get_available_filters(category_slug)
                    
                    # Build filter groups same as /api/v1/crawl-products
                    from app.models.sku_models import FilterGroup, FilterOption
                    filter_groups = []
                    for f in available_filters:
                        filter_groups.append({
                            "attribute_name": f['attribute_name'],
                            "display_name": f['display_name'] or f['attribute_name'],
                            "data_type": f['data_type'],
                            "options": [
                                {"attribute_value": opt.get('attribute_value'), "product_count": opt.get('product_count')}
                                for opt in f['options']
                                if opt.get('attribute_value') is not None
                            ]
                        })
                    
                    # Add filters to response
                    result["filters"] = filter_groups
                    print(f"✅ Added {len(filter_groups)} filter groups to query response")
                    
        except Exception as e:
            print(f"⚠️ Error fetching filters: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the request if filters fail
            result["filters"] = []
    
    return result

@app.post("/api/analyze")
async def analyze_query(request: QueryRequest):
    """
    FAST endpoint: Analyze user input + get initial products
    
    Flow:
    1. Detect category from user input
    2. Get attributes/filters from DB
    3. **Search DB with category + empty filters to get initial products**
    4. If no products, crawl the web
    5. Return: category, hints, filters, initial_products
    
    Returns:
    {
        "success": True,
        "category": "giày",
        "clarifying_hints": ["👟 Giới tính: Nam / Nữ?", ...],
        "filters": [{
            "attribute_name": "gender",
            "display_name": "Giới tính",
            "options": [{"attribute_value": "Nam", "product_count": 25}]
        }],
        "products": [initial products from DB],
        "total": 25,
        "total_pages": 2
    }
    """
    
    try:
        logger.info(f"\n{'='*100}")
        logger.info(f"[/api/analyze] ✅ ENDPOINT HIT!")
        logger.info(f"[/api/analyze] Request: {request.user_input}")
        logger.info(f"{'='*100}")
        
        log_analyze(f"[/api/analyze] Starting analysis...")
        
        # Get or create session
        conversation_id = request.conversation_id
        if not conversation_id:
            import uuid
            conversation_id = str(uuid.uuid4())
            sessions[conversation_id] = None
        
        conversation_state = sessions.get(conversation_id)
        
        # Step 1: Detect category only (FAST - no crawl)
        # Use the intent mapper + quick detection
        from app.core.intent_mapper import IntentMapper
        from app.services.category_validator import CategoryValidator
        from app.core.extractor import AttributeExtractor
        
        intent_mapper = IntentMapper()
        validator = CategoryValidator()
        attr_extractor = AttributeExtractor()
        
        # Detect intent + category
        intent_result = intent_mapper.map_intent(request.user_input)
        
        if intent_result.get("intent") and intent_result.get("categories"):
            # Pick first category
            category = intent_result["categories"][0]
            print(f"[/api/analyze] Detected category: {category}")
        else:
            # Try rule-based detection as fallback
            from app.core.orchestrator import RecommendationOrchestrator
            orch = RecommendationOrchestrator()
            detected = orch._quick_category_detection(request.user_input)
            if detected.get("category"):
                category = detected["category"]
                print(f"[/api/analyze] Rule-based category: {category}")
            else:
                return {
                    "success": False,
                    "error": "Không detect được loại sản phẩm",
                    "conversation_id": conversation_id
                }
        
        # Validate category
        validation = validator.validate_category(category)
        if not validation["success"]:
            return {
                "success": False,
                "error": f"Danh mục không hợp lệ: {category}",
                "conversation_id": conversation_id
            }
        
        validated_category = validation["category"]
        
        # NEW: Step 1.5 - Extract attributes from user input
        print(f"\n{'='*80}")
        print(f"[/api/analyze] 🔍 EXTRACTION PHASE")
        print(f"{'='*80}")
        print(f"[/api/analyze] Input: '{request.user_input}'")
        print(f"[/api/analyze] Category: '{validated_category}'")
        
        extraction_result = attr_extractor.extract(request.user_input, validated_category, use_llm=False)
        extracted_attrs = extraction_result.get("extracted", {})
        
        print(f"[/api/analyze] Extraction method: {extraction_result.get('method', 'unknown')}")
        print(f"[/api/analyze] Extraction confidence: {extraction_result.get('confidence', 0):.2f}")
        print(f"[/api/analyze] ✅ Extracted attributes:")
        for attr, value in extracted_attrs.items():
            print(f"   - {attr}: {value} (type: {type(value).__name__})")
        if not extracted_attrs:
            print(f"   (none)")
        
        # Step 2: Fetch filters from DB (FAST)
        try:
            category_slug = sku_repo.get_category_slug_from_name(validated_category)
            
            # NEW: If category not in DB, crawl web + save to DB
            if not category_slug:
                log_analyze(f"\n{'='*80}")
                log_analyze(f"[/api/analyze] 🌐 CRAWL PHASE (Category not in DB)")
                log_analyze(f"[/api/analyze] Category '{validated_category}' not in DB, crawling web...")
                log_analyze(f"{'='*80}")
                
                try:
                    # Step 1: Crawl with extracted attributes
                    crawler = TikiCrawler()
                    crawled_products = await crawler.crawl(
                        category=validated_category,
                        attributes=extracted_attrs,
                        get_details=True
                    )
                    
                    log_analyze(f"[/api/analyze] ✅ Crawled {len(crawled_products)} products from web")
                    
                    if not crawled_products:
                        return {
                            "success": False,
                            "error": f"Không tìm được sản phẩm '{validated_category}' trên web",
                            "conversation_id": conversation_id
                        }
                    
                    # Step 2: Extract actual schema from crawled data
                    from app.services.schema_reconciler import SchemaReconciler
                    reconciler = SchemaReconciler()
                    
                    actual_schema = reconciler.extract_actual_schema(crawled_products)
                    log_analyze(f"[/api/analyze] ✅ Extracted actual schema: {len(actual_schema)} attributes")
                    
                    # Step 3: Reconcile LLM predicted schema vs actual schema
                    llm_schema = {
                        attr: {"type": "text", "values": []}
                        for attr in extracted_attrs.keys()
                    }
                    final_schema = reconciler.reconcile_schemas(llm_schema, actual_schema)
                    
                    # Step 4: Get category ID (just created)
                    new_category_id = validation.get("category_id")
                    
                    # Step 5: Save products to DB
                    saved_count = reconciler.save_products_to_db(
                        validated_category,
                        new_category_id,
                        crawled_products,
                        final_schema
                    )
                    
                    # Step 6: Save schema to DB
                    reconciler.save_schema_to_db(
                        new_category_id,
                        validated_category,
                        final_schema
                    )
                    
                    log_analyze(f"[/api/analyze] ✅ Saved {saved_count} products + schema to DB")
                    
                    # Return results
                    initial_products = crawled_products[:20]
                    total_products = len(crawled_products)
                    total_pages = (total_products + 19) // 20
                    
                    return {
                        "success": True,
                        "category": validated_category,
                        "clarifying_hints": [],
                        "filters": [],
                        "products": initial_products,
                        "total": total_products,
                        "total_pages": total_pages,
                        "conversation_id": conversation_id,
                        "source": "crawled"  # Mark as crawled data
                    }
                        
                except Exception as crawl_error:
                    log_analyze(f"[/api/analyze] ❌ Crawl error: {crawl_error}")
                    return {
                        "success": False,
                        "error": f"Lỗi crawl web: {str(crawl_error)}",
                        "conversation_id": conversation_id
                    }
            
            # Category exists in DB, continue normal flow
            
            # Get filters
            available_filters = sku_repo.get_available_filters(category_slug)
            
            # Build filter groups
            filter_groups = []
            for f in available_filters:
                filter_groups.append({
                    "attribute_name": f['attribute_name'],
                    "display_name": f['display_name'] or f['attribute_name'],
                    "data_type": f['data_type'],
                    "options": [
                        {"attribute_value": opt.get('attribute_value'), "product_count": opt.get('product_count')}
                        for opt in f['options']
                        if opt.get('attribute_value') is not None
                    ]
                })
            
            print(f"[/api/analyze] Fetched {len(filter_groups)} filters from DB")
            
        except Exception as e:
            print(f"[/api/analyze] ⚠️ Error fetching filters: {e}")
            filter_groups = []
        
        # Step 3: Search DB with extracted attributes (build query from extracted data)
        print(f"\n{'='*80}")
        print(f"[/api/analyze] 🔎 SEARCH PHASE")
        print(f"{'='*80}")
        print(f"[/api/analyze] Category slug: '{category_slug}'")
        
        try:
            # Convert extracted attributes to filter format {attr: [value]}
            search_filters = {}
            min_price = None
            max_price = None
            
            for attr_name, attr_value in extracted_attrs.items():
                if attr_value is None:
                    continue
                
                # Special handling for price (range)
                if attr_name == "gia" and isinstance(attr_value, dict):
                    min_price = attr_value.get("min")
                    max_price = attr_value.get("max")
                    print(f"[/api/analyze] 💰 Price range extracted: {min_price} - {max_price}")
                # Handle list values
                elif isinstance(attr_value, list):
                    search_filters[attr_name] = attr_value
                # Handle single values - wrap in list
                elif isinstance(attr_value, (str, int, float)):
                    search_filters[attr_name] = [str(attr_value)]
                else:
                    # Skip dict or other complex types
                    continue
            
            print(f"[/api/analyze] 📊 Search filters (converted from extracted attributes):")
            for filter_name, filter_value in search_filters.items():
                print(f"   - {filter_name}: {filter_value}")
            if not search_filters and not min_price and not max_price:
                print(f"   (no filters - using category only)")
            
            print(f"[/api/analyze] 🔗 Calling: sku_repo.search_products(")
            print(f"   category_slug='{category_slug}',")
            print(f"   filters={search_filters},")
            print(f"   min_price={min_price},")
            print(f"   max_price={max_price},")
            print(f"   page=1,")
            print(f"   page_size=20")
            print(f")")
            
            # search_products returns (products_list, total_count) tuple
            initial_products, total_products = sku_repo.search_products(
                category_slug, 
                filters=search_filters,  # ✅ NOW using extracted attributes
                min_price=min_price,
                max_price=max_price,
                page=1, 
                page_size=20
            )
            
            print(f"[/api/analyze] ✅ Search result: {total_products} products found")
            if initial_products:
                print(f"[/api/analyze] First 3 products:")
                for i, prod in enumerate(initial_products[:3]):
                    print(f"   {i+1}. {prod.get('title', 'N/A')}")
                    attrs = prod.get('attributes', {})
                    if attrs:
                        for k, v in list(attrs.items())[:3]:
                            print(f"      - {k}: {v}")
            
            # Calculate total pages
            page_size = 20
            total_pages = (total_products + page_size - 1) // page_size  # Ceiling division
            
            # If no products found with extracted filters, fallback to category-only search
            if total_products == 0 and (search_filters or min_price or max_price):
                print(f"[/api/analyze] ⚠️ No products found with extracted filters!")
                print(f"[/api/analyze] 🔄 Fallback: Trying category-only search (no filters)...")
                initial_products, total_products = sku_repo.search_products(
                    category_slug, 
                    filters={},  # Fallback to empty filters
                    min_price=None,
                    max_price=None,
                    page=1, 
                    page_size=20
                )
                print(f"[/api/analyze] ✅ Fallback result: {total_products} products found (category-only)")
                total_pages = (total_products + page_size - 1) // page_size
            
        except Exception as e:
            print(f"[/api/analyze] ❌ Error searching products: {e}")
            import traceback
            traceback.print_exc()
            initial_products = []
            total_products = 0
            total_pages = 0
        
        # Step 4: Generate clarifying hints from filter names
        from app.core.dialogue import DialogueManager
        dialogue_mgr = DialogueManager()
        
        # Map filter attribute_names to user-friendly hints
        hints = _generate_hints_from_filters(validated_category, filter_groups)
        
        print(f"\n{'='*80}")
        print(f"[/api/analyze] 💡 RESPONSE PHASE")
        print(f"{'='*80}")
        print(f"[/api/analyze] Generated {len(hints)} hints from filters")
        for i, hint in enumerate(hints[:3]):
            print(f"   {i+1}. {hint}")
        print(f"[/api/analyze] Available filters: {len(filter_groups)} groups")
        print(f"[/api/analyze] Final response:")
        print(f"   - success: True")
        print(f"   - category: {validated_category}")
        print(f"   - products: {len(initial_products)}")
        print(f"   - total: {total_products}")
        print(f"[/api/analyze] {'='*80}\n")
        
        # Save partial state for later search
        if conversation_state is None:
            conversation_state = {}
        conversation_state["has_category"] = True
        conversation_state["category"] = validated_category
        conversation_state["category_id"] = validation.get("category_id")
        conversation_state["extracted_attributes"] = extracted_attrs  # ✅ NEW: Save extracted attributes
        sessions[conversation_id] = conversation_state
        
        return {
            "success": True,
            "category": validated_category,
            "clarifying_hints": hints,
            "filters": filter_groups,
            "products": initial_products,  # ✅ NEW: Initial products from DB
            "total": total_products,  # ✅ NEW
            "total_pages": total_pages,  # ✅ NEW
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        print(f"[/api/analyze] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "conversation_id": request.conversation_id or "unknown"
        }

@app.post("/api/respond")
async def respond_to_question(request: ResponseUpdate):
    """
    User responds to a question (chọn category hoặc attribute)
    """
    
    conversation_id = request.conversation_id
    
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    conversation_state = sessions[conversation_id]
    
    # Update state với response của user
    updated_state = orchestrator.update_state(
        conversation_state,
        {
            "question_type": request.question_type,
            "value": request.value,
            "attribute_name": request.attribute_name
        }
    )
    
    sessions[conversation_id] = updated_state
    
    # Continue processing với state mới
    # Gửi empty string vì user đã trả lời rồi
    result = await orchestrator.process_query(
        user_input="",  
        conversation_state=updated_state
    )
    
    result["conversation_id"] = conversation_id
    
    return result

@app.get("/api/session/{conversation_id}")
async def get_session(conversation_id: str):
    """Debug endpoint: xem session state"""
    if conversation_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "conversation_id": conversation_id,
        "state": sessions[conversation_id]
    }

@app.delete("/api/session/{conversation_id}")
async def clear_session(conversation_id: str):
    """Clear session"""
    if conversation_id in sessions:
        del sessions[conversation_id]
    
    return {"message": "Session cleared"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/v1/crawl/tiki")
async def crawl_tiki(request: Dict[str, Any]):
    """
    Crawl real products from Tiki and auto-save to database
    
    Request:
    {
        "category": "giày",
        "attributes": {}
    }
    
    Response:
    {
        "success": true,
        "total_products": 30,
        "message": "Crawled and saved products to SKU database"
    }
    """
    try:
        category = request.get("category", "giày")
        attributes = request.get("attributes", {})
        
        # Run crawler
        crawler = TikiCrawler()
        results = await crawler.crawl(
            category=category,
            attributes=attributes,
            get_details=True  # Always get details to extract attributes
        )
        
        return {
            "success": True,
            "total_products": len(results),
            "message": f"Crawled {len(results)} products from Tiki and saved to database",
            "products": [
                {
                    "title": p.get("title"),
                    "price": p.get("price"),
                    "brand": p.get("brand"),
                    "attributes": p.get("extracted_attributes", {})
                }
                for p in results[:5]  # Return first 5
            ]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

# ===== EXAMPLE USAGE =====

"""
Flow 1: Query mơ hồ
----------------------
POST /api/query
{
  "user_input": "tôi muốn mua quà"
}

Response:
{
  "status": "need_info",
  "question": "Bạn muốn mua quà gì? Chọn một loại sản phẩm:",
  "options": [
    {"label": "Giày", "value": "giày"},
    {"label": "Bột giặt", "value": "bột giặt"}
  ],
  "conversation_id": "abc-123"
}

POST /api/respond
{
  "conversation_id": "abc-123",
  "question_type": "category",
  "value": "giày"
}

Response:
{
  "status": "need_info",
  "question": "Bạn cần giày loại nào?",
  "options": [
    {"label": "Thể thao", "value": "thể thao"},
    ...
  ]
}

... (tiếp tục hỏi cho đến khi đủ info)

Final Response:
{
  "status": "results",
  "products": [
    {
      "name": "Nike Air Max 90",
      "price": 1800000,
      "match_score": 85,
      "explanation": "Phù hợp với yêu cầu giày thể thao..."
    }
  ]
}

Flow 2: Query cụ thể
----------------------
POST /api/query
{
  "user_input": "giày thể thao size 42 màu trắng"
}

Response:
{
  "status": "results",
  "products": [...]
}
"""

# ===== HELPER FUNCTIONS =====

def _generate_hints_from_filters(category: str, filters: list) -> list:
    """
    Generate clarifying hints from available filters
    
    Maps filter attribute_names to user-friendly questions
    
    Example:
    Input:  filters = [
        {"attribute_name": "gender", "display_name": "Giới tính", ...},
        {"attribute_name": "size", "display_name": "Size", ...},
        {"attribute_name": "color", "display_name": "Màu sắc", ...}
    ]
    
    Output: [
        "👟 Giới tính: Nam / Nữ?",
        "📏 Size: 35-45?",
        "🎨 Màu sắc?"
    ]
    """
    
    # Map attribute_name → emoji + question
    hint_map = {
        "gender": ("👟", "Giới tính: Nam / Nữ?"),
        "size": ("📏", "Size: 35-45?"),
        "mau": ("🎨", "Màu sắc?"),
        "color": ("🎨", "Màu sắc?"),
        "loai": ("🏷️", "Loại nào?"),
        "type": ("🏷️", "Loại nào?"),
        "gia": ("💰", "Giá bao nhiêu?"),
        "price": ("💰", "Giá bao nhiêu?"),
        "muc_dich": ("🎯", "Mục đích sử dụng?"),
        "purpose": ("🎯", "Mục đích sử dụng?"),
        "material": ("🧵", "Chất liệu?"),
        "brand": ("🏢", "Thương hiệu?"),
        "style": ("✨", "Phong cách?"),
        "pattern": ("🎨", "Họa tiết?"),
    }
    
    hints = []
    priority_attrs = ["gender", "size", "mau", "color", "gia", "price", "muc_dich", "purpose"]
    
    # Priority: hỏi những attribute quan trọng nhất
    for attr in priority_attrs:
        for f in filters:
            if f["attribute_name"].lower() == attr.lower():
                emoji, question = hint_map.get(attr, ("❓", f"{f['display_name']}?"))
                hints.append(f"{emoji} {question}")
                break
    
    # Nếu chưa đủ 3 hints, thêm từ filters còn lại
    if len(hints) < 3:
        for f in filters:
            if len(hints) >= 3:
                break
            attr_name = f["attribute_name"].lower()
            if not any(h.endswith(f["display_name"] + "?") for h in hints):
                emoji, _ = hint_map.get(attr_name, ("❓", f"{f['display_name']}?"))
                hints.append(f"{emoji} {f['display_name']}?")
    
    # Return top 3
    return hints[:3]
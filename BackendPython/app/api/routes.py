# app/api/routes.py

import asyncio
import logging
import sys
import uuid
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.core.orchestrator import RecommendationOrchestrator
from app.api.sku_routes import router as sku_router
from app.api.progressive_search_routes import router as progressive_search_router
from app.api.product_automation_routes import router as product_automation_router
from app.crawler.crawler import TikiCrawler
from app.db.sku_repository import SKURepository
from app.services.session_manager import get_session_manager
# from app.core.crawler import YourCrawler  # Import your crawler

# Configure logging with immediate flush
class FlushingStreamHandler(logging.StreamHandler):
    """Custom handler that flushes after each log"""
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.stream.flush()  # 👈 Force flush immediately
        except Exception:
            self.handleError(record)

handler = FlushingStreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('[%(name)s] %(levelname)s: %(message)s'))
logging.root.addHandler(handler)
logging.root.setLevel(logging.DEBUG)
logger = logging.getLogger("routes")

def log_analyze(msg):
    """Helper để log messages từ /api/analyze"""
    print(msg, flush=True)  # Also print for console
    logger.info(msg)  # And log it

app = FastAPI(title="Smart Product Recommendation API")

# Register routers
app.include_router(sku_router)
app.include_router(progressive_search_router)
app.include_router(product_automation_router)  # ✅ NEW: Product automation routes

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

# ===== SESSION MANAGEMENT =====
# Using Redis with in-memory fallback
session_manager = get_session_manager()
print(f"[Routes] Session storage type: {session_manager.get_storage_type()}", flush=True)

# ===== INITIALIZE ORCHESTRATOR =====
# Giả sử bạn có YourCrawler class
# crawler = YourCrawler()
# orchestrator = RecommendationOrchestrator(crawler)

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
    print('vao api query', flush=True)
    
    # Get or create session
    conversation_id = request.conversation_id
    if not conversation_id:
        # Auto-generate conversation_id
        conversation_id = session_manager.create_session()
    
    conversation_state = session_manager.get_session(conversation_id)
    
    # Process
    result = await orchestrator.process_query(
        user_input=request.user_input,
        conversation_state=conversation_state
    )
    
    # Save state
    session_manager.set_session(conversation_id, result.get("state"))
    
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
                    print(f"✅ Added {len(filter_groups)} filter groups to query response", flush=True)
                    
        except Exception as e:
            print(f"⚠️ Error fetching filters: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Don't fail the request if filters fail
            result["filters"] = []
    
    return result

@app.post("/api/analyze")
async def analyze_query(request: QueryRequest):
    """
    FAST endpoint: Analyze user input + get initial products
    
    ✅ NOW using orchestrator.process_query() with 7-case routing
    
    Returns (same format as before):
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
        "total_pages": 2,
        "conversation_id": "abc123",
        "selected_attributes": {"brand": "Nike", ...}
    }
    """
    
    try:
        logger.info(f"\n{'='*100}")
        logger.info(f"[/api/analyze] ✅ ENDPOINT HIT!")
        logger.info(f"[/api/analyze] Request: {request.user_input}")
        
        print(f"[/api/analyze] Starting analysis with orchestrator...", flush=True)
        
        # Step 1: Get or create session
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = session_manager.create_session()
        logger.info(f"[/api/analyze] Conversation ID: {conversation_id}")
        
        conversation_state = session_manager.get_session(conversation_id)
        logger.info(f"[/api/analyze] Initial conversation state: {conversation_state}")
        if conversation_state is None:
            conversation_state = {
                "has_category": False,
                "category": None,
                "extracted": {},
                "missing_required": [],
                "search_history": [],
                "attributes_asked": [],
                "cached_products": None,
                "cached_filters": None,
                "last_crawl_params": None,
                "cache_hits": 0,
                "cache_misses": 0
            }
        
        # Step 2: ✅ USE ORCHESTRATOR - Let it handle all 7 cases!
        logger.info(f"[/api/analyze] Calling orchestrator.process_query()...", flush=True)
        orch_result = await orchestrator.process_query(
            user_input=request.user_input,
            conversation_state=conversation_state
        )
        
        logger.info(f"[/api/analyze] ✅ Orchestrator returned: status={orch_result.get('status')}", flush=True)
        
        # Step 3: Save state
        if "state" in orch_result:
            session_manager.set_session(conversation_id, orch_result["state"])
            conversation_state = orch_result["state"]
        
        # Step 4: Transform orchestrator response to /api/analyze format
        # Get products and category from result
        products = orch_result.get("products", [])
        total_products = orch_result.get("total_found", len(products))
        total_pages = (total_products + 19) // 20 if total_products > 0 else 0
        
        category = conversation_state.get("category", "")
        extracted_attrs = conversation_state.get("extracted", {})
        
        # Step 5: Fetch filters from DB (if category exists)
        filter_groups = []
        hints = []
        
        if category:
            try:
                category_slug = sku_repo.get_category_slug_from_name(category)
                if category_slug:
                    available_filters = sku_repo.get_available_filters(category_slug)
                    
                    # Build filter groups
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
                    
                    # Generate hints from filters
                    hints = _generate_hints_from_filters(category, filter_groups)
                    
                    print(f"[/api/analyze] ✅ Fetched {len(filter_groups)} filters from DB", flush=True)
                else:
                    print(f"[/api/analyze] ⚠️ Category '{category}' not found in DB", flush=True)
            except Exception as e:
                print(f"[/api/analyze] ⚠️ Error fetching filters: {e}", flush=True)
        
        print(f"\n{'='*80}", flush=True)
        print(f"[/api/analyze] 💡 FINAL RESPONSE", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"[/api/analyze] Success: True", flush=True)
        print(f"[/api/analyze] Category: {category}", flush=True)
        print(f"[/api/analyze] Products: {len(products)}", flush=True)
        print(f"[/api/analyze] Total: {total_products}", flush=True)
        print(f"[/api/analyze] Filters: {len(filter_groups)}", flush=True)
        print(f"[/api/analyze] Hints: {len(hints)}", flush=True)
        print(f"[/api/analyze] {'='*80}\n", flush=True)
        
        # Step 6: Return in /api/analyze format
        return {
            "success": True,
            "category": category,
            "clarifying_hints": hints,
            "filters": filter_groups,
            "products": products,
            "total": total_products,
            "total_pages": total_pages,
            "conversation_id": conversation_id,
            "selected_attributes": extracted_attrs,
            "routing_info": orch_result.get("routing_info", {})  # NEW: Include routing info for debugging
        }
        
    except Exception as e:
        print(f"[/api/analyze] ❌ Error: {e}", flush=True)
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
    
    if not session_manager.session_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    conversation_state = session_manager.get_session(conversation_id)
    
    # Update state với response của user
    updated_state = orchestrator.update_state(
        conversation_state,
        {
            "question_type": request.question_type,
            "value": request.value,
            "attribute_name": request.attribute_name
        }
    )
    
    session_manager.set_session(conversation_id, updated_state)
    
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
    if not session_manager.session_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "conversation_id": conversation_id,
        "state": session_manager.get_session(conversation_id)
    }

@app.delete("/api/session/{conversation_id}")
async def clear_session(conversation_id: str):
    """Clear session"""
    session_manager.delete_session(conversation_id)
    return {"message": "Session cleared"}

@app.get("/health")
async def health_check():
    """Health check endpoint with session stats"""
    return {
        "status": "ok",
        "session_storage": session_manager.get_storage_type(),
        "active_sessions": session_manager.get_session_count()
    }

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


# ===== HELPER: Background Crawl =====

async def _trigger_crawl(
    search_query: str,
    category: str,
    category_slug: str,
    extracted_attrs: Dict[str, Any]
):
    """
    Background crawl task - triggered when DB has 0 products
    
    Args:
        search_query: Original user query (e.g., "giày nike")
        category: Detected category (e.g., "Giày")
        category_slug: Category slug (e.g., "giay")
        extracted_attrs: Extracted attributes from query (e.g., {brand: "Nike"})
    """
    try:
        print(f"\n{'='*80}", flush=True)
        print(f"[_trigger_crawl] 🌐 STARTING BACKGROUND CRAWL", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"[_trigger_crawl] Query: '{search_query}'", flush=True)
        print(f"[_trigger_crawl] Category: '{category}'", flush=True)
        print(f"[_trigger_crawl] Attributes: {extracted_attrs}", flush=True)
        
        # Import crawler
        from app.crawler.crawler import TikiCrawler
        
        # Create crawler and crawl
        crawler = TikiCrawler()
        
        print(f"[_trigger_crawl] Crawling from Tiki...", flush=True)
        crawled_products = await crawler.crawl(
            category=category,
            attributes=extracted_attrs,
            get_details=True
        )
        
        print(f"[_trigger_crawl] ✅ Crawled {len(crawled_products)} products from Tiki", flush=True)
        
        # Save to DB
        if crawled_products:
            try:
                # Extract schema from crawled data
                from app.services.schema_reconciler import SchemaReconciler
                reconciler = SchemaReconciler()
                
                actual_schema = reconciler.extract_actual_schema(crawled_products)
                print(f"[_trigger_crawl] ✅ Extracted schema: {len(actual_schema)} attributes", flush=True)
                
                # Save products
                saved_count = reconciler.save_products_to_db(
                    category,
                    category_id=None,  # Will be looked up
                    products=crawled_products,
                    schema=actual_schema
                )
                
                print(f"[_trigger_crawl] ✅ Saved {saved_count} products to DB", flush=True)
                print(f"[_trigger_crawl] ℹ️ Products now available in /api/analyze", flush=True)
                
            except Exception as save_error:
                print(f"[_trigger_crawl] ⚠️ Could not save to DB: {save_error}", flush=True)
                import traceback
                traceback.print_exc()
        
        print(f"[_trigger_crawl] ✅ Background crawl completed", flush=True)
        print(f"{'='*80}\n", flush=True)
        
    except Exception as e:
        print(f"[_trigger_crawl] ❌ Crawl error: {e}", flush=True)
        import traceback
        traceback.print_exc()

# app/api/routes.py

import asyncio
import logging
import sys
import uuid
import traceback
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.core.orchestrator import RecommendationOrchestrator
from app.core.context_analyzer import get_context_analyzer
from app.api.sku_routes import router as sku_router
from app.api.progressive_search_routes import router as progressive_search_router
from app.api.product_automation_routes import router as product_automation_router
from app.api.auth_routes import router as auth_router
from app.api.user_routes import router as user_router
from app.crawler.crawler import TikiCrawler
from app.db.sku_repository import SKURepository
from app.services.session_manager import get_session_manager
from app.config.database_orm import Base, engine, get_db
from app.api.auth_middleware import get_current_user_optional
from app.services.user_service import UserService
from app.models.user_models import User
# from app.core.crawler import YourCrawler  # Import your crawler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)      # Tắt httpx
logging.getLogger("httpcore").setLevel(logging.WARNING)   # Tắt httpcore
logging.getLogger("openai").setLevel(logging.WARNING)     # Tắt openai
logger = logging.getLogger("routes")

def log_analyze(msg):
    """Helper để log messages từ /api/analyze"""
    print(msg,  )  # Also print for console
    logger.info(msg)  # And log it

app = FastAPI(title="Smart Product Recommendation API")

# Register routers
app.include_router(auth_router)  # Auth routes first
app.include_router(user_router)  # User personalization routes
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

# ===== STARTUP EVENT =====
@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")
        traceback.print_exc()

# ===== MODELS =====

class QueryRequest(BaseModel):
    """Query request - context-based intent reconstruction"""
    user_input: str  # User's input (always required)
    conversation_id: Optional[str] = None  # For follow-up requests

class ResponseUpdate(BaseModel):
    """User response to a question"""
    conversation_id: str
    question_type: str  # "category" | "attribute"
    value: str
    attribute_name: Optional[str] = None

# ===== SESSION MANAGEMENT =====
# Using Redis with in-memory fallback
session_manager = get_session_manager()
print(f"[Routes] Session storage type: {session_manager.get_storage_type()}",  )

# ===== INITIALIZE ORCHESTRATOR + CONTEXT ANALYZER =====
orchestrator = RecommendationOrchestrator()
context_analyzer = get_context_analyzer()
sku_repo = SKURepository()  # Initialize SKU repository for filters

# ===== HELPER FUNCTIONS =====

def _generate_hints_from_filters(category: str, filter_groups: List[Dict]) -> List[str]:
    """
    Generate user-friendly hints from available filters
    
    Args:
        category: Product category name
        filter_groups: List of available filter groups with options
    
    Returns:
        List of hint messages to suggest to user
    """
    hints = []
    
    if not filter_groups:
        return hints
    
    # Group filters by type
    enum_filters = [f for f in filter_groups if f.get('data_type') == 'enum']
    range_filters = [f for f in filter_groups if f.get('data_type') in ['range', 'number']]
    
    # Generate hints for enum filters
    if enum_filters:
        filter_names = ", ".join([f['display_name'] for f in enum_filters[:3]])
        hints.append(f"Bạn có thể lọc theo {filter_names}")
    
    # Generate hints for range filters
    if range_filters:
        for f in range_filters[:2]:
            hints.append(f"Cụ thể hơn giá cả hoặc {f['display_name'].lower()}")
    
    # If no specific hints, provide generic suggestion
    if not hints:
        hints.append(f"Chọn loại {category.lower()} bạn quan tâm")
    
    return hints


async def _save_search_history_if_user(
    current_user: Optional[User],
    db: Session,
    user_input: str,
    category_name: Optional[str] = None,
    result_count: int = 0,
    session_id: Optional[str] = None
):
    """
    Helper to save search history for authenticated users
    """
    if not current_user:
        return None
    
    try:
        search_record = UserService.save_search_query(
            db=db,
            user_id=current_user.id,
            query=user_input,
            category_name=category_name,
            session_id=session_id
        )
        
        if result_count > 0:
            UserService.update_search_result_count(db, search_record.id, result_count)
        
        logger.info(f"✅ Saved search history for user {current_user.id}: '{user_input}'")
        return search_record.id
    except Exception as e:
        logger.warning(f"⚠️ Failed to save search history: {e}")
        return None

# ===== ENDPOINTS =====

@app.post("/api/query")
async def process_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Process user query with optional authentication for history tracking
    
    Response types:
    1. need_info: Cần hỏi thêm thông tin
    2. searching: Đang crawl
    3. results: Có kết quả + filters
    """
    print('vao api query',  )
    
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
    
    # ===== SAVE SEARCH HISTORY IF USER IS LOGGED IN =====
    if current_user:
        category_name = result.get("state", {}).get("category")
        try:
            search_record = UserService.save_search_query(
                db=db,
                user_id=current_user.id,
                query=request.user_input,
                category_name=category_name,
                session_id=conversation_id
            )
            
            # Update result count in the search record
            if result.get("status") == "results":
                result_count = len(result.get("results", []))
                UserService.update_search_result_count(db, search_record.id, result_count)
            
            logger.info(f"✅ Saved search history for user {current_user.id}: {request.user_input}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save search history: {e}")
            # Don't fail the request if history saving fails
    
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
                    print(f"✅ Added {len(filter_groups)} filter groups to query response",  )
                    
        except Exception as e:
            print(f"⚠️ Error fetching filters: {e}",  )
            import traceback
            traceback.print_exc()
            # Don't fail the request if filters fail
            result["filters"] = []
    
    return result

@app.post("/api/analyze")
async def analyze_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    try:
        # Validation
        if not request.user_input or request.user_input.strip() == "":
            return {
                "success": False,
                "error": "user_input is required"
            }
        
        is_new_query = not request.conversation_id
        conversation_id = request.conversation_id
        
        # ========================================================================
        # STEP 1: Tao session mới hoặc lấy session cũ dựa trên conversation_id
        # ========================================================================
        if not conversation_id:
            conversation_id = session_manager.create_session()
            conversation_state = None
            logger.info(f"\n[/api/analyze] 🆕 NEW CONVERSATION: {conversation_id}")
        else:
            if not session_manager.session_exists(conversation_id):
                return {
                    "success": False,
                    "error": f"Session {conversation_id} not found"
                }
            conversation_state = session_manager.get_session(conversation_id)
            logger.info(f"\n[/api/analyze] 📝 EXISTING CONVERSATION: {conversation_id}")
        
        # Initialize state if needed
        if conversation_state is None:
            conversation_state = {
                "has_category": False,
                "category": None,
                "extracted": {},
                "missing_required": [],
                "search_history": [],
                "attributes_asked": [],
                "last_crawl_params": None,
                "cache_hits": 0,
                "cache_misses": 0
            }
        
        # ========================================================================
        # STEP 2: Nếu có history, dùng LLM để reconstruct intent (ví dụ: "giày màu đen") và detect category change
        # ========================================================================
        user_input_to_process = request.user_input
        # Nếu có search history, gọi LLM để reconstruct intent
        if not is_new_query and conversation_state.get("search_history"):
            # 🎯 Use LLM to reconstruct intent
            logger.info(f"[/api/analyze] 🔄 RECONSTRUCTING INTENT")
            result_dict = context_analyzer.reconstruct_intent(
                user_input=request.user_input,
                conversation_state=conversation_state
            )
            #da clear
            logger.info(f"[/api/analyze] 🔄 LLM reconstructed intent: '{result_dict}'")
            user_input_to_process = result_dict["intent"]
            
            # 🔴 HANDLE CATEGORY CHANGE
            if result_dict.get("category_changed"):
                logger.info(f"[/api/analyze] 🔄 CATEGORY CHANGE DETECTED!")
                logger.info(f"  Old category: {conversation_state.get('category')}")
                logger.info(f"  New category: {result_dict.get('new_category')}")
                
                # Reset context for new category
                conversation_state["search_history"] = [request.user_input]  # Start fresh
                conversation_state["extracted"] = {}  # Clear old attributes
                conversation_state["category"] = None  # Will be re-detected
                conversation_state["has_category"] = False
                conversation_state["missing_required"] = []
                conversation_state["attributes_asked"] = []
                conversation_state["last_crawl_params"] = None
                conversation_state["detected_intent"] = None  # ← CRITICAL: Clear cached intent so new one is re-analyzed
                
                logger.info(f"[/api/analyze] ✅ Context reset for new category")
        else:
            logger.info(f"[/api/analyze] ✅ FIRST REQUEST - Using input as-is: '{request.user_input}'")
        
        # ========================================================================
        # STEP 3: Process with orchestrator
        # ========================================================================
        logger.info(f"\n{'-'*200}")
        logger.info(f"[/api/analyze] Processing: '{user_input_to_process}'")
        logger.info(f"[/api/analyze] Original input: '{request.user_input}'")
        
        orch_result = await orchestrator.process_query(
            user_input=user_input_to_process,
            conversation_state=conversation_state
        )
        # logger.info(f"[/api/analyze] Orchestrator result : {orch_result}")
        
        # Save updated state
        if "state" in orch_result:
            conversation_state = orch_result["state"]
            session_manager.set_session(conversation_id, conversation_state)
        
        # ========================================================================
        # STEP 4: Update search history (smart - replace duplicate attributes)
        # ========================================================================
        if "search_history" not in conversation_state:
            conversation_state["search_history"] = []
        
        conversation_state["search_history"] = _update_search_history_smart(
            conversation_state["search_history"],
            request.user_input
        )
        session_manager.set_session(conversation_id, conversation_state)
        
        # ========================================================================
        # STEP 4.5: Save search history to DB if user is authenticated
        # ========================================================================
        category_for_db = conversation_state.get("category")
        search_history_id = await _save_search_history_if_user(
            current_user=current_user,
            db=db,
            user_input=request.user_input,
            category_name=category_for_db,
            result_count=0,  # Will update after we know result count
        )
        
        # ========================================================================
        # STEP 5: Build response
        # ========================================================================
        products = orch_result.get("products", [])
        total_products = orch_result.get("total_found", len(products))
        total_pages = (total_products + 19) // 20 if total_products > 0 else 0
        
        category = conversation_state.get("category", "")
        extracted_attrs = conversation_state.get("extracted", {})
        
        # NEW: Handle non-results status from orchestrator
        orch_status = orch_result.get("status")
        
        if orch_status == "need_info":
            # CASE 4 (abstract), CASE 2/3 (need attributes), etc.
            logger.info(f"[/api/analyze] 💬 Returning clarification question (status: need_info)")
            session_manager.set_session(conversation_id, conversation_state)  # ← Save state
            return {
                "success": True,
                "status": "need_info",
                "question": orch_result.get("question"),
                "options": orch_result.get("options", []),
                "case": orch_result.get("case"),
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
        
        if orch_status == "no_results":
            logger.info(f"[/api/analyze] 🔍 No products found")
            session_manager.set_session(conversation_id, conversation_state)  # ← Save state
            return {
                "success": True,
                "status": "no_results",
                "message": orch_result.get("message", "Không tìm thấy sản phẩm phù hợp"),
                "category": category,
                "conversation_id": conversation_id,
                "search_history": conversation_state.get("search_history", [])
            }
        
        if orch_status == "error":
            logger.info(f"[/api/analyze] ❌ Orchestrator error")
            session_manager.set_session(conversation_id, conversation_state)  # ← Save state
            return {
                "success": False,
                "status": "error",
                "message": orch_result.get("message", "Xin lỗi, đã xảy ra lỗi. Vui lòng thử lại."),
                "conversation_id": conversation_id
            }
        
        # Fetch filters from DB
        filter_groups = []
        hints = []
        
        if category:
            try:
                category_slug = sku_repo.get_category_slug_from_name(category)
                if category_slug:
                    available_filters = sku_repo.get_available_filters(category_slug)
                    
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
                    
                    hints = _generate_hints_from_filters(category, filter_groups)
                    logger.info(f"✅ Fetched {len(filter_groups)} filters from DB")
                else:
                    logger.warning(f"Category '{category}' not found in DB")
            except Exception as e:
                logger.error(f"Error fetching filters: {e}")
        
        # ========================================================================
        # STEP 6: Log & return
        # ========================================================================
        logger.info(f"\n{'='*80}")
        logger.info(f"[/api/analyze] 💡 RESPONSE SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Input: '{request.user_input}'")
        if user_input_to_process != request.user_input:
            logger.info(f"Reconstructed: '{user_input_to_process}'")
        logger.info(f"Category: {category}")
        logger.info(f"Products: {len(products)}")
        logger.info(f"Filters: {len(filter_groups)}")
        logger.info(f"Search History: {conversation_state.get('search_history', [])}")
        logger.info(f"{'='*80}\n")
        
        # ========================================================================
        # Update search history with result count if user is authenticated
        # ========================================================================
        if search_history_id and len(products) > 0:
            try:
                UserService.update_search_result_count(db, search_history_id, len(products))
            except Exception as e:
                logger.warning(f"⚠️ Failed to update search result count: {e}")
        
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
            "search_history": conversation_state.get("search_history", []),
            "routing_info": orch_result.get("routing_info", {})
        }
        
    except Exception as e:
        logger.info(f"[/api/analyze] ❌ Error: {e}")
        import traceback as tb
        logger.exception("Error processing query")
        
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
        traceback.logger.info_exc()
        return {
            "success": False,
            "error": str(e)
        }

# ===== HELPER FUNCTIONS =====

def _detect_attribute_type(text: str) -> Optional[str]:
    """
    Detect attribute type from user input.
    
    Returns: "color", "size", "material", "brand", "type", or None
    """
    text_lower = text.lower()
    
    # Color keywords
    if any(kw in text_lower for kw in ["màu", "color", "sắc", "đen", "trắng", "xanh", "đỏ", "vàng", "hồng", "tím", "cam", "xám", "beige"]):
        return "color"
    
    # Size keywords
    if any(kw in text_lower for kw in ["size", "kích thước", "kich thuoc", "39", "40", "41", "42", "43", "44", "45", "m", "l", "xl", "xxl", "xs", "s"]):
        return "size"
    
    # Material keywords
    if any(kw in text_lower for kw in ["chất liệu", "chat lieu", "vải", "da", "cao su", "nhựa", "vàng đồng", "material", "fabric", "leather"]):
        return "material"
    
    # Brand keywords
    if any(kw in text_lower for kw in ["nike", "adidas", "puma", "reebok", "vans", "converse", "timberland", "brand"]):
        return "brand"
    
    # Type/Style keywords
    if any(kw in text_lower for kw in ["thể thao", "casual", "chạy bộ", "bóng rổ", "đế bệm", "thấp", "cao", "cổ thấp", "cổ cao"]):
        return "type"
    
    return None

def _update_search_history_smart(history: list, new_input: str, max_items: int = 8) -> list:
    """
    Smart search history update - replace duplicate attributes, keep max items.
    
    Logic:
    1. Detect attribute type of new_input
    2. If it's an attribute (color, size, etc) → remove same type from history
    3. Append new input
    4. Keep only last max_items (default 8)
    
    Example:
    - history = ["giày nike", "màu đen", "thể thao"]
    - new_input = "màu đỏ"
    - detected_type = "color"
    - Remove "màu đen" (same type)
    - Result: ["giày nike", "thể thao", "màu đỏ"]
    """
    detected_type = _detect_attribute_type(new_input)
    
    # If it's an attribute type, remove same type from history
    if detected_type:
        history = [
            h for h in history 
            if isinstance(h, str) and _detect_attribute_type(h) != detected_type
        ]
    
    # Append new input
    history.append(new_input)
    
    # Keep only last max_items
    return history[-max_items:]



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
        logger.info(f"\n{'='*80}",  )
        logger.info(f"[_trigger_crawl] 🌐 STARTING BACKGROUND CRAWL",  )
        logger.info(f"{'='*80}",  )
        logger.info(f"[_trigger_crawl] Query: '{search_query}'",  )
        logger.info(f"[_trigger_crawl] Category: '{category}'",  )
        logger.info(f"[_trigger_crawl] Attributes: {extracted_attrs}",  )
        
        # Import crawler
        from app.crawler.crawler import TikiCrawler
        
        # Create crawler and crawl
        crawler = TikiCrawler()
        
        logger.info(f"[_trigger_crawl] Crawling from Tiki...",  )
        crawled_products = await crawler.crawl(
            category=category,
            attributes=extracted_attrs,
            get_details=True
        )
        
        logger.info(f"[_trigger_crawl] ✅ Crawled {len(crawled_products)} products from Tiki",  )
        
        # Save to DB
        if crawled_products:
            try:
                # Extract schema from crawled data
                from app.services.schema_reconciler import SchemaReconciler
                reconciler = SchemaReconciler()
                
                actual_schema = reconciler.extract_actual_schema(crawled_products)
                logger.info(f"[_trigger_crawl] ✅ Extracted schema: {len(actual_schema)} attributes",  )
                
                # Save products
                saved_count = reconciler.save_products_to_db(
                    category,
                    category_id=None,  # Will be looked up
                    products=crawled_products,
                    schema=actual_schema
                )
                
                logger.info(f"[_trigger_crawl] ✅ Saved {saved_count} products to DB",  )
                logger.info(f"[_trigger_crawl] ℹ️ Products now available in /api/analyze",  )
                
            except Exception as save_error:
                logger.info(f"[_trigger_crawl] ⚠️ Could not save to DB: {save_error}",  )
                import traceback
                traceback.logger.info_exc()
        
        logger.info(f"[_trigger_crawl] ✅ Background crawl completed",  )
        logger.info(f"{'='*80}\n",  )
        
    except Exception as e:
        logger.info(f"[_trigger_crawl] ❌ Crawl error: {e}",  )
        import traceback
        traceback.print_exc()

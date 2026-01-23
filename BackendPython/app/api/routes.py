# app/api/routes.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.core.orchestrator import RecommendationOrchestrator
# from app.core.crawler import YourCrawler  # Import your crawler

app = FastAPI(title="Smart Product Recommendation API")

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

# ===== ENDPOINTS =====

@app.post("/api/query")
async def process_query(request: QueryRequest):
    """
    Process user query
    
    Response types:
    1. need_info: Cần hỏi thêm thông tin
    2. searching: Đang crawl
    3. results: Có kết quả
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
    
    return result

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
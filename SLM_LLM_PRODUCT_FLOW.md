# Product Request Flow with SLM/LLM Integration

## Architecture Overview

When a product request arrives from the UI, it now flows through the following SLM/LLM logic pipeline:

```
User Query (Frontend)
        ↓
GET /api/v1/products/search?q=<query>
        ↓
ProductController.search()
        ↓
┌─────────────────────────────────────────────────────────┐
│              INTENT ANALYSIS (SLM)                       │
│  IntentService.analyzeIntent()                          │
│  - Analyzes user query                                  │
│  - Extracts constraints (category, price, brand, etc.)  │
│  - Determines if intent is clear or needs clarification │
│  - Returns: intent_status, extracted_constraints        │
└─────────────────────────────────────────────────────────┘
        ↓
   [Intent Clear?]
   ↙          ↘
YES            NO → Return clarification request
  ↓            └─→ Ask follow-up questions
  ↓
┌─────────────────────────────────────────────────────────┐
│         PRODUCT SEARCH (Database/Service)               │
│  ProductService.searchProducts()                        │
│  - Searches database with extracted constraints         │
│  - Filters by category, price range, brand, etc.        │
│  - Returns matching products                            │
└─────────────────────────────────────────────────────────┘
        ↓
   [Products Found?]
   ↙          ↘
YES            NO → Return empty results
  ↓
┌─────────────────────────────────────────────────────────┐
│         LLM ENHANCEMENT (SLM)                            │
│  LLMService.generateRecommendationReason()              │
│  For each top 5 products:                               │
│  - Generates explanation why product matches user need  │
│  - Adds recommendationReason to each product            │
│  - Handles failures gracefully                          │
└─────────────────────────────────────────────────────────┘
        ↓
Return Enhanced Results to UI
{
  "type": "query",
  "products": [
    {
      "id": "lp001",
      "title": "Dell Inspiron 15",
      ...specs,
      "recommendationReason": "This product is ideal because..."
    },
    ...
  ],
  "intentAnalysis": {
    "status": "clear",
    "summary": "User wants a laptop for coding",
    "constraints": { category: "laptop", price_max: 20000000 }
  }
}
```

## Flow Details

### Step 1: Intent Analysis (SLM)
- **Service**: IntentService
- **Model**: Ollama (qwen2.5)
- **Input**: User query
- **Output**:
  - `intent_status`: "clear" | "unclear"
  - `intent_summary`: Natural language summary
  - `extracted_constraints`: Structured filters
  - `follow_up_questions`: Questions if intent unclear

### Step 2: Intent Check
- If `intent_status === "unclear"`: Return clarification response
- If `intent_status === "clear"`: Proceed to search

### Step 3: Product Search
- **Service**: ProductService
- **Input**: Query + extracted constraints from intent analysis
- **Output**: Array of matching products

### Step 4: LLM Enhancement
- **Service**: LLMService
- **Operation**: generateRecommendationReason()
- **Input**: Product + user query + constraints
- **Output**: Added `recommendationReason` field to each product
- **Resilience**: If LLM enhancement fails, return product without reason

## Error Handling

```javascript
// Intent Analysis Fails
→ Continue with basic search
→ Treat query as clear intent
→ Skip enhanced constraints

// Product Search Returns No Results
→ Return empty products array
→ Skip LLM enhancement

// LLM Enhancement Fails
→ Return products without recommendation reasons
→ Log warning, don't break the flow
```

## Response Formats

### Clarification Response (Intent Unclear)
```json
{
  "success": true,
  "data": {
    "type": "clarify",
    "question": "Bạn sử dụng laptop cho mục đích gì?",
    "options": ["Lập trình", "Thiết kế", "Văn phòng"],
    "understanding": "Bạn muốn mua một chiếc laptop"
  }
}
```

### Product Results Response (Intent Clear)
```json
{
  "success": true,
  "data": {
    "type": "query",
    "products": [
      {
        "id": "lp001",
        "title": "Dell Inspiron 15",
        "price": 13990000,
        "rating": 4.5,
        "recommendationReason": "Perfect for programming...",
        "specs": {...}
      }
    ],
    "intentAnalysis": {
      "status": "clear",
      "summary": "Laptop for coding",
      "constraints": {
        "category": "laptop",
        "usage": "programming",
        "price_max": 20000000
      }
    }
  }
}
```

## Integration Points

### Frontend Benefits:
1. **Intent Clarification**: Asks users for missing info before searching
2. **Recommendation Reasons**: Shows why each product matches their need
3. **Constraint Extraction**: Automatically understands user preferences
4. **Smart Search**: Returns more relevant results

### Backend Architecture:
1. **SeparationOfConcerns**: Intent ≠ Search ≠ Enhancement
2. **Fallback Mechanisms**: Works even if SLM/LLM services fail
3. **Logging**: Tracks intent analysis and LLM performance
4. **Error Resilience**: Graceful degradation on service failures

## Code Files Modified

1. **`src/controllers/product.controller.js`**
   - Added imports for intentService and llmService
   - Implemented complete 4-step product search flow
   - Added intent analysis before search
   - Added LLM enhancement after search

2. **Services Used** (No changes needed):
   - `src/services/intent.service.js` - Already implements analyzeIntent()
   - `src/services/llm.service.js` - Already implements generateRecommendationReason()
   - `src/services/product.service.js` - Uses extracted constraints

## Testing the Flow

### Test 1: Clear Intent
```bash
curl "http://localhost:3000/api/v1/products/search?q=laptop%20cho%20l%E1%BA%ADp%20tr%C3%ACnh"
```
Expected: Products returned with recommendation reasons

### Test 2: Unclear Intent
```bash
curl "http://localhost:3000/api/v1/products/search?q=th%E1%BB%A9c"
```
Expected: Clarification request with follow-up questions

### Test 3: LLM Service Down
Expected: Products returned without recommendation reasons (graceful degradation)

## Future Enhancements

1. **Caching**: Cache intent analysis for repeated queries
2. **Ranking**: Rerank results based on recommendation reasons
3. **Feedback Loop**: Learn from user selections to improve intent analysis
4. **Multi-turn**: Remember conversation history for better intent understanding
5. **A/B Testing**: Compare intent-based vs. simple search results

---

**Status**: ✅ Complete - Product requests now flow through SLM/LLM logic for intelligent processing and enhanced results.

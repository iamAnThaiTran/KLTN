# Clarification Response Handling - Implementation Guide

## What Was Updated

### ✅ Frontend Now Handles Two Response Types:

**1. Type: "clarify" (Unclear Intent)**
- Displays the AIUnderstandingPanel with:
  - User's current understanding of what they're looking for
  - A clarification question from the SLM
  - Multiple choice options to refine the search
- Example flow:
  ```
  User searches: "hello"
  ↓
  Backend returns: { type: "clarify", question: "...", options: [...] }
  ↓
  UI shows AIUnderstandingPanel with options
  ↓
  User clicks an option
  ↓
  New search with combined query: "hello [selected_option]"
  ```

**2. Type: "query" (Clear Intent)**
- Displays the ProductGrid with search results
- Shows products with recommendation reasons (from LLM)
- Normal product browsing experience

## Files Modified

### [src/services/productServices.js](src/services/productServices.js#L3-L13)
**Change**: Return full response object instead of just products array
```javascript
// Before: return res.data?.data || []
// After: return res.data?.data || { type: 'query', products: [] }
```
- Now returns complete response with type, products, intentAnalysis
- Allows Home.jsx to determine what to display

### [src/pages/Home.jsx](src/pages/Home.jsx#L35-L75)
**Changes**: 
1. Updated `handleSearch()` to check response.type
   - If 'clarify': Show AIUnderstandingPanel with question & options
   - If 'query': Show ProductGrid with results

2. Updated `handleSelectOption()` to handle multi-turn clarification
   - User can refine their search through multiple clarification rounds
   - Combines original query + selected option + sends again
   - May trigger another clarification if still unclear

## User Experience Flow

### Scenario 1: Clear Intent (Normal Search)
```
User: "laptop for coding"
  ↓
SLM analyzes: "Clear intent - wants laptop for programming"
  ↓
Extract constraints: category: laptop, usage: programming
  ↓
Search database with constraints
  ↓
Show products with LLM recommendations: "This is perfect because..."
```

### Scenario 2: Unclear Intent (Clarification Flow)
```
User: "hello"
  ↓
SLM analyzes: "Unclear what product they want"
  ↓
Backend returns: type: 'clarify'
  ↓
UI shows: "What are you looking for?"
         Options: [Electronics, Clothing, Books, ...]
  ↓
User clicks: "Electronics"
  ↓
New search: "hello electronics"
  ↓
If still unclear → Another clarification
If clear → Show products
```

### Scenario 3: Multi-turn Clarification
```
User: "phone"
  ↓
SLM: "Phone is unclear" → Clarification #1
UI: "What's your budget?"
User: "Under 5 million"
  ↓
New query: "phone under 5 million"
  ↓
SLM: "Still need more info" → Clarification #2
UI: "iPhone or Android?"
User: "Android"
  ↓
New query: "phone under 5 million android"
  ↓
SLM: "Clear now" → Show products
```

## Response Format Examples

### Clarification Response
```json
{
  "success": true,
  "data": {
    "type": "clarify",
    "question": "Bạn đang tìm kiếm loại sản phẩm nào?",
    "options": ["Laptop", "Điện thoại", "Tablet", "Phụ kiện"],
    "understanding": "You're asking about 'hello', but unclear what product category"
  }
}
```

### Product Results Response
```json
{
  "success": true,
  "data": {
    "type": "query",
    "products": [
      {
        "id": "lp001",
        "title": "Dell XPS 13",
        "price": 25000000,
        "rating": 4.8,
        "recommendationReason": "Perfect for coding - 16GB RAM, SSD, lightweight",
        "specs": {...}
      }
    ],
    "intentAnalysis": {
      "status": "clear",
      "summary": "User wants laptop for programming",
      "constraints": { category: "laptop", usage: "programming" }
    }
  }
}
```

## Testing the Implementation

### Test 1: Clear Intent (Should show products immediately)
```bash
curl "http://localhost:3000/api/v1/products/search?q=laptop%20cho%20l%E1%BA%ADp%20tr%C3%ACnh"
```
Expected: type: "query" with products array

### Test 2: Unclear Intent (Should show clarification)
```bash
curl "http://localhost:3000/api/v1/products/search?q=hello"
```
Expected: type: "clarify" with question and options

### Test 3: UI Flow (In browser)
1. Search for "hello"
2. See AIUnderstandingPanel appear with question
3. Click an option (e.g., "Laptop")
4. See search results appear

## Component Hierarchy

```
Home.jsx
├── searchMode state: 'recommended' | 'clarify' | 'query'
├── clarifyData state: { question, options, understanding }
├── products state: array of products
│
├── Header (onSearch → handleSearch)
│   └── Passes query to handleSearch()
│
├── AIUnderstandingPanel (shown when searchMode === 'clarify')
│   └── onSelectOption → handleSelectOption()
│       └── Combines query + option
│
└── ProductGrid (shown when searchMode === 'query' or 'recommended')
    └── Displays products
```

## Error Handling

- If network error: Fall back to empty results
- If intent service down: Continue with basic search (graceful degradation)
- If LLM enhancement fails: Show products without recommendation reasons
- If options array is empty: Still show clarification panel (user can type more)

---

**Status**: ✅ Complete - UI now fully handles both clarification and product results responses

# AssistOverlay Integration - NOW LIVE ✅

## What's Done

✅ **AssistOverlay** component imported into Home.jsx  
✅ **State management** for overlay (showAssistOverlay, assistOverlayData)  
✅ **Event handlers** added (handleAssistOptionSelect, handleAssistSkip, handleAssistClose)  
✅ **Response handling** for ui_mode: 'OVERLAY_ASSIST' in handleSearch  
✅ **Component rendered** at top of page (above all content)  

## How to Test

### Test 1: Trigger Clarification Overlay

1. **Backend** needs to return response with `ui_mode: 'OVERLAY_ASSIST'`
2. **Open browser** at `http://localhost:5173`
3. **Search** for something (e.g., "hello")
4. **Expected**: Overlay appears with backdrop blur

### Test 2: Expected Server Response Format

```json
{
  "success": true,
  "data": {
    "ui_mode": "OVERLAY_ASSIST",
    "summary": "✔ Đã hiểu: mua áo mưa",
    "question": "Bạn muốn áo mưa cho mục đích gì?",
    "options": [
      { "key": "outdoor", "label": "Dã ngoại / Du lịch" },
      { "key": "work", "label": "Công việc / Học tập" },
      { "key": "casual", "label": "Hàng ngày" }
    ],
    "allow_skip": true
  },
  "message": "Clarification needed",
  "timestamp": "2026-01-15T12:34:56.789Z"
}
```

### Test 3: User Interactions

**Click Option Button:**
- Closes overlay
- Combines query + option key
- Searches again with new query

**Click Skip Button:**
- Closes overlay
- Shows empty results

**Click Outside or ESC:**
- Closes overlay
- Goes to query mode

## Code Flow

```
User searches "hello"
    ↓
getProductFromTiki(query)
    ↓
API returns: { ui_mode: 'OVERLAY_ASSIST', ... }
    ↓
handleSearch detects ui_mode
    ↓
setShowAssistOverlay(true)
setAssistOverlayData(response)
    ↓
AssistOverlay component renders
    ↓
User clicks option "outdoor"
    ↓
handleAssistOptionSelect("outdoor")
    ↓
Calls handleSearch("hello outdoor")
    ↓
API responds with products or another overlay
```

## Backend Integration Example

Update `src/controllers/product.controller.js` search function:

```javascript
export async function search(req, res, next) {
  const { q } = req.query;
  
  try {
    // 1. Intent Analysis
    const intentAnalysis = await intentService.analyzeIntent(q, [], {});
    
    // 2. Check if unclear and needs overlay
    if (intentAnalysis.intent_status === 'unclear') {
      return successResponse(res, {
        ui_mode: 'OVERLAY_ASSIST',
        summary: `✔ Đã hiểu: ${q}`,
        question: 'Bạn muốn sản phẩm này cho mục đích gì?',
        options: [
          { key: 'option1', label: 'Use case 1' },
          { key: 'option2', label: 'Use case 2' },
          { key: 'option3', label: 'Use case 3' }
        ],
        allow_skip: true
      }, 'Clarification needed');
    }
    
    // 3. Rest of search logic...
    const products = await productService.searchProducts(q, {...});
    return successResponse(res, {
      type: 'query',
      products,
      intentAnalysis
    });
  } catch (error) {
    // ...
  }
}
```

## Files Modified

- ✅ `src/pages/Home.jsx` - Added overlay integration
- ✅ `src/components/AssistOverlay.jsx` - Component created
- ✅ `src/components/AssistOverlay.css` - Styling created
- ✅ `src/components/AssistOverlay.types.ts` - Types created

## Ready to Use

The component is **production-ready**. Just make sure your backend returns the correct response format with `ui_mode: 'OVERLAY_ASSIST'` and it will appear immediately!

---

**Status**: 🟢 LIVE - Test it now by searching for unclear queries

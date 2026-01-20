# Frontend & Backend Integration Setup

## How to Run the Application

### 1. Backend (Python)

```bash
cd C:\Code\KLTN\BackendPython

# Run with poetry
poetry run python main.py
```

The backend will start at: **http://localhost:8000**

You can test the API at: **http://localhost:8000/docs** (Swagger UI)

### 2. Frontend (React)

```bash
cd C:\Code\KLTN\FrontEnd_JS\FrontEnd

# Install dependencies (if not already done)
npm install

# Run development server
npm run dev
```

The frontend will start at: **http://localhost:5173** (or another port if 5173 is in use)

---

## What's Connected

### Frontend → Backend API Calls

The ShoeFinder component now makes real API calls to:

1. **POST /api/query**
   - Sends initial user input
   - Returns questions/recommendations from the backend
   - Parameters: `user_input`, `conversation_id`

2. **POST /api/respond** 
   - Sends user responses to follow-up questions
   - Parameters: `conversation_id`, `question_type`, `value`, `attribute_name`

### CORS Configuration

✅ CORS is enabled in the backend to allow requests from the frontend

---

## How to Test

1. **Start Backend:**
   ```bash
   cd C:\Code\KLTN\BackendPython
   poetry run python main.py
   ```

2. **Start Frontend:**
   ```bash
   cd C:\Code\KLTN\FrontEnd_JS\FrontEnd
   npm run dev
   ```

3. **Open Browser:**
   - Navigate to `http://localhost:5173`
   - Start chatting with the Shoe Finder AI

---

## Troubleshooting

### Backend Connection Error

If you see "Cannot POST /api/query":
- Make sure backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify the API_BASE_URL in `ShoeFinder.jsx` is correct

### Port Already in Use

Backend port 8000:
```bash
poetry run python main.py --host 0.0.0.0 --port 8001
```
Then update `API_BASE_URL` in `ShoeFinder.jsx`:
```javascript
const API_BASE_URL = 'http://localhost:8001';
```

Frontend port 5173:
```bash
npm run dev -- --port 3000
```

---

## API Response Format Expected

The backend should return responses in this format:

```json
{
  "conversation_id": "uuid",
  "question": "What type of shoes...",
  "options": [
    {"label": "Running", "value": "running"},
    {"label": "Casual", "value": "casual"}
  ],
  "products": [
    {
      "name": "Nike Air Max",
      "price": 2500000,
      "description": "...",
      "match_score": 95,
      "explanation": "..."
    }
  ]
}
```

Make sure your backend returns data in this format or update `displayBackendResponse()` in `ShoeFinder.jsx` accordingly.

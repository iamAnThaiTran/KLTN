import express from 'express';
import {
  recommendHandler,
  clarifyHandler,
  getSessionHandler,
  clearSessionHandler
} from '../controllers/recommend.controller.js';

const router = express.Router();

/**
 * POST /api/recommend
 * Main recommendation endpoint
 * 
 * Body:
 * {
 *   "session_id": "optional-session-id",
 *   "user_query": "laptop cho sinh viên IT, pin trâu, dưới 15 triệu"
 * }
 * 
 * Response (unclear intent):
 * {
 *   "intent_status": "unclear",
 *   "ui_state": "INTENT_CLARIFICATION",
 *   "follow_up_questions": [...]
 * }
 * 
 * Response (clear intent):
 * {
 *   "intent_status": "clear",
 *   "ui_state": "SEARCH_RESULT",
 *   "products": [...]
 * }
 */
router.post('/recommend', recommendHandler);

/**
 * POST /api/recommend/clarify
 * Handle clarification responses
 * 
 * Body:
 * {
 *   "session_id": "session-id",
 *   "answers": {
 *     "category": "laptop",
 *     "budget": "10-15 triệu",
 *     "usage": "học tập"
 *   }
 * }
 */
router.post('/recommend/clarify', clarifyHandler);

/**
 * GET /api/recommend/session/:sessionId
 * Get session history
 */
router.get('/recommend/session/:sessionId', getSessionHandler);

/**
 * DELETE /api/recommend/session/:sessionId
 * Clear session data
 */
router.delete('/recommend/session/:sessionId', clearSessionHandler);

export default router;
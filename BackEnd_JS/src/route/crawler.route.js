import express from 'express';
// import { authenticate, authorize } from '../middleware/auth.js';

const router = express.Router();

/**
 * Crawler Routes
 * Admin only - trigger crawling and manage data sync
 */

// GET /api/crawlers/stats - Get crawler sync statistics
// router.get('/stats', authenticate, authorize(['admin']), getCrawlerStats);

// // POST /api/crawlers/sync/full - Trigger full crawl of all categories
// router.post('/sync/full', authenticate, authorize(['admin']), triggerFullSync);

// // POST /api/crawlers/sync/category - Crawl specific category
// router.post('/sync/category', authenticate, authorize(['admin']), crawlCategory);

export default router;

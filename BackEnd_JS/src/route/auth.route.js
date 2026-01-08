import express from 'express';
import {
    register,
    login,
    logout,
    getCurrentUser,
    refreshToken
} from '../controllers/auth.controller.js';
import { authenticateToken } from '../middleware/auth.js';

const router = express.Router();

/**
 * Public routes - no authentication required
 */
router.post('/register', register);
router.post('/login', login);

/**
 * Protected routes - authentication required
 */
router.get('/me', authenticateToken, getCurrentUser);
router.post('/logout', authenticateToken, logout);
router.post('/refresh', authenticateToken, refreshToken);

export default router;

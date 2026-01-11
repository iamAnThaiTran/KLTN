import express from 'express';
import {
    register,
    login,
    logout,
    getCurrentUser,
    refreshToken
} from '../controllers/auth.controller.js';
import { authenticateToken } from '../middleware/auth.js';
import { validateLogin, validateRegister } from '../validators/auth.validator.js';

const router = express.Router();

/**
 * Public routes - no authentication required
 */
router.post('/register', validateRegister, register);
router.post('/login', validateLogin, login);

/**
 * Protected routes - authentication required
 */
router.get('/me', authenticateToken, getCurrentUser);
router.post('/logout', authenticateToken, logout);
router.post('/refresh', authenticateToken, refreshToken);

export default router;

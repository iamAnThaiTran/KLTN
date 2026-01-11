import { authService } from '../services/auth.service.js';
import { generateToken } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

/**
 * Register
 */
export const register = async (req, res) => {
    try {
        const { email, password, name } = req.body;
        if (!email || !password || !name) {
            return res.status(400).json({
                success: false,
                message: 'Email, password, and name are required'
            });
        }
        const user = await authService.register(email, password, name);
        const token = generateToken({ id: user.id, email: user.email });

        res.status(201).json({
            success: true,
            message: 'Registration successful',
            token,
            user
        });
    } catch (error) {
        logger.error('Register controller error:', error);
        
        if (error.message.includes('already registered')) {
            return res.status(400).json({
                success: false,
                message: error.message
            });
        }

        res.status(500).json({
            success: false,
            message: 'Registration failed',
            error: error.message
        });
    }
};

/**
 * Login user
 */
export const login = async (req, res) => {
    try {
        const { email, password } = req.body;

        // Validate input
        if (!email || !password) {
            return res.status(400).json({
                success: false,
                message: 'Email and password are required'
            });
        }

        // Login user
        const user = await authService.login(email, password);

        // Generate token
        const token = generateToken({ id: user.id, email: user.email });

        res.status(200).json({
            success: true,
            message: 'Login successful',
            token,
            user
        });
    } catch (error) {
        logger.error('Login controller error:', error);

        if (error.message.includes('Invalid') || error.message.includes('deactivated')) {
            return res.status(401).json({
                success: false,
                message: error.message
            });
        }

        res.status(500).json({
            success: false,
            message: 'Login failed',
            error: error.message
        });
    }
};

/**
 * Get current user
 */
export const getCurrentUser = async (req, res) => {
    try {
        const userId = req.user.id;

        const user = await authService.getCurrentUser(userId);

        if (!user) {
            return res.status(404).json({
                success: false,
                message: 'User not found'
            });
        }

        res.status(200).json({
            success: true,
            user
        });
    } catch (error) {
        logger.error('Get current user error:', error);
        res.status(500).json({
            success: false,
            message: 'Failed to get user',
            error: error.message
        });
    }
};

/**
 * Logout user
 */
export const logout = async (req, res) => {
    try {
        const userId = req.user.id;

        await authService.logout(userId);

        res.status(200).json({
            success: true,
            message: 'Logout successful'
        });
    } catch (error) {
        logger.error('Logout error:', error);
        res.status(500).json({
            success: false,
            message: 'Logout failed',
            error: error.message
        });
    }
};

/**
 * Refresh token
 */
export const refreshToken = async (req, res) => {
    try {
        const userId = req.user.id;

        const user = await authService.validateTokenUser(userId);

        const newToken = generateToken({ id: user.id, email: user.email });

        res.status(200).json({
            success: true,
            token: newToken
        });
    } catch (error) {
        logger.error('Refresh token error:', error);
        res.status(401).json({
            success: false,
            message: 'Token refresh failed',
            error: error.message
        });
    }
};

export default {
    register,
    login,
    getCurrentUser,
    logout,
    refreshToken
};

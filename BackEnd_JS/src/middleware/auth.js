import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';

/**
 * Optional authentication - allows both logged in and guest users
 * Attaches user info to req.user if token is valid, otherwise user is null
 */
export const optionalAuth = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        // No token provided - user is guest
        req.user = null;
        req.isAuthenticated = false;
        return next();
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            // Invalid token - treat as guest
            req.user = null;
            req.isAuthenticated = false;
        } else {
            req.user = user;
            req.isAuthenticated = true;
        }
        next();
    });
};

/**
 * Required authentication - user must be logged in
 */
export const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({
            success: false,
            message: 'Vui lòng đăng nhập để tiếp tục'
        });
    }

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) {
            return res.status(403).json({
                success: false,
                message: 'Token không hợp lệ hoặc đã hết hạn'
            });
        }
        req.user = user;
        req.isAuthenticated = true;
        next();
    });
};

/**
 * Admin only - user must be authenticated and have admin role
 */
export const requireAdmin = (req, res, next) => {
    // First check if user is authenticated
    if (!req.user || !req.isAuthenticated) {
        return res.status(401).json({
            success: false,
            message: 'Vui lòng đăng nhập để tiếp tục'
        });
    }

    // Then check if user is admin
    if (req.user.role !== 'admin') {
        return res.status(403).json({
            success: false,
            message: 'Không có quyền truy cập. Chỉ quản trị viên mới có thể thực hiện hành động này'
        });
    }

    next();
};

/**
 * Generate JWT token for user
 */
export const generateToken = (user) => {
    return jwt.sign(
        {
            id: user.id,
            email: user.email,
            role: user.role || 'user'
        },
        JWT_SECRET,
        { expiresIn: process.env.JWT_EXPIRES_IN || '7d' }
    );
};

/**
 * Verify and decode JWT token
 */
export const verifyToken = (token) => {
    try {
        return jwt.verify(token, JWT_SECRET);
    } catch (err) {
        return null;
    }
};

export default {
    optionalAuth,
    authenticateToken,
    requireAdmin,
    generateToken,
    verifyToken
};
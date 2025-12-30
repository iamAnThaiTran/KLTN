import { generateToken } from '../middleware/auth.js';

/**
 * Mock user database - replace with real database
 */
const users = [
    { id: 1, email: 'admin@kltn.com', password: 'admin123', role: 'admin', name: 'Admin' },
    { id: 2, email: 'user@kltn.com', password: 'user123', role: 'user', name: 'User' }
];

/**
 * Register new user
 */
export const register = async (req, res) => {
    try {
        const { email, password, name } = req.body;

        // Validate input
        if (!email || !password || !name) {
            return res.status(400).json({
                success: false,
                message: 'Email, password và name là bắt buộc'
            });
        }

        // Check if user already exists
        const existingUser = users.find(u => u.email === email);
        if (existingUser) {
            return res.status(400).json({
                success: false,
                message: 'Email này đã được đăng ký'
            });
        }

        // Create new user (in real app, hash password with bcrypt)
        const newUser = {
            id: users.length + 1,
            email,
            password, // In production: bcrypt.hash(password, 10)
            name,
            role: 'user'
        };

        users.push(newUser);

        // Generate token
        const token = generateToken(newUser);

        res.status(201).json({
            success: true,
            message: 'Đăng ký thành công',
            token,
            user: {
                id: newUser.id,
                email: newUser.email,
                name: newUser.name,
                role: newUser.role
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Lỗi đăng ký',
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
                message: 'Email và password là bắt buộc'
            });
        }

        // Find user
        const user = users.find(u => u.email === email);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'Email hoặc mật khẩu không đúng'
            });
        }

        // Check password (in production: bcrypt.compare(password, user.password))
        if (user.password !== password) {
            return res.status(401).json({
                success: false,
                message: 'Email hoặc mật khẩu không đúng'
            });
        }

        // Generate token
        const token = generateToken(user);

        res.json({
            success: true,
            message: 'Đăng nhập thành công',
            token,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                role: user.role
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Lỗi đăng nhập',
            error: error.message
        });
    }
};

/**
 * Get current user info
 */
export const getCurrentUser = async (req, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'Vui lòng đăng nhập'
            });
        }

        const user = users.find(u => u.id === req.user.id);
        if (!user) {
            return res.status(404).json({
                success: false,
                message: 'Không tìm thấy người dùng'
            });
        }

        res.json({
            success: true,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                role: user.role
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Lỗi lấy thông tin người dùng',
            error: error.message
        });
    }
};

/**
 * Logout user
 */
export const logout = async (req, res) => {
    try {
        // In real app, you might invalidate the token in a blacklist
        res.json({
            success: true,
            message: 'Đăng xuất thành công'
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Lỗi đăng xuất',
            error: error.message
        });
    }
};

/**
 * Refresh token
 */
export const refreshToken = async (req, res) => {
    try {
        if (!req.user) {
            return res.status(401).json({
                success: false,
                message: 'Vui lòng đăng nhập'
            });
        }

        const user = users.find(u => u.id === req.user.id);
        const newToken = generateToken(user);

        res.json({
            success: true,
            message: 'Làm mới token thành công',
            token: newToken
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'Lỗi làm mới token',
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

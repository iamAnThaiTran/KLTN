/**
 * Auth Validators
 */

export const validateLogin = (req, res, next) => {
    const { email, password } = req.body;

    // Check if fields exist
    if (!email || !password) {
        return res.status(400).json({
            success: false,
            error: { message: 'Email and password are required' }
        });
    }

    // Ensure all fields are strings
    if (typeof email !== 'string') {
        return res.status(400).json({
            success: false,
            error: { message: 'Email must be a string' }
        });
    }

    if (typeof password !== 'string') {
        return res.status(400).json({
            success: false,
            error: { message: 'Password must be a string' }
        });
    }

    // Trim whitespace
    req.body.email = email.trim();
    req.body.password = password.trim();

    next();
};

export const validateRegister = (req, res, next) => {
    const { email, password, name } = req.body;

    // Check if fields exist
    if (!email || !password || !name) {
        return res.status(400).json({
            success: false,
            error: { message: 'Email, password, and name are required' }
        });
    }

    // Ensure all fields are strings
    if (typeof email !== 'string') {
        return res.status(400).json({
            success: false,
            error: { message: 'Email must be a string' }
        });
    }

    if (typeof password !== 'string') {
        return res.status(400).json({
            success: false,
            error: { message: 'Password must be a string' }
        });
    }

    if (typeof name !== 'string') {
        return res.status(400).json({
            success: false,
            error: { message: 'Name must be a string' }
        });
    }

    // Trim whitespace
    req.body.email = email.trim();
    req.body.password = password.trim();
    req.body.name = name.trim();

    next();
};

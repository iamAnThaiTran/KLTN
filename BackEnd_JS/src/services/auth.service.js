import bcrypt from 'bcrypt';
import { db } from '../config/database.js';
import { logger } from '../utils/logger.js';

class AuthService {
  /**
   * Register new user
   */
  async register(email, password, fullName) {
    try {
      // Validate input
      if (!email || !password || !fullName) {
        throw new Error('Email, password, and name are required');
      }

      // Check if user already exists
      const existingUser = await db.getOne(
        'SELECT * FROM users WHERE email = $1',
        [email]
      );

      if (existingUser) {
        throw new Error('Email already registered');
      }

      // Hash password
      const passwordHash = await bcrypt.hash(password, 10);

      // Create user
      const result = await db.query(
        `INSERT INTO users (email, password_hash, full_name, is_verified, is_active, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
         RETURNING id, email, full_name, phone, is_verified, is_active, created_at, updated_at`,
        [email, passwordHash, fullName, false, true]
      );

      const user = result.rows[0];
      logger.info(`User registered: ${email}`);

      return user;
    } catch (error) {
      logger.error('Register error:', error.message);
      throw error;
    }
  }

  /**
   * Login user
   */
  async login(email, password) {
    try {
      // Validate input
      if (!email || !password) {
        throw new Error('Email and password are required');
      }

      // Find user
      const user = await db.getOne(
        'SELECT * FROM users WHERE email = $1',
        [email]
      );
      logger.info('User found during login:', user);

      if (!user) {
        throw new Error('Invalid email or password');
      }

      // Check if account is active
      if (!user.is_active) {
        throw new Error('Account is deactivated');
      }

      // Verify password
      const isPasswordValid = await bcrypt.compare(password, user.password_hash);
      if (!isPasswordValid) {
        throw new Error('Invalid email or password');
      }

      // Update last login
      await db.query(
        'UPDATE users SET last_login = NOW() WHERE id = $1',
        [user.id]
      );

      logger.info(`User logged in: ${email}`);

      // Return user without password hash
      const { password_hash: _, ...userWithoutPassword } = user;
      return userWithoutPassword;
    } catch (error) {
      logger.error('Login error:', error.message);
      throw error;
    }
  }

  /**
   * Get user by ID
   */
  async getUserById(id) {
    try {
      const user = await db.getOne(
        `SELECT id, email, full_name, phone, is_verified, is_active, created_at, updated_at
         FROM users WHERE id = $1`,
        [id]
      );

      return user;
    } catch (error) {
      logger.error('Get user error:', error.message);
      throw error;
    }
  }

  /**
   * Verify token and get user
   */
  async getCurrentUser(userId) {
    try {
      return await this.getUserById(userId);
    } catch (error) {
      logger.error('Get current user error:', error.message);
      throw error;
    }
  }

  /**
   * Logout user (in stateless JWT, this is just server-side cleanup)
   */
  async logout(userId) {
    try {
      // In a real app, you might invalidate tokens in a blacklist
      logger.info(`User logged out: ${userId}`);
      return { success: true };
    } catch (error) {
      logger.error('Logout error:', error.message);
      throw error;
    }
  }

  /**
   * Change password
   */
  async changePassword(userId, oldPassword, newPassword) {
    try {
      const user = await db.getOne(
        'SELECT * FROM users WHERE id = $1',
        [userId]
      );

      if (!user) {
        throw new Error('User not found');
      }

      // Verify old password
      const isOldPasswordValid = await bcrypt.compare(oldPassword, user.password_hash);
      if (!isOldPasswordValid) {
        throw new Error('Current password is incorrect');
      }

      // Hash new password
      const newPasswordHash = await bcrypt.hash(newPassword, 10);

      // Update password
      await db.query(
        'UPDATE users SET password_hash = $1 WHERE id = $2',
        [newPasswordHash, userId]
      );

      logger.info(`Password changed for user: ${user.email}`);
      return { success: true };
    } catch (error) {
      logger.error('Change password error:', error.message);
      throw error;
    }
  }

  /**
   * Refresh token (validate user still exists and is active)
   */
  async validateTokenUser(userId) {
    try {
      const user = await this.getUserById(userId);

      if (!user || !user.isActive) {
        throw new Error('User is not active');
      }

      return user;
    } catch (error) {
      logger.error('Validate token error:', error.message);
      throw error;
    }
  }
}

export const authService = new AuthService();

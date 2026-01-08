import { logger } from '../utils/logger.js';
import { redisConnection } from '../config/redis.js';

class CacheService {
  /**
   * Get value from cache
   * @param {string} key - Cache key
   * @returns {Promise<any|null>} - Cached value or null if not found
   */
  async get(key) {
    try {
      const client = redisConnection.getClient();
      const value = await client.get(key);
      
      if (value) {
        logger.info(`Cache HIT: ${key}`);
        // Parse JSON if it's a string
        return typeof value === 'string' ? JSON.parse(value) : value;
      }
      
      logger.info(`Cache MISS: ${key}`);
      return null;
    } catch (error) {
      logger.error(`Cache GET error for key ${key}:`, error);
      return null; // Fail gracefully
    }
  }

  /**
   * Set value in cache with optional TTL
   * @param {string} key - Cache key
   * @param {any} value - Value to cache
   * @param {number} ttl - Time to live in seconds (default: 3600 = 1 hour)
   * @returns {Promise<boolean>} - Success status
   */
  async set(key, value, ttl = 3600) {
    try {
      const client = redisConnection.getClient();
      // Convert value to JSON string
      const serialized = typeof value === 'string' ? value : JSON.stringify(value);
      
      await client.set(key, serialized, ttl);
      logger.info(`Cache SET: ${key} (TTL: ${ttl}s)`);
      return true;
    } catch (error) {
      logger.error(`Cache SET error for key ${key}:`, error);
      return false; // Fail gracefully
    }
  }

  /**
   * Delete value from cache
   * @param {string} key - Cache key
   * @returns {Promise<boolean>} - Success status
   */
  async delete(key) {
    try {
      const client = redisConnection.getClient();
      await client.del(key);
      logger.info(`Cache DELETE: ${key}`);
      return true;
    } catch (error) {
      logger.error(`Cache DELETE error for key ${key}:`, error);
      return false;
    }
  }

  /**
   * Clear all cache entries
   * @returns {Promise<boolean>} - Success status
   */
  async flush() {
    try {
      const client = redisConnection.getClient();
      await client.flushAll();
      logger.info('Cache FLUSH: Clearing all cache');
      return true;
    } catch (error) {
      logger.error('Cache FLUSH error:', error);
      return false;
    }
  }

  /**
   * Check if key exists in cache
   * @param {string} key - Cache key
   * @returns {Promise<boolean>} - Whether key exists
   */
  async exists(key) {
    try {
      const client = redisConnection.getClient();
      const exists = await client.exists(key);
      return exists === 1;
    } catch (error) {
      logger.error(`Cache EXISTS error for key ${key}:`, error);
      return false;
    }
  }

  /**
   * Get remaining TTL for a key
   * @param {string} key - Cache key
   * @returns {Promise<number>} - TTL in seconds (-1 if no expiry, -2 if not found)
   */
  async getTTL(key) {
    try {
      const client = redisConnection.getClient();
      return await client.ttl(key);
    } catch (error) {
      logger.error(`Cache getTTL error for key ${key}:`, error);
      return -2;
    }
  }
}

export const cacheService = new CacheService();

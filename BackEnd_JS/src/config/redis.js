import { logger } from '../utils/logger.js';

/**
 * Redis Connection Manager
 * Handles connection to Redis service in db_service
 * Since Redis runs in separate docker-compose, this simulates the connection
 */
class RedisConnection {
  constructor(config = {}) {
    this.config = {
      host: config.host || process.env.REDIS_HOST || 'localhost',
      port: config.port || process.env.REDIS_PORT || 6379,
      password: config.password || process.env.REDIS_PASSWORD || null,
      db: config.db || 0,
      timeout: config.timeout || 5000,
    };
    
    this.client = null;
    this.isConnected = false;
  }

  /**
   * Connect to Redis
   * TODO: When redis package is installed, implement actual connection
   * For now, returns a mock client
   */
  async connect() {
    try {
      logger.info(
        `[Redis] Connecting to ${this.config.host}:${this.config.port}`
      );
      
      // TODO: Uncomment when redis package is installed
      // const redis = require('redis');
      // this.client = redis.createClient({
      //   host: this.config.host,
      //   port: this.config.port,
      //   password: this.config.password,
      //   db: this.config.db,
      // });
      //
      // await this.client.connect();
      
      // For now, use in-memory mock (will not persist across restarts)
      this.client = new InMemoryCache();
      this.isConnected = true;
      
      logger.info('[Redis] Connected successfully (using in-memory fallback)');
      return true;
    } catch (error) {
      logger.error('[Redis] Connection failed:', error);
      this.isConnected = false;
      return false;
    }
  }

  /**
   * Disconnect from Redis
   */
  async disconnect() {
    try {
      if (this.client && this.isConnected) {
        // await this.client.quit();
        this.isConnected = false;
        logger.info('[Redis] Disconnected');
      }
    } catch (error) {
      logger.error('[Redis] Disconnect error:', error);
    }
  }

  /**
   * Get Redis client
   */
  getClient() {
    if (!this.client) {
      throw new Error('Redis client not initialized. Call connect() first.');
    }
    return this.client;
  }

  /**
   * Check connection status
   */
  isReady() {
    return this.isConnected && this.client !== null;
  }
}

/**
 * In-Memory Cache - Fallback implementation
 * Used when Redis package is not available
 * Does NOT persist data across server restarts
 */
class InMemoryCache {
  constructor() {
    this.store = new Map();
    this.timers = new Map();
  }

  async get(key) {
    return this.store.get(key) || null;
  }

  async set(key, value, ttl = null) {
    this.store.set(key, value);
    
    // Clear existing timer if any
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
    }
    
    // Set expiration if TTL provided
    if (ttl) {
      const timer = setTimeout(() => {
        this.store.delete(key);
        this.timers.delete(key);
      }, ttl * 1000);
      this.timers.set(key, timer);
    }
    
    return true;
  }

  async del(key) {
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
      this.timers.delete(key);
    }
    return this.store.delete(key);
  }

  async exists(key) {
    return this.store.has(key) ? 1 : 0;
  }

  async ttl(key) {
    return this.store.has(key) ? -1 : -2;
  }

  async flushAll() {
    this.store.clear();
    this.timers.forEach((timer) => clearTimeout(timer));
    this.timers.clear();
    return true;
  }
}

// Initialize and export
const redisConnection = new RedisConnection();

// Auto-connect on import
redisConnection.connect().catch((err) => {
  logger.error('[Redis] Failed to auto-connect:', err);
});

export { redisConnection, RedisConnection, InMemoryCache };

import pkg from 'pg';
import { logger } from '../utils/logger.js';
import { config } from './env.js';

const { Pool } = pkg;

// Create a connection pool
const pool = new Pool({
  user: config.db.user,
  password: config.db.password,
  host: config.db.host,
  port: config.db.port,
  database: config.db.database,
  max: 20, // maximum number of clients
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Handle pool errors
pool.on('error', (err) => {
  logger.error('❌ Unexpected error on idle client', err.message);
});

// Test the connection
const testConnection = async () => {
  try {
    const result = await pool.query('SELECT NOW()');
    logger.info('✅ Database connection successful');
    return true;
  } catch (error) {
    logger.error('❌ Database connection failed:', error.message);
    return false;
  }
};

// Graceful shutdown
const closePool = async () => {
  try {
    await pool.end();
    logger.info('Database pool closed');
  } catch (error) {
    logger.error('Error closing database pool:', error.message);
  }
};

// Helper functions for common operations
const db = {
  query: (text, params) => pool.query(text, params),
  getOne: async (text, params) => {
    const result = await pool.query(text, params);
    return result.rows[0] || null;
  },
  getAll: async (text, params) => {
    const result = await pool.query(text, params);
    return result.rows;
  },
  run: (text, params) => pool.query(text, params),
};

export { pool, db, testConnection, closePool };
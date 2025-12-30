import dotenv from 'dotenv';

dotenv.config();

export const config = {
  // Server
  port: process.env.PORT || 3000,
  env: process.env.NODE_ENV || 'development',
  
  // Frontend
  frontendUrl: process.env.FRONTEND_URL || 'http://localhost:5173',
  
  // Database
  db: {
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    database: process.env.DB_NAME || 'kltn',
  },
  
  // Web Crawlers
  crawlers: {
    lazada: {
      enabled: process.env.CRAWLER_LAZADA_ENABLED !== 'false',
      timeout: process.env.CRAWLER_LAZADA_TIMEOUT || 30000,
    },
    tiki: {
      enabled: process.env.CRAWLER_TIKI_ENABLED !== 'false',
      timeout: process.env.CRAWLER_TIKI_TIMEOUT || 30000,
    },
  },
  
  // Browser automation
  browser: {
    headless: process.env.BROWSER_HEADLESS !== 'false',
    timeout: process.env.BROWSER_TIMEOUT || 30000,
  },
  
  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
  },
  
  // Rate limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000', 10), // 15 minutes
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10),
  },
  
  // CORS
  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:5173',
    credentials: process.env.CORS_CREDENTIALS === 'true',
  },
};

import app from './src/app.js';
import { config } from './src/config/env.js';
import { logger } from './src/utils/logger.js';
import { testConnection, closePool } from './src/config/database.js';
// import { startJobs } from './src/jobs/index.js';

const PORT = config.port || 3000;

const server = app.listen(PORT, async () => {
  logger.info(`🚀 Server running on port ${PORT}`);
  logger.info(`📊 Environment: ${config.env}`);

  // Test database connection
  const dbConnected = await testConnection();
  if (!dbConnected) {
    logger.error('Failed to connect to database. Exiting...');
    process.exit(1);
  }

  // Start background jobs
  // startJobs();
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  await closePool();
  server.close(() => {
    logger.info('HTTP server closed');
  });
});
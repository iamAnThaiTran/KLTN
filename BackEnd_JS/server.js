import app from './src/app.js';
import { config } from './src/config/env.js';
import { logger } from './src/utils/logger.js';
// import { startJobs } from './src/jobs/index.js';

const PORT = config.port || 3000;

const server = app.listen(PORT, () => {
  logger.info(`🚀 Server running on port ${PORT}`);
  logger.info(`📊 Environment: ${config.env}`);
  
  // Start background jobs
  // startJobs();
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM signal received: closing HTTP server');
  server.close(() => {
    logger.info('HTTP server closed');
  });
});
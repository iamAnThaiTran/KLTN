import cron from 'node-cron';
import { refreshPopularProducts } from './refreshPrices.job.js';
import { checkPriceAlerts } from './checkAlerts.job.js';
import { cleanupOldData } from './cleanupOldData.job.js';
import { logger } from '../utils/logger.js';

export function startJobs() {
  // Refresh prices every 6 hours
  cron.schedule('0 */6 * * *', async () => {
    logger.info('🔄 Starting scheduled price refresh...');
    try {
      await refreshPopularProducts();
      logger.info('✅ Price refresh completed');
    } catch (error) {
      logger.error('❌ Price refresh failed:', error);
    }
  });
  
  // Check price alerts every hour
  cron.schedule('0 * * * *', async () => {
    logger.info('🔔 Checking price alerts...');
    try {
      await checkPriceAlerts();
      logger.info('✅ Price alerts checked');
    } catch (error) {
      logger.error('❌ Price alert check failed:', error);
    }
  });
  
  // Cleanup old data daily at 3 AM
  cron.schedule('0 3 * * *', async () => {
    logger.info('🧹 Starting data cleanup...');
    try {
      await cleanupOldData();
      logger.info('✅ Data cleanup completed');
    } catch (error) {
      logger.error('❌ Data cleanup failed:', error);
    }
  });
  
  logger.info('📅 Background jobs scheduled');
}